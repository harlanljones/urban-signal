"""Unit tests for the national signal builder (US-382, US-435).

All tests run offline: LODES CSVs are synthesized gz fixtures and the fetcher is
stubbed to return local paths.
"""

import gzip
import json
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

BLOCKS = {
    "360610001001001": (40.7505, -73.9934),
    "360610001001002": (40.7507, -73.9936),
    "360610001001003": (40.8410, -73.9390),
    "301100001001004": (46.8790, -113.9960),
}


def _write_gz_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(",".join(header) + "\n")
        for row in rows:
            handle.write(",".join(row) + "\n")


@pytest.fixture()
def state_fixtures(tmp_path: Path) -> dict:
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

    def fetcher(url: str, cache_dir: Path, sha_list_url: str | None = None) -> Path:
        name = url.rsplit("/", 1)[-1]
        target = Path(cache_dir) / name
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
    frame, report = aggregate_state("de", 2023, RES, state_fixtures["cache"], state_fixtures["fetcher"])
    dense_cell = h3.latlng_to_cell(*BLOCKS["360610001001001"], RES)
    row = frame.filter(pl.col("h3_index") == dense_cell)
    assert row[JOBS_COL][0] == 200
    assert row["blocks_wac"][0] == 2
    assert row[WORKERS_COL][0] == 60
    assert row["blocks_rac"][0] == 1
    rural_cell = h3.latlng_to_cell(*BLOCKS["301100001001004"], RES)
    rural = frame.filter(pl.col("h3_index") == rural_cell)
    assert rural[JOBS_COL][0] == 5 and rural[WORKERS_COL][0] is None
    assert len(frame) == 3
    assert report["wac_status"] == "ok"
    assert report["rac_status"] == "ok"


def test_aggregate_state_drops_cells_outside_filter(state_fixtures):
    keep = {h3.latlng_to_cell(*BLOCKS["360610001001001"], RES)}
    frame, _ = aggregate_state(
        "de", 2023, RES, state_fixtures["cache"], state_fixtures["fetcher"], cell_filter=keep
    )
    assert set(frame["h3_index"].to_list()) == keep


def test_aggregate_state_independent_wac_rac(state_fixtures):
    """A missing RAC file should not discard WAC data (US-435)."""

    def failing_rac_fetcher(url: str, cache_dir: Path, sha_list_url: str | None = None) -> Path:
        if "_rac_" in url:
            raise RuntimeError("RAC unavailable")
        return state_fixtures["fetcher"](url, cache_dir)

    frame, report = aggregate_state(
        "de", 2023, RES, state_fixtures["cache"], failing_rac_fetcher
    )
    assert report["wac_status"] == "ok"
    assert report["rac_status"] == "no_data"
    dense_cell = h3.latlng_to_cell(*BLOCKS["360610001001001"], RES)
    row = frame.filter(pl.col("h3_index") == dense_cell)
    assert row[JOBS_COL][0] == 200
    assert row[WORKERS_COL][0] is None


def test_aggregate_state_independent_wac_rac_missing_wac(state_fixtures):
    """A missing WAC file should not discard RAC data (US-435)."""

    def failing_wac_fetcher(url: str, cache_dir: Path, sha_list_url: str | None = None) -> Path:
        if "_wac_" in url:
            raise RuntimeError("WAC unavailable")
        return state_fixtures["fetcher"](url, cache_dir)

    frame, report = aggregate_state(
        "de", 2023, RES, state_fixtures["cache"], failing_wac_fetcher
    )
    assert report["wac_status"] == "no_data"
    assert report["rac_status"] == "ok"
    dense_cell = h3.latlng_to_cell(*BLOCKS["360610001001001"], RES)
    row = frame.filter(pl.col("h3_index") == dense_cell)
    assert row[JOBS_COL][0] is None
    assert row[WORKERS_COL][0] == 60


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
    assert jobs_rank["b"] is None
    assert jobs_rank["a"] < jobs_rank["d"] < jobs_rank["c"]
    workers_rank = dict(zip(ranked["h3_index"].to_list(), ranked[RANK_COLS[1]].to_list()))
    assert all(v is None for v in workers_rank.values())


def test_build_national_end_to_end(state_fixtures, tmp_path, monkeypatch):
    monkeypatch.setattr(nb, "LODES_STATES", frozenset({"de"}))
    empty_cell = h3.latlng_to_cell(20.0, -100.0, RES)
    cells = tuple(sorted(_expected_cells() | {empty_cell}))
    report = build_national(
        out_dir=tmp_path,
        year=2023,
        states=["de"],
        cache_dir=state_fixtures["cache"],
        fetcher=state_fixtures["fetcher"],
        cells_provider=lambda res: cells,
        promote=False,
    )

    assert len(report["artifacts"]) == len(nb.DEFAULT_RESOLUTIONS)
    res6 = report["artifacts"].get(str(RES))
    assert res6 is not None
    assert res6["cells"] == 4
    assert res6["hexes_with_jobs"] == 2
    assert res6["hexes_with_workers"] == 2
    assert res6["total_jobs"] == 205
    assert res6["total_workers"] == 105

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
    null_rows = full.filter(pl.col(JOBS_COL).is_null())
    assert sorted(null_rows["h3_index"].to_list()) == sorted([uptown_cell, empty_cell])
    assert null_rows[RANK_COLS[0]].is_null().all()


