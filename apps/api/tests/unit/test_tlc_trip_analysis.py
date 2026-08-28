"""Tests for the read-only NYC TLC trip-record prototype (US-362)."""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from src.features.tlc_trip_analysis import (
    DatasetInput,
    TLCAnalysisError,
    analyze_dataset,
    analyze_month,
    trip_url,
)


def _write_parquet(path: Path, columns: list[str], rows: list[tuple[object, ...]]) -> None:
    con = duckdb.connect()
    try:
        types = []
        for value in rows[0]:
            if isinstance(value, int):
                types.append("INTEGER")
            elif isinstance(value, float):
                types.append("DOUBLE")
            else:
                types.append("VARCHAR")
        definition = ", ".join(f'"{column}" {type_}' for column, type_ in zip(columns, types))
        con.execute(f'CREATE TABLE fixture ({definition})')
        placeholders = ", ".join("?" for _ in columns)
        con.executemany(f"INSERT INTO fixture VALUES ({placeholders})", rows)
        con.execute("COPY fixture TO ? (FORMAT PARQUET)", [str(path)])
    finally:
        con.close()


def _write_zones(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["LocationID", "Borough", "Zone", "service_zone"])
        writer.writerows(
            [
                (1, "Manhattan", "Zone One", "Yellow Zone"),
                (2, "Brooklyn", "Zone Two", "Boro Zone"),
                (3, "Queens", "Zone Three", "Boro Zone"),
            ]
        )


def test_trip_url_uses_official_cloudfront_naming() -> None:
    assert trip_url("yellow", 2025, 1) == (
        "https://d37ci6vzurychx.cloudfront.net/trip-data/"
        "yellow_tripdata_2025-01.parquet"
    )
    with pytest.raises(ValueError):
        trip_url("yellow", 2025, 13)


def test_yellow_quality_and_zone_od_aggregates(tmp_path: Path) -> None:
    trips = tmp_path / "yellow.parquet"
    zones = tmp_path / "zones.csv"
    _write_parquet(
        trips,
        [
            "tpep_pickup_datetime",
            "tpep_dropoff_datetime",
            "PULocationID",
            "DOLocationID",
            "trip_distance",
            "fare_amount",
            "total_amount",
            "passenger_count",
        ],
        [
            ("2025-01-01 08:00:00", "2025-01-01 08:20:00", 1, 2, 2.5, 10.0, 12.0, 1.0),
            ("2025-01-01 09:00:00", "2025-01-01 09:30:00", 1, 3, 3.0, 15.0, 18.0, 2.0),
            # Negative distance and a zone not present in the lookup: quality issue.
            ("2025-01-01 10:00:00", "2025-01-01 09:59:00", 99, 2, -1.0, 20.0, 22.0, 1.0),
            # Otherwise valid trip, but unknown pickup zone must not aggregate.
            ("2025-01-01 11:00:00", "2025-01-01 11:20:00", 99, 2, 2.0, 8.0, 10.0, 1.0),
        ],
    )
    _write_zones(zones)

    report = analyze_dataset("yellow", trips, zones, top_n=5)

    assert report["schema"]["status"] == "ok"
    assert report["quality"]["rows_total"] == 4
    assert report["quality"]["impossible_duration"] == 1
    assert report["quality"]["impossible_distance"] == 1
    assert report["quality"]["invalid_pickup_zone"] == 2
    assert report["aggregates"]["valid_totals"]["trips"] == 2
    assert report["aggregates"]["valid_totals"]["fare_amount"] == 25.0
    assert report["aggregates"]["top_pickup_zones"][0]["location_id"] == 1
    assert report["aggregates"]["top_od_pairs"][0]["dropoff_location_id"] in {2, 3}


def test_hvfhv_schema_drift_derives_duration_and_total(tmp_path: Path) -> None:
    trips = tmp_path / "hvfhv.parquet"
    zones = tmp_path / "zones.csv"
    _write_parquet(
        trips,
        [
            "pickup_datetime",
            "dropoff_datetime",
            "PULocationID",
            "DOLocationID",
            "trip_miles",
            "base_passenger_fare",
            "tolls",
            "bcf",
            "sales_tax",
            "congestion_surcharge",
            "airport_fee",
            "tips",
        ],
        [("2025-01-02 12:00:00", "2025-01-02 12:15:00", 2, 3, 4.0, 20.0, 2.0, 1.0, 2.0, 1.0, 0.0, 3.0)],
    )
    _write_zones(zones)

    report = analyze_dataset("hvfhv", trips, zones)

    assert report["schema"]["derived_total_amount"] is True
    assert report["aggregates"]["valid_totals"]["trips"] == 1
    assert report["aggregates"]["valid_totals"]["total_amount"] == 29.0
    assert report["aggregates"]["valid_totals"]["average_duration_seconds"] == 900.0


def test_month_report_exposes_common_schema_and_benchmark(tmp_path: Path) -> None:
    zones = tmp_path / "zones.csv"
    yellow = tmp_path / "yellow.parquet"
    hvfhv = tmp_path / "hvfhv.parquet"
    _write_zones(zones)
    _write_parquet(
        yellow,
        ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance", "fare_amount", "total_amount"],
        [("2025-01-01", "2025-01-01 00:10:00", 1, 2, 1.0, 5.0, 6.0)],
    )
    _write_parquet(
        hvfhv,
        ["pickup_datetime", "dropoff_datetime", "PULocationID", "DOLocationID", "trip_miles", "base_passenger_fare"],
        [("2025-01-01", "2025-01-01 00:10:00", 1, 2, 1.0, 5.0)],
    )

    report = analyze_month(
        [
            DatasetInput("yellow", str(yellow)),
            DatasetInput("hvfhv", str(hvfhv)),
        ],
        zones,
        benchmarks={"yellow": {"trips": 1}},
    )

    assert report["schema_consistency"]["all_have_required_columns"] is True
    assert "pickup_at" in report["schema_consistency"]["common_canonical_columns"]
    assert report["datasets"][0]["benchmark"]["status"] == "compared"


def test_missing_required_schema_fails_closed(tmp_path: Path) -> None:
    trips = tmp_path / "broken.parquet"
    zones = tmp_path / "zones.csv"
    _write_parquet(trips, ["PULocationID"], [(1,)])
    _write_zones(zones)

    with pytest.raises(TLCAnalysisError, match="missing required columns"):
        analyze_dataset("yellow", trips, zones)
