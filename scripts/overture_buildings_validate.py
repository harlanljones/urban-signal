#!/usr/bin/env python3
"""
Overture Buildings — base-layer validation runner (US-360).

See docs/research/overture-buildings-base-layer.md for usage and context.
This script mirrors data/eval intent, but lives under scripts/ to avoid .gitignore.
"""
from __future__ import annotations

# Delegates to the implementation embedded here (copied from data/eval/overture/buildings_validate.py).
# The code is self-contained so CI does not need extra package wiring.

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import duckdb  # type: ignore

logger = logging.getLogger("overture_buildings_validate")


@dataclass(frozen=True)
class GeometryRow:
    id: str
    wkb: bytes
    height: float | None = None
    levels: float | None = None


@dataclass
class Metrics:
    city: str
    source: str
    release: str | None
    bbox: tuple[float, float, float, float] | None
    total_features: int
    invalid_geometries: int
    duplicate_ids: int
    duplicate_centroids: int
    duplicate_bboxes: int
    match_rate_pct: float | None = None
    matched_pairs: int | None = None
    reference_features: int | None = None
    height_summary: dict[str, float | None] | None = None
    levels_summary: dict[str, float | None] | None = None
    notes: list[str] | None = None


def _install_duckdb_extensions(con: duckdb.DuckDBPyConnection) -> None:
    try:
        con.sql("INSTALL httpfs; LOAD httpfs;").execute()
        con.sql("INSTALL spatial; LOAD spatial;").execute()
        con.sql("SET s3_region='us-west-2';").execute()
        con.sql("SET s3_url_style='path';").execute()
        con.sql("SET s3_use_ssl=true;").execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("DuckDB extension init failed (%s). Remote pulls may not work.", exc)


def _to_dataframe(rows: list[GeometryRow]) -> "duckdb.DuckDBPyRelation":
    con = duckdb.connect()
    _install_duckdb_extensions(con)
    if not rows:
        return con.sql(
            "SELECT * FROM (SELECT ''::VARCHAR AS id, ''::BLOB AS wkb, NULL::DOUBLE AS height, NULL::DOUBLE AS levels) WHERE 1=0"
        )
    tuples = [(r.id, r.wkb, r.height, r.levels) for r in rows]
    con.register("tmp_values", tuples)
    return con.sql(
        "SELECT id, wkb, height, levels FROM tmp_values AS (id VARCHAR, wkb BLOB, height DOUBLE, levels DOUBLE)"
    )


def _load_local_geojson(path: Path) -> list[GeometryRow]:
    import json as pyjson
    from shapely.geometry import shape  # type: ignore

    data = pyjson.loads(path.read_text(encoding="utf-8"))
    feats = data["features"] if isinstance(data, dict) and "features" in data else []
    rows: list[GeometryRow] = []
    for f in feats:
        props = f.get("properties") or {}
        fid = str(
            props.get("id")
            or props.get("overture_id")
            or props.get("gers_id")
            or props.get("OBJECTID")
            or f.get("id")
            or f"{len(rows)}"
        )
        geom = shape(f.get("geometry"))
        height = props.get("height")
        levels = props.get("levels") or props.get("num_levels")
        try:
            height = float(height) if height is not None else None
        except Exception:
            height = None
        try:
            levels = float(levels) if levels is not None else None
        except Exception:
            levels = None
        rows.append(GeometryRow(id=fid, wkb=geom.wkb, height=height, levels=levels))
    return rows


def _load_local_parquet(path: Path, id_col: str = "id", wkb_col: str = "geometry") -> list[GeometryRow]:
    con = duckdb.connect()
    _install_duckdb_extensions(con)
    cols = [r[0] for r in con.sql(f"PRAGMA table_info(read_parquet('{path.as_posix()}'))").fetchall()]
    geom_expr = None
    if wkb_col in cols:
        try:
            test = con.sql(
                f"SELECT COUNT(*) FROM read_parquet('{path.as_posix()}') WHERE typeof({wkb_col})='BLOB'"
            ).fetchone()[0]
            if int(test) >= 0:
                geom_expr = f"CAST({wkb_col} AS BLOB)"
        except Exception:
            geom_expr = None
        if geom_expr is None:
            geom_expr = f"ST_AsWKB(ST_GeomFromText({wkb_col}))"
    else:
        for cand in ("wkb", "geom", "wkt"):
            if cand in cols:
                wkb_col = cand
                geom_expr = f"ST_AsWKB(ST_GeomFromText({wkb_col}))"
                break
    if geom_expr is None:
        raise ValueError(f"Could not locate a geometry column in {path}")
    query = f"""
        SELECT
          CAST({id_col} AS VARCHAR) AS id,
          {geom_expr} AS wkb,
          TRY_CAST(height AS DOUBLE) AS height,
          TRY_CAST(levels AS DOUBLE) AS levels
        FROM read_parquet('{path.as_posix()}')
    """
    recs = con.sql(query).fetchall()
    return [GeometryRow(id=r[0], wkb=r[1], height=r[2], levels=r[3]) for r in recs]