def test_build_national_reports_no_data_state(state_fixtures, tmp_path, monkeypatch):
    monkeypatch.setattr(nb, "LODES_STATES", frozenset({"de", "zz"}))

    def failing_fetcher(url: str, cache_dir: Path, sha_list_url: str | None = None) -> Path:
        if "_zz_" in url or url.endswith("/zz/zz_xwalk.csv.gz"):
            raise RuntimeError("state unavailable")
        return state_fixtures["fetcher"](url, cache_dir)

    report = build_national(
        out_dir=tmp_path,
        year=2023,
        states=["de", "zz"],
        cache_dir=state_fixtures["cache"],
        fetcher=failing_fetcher,
        cells_provider=lambda res: tuple(sorted(_expected_cells())),
        promote=False,
    )

    res6 = report["artifacts"].get(str(RES))
    assert res6 is not None
    assert res6["total_jobs"] == 205


def test_promote_national_writes_pointer(state_fixtures, tmp_path, monkeypatch):
    """A validated build promotes a pointer carrying identity + provenance (US-435 §23)."""
    import json

    from src.export.national_builder import promote_national

    monkeypatch.setattr(nb, "LODES_STATES", frozenset({"de"}))
    cells = tuple(sorted(_expected_cells()))
    build_national(
        out_dir=tmp_path,
        year=2023,
        resolutions=(RES,),
        states=["de"],
        cache_dir=state_fixtures["cache"],
        fetcher=state_fixtures["fetcher"],
        cells_provider=lambda res: cells,
    )
    pointer = json.loads((tmp_path / "national" / "current.json").read_text())
    assert pointer["sha256"] == promote_national(tmp_path)["sha256"]
    assert pointer["artifact_key"].startswith("national/census_lehd_lodes8/2023/")
    assert pointer["artifact_key"].endswith(pointer["sha256"])
    assert pointer["builder_revision"] == nb.BUILDER_REVISION
    assert pointer["lodes_version"] == "v8"
    assert pointer["resolutions"] == [RES]
    assert pointer["promoted_at"]


def test_promote_national_rejects_empty_build(state_fixtures, tmp_path, monkeypatch):
    """A build with no data chunks must not replace a valid pointer (US-435 §23)."""
    from src.export.national_builder import promote_national

    monkeypatch.setattr(nb, "LODES_STATES", frozenset({"de"}))
    build_national(
        out_dir=tmp_path,
        year=2023,
        resolutions=(RES,),
        states=["de"],
        cache_dir=state_fixtures["cache"],
        fetcher=state_fixtures["fetcher"],
        cells_provider=lambda res: (),
        promote=False,
    )
    with pytest.raises(ValueError, match="no data chunks"):
        promote_national(tmp_path)
    assert not (tmp_path / "national" / "current.json").exists()


def test_promote_national_rejects_missing_manifest(tmp_path):
    from src.export.national_builder import promote_national

    with pytest.raises(ValueError, match="no manifest"):
        promote_national(tmp_path)


def test_build_national_rejects_unknown_states(state_fixtures, tmp_path):
    with pytest.raises(ValueError, match="Unknown LODES state codes"):
        build_national(
            out_dir=tmp_path,
            states=["xx"],
            cache_dir=state_fixtures["cache"],
            cells_provider=lambda res: (),
        )


def test_build_national_manifest_sha256(state_fixtures, tmp_path, monkeypatch):
    """The aggregate manifest must include a sha256 over all resolution data (US-435)."""
    monkeypatch.setattr(nb, "LODES_STATES", frozenset({"de"}))
    cells = tuple(sorted(_expected_cells()))
    report = build_national(
        out_dir=tmp_path,
        year=2023,
        states=["de"],
        cache_dir=state_fixtures["cache"],
        fetcher=state_fixtures["fetcher"],
        cells_provider=lambda res: cells,
        promote=False,
    )
    assert "sha256" in report
    assert len(report["sha256"]) == 64

    manifest_path = tmp_path / "national" / "manifest.json"
    assert manifest_path.exists()
    loaded = json.loads(manifest_path.read_text())
    assert loaded["resolutions"] == list(nb.DEFAULT_RESOLUTIONS)
    assert loaded["checksum_verified"] is True
    assert loaded["lodes_version"] == "v8"
