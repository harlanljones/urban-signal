"""Tests for BG→H3 resolver built from local LODES crosswalk fixtures (US-361)."""

from __future__ import annotations

from pathlib import Path

from src.spatial.acs_join import BGToH3Resolver


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "acs"


def test_bg_to_h3_from_local_xwalks():
    resolver = BGToH3Resolver.from_local_xwalks([FIXTURES / "xwalk_sample.csv"], resolution=9)
    cell1 = resolver("220710001001")
    cell2 = resolver("220710001002")
    assert isinstance(cell1, str) and len(cell1) > 0
    assert isinstance(cell2, str) and len(cell2) > 0
    assert cell1 != "" and cell2 != ""
