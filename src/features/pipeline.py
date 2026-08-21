"""DuckDB and Polars analytical feature pipeline for out-of-core spatial-temporal aggregations."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import duckdb
import pandas as pd
import polars as pl
from src.features.lims_calculator import LIMSCalculator
from src.features.shift_dynamics import ComplaintShiftDynamics
from src.features.time_decay import TimeDecayedCapExCalculator
from src.spatial.h3_indexer import H3SpatialIndexer


class SpatialFeaturePipeline:
    """Out-of-core analytical aggregation pipeline using DuckDB and Polars."""

    def __init__(self, db_path: str = ":memory:"):
        self.con = duckdb.connect(db_path)
        self.h3_indexer = H3SpatialIndexer()
        self.capex_calc = TimeDecayedCapExCalculator(halflife_days=180.0)
        self.shift_calc = ComplaintShiftDynamics(epsilon=1.0)
        self.lims_calc = LIMSCalculator()
        self._init_tables()

    def _init_tables(self):
        """Initialize in-memory or persistent DuckDB analytical tables."""
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS raw_permits (
                job_id VARCHAR PRIMARY KEY,
                job_type VARCHAR,
                latitude DOUBLE,
                longitude DOUBLE,
                estimated_cost DOUBLE,
                issuance_date TIMESTAMP,
                h3_res7 VARCHAR,
                h3_res8 VARCHAR,
                h3_res9 VARCHAR,
                ingested_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS raw_complaints (
                incident_id VARCHAR PRIMARY KEY,
                complaint_type VARCHAR,
                category VARCHAR,
                latitude DOUBLE,
                longitude DOUBLE,
                created_date TIMESTAMP,
                h3_res7 VARCHAR,
                h3_res8 VARCHAR,
                h3_res9 VARCHAR,
                ingested_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS raw_sla (
                license_id VARCHAR PRIMARY KEY,
                license_type VARCHAR,
                latitude DOUBLE,
                longitude DOUBLE,
                effective_date TIMESTAMP,
                license_status VARCHAR,
                h3_res7 VARCHAR,
                h3_res8 VARCHAR,
                h3_res9 VARCHAR,
                ingested_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS raw_deeds (
                doc_id VARCHAR PRIMARY KEY,
                doc_type VARCHAR,
                document_amount DOUBLE,
                recorded_date TIMESTAMP,
                latitude DOUBLE,
                longitude DOUBLE,
                h3_res7 VARCHAR,
                h3_res8 VARCHAR,
                h3_res9 VARCHAR,
                ingested_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feature_store_h3 (
                h3_index VARCHAR,
                h3_resolution INTEGER,
                as_of_date TIMESTAMP,
                capex_density_decayed DOUBLE,
                permit_count_60d INTEGER,
                permit_count_180d INTEGER,
                permit_velocity DOUBLE,
                complaints_neglect_count INTEGER,
                complaints_qol_count INTEGER,
                shift_ratio_311 DOUBLE,
                sla_active_licenses INTEGER,
                sla_new_filings_90d INTEGER,
                deed_total_volume_180d DOUBLE,
                deed_transaction_count_180d INTEGER,
                lims_score DOUBLE,
                PRIMARY KEY (h3_index, as_of_date)
            );
        """)

    def insert_permits(self, df: pd.DataFrame):
        """Batch insert DOB permits into DuckDB."""
        if not df.empty:
            cols = ["job_id", "job_type", "latitude", "longitude", "estimated_cost", "issuance_date", "h3_res7", "h3_res8", "h3_res9", "ingested_at"]
            filtered = df[[c for c in cols if c in df.columns]].copy()
            self.con.register("df_permits_temp", filtered)
            self.con.execute("""
                INSERT OR REPLACE INTO raw_permits
                SELECT * FROM df_permits_temp
            """)
            self.con.unregister("df_permits_temp")

    def insert_complaints(self, df: pd.DataFrame):
        """Batch insert 311 complaints into DuckDB."""
        if not df.empty:
            cols = ["incident_id", "complaint_type", "category", "latitude", "longitude", "created_date", "h3_res7", "h3_res8", "h3_res9", "ingested_at"]
            filtered = df[[c for c in cols if c in df.columns]].copy()
            self.con.register("df_complaints_temp", filtered)
            self.con.execute("""
                INSERT OR REPLACE INTO raw_complaints
                SELECT * FROM df_complaints_temp
            """)
            self.con.unregister("df_complaints_temp")

    def insert_sla(self, df: pd.DataFrame):
        """Batch insert SLA licenses into DuckDB."""
        if not df.empty:
            cols = ["license_id", "license_type", "latitude", "longitude", "effective_date", "license_status", "h3_res7", "h3_res8", "h3_res9", "ingested_at"]
            filtered = df[[c for c in cols if c in df.columns]].copy()
            self.con.register("df_sla_temp", filtered)
            self.con.execute("""
                INSERT OR REPLACE INTO raw_sla
                SELECT * FROM df_sla_temp
            """)
            self.con.unregister("df_sla_temp")

    def insert_deeds(self, df: pd.DataFrame):
        """Batch insert ACRIS deeds into DuckDB."""
        if not df.empty:
            cols = ["doc_id", "doc_type", "document_amount", "recorded_date", "latitude", "longitude", "h3_res7", "h3_res8", "h3_res9", "ingested_at"]
            filtered = df[[c for c in cols if c in df.columns]].copy()
            self.con.register("df_deeds_temp", filtered)
            self.con.execute("""
                INSERT OR REPLACE INTO raw_deeds
                SELECT * FROM df_deeds_temp
            """)
            self.con.unregister("df_deeds_temp")

    def compute_h3_cell_features(
        self,
        h3_index: str,
        resolution: int = 9,
        as_of_date: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """Compute rolling spatio-temporal features for a single H3 cell as of a specific date."""
        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc)

        col_name = f"h3_res{resolution}"
        dt_str = as_of_date.strftime("%Y-%m-%d %H:%M:%S")
        dt_60d = (as_of_date - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        dt_180d = (as_of_date - timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S")
        dt_360d = (as_of_date - timedelta(days=360)).strftime("%Y-%m-%d %H:%M:%S")

        # 1. Permits query
        permits_df = self.con.execute(f"""
            SELECT estimated_cost, issuance_date
            FROM raw_permits
            WHERE {col_name} = ? AND issuance_date <= ? AND issuance_date >= ?
        """, [h3_index, dt_str, dt_360d]).df()

        area_km2 = self.h3_indexer.get_cell_area_km2(resolution)
        capex_density = self.capex_calc.compute_batch_decay(
            permits_df, cost_col="estimated_cost", date_col="issuance_date",
            cell_area_km2=area_km2, as_of_date=as_of_date,
        )

        cnt_60d = self.con.execute(f"""
            SELECT COUNT(*) FROM raw_permits
            WHERE {col_name} = ? AND issuance_date <= ? AND issuance_date >= ?
        """, [h3_index, dt_str, dt_60d]).fetchone()[0]

        cnt_180d = self.con.execute(f"""
            SELECT COUNT(*) FROM raw_permits
            WHERE {col_name} = ? AND issuance_date <= ? AND issuance_date >= ?
        """, [h3_index, dt_str, dt_180d]).fetchone()[0]

        # Permit velocity: annualized rate of change (60d vs 180d baseline)
        baseline_rate = (cnt_180d / 3.0) if cnt_180d > 0 else 0.1
        velocity = (cnt_60d - baseline_rate) / baseline_rate

        # 2. 311 Complaints query
        complaints_res = self.con.execute(f"""
            SELECT
                SUM(CASE WHEN category = 'NEGLECT' THEN 1 ELSE 0 END) AS neglect_cnt,
                SUM(CASE WHEN category = 'QOL' THEN 1 ELSE 0 END) AS qol_cnt
            FROM raw_complaints
            WHERE {col_name} = ? AND created_date <= ? AND created_date >= ?
        """, [h3_index, dt_str, dt_180d]).fetchone()

        neglect_cnt = complaints_res[0] or 0
        qol_cnt = complaints_res[1] or 0
        shift_ratio = self.shift_calc.calculate_ratio(qol_cnt, neglect_cnt)

        # 3. SLA Licenses query
        sla_res = self.con.execute(f"""
            SELECT
                COUNT(*) AS active_lic,
                SUM(CASE WHEN effective_date >= ? THEN 1 ELSE 0 END) AS new_lic
            FROM raw_sla
            WHERE {col_name} = ? AND effective_date <= ?
        """, [dt_60d, h3_index, dt_str]).fetchone()

        active_sla = sla_res[0] or 0
        new_sla_90d = sla_res[1] or 0

        # 4. Deeds query
        deeds_res = self.con.execute(f"""
            SELECT
                COALESCE(SUM(document_amount), 0.0) AS total_vol,
                COUNT(*) AS tx_cnt
            FROM raw_deeds
            WHERE {col_name} = ? AND recorded_date <= ? AND recorded_date >= ?
        """, [h3_index, dt_str, dt_180d]).fetchone()

        deed_vol = deeds_res[0] or 0.0
        deed_cnt = deeds_res[1] or 0

        # 5. Compute LIMS Score
        lims = self.lims_calc.compute_scaled_lims(
            capex=capex_density,
            permit_velocity=velocity,
            shift_ratio_311=shift_ratio,
            sla_activations=float(new_sla_90d),
        )

        return {
            "h3_index": h3_index,
            "h3_resolution": resolution,
            "as_of_date": as_of_date,
            "capex_density_decayed": round(capex_density, 2),
            "permit_count_60d": int(cnt_60d),
            "permit_count_180d": int(cnt_180d),
            "permit_velocity": round(float(velocity), 4),
            "complaints_neglect_count": int(neglect_cnt),
            "complaints_qol_count": int(qol_cnt),
            "shift_ratio_311": round(float(shift_ratio), 4),
            "sla_active_licenses": int(active_sla),
            "sla_new_filings_90d": int(new_sla_90d),
            "deed_total_volume_180d": round(float(deed_vol), 2),
            "deed_transaction_count_180d": int(deed_cnt),
            "lims_score": lims,
        }

    def export_feature_matrix_polars(self, as_of_date: Optional[datetime] = None) -> pl.DataFrame:
        """Export full spatial feature matrix as high-performance Polars DataFrame."""
        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc)

        df = self.con.execute("""
            SELECT * FROM feature_store_h3
        """).df()

        if df.empty:
            return pl.DataFrame()
        return pl.DataFrame(df.to_dict(orient="list"))
