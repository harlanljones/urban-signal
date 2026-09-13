"""Bay Area LEHD LODES employment density & commute flow join (US-439).

Ingests Census LEHD LODES v8 Workplace Area Characteristics (WAC) and
Residence Area Characteristics (RAC) for California, filters to the 9 Bay
Area FIPS counties (``src.spatial.acs_variables.BAY_AREA_COUNTIES``), and
joins census-block-level job counts and resident-worker counts to H3 res-9
hexes via the LODES crosswalk's block internal points (``blklatdd``/
``blklondd``) — the same point-in-polygon-free join used by
``src.export.national_builder`` and ``src.spatial.acs_join``.

Per-hex derived features:

- ``total_jobs`` — WAC ``C000`` summed per hex.
- ``total_residents`` — RAC ``C000`` summed per hex.
- ``jobs_to_residents_ratio`` — ``total_jobs / total_residents``; ``None``
  when a hex has zero residents (daytime-population proxy: >1 = job center,
  <1 = bedroom community).
- ``industry_mix`` — CNS01-CNS20 (NAICS 2-digit super-sector) WAC sums as
  fractions of ``total_jobs``; ``None`` per code when ``total_jobs`` is zero.
- ``wage_tier_mix`` — CE01 (<$1250/mo), CE02 ($1250-$3333), CE03 (>$3333) WAC
  sums as fractions of ``total_jobs``; ``None`` when ``total_jobs`` is zero.

Blocks with zero jobs or zero residents are not an error: LODES ships C000=0
rows and blocks that appear in only one of WAC/RAC. Hexes derived from such
blocks keep a zero count on the missing side rather than being dropped, and
ratios/fractions null out rather than raising.

Optional OD (origin-destination) commute-flow aggregation is scoped to flows
where both the home and work block resolve inside the 9-county extent (both
endpoints join against the same Bay-Area-filtered crosswalk); commutes that
cross the county-set boundary are not captured. This is an intentional
tradeoff for a first cut — see PR notes.

Output is tagged with the LODES vintage year and version (``lodes_version``
"v8") so consumers can distinguish releases.
"""

from __future__ import annotations

import gzip
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import h3
import polars as pl

from src.export.national_builder import (
    download_to_cache,
    state_file_url,
    state_sha_url,
    state_xwalk_url,
)
from src.spatial.acs_variables import BAY_AREA_COUNTIES

logger = logging.getLogger(__name__)

STATE_FIPS = "06"
STATE_CODE = "ca"
DEFAULT_YEAR = 2023
DEFAULT_H3_RESOLUTION = 9
DEFAULT_CACHE_DIR = Path("data") / "lodes" / "bay_area"
LODES_VERSION = "v8"

# NAICS 2-digit super-sector industry codes (LODES WAC/RAC schema).
CNS_CODES: tuple[str, ...] = tuple(f"CNS{i:02d}" for i in range(1, 21))
# Monthly earnings tiers: CE01 <$1250, CE02 $1250-$3333, CE03 >$3333.
CE_CODES: tuple[str, ...] = ("CE01", "CE02", "CE03")

JOBS_COL = "total_jobs"
RESIDENTS_COL = "total_residents"

FetcherFn = Callable[..., Path]


def _bay_area_county_codes() -> list[str]:
    return list(BAY_AREA_COUNTIES.keys())


def _is_bay_area_block(block_fips15: str) -> bool:
    """True if a 15-digit 2020 census block FIPS falls in a Bay Area county."""
    if len(block_fips15) != 15:
        return False
    return block_fips15[:2] == STATE_FIPS and block_fips15[2:5] in BAY_AREA_COUNTIES


