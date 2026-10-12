"""Vendor the Census 2020 Urban Area boundaries as the Urban Anchor asset (HX-A1).

Source: ``cb_2020_us_ua20_500k`` (public domain). Output: GeoJSON FeatureCollection
at ``apps/api/src/spatial/assets/us_urban_areas_2020.geojson`` with properties
``anchor_id`` (UACE20), ``name``, ``land_km2``, ``population`` (null: the cartographic
boundary file carries no population; a later join may fill it).

Usage: ``python scripts/vendor_urban_anchors.py [--tolerance 0.004]``
"""

from __future__ import annotations

import argparse
import io
import json
import urllib.request
import zipfile
from pathlib import Path

import duckdb
from shapely import wkb
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

URL = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_ua20_500k.zip"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/api/src/spatial/assets/us_urban_areas_2020.geojson"
CACHE = Path("/tmp/urban-anchors-cache")


def _fetch() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    shp = CACHE / "cb_2020_us_ua20_500k.shp"
    if not shp.exists():
        with urllib.request.urlopen(URL, timeout=180) as resp:
            archive = zipfile.ZipFile(io.BytesIO(resp.read()))
        archive.extractall(CACHE)
    return shp


def _round(coords: object) -> object:
    if isinstance(coords, (list, tuple)) and coords and isinstance(coords[0], (int, float)):
        return [round(coords[0], 5), round(coords[1], 5)]
    return [_round(item) for item in coords]  # type: ignore[union-attr]


def _simplified(geom: BaseGeometry, tolerance: float) -> BaseGeometry:
    simple = geom.simplify(tolerance, preserve_topology=True)
    return geom if simple.is_empty else simple


def read_features(shp: Path) -> list[tuple[str, str, float, BaseGeometry]]:
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    rows = con.execute(
        "SELECT UACE20, NAME20, ALAND20, ST_AsWKB(geom) FROM ST_Read(?) ORDER BY UACE20", [str(shp)]
    ).fetchall()
    return [(str(a), str(n), float(land) / 1e6, wkb.loads(bytes(g))) for a, n, land, g in rows]


def build(tolerance: float) -> dict:
    features = []
    for anchor_id, name, land_km2, geom in read_features(_fetch()):
        simple = _simplified(geom, tolerance)
        if simple.geom_type == "Polygon":
            simple = type(geom)([simple]) if geom.geom_type == "MultiPolygon" else simple
        geometry = mapping(simple)
        if geometry["type"] == "Polygon":
            geometry = {"type": "MultiPolygon", "coordinates": [geometry["coordinates"]]}
        geometry["coordinates"] = _round(geometry["coordinates"])
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "anchor_id": anchor_id,
                    "name": name,
                    "land_km2": round(land_km2, 3),
                    "population": None,
                },
                "geometry": geometry,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tolerance", type=float, default=0.004)
    args = parser.parse_args()
    collection = build(args.tolerance)
    OUT.write_text(json.dumps(collection, separators=(",", ":")), encoding="utf-8")
    print(f"{len(collection['features'])} anchors, {OUT.stat().st_size} bytes, tolerance={args.tolerance}")


if __name__ == "__main__":
    main()
