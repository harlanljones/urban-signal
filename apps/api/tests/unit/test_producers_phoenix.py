"""Unit tests for the Phoenix leaf (US-197): spatial module + field maps.

Phoenix is a PARTIAL metro: Planning_Permit (primary PERMITS) plus ShapePHX
``_DL`` companion, and ShapePHX Short Term Rentals as SLA (STR is the SLA,
not ``FeedType.STR``). 311 and deeds are absent. Tests pass WITHOUT a spine
registration (no ``CityId.PHOENIX``).

Live fixtures captured 2026-08-27 from maps.phoenix.gov / mapportal.phoenix.gov,
flattened the way ``ArcGISClient`` would (geometry → latitude/longitude,
epoch-ms dates → ISO).
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_phoenix import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.spatial.cities.phoenix import (
    PHOENIX_CITY_ID,
    PHOENIX_DIVISION_BBOXES,
    PHOENIX_DIVISIONS,
    PHOENIX_FEED_SPECS,
    PHOENIX_FROZEN_SHAPEPHX_PERMITS,
    PHOENIX_GEOCODE_CONTEXT,
    PHOENIX_METRO_BBOX,
    PHOENIX_PERMITS_ENDPOINT,
    PHOENIX_SHAPEPHX_PERMITS_ENDPOINT,
    PHOENIX_SLA_ENDPOINT,
    PHOENIX_SUBMARKETS,
    get_phoenix_dataset,
    is_in_phoenix_metro,
)
from src.spatial.city_registry import CityId, FeedType


# Planning_Permit layer 1, newest issued row with PER_ISSUE_DATE (2026-08-26).
# Geometry WGS84 via outSR=4326; client would also set latitude/longitude.
PERMITS_ROW = {
    "OBJECTID": 1242716,
    "PER_TYPE": "SE",
    "PER_NUM": "26010094",
    "PROJECT": "21-671",
    "PERMIT_NAME": "PARCEL A - PANEL B",
    "PERMIT_STAT": "OPEN",
    "PER_ENT_DATE": "2026-08-26T23:04:32+00:00",
    "PER_ISSUE_DATE": "2026-08-26T23:16:28+00:00",
    "STREET_FULL_NAME": "3555 E HIDALGO AVE",
    "PID": "3453054",
    "PER_TYPE_DESC": "STRUC/ELEC",
    "SCOPE_DESC": "COMMERCIAL MISCELLANEOUS",
    "MOD_DESC": "Building",
    "longitude": -112.0048014927471,
    "latitude": 33.39352246419764,
}

# ShapePHXPermitsPoints_DL companion. ADDRESS is null on every row; X/Y are
# NAD83, not WGS84. Geometry is the coordinate path.
SHAPEPHX_PERMITS_ROW = {
    "OBJECTID": 6508689,
    "PERMIT_NUMBER": "CTR-102505941- ",
    "PERMIT_TYPE": (
        "Construction and Trades Residential;Residential;Single Family;Addition only"
    ),
    "STATUS": "Issued",
    "PERMIT_ISSUE_DATE": "2026-08-19T00:00:00+00:00",
    "CONTACT": "NMG Construction LLC",
    "SCOPE": "GARAGE ADDITION (WITH INTERIOR STORAGE L",
    "X": 659083,
    "Y": 934211,
    "ADDRESS": None,
    "PERMIT_NAME": "2ND FLOOR ADDITION",
    "RECORD_ID": "a03cs00000sTMpGAAW",
    "longitude": -112.0509990832149,
    "latitude": 33.56797814435257,
}

# ShapePHX Short Term Rentals — this is the SLA. Native LATITUDE/LONGITUDE.
SLA_ROW = {
    "OBJECTID": 421368,
    "ID": "a02cs000000b0AkAAI",
    "NAME": "STR-2024-003813",
    "REGISTRATION_TYPE": "Short Term Rental Operating Permit",
    "STATUS": "Operational",
    "ISSUED_DATE": "2026-08-19T07:00:00+00:00",
    "EXPIRATION_DATE": "2027-08-19T07:00:00+00:00",
    "PROPERTY_ADDRESS": "223 W PINE VALLEY DR  (Active)",
    "PROPERTY_CITY_STATE": "PHOENIX, AZ",
    "PROPERTY_ZIP": "85023-5284",
    "LATITUDE": 33.62137321,
    "LONGITUDE": -112.07692455,
    "NAD83_X": 651216.48506133,
    "NAD83_Y": 953652.52461079,
    "POW_NAME": "Tim Ford",
    "longitude": -112.07692391867715,
    "latitude": 33.621378802947355,
}


class TestPhoenixSpatial:
    def test_city_id_constant(self):
        assert PHOENIX_CITY_ID == "phoenix"

    def test_metro_contains_center(self):
        assert is_in_phoenix_metro(33.4484, -112.0740) is True  # Downtown
        assert is_in_phoenix_metro(33.3417, -111.9833) is True  # Ahwatukee
        assert is_in_phoenix_metro(33.7967, -112.1180) is True  # North Gateway

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_phoenix_metro(None, None) is False
        assert is_in_phoenix_metro(33.4484, -111.8833) is False  # Scottsdale
        assert is_in_phoenix_metro(32.2226, -110.9747) is False  # Tucson
        assert is_in_phoenix_metro(36.1699, -115.1398) is False  # Las Vegas

    def test_live_samples_sit_inside_the_metro_bbox(self):
        assert is_in_phoenix_metro(PERMITS_ROW["latitude"], PERMITS_ROW["longitude"])
        assert is_in_phoenix_metro(
            SHAPEPHX_PERMITS_ROW["latitude"], SHAPEPHX_PERMITS_ROW["longitude"]
        )
        assert is_in_phoenix_metro(SLA_ROW["LATITUDE"], SLA_ROW["LONGITUDE"])
        assert is_in_phoenix_metro(33.478714188303854, -112.22159505670245)  # 75th Ave

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in PHOENIX_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= PHOENIX_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= PHOENIX_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= PHOENIX_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= PHOENIX_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in PHOENIX_SUBMARKETS.items():
            bbox = PHOENIX_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in PHOENIX_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(PHOENIX_SUBMARKETS)

    def test_submarkets_carry_phoenix_city_id(self):
        assert {m.city_id for m in PHOENIX_SUBMARKETS.values()} == {"phoenix"}
        for meta in PHOENIX_SUBMARKETS.values():
            assert meta.name
            assert meta.borough
            assert meta.description
            assert meta.zoom > 0
            assert meta.pitch >= 0
            assert meta.base_lims > 0
            assert meta.capex > 0
            assert meta.permit_vel > 0
            assert meta.shift_ratio > 0
            assert meta.sla > 0

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in PHOENIX_DIVISIONS.items():
            bbox = PHOENIX_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name
            assert meta.city_id == "phoenix"

    def test_division_count(self):
        assert 4 <= len(PHOENIX_DIVISIONS) <= 8


class TestNoSpineRegistration:
    def test_city_id_phoenix_is_registered(self):
        assert CityId.PHOENIX.value == "phoenix"
        assert "phoenix" in {c.value for c in CityId}

    def test_feed_map_has_no_311_deeds_or_str_type(self):
        assert set(PHOENIX_FEED_SPECS) == {"permits", "sla"}
        assert "str" not in PHOENIX_FEED_SPECS
        assert "311" not in PHOENIX_FEED_SPECS
        assert "deeds" not in PHOENIX_FEED_SPECS


class TestFeedRegistration:
    def test_permits_spec_matches_live_planning_permit(self):
        spec = get_phoenix_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == PHOENIX_PERMITS_ENDPOINT
        assert spec.watermark_col == "PER_ISSUE_DATE"
        assert spec.id_keys == ["PER_NUM", "PID", "OBJECTID"]
        assert spec.producer_key == "permits"
        assert spec.needs_geocode is False
        assert spec.expected_cadence_days == 1
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.field_map is PERMITS_FIELD_MAP
        assert spec.companion_endpoints["shapephx_issued"] == (
            PHOENIX_SHAPEPHX_PERMITS_ENDPOINT
        )

    def test_companion_is_dl_only_not_frozen_twin(self):
        spec = get_phoenix_dataset(FeedType.PERMITS)
        companion = spec.companion_endpoints["shapephx_issued"]
        assert companion.endswith("ShapePHXPermitsPoints_DL/MapServer/0")
        assert "ShapePHXPermitsPoints_DL" in companion
        assert companion != PHOENIX_FROZEN_SHAPEPHX_PERMITS
        assert PHOENIX_FROZEN_SHAPEPHX_PERMITS not in spec.companion_endpoints.values()

    def test_sla_spec_is_shapephx_str_not_feedtype_str(self):
        spec = get_phoenix_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == PHOENIX_SLA_ENDPOINT
        assert spec.watermark_col == "ISSUED_DATE"
        assert spec.id_keys == ["NAME", "ID", "OBJECTID"]
        assert spec.producer_key == "sla"
        assert spec.needs_geocode is False
        assert spec.expected_cadence_days == 7
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.field_map is SLA_FIELD_MAP

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.COMPLAINTS_311, FeedType.DEEDS, FeedType.STR],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'phoenix'.*available"):
            get_phoenix_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert set(FIELD_MAP) == {"permits", "sla"}
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert GEOCODE_CONTEXT == PHOENIX_GEOCODE_CONTEXT == "Phoenix, AZ"


class TestPhoenixFieldMaps:
    def test_permits_map_reads_live_planning_permit_columns(self):
        row = PERMITS_ROW
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "26010094"
        assert first_mapped(row, PERMITS_FIELD_MAP, "issuance_date") == (
            "2026-08-26T23:16:28+00:00"
        )
        assert first_mapped(row, PERMITS_FIELD_MAP, "filing_date") == (
            "2026-08-26T23:04:32+00:00"
        )
        assert first_mapped(row, PERMITS_FIELD_MAP, "status") == "OPEN"
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_type") == "STRUC/ELEC"
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") == (
            "3555 E HIDALGO AVE"
        )

    def test_permits_job_id_falls_back_to_pid_then_objectid(self):
        row = {"PER_NUM": None, "PID": "3453054", "OBJECTID": 1242716}
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "3453054"
        row = {"PER_NUM": None, "PID": None, "OBJECTID": 1242716}
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == 1242716

    def test_companion_map_reads_shapephx_spellings(self):
        row = SHAPEPHX_PERMITS_ROW
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "CTR-102505941- "
        assert first_mapped(row, PERMITS_FIELD_MAP, "issuance_date") == (
            "2026-08-19T00:00:00+00:00"
        )
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_type") == (
            "Construction and Trades Residential;Residential;Single Family;Addition only"
        )
        assert first_mapped(row, PERMITS_FIELD_MAP, "status") == "Issued"
        # ADDRESS is null on every ShapePHX companion row.
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") is None

    def test_companion_state_plane_xy_are_not_lat_lng_candidates(self):
        mapped_cols = {c for cols in PERMITS_FIELD_MAP.values() for c in cols}
        assert "X" not in mapped_cols
        assert "Y" not in mapped_cols
        assert "NAD83_X" not in mapped_cols
        assert "NAD83_Y" not in mapped_cols

    def test_sla_map_reads_live_str_columns(self):
        row = SLA_ROW
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "STR-2024-003813"
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == (
            "Short Term Rental Operating Permit"
        )
        assert first_mapped(row, SLA_FIELD_MAP, "effective_date") == (
            "2026-08-19T07:00:00+00:00"
        )
        assert first_mapped(row, SLA_FIELD_MAP, "expiration_date") == (
            "2027-08-19T07:00:00+00:00"
        )
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "Tim Ford"
        assert first_mapped(row, SLA_FIELD_MAP, "latitude") == pytest.approx(33.62137321)
        assert first_mapped(row, SLA_FIELD_MAP, "longitude") == pytest.approx(
            -112.07692455
        )
        assert first_mapped(row, SLA_FIELD_MAP, "address_street") == (
            "223 W PINE VALLEY DR  (Active)"
        )
        assert first_mapped(row, SLA_FIELD_MAP, "status") == "Operational"
        assert first_mapped(row, SLA_FIELD_MAP, "zipcode") == "85023-5284"

    def test_sla_license_id_falls_back_to_id_then_objectid(self):
        row = {"NAME": None, "ID": "a02cs000000b0AkAAI", "OBJECTID": 421368}
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "a02cs000000b0AkAAI"

    def test_sla_does_not_map_nad83_as_wgs84(self):
        mapped_cols = {c for cols in SLA_FIELD_MAP.values() for c in cols}
        assert "NAD83_X" not in mapped_cols
        assert "NAD83_Y" not in mapped_cols
        assert first_mapped(SLA_ROW, SLA_FIELD_MAP, "latitude") != SLA_ROW["NAD83_Y"]
        assert first_mapped(SLA_ROW, SLA_FIELD_MAP, "longitude") != SLA_ROW["NAD83_X"]


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        return DOBPermitsProducer()


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


class TestPhoenixPermitParsing:
    def test_native_geometry_permit_parses_without_geocoder(self, permits, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: PERMITS_FIELD_MAP,
        )
        event = permits.parse_socrata_row(PERMITS_ROW, city_id="phoenix")
        assert event is not None
        assert event.city_id == "phoenix"
        assert event.job_id == "26010094"
        assert event.address_street == "3555 E HIDALGO AVE"
        assert event.latitude == pytest.approx(33.39352246419764)
        assert event.longitude == pytest.approx(-112.0048014927471)
        assert event.issuance_date is not None
        assert str(event.issuance_date).startswith("2026-08-26")
        assert event.h3_res7 is not None
        assert is_in_phoenix_metro(event.latitude, event.longitude)

    def test_companion_geometry_permit_parses_without_address(self, permits, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: PERMITS_FIELD_MAP,
        )
        event = permits.parse_socrata_row(SHAPEPHX_PERMITS_ROW, city_id="phoenix")
        assert event is not None
        assert event.job_id == "CTR-102505941-"
        assert event.latitude == pytest.approx(33.56797814435257)
        assert event.longitude == pytest.approx(-112.0509990832149)
        # NAD83 easting/northing must not leak into WGS84 slots.
        assert event.latitude != 934211
        assert event.longitude != 659083


class TestPhoenixSlaParsing:
    def test_native_str_parses_as_sla(self, sla, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: SLA_FIELD_MAP,
        )
        event = sla.parse_socrata_row(SLA_ROW, city_id="phoenix")
        assert event is not None
        assert event.city_id == "phoenix"
        assert event.license_id == "STR-2024-003813"
        assert event.license_type == "Short Term Rental Operating Permit"
        assert event.license_status == "Operational"
        assert event.dba == "Tim Ford"
        assert event.address == "223 W PINE VALLEY DR  (Active)"
        assert event.latitude == pytest.approx(33.62137321)
        assert event.longitude == pytest.approx(-112.07692455)
        assert str(event.effective_date).startswith("2026-08-19")
        assert str(event.expiration_date).startswith("2027-08-19")
        assert event.h3_res7 is not None
        assert is_in_phoenix_metro(event.latitude, event.longitude)

    def test_str_is_not_a_new_feed_type(self):
        assert PHOENIX_FEED_SPECS["sla"]["producer_key"] == "sla"
        assert "str" not in PHOENIX_FEED_SPECS
