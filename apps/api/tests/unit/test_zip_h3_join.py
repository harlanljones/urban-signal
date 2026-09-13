"""Unit tests for the ZIP-to-H3 area-weighted join (US-440).

Uses small synthetic squares (not real ZCTA geometry — that's
``zcta_boundaries``'s job) so hex counts and overlap ratios are deterministic
and fast to assert on. Covers the ticket's three named scenarios: a
single-ZIP hex, a multi-ZIP (overlapping) hex, and the missing-data fallback
when one contributing ZIP has no value for a period.
"""

import pytest
from shapely.geometry import Polygon

from src.spatial.zip_h3_join import (
    ZipHexWeight,
    aggregate_extensive,
    aggregate_intensive,
    build_weights,
    hexes_for_zctas,
)

# Two squares over the East Bay that overlap in their middle band, so some
# hexes fall entirely in ZIP A, some entirely in ZIP B, and some in both.
ZIP_A = Polygon([(-122.46, 37.75), (-122.46, 37.78), (-122.42, 37.78), (-122.42, 37.75)])
ZIP_B = Polygon([(-122.43, 37.75), (-122.43, 37.78), (-122.39, 37.78), (-122.39, 37.75)])


@pytest.fixture(scope="module")
def weights():
    return build_weights({"94601": ZIP_A, "94610": ZIP_B}, resolution=9)


class TestBuildWeights:
    def test_every_hex_has_at_least_one_contributor(self, weights):
        assert len(weights) > 0
        assert all(len(contributors) >= 1 for contributors in weights.values())

    def test_weights_are_positive_fractions(self, weights):
        for contributors in weights.values():
            for w in contributors.values():
                assert 0.0 < w.hex_fraction <= 1.0 + 1e-9
                assert 0.0 < w.zcta_fraction <= 1.0 + 1e-9

    def test_skips_empty_or_degenerate_polygon(self):
        degenerate = Polygon()
        result = build_weights({"00000": degenerate, "94601": ZIP_A}, resolution=9)
        assert all("00000" not in contributors for contributors in result.values())


class TestSingleZipHex:
    """A hex fully inside one ZIP and untouched by the other."""

    def test_single_zip_hex_gets_one_contributor(self, weights):
        single = {c: w for c, w in weights.items() if len(w) == 1}
        assert single, "expected at least one hex touched by only one ZIP"
        _cell, contributors = next(iter(single.items()))
        zcta = next(iter(contributors))
        assert zcta in ("94601", "94610")

    def test_single_zip_hex_intensive_equals_that_zips_value(self, weights):
        single = {c: w for c, w in weights.items() if len(w) == 1}
        _cell, contributors = next(iter(single.items()))
        zcta = next(iter(contributors))
        values = {"94601": 900000.0, "94610": 1450000.0}
        result = aggregate_intensive(contributors, values)
        assert result == pytest.approx(values[zcta])

    def test_single_zip_hex_extensive_is_a_fraction_of_the_total(self, weights):
        single = {c: w for c, w in weights.items() if len(w) == 1}
        _cell, contributors = next(iter(single.items()))
        zcta = next(iter(contributors))
        totals = {"94601": 100.0, "94610": 200.0}
        result = aggregate_extensive(contributors, totals)
        expected = totals[zcta] * contributors[zcta].zcta_fraction
        assert result == pytest.approx(expected)


class TestMultiZipHex:
    """A hex overlapping both ZIPs in their shared band."""

    def test_multi_zip_hex_has_two_contributors(self, weights):
        multi = {c: w for c, w in weights.items() if len(w) > 1}
        assert multi, "expected at least one hex touched by both ZIPs"
        assert set(next(iter(multi.values())).keys()) == {"94601", "94610"}

    def test_multi_zip_hex_intensive_is_area_weighted_average(self, weights):
        multi = {c: w for c, w in weights.items() if len(w) > 1}
        _cell, contributors = next(iter(multi.items()))
        values = {"94601": 900000.0, "94610": 1300000.0}
        result = aggregate_intensive(contributors, values)
        w_a = contributors["94601"].hex_fraction
        w_b = contributors["94610"].hex_fraction
        expected = (values["94601"] * w_a + values["94610"] * w_b) / (w_a + w_b)
        assert result == pytest.approx(expected)
        # Blended value must lie strictly between the two source values.
        assert min(values.values()) < result < max(values.values())

    def test_multi_zip_hex_extensive_sums_both_allocations(self, weights):
        multi = {c: w for c, w in weights.items() if len(w) > 1}
        _cell, contributors = next(iter(multi.items()))
        totals = {"94601": 100.0, "94610": 200.0}
        result = aggregate_extensive(contributors, totals)
        expected = sum(totals[z] * contributors[z].zcta_fraction for z in contributors)
        assert result == pytest.approx(expected)


class TestMissingDataFallback:
    """A contributing ZIP has no reported value for this period."""

    def test_intensive_falls_back_to_the_reporting_zip_only(self, weights):
        multi = {c: w for c, w in weights.items() if len(w) > 1}
        _cell, contributors = next(iter(multi.items()))
        # 94610 has no value this period (e.g. too few Redfin transactions).
        partial_values = {"94601": 950000.0}
        result = aggregate_intensive(contributors, partial_values)
        assert result == pytest.approx(950000.0)

    def test_extensive_falls_back_to_the_reporting_zip_only(self, weights):
        multi = {c: w for c, w in weights.items() if len(w) > 1}
        _cell, contributors = next(iter(multi.items()))
        partial_totals = {"94601": 100.0}
        result = aggregate_extensive(contributors, partial_totals)
        expected = 100.0 * contributors["94601"].zcta_fraction
        assert result == pytest.approx(expected)

    def test_hex_with_no_reporting_zip_returns_none(self, weights):
        _cell, contributors = next(iter(weights.items()))
        assert aggregate_intensive(contributors, {}) is None
        assert aggregate_extensive(contributors, {}) is None

    def test_unregistered_zcta_in_values_is_ignored(self, weights):
        _cell, contributors = next(iter(weights.items()))
        zcta = next(iter(contributors))
        result = aggregate_intensive(contributors, {zcta: 500.0, "99999": 999999.0})
        assert result == pytest.approx(500.0)


class TestHexesForZctas:
    def test_filters_to_touched_hexes_only(self, weights):
        only_a = hexes_for_zctas(weights, ["94601"])
        assert all("94601" in contributors for contributors in only_a.values())
        assert len(only_a) < len(weights)

    def test_unknown_zcta_yields_nothing(self, weights):
        assert hexes_for_zctas(weights, ["00000"]) == {}


def test_zip_hex_weight_is_a_plain_value_object():
    w = ZipHexWeight(hex_fraction=0.5, zcta_fraction=0.1)
    assert w.hex_fraction == 0.5
    assert w.zcta_fraction == 0.1
