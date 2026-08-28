"""Read-only NYC TLC trip-record prototype (US-362).

The TLC publishes monthly Parquet files rather than a paginated event feed. This
module deliberately stays outside the city registry and Kafka ingestion path:
it profiles a bounded analytical sample, validates trip quality, and produces
zone/OD aggregates suitable for deciding whether a production mobility signal
is worth building.

DuckDB is used for both local files and the TLC CloudFront URLs. Queries are
constructed only from source-controlled column names and escaped paths; values
from the input data never become SQL.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

TLC_TRIP_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
TLC_ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"

MAX_REASONABLE_DURATION_SECONDS = 24 * 60 * 60
MAX_REASONABLE_DISTANCE_MILES = 500.0
MAX_REASONABLE_FARE = 2_000.0

DATASET_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "yellow": {
        "pickup_at": ("tpep_pickup_datetime", "lpep_pickup_datetime", "pickup_datetime"),
        "dropoff_at": ("tpep_dropoff_datetime", "lpep_dropoff_datetime", "dropoff_datetime"),
        "pickup_zone": ("pulocationid", "pu_location_id"),
        "dropoff_zone": ("dolocationid", "do_location_id"),
        "distance_miles": ("trip_distance", "trip_miles"),
        "duration_seconds": ("trip_time",),
        "fare_amount": ("fare_amount",),
        "total_amount": ("total_amount",),
        "passenger_count": ("passenger_count",),
    },
    "hvfhv": {
        "pickup_at": ("pickup_datetime",),
        "dropoff_at": ("dropoff_datetime",),
        "pickup_zone": ("pulocationid", "pu_location_id"),
        "dropoff_zone": ("dolocationid", "do_location_id"),
        "distance_miles": ("trip_miles", "trip_distance"),
        "duration_seconds": ("trip_time",),
        "fare_amount": ("base_passenger_fare", "fare_amount"),
        "total_amount": ("total_amount",),
        "passenger_count": ("passenger_count",),
    },
}

# Columns used when HVFHV does not publish a total_amount column. This is a
# transparent sum of its published fare components, not an attempt to infer a
# retail price from a meter fare.
HVFHV_TOTAL_COMPONENTS = (
    "base_passenger_fare",
    "tolls",
    "bcf",
    "sales_tax",
    "congestion_surcharge",
    "airport_fee",
    "tips",
)


@dataclass(frozen=True)
class DatasetInput:
    """One TLC dataset and its source label."""

    name: str
    trip_path: str


class TLCAnalysisError(RuntimeError):
    """Raised when a TLC input cannot satisfy the prototype contract."""


def trip_url(dataset: str, year: int, month: int) -> str:
    """Return TLC's published monthly Parquet URL for a dataset."""
    if dataset not in {"yellow", "hvfhv", "green", "fhv"}:
        raise ValueError(f"unsupported TLC dataset: {dataset!r}")
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    return f"{TLC_TRIP_BASE_URL}/{dataset}_tripdata_{year:04d}-{month:02d}.parquet"


