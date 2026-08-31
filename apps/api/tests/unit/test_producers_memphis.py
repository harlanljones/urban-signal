"""Unit tests for the Memphis leaf (US-201): spatial module + field maps.

Memphis is a PARTIAL metro: DPD Building Permits (monthly ArcGIS) and
citywide 311 (same-day ArcGIS). SLA / deeds stay absent. Tests pass
WITHOUT a spine registration (no CityId.MEMPHIS).

Live fixtures captured 2026-08-27 from MEMEGIS AGOL and 311.memphistn.gov.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_memphis import (
    COMPLAINTS_311_FIELD_MAP,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.spatial.cities.memphis import (
    MEMPHIS_311_ENDPOINT,
    MEMPHIS_CITY_ID,
    MEMPHIS_DIVISION_BBOXES,
    MEMPHIS_DIVISIONS,
    MEMPHIS_FEED_SPECS,
    MEMPHIS_GEOCODE_CONTEXT,
    MEMPHIS_METRO_BBOX,
    MEMPHIS_PERMITS_ENDPOINT,
    MEMPHIS_SUBMARKETS,
    REGISTRATION,
    get_memphis_dataset,
    is_in_memphis_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address
from src.spatial.submarkets import SubmarketMeta


# Newest DPD permit on the 2026-08-27 probe (Issued_Date 2026-07-31).
# Native WGS84 attributes match outSR=4326 geometry.
_PERMITS_FIXTURE = {
    "Record_ID": "RES-ALT-26-000896",
    "Issued_Date": "2026-07-31T05:00:00+00:00",
    "Sub_Type": "RES",
    "Construction_Type": "ALT",
    "Valuation": 23000,
    "Address": "2218 OXFORD SQUARE CT",
    "City": "MEMPHIS",
    "Description": (
        "Changing out windows, doors and siding, renovating inside of units "
        "to include getting electrical, plumbing and mechanical up to code."
    ),
    "ZIP_Code": "38116",
    "State": "TN",
    "Latitude": 35.032970528686185,
    "Longitude": -89.99330263662729,
    "ObjectId": 116468,
    # ArcGISClient setdefault from outSR=4326 geometry (does not overwrite attrs).
    "latitude": 35.032970528686185,
    "longitude": -89.99330263662729,
}

# Newest 311 row on a later 2026-08-27 probe. Geometry is WGS84 via outSR=4326.
# X/Y happen to be WGS84 on this row; the map still must not read them.
_311_FIXTURE = {
    "OBJECTID": 1777330,
    "X": -89.90914791,
    "Y": 35.23092538,
    "INCIDENT_ID": None,
    "INCIDENT_NUMBER": "8041445",
    "REQUEST_TYPE": "SWM-Missing Cart",
    "REQUEST_STATUS": "Open",
    "REPORTED_DATE": "2026-08-27T19:52:00+00:00",
    "Closed_Date": None,
    "RESOLVED_DATE": None,
    "Location_Address": "4626  SAINT ELMO AVE",
    "ZipCode": "38128",
    "CITY": "Memphis",
    "STATE": "Tennessee",
    "DEPARTMENT": "Solid Waste Management",
    "CONTACT_NAME": "JANE DOE",
    "CONTACT_EMAIL": "jane@example.com",
    "CONTACT_PHONE": "901-555-0100",
    "MLGW_CUSTOMER": "DOE JANE",
    "MLGW_EMAIL": "jane@mlgw.example.com",
    "latitude": 35.23092537958096,
    "longitude": -89.90914790999382,
}

# Probe-documented mixed-CRS row: State Plane feet on X/Y, no lifted geometry.
_311_STATE_PLANE = {
    "OBJECTID": 1,
    "X": 800000.0,
    "Y": 270000.0,
    "INCIDENT_NUMBER": "8041417",
    "REQUEST_TYPE": "Code Enforcement — weeds occupied property",
    "REQUEST_STATUS": "Open",
    "REPORTED_DATE": "2026-08-27T19:31:00+00:00",
    "Location_Address": "123 TEST ST",
    "ZipCode": "38116",
    "CONTACT_NAME": "SHOULD NOT MAP",
}

_SUBMARKET_FIELDS = (
    "name",
    "borough",
    "lat",
    "lng",
    "zoom",
    "pitch",
    "base_lims",
    "capex",
    "permit_vel",
    "shift_ratio",
    "sla",
    "description",
    "city_id",
)


class TestMemphisSpatial:
    def test_city_id_constant(self):
        assert MEMPHIS_CITY_ID == "memphis"

    def test_metro_contains_center(self):
        assert is_in_memphis_metro(35.1495, -90.0490) is True
        assert is_in_memphis_metro(35.033, -90.025) is True  # Whitehaven
        assert is_in_memphis_metro(35.230, -89.910) is True  # Raleigh

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_memphis_metro(None, None) is False
        assert is_in_memphis_metro(36.1627, -86.7816) is False  # Nashville
        assert is_in_memphis_metro(35.0456, -85.3097) is False  # Chattanooga

    def test_live_samples_sit_inside_the_metro_bbox(self):
        assert is_in_memphis_metro(_PERMITS_FIXTURE["Latitude"], _PERMITS_FIXTURE["Longitude"])
        assert is_in_memphis_metro(_311_FIXTURE["latitude"], _311_FIXTURE["longitude"])

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in MEMPHIS_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= MEMPHIS_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= MEMPHIS_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= MEMPHIS_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= MEMPHIS_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in MEMPHIS_SUBMARKETS.items():
            bbox = MEMPHIS_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in MEMPHIS_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(MEMPHIS_SUBMARKETS)

    def test_submarkets_carry_memphis_city_id_and_all_meta_fields(self):
        assert {m.city_id for m in MEMPHIS_SUBMARKETS.values()} == {"memphis"}
        for name, meta in MEMPHIS_SUBMARKETS.items():
            assert isinstance(meta, SubmarketMeta), name
            for field in _SUBMARKET_FIELDS:
                value = getattr(meta, field)
                assert value is not None, f"{name}.{field}"
                if field == "description":
                    assert len(value) > 20, name

    def test_division_count_and_centers(self):
        assert 4 <= len(MEMPHIS_DIVISIONS) <= 8
        for name, meta in MEMPHIS_DIVISIONS.items():
            assert meta.city_id == "memphis"
            bbox = MEMPHIS_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_spatial_registration_references_module_constants(self):
        assert REGISTRATION.metro_bbox is MEMPHIS_METRO_BBOX
        assert REGISTRATION.submarkets is MEMPHIS_SUBMARKETS
        assert REGISTRATION.divisions is MEMPHIS_DIVISIONS
        assert REGISTRATION.contains is is_in_memphis_metro


class TestFeedRegistration:
    def test_exactly_two_feed_types_are_registered(self):
        assert set(MEMPHIS_FEED_SPECS) == {"permits", "311"}

    def test_permits_spec_matches_live_layer(self):
        spec = get_memphis_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == MEMPHIS_PERMITS_ENDPOINT
        assert spec.watermark_col == "Issued_Date"
        assert spec.id_keys == ["Record_ID", "ObjectId"]
        assert spec.producer_key == "permits"
        assert spec.expected_cadence_days == 31
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Memphis, TN"
        assert spec.oid_field == "ObjectId"
        assert spec.max_record_count == 1000
        assert spec.field_map == PERMITS_FIELD_MAP

    def test_311_spec_matches_live_layer(self):
        spec = get_memphis_dataset(FeedType.COMPLAINTS_311)
        assert spec.platform == "arcgis"
        assert spec.endpoint == MEMPHIS_311_ENDPOINT
        assert spec.watermark_col == "REPORTED_DATE"
        assert spec.watermark_col != "Closed_Date"
        assert spec.id_keys == ["INCIDENT_NUMBER", "OBJECTID"]
        assert spec.producer_key == "311"
        assert spec.expected_cadence_days == 1
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Memphis, TN"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 3000
        assert spec.field_map == COMPLAINTS_311_FIELD_MAP

    @pytest.mark.parametrize("absent_feed", [FeedType.SLA, FeedType.DEEDS, FeedType.STR])
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'memphis'.*available"):
            get_memphis_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert FIELD_MAP["311"] is COMPLAINTS_311_FIELD_MAP
        assert GEOCODE_CONTEXT == MEMPHIS_GEOCODE_CONTEXT == "Memphis, TN"


class TestMemphisFieldMaps:
    def test_permits_map_reads_live_columns(self):
        row = _PERMITS_FIXTURE
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "RES-ALT-26-000896"
        assert first_mapped(row, PERMITS_FIELD_MAP, "issuance_date") == "2026-07-31T05:00:00+00:00"
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") == "2218 OXFORD SQUARE CT"
        assert first_mapped(row, PERMITS_FIELD_MAP, "cost") == 23000
        assert first_mapped(row, PERMITS_FIELD_MAP, "zipcode") == "38116"
        assert first_mapped(row, PERMITS_FIELD_MAP, "latitude") == pytest.approx(35.032970528686185)
        assert first_mapped(row, PERMITS_FIELD_MAP, "longitude") == pytest.approx(-89.99330263662729)

    def test_permits_job_id_falls_back_to_objectid(self):
        row = {"Record_ID": None, "ObjectId": 116468}
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == 116468

    def test_permits_prefers_wgs84_attributes_not_xy(self):
        mapped = {c for cols in PERMITS_FIELD_MAP.values() for c in cols}
        assert "Latitude" in mapped
        assert "Longitude" in mapped
        assert "X" not in mapped
        assert "Y" not in mapped

    def test_311_map_reads_live_columns(self):
        row = _311_FIXTURE
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_id") == "8041445"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "complaint_type") == "SWM-Missing Cart"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "created_date") == "2026-08-27T19:52:00+00:00"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_address") == "4626  SAINT ELMO AVE"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "zipcode") == "38128"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "status") == "Open"

    def test_311_does_not_map_xy_or_closed_date_as_created(self):
        mapped = {c for cols in COMPLAINTS_311_FIELD_MAP.values() for c in cols}
        assert "X" not in mapped
        assert "Y" not in mapped
        assert "Closed_Date" not in mapped
        assert COMPLAINTS_311_FIELD_MAP["created_date"] == ["REPORTED_DATE"]
        assert "latitude" not in COMPLAINTS_311_FIELD_MAP
        assert "longitude" not in COMPLAINTS_311_FIELD_MAP

    def test_311_drops_pii_columns(self):
        mapped = {c for cols in COMPLAINTS_311_FIELD_MAP.values() for c in cols}
        for col in DROPPED_PII_COLUMNS:
            assert col not in mapped, col
        assert first_mapped(_311_FIXTURE, COMPLAINTS_311_FIELD_MAP, "incident_address") != "JANE DOE"

    def test_311_incident_id_skips_null_incident_id(self):
        assert first_mapped(_311_FIXTURE, COMPLAINTS_311_FIELD_MAP, "incident_id") == "8041445"


class TestGeocodingCaveats:
    def test_court_suffix_false_positives_connecticut(self):
        # Live permit streets often end in CT (Court). ``_STATE_RE`` treats
        # that token as Connecticut, so ADR-0004 will NOT append
        # geocode_context. Native WGS84 covers ~95% of rows; the 5% geocode
        # gap is the only path that sees this. Do not concatenate City/State
        # onto address_street (Honolulu Hawaii-word precedent).
        assert _STATE_RE.search("2218 OXFORD SQUARE CT".upper()) is not None
        assert _STATE_RE.search("2218 OXFORD SQUARE COURT, MEMPHIS, TN".upper()) is not None

    def test_311_street_has_no_state_token(self):
        assert _STATE_RE.search("4626  SAINT ELMO AVE".upper()) is None

    def test_full_word_tennessee_is_not_a_state_token(self):
        assert _STATE_RE.search("4626 SAINT ELMO AVE, MEMPHIS, TENNESSEE".upper()) is None
        assert _STATE_RE.search("4626 SAINT ELMO AVE, MEMPHIS, TN".upper()) is not None

    def test_unit_designator_normalization_preserves_city(self):
        norm = normalize_address("2218 OXFORD SQUARE COURT, MEMPHIS, TN")
        assert "MEMPHIS" in norm
        assert "TN" in norm


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


@pytest.fixture
def complaints():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        return Complaints311Producer()


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        return DOBPermitsProducer()


class TestMemphisPermitParsing:
    def test_native_wgs84_attributes_used_without_geocoder(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            return_value=(0.0, 0.0),
        ) as geocode:
            event = permits.parse_socrata_row(_PERMITS_FIXTURE, city_id="memphis")
        assert event is not None
        assert event.city_id == "memphis"
        assert event.job_id == "RES-ALT-26-000896"
        assert event.latitude == pytest.approx(35.032970528686185)
        assert event.longitude == pytest.approx(-89.99330263662729)
        assert event.address_street == "2218 OXFORD SQUARE CT"
        assert event.issuance_date is not None
        geocode.assert_not_called()

    def test_missing_coords_geocode_address_supplement(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        row = {
            k: v
            for k, v in _PERMITS_FIXTURE.items()
            if k not in {"Latitude", "Longitude", "latitude", "longitude"}
        }
        captured = []

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return (35.033, -90.025)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = permits.parse_socrata_row(row, city_id="memphis")
        assert event is not None
        assert event.latitude == pytest.approx(35.033)
        assert event.longitude == pytest.approx(-90.025)
        assert captured == [("memphis", "permits", "2218 OXFORD SQUARE CT", None)]

    def test_needs_geocode_is_pinned_true_as_supplement(self):
        spec = get_memphis_dataset(FeedType.PERMITS)
        assert spec.needs_geocode is True


class TestMemphis311Parsing:
    def test_outsr_geometry_used_not_xy(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            return_value=(0.0, 0.0),
        ) as geocode:
            event = complaints.parse_socrata_row(_311_FIXTURE, city_id="memphis")
        assert event is not None
        assert event.city_id == "memphis"
        assert event.incident_id == "8041445"
        assert event.complaint_type == "SWM-Missing Cart"
        assert event.incident_address == "4626  SAINT ELMO AVE"
        assert event.latitude == pytest.approx(35.23092537958096)
        assert event.longitude == pytest.approx(-89.90914790999382)
        geocode.assert_not_called()

    def test_state_plane_xy_are_not_emitted_as_degrees(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        captured = []

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return (35.0431, -89.8677)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = complaints.parse_socrata_row(_311_STATE_PLANE, city_id="memphis")
        assert event is not None
        assert event.latitude == pytest.approx(35.0431)
        assert event.longitude == pytest.approx(-89.8677)
        assert event.latitude != 270000.0
        assert event.longitude != 800000.0
        assert captured == [("memphis", "311", "123 TEST ST", None)]

    def test_pii_does_not_become_the_address(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints.parse_socrata_row(_311_FIXTURE, city_id="memphis")
        assert event is not None
        assert event.incident_address == "4626  SAINT ELMO AVE"
        assert "JANE DOE" not in (event.incident_address or "")
        assert "jane@example.com" not in (event.descriptor or "")

    def test_created_date_is_reported_not_closed(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        row = {
            **_311_FIXTURE,
            "Closed_Date": "2026-09-02T00:00:00+00:00",
            "RESOLVED_DATE": "2026-08-26T00:00:00+00:00",
        }
        event = complaints.parse_socrata_row(row, city_id="memphis")
        assert event is not None
        assert event.created_date is not None
        assert (event.created_date.year, event.created_date.month, event.created_date.day) == (
            2026,
            8,
            27,
        )