def _read_gzip_csv(path: Path, columns: list[str]) -> pl.DataFrame:
    """Read selected columns from a gzipped (or plain) LODES CSV."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:  # type: ignore[operator]
        header = handle.readline().strip().split(",")
    missing = [col for col in columns if col not in header]
    if missing:
        raise ValueError(
            f"{path.name}: missing columns {missing}; header={header[:8]}..."
        )
    return pl.read_csv(path, columns=columns, infer_schema_length=0)


def load_bay_area_xwalk(
    cache_dir: Path = DEFAULT_CACHE_DIR,
    resolution: int = DEFAULT_H3_RESOLUTION,
    fetcher: FetcherFn = download_to_cache,
    verify_checksums: bool = True,
) -> pl.DataFrame:
    """Load the CA LODES crosswalk, filtered to the 9 Bay Area counties, with H3 cells.

    Returns a frame with columns ``tabblk2020``, ``h3_index`` — one row per
    Bay Area census block, H3-resolved from the crosswalk's block internal
    point (``blklatdd``/``blklondd``), not a block-group centroid.
    """
    sha_url = state_sha_url(STATE_CODE) if verify_checksums else None
    path = fetcher(state_xwalk_url(STATE_CODE), cache_dir, sha_url)
    xwalk = _read_gzip_csv(path, ["tabblk2020", "blklatdd", "blklondd"]).with_columns(
        pl.col("blklatdd").cast(pl.Float64), pl.col("blklondd").cast(pl.Float64)
    )
    county_codes = _bay_area_county_codes()
    xwalk = xwalk.filter(
        (pl.col("tabblk2020").str.slice(0, 2) == STATE_FIPS)
        & (pl.col("tabblk2020").str.slice(2, 3).is_in(county_codes))
    )
    cells = [
        h3.latlng_to_cell(lat, lng, resolution)
        for lat, lng in zip(xwalk["blklatdd"].to_list(), xwalk["blklondd"].to_list())
    ]
    return xwalk.with_columns(pl.Series("h3_index", cells)).select(
        "tabblk2020", "h3_index"
    )


def _load_measure(
    kind: str,
    geocode_col: str,
    sum_cols: tuple[str, ...],
    year: int,
    xwalk: pl.DataFrame,
    cache_dir: Path,
    fetcher: FetcherFn,
    verify_checksums: bool,
) -> tuple[pl.DataFrame | None, str | None]:
    """Load and hex-aggregate one LODES measure (wac or rac).

    Returns ``(frame, error)``. On failure (e.g. missing file/coverage gap)
    ``frame`` is ``None`` and ``error`` describes it — never raises, so a
    missing WAC does not discard RAC data and vice versa.
    """
    try:
        sha_url = state_sha_url(STATE_CODE) if verify_checksums else None
        path = fetcher(state_file_url(STATE_CODE, kind, year), cache_dir, sha_url)
        data = _read_gzip_csv(path, [geocode_col, *sum_cols])
        for col in sum_cols:
            data = data.with_columns(pl.col(col).cast(pl.Int64))
    except Exception as exc:  # noqa: BLE001 — coverage gaps must not kill the run
        return None, f"{type(exc).__name__}: {exc}"

    joined = data.rename({geocode_col: "tabblk2020"}).join(
        xwalk, on="tabblk2020", how="inner"
    )
    agg = joined.group_by("h3_index").agg(
        *[pl.col(c).sum().alias(c) for c in sum_cols],
        pl.len().alias(f"blocks_{kind}"),
    )
    return agg, None


@dataclass(frozen=True)
class H3EmploymentRecord:
    """One H3 res-9 hex's LODES-derived employment/residence density record."""

    h3_index: str
    year: int
    total_jobs: int
    total_residents: int
    jobs_to_residents_ratio: float | None
    industry_mix: dict[str, float | None]  # CNS01..CNS20 -> fraction of total_jobs
    wage_tier_mix: dict[str, float | None]  # CE01..CE03 -> fraction of total_jobs
    blocks_wac: int
    blocks_rac: int
    lodes_version: str = LODES_VERSION