def _load_overture_remote(bbox: tuple[float, float, float, float], release: str) -> "duckdb.DuckDBPyRelation":
    west, south, east, north = bbox
    con = duckdb.connect()
    _install_duckdb_extensions(con)
    parquet_glob = f"s3://overturemaps-us-west-2/release/{release}/theme=buildings/type=building/*"
    query = f"""
        WITH src AS (
            SELECT
              CAST(id AS VARCHAR) AS id,
              geometry,
              TRY_CAST(height AS DOUBLE) AS height,
              TRY_CAST(levels AS DOUBLE) AS levels
            FROM read_parquet('{parquet_glob}')
        ),
        clipped AS (
            SELECT
              id,
              ST_AsWKB(ST_GeomFromWKB(geometry)) AS wkb,
              height,
              levels
            FROM src
            WHERE ST_Intersects(
              ST_GeomFromWKB(geometry),
              ST_MakeEnvelope({west}, {south}, {east}, {north})
            )
        )
        SELECT * FROM clipped
    """
    return con.sql(query)


def _summarize_series(con: duckdb.DuckDBPyConnection, rel_name: str, col: str) -> dict[str, float | None]:
    row = con.sql(
        f"""
        SELECT
          COUNT({col}) AS n,
          AVG({col}) AS mean,
          MIN({col}) AS min,
          MAX({col}) AS max,
          QUANTILE_CONT({col}, 0.5) AS p50
        FROM {rel_name}
        WHERE {col} IS NOT NULL
        """
    ).fetchone()
    if row is None:
        return {"n": 0, "mean": None, "min": None, "max": None, "p50": None}
    n, mean, minv, maxv, p50 = row
    return {
        "n": int(n or 0),
        "mean": float(mean) if mean is not None else None,
        "min": float(minv) if minv is not None else None,
        "max": float(maxv) if maxv is not None else None,
        "p50": float(p50) if p50 is not None else None,
    }


