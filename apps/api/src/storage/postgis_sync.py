"""PostgreSQL / PostGIS Spatial Persistence & Sync Worker for Urban Signal."""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from src.config import settings
from src.spatial.geo_utils import point_to_wkt
from src.spatial.h3_indexer import H3SpatialIndexer

logger = logging.getLogger(__name__)


def _extract_str(val: Any, default: str = "") -> str:
    if val is None or pd.isna(val):
        return default
    if hasattr(val, "value"):
        return str(val.value)
    if isinstance(val, Enum):
        return str(val.value)
    s = str(val)
    if "." in s and (s.startswith("ComplaintCategory.") or s.startswith("JobType.")):
        return s.split(".", 1)[1]
    return s


def _normalize_input(data: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]]) -> pd.DataFrame:
    """Normalize DataFrame, sequence of objects/dicts, or single dict/object to DataFrame."""
    if isinstance(data, pd.DataFrame):
        return data
    if isinstance(data, dict):
        return pd.DataFrame([data])
    if hasattr(data, "model_dump"):
        return pd.DataFrame([data.model_dump()])
    if hasattr(data, "dict"):
        return pd.DataFrame([data.dict()])
    if isinstance(data, (list, tuple)):
        if not data:
            return pd.DataFrame()
        first = data[0]
        if hasattr(first, "model_dump"):
            return pd.DataFrame([x.model_dump() for x in data])
        if hasattr(first, "dict"):
            return pd.DataFrame([x.dict() for x in data])
        if isinstance(first, dict):
            return pd.DataFrame(data)
        if hasattr(first, "__dict__"):
            return pd.DataFrame([x.__dict__ for x in data])
    return pd.DataFrame(data)