@dataclass(frozen=True)
class H3CommuteFlow:
    """One home-hex -> work-hex commute flow aggregated from LODES OD (US-439, optional)."""

    home_h3: str
    work_h3: str
    year: int
    flow_count: int
    lodes_version: str = LODES_VERSION


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def build_employment_records(
    wac: pl.DataFrame | None,
    rac: pl.DataFrame | None,
    year: int,
) -> list[H3EmploymentRecord]:
    """Combine hex-aggregated WAC/RAC frames into per-hex employment records.

    Either input may be ``None`` (measure unavailable) or contain hexes the
    other lacks; all hexes present in either are emitted, with zero-filled
    counts on the side that's missing and null ratios/fractions where the
    denominator is zero.
    """
    all_cells: set[str] = set()
    if wac is not None:
        all_cells.update(wac["h3_index"].to_list())
    if rac is not None:
        all_cells.update(rac["h3_index"].to_list())

    wac_by_cell: dict[str, dict] = (
        {row["h3_index"]: row for row in wac.to_dicts()} if wac is not None else {}
    )
    rac_by_cell: dict[str, dict] = (
        {row["h3_index"]: row for row in rac.to_dicts()} if rac is not None else {}
    )

    records: list[H3EmploymentRecord] = []
    for cell in sorted(all_cells):
        wac_row = wac_by_cell.get(cell)
        rac_row = rac_by_cell.get(cell)
        total_jobs = int(wac_row["C000"]) if wac_row is not None else 0
        total_residents = int(rac_row["C000"]) if rac_row is not None else 0
        blocks_wac = int(wac_row["blocks_wac"]) if wac_row is not None else 0
        blocks_rac = int(rac_row["blocks_rac"]) if rac_row is not None else 0

        industry_mix = {
            code: (
                _safe_ratio(int(wac_row[code]), total_jobs) if wac_row is not None else None
            )
            for code in CNS_CODES
        }
        wage_tier_mix = {
            code: (
                _safe_ratio(int(wac_row[code]), total_jobs) if wac_row is not None else None
            )
            for code in CE_CODES
        }

        records.append(
            H3EmploymentRecord(
                h3_index=cell,
                year=year,
                total_jobs=total_jobs,
                total_residents=total_residents,
                jobs_to_residents_ratio=_safe_ratio(total_jobs, total_residents),
                industry_mix=industry_mix,
                wage_tier_mix=wage_tier_mix,
                blocks_wac=blocks_wac,
                blocks_rac=blocks_rac,
            )
        )
    return records


def aggregate_od_flows(
    year: int,
    xwalk: pl.DataFrame,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    fetcher: FetcherFn = download_to_cache,
    verify_checksums: bool = True,
) -> tuple[list[H3CommuteFlow], str | None]:
    """Aggregate LODES OD ``S000`` flows to a hex-to-hex commute matrix.

    Optional (per US-439): scoped to flows where both the home and work
    block resolve inside the 9-county Bay Area extent, via the same
    Bay-Area-filtered crosswalk used for WAC/RAC. Returns ``([], error)`` on
    a missing/unavailable OD file rather than raising, matching the
    WAC/RAC-independence convention.
    """
    try:
        sha_url = state_sha_url(STATE_CODE) if verify_checksums else None
        path = fetcher(
            f"https://lehd.ces.census.gov/data/lodes/LODES8/{STATE_CODE}/"
            f"{STATE_CODE}_od_main_JT00_{year}.csv.gz",
            cache_dir,
            sha_url,
        )
        data = _read_gzip_csv(path, ["w_geocode", "h_geocode", "S000"]).with_columns(
            pl.col("S000").cast(pl.Int64)
        )
    except Exception as exc:  # noqa: BLE001 — OD is optional; never fail the run
        return [], f"{type(exc).__name__}: {exc}"

    work_xwalk = xwalk.rename({"tabblk2020": "w_geocode", "h3_index": "work_h3"})
    home_xwalk = xwalk.rename({"tabblk2020": "h_geocode", "h3_index": "home_h3"})
    joined = data.join(work_xwalk, on="w_geocode", how="inner").join(
        home_xwalk, on="h_geocode", how="inner"
    )
    agg = joined.group_by(["home_h3", "work_h3"]).agg(pl.col("S000").sum().alias("flow_count"))
    flows = [
        H3CommuteFlow(
            home_h3=row["home_h3"],
            work_h3=row["work_h3"],
            year=year,
            flow_count=int(row["flow_count"]),
        )
        for row in agg.sort(["home_h3", "work_h3"]).to_dicts()
    ]
    return flows, None


