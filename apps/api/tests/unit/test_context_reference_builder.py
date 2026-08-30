"""Tests for context_reference_builder (US-380)."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.producers.context_reference_builder import (
    CLINIC_OPENING_WINDOW_DAYS,
    EDGE_POSTSEC_CITY,
    EDGE_POSTSEC_LAT,
    EDGE_POSTSEC_LON,
    EDGE_POSTSEC_NAME,
    EDGE_POSTSEC_STATE,
    EDGE_POSTSEC_STREET,
    EDGE_POSTSEC_UNITID,
    EDGE_POSTSEC_YEAR,
    EDGE_POSTSEC_ZIP,
    SOURCE_FRA_CROSSINGS,
    SOURCE_FRA_INCIDENTS,
    SOURCE_HRSA_SITES,
    SOURCE_IMLS_LIBRARIES,
    SOURCE_NCES_POSTSEC,
    CampusRef,
    ClinicRef,
    ContextReferenceBuilder,
    CrossingRef,
    HexContextReference,
    LibraryRef,
    _coords,
    _field,
    _geom_point_coords,
    _text,
)


def _builder(indexer=None, city_for_point=None) -> ContextReferenceBuilder:
    """Construct a builder with defaults: mock indexer and no crosswalk."""
    idx = indexer or MagicMock()
    if indexer is None:
        idx.return_value = {
            "h3_res7": "r7_abc",
            "h3_res8": "r8_abc",
            "h3_res9": "r9_abc",
        }
    return ContextReferenceBuilder(indexer=idx, city_for_point=city_for_point)


# ---------------------------------------------------------------------------
# Standalone helper tests
# ---------------------------------------------------------------------------


class TestField:
    def test_first_present(self) -> None:
        row = {"a": "x", "b": "y"}
        assert _field(row, "a", "b") == "x"
        assert _field(row, "b", "a") == "y"

    def test_skips_none(self) -> None:
        row = {"a": None, "b": "y"}
        assert _field(row, "a", "b") == "y"

    def test_skips_blank(self) -> None:
        row = {"a": "  ", "b": "y"}
        assert _field(row, "a", "b") == "y"

    def test_returns_none_when_missing(self) -> None:
        row = {"a": "x"}
        assert _field(row, "z") is None

    def test_returns_none_on_empty_row(self) -> None:
        assert _field({}, "z") is None


class TestCoords:
    def test_valid_pair(self) -> None:
        assert _coords("40.7128", "-74.0060") == (40.7128, -74.0060)

    def test_none_lat(self) -> None:
        assert _coords(None, "-74.0") == (None, None)

    def test_none_lng(self) -> None:
        assert _coords("40.0", None) == (None, None)

    def test_null_island(self) -> None:
        assert _coords(0.0, 0.0) == (None, None)

    def test_blank_string(self) -> None:
        assert _coords("", "") == (None, None)


class TestGeomPointCoords:
    def test_valid_geopoint(self) -> None:
        geom = {"type": "Point", "coordinates": [-74.006, 40.7128]}
        lat, lng = _geom_point_coords(geom)
        assert lat == pytest.approx(40.7128)
        assert lng == pytest.approx(-74.006)

    def test_none(self) -> None:
        assert _geom_point_coords(None) == (None, None)

    def test_not_a_dict(self) -> None:
        assert _geom_point_coords("string") == (None, None)

    def test_short_coords(self) -> None:
        geom = {"coordinates": [-74.006]}
        assert _geom_point_coords(geom) == (None, None)

    def test_empty_coords(self) -> None:
        geom = {"coordinates": []}
        assert _geom_point_coords(geom) == (None, None)


class TestText:
    def test_none(self) -> None:
        assert _text(None) is None

    def test_blank(self) -> None:
        assert _text("  ") is None

    def test_strips(self) -> None:
        assert _text("  hello  ") == "hello"

    def test_non_string(self) -> None:
        assert _text(123) == "123"


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


class TestCrossingRef:
    def test_defaults(self) -> None:
        c = CrossingRef()
        assert c.source == ""
        assert c.objectid == ""
        assert c.aadt is None
        assert c.h3_res9 is None
        assert c.needs_geocode is False


class TestClinicRef:
    def test_defaults(self) -> None:
        c = ClinicRef()
        assert c.site_added_date is None


class TestHexContextReference:
    def test_minimal_required(self) -> None:
        ref = HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9")
        assert ref.crossing_density == 0
        assert ref.aadt_mean is None
        assert ref.city_id is None

    def test_fields(self) -> None:
        ref = HexContextReference(
            city_id="nyc", h3_res7="r7", h3_res8="r8", h3_res9="r9",
            crossing_density=5, rail_thru_trains=100.0, aadt_mean=2500.5,
            incident_count=2, library_density=3, campus_presence=1,
            clinic_density=4, clinic_openings_365d=1,
        )
        assert ref.city_id == "nyc"
        assert ref.crossing_density == 5
        assert ref.aadt_mean == 2500.5


# ---------------------------------------------------------------------------
# ContextReferenceBuilder tests
# ---------------------------------------------------------------------------


class TestInitAndTag:
    def test_stores_dependencies(self) -> None:
        idx = MagicMock()
        cwp = MagicMock()
        b = ContextReferenceBuilder(indexer=idx, city_for_point=cwp)
        assert b.indexer is idx
        assert b.city_for_point is cwp

    def test_defaults(self) -> None:
        b = ContextReferenceBuilder()
        assert b.indexer is None
        assert b.city_for_point is None

    def test_tag_sets_h3(self) -> None:
        b = _builder()
        rec = CrossingRef()
        b._tag(rec, 40.7128, -74.006)
        assert rec.latitude == 40.7128
        assert rec.longitude == -74.006
        assert rec.h3_res7 == "r7_abc"
        assert rec.h3_res8 == "r8_abc"
        assert rec.h3_res9 == "r9_abc"
        assert rec.needs_geocode is False

    def test_tag_sets_geocode_pending(self) -> None:
        b = _builder()
        rec = CrossingRef()
        b._tag(rec, None, None)
        assert rec.latitude is None
        assert rec.longitude is None
        assert rec.h3_res9 is None
        assert rec.needs_geocode is True

    def test_tag_city_for_point(self) -> None:
        cwp = MagicMock(return_value="nyc")
        b = _builder(city_for_point=cwp)
        rec = CrossingRef()
        b._tag(rec, 40.7128, -74.006)
        cwp.assert_called_once_with(40.7128, -74.006)
        assert rec.city_id == "nyc"

    def test_tag_no_indexer(self) -> None:
        b = ContextReferenceBuilder()
        rec = CrossingRef()
        b._tag(rec, 40.7128, -74.006)
        assert rec.h3_res7 is None
        assert rec.h3_res9 is None


class TestSited:
    def test_filters_unsited(self) -> None:
        b = _builder()
        sited = CrossingRef(h3_res9="r9")
        unsited = CrossingRef(h3_res9=None)
        result = b._sited([sited, unsited])
        assert result == [sited]

    def test_empty(self) -> None:
        b = _builder()
        assert b._sited([]) == []

    def test_none(self) -> None:
        b = _builder()
        assert b._sited(None) == []


class TestGeocodePendingRows:
    def test_returns_only_needs_geocode(self) -> None:
        b = _builder()
        r1 = CrossingRef(site_id="a", needs_geocode=True, address="123 Main")
        r2 = CrossingRef(site_id="b", needs_geocode=False)
        pending = b.geocode_pending_rows([r1, r2])
        assert len(pending) == 1
        assert pending[0]["site_id"] == "a"

    def test_empty(self) -> None:
        b = _builder()
        assert b.geocode_pending_rows([]) == []

    def test_none(self) -> None:
        b = _builder()
        assert b.geocode_pending_rows(None) == []


# ---------------------------------------------------------------------------
# Load / parse tests
# ---------------------------------------------------------------------------


class TestLoadFraCrossings:
    def test_dedup_by_crossing_min_objectid(self) -> None:
        b = _builder()
        rows = [
            {"crossing": "X1", "objectid": "100", "latitude": "40.0", "longitude": "-74.0"},
            {"crossing": "X1", "objectid": "050", "latitude": "40.1", "longitude": "-74.1"},
        ]
        records = b.load_fra_crossings(rows)
        assert len(records) == 1
        assert records[0].site_id == "X1"
        assert records[0].objectid == "050"  # min objectid (lexicographic)

    def test_skips_rows_without_crossing(self) -> None:
        b = _builder()
        rows = [{"objectid": "1", "latitude": "40.0", "longitude": "-74.0"}]
        records = b.load_fra_crossings(rows)
        assert len(records) == 0

    def test_fallback_to_geom(self) -> None:
        b = _builder()
        rows = [{"crossing": "X1", "objectid": "1",
                 "the_geom": {"type": "Point", "coordinates": [-74.0, 40.0]}}]
        records = b.load_fra_crossings(rows)
        assert len(records) == 1
        assert records[0].latitude == pytest.approx(40.0)

    def test_empty(self) -> None:
        b = _builder()
        assert b.load_fra_crossings([]) == []

    def test_none(self) -> None:
        b = _builder()
        assert b.load_fra_crossings(None) == []


class TestLoadFraIncidents:
    def test_counts_per_crossing(self) -> None:
        b = _builder()
        rows = [{"gradecrossingid": "X1"}, {"gradecrossingid": "X1"},
                {"gradecrossingid": "X2"}, {}]
        counts = b.load_fra_incidents(rows)
        assert counts == {"X1": 2, "X2": 1}

    def test_empty(self) -> None:
        b = _builder()
        assert b.load_fra_incidents([]) == {}

    def test_none(self) -> None:
        b = _builder()
        assert b.load_fra_incidents(None) == {}

    def test_skips_missing(self) -> None:
        b = _builder()
        rows = [{"some_other_field": "value"}]
        assert b.load_fra_incidents(rows) == {}


class TestLoadLibraries:
    def test_parses_row(self) -> None:
        b = _builder()
        rows = [{"LIBID": "L1", "LIBNAME": "Main Library",
                 "ADDRESS": "1 Library St", "CITY": "New York",
                 "STABR": "NY", "ZIP": "10001",
                 "LATITUDE": "40.7128", "LONGITUD": "-74.0060",
                 "GEOSTATUS": "A", "GEOMTYPE": "point"}]
        records = b.load_libraries(rows)
        assert len(records) == 1
        assert records[0].site_id == "L1"
        assert records[0].name == "Main Library"

    def test_skips_missing_libid(self) -> None:
        b = _builder()
        rows = [{"LIBNAME": "Missing ID"}]
        records = b.load_libraries(rows)
        assert len(records) == 0

    def test_empty(self) -> None:
        b = _builder()
        assert b.load_libraries([]) == []

    def test_none(self) -> None:
        b = _builder()
        assert b.load_libraries(None) == []


class TestLoadPostsec:
    def _line(self, **overrides: Any) -> str:
        parts = [""] * 21
        parts[EDGE_POSTSEC_UNITID] = str(overrides.get("unitid", "123456"))
        parts[EDGE_POSTSEC_NAME] = overrides.get("name", "Test University")
        parts[EDGE_POSTSEC_STREET] = overrides.get("street", "100 College Ave")
        parts[EDGE_POSTSEC_CITY] = overrides.get("city", "New York")
        parts[EDGE_POSTSEC_STATE] = overrides.get("state", "NY")
        parts[EDGE_POSTSEC_ZIP] = overrides.get("zip", "10001")
        parts[EDGE_POSTSEC_LAT] = overrides.get("lat", "40.7128")
        parts[EDGE_POSTSEC_LON] = overrides.get("lon", "-74.006")
        parts[EDGE_POSTSEC_YEAR] = overrides.get("year", "2024")
        return "|".join(parts)

    def test_parses_line(self) -> None:
        b = _builder()
        lines = [self._line()]
        records = b.load_postsec(lines)
        assert len(records) == 1
        assert records[0].site_id == "123456"
        assert records[0].name == "Test University"
        assert records[0].school_year == "2024"

    def test_skips_short_line(self) -> None:
        b = _builder()
        lines = ["short"]
        assert b.load_postsec(lines) == []

    def test_skips_blank_unitid(self) -> None:
        b = _builder()
        lines = [self._line(unitid="")]
        assert b.load_postsec(lines) == []

    def test_handles_empty_and_none(self) -> None:
        b = _builder()
        assert b.load_postsec([]) == []
        assert b.load_postsec(None) == []


class TestLoadHrsa:
    def test_parses_row(self) -> None:
        b = _builder()
        rows = [{"BPHC Assigned Number": "H1", "Site Name": "Health Center 1",
                 "Site Address": "200 Health Dr", "Site City": "Brooklyn",
                 "Site State Abbreviation": "NY", "Site Postal Code": "11201",
                 "Geocoding Artifact Address Primary Y Coordinate": "40.6782",
                 "Geocoding Artifact Address Primary X Coordinate": "-73.9442"}]
        records = b.load_hrsa(rows)
        assert len(records) == 1
        assert records[0].site_id == "H1"
        assert records[0].name == "Health Center 1"

    def test_falls_back_to_health_center_number(self) -> None:
        b = _builder()
        rows = [{"Health Center Number": "H2", "Site Name": "Health Center 2",
                 "Geocoding Artifact Address Primary Y Coordinate": "40.0",
                 "Geocoding Artifact Address Primary X Coordinate": "-74.0"}]
        records = b.load_hrsa(rows)
        assert len(records) == 1
        assert records[0].site_id == "H2"

    def test_skips_without_any_id(self) -> None:
        b = _builder()
        rows = [{"Site Name": "No ID"}]
        records = b.load_hrsa(rows)
        assert len(records) == 0

    def test_parses_site_added_date(self) -> None:
        b = _builder()
        rows = [{"BPHC Assigned Number": "H1",
                 "Geocoding Artifact Address Primary Y Coordinate": "40.0",
                 "Geocoding Artifact Address Primary X Coordinate": "-74.0",
                 "Site Added to Scope this Date": "01/15/2024"}]
        records = b.load_hrsa(rows)
        assert records[0].site_added_date == date(2024, 1, 15)

    def test_empty_and_none(self) -> None:
        b = _builder()
        assert b.load_hrsa([]) == []
        assert b.load_hrsa(None) == []


class TestParseSiteAdded:
    def test_valid_date(self) -> None:
        result = ContextReferenceBuilder._parse_site_added("01/15/2024")
        assert result == date(2024, 1, 15)

    def test_none(self) -> None:
        assert ContextReferenceBuilder._parse_site_added(None) is None

    def test_blank(self) -> None:
        assert ContextReferenceBuilder._parse_site_added("") is None

    def test_invalid_format(self) -> None:
        assert ContextReferenceBuilder._parse_site_added("2024-01-15") is None

    def test_whitespace(self) -> None:
        result = ContextReferenceBuilder._parse_site_added("  01/15/2024  ")
        assert result == date(2024, 1, 15)


# ---------------------------------------------------------------------------
# Aggregation tests
# ---------------------------------------------------------------------------


class TestAggregateCrossings:
    def test_basic_fold(self) -> None:
        b = _builder()
        records = [CrossingRef(h3_res7="r7", h3_res8="r8", h3_res9="r9_abc",
                               day_thru_trains=10, night_thru_trains=5,
                               aadt=1000.0, site_id="X1")]
        folds, weights = b.aggregate_crossings(records, {})
        assert "r9_abc" in folds
        assert folds["r9_abc"].crossing_density == 1
        assert folds["r9_abc"].rail_thru_trains == 15.0
        assert folds["r9_abc"].incident_count == 0
        assert weights["r9_abc"] == (1000.0, 1)

    def test_incident_count(self) -> None:
        b = _builder()
        records = [CrossingRef(h3_res9="r9_abc", site_id="X1")]
        folds, weights = b.aggregate_crossings(records, {"X1": 3})
        assert folds["r9_abc"].incident_count == 3

    def test_skips_unsited(self) -> None:
        b = _builder()
        records = [CrossingRef(h3_res9=None)]
        folds, weights = b.aggregate_crossings(records, {})
        assert folds == {}
        assert weights == {}

    def test_aadt_none_not_counted(self) -> None:
        b = _builder()
        records = [CrossingRef(h3_res9="r9_abc", aadt=None)]
        folds, weights = b.aggregate_crossings(records, {})
        assert folds["r9_abc"].crossing_density == 1
        assert folds["r9_abc"].aadt_mean is None
        assert weights == {}

    def test_empty(self) -> None:
        b = _builder()
        folds, weights = b.aggregate_crossings([], {})
        assert folds == {}
        assert weights == {}


class TestAggregateLibraries:
    def test_fold(self) -> None:
        b = _builder()
        records = [LibraryRef(h3_res9="r9_abc")]
        folds = b.aggregate_libraries(records)
        assert folds["r9_abc"].library_density == 1

    def test_skips_unsited(self) -> None:
        b = _builder()
        records = [LibraryRef(h3_res9=None)]
        assert b.aggregate_libraries(records) == {}

    def test_empty(self) -> None:
        b = _builder()
        assert b.aggregate_libraries([]) == {}


class TestAggregateCampuses:
    def test_fold(self) -> None:
        b = _builder()
        records = [CampusRef(h3_res9="r9_abc")]
        folds = b.aggregate_campuses(records)
        assert folds["r9_abc"].campus_presence == 1

    def test_skips_unsited(self) -> None:
        b = _builder()
        records = [CampusRef(h3_res9=None)]
        assert b.aggregate_campuses(records) == {}

    def test_empty(self) -> None:
        b = _builder()
        assert b.aggregate_campuses([]) == {}


class TestAggregateClinics:
    def test_fold(self) -> None:
        b = _builder()
        records = [ClinicRef(h3_res9="r9_abc")]
        folds = b.aggregate_clinics(records, as_of=date(2025, 1, 1))
        assert folds["r9_abc"].clinic_density == 1
        assert folds["r9_abc"].clinic_openings_365d == 0

    def test_opening_in_window(self) -> None:
        b = _builder()
        as_of = date(2025, 3, 1)
        recent = date(2024, 6, 1)
        records = [ClinicRef(h3_res9="r9_abc", site_added_date=recent)]
        folds = b.aggregate_clinics(records, as_of=as_of)
        assert folds["r9_abc"].clinic_openings_365d == 1

    def test_opening_outside_window(self) -> None:
        b = _builder()
        as_of = date(2025, 3, 1)
        old = date(2023, 1, 1)
        records = [ClinicRef(h3_res9="r9_abc", site_added_date=old)]
        folds = b.aggregate_clinics(records, as_of=as_of)
        assert folds["r9_abc"].clinic_openings_365d == 0

    def test_default_as_of(self) -> None:
        b = _builder()
        records = [ClinicRef(h3_res9="r9_abc")]
        folds = b.aggregate_clinics(records)
        assert folds["r9_abc"].clinic_density == 1

    def test_skips_unsited(self) -> None:
        b = _builder()
        records = [ClinicRef(h3_res9=None)]
        assert b.aggregate_clinics(records) == {}

    def test_empty(self) -> None:
        b = _builder()
        assert b.aggregate_clinics([]) == {}


class TestMergeHexRows:
    def test_merges_two_dicts(self) -> None:
        b = _builder()
        a = HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9_abc", crossing_density=1)
        result = b.merge_hex_rows(
            {"r9_abc": a},
            {"r9_abc": HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9_abc", library_density=2)},
        )
        merged = result["r9_abc"]
        assert merged.crossing_density == 1
        assert merged.library_density == 2

    def test_handles_crossing_tuple(self) -> None:
        b = _builder()
        a = HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9_abc")
        folds, weights = {"r9_abc": a}, {"r9_abc": (5000.0, 3)}
        result = b.merge_hex_rows((folds, weights))
        merged = result["r9_abc"]
        assert merged.aadt_mean == pytest.approx(5000.0 / 3)

    def test_city_id_not_overwritten(self) -> None:
        b = _builder()
        a = HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9_abc", city_id="nyc")
        b_ref = HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9_abc", city_id=None)
        result = b.merge_hex_rows({"r9_abc": a}, {"r9_abc": b_ref})
        assert result["r9_abc"].city_id == "nyc"

    def test_none_city_id_filled(self) -> None:
        b = _builder()
        a = HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9_abc", city_id=None)
        b_ref = HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9_abc", city_id="nyc")
        result = b.merge_hex_rows({"r9_abc": a}, {"r9_abc": b_ref})
        assert result["r9_abc"].city_id == "nyc"

    def test_empty(self) -> None:
        b = _builder()
        assert b.merge_hex_rows() == {}

    def test_no_aadt(self) -> None:
        b = _builder()
        a = HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9_abc")
        result = b.merge_hex_rows(({"r9_abc": a}, {}))
        assert result["r9_abc"].aadt_mean is None

    def test_separate_hexes(self) -> None:
        b = _builder()
        a = HexContextReference(h3_res7="r7", h3_res8="r8", h3_res9="r9_a", crossing_density=1)
        b_ref = HexContextReference(h3_res7="r7_x", h3_res8="r8_x", h3_res9="r9_b", library_density=3)
        result = b.merge_hex_rows({"r9_a": a}, {"r9_b": b_ref})
        assert result["r9_a"].crossing_density == 1
        assert result["r9_b"].library_density == 3
        assert "r9_a" in result
        assert "r9_b" in result


# ---------------------------------------------------------------------------
# build_reference_table integration
# ---------------------------------------------------------------------------


class TestBuildReferenceTable:
    def test_full_pipeline(self) -> None:
        b = _builder()
        crossings = [CrossingRef(h3_res9="r9_abc", day_thru_trains=10, night_thru_trains=5, aadt=1000.0, site_id="X1")]
        libraries = [LibraryRef(h3_res9="r9_abc")]
        campuses = [CampusRef(h3_res9="r9_abc")]
        clinics = [ClinicRef(h3_res9="r9_abc")]
        result = b.build_reference_table(
            crossings=crossings, libraries=libraries, campuses=campuses,
            clinics=clinics, incidents_by_crossing={"X1": 2},
            as_of=date(2025, 1, 1),
        )
        merged = result["r9_abc"]
        assert merged.crossing_density == 1
        assert merged.rail_thru_trains == 15.0
        assert merged.incident_count == 2
        assert merged.library_density == 1
        assert merged.campus_presence == 1
        assert merged.clinic_density == 1

    def test_empty(self) -> None:
        b = _builder()
        assert b.build_reference_table() == {}

    def test_none_inputs(self) -> None:
        b = _builder()
        result = b.build_reference_table(crossings=None, libraries=None, campuses=None, clinics=None)
        assert result == {}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_multiple_crossings_same_hex(self) -> None:
        b = _builder()
        records = [
            CrossingRef(h3_res9="r9_abc", day_thru_trains=10, night_thru_trains=5, aadt=1000.0, site_id="X1"),
            CrossingRef(h3_res9="r9_abc", day_thru_trains=20, night_thru_trains=10, aadt=2000.0, site_id="X2"),
        ]
        folds, weights = b.aggregate_crossings(records, {"X1": 1, "X2": 2})
        assert folds["r9_abc"].crossing_density == 2
        assert folds["r9_abc"].rail_thru_trains == 45.0
        assert folds["r9_abc"].incident_count == 3
        assert weights["r9_abc"] == (3000.0, 2)

    def test_multiple_sources_same_hex_merge(self) -> None:
        b = _builder()
        crossing_folds, weights = b.aggregate_crossings([CrossingRef(h3_res9="r9_abc", site_id="X1")], {})
        lib_folds = b.aggregate_libraries([LibraryRef(h3_res9="r9_abc")])
        result = b.merge_hex_rows((crossing_folds, weights), lib_folds)
        assert result["r9_abc"].crossing_density == 1
        assert result["r9_abc"].library_density == 1

    def test_row_without_coords_sets_needs_geocode(self) -> None:
        b = _builder()
        rows = [{"crossing": "X1", "objectid": "1"}]
        records = b.load_fra_crossings(rows)
        assert len(records) == 1
        assert records[0].needs_geocode is True
