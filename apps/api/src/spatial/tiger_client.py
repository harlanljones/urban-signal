"""TIGER/Line Census block-group geometries client and parser (US-438).

Downloads, caches, and parses Census TIGER/Line block group geometries for
California and the 9 Bay Area counties.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path

import duckdb
import httpx
from shapely import wkt
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

from src.spatial.acs_variables import BAY_AREA_COUNTIES

logger = logging.getLogger(__name__)

TIGER_BASE_URL = "https://www2.census.gov/geo/tiger"
DEFAULT_CACHE_DIR = Path("data") / "tiger" / "bg"


def tiger_block_group_url(year: int = 2023, state_fips: str = "06") -> str:
    """Return the official Census TIGER/Line download URL for a state's block groups."""
    return f"{TIGER_BASE_URL}/TIGER{year}/BG/tl_{year}_{state_fips}_bg.zip"


def download_tiger_block_groups(
    year: int = 2023,
    state_fips: str = "06",
    cache_dir: Path | None = None,
    timeout_s: float = 120.0,
) -> Path:
    """Download state TIGER/Line block groups zip archive into cache_dir (skipped if cached)."""
    target_dir = cache_dir or DEFAULT_CACHE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"tl_{year}_{state_fips}_bg.zip"
    target_file = target_dir / filename

    if not target_file.exists():
        url = tiger_block_group_url(year=year, state_fips=state_fips)
        logger.info("Downloading TIGER/Line block groups from %s", url)
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            target_file.write_bytes(resp.content)
    return target_file


def parse_tiger_block_groups_from_shp_or_zip(
    path: Path,
    county_fips: Iterable[str] | None = None,
) -> dict[str, BaseGeometry]:
    """Parse block group geometries from a TIGER/Line .zip or .shp using DuckDB spatial.

    Returns mapping: 12-digit GEOID -> shapely geometry (Polygon/MultiPolygon) in EPSG:4326.
    """
    con = duckdb.connect()
    try:
        con.sql("INSTALL spatial; LOAD spatial;").execute()
    except (RuntimeError, OSError) as exc:
        logger.warning("DuckDB spatial extension load notice: %s", exc)

    # Filter by county FIPS if supplied
    where_clauses = []
    if county_fips:
        fips_list = ", ".join(f"'{c.zfill(3)}'" for c in county_fips)
        where_clauses.append(f"COUNTYFP IN ({fips_list})")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    path_posix = path.as_posix()

    query = f"""
        SELECT
            GEOID::VARCHAR AS geoid,
            ST_AsText(geom) AS geom_wkt
        FROM ST_Read('{path_posix}')
        {where_sql}
    """
    rows = con.sql(query).fetchall()
    out: dict[str, BaseGeometry] = {}
    for geoid, geom_wkt_str in rows:
        if not geoid or not geom_wkt_str:
            continue
        try:
            geom = wkt.loads(geom_wkt_str)
            if not geom.is_valid:
                geom = make_valid(geom)
            out[str(geoid)] = geom
        except (ValueError, AttributeError) as exc:
            logger.warning("Failed to parse geometry for GEOID %s: %s", geoid, exc)
    return out


def parse_tiger_block_groups_from_geojson(
    data_or_path: Path | str | dict,
    county_fips: Iterable[str] | None = None,
) -> dict[str, BaseGeometry]:
    """Parse block group geometries from a GeoJSON FeatureCollection or file.

    Returns mapping: 12-digit GEOID -> shapely geometry (Polygon/MultiPolygon).
    """
    if isinstance(data_or_path, (Path, str)):
        raw_text = Path(data_or_path).read_text(encoding="utf-8")
        data = json.loads(raw_text)
    else:
        data = data_or_path

    features = data.get("features", []) if isinstance(data, dict) else []
    county_filter: set[str] | None = {c.zfill(3) for c in county_fips} if county_fips else None

    out: dict[str, BaseGeometry] = {}
    for feat in features:
        props = feat.get("properties") or {}
        geoid = str(
            props.get("GEOID")
            or props.get("geoid")
            or props.get("GEOID20")
            or props.get("FIPS")
            or ""
        )
        county = str(props.get("COUNTYFP") or props.get("county") or (geoid[2:5] if len(geoid) >= 5 else ""))
        if county_filter and county not in county_filter:
            continue
        if not geoid and "id" in feat:
            geoid = str(feat["id"])
        if not geoid:
            continue
        raw_geom = feat.get("geometry")
        if not raw_geom:
            continue
        geom = shape(raw_geom)
        if not geom.is_valid:
            geom = make_valid(geom)
        out[geoid] = geom
    return out


def load_bay_area_block_groups(
    source: Path | str | dict | None = None,
    year: int = 2023,
    state_fips: str = "06",
    cache_dir: Path | None = None,
) -> dict[str, BaseGeometry]:
    """Load and parse block groups for the 9 Bay Area counties.

    If ``source`` is provided (Path to .zip, .shp, .geojson, or dict), parses it directly.
    Otherwise, downloads the official Census TIGER/Line zip archive for the year/state.
    """
    county_fips = list(BAY_AREA_COUNTIES.keys())
    if source is not None:
        if isinstance(source, (Path, str)):
            p = Path(source)
            if p.suffix.lower() in (".zip", ".shp"):
                return parse_tiger_block_groups_from_shp_or_zip(p, county_fips=county_fips)
            return parse_tiger_block_groups_from_geojson(p, county_fips=county_fips)
        return parse_tiger_block_groups_from_geojson(source, county_fips=county_fips)

    # Download from Census TIGER/Line
    zip_path = download_tiger_block_groups(year=year, state_fips=state_fips, cache_dir=cache_dir)
    return parse_tiger_block_groups_from_shp_or_zip(zip_path, county_fips=county_fips)
