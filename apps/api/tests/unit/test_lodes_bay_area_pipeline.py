"""Unit tests for the Bay Area LODES employment density pipeline (US-439).

All tests run offline: LODES CSVs are synthesized gz fixtures and the fetcher
is stubbed to return local paths, following ``test_national_builder.py``.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import h3
import pytest

from src.spatial.acs_variables import BAY_AREA_COUNTIES
from src.spatial.lodes_bay_area_pipeline import (
    CE_CODES,
    CNS_CODES,
    LodesBayAreaPipelineConfig,
    aggregate_od_flows,
    build_employment_records,
    load_bay_area_xwalk,
    run_bay_area_lodes_pipeline,
)

RES = 9

# Two blocks in San Francisco (county 075) that map to the same res-9 hex, one
# block in Alameda (county 001), and one non-Bay-Area block in Fresno county
# (county 019) that must be filtered out.
SF_BLOCK_A = "060750101001001"
SF_BLOCK_B = "060750101001002"
ALAMEDA_BLOCK = "060010101001001"
FRESNO_BLOCK = "060190101001001"  # not a Bay Area county — must be excluded

SF_LATLNG = (37.7749, -122.4194)
ALAMEDA_LATLNG = (37.8044, -122.2712)
FRESNO_LATLNG = (36.7378, -119.7871)


def _write_gz_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(",".join(header) + "\n")
        for row in rows:
            handle.write(",".join(row) + "\n")


def _cns_ce_zeros() -> dict[str, str]:
    return {c: "0" for c in (*CNS_CODES, *CE_CODES)}


@pytest.fixture()
def bay_area_fixtures(tmp_path: Path) -> dict:
    cache = tmp_path / "cache"
    _write_gz_csv(
        cache / "ca_xwalk.csv.gz",
        ["tabblk2020", "blklatdd", "blklondd"],
        [
            [SF_BLOCK_A, f"{SF_LATLNG[0]:.7f}", f"{SF_LATLNG[1]:.7f}"],
            [SF_BLOCK_B, f"{SF_LATLNG[0] + 0.00001:.7f}", f"{SF_LATLNG[1] + 0.00001:.7f}"],
            [ALAMEDA_BLOCK, f"{ALAMEDA_LATLNG[0]:.7f}", f"{ALAMEDA_LATLNG[1]:.7f}"],
            [FRESNO_BLOCK, f"{FRESNO_LATLNG[0]:.7f}", f"{FRESNO_LATLNG[1]:.7f}"],
        ],
    )

    wac_header = ["w_geocode", "C000", *CNS_CODES, *CE_CODES, "createdate"]

    def _wac_row(geocode: str, c000: int, cns01: int, ce01: int, ce02: int, ce03: int) -> list[str]:
        row = _cns_ce_zeros()
        row["C000"] = str(c000)
        row["CNS01"] = str(cns01)
        row["CE01"] = str(ce01)
        row["CE02"] = str(ce02)
        row["CE03"] = str(ce03)
        return [geocode] + [row[k] if k != "C000" else str(c000) for k in wac_header[1:-1]] + ["20240101"]

    _write_gz_csv(
        cache / "ca_wac_S000_JT00_2023.csv.gz",
        wac_header,
        [
            _wac_row(SF_BLOCK_A, 100, 40, 20, 30, 50),
            _wac_row(SF_BLOCK_B, 50, 10, 5, 15, 30),
            # Alameda block has jobs but zero residents in RAC below.
            _wac_row(ALAMEDA_BLOCK, 20, 20, 20, 0, 0),
            _wac_row(FRESNO_BLOCK, 999, 999, 999, 0, 0),
        ],
    )

    rac_header = ["h_geocode", "C000", "createdate"]
    _write_gz_csv(
        cache / "ca_rac_S000_JT00_2023.csv.gz",
        rac_header,
        [
            [SF_BLOCK_A, "60", "20240101"],
            [SF_BLOCK_B, "10", "20240101"],
            # ALAMEDA_BLOCK deliberately absent from RAC (zero residents).
            [FRESNO_BLOCK, "500", "20240101"],
        ],
    )

    od_header = ["w_geocode", "h_geocode", "S000", "createdate"]
    _write_gz_csv(
        cache / "ca_od_main_JT00_2023.csv.gz",
        od_header,
        [
            [SF_BLOCK_A, ALAMEDA_BLOCK, "15", "20240101"],
            [ALAMEDA_BLOCK, SF_BLOCK_A, "5", "20240101"],
            # Cross-boundary flow (home in Fresno) must be dropped.
            [SF_BLOCK_A, FRESNO_BLOCK, "3", "20240101"],
        ],
    )

    def fetcher(url: str, cache_dir: Path, sha_list_url: str | None = None) -> Path:
        name = url.rsplit("/", 1)[-1]
        target = Path(cache_dir) / name
        if not target.exists():
            raise FileNotFoundError(f"fixture fetcher missing {name}")
        return target

    return {"cache": cache, "fetcher": fetcher}


def test_bay_area_counties_cover_nine_fips_codes():
    assert len(BAY_AREA_COUNTIES) == 9


def test_load_bay_area_xwalk_filters_to_nine_counties(bay_area_fixtures):
    xwalk = load_bay_area_xwalk(
        cache_dir=bay_area_fixtures["cache"],
        resolution=RES,
        fetcher=bay_area_fixtures["fetcher"],
        verify_checksums=False,
    )
    blocks = set(xwalk["tabblk2020"].to_list())
    assert blocks == {SF_BLOCK_A, SF_BLOCK_B, ALAMEDA_BLOCK}
    assert FRESNO_BLOCK not in blocks

    sf_cell = h3.latlng_to_cell(*SF_LATLNG, RES)
    assert sf_cell in set(xwalk["h3_index"].to_list())


def test_run_bay_area_lodes_pipeline_computes_hex_records(bay_area_fixtures):
    cfg = LodesBayAreaPipelineConfig(
        year=2023, h3_resolution=RES, cache_dir=bay_area_fixtures["cache"], verify_checksums=False
    )
    result = run_bay_area_lodes_pipeline(config=cfg, fetcher=bay_area_fixtures["fetcher"])

    assert result.report["wac_status"] == "ok"
    assert result.report["rac_status"] == "ok"
    assert result.report["year"] == 2023
    assert result.report["lodes_version"] == "v8"

    sf_cell = h3.latlng_to_cell(*SF_LATLNG, RES)
    alameda_cell = h3.latlng_to_cell(*ALAMEDA_LATLNG, RES)
    by_cell = {r.h3_index: r for r in result.records}

    # SF hex: two blocks merge into one hex (dense point cloud).
    sf_rec = by_cell[sf_cell]
    assert sf_rec.total_jobs == 150  # 100 + 50
    assert sf_rec.total_residents == 70  # 60 + 10
    assert sf_rec.blocks_wac == 2
    assert sf_rec.blocks_rac == 2
    assert sf_rec.jobs_to_residents_ratio == pytest.approx(150 / 70)
    assert sf_rec.industry_mix["CNS01"] == pytest.approx(50 / 150)
    assert sf_rec.wage_tier_mix["CE01"] == pytest.approx(25 / 150)
    assert sf_rec.wage_tier_mix["CE02"] == pytest.approx(45 / 150)
    assert sf_rec.wage_tier_mix["CE03"] == pytest.approx(80 / 150)
    assert sf_rec.year == 2023
    assert sf_rec.lodes_version == "v8"

    # Alameda hex has jobs but zero residents (RAC absent for that block):
    # ratio must be gracefully None, never a ZeroDivisionError.
    alameda_rec = by_cell[alameda_cell]
    assert alameda_rec.total_jobs == 20
    assert alameda_rec.total_residents == 0
    assert alameda_rec.jobs_to_residents_ratio is None
    assert alameda_rec.industry_mix["CNS01"] == pytest.approx(1.0)

    # Fresno block was filtered out upstream by the Bay Area xwalk.
    fresno_cell = h3.latlng_to_cell(*FRESNO_LATLNG, RES)
    assert fresno_cell not in by_cell


def test_industry_mix_and_wage_tiers_sum_to_one(bay_area_fixtures):
    cfg = LodesBayAreaPipelineConfig(cache_dir=bay_area_fixtures["cache"], verify_checksums=False)
    result = run_bay_area_lodes_pipeline(config=cfg, fetcher=bay_area_fixtures["fetcher"])
    sf_cell = h3.latlng_to_cell(*SF_LATLNG, RES)
    rec = next(r for r in result.records if r.h3_index == sf_cell)
    wage_sum = sum(v for v in rec.wage_tier_mix.values() if v is not None)
    assert wage_sum == pytest.approx(1.0)
    assert set(rec.industry_mix) == set(CNS_CODES)
    assert set(rec.wage_tier_mix) == set(CE_CODES)


def test_zero_jobs_and_zero_residents_hexes_never_raise():
    """A hex present only in RAC (zero jobs) or only in WAC (zero residents)
    must null out ratios/fractions gracefully rather than divide by zero."""
    import polars as pl

    jobs_only_cell = "89283082837ffff"
    residents_only_cell = "89283082833ffff"
    wac = pl.DataFrame(
        {
            "h3_index": [jobs_only_cell],
            "C000": [10],
            **{c: [10 if c == "CNS01" else 0] for c in CNS_CODES},
            **{c: [10 if c == "CE01" else 0] for c in CE_CODES},
            "blocks_wac": [1],
        }
    )
    rac = pl.DataFrame(
        {
            "h3_index": [residents_only_cell],
            "C000": [5],
            "blocks_rac": [1],
        }
    )
    records = build_employment_records(wac=wac, rac=rac, year=2023)
    by_cell = {r.h3_index: r for r in records}

    jobs_only = by_cell[jobs_only_cell]
    assert jobs_only.total_jobs == 10
    assert jobs_only.total_residents == 0
    assert jobs_only.jobs_to_residents_ratio is None
    assert jobs_only.industry_mix["CNS01"] == pytest.approx(1.0)

    residents_only = by_cell[residents_only_cell]
    assert residents_only.total_jobs == 0
    assert residents_only.total_residents == 5
    assert residents_only.jobs_to_residents_ratio == 0.0
    assert all(v is None for v in residents_only.industry_mix.values())
    assert all(v is None for v in residents_only.wage_tier_mix.values())


def test_missing_wac_file_does_not_discard_rac(tmp_path: Path):
    cache = tmp_path / "cache"
    _write_gz_csv(
        cache / "ca_xwalk.csv.gz",
        ["tabblk2020", "blklatdd", "blklondd"],
        [[SF_BLOCK_A, f"{SF_LATLNG[0]:.7f}", f"{SF_LATLNG[1]:.7f}"]],
    )
    _write_gz_csv(
        cache / "ca_rac_S000_JT00_2023.csv.gz",
        ["h_geocode", "C000", "createdate"],
        [[SF_BLOCK_A, "60", "20240101"]],
    )
    # No ca_wac_*.csv.gz written -> WAC fetch fails, RAC must still aggregate.

    def fetcher(url: str, cache_dir: Path, sha_list_url: str | None = None) -> Path:
        name = url.rsplit("/", 1)[-1]
        target = Path(cache_dir) / name
        if not target.exists():
            raise FileNotFoundError(f"fixture fetcher missing {name}")
        return target

    cfg = LodesBayAreaPipelineConfig(cache_dir=cache, verify_checksums=False)
    result = run_bay_area_lodes_pipeline(config=cfg, fetcher=fetcher)
    assert result.report["wac_status"] == "no_data"
    assert result.report["rac_status"] == "ok"
    assert len(result.records) == 1
    rec = result.records[0]
    assert rec.total_jobs == 0
    assert rec.total_residents == 60
    assert rec.jobs_to_residents_ratio == 0.0
    assert all(v is None for v in rec.industry_mix.values())


def test_aggregate_od_flows_scoped_to_bay_area_boundary(bay_area_fixtures):
    xwalk = load_bay_area_xwalk(
        cache_dir=bay_area_fixtures["cache"],
        resolution=RES,
        fetcher=bay_area_fixtures["fetcher"],
        verify_checksums=False,
    )
    flows, error = aggregate_od_flows(
        2023, xwalk, cache_dir=bay_area_fixtures["cache"], fetcher=bay_area_fixtures["fetcher"], verify_checksums=False
    )
    assert error is None
    sf_cell = h3.latlng_to_cell(*SF_LATLNG, RES)
    alameda_cell = h3.latlng_to_cell(*ALAMEDA_LATLNG, RES)
    pairs = {(f.home_h3, f.work_h3): f.flow_count for f in flows}
    assert pairs.get((alameda_cell, sf_cell)) == 15
    assert pairs.get((sf_cell, alameda_cell)) == 5
    # The Fresno-bound flow (home block outside the Bay Area xwalk) must be
    # excluded: only the two intra-Bay-Area pairs should be present.
    assert len(flows) == 2
    for f in flows:
        assert f.year == 2023
        assert f.lodes_version == "v8"


def test_include_od_flag_wires_flows_into_pipeline_report(bay_area_fixtures):
    cfg = LodesBayAreaPipelineConfig(cache_dir=bay_area_fixtures["cache"], verify_checksums=False, include_od=True)
    result = run_bay_area_lodes_pipeline(config=cfg, fetcher=bay_area_fixtures["fetcher"])
    assert result.report["od_status"] == "ok"
    assert result.report["commute_flows"] == len(result.commute_flows)
    assert len(result.commute_flows) == 2