def _sql_string(value: str | Path) -> str:
    """Escape a local path or URL for a DuckDB string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def _identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _normalize_column(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch == "_")


def _columns(con: duckdb.DuckDBPyConnection, relation: str) -> list[str]:
    rows = con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()
    return [str(row[0]) for row in rows]


def _read_relation(
    con: duckdb.DuckDBPyConnection, path: str | Path, *, csv: bool = False
) -> str:
    source = _sql_string(path)
    if csv:
        return f"read_csv_auto({source}, header=true, null_padding=true)"
    return f"read_parquet({source}, union_by_name=true)"


def _find_column(columns: Sequence[str], candidates: Sequence[str]) -> str | None:
    by_normalized = {_normalize_column(column): column for column in columns}
    for candidate in candidates:
        if _normalize_column(candidate) in by_normalized:
            return by_normalized[_normalize_column(candidate)]
    return None


def _profile(
    con: duckdb.DuckDBPyConnection,
    dataset: str,
    relation: str,
) -> dict[str, Any]:
    columns = _columns(con, relation)
    aliases = DATASET_ALIASES[dataset]
    resolved = {
        canonical: _find_column(columns, candidates)
        for canonical, candidates in aliases.items()
    }
    missing = [
        name
        for name in ("pickup_at", "dropoff_at", "pickup_zone", "dropoff_zone")
        if resolved[name] is None
    ]
    row = con.execute(f"SELECT COUNT(*) FROM {relation}").fetchone()
    if row is None:
        raise TLCAnalysisError("could not count TLC relation")
    row_count = int(row[0])
    return {
        "dataset": dataset,
        "row_count": row_count,
        "columns": columns,
        "canonical_columns": resolved,
        "missing_required_columns": missing,
        "derived_total_amount": dataset == "hvfhv" and resolved["total_amount"] is None,
        "status": "ok" if not missing else "invalid",
    }


def _null_expression(column: str | None, alias: str) -> str:
    if column is None:
        return f"NULL::{alias}"
    return _identifier(column)


def _canonical_select(dataset: str, columns: Sequence[str]) -> str:
    aliases = DATASET_ALIASES[dataset]
    resolved = {
        canonical: _find_column(columns, candidates)
        for canonical, candidates in aliases.items()
    }
    pickup = _null_expression(resolved["pickup_at"], "TIMESTAMP")
    dropoff = _null_expression(resolved["dropoff_at"], "TIMESTAMP")
    duration = _null_expression(resolved["duration_seconds"], "DOUBLE")
    if resolved["duration_seconds"] is None and resolved["pickup_at"] and resolved["dropoff_at"]:
        duration = (
            f"date_diff('second', try_cast({pickup} AS TIMESTAMP), "
            f"try_cast({dropoff} AS TIMESTAMP))::DOUBLE"
        )

    total = resolved["total_amount"]
    if total:
        total_expression = _identifier(total)
    elif dataset == "hvfhv":
        available = [_find_column(columns, (name,)) for name in HVFHV_TOTAL_COMPONENTS]
        terms = [f"coalesce({_identifier(column)}, 0)" for column in available if column]
        total_expression = " + ".join(terms) if terms else "NULL::DOUBLE"
    else:
        total_expression = "NULL::DOUBLE"

    return ",\n".join(
        [
            f"try_cast({pickup} AS TIMESTAMP) AS pickup_at",
            f"try_cast({dropoff} AS TIMESTAMP) AS dropoff_at",
            f"try_cast({_null_expression(resolved['pickup_zone'], 'INTEGER')} AS INTEGER) AS pickup_zone",
            f"try_cast({_null_expression(resolved['dropoff_zone'], 'INTEGER')} AS INTEGER) AS dropoff_zone",
            f"try_cast({_null_expression(resolved['distance_miles'], 'DOUBLE')} AS DOUBLE) AS distance_miles",
            f"try_cast({duration} AS DOUBLE) AS duration_seconds",
            f"try_cast({_null_expression(resolved['fare_amount'], 'DOUBLE')} AS DOUBLE) AS fare_amount",
            f"try_cast({total_expression} AS DOUBLE) AS total_amount",
            f"try_cast({_null_expression(resolved['passenger_count'], 'DOUBLE')} AS DOUBLE) AS passenger_count",
        ]
    )


def _quality_query() -> str:
    return """
        SELECT
            count(*)::BIGINT AS rows_total,
            count(*) FILTER (WHERE pickup_at IS NULL)::BIGINT AS null_pickup_at,
            count(*) FILTER (WHERE dropoff_at IS NULL)::BIGINT AS null_dropoff_at,
            count(*) FILTER (WHERE pickup_zone IS NULL)::BIGINT AS null_pickup_zone,
            count(*) FILTER (WHERE dropoff_zone IS NULL)::BIGINT AS null_dropoff_zone,
            count(*) FILTER (WHERE distance_miles IS NULL)::BIGINT AS null_distance_miles,
            count(*) FILTER (WHERE duration_seconds IS NULL)::BIGINT AS null_duration_seconds,
            count(*) FILTER (WHERE fare_amount IS NULL)::BIGINT AS null_fare_amount,
            count(*) FILTER (WHERE total_amount IS NULL)::BIGINT AS null_total_amount,
            count(*) FILTER (WHERE duration_seconds <= 0 OR duration_seconds > $duration_limit)::BIGINT AS impossible_duration,
            count(*) FILTER (WHERE distance_miles < 0 OR distance_miles > $distance_limit)::BIGINT AS impossible_distance,
            count(*) FILTER (WHERE fare_amount < 0 OR fare_amount > $fare_limit)::BIGINT AS impossible_fare,
            count(*) FILTER (WHERE total_amount < 0 OR total_amount > $fare_limit)::BIGINT AS impossible_total_amount
        FROM trips
    """


def _valid_predicate() -> str:
    return """
        pickup_at IS NOT NULL AND dropoff_at IS NOT NULL
        AND pickup_zone IS NOT NULL AND dropoff_zone IS NOT NULL
        AND duration_seconds > 0 AND duration_seconds <= $duration_limit
        AND distance_miles >= 0 AND distance_miles <= $distance_limit
        AND fare_amount >= 0 AND fare_amount <= $fare_limit
        AND EXISTS (SELECT 1 FROM zones p WHERE p.location_id = pickup_zone)
        AND EXISTS (SELECT 1 FROM zones d WHERE d.location_id = dropoff_zone)
    """


def _fetch_dicts(
    con: duckdb.DuckDBPyConnection,
    query: str,
    params: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    result = con.execute(query, params or {})
    names = [str(column[0]) for column in result.description]
    return [dict(zip(names, row)) for row in result.fetchall()]


def _json_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _quality(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    row = _fetch_dicts(
        con,
        _quality_query(),
        {
            "duration_limit": MAX_REASONABLE_DURATION_SECONDS,
            "distance_limit": MAX_REASONABLE_DISTANCE_MILES,
            "fare_limit": MAX_REASONABLE_FARE,
        },
    )[0]
    return {key: _json_value(value) for key, value in row.items()}


def _aggregates(
    con: duckdb.DuckDBPyConnection,
    top_n: int,
) -> dict[str, Any]:
    valid = _valid_predicate()
    params = {
        "duration_limit": MAX_REASONABLE_DURATION_SECONDS,
        "distance_limit": MAX_REASONABLE_DISTANCE_MILES,
        "fare_limit": MAX_REASONABLE_FARE,
    }
    totals = _fetch_dicts(
        con,
        f"""
        SELECT count(*)::BIGINT AS trips,
               coalesce(sum(fare_amount), 0)::DOUBLE AS fare_amount,
               coalesce(sum(total_amount), 0)::DOUBLE AS total_amount,
               avg(distance_miles)::DOUBLE AS average_distance_miles,
               avg(duration_seconds)::DOUBLE AS average_duration_seconds
        FROM trips WHERE {valid}
        """,
        params,
    )[0]
    zones = _fetch_dicts(
        con,
        f"""
        SELECT pickup_zone AS location_id,
               coalesce(z.borough, 'Unknown') AS borough,
               coalesce(z.zone, 'Unknown') AS zone,
               count(*)::BIGINT AS trips,
               sum(fare_amount)::DOUBLE AS fare_amount,
               avg(distance_miles)::DOUBLE AS average_distance_miles,
               avg(duration_seconds)::DOUBLE AS average_duration_seconds,
               count(DISTINCT dropoff_zone)::BIGINT AS distinct_dropoff_zones
        FROM trips t LEFT JOIN zones z ON z.location_id = t.pickup_zone
        WHERE {valid}
        GROUP BY pickup_zone, z.borough, z.zone
        ORDER BY trips DESC, location_id
        LIMIT {int(top_n)}
        """,
        params,
    )
    od_pairs = _fetch_dicts(
        con,
        f"""
        SELECT pickup_zone AS pickup_location_id,
               dropoff_zone AS dropoff_location_id,
               count(*)::BIGINT AS trips,
               avg(distance_miles)::DOUBLE AS average_distance_miles,
               avg(duration_seconds)::DOUBLE AS average_duration_seconds,
               sum(fare_amount)::DOUBLE AS fare_amount
        FROM trips
        WHERE {valid}
        GROUP BY pickup_zone, dropoff_zone
        ORDER BY trips DESC, pickup_location_id, dropoff_location_id
        LIMIT {int(top_n)}
        """,
        params,
    )
    return {
        "valid_totals": {key: _json_value(value) for key, value in totals.items()},
        "top_pickup_zones": [
            {key: _json_value(value) for key, value in row.items()} for row in zones
        ],
        "top_od_pairs": [
            {key: _json_value(value) for key, value in row.items()} for row in od_pairs
        ],
    }


def _zone_profile(con: duckdb.DuckDBPyConnection, relation: str) -> dict[str, Any]:
    columns = _columns(con, relation)
    location = _find_column(columns, ("LocationID", "location_id", "zone_id"))
    borough = _find_column(columns, ("Borough", "borough"))
    zone = _find_column(columns, ("Zone", "zone"))
    if not location:
        raise TLCAnalysisError("taxi zone lookup is missing LocationID")
    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW zones AS
        SELECT try_cast({_identifier(location)} AS INTEGER) AS location_id,
               {_identifier(borough) if borough else "NULL::VARCHAR"} AS borough,
               {_identifier(zone) if zone else "NULL::VARCHAR"} AS zone
        FROM {relation}
        WHERE {_identifier(location)} IS NOT NULL
        """
    )
    count_row = con.execute("SELECT count(*) FROM zones").fetchone()
    if count_row is None:
        raise TLCAnalysisError("could not count taxi zones")
    count = int(count_row[0])
    return {"row_count": count, "columns": columns, "location_column": location}


