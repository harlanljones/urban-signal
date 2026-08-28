"""Unit tests for the national signal builder (US-382).

All tests run offline: LODES CSVs are synthesized gz fixtures and the fetcher is
stubbed to return local paths.
"""

import gzip
from pathlib import Path

import h3
import polars as pl
import pytest

from src.export import national_builder as nb
from src.export.national_builder import (
    JOBS_COL,
    RANK_COLS,
    WORKERS_COL,
    _attach_ranks,
    _expected_sha,
    _read_gzip_csv,
    _sha256,
    aggregate_state,
    build_national,
)

RES = 6

# Fixture block coordinates (Manhattan + one rural point); expected cells are
# computed with the real h3 library so the test asserts aggregation, not geometry.
BLOCKS = {
    "360610001001001": (40.7505, -73.9934),  # two blocks share one res-6 cell (dense)
    "360610001001002": (40.7507, -73.9936),
    "360610001001003": (40.8410, -73.9390),  # own cell
    "301100001001004": (46.8790, -113.9960),  # wac-only rural block
}


def _write_gz_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(",".join(header) + "\n")
        for row in rows:
            handle.write(",".join(row) + "\n")


@pytest.fixture()
def state_fixtures(tmp_path: Path) -> dict[str, Path]:
    cache = tmp_path / "cache"
    latlng = list(BLOCKS.values())
    _write_gz_csv(
        cache / "de_xwalk.csv.gz",
        ["tabblk2020", "blklatdd", "blklondd"],
        [[geocode, f"{lat:.7f}", f"{lng:.7f}"] for geocode, (lat, lng) in zip(BLOCKS, latlng)],
    )
    wac_rows = [
        ["360610001001001", "120"],
        ["360610001001002", "80"],
        ["301100001001004", "5"],
    ]
    _write_gz_csv(
        cache / "de_wac_S000_JT00_2023.csv.gz",
        ["w_geocode", "C000", "createdate"],
        [row + ["20240101"] for row in wac_rows],
    )
    rac_rows = [
        ["360610001001001", "60"],
        ["360610001001003", "45"],
    ]
    _write_gz_csv(
        cache / "de_rac_S000_JT00_2023.csv.gz",
        ["h_geocode", "C000", "createdate"],
        [row + ["20240101"] for row in rac_rows],
    )

    def fetcher(url: str, cache_dir: Path) -> Path:
        name = url.rsplit("/", 1)[-1]
        target = cache_dir / name
        if not target.exists():
            raise FileNotFoundError(f"fixture fetcher missing {name}")
        return target

    return {"cache": cache, "fetcher": fetcher}


def _expected_cells(resolution: int = RES) -> set[str]:
    return {h3.latlng_to_cell(lat, lng, resolution) for lat, lng in BLOCKS.values()}


def test_read_gzip_csv_selects_columns(tmp_path: Path):
    path = tmp_path / "t.csv.gz"
    _write_gz_csv(
        path, ["w_geocode", "C000", "createdate"], [["360610001001001", "10", "20240101"]]
    )
    frame = _read_gzip_csv(path, ["w_geocode", "C000"])
    assert frame.columns == ["w_geocode", "C000"]
    with pytest.raises(ValueError, match="missing columns"):
        _read_gzip_csv(path, ["nope"])


def test_expected_sha_and_hashing(tmp_path: Path):
    path = tmp_path / "f.txt"
    path.write_text("hello")
    sha = _sha256(path)
    assert sha == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    sha_list = tmp_path / "lodes_xx.sha256sum"
    sha_list.write_text(f"{sha}  f.txt\n deadbeef  other.txt\n")
    assert _expected_sha(sha_list, "f.txt") == sha
    assert _expected_sha(sha_list, "other.txt") == "deadbeef"
    assert _expected_sha(sha_list, "unknown.txt") is None


def test_aggregate_state_sums_and_block_counts(state_fixtures):
    frame = aggregate_state("de", 2023, RES, state_fixtures["cache"], state_fixtures["fetcher"])
    dense_cell = h3.latlng_to_cell(*BLOCKS["360610001001001"], RES)
    row = frame.filter(pl.col("h3_index") == dense_cell)
    assert row[JOBS_COL][0] == 200  # 120 + 80 in the same cell
    assert row["blocks_wac"][0] == 2
    assert row[WORKERS_COL][0] == 60
    assert row["blocks_rac"][0] == 1
    rural_cell = h3.latlng_to_cell(*BLOCKS["301100001001004"], RES)
    rural = frame.filter(pl.col("h3_index") == rural_cell)
    assert rural[JOBS_COL][0] == 5 and rural[WORKERS_COL][0] is None
    # Cells sum: dense + manhattan-2 + rural = 3 distinct cells
    assert len(frame) == 3


