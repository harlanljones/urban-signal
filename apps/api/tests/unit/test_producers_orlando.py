"""Unit tests for the Orlando leaf (US-194): spatial module + SLA field maps.

Orlando is a PARTIAL metro: Business Tax Receipts (primary SLA) and Short Term
Rental Licenses (SLA companion). PERMITS ``ryhf-m453`` is live but out of
ticket scope. Tests pass WITHOUT a spine registration (no CityId.ORLANDO).

Live fixtures captured 2026-08-27 from data.cityoforlando.net.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_orlando import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
    STR_SLA_FIELD_MAP,
)
from src.spatial.cities.orlando import (
    ORLANDO_BTR_ENDPOINT,
    ORLANDO_CITY_ID,
    ORLANDO_DIVISION_BBOXES,
    ORLANDO_DIVISIONS,
    ORLANDO_FEED_SPECS,
    ORLANDO_GEOCODE_CONTEXT,
    ORLANDO_METRO_BBOX,
    ORLANDO_STR_ENDPOINT,
    ORLANDO_STR_SLA_SPEC,
    ORLANDO_SUBMARKETS,
    get_orlando_dataset,
    is_in_orlando_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address


# Live BTR row: newest received_date with a real street (not "DESIRED CITY LICENSE").
# Probed 2026-08-27. No geocoded_column on the live window.
BTR_ROW = {
    "case_number": "BUS-1125042",
    "business_name": "LAMIRA JOIAS E PIERCING LLC",
    "business_address": "5438 INTERNATIONAL DR  SUITE B, ORLANDO, FL",
    "business_owner_name": "LAMIRA JOIAS E PIERCING LLC",
    "license_status": "Open",
    "license_type": "BODY PIERCING",
    "license_category": "SERREP",
    "received_date": "2026-08-26T00:00:00.000",
    "gpsx": "510560.80434167",
    "gpsy": "1500990.67555001",
    "neighborhood_name": "Florida Center",
}

# Live STR row: newest issued_date IS NOT NULL. Address is street-only.
STR_ROW = {
    "license_number": "STR-1116182",
    "last_action_date": "2026-08-25T00:00:00.000",
    "license_holder_name": "ROSENA USMANI",
    "property_address": "2219 AMHERST AVE",
    "property_detail": " ",
    "license_date": "2025-04-23T00:00:00.000",
    "issued_date": "2026-08-25T00:00:00.000",
    "expire_date": "2028-07-10T00:00:00.000",
    "license_status": "Active",
    "next_renew_date": "2028-07-10T00:00:00.000",
    "license_milestone": "Waiting for Renewal",
    "property_owner_name1": "USMANI ROSENA",
    "property_owner_city": "ORLANDO",
    "property_owner_state": "FL",
    "property_owner_zip": "32804",
    "last_modify_date": "2026-08-25T00:00:00.000",
}

# Approximate WGS84 for the I-Drive / College Park fixtures (geocoder stub).
BTR_GEOCODE = (28.460, -81.467)
STR_GEOCODE = (28.575, -81.389)


class TestOrlandoSpatial:
    def test_city_id_constant(self):
        assert ORLANDO_CITY_ID == "orlando"

    def test_metro_contains_downtown(self):
        assert is_in_orlando_metro(28.5383, -81.3792) is True

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_orlando_metro(None, None) is False
        assert is_in_orlando_metro(27.948, -82.458) is False  # Tampa
        assert is_in_orlando_metro(25.7617, -80.1918) is False  # Miami

    def test_live_samples_sit_inside_the_metro_bbox(self):
        assert is_in_orlando_metro(*BTR_GEOCODE)
        assert is_in_orlando_metro(*STR_GEOCODE)
        assert is_in_orlando_metro(28.368, -81.275)  # Lake Nona
        assert is_in_orlando_metro(28.570, -81.325)  # Baldwin Park

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in ORLANDO_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ORLANDO_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ORLANDO_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ORLANDO_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ORLANDO_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in ORLANDO_SUBMARKETS.items():
            bbox = ORLANDO_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in ORLANDO_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ORLANDO_SUBMARKETS)

    def test_submarkets_carry_orlando_city_id(self):
        assert {m.city_id for m in ORLANDO_SUBMARKETS.values()} == {"orlando"}

    def test_division_count(self):
        assert len(ORLANDO_DIVISIONS) == 6
        for div in ORLANDO_DIVISIONS.values():
            assert div.city_id == "orlando"


class TestFeedRegistration:
    def test_exactly_one_feed_type_is_registered(self):
        assert set(ORLANDO_FEED_SPECS) == {"sla"}

    def test_sla_spec_matches_live_btr(self):
        spec = get_orlando_dataset(FeedType.SLA)
        assert spec.platform == "socrata"
        assert spec.endpoint == ORLANDO_BTR_ENDPOINT
        assert spec.watermark_col == "received_date"
        assert spec.id_keys == ["case_number"]
        assert spec.producer_key == "sla"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Orlando, FL"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.companion_endpoints["str_licenses"] == ORLANDO_STR_ENDPOINT

    def test_str_companion_spec_is_also_sla(self):
        extra = ORLANDO_STR_SLA_SPEC["extra"]
        assert ORLANDO_STR_SLA_SPEC["producer_key"] == "sla"
        assert ORLANDO_STR_SLA_SPEC["endpoint"] == ORLANDO_STR_ENDPOINT
        assert extra["needs_geocode"] is True
        assert extra["geocode_context"] == "Orlando, FL"
        assert extra["field_map"] is STR_SLA_FIELD_MAP

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.DEEDS, FeedType.STR],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'orlando'.*available"):
            get_orlando_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert FIELD_MAP["sla_str"] is STR_SLA_FIELD_MAP
        assert GEOCODE_CONTEXT == ORLANDO_GEOCODE_CONTEXT == "Orlando, FL"


class TestOrlandoFieldMaps:
    def test_btr_map_reads_live_columns(self):
        assert first_mapped(BTR_ROW, SLA_FIELD_MAP, "license_id") == "BUS-1125042"
        assert first_mapped(BTR_ROW, SLA_FIELD_MAP, "license_type") == "BODY PIERCING"
        assert first_mapped(BTR_ROW, SLA_FIELD_MAP, "premises_name") == "LAMIRA JOIAS E PIERCING LLC"
        assert (
            first_mapped(BTR_ROW, SLA_FIELD_MAP, "address_street")
            == "5438 INTERNATIONAL DR  SUITE B, ORLANDO, FL"
        )
        assert first_mapped(BTR_ROW, SLA_FIELD_MAP, "status") == "Open"
        assert first_mapped(BTR_ROW, SLA_FIELD_MAP, "borough") == "Florida Center"

    def test_btr_live_window_has_no_usable_coordinates(self):
        assert first_mapped(BTR_ROW, SLA_FIELD_MAP, "latitude") is None
        assert first_mapped(BTR_ROW, SLA_FIELD_MAP, "longitude") is None
        # State-plane feet must not be treated as WGS84.
        assert "gpsx" not in {c for cols in SLA_FIELD_MAP.values() for c in cols}
        assert "gpsy" not in {c for cols in SLA_FIELD_MAP.values() for c in cols}

    def test_str_map_reads_live_columns(self):
        assert first_mapped(STR_ROW, STR_SLA_FIELD_MAP, "license_id") == "STR-1116182"
        assert first_mapped(STR_ROW, STR_SLA_FIELD_MAP, "address_street") == "2219 AMHERST AVE"
        assert first_mapped(STR_ROW, STR_SLA_FIELD_MAP, "effective_date") == "2026-08-25T00:00:00.000"
        assert first_mapped(STR_ROW, STR_SLA_FIELD_MAP, "expiration_date") == "2028-07-10T00:00:00.000"
        assert first_mapped(STR_ROW, STR_SLA_FIELD_MAP, "status") == "Active"
        assert first_mapped(STR_ROW, STR_SLA_FIELD_MAP, "zipcode") == "32804"


class TestGeocodingCaveats:
    def test_btr_address_already_carrying_fl_is_not_double_contexted(self):
        assert _STATE_RE.search("5438 INTERNATIONAL DR, ORLANDO, FL".upper()) is not None

    def test_str_street_only_address_accepts_context(self):
        assert _STATE_RE.search("2219 AMHERST AVE".upper()) is None

    def test_unit_designator_normalization_preserves_city(self):
        # SUITE B is dropped in place. ``FL`` is also in the geocoder's unit
        # token set (FLOOR), so the state abbreviation is stripped from
        # Florida addresses during normalize — a live-window caveat. Raw
        # BTR strings still match ``_STATE_RE``, so geocode_context is NOT
        # appended even though the normalized query has lost ``FL``.
        norm = normalize_address("5438 INTERNATIONAL DR SUITE B, ORLANDO, FL")
        assert "SUITE" not in norm
        assert "ORLANDO" in norm
        assert "FL" not in norm


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


class TestOrlandoBtrParsing:
    def test_address_only_btr_uses_declared_geocoder(self, sla, monkeypatch):
        captured = []

        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: SLA_FIELD_MAP,
        )

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return BTR_GEOCODE

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = sla.parse_socrata_row(BTR_ROW, city_id="orlando")
        assert event is not None
        assert event.city_id == "orlando"
        assert event.license_id == "BUS-1125042"
        assert event.license_type == "BODY PIERCING"
        assert event.license_status == "Open"
        assert event.address == "5438 INTERNATIONAL DR  SUITE B, ORLANDO, FL"
        assert event.latitude == pytest.approx(BTR_GEOCODE[0])
        assert event.longitude == pytest.approx(BTR_GEOCODE[1])
        assert event.h3_res7 is not None
        assert captured == [
            (
                "orlando",
                "sla",
                "5438 INTERNATIONAL DR  SUITE B, ORLANDO, FL",
                None,
            )
        ]

    def test_btr_live_fixture_geocode_is_inside_metro(self):
        assert is_in_orlando_metro(*BTR_GEOCODE)


class TestOrlandoStrParsing:
    def test_address_only_str_parses_as_sla(self, sla, monkeypatch):
        captured = []

        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: STR_SLA_FIELD_MAP,
        )

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return STR_GEOCODE

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = sla.parse_socrata_row(STR_ROW, city_id="orlando")
        assert event is not None
        assert event.city_id == "orlando"
        assert event.license_id == "STR-1116182"
        assert event.address == "2219 AMHERST AVE"
        assert str(event.effective_date).startswith("2026-08-25")
        assert str(event.expiration_date).startswith("2028-07-10")
        assert event.license_status == "Active"
        assert event.latitude == pytest.approx(STR_GEOCODE[0])
        assert event.longitude == pytest.approx(STR_GEOCODE[1])
        assert captured == [("orlando", "sla", "2219 AMHERST AVE", None)]

    def test_str_is_not_a_new_feed_type(self):
        """STR licenses stay on producer_key=sla; FeedType.STR is unused here."""
        assert ORLANDO_STR_SLA_SPEC["producer_key"] == "sla"
        assert "str" not in ORLANDO_FEED_SPECS

    def test_str_live_fixture_geocode_is_inside_metro(self):
        assert is_in_orlando_metro(*STR_GEOCODE)