def _invalid_zone_counts(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    rows = _fetch_dicts(
        con,
        """
        SELECT
          count(*) FILTER (WHERE t.pickup_zone IS NOT NULL AND p.location_id IS NULL)::BIGINT AS invalid_pickup_zone,
          count(*) FILTER (WHERE t.dropoff_zone IS NOT NULL AND d.location_id IS NULL)::BIGINT AS invalid_dropoff_zone
        FROM trips t
        LEFT JOIN zones p ON p.location_id = t.pickup_zone
        LEFT JOIN zones d ON d.location_id = t.dropoff_zone
        """,
    )[0]
    return {key: int(value) for key, value in rows.items()}


def _compare_benchmark(
    actual: Mapping[str, Any], expected: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Compare totals to an optional TLC-published aggregate benchmark.

    The TLC landing page links the raw monthly files but does not expose a
    machine-readable aggregate-total endpoint. Keeping the benchmark optional
    lets a researcher paste a value from a TLC aggregate report without making
    the prototype invent one.
    """
    if not expected:
        return {"status": "not_provided", "expected": None, "differences": {}}
    differences: dict[str, Any] = {}
    for key in ("trips", "fare_amount", "total_amount"):
        if key not in expected or key not in actual:
            continue
        observed = float(actual[key])
        target = float(expected[key])
        differences[key] = {
            "observed": observed,
            "expected": target,
            "absolute_difference": observed - target,
            "relative_difference": (observed - target) / target if target else None,
        }
    return {"status": "compared", "expected": dict(expected), "differences": differences}


def analyze_dataset(
    dataset: str,
    trip_path: str | Path,
    zones_path: str | Path,
    *,
    top_n: int = 20,
    row_limit: int | None = None,
    expected_totals: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Profile one TLC Parquet file and return a JSON-serializable report."""
    if dataset not in DATASET_ALIASES:
        raise ValueError(f"unsupported analytical dataset: {dataset!r}")
    if top_n < 1:
        raise ValueError("top_n must be positive")
    if row_limit is not None and row_limit < 1:
        raise ValueError("row_limit must be positive")

    con = duckdb.connect()
    try:
        raw_relation = _read_relation(con, trip_path)
        profile = _profile(con, dataset, raw_relation)
        if profile["missing_required_columns"]:
            raise TLCAnalysisError(
                f"{dataset} schema is missing required columns: "
                f"{profile['missing_required_columns']}"
            )
        selected = _canonical_select(dataset, profile["columns"])
        limit_clause = f" LIMIT {int(row_limit)}" if row_limit else ""
        con.execute(
            f"CREATE OR REPLACE TEMP VIEW trips AS SELECT {selected} FROM {raw_relation}{limit_clause}"
        )
        zone_relation = _read_relation(con, zones_path, csv=True)
        zone_profile = _zone_profile(con, zone_relation)
        quality = _quality(con)
        quality.update(_invalid_zone_counts(con))
        aggregates = _aggregates(con, top_n)
        actual = aggregates["valid_totals"]
        return {
            "dataset": dataset,
            "trip_source": str(trip_path),
            "zone_source": str(zones_path),
            "schema": profile,
            "zones": zone_profile,
            "quality": quality,
            "aggregates": aggregates,
            "benchmark": _compare_benchmark(actual, expected_totals),
            "thresholds": {
                "max_reasonable_duration_seconds": MAX_REASONABLE_DURATION_SECONDS,
                "max_reasonable_distance_miles": MAX_REASONABLE_DISTANCE_MILES,
                "max_reasonable_fare": MAX_REASONABLE_FARE,
            },
        }
    finally:
        con.close()


def analyze_month(
    datasets: Sequence[DatasetInput],
    zones_path: str | Path,
    *,
    top_n: int = 20,
    row_limit: int | None = None,
    benchmarks: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Analyze Yellow/HVFHV inputs and report shared canonical coverage."""
    reports = [
        analyze_dataset(
            item.name,
            item.trip_path,
            zones_path,
            top_n=top_n,
            row_limit=row_limit,
            expected_totals=(benchmarks or {}).get(item.name),
        )
        for item in datasets
    ]
    canonical_sets = [
        set(report["schema"]["canonical_columns"])
        - set(report["schema"]["missing_required_columns"])
        for report in reports
    ]
    common = sorted(set.intersection(*canonical_sets)) if canonical_sets else []
    return {
        "source": "NYC Taxi & Limousine Commission Trip Record Data",
        "prototype_scope": "monthly Parquet profiling and zone-level mobility analytics",
        "datasets": reports,
        "schema_consistency": {
            "datasets": [item.name for item in datasets],
            "common_canonical_columns": common,
            "all_have_required_columns": all(
                not report["schema"]["missing_required_columns"] for report in reports
            ),
        },
    }


def load_benchmarks(path: str | Path | None) -> dict[str, Mapping[str, Any]]:
    """Load optional benchmark totals from a JSON object keyed by dataset."""
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TLCAnalysisError("benchmark JSON must be an object keyed by dataset")
    return payload