@dataclass
class LodesBayAreaPipelineConfig:
    """Configuration for the Bay Area LODES employment density pipeline."""

    year: int = DEFAULT_YEAR
    h3_resolution: int = DEFAULT_H3_RESOLUTION
    cache_dir: Path = DEFAULT_CACHE_DIR
    verify_checksums: bool = True
    include_od: bool = False


@dataclass
class LodesBayAreaPipelineResult:
    """Result of a Bay Area LODES pipeline run: hex records + per-measure status."""

    records: list[H3EmploymentRecord]
    report: dict = field(default_factory=dict)
    commute_flows: list[H3CommuteFlow] = field(default_factory=list)


def run_bay_area_lodes_pipeline(
    config: LodesBayAreaPipelineConfig | None = None,
    fetcher: FetcherFn = download_to_cache,
) -> LodesBayAreaPipelineResult:
    """Execute the end-to-end Bay Area LODES WAC/RAC (+ optional OD) ETL pipeline.

    1. Loads the CA LODES v8 crosswalk, filtered to the 9 Bay Area FIPS
       counties, resolving each block's internal point to an H3 res-9 cell.
    2. Loads WAC (jobs, industry mix, wage tiers) and RAC (resident workers),
       independently — a missing/unavailable file on one side does not
       discard the other.
    3. Joins both to hexes and computes ``total_jobs``,
       ``jobs_to_residents_ratio``, industry mix fractions (CNS01-20), and
       wage tier fractions (CE01-03), tagged with the LODES vintage year.
    4. Optionally aggregates OD flows to a hex-to-hex commute matrix.
    """
    cfg = config or LodesBayAreaPipelineConfig()
    xwalk = load_bay_area_xwalk(
        cache_dir=cfg.cache_dir,
        resolution=cfg.h3_resolution,
        fetcher=fetcher,
        verify_checksums=cfg.verify_checksums,
    )

    wac, wac_error = _load_measure(
        "wac",
        "w_geocode",
        ("C000", *CNS_CODES, *CE_CODES),
        cfg.year,
        xwalk,
        cfg.cache_dir,
        fetcher,
        cfg.verify_checksums,
    )
    rac, rac_error = _load_measure(
        "rac",
        "h_geocode",
        ("C000",),
        cfg.year,
        xwalk,
        cfg.cache_dir,
        fetcher,
        cfg.verify_checksums,
    )

    records = build_employment_records(wac, rac, cfg.year)

    report: dict = {
        "wac_status": "ok" if wac_error is None else "no_data",
        "rac_status": "ok" if rac_error is None else "no_data",
        "hexes": len(records),
        "year": cfg.year,
        "lodes_version": LODES_VERSION,
        "bay_area_blocks": xwalk.height,
    }
    if wac_error is not None:
        report["wac_error"] = wac_error
    if rac_error is not None:
        report["rac_error"] = rac_error

    commute_flows: list[H3CommuteFlow] = []
    if cfg.include_od:
        commute_flows, od_error = aggregate_od_flows(
            cfg.year, xwalk, cfg.cache_dir, fetcher, cfg.verify_checksums
        )
        report["od_status"] = "ok" if od_error is None else "no_data"
        if od_error is not None:
            report["od_error"] = od_error
        report["commute_flows"] = len(commute_flows)

    logger.info(
        "Bay Area LODES pipeline: WAC=%s RAC=%s -> %d hexes (year=%d)",
        report["wac_status"],
        report["rac_status"],
        len(records),
        cfg.year,
    )
    return LodesBayAreaPipelineResult(records=records, report=report, commute_flows=commute_flows)


__all__ = [
    "CE_CODES",
    "CNS_CODES",
    "DEFAULT_H3_RESOLUTION",
    "DEFAULT_YEAR",
    "LODES_VERSION",
    "H3CommuteFlow",
    "H3EmploymentRecord",
    "LodesBayAreaPipelineConfig",
    "LodesBayAreaPipelineResult",
    "aggregate_od_flows",
    "build_employment_records",
    "load_bay_area_xwalk",
    "run_bay_area_lodes_pipeline",
]
