"""macro_series store — revision-aware upsert for aggregate series (US-363 §1.1).

Series rows are not events. They are keyed
``(city_id, series_id, geography_id, period)`` and carry ``value``,
``ingested_at`` and ``source_vintage``; the DCN-v2 macro model consumes them,
and the ZIP -> H3 join feeds ``EnrichedH3Feature`` covariates. Nothing is
produced to Kafka.

**Why this is not an append-only table.** Zillow and FHFA reissue full history
every release and revise old periods in place: the value for 2019-03 in the
2026-08 file is not necessarily the value for 2019-03 in the 2026-07 file.
A watermark-based append would keep the first vintage of every revised month
forever and quietly diverge from the publisher. So the store:

* upserts the *current* value for every key, and
* writes the displaced value to ``macro_series_vintages`` before overwriting,
  so a revision is recoverable and auditable rather than lost.

``max_period(series_id, geography_id)`` exists as a **freshness** signal — is
the publisher still publishing? — and is deliberately not used as an ingestion
cursor.

DuckDB backs the store because the feature pipeline already depends on it and
the whole table is small (tens of millions of rows at the outside, one file).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

CURRENT_TABLE = "macro_series"
VINTAGE_TABLE = "macro_series_vintages"


@dataclass(frozen=True)
class UpsertResult:
    """What one release actually changed."""

    inserted: int = 0
    revised: int = 0
    unchanged: int = 0

    @property
    def total(self) -> int:
        return self.inserted + self.revised + self.unchanged


class MacroSeriesStore:
    """DuckDB-backed macro series store with vintage retention."""

    def __init__(self, db_path: str = ":memory:"):
        import duckdb

        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(db_path)
        self._init_tables()

    def _init_tables(self) -> None:
        self.con.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CURRENT_TABLE} (
                city_id VARCHAR,
                series_id VARCHAR,
                geography_level VARCHAR,
                geography_id VARCHAR,
                period DATE,
                value DOUBLE,
                unit VARCHAR,
                source_vintage VARCHAR,
                ingested_at TIMESTAMP,
                -- The key is worth its index. Measured on the 313,065-row
                -- Zillow ZORI release: 0.09s to bulk-insert without the
                -- constraint, 0.28s with it. A 0.2s tax on a monthly job buys
                -- a hard guarantee that no revision path can ever fork a key
                -- into two rows.
                PRIMARY KEY (city_id, series_id, geography_id, period)
            );
            CREATE TABLE IF NOT EXISTS {VINTAGE_TABLE} (
                city_id VARCHAR,
                series_id VARCHAR,
                geography_id VARCHAR,
                period DATE,
                value DOUBLE,
                source_vintage VARCHAR,
                superseded_at TIMESTAMP,
                superseded_by VARCHAR
            );
            """
        )

    # ----------------------------------------------------------------- #
    # writes                                                             #
    # ----------------------------------------------------------------- #
    def upsert(self, observations: Sequence[Any], vintage: Optional[str] = None) -> UpsertResult:
        """Apply one release. Revised values are retained before overwrite.

        ``observations`` are ``SeriesObservation``-shaped: any object with
        ``series_id``, ``geography_level``, ``geography_id``, ``period``,
        ``value``, ``unit``, ``source_vintage`` and ``city_id``.

        Set-based on purpose. A Zillow release is ~313,000 observations
        (measured live: the ZIP-level ZORI file resolves to 313,065 rows
        across all 62 registered cities), and a per-row read-then-write costs
        one round trip each — over a minute per series, every month, for a
        table DuckDB can diff in one statement. The whole release is staged and
        then diffed in four statements.
        """
        if not observations:
            return UpsertResult()

        now = datetime.now(UTC)
        rows = [
            (
                obs.city_id or "",
                obs.series_id,
                obs.geography_level,
                obs.geography_id,
                obs.period,
                float(obs.value),
                getattr(obs, "unit", "") or "",
                vintage or obs.source_vintage,
            )
            for obs in observations
        ]

        # Staging goes through a registered DataFrame rather than
        # `executemany`. A release is hundreds of thousands to millions of
        # rows (the ZIP-level ZHVI file resolves to 2,407,210), and per-row
        # parameter binding costs ~37s per 300k where the frame path plus the
        # four diff statements together take well under a second.
        import pandas as pd

        frame = pd.DataFrame(
            rows,
            columns=[
                "city_id",
                "series_id",
                "geography_level",
                "geography_id",
                "period",
                "value",
                "unit",
                "source_vintage",
            ],
        )
        frame["period"] = pd.to_datetime(frame["period"]).dt.date
        self.con.register("_incoming", frame)
        # A release can repeat a key (a publisher listing the same ZIP twice).
        # Collapse to the last occurrence so the diff below is well defined.
        self.con.execute(
            """
            CREATE OR REPLACE TEMP TABLE _staged AS
            SELECT city_id, series_id, any_value(geography_level) AS geography_level,
                   geography_id, period, last(value) AS value,
                   any_value(unit) AS unit, any_value(source_vintage) AS source_vintage
            FROM _incoming
            GROUP BY city_id, series_id, geography_id, period
            """
        )
        self.con.unregister("_incoming")

        joined = (
            f"FROM _staged s JOIN {CURRENT_TABLE} c "
            f"ON c.city_id = s.city_id AND c.series_id = s.series_id "
            f"AND c.geography_id = s.geography_id AND c.period = s.period"
        )

        revised = int(
            self.con.execute(
                f"SELECT count(1) {joined} WHERE c.value IS DISTINCT FROM s.value"
            ).fetchone()[0]
        )
        unchanged = int(
            self.con.execute(
                f"SELECT count(1) {joined} WHERE c.value IS NOT DISTINCT FROM s.value"
            ).fetchone()[0]
        )

        # Retain every displaced value before overwriting it.
        self.con.execute(
            f"""
            INSERT INTO {VINTAGE_TABLE}
            SELECT c.city_id, c.series_id, c.geography_id, c.period, c.value,
                   c.source_vintage, ?, s.source_vintage
            {joined} WHERE c.value IS DISTINCT FROM s.value
            """,
            [now],
        )
        self.con.execute(
            f"""
            UPDATE {CURRENT_TABLE} AS c
            SET value = s.value, unit = s.unit, source_vintage = s.source_vintage,
                ingested_at = ?
            FROM _staged s
            WHERE c.city_id = s.city_id AND c.series_id = s.series_id
              AND c.geography_id = s.geography_id AND c.period = s.period
              AND c.value IS DISTINCT FROM s.value
            """,
            [now],
        )
        inserted = int(
            self.con.execute(
                f"""
                SELECT count(1) FROM _staged s
                WHERE NOT EXISTS (
                    SELECT 1 FROM {CURRENT_TABLE} c
                    WHERE c.city_id = s.city_id AND c.series_id = s.series_id
                      AND c.geography_id = s.geography_id AND c.period = s.period
                )
                """
            ).fetchone()[0]
        )
        self.con.execute(
            f"""
            INSERT INTO {CURRENT_TABLE}
            SELECT s.city_id, s.series_id, s.geography_level, s.geography_id,
                   s.period, s.value, s.unit, s.source_vintage, ?
            FROM _staged s
            WHERE NOT EXISTS (
                SELECT 1 FROM {CURRENT_TABLE} c
                WHERE c.city_id = s.city_id AND c.series_id = s.series_id
                  AND c.geography_id = s.geography_id AND c.period = s.period
            )
            """,
            [now],
        )

        return UpsertResult(inserted=inserted, revised=revised, unchanged=unchanged)

    # ----------------------------------------------------------------- #
    # reads                                                              #
    # ----------------------------------------------------------------- #
    def value(
        self, city_id: str, series_id: str, geography_id: str, period: date
    ) -> Optional[float]:
        row = self.con.execute(
            f"SELECT value FROM {CURRENT_TABLE} WHERE city_id = ? AND series_id = ? "
            f"AND geography_id = ? AND period = ?",
            [city_id, series_id, geography_id, period],
        ).fetchone()
        return float(row[0]) if row and row[0] is not None else None

    def max_period(self, series_id: str, geography_id: Optional[str] = None) -> Optional[date]:
        """Newest period held for a series. A freshness signal, not a cursor."""
        if geography_id:
            row = self.con.execute(
                f"SELECT max(period) FROM {CURRENT_TABLE} WHERE series_id = ? AND geography_id = ?",
                [series_id, geography_id],
            ).fetchone()
        else:
            row = self.con.execute(
                f"SELECT max(period) FROM {CURRENT_TABLE} WHERE series_id = ?", [series_id]
            ).fetchone()
        return row[0] if row and row[0] is not None else None

    def latest_by_geography(self, city_id: str, series_id: str) -> Dict[str, float]:
        """Most recent value per geography for one city+series."""
        rows = self.con.execute(
            f"""
            SELECT geography_id, value FROM {CURRENT_TABLE} c
            WHERE city_id = ? AND series_id = ?
              AND period = (
                  SELECT max(period) FROM {CURRENT_TABLE} i
                  WHERE i.city_id = c.city_id AND i.series_id = c.series_id
                    AND i.geography_id = c.geography_id
              )
            """,
            [city_id, series_id],
        ).fetchall()
        return {str(g): float(v) for g, v in rows if v is not None}

    def vintages(self, city_id: str, series_id: str, geography_id: str, period: date) -> List[Dict[str, Any]]:
        """Every superseded value for one key, oldest first."""
        rows = self.con.execute(
            f"SELECT value, source_vintage, superseded_at, superseded_by FROM {VINTAGE_TABLE} "
            f"WHERE city_id = ? AND series_id = ? AND geography_id = ? AND period = ? "
            f"ORDER BY superseded_at",
            [city_id, series_id, geography_id, period],
        ).fetchall()
        return [
            {
                "value": float(v) if v is not None else None,
                "source_vintage": sv,
                "superseded_at": sa,
                "superseded_by": sb,
            }
            for v, sv, sa, sb in rows
        ]

    def count(self) -> int:
        return int(self.con.execute(f"SELECT count(1) FROM {CURRENT_TABLE}").fetchone()[0])

    def close(self) -> None:
        self.con.close()
