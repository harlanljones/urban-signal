"""National signal builder: per-hex nationwide context signals for the national hex layer.

v1 signal — Census LEHD LODES version 8 (public domain, no auth; validated in
``docs/research/census-lodes-validation.md``): workplace jobs (WAC ``C000``) and
resident workers (RAC ``C000``) aggregated from census blocks to the national hex
pyramid at ``apps.api/src/spatial/national_grid.py``. Block coordinates come from
the LODES crosswalk internal points (``blklatdd``/``blklondd``) — no TIGER
geometry needed.

Honesty rule: hexes without data stay null (never zero-filled, never synthesized).
LODES covers the 50 states + DC; territory hexes (PR/VI/...) remain null, as do
states/years with published coverage gaps (e.g. WAC/OD for AK 2017+).

Output layout (per run)::

    <out>/national/res{res}/{res3_parent}.parquet   one chunk per res-3 parent
    <out>/national/build_report.json                run metadata + per-state counts

Parquet columns: ``h3_index``, ``res5_parent``, ``res4_parent``, ``jobs_c000``,
``workers_c000``, ``blocks_wac``, ``blocks_rac``, ``jobs_national_pct``,
``workers_national_pct``, ``year``, ``signal_source``. Chunks are partitioned by
the res-3 parent of every cell so a publish step can shard them under the KV
25 MiB value cap without re-reading the whole set.

Percentile ranks reuse the average-rank implementation from the snapshot builder
and are computed over non-null values only; null hexes carry null ranks. LODES
block counts are partly synthetic (CBDRB-FY21-249) — treat values as an index,
never an exact count.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path

import h3
import polars as pl

from src.export.snapshot_builder import _percentile_ranks
from src.spatial.national_grid import (
    NATIONAL_RESOLUTIONS,
    cells_at_resolution,
    parent_at,
)

logger = logging.getLogger(__name__)

LODES_BASE_URL = "https://lehd.ces.census.gov/data/lodes/LODES8"
DEFAULT_YEAR = 2023
DEFAULT_RESOLUTION = 6
DEFAULT_CACHE_DIR = Path("data") / "national" / "lodes"
DEFAULT_OUT_DIR = Path("dist")
SIGNAL_SOURCE = "census_lehd_lodes8"

# TODO(US-382 follow-ups) remaining national signals, each a self-contained
# aggregator beside aggregate_state, all independently nullable:
#   - building density: Microsoft GlobalMLBuildingFootprints (quadkey tiles,
#     CDLA-Permissive) or Overture Buildings (ODbL gate, see signal-overture log)
#   - OSM building/road density: Geofabrik state extracts
#   - VIIRS nighttime lights: needs a raster platform (repo has none; see
#     us123-nlcd log) — defer until raster/zonal capability exists
#   - ACS baseline: reuse src/spatial/acs_baseline.py (needs a Census API key)

# LODES ships the 50 states + DC (lowercase two-letter codes). Territories are
# absent in all years; their national hexes stay null.
LODES_STATES: frozenset[str] = frozenset(
    [
        "al",
        "ak",
        "az",
        "ar",
        "ca",
        "co",
        "ct",
        "de",
        "dc",
        "fl",
        "ga",
        "hi",
        "id",
        "il",
        "in",
        "ia",
        "ks",
        "ky",
        "la",
        "me",
        "md",
        "ma",
        "mi",
        "mn",
        "ms",
        "mo",
        "mt",
        "ne",
        "nv",
        "nh",
        "nj",
        "nm",
        "ny",
        "nc",
        "nd",
        "oh",
        "ok",
        "or",
        "pa",
        "ri",
        "sc",
        "sd",
        "tn",
        "tx",
        "ut",
        "vt",
        "va",
        "wa",
        "wv",
        "wi",
        "wy",
    ]
)

JOBS_COL = "jobs_c000"
WORKERS_COL = "workers_c000"
RANK_COLS = (f"{JOBS_COL}_national_pct", f"{WORKERS_COL}_national_pct")
PARQUET_COLUMNS = (
    "h3_index",
    "res5_parent",
    "res4_parent",
    JOBS_COL,
    WORKERS_COL,
    "blocks_wac",
    "blocks_rac",
    *RANK_COLS,
    "year",
    "signal_source",
)


def state_xwalk_url(state: str) -> str:
    return f"{LODES_BASE_URL}/{state}/{state}_xwalk.csv.gz"


def state_file_url(state: str, kind: str, year: int) -> str:
    """kind is 'wac' or 'rac'; file family is S000 (total) JT00 (all jobs)."""
    return f"{LODES_BASE_URL}/{state}/{kind}/{state}_{kind}_S000_JT00_{year}.csv.gz"


def state_sha_url(state: str) -> str:
    return f"{LODES_BASE_URL}/{state}/lodes_{state}.sha256sum"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_to_cache(url: str, cache_dir: Path, sha_list_url: str | None = None) -> Path:
    """Download ``url`` into ``cache_dir`` (skipped when cached) and verify integrity.

    The fetcher is plain httpx with no auth, mirroring the anonymous-curl access
    proven in the LODES validation doc. When ``sha_list_url`` is provided, the
    remote per-state ``lodes_<st>.sha256sum`` is consulted (and cached) and the
    local file's SHA-256 must match the listed digest.
    """
    import httpx

    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / url.rsplit("/", 1)[-1]
    if not target.exists():
        logger.info("Downloading %s", url)
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            target.write_bytes(response.content)
    if sha_list_url is not None:
        sha_path = download_to_cache(sha_list_url, cache_dir)
        expected = _expected_sha(sha_path, target.name)
        if expected is not None and _sha256(target) != expected:
            raise ValueError(f"SHA-256 mismatch for {target.name}: expected {expected}")
    return target


def _expected_sha(sha_list_path: Path, filename: str) -> str | None:
    for line in sha_list_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].strip("*") == filename:
            return parts[0].lower()
    return None


def _read_gzip_csv(path: Path, columns: list[str]) -> pl.DataFrame:
    """Read selected columns from a gzipped LODES CSV (utf-8, comma-separated)."""
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
    missing = [col for col in columns if col not in header]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}; header={header[:8]}...")
    return pl.read_csv(path, columns=columns, infer_schema_length=0)


def aggregate_state(
    state: str,
    year: int,
    resolution: int,
    cache_dir: Path,
    fetcher: Callable[[str, Path], Path] = download_to_cache,
    cell_filter: Iterable[str] | None = None,
) -> pl.DataFrame:
    """Aggregate one state's LODES WAC/RAC to national hex cells.

    Returns columns ``h3_index, jobs_c000, workers_c000, blocks_wac, blocks_rac``.
    ``fetcher`` is injectable for tests. ``cell_filter`` restricts output to the
    given cells (the national pyramid); blocks resolving outside it are dropped.
    """
    xwalk_path = fetcher(state_xwalk_url(state), cache_dir)
    wac_path = fetcher(state_file_url(state, "wac", year), cache_dir)
    rac_path = fetcher(state_file_url(state, "rac", year), cache_dir)
    allowed = set(cell_filter) if cell_filter is not None else None

    xwalk = _read_gzip_csv(xwalk_path, ["tabblk2020", "blklatdd", "blklondd"]).with_columns(
        pl.col("blklatdd").cast(pl.Float64), pl.col("blklondd").cast(pl.Float64)
    )
    wac = _read_gzip_csv(wac_path, ["w_geocode", "C000"]).with_columns(
        pl.col("C000").cast(pl.Int64)
    )
    rac = _read_gzip_csv(rac_path, ["h_geocode", "C000"]).with_columns(
        pl.col("C000").cast(pl.Int64)
    )

    def _cells_sum(
        latlng: list[tuple[float, float]], counts: list[int]
    ) -> tuple[dict[str, int], dict[str, int]]:
        sums: dict[str, int] = {}
        blocks: dict[str, int] = {}
        for (lat, lng), count in zip(latlng, counts):
            cell = h3.latlng_to_cell(lat, lng, resolution)
            if allowed is not None and cell not in allowed:
                continue
            sums[cell] = sums.get(cell, 0) + count
            blocks[cell] = blocks.get(cell, 0) + 1
        return sums, blocks

    wac_joined = wac.rename({"w_geocode": "tabblk2020"}).join(xwalk, on="tabblk2020", how="inner")
    rac_joined = rac.rename({"h_geocode": "tabblk2020"}).join(xwalk, on="tabblk2020", how="inner")

    jobs_by_cell, job_blocks = _cells_sum(
        list(zip(wac_joined["blklatdd"].to_list(), wac_joined["blklondd"].to_list())),
        wac_joined["C000"].to_list(),
    )
    workers_by_cell, worker_blocks = _cells_sum(
        list(zip(rac_joined["blklatdd"].to_list(), rac_joined["blklondd"].to_list())),
        rac_joined["C000"].to_list(),
    )

    frame = pl.DataFrame({"h3_index": sorted(set(jobs_by_cell) | set(workers_by_cell))})
    frame = frame.with_columns(
        pl.col("h3_index")
        .replace_strict(jobs_by_cell, default=None, return_dtype=pl.Int64)
        .alias(JOBS_COL),
        pl.col("h3_index")
        .replace_strict(workers_by_cell, default=None, return_dtype=pl.Int64)
        .alias(WORKERS_COL),
    ).with_columns(
        pl.col("h3_index")
        .replace_strict(job_blocks, default=None, return_dtype=pl.Int64)
        .alias("blocks_wac"),
        pl.col("h3_index")
        .replace_strict(worker_blocks, default=None, return_dtype=pl.Int64)
        .alias("blocks_rac"),
    )
    logger.info(
        "%s: %d WAC blocks, %d RAC blocks -> %d cells",
        state,
        sum(job_blocks.values()),
        sum(worker_blocks.values()),
        len(frame),
    )
    return frame.select("h3_index", JOBS_COL, WORKERS_COL, "blocks_wac", "blocks_rac")


def _sum_frames(frames: list[pl.DataFrame]) -> pl.DataFrame:
    combined = pl.concat(frames, how="vertical")

    def _null_aware_sum(col: str) -> pl.Expr:
        # A group whose values are all null must stay null: polars' plain sum()
        # maps an all-null group to 0, which would fabricate data.
        return (
            pl.when(pl.col(col).null_count() == pl.len())
            .then(None)
            .otherwise(pl.col(col).sum())
            .alias(col)
        )

    return combined.group_by("h3_index").agg(
        _null_aware_sum(JOBS_COL),
        _null_aware_sum(WORKERS_COL),
        pl.col("blocks_wac").sum(),
        pl.col("blocks_rac").sum(),
    )


def _attach_ranks(frame: pl.DataFrame) -> pl.DataFrame:
    """Average-rank percentiles over non-null values; nulls keep null ranks."""
    jobs = frame[JOBS_COL].to_list()
    workers = frame[WORKERS_COL].to_list()
    jobs_known = [(i, v) for i, v in enumerate(jobs) if v is not None]
    workers_known = [(i, v) for i, v in enumerate(workers) if v is not None]
    jobs_pct = _percentile_ranks([v for _, v in jobs_known])
    workers_pct = _percentile_ranks([v for _, v in workers_known])
    jobs_rank = [None] * len(jobs)
    workers_rank = [None] * len(workers)
    for (i, _), pct in zip(jobs_known, jobs_pct):
        jobs_rank[i] = pct
    for (i, _), pct in zip(workers_known, workers_pct):
        workers_rank[i] = pct
    return frame.with_columns(
        pl.Series(RANK_COLS[0], jobs_rank, dtype=pl.Float64),
        pl.Series(RANK_COLS[1], workers_rank, dtype=pl.Float64),
    )


def build_national(
    out_dir: Path = DEFAULT_OUT_DIR,
    resolution: int = DEFAULT_RESOLUTION,
    year: int = DEFAULT_YEAR,
    states: Iterable[str] | None = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    fetcher: Callable[[str, Path], Path] = download_to_cache,
    cells_provider: Callable[[int], tuple[str, ...]] = cells_at_resolution,
) -> dict:
    """Build national hex signal Parquet chunks + build report; returns the report."""
    out_dir = Path(out_dir)
    cache_dir = Path(cache_dir)
    state_list = sorted(set(states) if states is not None else LODES_STATES)
    unknown = [s for s in state_list if s not in LODES_STATES]
    if unknown:
        raise ValueError(f"Unknown LODES state codes: {unknown}")

    cells = cells_provider(resolution)
    allowed = set(cells)
    res3_parents: dict[str, str] = {cell: parent_at(cell, 3) for cell in cells}

    state_frames: list[pl.DataFrame] = []
    report_states: dict[str, dict] = {}
    for state in state_list:
        try:
            frame = aggregate_state(state, year, resolution, cache_dir, fetcher, allowed)
        except Exception as exc:  # noqa: BLE001 — coverage gaps must not kill the run
            logger.warning(
                "State %s unavailable (%s: %s); hexes stay null", state, type(exc).__name__, exc
            )
            report_states[state] = {"status": "no_data", "error": f"{type(exc).__name__}: {exc}"}
            continue
        state_frames.append(frame)
        report_states[state] = {
            "status": "ok",
            "cells": len(frame),
            "jobs": int(frame[JOBS_COL].sum() or 0),
            "workers": int(frame[WORKERS_COL].sum() or 0),
        }

    if state_frames:
        combined = _sum_frames(state_frames)
    else:
        combined = pl.DataFrame(
            schema={
                "h3_index": pl.String,
                JOBS_COL: pl.Int64,
                WORKERS_COL: pl.Int64,
                "blocks_wac": pl.Int64,
                "blocks_rac": pl.Int64,
            }
        )

    full = (
        pl.DataFrame({"h3_index": list(cells)})
        .join(combined, on="h3_index", how="left")
        .with_columns(
            pl.col("h3_index")
            .replace_strict(res3_parents, return_dtype=pl.String)
            .alias("res3_parent"),
            pl.col("h3_index")
            .map_elements(lambda c: parent_at(c, 5), return_dtype=pl.String)
            .alias("res5_parent"),
            pl.col("h3_index")
            .map_elements(lambda c: parent_at(c, 4), return_dtype=pl.String)
            .alias("res4_parent"),
        )
    )
    full = _attach_ranks(full)
    full = full.with_columns(
        pl.lit(year, dtype=pl.Int64).alias("year"),
        pl.lit(SIGNAL_SOURCE).alias("signal_source"),
    )
    full = full.select("res3_parent", *PARQUET_COLUMNS)

    res_dir = out_dir / "national" / f"res{resolution}"
    res_dir.mkdir(parents=True, exist_ok=True)
    chunk_sizes: dict[str, int] = {}
    for parent, part in full.group_by("res3_parent"):
        parent_key = parent[0] if isinstance(parent, tuple) else parent
        chunk = part.drop("res3_parent")
        path = res_dir / f"{parent_key}.parquet"
        chunk.write_parquet(path)
        chunk_sizes[path.name] = path.stat().st_size

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "signal_source": SIGNAL_SOURCE,
        "year": year,
        "resolution": resolution,
        "cells": len(cells),
        "states_requested": len(state_list),
        "states_with_data": sum(1 for s in report_states.values() if s.get("status") == "ok"),
        "hexes_with_jobs": int(full[JOBS_COL].is_not_null().sum()),
        "hexes_with_workers": int(full[WORKERS_COL].is_not_null().sum()),
        "total_jobs": int(full[JOBS_COL].sum() or 0),
        "total_workers": int(full[WORKERS_COL].sum() or 0),
        "chunks": chunk_sizes,
        "states": report_states,
    }
    report_path = out_dir / "national" / "build_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.info(
        "National build complete: %d cells, %d with jobs, %d chunks -> %s",
        len(cells),
        report["hexes_with_jobs"],
        len(chunk_sizes),
        res_dir,
    )
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Build national hex signal Parquet chunks (LODES v1)"
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument(
        "--res", type=int, default=DEFAULT_RESOLUTION, choices=list(NATIONAL_RESOLUTIONS)
    )
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument(
        "--states", nargs="*", default=None, help="Subset of state codes (default: all 51)"
    )
    parser.add_argument(
        "--cache-dir", default=str(DEFAULT_CACHE_DIR), help="Download cache (gitignored)"
    )
    args = parser.parse_args()
    build_national(
        out_dir=Path(args.out),
        resolution=args.res,
        year=args.year,
        states=args.states,
        cache_dir=Path(args.cache_dir),
    )


if __name__ == "__main__":
    main()
