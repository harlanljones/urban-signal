"""Unit tests for the geographic context-source registry (US-435)."""

import pytest

from src.export import national_builder as nb
from src.spatial.context_source import (
    CONTEXT_SOURCES,
    ContextSourceId,
    get_context_source,
)
from src.spatial.national_grid import NATIONAL_RESOLUTIONS
from src.spatial.zbp_signal import normalize_zbp_flag


def test_lodes_spec_matches_builder_contract():
    spec = get_context_source(ContextSourceId.LODES)
    assert spec.implemented is True
    assert spec.supported_resolutions == NATIONAL_RESOLUTIONS
    assert spec.builder_module == "src.export.national_builder"
    assert spec.builder_revision == nb.BUILDER_REVISION
    assert spec.requires_checksum is True
    assert spec.vintage_year == 2023
    assert spec.version == "v8"
    assert spec.attribution
    assert spec.assignment_method == "census_block_internal_point"
    # Every published metric is nullable: missing data stays null, never zero-filled.
    assert spec.metrics
    assert all(m.nullable for m in spec.metrics)


def test_lodes_manifest_carries_spec_identity(tmp_path, monkeypatch):
    """The built artifact must identify source, vintage, and builder revision (US-435 §12)."""
    from src.export.national_builder import build_national

    monkeypatch.setattr(nb, "LODES_STATES", frozenset({"de"}))
    manifest = build_national(
        out_dir=tmp_path,
        year=2023,
        resolutions=(6,),
        states=["de"],
        cache_dir=tmp_path / "cache",
        fetcher=_missing_fetcher,
        cells_provider=lambda res: (),
        promote=False,
    )
    assert manifest["signal_source"] == "census_lehd_lodes8"
    assert manifest["builder_revision"] == nb.BUILDER_REVISION
    assert manifest["year"] == 2023
    assert manifest["lodes_version"] == "v8"


def _missing_fetcher(url: str, cache_dir, sha_list_url=None):
    raise RuntimeError("no fixture data")


def test_zbp_spec_declares_assignment_and_suppression_contract():
    spec = get_context_source(ContextSourceId.ZBP)
    assert spec.implemented is False
    assert spec.assignment_method == "zip_to_dominant_zcta_representative_point"
    assert "representative point" in spec.assignment_description.lower()
    by_name = {m.name: m for m in spec.metrics}
    assert by_name["employment"].suppression == "withheld_as_null"
    # The registered contract must agree with the proven helpers: flags are
    # unknown (None), never zero; a real zero survives.
    assert normalize_zbp_flag("D") is None
    assert normalize_zbp_flag("S") is None
    assert normalize_zbp_flag("0") == 0.0


def test_unknown_source_readable_error():
    with pytest.raises(KeyError, match="not registered"):
        get_context_source("qcew")  # type: ignore[arg-type]


def test_registry_covers_expected_sources():
    assert set(CONTEXT_SOURCES) == {ContextSourceId.LODES, ContextSourceId.ZBP}