# PostGIS DDL Statements with GiST indices on geometry and BRIN indices on timestamp
POSTGIS_DDL_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS postgis;",
    """
    CREATE TABLE IF NOT EXISTS municipal_permits (
        job_id VARCHAR(64) PRIMARY KEY,
        city_id VARCHAR(32) DEFAULT 'nyc',
        job_type VARCHAR(16),
        borough VARCHAR(64),
        block VARCHAR(32),
        lot VARCHAR(32),
        bbl VARCHAR(32),
        address_street VARCHAR(255),
        address_num VARCHAR(64),
        zipcode VARCHAR(16),
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        geom GEOMETRY(Point, 4326),
        estimated_cost DOUBLE PRECISION DEFAULT 0.0,
        proposed_dwelling_units INTEGER,
        existing_dwelling_units INTEGER,
        proposed_stories INTEGER,
        filing_date TIMESTAMPTZ,
        issuance_date TIMESTAMPTZ,
        status VARCHAR(64),
        h3_res7 VARCHAR(15),
        h3_res8 VARCHAR(15),
        h3_res9 VARCHAR(15),
        ingested_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_permits_geom ON municipal_permits USING GIST (geom);",
    "CREATE INDEX IF NOT EXISTS idx_permits_issuance_brin ON municipal_permits USING BRIN (issuance_date);",
    "CREATE INDEX IF NOT EXISTS idx_permits_h3_res9 ON municipal_permits (h3_res9);",
    "CREATE INDEX IF NOT EXISTS idx_permits_h3_res8 ON municipal_permits (h3_res8);",
    "CREATE INDEX IF NOT EXISTS idx_permits_h3_res7 ON municipal_permits (h3_res7);",
    "CREATE INDEX IF NOT EXISTS idx_permits_city_id ON municipal_permits (city_id);",

    """
    CREATE TABLE IF NOT EXISTS municipal_311_complaints (
        incident_id VARCHAR(64) PRIMARY KEY,
        city_id VARCHAR(32) DEFAULT 'nyc',
        complaint_type VARCHAR(128),
        descriptor VARCHAR(255),
        category VARCHAR(32),
        incident_address VARCHAR(255),
        borough VARCHAR(64),
        zipcode VARCHAR(16),
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        geom GEOMETRY(Point, 4326),
        created_date TIMESTAMPTZ,
        closed_date TIMESTAMPTZ,
        status VARCHAR(64),
        h3_res7 VARCHAR(15),
        h3_res8 VARCHAR(15),
        h3_res9 VARCHAR(15),
        ingested_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_complaints_geom ON municipal_311_complaints USING GIST (geom);",
    "CREATE INDEX IF NOT EXISTS idx_complaints_created_brin ON municipal_311_complaints USING BRIN (created_date);",
    "CREATE INDEX IF NOT EXISTS idx_complaints_h3_res9 ON municipal_311_complaints (h3_res9);",
    "CREATE INDEX IF NOT EXISTS idx_complaints_h3_res8 ON municipal_311_complaints (h3_res8);",
    "CREATE INDEX IF NOT EXISTS idx_complaints_h3_res7 ON municipal_311_complaints (h3_res7);",
    "CREATE INDEX IF NOT EXISTS idx_complaints_city_id ON municipal_311_complaints (city_id);",

    """
    CREATE TABLE IF NOT EXISTS municipal_sla_licenses (
        license_id VARCHAR(64) PRIMARY KEY,
        city_id VARCHAR(32) DEFAULT 'nyc',
        license_type VARCHAR(128),
        premises_name VARCHAR(255),
        dba VARCHAR(255),
        address VARCHAR(255),
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        geom GEOMETRY(Point, 4326),
        effective_date TIMESTAMPTZ,
        expiration_date TIMESTAMPTZ,
        license_status VARCHAR(64),
        h3_res7 VARCHAR(15),
        h3_res8 VARCHAR(15),
        h3_res9 VARCHAR(15),
        ingested_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_sla_geom ON municipal_sla_licenses USING GIST (geom);",
    "CREATE INDEX IF NOT EXISTS idx_sla_effective_brin ON municipal_sla_licenses USING BRIN (effective_date);",
    "CREATE INDEX IF NOT EXISTS idx_sla_h3_res9 ON municipal_sla_licenses (h3_res9);",
    "CREATE INDEX IF NOT EXISTS idx_sla_h3_res8 ON municipal_sla_licenses (h3_res8);",
    "CREATE INDEX IF NOT EXISTS idx_sla_h3_res7 ON municipal_sla_licenses (h3_res7);",
    "CREATE INDEX IF NOT EXISTS idx_sla_city_id ON municipal_sla_licenses (city_id);",

    """
    CREATE TABLE IF NOT EXISTS municipal_deeds (
        doc_id VARCHAR(64) PRIMARY KEY,
        city_id VARCHAR(32) DEFAULT 'nyc',
        doc_type VARCHAR(256),
        bbl VARCHAR(32),
        borough VARCHAR(64),
        block VARCHAR(32),
        lot VARCHAR(32),
        document_amount DOUBLE PRECISION DEFAULT 0.0,
        recorded_date TIMESTAMPTZ,
        party1_grantor VARCHAR(255),
        party2_grantee VARCHAR(255),
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        geom GEOMETRY(Point, 4326),
        h3_res7 VARCHAR(15),
        h3_res8 VARCHAR(15),
        h3_res9 VARCHAR(15),
        ingested_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_deeds_geom ON municipal_deeds USING GIST (geom);",
    "CREATE INDEX IF NOT EXISTS idx_deeds_recorded_brin ON municipal_deeds USING BRIN (recorded_date);",
    "CREATE INDEX IF NOT EXISTS idx_deeds_h3_res9 ON municipal_deeds (h3_res9);",
    "CREATE INDEX IF NOT EXISTS idx_deeds_h3_res8 ON municipal_deeds (h3_res8);",
    "CREATE INDEX IF NOT EXISTS idx_deeds_h3_res7 ON municipal_deeds (h3_res7);",
    "CREATE INDEX IF NOT EXISTS idx_deeds_city_id ON municipal_deeds (city_id);",

    """
    CREATE TABLE IF NOT EXISTS feature_store_h3_spatial (
        h3_index VARCHAR(15),
        city_id VARCHAR(32) DEFAULT 'nyc',
        h3_resolution INTEGER,
        as_of_date TIMESTAMPTZ,
        geom GEOMETRY(Polygon, 4326),
        centroid GEOMETRY(Point, 4326),
        capex_density_decayed DOUBLE PRECISION DEFAULT 0.0,
        permit_count_60d INTEGER DEFAULT 0,
        permit_count_180d INTEGER DEFAULT 0,
        permit_velocity DOUBLE PRECISION DEFAULT 0.0,
        complaints_neglect_count INTEGER DEFAULT 0,
        complaints_qol_count INTEGER DEFAULT 0,
        shift_ratio_311 DOUBLE PRECISION DEFAULT 1.0,
        sla_active_licenses INTEGER DEFAULT 0,
        sla_new_filings_90d INTEGER DEFAULT 0,
        deed_total_volume_180d DOUBLE PRECISION DEFAULT 0.0,
        deed_transaction_count_180d INTEGER DEFAULT 0,
        lims_score DOUBLE PRECISION DEFAULT 0.0,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (h3_index, as_of_date)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_feature_h3_geom ON feature_store_h3_spatial USING GIST (geom);",
    "CREATE INDEX IF NOT EXISTS idx_feature_h3_centroid ON feature_store_h3_spatial USING GIST (centroid);",
    "CREATE INDEX IF NOT EXISTS idx_feature_h3_as_of_brin ON feature_store_h3_spatial USING BRIN (as_of_date);",
    "CREATE INDEX IF NOT EXISTS idx_feature_city_id ON feature_store_h3_spatial (city_id);",

    """
    CREATE TABLE IF NOT EXISTS catalyst_alerts (
        alert_id VARCHAR(64) PRIMARY KEY,
        city_id VARCHAR(32) DEFAULT 'nyc',
        h3_index VARCHAR(15),
        h3_resolution INTEGER DEFAULT 9,
        lims_score DOUBLE PRECISION,
        predicted_delta_6m DOUBLE PRECISION,
        predicted_delta_12m DOUBLE PRECISION,
        macro_outperformance_prob_18m DOUBLE PRECISION,
        top_catalyst_drivers JSONB,
        centroid_lat DOUBLE PRECISION,
        centroid_lng DOUBLE PRECISION,
        centroid GEOMETRY(Point, 4326),
        timestamp TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_catalyst_alerts_centroid ON catalyst_alerts USING GIST (centroid);",
    "CREATE INDEX IF NOT EXISTS idx_catalyst_alerts_timestamp_brin ON catalyst_alerts USING BRIN (timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_city_id ON catalyst_alerts (city_id);"
]

# SQLite compatible fallback DDL (for local unit testing without active postgres server)
SQLITE_DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS municipal_permits (
        job_id TEXT PRIMARY KEY,
        city_id TEXT DEFAULT 'nyc',
        job_type TEXT,
        borough TEXT,
        block TEXT,
        lot TEXT,
        bbl TEXT,
        address_street TEXT,
        address_num TEXT,
        zipcode TEXT,
        latitude REAL,
        longitude REAL,
        geom_wkt TEXT,
        estimated_cost REAL DEFAULT 0.0,
        proposed_dwelling_units INTEGER,
        existing_dwelling_units INTEGER,
        proposed_stories INTEGER,
        filing_date TEXT,
        issuance_date TEXT,
        status TEXT,
        h3_res7 TEXT,
        h3_res8 TEXT,
        h3_res9 TEXT,
        ingested_at TEXT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_permits_h3_res9 ON municipal_permits (h3_res9);",
    "CREATE INDEX IF NOT EXISTS idx_permits_issuance ON municipal_permits (issuance_date);",
    "CREATE INDEX IF NOT EXISTS idx_permits_city_id ON municipal_permits (city_id);",

    """
    CREATE TABLE IF NOT EXISTS municipal_311_complaints (
        incident_id TEXT PRIMARY KEY,
        city_id TEXT DEFAULT 'nyc',
        complaint_type TEXT,
        descriptor TEXT,
        category TEXT,
        incident_address TEXT,
        borough TEXT,
        zipcode TEXT,
        latitude REAL,
        longitude REAL,
        geom_wkt TEXT,
        created_date TEXT,
        closed_date TEXT,
        status TEXT,
        h3_res7 TEXT,
        h3_res8 TEXT,
        h3_res9 TEXT,
        ingested_at TEXT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_complaints_h3_res9 ON municipal_311_complaints (h3_res9);",
    "CREATE INDEX IF NOT EXISTS idx_complaints_created ON municipal_311_complaints (created_date);",
    "CREATE INDEX IF NOT EXISTS idx_complaints_city_id ON municipal_311_complaints (city_id);",

    """
    CREATE TABLE IF NOT EXISTS municipal_sla_licenses (
        license_id TEXT PRIMARY KEY,
        city_id TEXT DEFAULT 'nyc',
        license_type TEXT,
        premises_name TEXT,
        dba TEXT,
        address TEXT,
        latitude REAL,
        longitude REAL,
        geom_wkt TEXT,
        effective_date TEXT,
        expiration_date TEXT,
        license_status TEXT,
        h3_res7 TEXT,
        h3_res8 TEXT,
        h3_res9 TEXT,
        ingested_at TEXT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_sla_h3_res9 ON municipal_sla_licenses (h3_res9);",
    "CREATE INDEX IF NOT EXISTS idx_sla_city_id ON municipal_sla_licenses (city_id);",

    """
    CREATE TABLE IF NOT EXISTS municipal_deeds (
        doc_id TEXT PRIMARY KEY,
        city_id TEXT DEFAULT 'nyc',
        doc_type TEXT,
        bbl TEXT,
        borough TEXT,
        block TEXT,
        lot TEXT,
        document_amount REAL DEFAULT 0.0,
        recorded_date TEXT,
        party1_grantor TEXT,
        party2_grantee TEXT,
        latitude REAL,
        longitude REAL,
        geom_wkt TEXT,
        h3_res7 TEXT,
        h3_res8 TEXT,
        h3_res9 TEXT,
        ingested_at TEXT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_deeds_h3_res9 ON municipal_deeds (h3_res9);",
    "CREATE INDEX IF NOT EXISTS idx_deeds_city_id ON municipal_deeds (city_id);",

    """
    CREATE TABLE IF NOT EXISTS feature_store_h3_spatial (
        h3_index TEXT,
        city_id TEXT DEFAULT 'nyc',
        h3_resolution INTEGER,
        as_of_date TEXT,
        geom_wkt TEXT,
        centroid_wkt TEXT,
        capex_density_decayed REAL DEFAULT 0.0,
        permit_count_60d INTEGER DEFAULT 0,
        permit_count_180d INTEGER DEFAULT 0,
        permit_velocity REAL DEFAULT 0.0,
        complaints_neglect_count INTEGER DEFAULT 0,
        complaints_qol_count INTEGER DEFAULT 0,
        shift_ratio_311 REAL DEFAULT 1.0,
        sla_active_licenses INTEGER DEFAULT 0,
        sla_new_filings_90d INTEGER DEFAULT 0,
        deed_total_volume_180d REAL DEFAULT 0.0,
        deed_transaction_count_180d INTEGER DEFAULT 0,
        lims_score REAL DEFAULT 0.0,
        created_at TEXT,
        PRIMARY KEY (h3_index, as_of_date)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_feature_city_id ON feature_store_h3_spatial (city_id);",

    """
    CREATE TABLE IF NOT EXISTS catalyst_alerts (
        alert_id TEXT PRIMARY KEY,
        city_id TEXT DEFAULT 'nyc',
        h3_index TEXT,
        h3_resolution INTEGER DEFAULT 9,
        lims_score REAL,
        predicted_delta_6m REAL,
        predicted_delta_12m REAL,
        macro_outperformance_prob_18m REAL,
        top_catalyst_drivers TEXT,
        centroid_lat REAL,
        centroid_lng REAL,
        centroid_wkt TEXT,
        timestamp TEXT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_alerts_city_id ON catalyst_alerts (city_id);"
]


class PostGISSpatialSync:
    """Manages PostgreSQL / PostGIS spatial table lifecycles, GiST/BRIN indexing, and synchronization from DuckDB/Kafka."""

    def __init__(
        self,
        connection_string: Optional[str] = None,
        engine: Optional[Engine] = None,
    ):
        self.indexer = H3SpatialIndexer()
        if engine is not None:
            self.engine = engine
        else:
            uri = connection_string or settings.postgres_uri
            self.engine = create_engine(uri, pool_pre_ping=True)

        self.is_sqlite = self.engine.dialect.name == "sqlite"
        self.is_postgres = self.engine.dialect.name == "postgresql"

    @classmethod
    def get_postgis_ddl_statements(cls) -> List[str]:
        """Return raw PostGIS DDL and index statements for verification and migrations."""
        return list(POSTGIS_DDL_STATEMENTS)

    def init_tables(self):
        """Execute DDL scripts to create PostGIS spatial tables and GiST/BRIN indices."""
        statements = SQLITE_DDL_STATEMENTS if self.is_sqlite else POSTGIS_DDL_STATEMENTS
        with self.engine.begin() as conn:
            for stmt in statements:
                cleaned = stmt.strip()
                if cleaned:
                    try:
                        conn.execute(text(cleaned))
                    except Exception as e:
                        logger.warning("DDL execution notice on '%s...': %s", cleaned[:40], e)

    def sync_permits(
        self,
        df_or_records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert/upsert municipal permits with spatial point geometry and multi-city support."""
        df = _normalize_input(df_or_records)
        if df.empty:
            return

        records = []
        for _, row in df.iterrows():
            lat = row.get("latitude")
            lng = row.get("longitude")
            lat_f = float(lat) if pd.notna(lat) and lat is not None else None
            lng_f = float(lng) if pd.notna(lng) and lng is not None else None
            wkt = point_to_wkt(lat_f, lng_f) if lat_f is not None and lng_f is not None else None

            dt_issuance = str(row.get("issuance_date")) if pd.notna(row.get("issuance_date")) else None
            dt_filing = str(row.get("filing_date")) if pd.notna(row.get("filing_date")) else None
            dt_ingested = str(row.get("ingested_at")) if pd.notna(row.get("ingested_at")) else datetime.now(timezone.utc).isoformat()

            row_city = row.get("city_id")
            resolved_city = _extract_str(row_city if pd.notna(row_city) and row_city is not None else (city_id or "nyc"), "nyc")

            records.append({
                "job_id": str(row.get("job_id")),
                "city_id": resolved_city,
                "job_type": _extract_str(row.get("job_type"), ""),
                "borough": _extract_str(row.get("borough"), ""),
                "block": _extract_str(row.get("block"), ""),
                "lot": _extract_str(row.get("lot"), ""),
                "bbl": _extract_str(row.get("bbl"), ""),
                "address_street": _extract_str(row.get("address_street"), ""),
                "address_num": _extract_str(row.get("address_num"), ""),
                "zipcode": _extract_str(row.get("zipcode"), ""),
                "latitude": lat_f,
                "longitude": lng_f,
                "geom_wkt": wkt,
                "estimated_cost": float(row.get("estimated_cost", 0.0) or 0.0),
                "proposed_dwelling_units": int(row.get("proposed_dwelling_units", 0) or 0),
                "existing_dwelling_units": int(row.get("existing_dwelling_units", 0) or 0),
                "proposed_stories": int(row.get("proposed_stories", 0) or 0),
                "filing_date": dt_filing,
                "issuance_date": dt_issuance,
                "status": _extract_str(row.get("status"), "ISSUED"),
                "h3_res7": _extract_str(row.get("h3_res7"), ""),
                "h3_res8": _extract_str(row.get("h3_res8"), ""),
                "h3_res9": _extract_str(row.get("h3_res9"), ""),
                "ingested_at": dt_ingested,
            })

        with self.engine.begin() as conn:
            if self.is_postgres:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT INTO municipal_permits (
                                job_id, city_id, job_type, borough, block, lot, bbl, address_street, address_num,
                                zipcode, latitude, longitude, geom, estimated_cost, proposed_dwelling_units,
                                existing_dwelling_units, proposed_stories, filing_date, issuance_date,
                                status, h3_res7, h3_res8, h3_res9, ingested_at
                            ) VALUES (
                                :job_id, :city_id, :job_type, :borough, :block, :lot, :bbl, :address_street, :address_num,
                                :zipcode, :latitude, :longitude,
                                CASE WHEN :longitude IS NOT NULL AND :latitude IS NOT NULL
                                     THEN ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                                     ELSE NULL END,
                                :estimated_cost, :proposed_dwelling_units, :existing_dwelling_units,
                                :proposed_stories, :filing_date, :issuance_date, :status,
                                :h3_res7, :h3_res8, :h3_res9, :ingested_at
                            )
                            ON CONFLICT (job_id) DO UPDATE SET
                                city_id = EXCLUDED.city_id,
                                estimated_cost = EXCLUDED.estimated_cost,
                                status = EXCLUDED.status,
                                issuance_date = EXCLUDED.issuance_date;
                        """),
                        r
                    )
            else:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT OR REPLACE INTO municipal_permits (
                                job_id, city_id, job_type, borough, block, lot, bbl, address_street, address_num,
                                zipcode, latitude, longitude, geom_wkt, estimated_cost, proposed_dwelling_units,
                                existing_dwelling_units, proposed_stories, filing_date, issuance_date,
                                status, h3_res7, h3_res8, h3_res9, ingested_at
                            ) VALUES (
                                :job_id, :city_id, :job_type, :borough, :block, :lot, :bbl, :address_street, :address_num,
                                :zipcode, :latitude, :longitude, :geom_wkt, :estimated_cost, :proposed_dwelling_units,
                                :existing_dwelling_units, :proposed_stories, :filing_date, :issuance_date,
                                :status, :h3_res7, :h3_res8, :h3_res9, :ingested_at
                            );
                        """),
                        r
                    )

    def insert_permits_batch(
        self,
        records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert municipal permits with multi-city support."""
        self.sync_permits(records, city_id=city_id)

    def sync_complaints(
        self,
        df_or_records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert/upsert 311 complaints with spatial point geometry and multi-city support."""
        df = _normalize_input(df_or_records)
        if df.empty:
            return

        records = []
        for _, row in df.iterrows():
            lat = row.get("latitude")
            lng = row.get("longitude")
            lat_f = float(lat) if pd.notna(lat) and lat is not None else None
            lng_f = float(lng) if pd.notna(lng) and lng is not None else None
            wkt = point_to_wkt(lat_f, lng_f) if lat_f is not None and lng_f is not None else None

            row_city = row.get("city_id")
            resolved_city = _extract_str(row_city if pd.notna(row_city) and row_city is not None else (city_id or "nyc"), "nyc")

            records.append({
                "incident_id": str(row.get("incident_id")),
                "city_id": resolved_city,
                "complaint_type": _extract_str(row.get("complaint_type"), ""),
                "descriptor": _extract_str(row.get("descriptor"), ""),
                "category": _extract_str(row.get("category"), "OTHER"),
                "incident_address": _extract_str(row.get("incident_address"), ""),
                "borough": _extract_str(row.get("borough"), ""),
                "zipcode": _extract_str(row.get("zipcode"), ""),
                "latitude": lat_f,
                "longitude": lng_f,
                "geom_wkt": wkt,
                "created_date": str(row.get("created_date")) if pd.notna(row.get("created_date")) else None,
                "closed_date": str(row.get("closed_date")) if pd.notna(row.get("closed_date")) else None,
                "status": _extract_str(row.get("status"), "Open"),
                "h3_res7": _extract_str(row.get("h3_res7"), ""),
                "h3_res8": _extract_str(row.get("h3_res8"), ""),
                "h3_res9": _extract_str(row.get("h3_res9"), ""),
                "ingested_at": str(row.get("ingested_at")) if pd.notna(row.get("ingested_at")) else datetime.now(timezone.utc).isoformat(),
            })

        with self.engine.begin() as conn:
            if self.is_postgres:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT INTO municipal_311_complaints (
                                incident_id, city_id, complaint_type, descriptor, category, incident_address,
                                borough, zipcode, latitude, longitude, geom, created_date, closed_date,
                                status, h3_res7, h3_res8, h3_res9, ingested_at
                            ) VALUES (
                                :incident_id, :city_id, :complaint_type, :descriptor, :category, :incident_address,
                                :borough, :zipcode, :latitude, :longitude,
                                CASE WHEN :longitude IS NOT NULL AND :latitude IS NOT NULL
                                     THEN ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                                     ELSE NULL END,
                                :created_date, :closed_date, :status, :h3_res7, :h3_res8, :h3_res9, :ingested_at
                            )
                            ON CONFLICT (incident_id) DO UPDATE SET
                                city_id = EXCLUDED.city_id,
                                status = EXCLUDED.status,
                                closed_date = EXCLUDED.closed_date;
                        """),
                        r
                    )
            else:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT OR REPLACE INTO municipal_311_complaints (
                                incident_id, city_id, complaint_type, descriptor, category, incident_address,
                                borough, zipcode, latitude, longitude, geom_wkt, created_date, closed_date,
                                status, h3_res7, h3_res8, h3_res9, ingested_at
                            ) VALUES (
                                :incident_id, :city_id, :complaint_type, :descriptor, :category, :incident_address,
                                :borough, :zipcode, :latitude, :longitude, :geom_wkt, :created_date, :closed_date,
                                :status, :h3_res7, :h3_res8, :h3_res9, :ingested_at
                            );
                        """),
                        r
                    )

    def insert_complaints_batch(
        self,
        records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert 311 complaints with multi-city support."""
        self.sync_complaints(records, city_id=city_id)

    def sync_sla(
        self,
        df_or_records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert/upsert SLA licenses with spatial point geometry and multi-city support."""
        df = _normalize_input(df_or_records)
        if df.empty:
            return

        records = []
        for _, row in df.iterrows():
            lat = row.get("latitude")
            lng = row.get("longitude")
            lat_f = float(lat) if pd.notna(lat) and lat is not None else None
            lng_f = float(lng) if pd.notna(lng) and lng is not None else None
            wkt = point_to_wkt(lat_f, lng_f) if lat_f is not None and lng_f is not None else None

            row_city = row.get("city_id")
            resolved_city = _extract_str(row_city if pd.notna(row_city) and row_city is not None else (city_id or "nyc"), "nyc")

            records.append({
                "license_id": str(row.get("license_id")),
                "city_id": resolved_city,
                "license_type": _extract_str(row.get("license_type"), ""),
                "premises_name": _extract_str(row.get("premises_name"), ""),
                "dba": _extract_str(row.get("dba"), ""),
                "address": _extract_str(row.get("address"), ""),
                "latitude": lat_f,
                "longitude": lng_f,
                "geom_wkt": wkt,
                "effective_date": str(row.get("effective_date")) if pd.notna(row.get("effective_date")) else None,
                "expiration_date": str(row.get("expiration_date")) if pd.notna(row.get("expiration_date")) else None,
                "license_status": _extract_str(row.get("license_status"), "ACTIVE"),
                "h3_res7": _extract_str(row.get("h3_res7"), ""),
                "h3_res8": _extract_str(row.get("h3_res8"), ""),
                "h3_res9": _extract_str(row.get("h3_res9"), ""),
                "ingested_at": str(row.get("ingested_at")) if pd.notna(row.get("ingested_at")) else datetime.now(timezone.utc).isoformat(),
            })

        with self.engine.begin() as conn:
            if self.is_postgres:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT INTO municipal_sla_licenses (
                                license_id, city_id, license_type, premises_name, dba, address,
                                latitude, longitude, geom, effective_date, expiration_date,
                                license_status, h3_res7, h3_res8, h3_res9, ingested_at
                            ) VALUES (
                                :license_id, :city_id, :license_type, :premises_name, :dba, :address,
                                :latitude, :longitude,
                                CASE WHEN :longitude IS NOT NULL AND :latitude IS NOT NULL
                                     THEN ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                                     ELSE NULL END,
                                :effective_date, :expiration_date, :license_status, :h3_res7, :h3_res8, :h3_res9, :ingested_at
                            )
                            ON CONFLICT (license_id) DO UPDATE SET
                                city_id = EXCLUDED.city_id,
                                license_status = EXCLUDED.license_status,
                                expiration_date = EXCLUDED.expiration_date;
                        """),
                        r
                    )
            else:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT OR REPLACE INTO municipal_sla_licenses (
                                license_id, city_id, license_type, premises_name, dba, address,
                                latitude, longitude, geom_wkt, effective_date, expiration_date,
                                license_status, h3_res7, h3_res8, h3_res9, ingested_at
                            ) VALUES (
                                :license_id, :city_id, :license_type, :premises_name, :dba, :address,
                                :latitude, :longitude, :geom_wkt, :effective_date, :expiration_date,
                                :license_status, :h3_res7, :h3_res8, :h3_res9, :ingested_at
                            );
                        """),
                        r
                    )

    def insert_sla_batch(
        self,
        records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert SLA licenses with multi-city support."""
        self.sync_sla(records, city_id=city_id)

    def sync_deeds(
        self,
        df_or_records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert/upsert ACRIS property deeds with spatial point geometry and multi-city support."""
        df = _normalize_input(df_or_records)
        if df.empty:
            return

        records = []
        for _, row in df.iterrows():
            lat = row.get("latitude")
            lng = row.get("longitude")
            lat_f = float(lat) if pd.notna(lat) and lat is not None else None
            lng_f = float(lng) if pd.notna(lng) and lng is not None else None
            wkt = point_to_wkt(lat_f, lng_f) if lat_f is not None and lng_f is not None else None

            row_city = row.get("city_id")
            resolved_city = _extract_str(row_city if pd.notna(row_city) and row_city is not None else (city_id or "nyc"), "nyc")

            records.append({
                "doc_id": str(row.get("doc_id")),
                "city_id": resolved_city,
                "doc_type": _extract_str(row.get("doc_type"), "DEED"),
                "bbl": _extract_str(row.get("bbl"), ""),
                "borough": _extract_str(row.get("borough"), ""),
                "block": _extract_str(row.get("block"), ""),
                "lot": _extract_str(row.get("lot"), ""),
                "document_amount": float(row.get("document_amount", 0.0) or 0.0),
                "recorded_date": str(row.get("recorded_date")) if pd.notna(row.get("recorded_date")) else None,
                "party1_grantor": _extract_str(row.get("party1_grantor"), ""),
                "party2_grantee": _extract_str(row.get("party2_grantee"), ""),
                "latitude": lat_f,
                "longitude": lng_f,
                "geom_wkt": wkt,
                "h3_res7": _extract_str(row.get("h3_res7"), ""),
                "h3_res8": _extract_str(row.get("h3_res8"), ""),
                "h3_res9": _extract_str(row.get("h3_res9"), ""),
                "ingested_at": str(row.get("ingested_at")) if pd.notna(row.get("ingested_at")) else datetime.now(timezone.utc).isoformat(),
            })

        with self.engine.begin() as conn:
            if self.is_postgres:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT INTO municipal_deeds (
                                doc_id, city_id, doc_type, bbl, borough, block, lot, document_amount,
                                recorded_date, party1_grantor, party2_grantee, latitude, longitude,
                                geom, h3_res7, h3_res8, h3_res9, ingested_at
                            ) VALUES (
                                :doc_id, :city_id, :doc_type, :bbl, :borough, :block, :lot, :document_amount,
                                :recorded_date, :party1_grantor, :party2_grantee, :latitude, :longitude,
                                CASE WHEN :longitude IS NOT NULL AND :latitude IS NOT NULL
                                     THEN ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                                     ELSE NULL END,
                                :h3_res7, :h3_res8, :h3_res9, :ingested_at
                            )
                            ON CONFLICT (doc_id) DO UPDATE SET
                                city_id = EXCLUDED.city_id,
                                document_amount = EXCLUDED.document_amount;
                        """),
                        r
                    )
            else:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT OR REPLACE INTO municipal_deeds (
                                doc_id, city_id, doc_type, bbl, borough, block, lot, document_amount,
                                recorded_date, party1_grantor, party2_grantee, latitude, longitude,
                                geom_wkt, h3_res7, h3_res8, h3_res9, ingested_at
                            ) VALUES (
                                :doc_id, :city_id, :doc_type, :bbl, :borough, :block, :lot, :document_amount,
                                :recorded_date, :party1_grantor, :party2_grantee, :latitude, :longitude,
                                :geom_wkt, :h3_res7, :h3_res8, :h3_res9, :ingested_at
                            );
                        """),
                        r
                    )

    def insert_deeds_batch(
        self,
        records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert municipal deeds with multi-city support."""
        self.sync_deeds(records, city_id=city_id)

    def sync_features(
        self,
        df_or_records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert/upsert aggregated H3 spatial features with polygon boundary geometry and multi-city support."""
        df = _normalize_input(df_or_records)
        if df.empty:
            return

        records = []
        for _, row in df.iterrows():
            h3_index = str(row.get("h3_index"))
            res = int(row.get("h3_resolution", 9))
            lat, lng = self.indexer.h3_to_latlng(h3_index)
            centroid_wkt = point_to_wkt(lat, lng)

            boundary = self.indexer.h3_to_boundary(h3_index, geojson_format=True)
            # GeoJSON polygon coordinate list format
            if boundary and len(boundary) >= 3:
                coords = ", ".join(f"{pt[0]} {pt[1]}" for pt in boundary)
                # close loop if not closed
                if boundary[0] != boundary[-1]:
                    coords += f", {boundary[0][0]} {boundary[0][1]}"
                polygon_wkt = f"POLYGON(({coords}))"
            else:
                polygon_wkt = None

            as_of = str(row.get("as_of_date")) if pd.notna(row.get("as_of_date")) else datetime.now(timezone.utc).isoformat()

            row_city = row.get("city_id")
            resolved_city = _extract_str(row_city if pd.notna(row_city) and row_city is not None else (city_id or "nyc"), "nyc")

            records.append({
                "h3_index": h3_index,
                "city_id": resolved_city,
                "h3_resolution": res,
                "as_of_date": as_of,
                "polygon_wkt": polygon_wkt,
                "centroid_wkt": centroid_wkt,
                "centroid_lat": lat,
                "centroid_lng": lng,
                "capex_density_decayed": float(row.get("capex_density_decayed", 0.0)),
                "permit_count_60d": int(row.get("permit_count_60d", 0)),
                "permit_count_180d": int(row.get("permit_count_180d", 0)),
                "permit_velocity": float(row.get("permit_velocity", 0.0)),
                "complaints_neglect_count": int(row.get("complaints_neglect_count", 0)),
                "complaints_qol_count": int(row.get("complaints_qol_count", 0)),
                "shift_ratio_311": float(row.get("shift_ratio_311", 1.0)),
                "sla_active_licenses": int(row.get("sla_active_licenses", 0)),
                "sla_new_filings_90d": int(row.get("sla_new_filings_90d", 0)),
                "deed_total_volume_180d": float(row.get("deed_total_volume_180d", 0.0)),
                "deed_transaction_count_180d": int(row.get("deed_transaction_count_180d", 0)),
                "lims_score": float(row.get("lims_score", 0.0)),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        with self.engine.begin() as conn:
            if self.is_postgres:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT INTO feature_store_h3_spatial (
                                h3_index, city_id, h3_resolution, as_of_date, geom, centroid,
                                capex_density_decayed, permit_count_60d, permit_count_180d,
                                permit_velocity, complaints_neglect_count, complaints_qol_count,
                                shift_ratio_311, sla_active_licenses, sla_new_filings_90d,
                                deed_total_volume_180d, deed_transaction_count_180d, lims_score, created_at
                            ) VALUES (
                                :h3_index, :city_id, :h3_resolution, :as_of_date,
                                CASE WHEN :polygon_wkt IS NOT NULL THEN ST_GeomFromText(:polygon_wkt, 4326) ELSE NULL END,
                                CASE WHEN :centroid_lng IS NOT NULL AND :centroid_lat IS NOT NULL
                                     THEN ST_SetSRID(ST_MakePoint(:centroid_lng, :centroid_lat), 4326) ELSE NULL END,
                                :capex_density_decayed, :permit_count_60d, :permit_count_180d,
                                :permit_velocity, :complaints_neglect_count, :complaints_qol_count,
                                :shift_ratio_311, :sla_active_licenses, :sla_new_filings_90d,
                                :deed_total_volume_180d, :deed_transaction_count_180d, :lims_score, :created_at
                            )
                            ON CONFLICT (h3_index, as_of_date) DO UPDATE SET
                                city_id = EXCLUDED.city_id,
                                capex_density_decayed = EXCLUDED.capex_density_decayed,
                                permit_velocity = EXCLUDED.permit_velocity,
                                shift_ratio_311 = EXCLUDED.shift_ratio_311,
                                lims_score = EXCLUDED.lims_score;
                        """),
                        r
                    )
            else:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT OR REPLACE INTO feature_store_h3_spatial (
                                h3_index, city_id, h3_resolution, as_of_date, geom_wkt, centroid_wkt,
                                capex_density_decayed, permit_count_60d, permit_count_180d,
                                permit_velocity, complaints_neglect_count, complaints_qol_count,
                                shift_ratio_311, sla_active_licenses, sla_new_filings_90d,
                                deed_total_volume_180d, deed_transaction_count_180d, lims_score, created_at
                            ) VALUES (
                                :h3_index, :city_id, :h3_resolution, :as_of_date, :polygon_wkt, :centroid_wkt,
                                :capex_density_decayed, :permit_count_60d, :permit_count_180d,
                                :permit_velocity, :complaints_neglect_count, :complaints_qol_count,
                                :shift_ratio_311, :sla_active_licenses, :sla_new_filings_90d,
                                :deed_total_volume_180d, :deed_transaction_count_180d, :lims_score, :created_at
                            );
                        """),
                        r
                    )

    def insert_h3_features(
        self,
        records: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert H3 features with multi-city support."""
        self.sync_features(records, city_id=city_id)

    def sync_catalyst_alerts(
        self,
        alerts: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert high-momentum catalyst alerts with centroid point geometry and multi-city support."""
        if not alerts and not isinstance(alerts, pd.DataFrame):
            return

        if isinstance(alerts, pd.DataFrame):
            alert_items = alerts.to_dict(orient="records")
        elif isinstance(alerts, dict):
            alert_items = [alerts]
        elif hasattr(alerts, "model_dump"):
            alert_items = [alerts.model_dump()]
        elif isinstance(alerts, (list, tuple)):
            alert_items = [x.model_dump() if hasattr(x, "model_dump") else x for x in alerts]
        else:
            alert_items = list(alerts)

        if not alert_items:
            return

        records = []
        for a in alert_items:
            lat = a.get("centroid_lat")
            lng = a.get("centroid_lng")
            lat_f = float(lat) if lat is not None else None
            lng_f = float(lng) if lng is not None else None
            wkt = point_to_wkt(lat_f, lng_f) if lat_f is not None and lng_f is not None else None

            drivers = a.get("top_catalyst_drivers", [])
            drivers_json = json.dumps(drivers) if isinstance(drivers, (list, dict)) else str(drivers)

            a_city = a.get("city_id")
            resolved_city = _extract_str(a_city if pd.notna(a_city) and a_city is not None else (city_id or "nyc"), "nyc")

            records.append({
                "alert_id": str(a.get("alert_id")),
                "city_id": resolved_city,
                "h3_index": str(a.get("h3_index")),
                "h3_resolution": int(a.get("h3_resolution", 9)),
                "lims_score": float(a.get("lims_score", 0.0)),
                "predicted_delta_6m": float(a.get("predicted_delta_6m", 0.0)),
                "predicted_delta_12m": float(a.get("predicted_delta_12m", 0.0)),
                "macro_outperformance_prob_18m": float(a.get("macro_outperformance_prob_18m", 0.0)),
                "top_catalyst_drivers": drivers_json,
                "centroid_lat": lat_f,
                "centroid_lng": lng_f,
                "centroid_wkt": wkt,
                "timestamp": str(a.get("timestamp")) if pd.notna(a.get("timestamp")) else datetime.now(timezone.utc).isoformat(),
            })

        with self.engine.begin() as conn:
            if self.is_postgres:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT INTO catalyst_alerts (
                                alert_id, city_id, h3_index, h3_resolution, lims_score, predicted_delta_6m,
                                predicted_delta_12m, macro_outperformance_prob_18m, top_catalyst_drivers,
                                centroid_lat, centroid_lng, centroid, timestamp
                            ) VALUES (
                                :alert_id, :city_id, :h3_index, :h3_resolution, :lims_score, :predicted_delta_6m,
                                :predicted_delta_12m, :macro_outperformance_prob_18m, CAST(:top_catalyst_drivers AS jsonb),
                                :centroid_lat, :centroid_lng,
                                CASE WHEN :centroid_lng IS NOT NULL AND :centroid_lat IS NOT NULL
                                     THEN ST_SetSRID(ST_MakePoint(:centroid_lng, :centroid_lat), 4326) ELSE NULL END,
                                :timestamp
                            )
                            ON CONFLICT (alert_id) DO UPDATE SET
                                city_id = EXCLUDED.city_id,
                                lims_score = EXCLUDED.lims_score;
                        """),
                        r
                    )
            else:
                for r in records:
                    conn.execute(
                        text("""
                            INSERT OR REPLACE INTO catalyst_alerts (
                                alert_id, city_id, h3_index, h3_resolution, lims_score, predicted_delta_6m,
                                predicted_delta_12m, macro_outperformance_prob_18m, top_catalyst_drivers,
                                centroid_lat, centroid_lng, centroid_wkt, timestamp
                            ) VALUES (
                                :alert_id, :city_id, :h3_index, :h3_resolution, :lims_score, :predicted_delta_6m,
                                :predicted_delta_12m, :macro_outperformance_prob_18m, :top_catalyst_drivers,
                                :centroid_lat, :centroid_lng, :centroid_wkt, :timestamp
                            );
                        """),
                        r
                    )

    def insert_catalyst_alerts(
        self,
        alerts: Union[pd.DataFrame, Sequence[Any], Dict[str, Any]],
        city_id: Optional[str] = None,
    ):
        """Batch insert catalyst alerts with multi-city support."""
        self.sync_catalyst_alerts(alerts, city_id=city_id)

    # ---------------------------------------------------------
    # Multi-City Query Methods
    # ---------------------------------------------------------

    def get_features_for_h3(
        self,
        h3_index: str,
        city_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query aggregated H3 features by index with optional city_id filter."""
        query = "SELECT * FROM feature_store_h3_spatial WHERE h3_index = :h3_index"
        params: Dict[str, Any] = {"h3_index": h3_index, "limit": limit}
        if city_id is not None:
            query += " AND city_id = :city_id"
            params["city_id"] = city_id
        query += " ORDER BY as_of_date DESC LIMIT :limit"

        with self.engine.connect() as conn:
            res = conn.execute(text(query), params).mappings().fetchall()
            return [dict(r) for r in res]

    def get_recent_alerts(
        self,
        city_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query recent catalyst alerts with optional city_id filter."""
        query = "SELECT * FROM catalyst_alerts"
        params: Dict[str, Any] = {"limit": limit}
        if city_id is not None:
            query += " WHERE city_id = :city_id"
            params["city_id"] = city_id
        query += " ORDER BY timestamp DESC LIMIT :limit"

        with self.engine.connect() as conn:
            res = conn.execute(text(query), params).mappings().fetchall()
            return [dict(r) for r in res]

    def query_permits_by_h3(
        self,
        h3_index: str,
        resolution: int = 9,
        city_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query municipal permits matching an H3 cell index, optionally filtered by city_id."""
        col = f"h3_res{resolution}" if resolution in (7, 8, 9) else "h3_res9"
        query = f"SELECT * FROM municipal_permits WHERE {col} = :h3_index"
        params: Dict[str, Any] = {"h3_index": h3_index, "limit": limit}
        if city_id is not None:
            query += " AND city_id = :city_id"
            params["city_id"] = city_id
        query += " ORDER BY issuance_date DESC, filing_date DESC LIMIT :limit"

        with self.engine.connect() as conn:
            res = conn.execute(text(query), params).mappings().fetchall()
            return [dict(r) for r in res]

    def query_complaints_by_h3(
        self,
        h3_index: str,
        resolution: int = 9,
        city_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query municipal 311 complaints matching an H3 cell index, optionally filtered by city_id."""
        col = f"h3_res{resolution}" if resolution in (7, 8, 9) else "h3_res9"
        query = f"SELECT * FROM municipal_311_complaints WHERE {col} = :h3_index"
        params: Dict[str, Any] = {"h3_index": h3_index, "limit": limit}
        if city_id is not None:
            query += " AND city_id = :city_id"
            params["city_id"] = city_id
        query += " ORDER BY created_date DESC LIMIT :limit"

        with self.engine.connect() as conn:
            res = conn.execute(text(query), params).mappings().fetchall()
            return [dict(r) for r in res]

    def query_sla_by_h3(
        self,
        h3_index: str,
        resolution: int = 9,
        city_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query SLA licenses matching an H3 cell index, optionally filtered by city_id."""
        col = f"h3_res{resolution}" if resolution in (7, 8, 9) else "h3_res9"
        query = f"SELECT * FROM municipal_sla_licenses WHERE {col} = :h3_index"
        params: Dict[str, Any] = {"h3_index": h3_index, "limit": limit}
        if city_id is not None:
            query += " AND city_id = :city_id"
            params["city_id"] = city_id
        query += " ORDER BY effective_date DESC LIMIT :limit"

        with self.engine.connect() as conn:
            res = conn.execute(text(query), params).mappings().fetchall()
            return [dict(r) for r in res]

    def query_deeds_by_h3(
        self,
        h3_index: str,
        resolution: int = 9,
        city_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query property deeds matching an H3 cell index, optionally filtered by city_id."""
        col = f"h3_res{resolution}" if resolution in (7, 8, 9) else "h3_res9"
        query = f"SELECT * FROM municipal_deeds WHERE {col} = :h3_index"
        params: Dict[str, Any] = {"h3_index": h3_index, "limit": limit}
        if city_id is not None:
            query += " AND city_id = :city_id"
            params["city_id"] = city_id
        query += " ORDER BY recorded_date DESC LIMIT :limit"

        with self.engine.connect() as conn:
            res = conn.execute(text(query), params).mappings().fetchall()
            return [dict(r) for r in res]

    def get_permits_by_city(self, city_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Query permits for a specific city."""
        with self.engine.connect() as conn:
            res = conn.execute(
                text("SELECT * FROM municipal_permits WHERE city_id = :city_id ORDER BY issuance_date DESC LIMIT :limit"),
                {"city_id": city_id, "limit": limit},
            ).mappings().fetchall()
            return [dict(r) for r in res]

    def get_complaints_by_city(self, city_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Query complaints for a specific city."""
        with self.engine.connect() as conn:
            res = conn.execute(
                text("SELECT * FROM municipal_311_complaints WHERE city_id = :city_id ORDER BY created_date DESC LIMIT :limit"),
                {"city_id": city_id, "limit": limit},
            ).mappings().fetchall()
            return [dict(r) for r in res]

    def get_sla_by_city(self, city_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Query SLA licenses for a specific city."""
        with self.engine.connect() as conn:
            res = conn.execute(
                text("SELECT * FROM municipal_sla_licenses WHERE city_id = :city_id ORDER BY effective_date DESC LIMIT :limit"),
                {"city_id": city_id, "limit": limit},
            ).mappings().fetchall()
            return [dict(r) for r in res]

    def get_deeds_by_city(self, city_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Query deeds for a specific city."""
        with self.engine.connect() as conn:
            res = conn.execute(
                text("SELECT * FROM municipal_deeds WHERE city_id = :city_id ORDER BY recorded_date DESC LIMIT :limit"),
                {"city_id": city_id, "limit": limit},
            ).mappings().fetchall()
            return [dict(r) for r in res]

    def sync_from_duckdb(self, duckdb_pipeline_or_con: Any):
        """Extract all raw and aggregated tables from DuckDB analytical feature store and sync to PostGIS."""
        con = getattr(duckdb_pipeline_or_con, "con", duckdb_pipeline_or_con)

        # 1. Permits
        try:
            df_permits = con.execute("SELECT * FROM raw_permits").df()
            if not df_permits.empty:
                self.sync_permits(df_permits)
        except Exception as e:
            logger.debug("Sync permits note: %s", e)

        # 2. 311 Complaints
        try:
            df_complaints = con.execute("SELECT * FROM raw_complaints").df()
            if not df_complaints.empty:
                self.sync_complaints(df_complaints)
        except Exception as e:
            logger.debug("Sync complaints note: %s", e)

        # 3. SLA
        try:
            df_sla = con.execute("SELECT * FROM raw_sla").df()
            if not df_sla.empty:
                self.sync_sla(df_sla)
        except Exception as e:
            logger.debug("Sync SLA note: %s", e)

        # 4. Deeds
        try:
            df_deeds = con.execute("SELECT * FROM raw_deeds").df()
            if not df_deeds.empty:
                self.sync_deeds(df_deeds)
        except Exception as e:
            logger.debug("Sync deeds note: %s", e)

        # 5. Features
        try:
            df_features = con.execute("SELECT * FROM feature_store_h3").df()
            if not df_features.empty:
                self.sync_features(df_features)
        except Exception as e:
            logger.debug("Sync features note: %s", e)

    def sync_kafka_record(self, record: Dict[str, Any], topic: str):
        """Sync single deserialized Kafka event into PostgreSQL / PostGIS spatial table."""
        df = pd.DataFrame([record])
        if topic == settings.topic_permits:
            self.sync_permits(df)
        elif topic == settings.topic_311:
            self.sync_complaints(df)
        elif topic == settings.topic_sla:
            self.sync_sla(df)
        elif topic == settings.topic_deeds:
            self.sync_deeds(df)
        elif topic == settings.topic_enriched_h3:
            self.sync_features(df)
        elif topic == settings.topic_catalyst_alerts:
            self.sync_catalyst_alerts([record])
