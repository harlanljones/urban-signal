"""Unit tests for the Overture GeoParquet client (US-443)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from src.spatial.overture_client import (
    BBox,
    OvertureClient,
    buildings_parquet_glob,
    places_parquet_glob,
)


def _write_buildings_fixture(path: Path) -> None:
    con = duckdb.connect()
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    con.execute(
        """
        CREATE TABLE bldg AS SELECT * FROM (VALUES
            (
                'overture:bldg:1',
                {'primary': 'Ferry Building'},
                'commercial',
                'office',
                24.0,
                4,
                ST_GeomFromText(
                    'POLYGON((-122.3937 37.7955, -122.3931 37.7955, '
                    '-122.3931 37.7959, -122.3937 37.7959, -122.3937 37.7955))'
                ),
                {'xmin': -122.3937, 'ymin': 37.7955, 'xmax': -122.3931, 'ymax': 37.7959}
            ),
            (
                'overture:bldg:2',
                {'primary': NULL},
                'residential',
                'single_family_residence',
                NULL,
                NULL,
                ST_GeomFromText(
                    'POLYGON((-123.9 39.9, -123.899 39.9, -123.899 39.901, '
                    '-123.9 39.901, -123.9 39.9))'
                ),
                {'xmin': -123.9, 'ymin': 39.9, 'xmax': -123.899, 'ymax': 39.901}
            )
        ) AS t(id, names, subtype, class, height, num_floors, geometry, bbox)
        """
    )
    con.execute(f"COPY bldg TO '{path.as_posix()}' (FORMAT PARQUET)")
    con.close()


def _write_places_fixture(path: Path) -> None:
    con = duckdb.connect()
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    con.execute(
        """
        CREATE TABLE plc AS SELECT * FROM (VALUES
            (
                'overture:place:1',
                {'primary': 'Blue Bottle Coffee'},
                {'primary': 'coffee_shop'},
                0.92,
                ST_GeomFromText('POINT(-122.3934 37.7957)'),
                {'xmin': -122.3934, 'ymin': 37.7957, 'xmax': -122.3934, 'ymax': 37.7957}
            )
        ) AS t(id, names, categories, confidence, geometry, bbox)
        """
    )
    con.execute(f"COPY plc TO '{path.as_posix()}' (FORMAT PARQUET)")
    con.close()


BAY_AREA_TEST_BBOX = BBox(xmin=-123.64, ymin=36.89, xmax=-121.20, ymax=38.87)


def test_fetch_buildings_parses_geometry_and_filters_bbox(tmp_path: Path):
    fixture = tmp_path / "buildings.parquet"
    _write_buildings_fixture(fixture)

    client = OvertureClient()
    try:
        rows = client.fetch_buildings(bbox=BAY_AREA_TEST_BBOX, source_override=fixture.as_posix())
    finally:
        client.close()

    # Only the Ferry Building falls inside the Bay Area bbox; the second
    # building (Mendocino county) is outside and must be pruned.
    assert len(rows) == 1
    row = rows[0]
    assert row.id == "overture:bldg:1"
    assert row.name == "Ferry Building"
    assert row.subtype == "commercial"
    assert row.building_class == "office"
    assert row.height == pytest.approx(24.0)
    assert row.num_floors == 4
    assert row.geometry.geom_type == "Polygon"
    assert row.geometry.area > 0


def test_fetch_places_parses_geometry(tmp_path: Path):
    fixture = tmp_path / "places.parquet"
    _write_places_fixture(fixture)

    client = OvertureClient()
    try:
        rows = client.fetch_places(bbox=BAY_AREA_TEST_BBOX, source_override=fixture.as_posix())
    finally:
        client.close()

    assert len(rows) == 1
    row = rows[0]
    assert row.id == "overture:place:1"
    assert row.name == "Blue Bottle Coffee"
    assert row.category_primary == "coffee_shop"
    assert row.confidence == pytest.approx(0.92)
    assert row.geometry.geom_type == "Point"


def test_buildings_parquet_glob_shape():
    glob = buildings_parquet_glob(release="2026-08-19.0")
    assert glob == (
        "s3://overturemaps-us-west-2/release/2026-08-19.0/theme=buildings/type=building/*"
    )


def test_places_parquet_glob_shape():
    glob = places_parquet_glob(release="2026-08-19.0")
    assert glob == "s3://overturemaps-us-west-2/release/2026-08-19.0/theme=places/type=place/*"


def test_bbox_from_metro_bbox_matches_bay_area_boundary():
    from src.spatial.overture_client import BAY_AREA_BBOX

    assert BAY_AREA_BBOX.xmin == pytest.approx(-123.64)
    assert BAY_AREA_BBOX.xmax == pytest.approx(-121.20)
    assert BAY_AREA_BBOX.ymin == pytest.approx(36.89)
    assert BAY_AREA_BBOX.ymax == pytest.approx(38.87)