def test_aggregate_state_drops_cells_outside_filter(state_fixtures):
    keep = {h3.latlng_to_cell(*BLOCKS["360610001001001"], RES)}
    frame = aggregate_state(
        "de", 2023, RES, state_fixtures["cache"], state_fixtures["fetcher"], cell_filter=keep
    )
    assert set(frame["h3_index"].to_list()) == keep


def test_attach_ranks_orders_and_preserves_nulls():
    frame = pl.DataFrame(
        {
            "h3_index": ["a", "b", "c", "d"],
            JOBS_COL: [10, None, 30, 20],
            WORKERS_COL: [None, None, None, None],
            "blocks_wac": [1, 0, 1, 1],
            "blocks_rac": [0, 0, 0, 0],
        }
    )
    ranked = _attach_ranks(frame)
    jobs_rank = dict(zip(ranked["h3_index"].to_list(), ranked[RANK_COLS[0]].to_list()))
    assert jobs_rank["b"] is None  # null stays null, never synthesized
    assert jobs_rank["a"] < jobs_rank["d"] < jobs_rank["c"]
    workers_rank = dict(zip(ranked["h3_index"].to_list(), ranked[RANK_COLS[1]].to_list()))
    assert all(v is None for v in workers_rank.values())


def test_build_national_end_to_end(state_fixtures, tmp_path, monkeypatch):
    monkeypatch.setattr(nb, "LODES_STATES", frozenset({"de"}))
    # One pyramid cell far from the fixture blocks must stay null (honest no-data).
    empty_cell = h3.latlng_to_cell(20.0, -100.0, RES)
    cells = tuple(sorted(_expected_cells() | {empty_cell}))
    report = build_national(
        out_dir=tmp_path,
        resolution=RES,
        year=2023,
        states=["de"],
        cache_dir=state_fixtures["cache"],
        fetcher=state_fixtures["fetcher"],
        cells_provider=lambda res: cells,
    )

    assert report["cells"] == 4
    assert report["hexes_with_jobs"] == 2  # dense cell + rural (uptown is RAC-only)
    assert report["hexes_with_workers"] == 2
    assert report["total_jobs"] == 205  # 120 + 80 + 5
    assert report["total_workers"] == 105  # 60 + 45
    assert report["states"]["de"]["status"] == "ok"

    res_dir = tmp_path / "national" / f"res{RES}"
    parquet_files = sorted(res_dir.glob("*.parquet"))
    assert parquet_files
    full = pl.concat([pl.read_parquet(path) for path in parquet_files], how="vertical")
    assert set(full.columns) == set(nb.PARQUET_COLUMNS) - {"res3_parent"}
    assert full["year"][0] == 2023
    assert full["signal_source"][0] == nb.SIGNAL_SOURCE
    dense_cell = h3.latlng_to_cell(*BLOCKS["360610001001001"], RES)
    uptown_cell = h3.latlng_to_cell(*BLOCKS["360610001001003"], RES)
    row = full.filter(pl.col("h3_index") == dense_cell)
    assert row[JOBS_COL][0] == 200
    assert row["res5_parent"][0] == h3.cell_to_parent(dense_cell, 5)
    assert row["res4_parent"][0] == h3.cell_to_parent(dense_cell, 4)
    # cells with no data are present with null metrics (never zero-filled)
    null_rows = full.filter(pl.col(JOBS_COL).is_null())
    assert sorted(null_rows["h3_index"].to_list()) == sorted([uptown_cell, empty_cell])
    assert null_rows[RANK_COLS[0]].is_null().all()


def test_build_national_reports_no_data_state(state_fixtures, tmp_path, monkeypatch):
    monkeypatch.setattr(nb, "LODES_STATES", frozenset({"de", "zz"}))

    def failing_fetcher(url: str, cache_dir: Path) -> Path:
        if "_zz_" in url or url.endswith("/zz/zz_xwalk.csv.gz"):
            raise RuntimeError("state unavailable")
        return state_fixtures["fetcher"](url, cache_dir)

    report = build_national(
        out_dir=tmp_path,
        resolution=RES,
        year=2023,
        states=["de", "zz"],
        cache_dir=state_fixtures["cache"],
        fetcher=failing_fetcher,
        cells_provider=lambda res: tuple(sorted(_expected_cells())),
    )
    assert report["states"]["de"]["status"] == "ok"
    assert report["states"]["zz"]["status"] == "no_data"
    # The run survives a coverage gap; totals come only from de.
    assert report["total_jobs"] == 205


def test_build_national_rejects_unknown_states(state_fixtures, tmp_path):
    with pytest.raises(ValueError, match="Unknown LODES state codes"):
        build_national(
            out_dir=tmp_path,
            resolution=RES,
            states=["xx"],
            cache_dir=state_fixtures["cache"],
            cells_provider=lambda res: (),
        )
