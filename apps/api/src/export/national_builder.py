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

WAC and RAC are independent measures: a missing WAC file does not discard RAC
data for the same state, and vice versa (US-435 §17).

Output layout (per run)::

    <out>/national/res{res}/{res3_parent}.parquet   one chunk per res-3 parent
    <out>/national/res{res}/report.json              per-resolution report
    <out>/national/manifest.json                     aggregate artifact manifest
    <out>/national/current.json                      promotion pointer (see below)

Build identity: the manifest SHA-256 over every resolution's chunk bytes is the
artifact's immutable identity (``artifact_key =
national/<signal_source>/<year>/<sha256>``). ``promote_national`` validates a
finished build and only then writes ``current.json`` — a partial or empty build
can never replace a valid pointer. The monthly workflow uploads the build tree
under its artifact key (R2) and publishes ``current.json``; the nightly
snapshot consumes whichever build the pointer names.

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
DEFAULT_CACHE_DIR = Path("data") / "national" / "lodes"
DEFAULT_OUT_DIR = Path("dist")
SIGNAL_SOURCE = "census_lehd_lodes8"
DEFAULT_RESOLUTIONS = (4, 5, 6)
# Bump whenever the aggregation, ranking, chunking, or report contract changes;
# the aggregate manifest and ContextSourceSpec both carry it (US-435 §12).
BUILDER_REVISION = "1"

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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_to_cache(
    url: str, cache_dir: Path, sha_list_url: str | None = None
) -> Path:
    """Download ``url`` into ``cache_dir`` (skipped when cached) and verify integrity.

    When ``sha_list_url`` is provided, the remote per-state ``lodes_<st>.sha256sum``
    is consulted (and cached) and the local file's SHA-256 must match the listed digest.
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
            raise ValueError(
                f"SHA-256 mismatch for {target.name}: expected {expected}"
            )
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
        raise ValueError(
            f"{path.name}: missing columns {missing}; header={header[:8]}..."
        )
    return pl.read_csv(path, columns=columns, infer_schema_length=0)


def _aggregate_measure(
    measure: str,
    geocode_col: str,
    data_path: Path,
    xwalk: pl.DataFrame,
    resolution: int,
    cell_filter: set[str] | None,
) -> tuple[dict[str, int], dict[str, int], str | None]:
    """Aggregate one LODES measure (wac or rac) to hex cells.

    Returns (sums_by_cell, blocks_by_cell, error_message).
    ``error_message`` is None on success, or a string describing the failure.
    """
    try:
        data = _read_gzip_csv(data_path, [geocode_col, "C000"]).with_columns(
            pl.col("C000").cast(pl.Int64)
        )
    except Exception as exc:  # noqa: BLE001 — coverage gaps must not kill the run
        return {}, {}, f"{type(exc).__name__}: {exc}"

    joined = data.rename({geocode_col: "tabblk2020"}).join(
        xwalk, on="tabblk2020", how="inner"
    )

    sums: dict[str, int] = {}
    blocks: dict[str, int] = {}
    for lat, lng, count in zip(
        joined["blklatdd"].to_list(),
        joined["blklondd"].to_list(),
        joined["C000"].to_list(),
    ):
        cell = h3.latlng_to_cell(lat, lng, resolution)
        if cell_filter is not None and cell not in cell_filter:
            continue
        sums[cell] = sums.get(cell, 0) + count
        blocks[cell] = blocks.get(cell, 0) + 1
    return sums, blocks, None


def aggregate_state(
    state: str,
    year: int,
    resolution: int,
    cache_dir: Path,
    fetcher: Callable[[str, Path], Path] = download_to_cache,
    cell_filter: Iterable[str] | None = None,
    verify_checksums: bool = True,
) -> tuple[pl.DataFrame, dict]:
    """Aggregate one state's LODES WAC and RAC to national hex cells.

    Returns (frame, state_report) where ``frame`` has columns ``h3_index,
    jobs_c000, workers_c000, blocks_wac, blocks_rac`` and ``state_report``
    contains per-measure status. WAC and RAC are independent: a missing WAC
    file does not discard RAC data, and vice versa.
    """
    allowed = set(cell_filter) if cell_filter is not None else None
    xwalk_path = fetcher(state_xwalk_url(state), cache_dir)

    xwalk = _read_gzip_csv(xwalk_path, ["tabblk2020", "blklatdd", "blklondd"]).with_columns(
        pl.col("blklatdd").cast(pl.Float64), pl.col("blklondd").cast(pl.Float64)
    )

    wac_sha_url = state_sha_url(state) if verify_checksums else None
    rac_sha_url = state_sha_url(state) if verify_checksums else None

    wac_data = None
    wac_error = None
    try:
        wac_path = fetcher(state_file_url(state, "wac", year), cache_dir, wac_sha_url)
        wac_data = wac_path
    except Exception as exc:  # noqa: BLE001 — WAC/RAC are independent measures
        wac_error = f"{type(exc).__name__}: {exc}"

    rac_data = None
    rac_error = None
    try:
        rac_path = fetcher(state_file_url(state, "rac", year), cache_dir, rac_sha_url)
        rac_data = rac_path
    except Exception as exc:  # noqa: BLE001 — WAC/RAC are independent measures
        rac_error = f"{type(exc).__name__}: {exc}"

    wac_sums: dict[str, int] = {}
    wac_blocks: dict[str, int] = {}
    if wac_data is not None:
        wac_sums, wac_blocks, wac_err = _aggregate_measure(
            "wac", "w_geocode", wac_data, xwalk, resolution, allowed
        )
        if wac_err is not None:
            wac_error = wac_err

    rac_sums: dict[str, int] = {}
    rac_blocks: dict[str, int] = {}
    if rac_data is not None:
        rac_sums, rac_blocks, rac_err = _aggregate_measure(
            "rac", "h_geocode", rac_data, xwalk, resolution, allowed
        )
        if rac_err is not None:
            rac_error = rac_err

    all_cells = sorted(set(wac_sums) | set(rac_sums))
    frame = pl.DataFrame({"h3_index": all_cells})
    frame = frame.with_columns(
        pl.col("h3_index")
        .replace_strict(wac_sums, default=None, return_dtype=pl.Int64)
        .alias(JOBS_COL),
        pl.col("h3_index")
        .replace_strict(rac_sums, default=None, return_dtype=pl.Int64)
        .alias(WORKERS_COL),
        pl.col("h3_index")
        .replace_strict(wac_blocks, default=None, return_dtype=pl.Int64)
        .alias("blocks_wac"),
        pl.col("h3_index")
        .replace_strict(rac_blocks, default=None, return_dtype=pl.Int64)
        .alias("blocks_rac"),
    )

    state_report: dict = {
        "wac_status": "ok" if wac_error is None else "no_data",
        "rac_status": "ok" if rac_error is None else "no_data",
    }
    if wac_error is not None:
        state_report["wac_error"] = wac_error
    if rac_error is not None:
        state_report["rac_error"] = rac_error
    state_report["cells"] = len(frame)
    if wac_error is None:
        state_report["jobs_c000"] = int(frame[JOBS_COL].sum() or 0)
    if rac_error is None:
        state_report["workers_c000"] = int(frame[WORKERS_COL].sum() or 0)

    logger.info(
        "%s: WAC=%s RAC=%s -> %d cells",
        state,
        state_report["wac_status"],
        state_report["rac_status"],
        len(frame),
    )
    return frame.select("h3_index", JOBS_COL, WORKERS_COL, "blocks_wac", "blocks_rac"), state_report


def _sum_frames(frames: list[pl.DataFrame]) -> pl.DataFrame:
    combined = pl.concat(frames, how="vertical")

    def _null_aware_sum(col: str) -> pl.Expr:
        return (
            pl.when(pl.col(col).null_count() == pl.len())
            .then(None)
            .otherwise(pl.col(col).sum())
            .alias(col)
        )

    result = combined.group_by("h3_index").agg(
        _null_aware_sum(JOBS_COL),
        _null_aware_sum(WORKERS_COL),
        pl.col("blocks_wac").sum(),
        pl.col("blocks_rac").sum(),
    )
    return result.with_columns(pl.col("h3_index").cast(pl.String))


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


def _build_resolution(
    resolution: int,
    year: int,
    state_list: list[str],
    cache_dir: Path,
    fetcher: Callable[[str, Path], Path],
    verify_checksums: bool,
    out_dir: Path,
    cells_provider: Callable[[int], tuple[str, ...]],
) -> dict:
    """Build one resolution's Parquet chunks and per-resolution report.

    Returns the per-resolution report dict.
    """
    cells = cells_provider(resolution)
    allowed = set(cells)
    res3_parents: dict[str, str] = {cell: parent_at(cell, 3) for cell in cells}

    state_frames: list[pl.DataFrame] = []
    report_states: dict[str, dict] = {}
    for state in state_list:
        try:
            frame, state_report = aggregate_state(
                state, year, resolution, cache_dir, fetcher, allowed, verify_checksums
            )
        except Exception as exc:  # noqa: BLE001 — coverage gaps must not kill the run
            logger.warning(
                "State %s unavailable (%s: %s); hexes stay null",
                state, type(exc).__name__, exc,
            )
            report_states[state] = {
                "wac_status": "no_data",
                "rac_status": "no_data",
                "error": f"{type(exc).__name__}: {exc}",
                "cells": 0,
            }
            continue
        state_frames.append(frame)
        report_states[state] = state_report

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
        pl.DataFrame({"h3_index": list(cells)}, schema={"h3_index": pl.String})
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
    chunk_sha256: dict[str, str] = {}
    for parent, part in full.group_by("res3_parent"):
        parent_key = parent[0] if isinstance(parent, tuple) else parent
        chunk = part.drop("res3_parent")
        path = res_dir / f"{parent_key}.parquet"
        chunk.write_parquet(path)
        chunk_sizes[path.name] = path.stat().st_size
        chunk_sha256[path.name] = _sha256(path)

    states_with_wac = sum(
        1 for s in report_states.values() if s.get("wac_status") == "ok"
    )
    states_with_rac = sum(
        1 for s in report_states.values() if s.get("rac_status") == "ok"
    )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "signal_source": SIGNAL_SOURCE,
        "builder_revision": BUILDER_REVISION,
        "year": year,
        "resolution": resolution,
        "cells": len(cells),
        "states_requested": len(state_list),
        "states_with_wac": states_with_wac,
        "states_with_rac": states_with_rac,
        "hexes_with_jobs": int(full[JOBS_COL].is_not_null().sum()),
        "hexes_with_workers": int(full[WORKERS_COL].is_not_null().sum()),
        "total_jobs": int(full[JOBS_COL].sum() or 0),
        "total_workers": int(full[WORKERS_COL].sum() or 0),
        "chunks": chunk_sizes,
        "chunks_sha256": chunk_sha256,
        "states": report_states,
    }
    report_path = res_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.info(
        "Resolution %d complete: %d cells, %d with jobs, %d chunks",
        resolution,
        len(cells),
        report["hexes_with_jobs"],
        len(chunk_sizes),
    )
    return report


def promote_national(out_dir: Path = DEFAULT_OUT_DIR) -> dict:
    """Validate a finished build and promote it as the current artifact.

    Reads ``national/manifest.json`` plus each per-resolution ``report.json``,
    requires checksums verified and at least one data chunk with measured hexes
    per resolution, then writes ``national/current.json``. A partial or empty
    build raises instead of replacing a valid pointer.
    """
    out_dir = Path(out_dir)
    national_root = out_dir / "national"
    manifest_path = national_root / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"promote: no manifest at {manifest_path}; nothing to promote")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if not manifest.get("checksum_verified"):
        failures.append("checksums not verified")
    for res in manifest.get("resolutions", []):
        report_path = national_root / f"res{res}" / "report.json"
        if not report_path.exists():
            failures.append(f"res{res}: missing report")
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not report.get("chunks"):
            failures.append(f"res{res}: no data chunks")
        elif not (report.get("hexes_with_jobs") or report.get("hexes_with_workers")):
            failures.append(f"res{res}: no measured hexes")
    if failures:
        raise ValueError(f"promote: refusing to promote invalid build: {failures}")

    pointer = {
        "artifact_key": (
            f"national/{manifest['signal_source']}/{manifest['year']}/{manifest['sha256']}"
        ),
        "sha256": manifest["sha256"],
        "signal_source": manifest["signal_source"],
        "builder_revision": manifest["builder_revision"],
        "lodes_version": manifest["lodes_version"],
        "year": manifest["year"],
        "resolutions": manifest["resolutions"],
        "promoted_at": datetime.now(UTC).isoformat(),
    }
    (national_root / "current.json").write_text(
        json.dumps(pointer, indent=2), encoding="utf-8"
    )
    logger.info("Promoted national artifact %s", pointer["artifact_key"])
    return pointer


def build_national(
    out_dir: Path = DEFAULT_OUT_DIR,
    year: int = DEFAULT_YEAR,
    resolutions: tuple[int, ...] = DEFAULT_RESOLUTIONS,
    states: Iterable[str] | None = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    verify_checksums: bool = True,
    fetcher: Callable[[str, Path], Path] = download_to_cache,
    cells_provider: Callable[[int], tuple[str, ...]] = cells_at_resolution,
    promote: bool = True,
) -> dict:
    """Build national hex signal for all requested resolutions.

    Produces per-resolution Parquet chunks, per-resolution reports, and an
    aggregate artifact manifest. Unless ``promote`` is False, validates the
    finished build and writes the ``current.json`` promotion pointer.
    Returns the manifest dict.
    """
    out_dir = Path(out_dir)
    cache_dir = Path(cache_dir)
    state_list = sorted(set(states) if states is not None else LODES_STATES)
    unknown = [s for s in state_list if s not in LODES_STATES]
    if unknown:
        raise ValueError(f"Unknown LODES state codes: {unknown}")

    invalid = [r for r in resolutions if r not in NATIONAL_RESOLUTIONS]
    if invalid:
        raise ValueError(
            f"Invalid resolutions {invalid}; valid: {NATIONAL_RESOLUTIONS}"
        )

    per_resolution_reports: dict[int, dict] = {}
    for res in resolutions:
        logger.info("Building resolution %d...", res)
        report = _build_resolution(
            res, year, state_list, cache_dir, fetcher, verify_checksums, out_dir, cells_provider
        )
        per_resolution_reports[res] = report

    full_manifest = _build_manifest(
        year, state_list, resolutions, per_resolution_reports, out_dir
    )
    if promote:
        promote_national(out_dir)
    return full_manifest


def _build_manifest(
    year: int,
    state_list: list[str],
    resolutions: tuple[int, ...],
    per_resolution_reports: dict[int, dict],
    out_dir: Path,
) -> dict:
    """Build the aggregate artifact manifest from per-resolution reports."""
    manifest: dict = {
        "generated_at": datetime.now(UTC).isoformat(),
        "signal_source": SIGNAL_SOURCE,
        "builder_revision": BUILDER_REVISION,
        "year": year,
        "resolutions": list(resolutions),
        "states": state_list,
        "checksum_verified": True,
        "lodes_version": "v8",
        "artifacts": {},
    }

    full_payload = b""
    for res in resolutions:
        report = per_resolution_reports[res]
        artifact = {
            "cells": report["cells"],
            "chunks": len(report["chunks"]),
            "hexes_with_jobs": report["hexes_with_jobs"],
            "hexes_with_workers": report["hexes_with_workers"],
            "states_with_wac": report["states_with_wac"],
            "states_with_rac": report["states_with_rac"],
            "total_jobs": report["total_jobs"],
            "total_workers": report["total_workers"],
        }
        manifest["artifacts"][str(res)] = artifact
        res_dir = out_dir / "national" / f"res{res}"
        for chunk_path in sorted(res_dir.glob("*.parquet")):
            full_payload += chunk_path.read_bytes()

    manifest["sha256"] = _sha256_bytes(full_payload)

    manifest_path = out_dir / "national" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    logger.info(
        "Aggregate manifest written: %d resolutions, %d states, sha256=%s",
        len(resolutions),
        len(state_list),
        manifest["sha256"][:16],
    )
    return manifest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Build national hex signal Parquet chunks (LODES v1, multi-resolution)"
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument(
        "--resolutions",
        type=int,
        nargs="+",
        default=list(DEFAULT_RESOLUTIONS),
        choices=list(NATIONAL_RESOLUTIONS),
        help="Resolutions to build (default: 4 5 6)",
    )
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument(
        "--states", nargs="*", default=None, help="Subset of state codes (default: all 51)"
    )
    parser.add_argument(
        "--cache-dir", default=str(DEFAULT_CACHE_DIR), help="Download cache (gitignored)"
    )
    parser.add_argument(
        "--no-verify-checksums",
        action="store_true",
        help="Skip official SHA-256 checksum verification (not recommended)",
    )
    parser.add_argument(
        "--no-promote",
        action="store_true",
        help="Do not write the current.json promotion pointer (leave staging unpromoted)",
    )
    args = parser.parse_args()
    build_national(
        out_dir=Path(args.out),
        year=args.year,
        resolutions=tuple(args.resolutions),
        states=args.states,
        cache_dir=Path(args.cache_dir),
        verify_checksums=not args.no_verify_checksums,
        promote=not args.no_promote,
    )


if __name__ == "__main__":
    main()