def compute_metrics(
    city: str,
    overture_rel: "duckdb.DuckDBPyRelation",
    *,
    bbox: tuple[float, float, float, float] | None,
    release: str | None,
    reference_rows: list[GeometryRow] | None = None,
    notes: list[str] | None = None,
) -> Metrics:
    con = overture_rel.connection
    overture_rel.create_view("overture_src")
    con.sql(
        """
        CREATE OR REPLACE VIEW overture AS
        SELECT
          id::VARCHAR AS id,
          ST_GeomFromWKB(wkb) AS geom,
          height::DOUBLE AS height,
          levels::DOUBLE AS levels
        FROM overture_src
        """
    ).execute()
    total = int(con.sql("SELECT COUNT(*) FROM overture").fetchone()[0])
    invalid = int(con.sql("SELECT COUNT(*) FROM overture WHERE NOT ST_IsValid(geom)").fetchone()[0])
    dup_ids = int(con.sql("SELECT COUNT(*) - COUNT(DISTINCT id) AS d FROM overture").fetchone()[0])
    dup_centroids = int(
        con.sql(
            """
            SELECT COALESCE(SUM(cnt - 1), 0) FROM (
              SELECT ROUND(ST_X(ST_Centroid(geom))::DOUBLE, 8) AS cx,
                     ROUND(ST_Y(ST_Centroid(geom))::DOUBLE, 8) AS cy,
                     COUNT(*) AS cnt
              FROM overture
              GROUP BY cx, cy
              HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
    )
    dup_bboxes = int(
        con.sql(
            """
            SELECT COALESCE(SUM(cnt - 1), 0) FROM (
              SELECT
                ROUND(ST_XMin(geom)::DOUBLE, 8) AS xmin,
                ROUND(ST_YMin(geom)::DOUBLE, 8) AS ymin,
                ROUND(ST_XMax(geom)::DOUBLE, 8) AS xmax,
                ROUND(ST_YMax(geom)::DOUBLE, 8) AS ymax,
                COUNT(*) AS cnt
              FROM overture
              GROUP BY xmin, ymin, xmax, ymax
              HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
    )
    height_summary = _summarize_series(con, "overture", "height")
    levels_summary = _summarize_series(con, "overture", "levels")

    match_rate_pct: float | None = None
    matched_pairs: int | None = None
    reference_features: int | None = None
    if reference_rows:
        ref_rel = _to_dataframe(reference_rows)
        ref_rel.create_view("reference_src")
        con.sql(
            """
            CREATE OR REPLACE VIEW reference AS
            SELECT
              id::VARCHAR AS id,
              ST_GeomFromWKB(wkb) AS geom
            FROM reference_src
            """
        ).execute()
        reference_features = int(con.sql("SELECT COUNT(*) FROM reference").fetchone()[0])
        con.sql(
            """
            CREATE OR REPLACE TEMP VIEW joined AS
            SELECT
              r.id AS ref_id,
              o.id AS overture_id,
              ST_Area(ST_Intersection(r.geom, o.geom)) AS inter,
              ST_Area(ST_Union(r.geom, o.geom)) AS uni
            FROM reference r
            JOIN overture o
              ON ST_Intersects(r.geom, o.geom)
            """
        ).execute()
        con.sql(
            "CREATE OR REPLACE TEMP VIEW joined_iou AS SELECT ref_id, overture_id, CASE WHEN uni = 0 THEN 0 ELSE inter / uni END AS iou FROM joined"
        ).execute()
        matched_pairs = int(con.sql("SELECT COUNT(*) FROM joined_iou WHERE iou >= 0.5").fetchone()[0])
        denom = reference_features or 0
        match_rate_pct = (
            float(
                con.sql(
                    f"""
                SELECT 100.0 * COUNT(DISTINCT ref_id) / NULLIF({denom}, 0)
                FROM joined_iou
                WHERE iou >= 0.5
                """
                ).fetchone()[0]
                or 0.0
            )
            if denom
            else None
        )

    return Metrics(
        city=city,
        source="remote" if release else "local",
        release=release,
        bbox=bbox,
        total_features=total,
        invalid_geometries=invalid,
        duplicate_ids=dup_ids,
        duplicate_centroids=dup_centroids,
        duplicate_bboxes=dup_bboxes,
        match_rate_pct=match_rate_pct,
        matched_pairs=matched_pairs,
        reference_features=reference_features,
        height_summary=height_summary,
        levels_summary=levels_summary,
        notes=notes or [],
    )


def _parse_bbox(bbox_str: str) -> tuple[float, float, float, float]:
    parts = [p.strip() for p in bbox_str.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be 'west,south,east,north'")
    return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))


def _preset_bbox(city: str) -> tuple[float, float, float, float] | None:
    presets = {
        "new_orleans": (-90.33, 29.78, -89.75, 30.13),
        "london": (-0.5103, 51.2868, 0.3340, 51.6919),
        "sample": (-73.99, 40.74, -73.98, 40.75),
    }
    return presets.get(city.lower())


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", default="new_orleans", help="City label for reporting")
    parser.add_argument("--bbox", default=None, help="west,south,east,north")
    parser.add_argument("--release", default=None, help="Overture release id (e.g. 2026-08-19.0)")
    parser.add_argument("--overture-local", default=None, help="Local Overture subset (GeoJSON/Parquet)")
    parser.add_argument(
        "--authoritative-local", default=None, help="Local authoritative footprints (GeoJSON/Parquet)"
    )
    parser.add_argument("--out", default=None, help="Path to write JSON metrics")
    args = parser.parse_args(argv)

    bbox = _parse_bbox(args.bbox) if args.bbox else _preset_bbox(args.city)
    if bbox is None:
        logger.error("No bbox provided and no preset for city=%s", args.city)
        return 2

    # Load Overture rows
    release: str | None = None
    if args.overture_local:
        overture_path = Path(args.overture_local)
        if not overture_path.exists():
            logger.error("Local overture path not found: %s", overture_path)
            return 2
        if overture_path.suffix.lower() == ".geojson":
            rows = _load_local_geojson(overture_path)
        else:
            rows = _load_local_parquet(overture_path)
        overture_rel = _to_dataframe(rows)
    else:
        if not args.release:
            logger.error("--release is required for remote S3 pulls; or pass --overture-local")
            return 2
        release = args.release
        try:
            overture_rel = _load_overture_remote(bbox, release)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Remote pull failed (%s). Try --overture-local instead.", exc)
            return 1

    reference_rows = None
    if args.authoritative_local:
        ref_path = Path(args.authoritative_local)
        if not ref_path.exists():
            logger.error("Authoritative path not found: %s", ref_path)
            return 2
        if ref_path.suffix.lower() == ".geojson":
            reference_rows = _load_local_geojson(ref_path)
        else:
            reference_rows = _load_local_parquet(ref_path)

    notes: list[str] = []
    if args.overture_local:
        notes.append("Used local Overture subset (no remote S3 access attempted).")
    if reference_rows is None and args.authoritative_local:
        notes.append("Authoritative dataset exists but could not be loaded.")
    if not args.overture_local and not args.release:
        notes.append("Remote S3 pull skipped (no release provided).")

    metrics = compute_metrics(
        city=args.city,
        overture_rel=overture_rel,
        bbox=bbox,
        release=release,
        reference_rows=reference_rows or [],
        notes=notes,
    )

    payload = asdict(metrics)
    text = json.dumps(payload, indent=2, default=str)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        logger.info("Wrote metrics to %s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

