"""Unit tests for the Syracuse, NY leaf (US-352): spatial module + field maps
+ producer parse wiring.

Syracuse is a ONE-FEED PARTIAL metro: the Syracuse Rental Registry
(`Syracuse_Rental_Registry/FeatureServer/0` on services6.arcgis.com, Tier 1,
native WGS84 Latitude/Longitude). Permits are frozen (2025-08-16 max), 311
and deeds are absent — nothing else is registered.

Tests pass WITHOUT a spine registration (no CityId.SYRACUSE, no REGISTRY
assertions — "syracuse" stays a plain string). Division/borough resolution
and geocode-hook behavior are deliberately NOT asserted: both change when
the spine lands. Parse fields, field-map mappings, H3 from fixture coords,
and bbox containment are the pinned surface.

Live fixtures captured byte-verbatim 2026-08-27 from
services6.arcgis.com/bdPqSfflsdgFRVVM (Rental Registry, newest by
RR_app_received + newest RRisValid='Yes'), dates ISO-normalized the way
ArcGISClient._flatten_feature delivers them (epoch-ms -> ISO 8601 UTC;
the ESRI null-date placeholder -2208902400000 reads 1900-01-02).
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_syracuse import (
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    SYRACUSE_SLA_FIELD_MAP,
)
from src.spatial.cities.syracuse import (
    SYRACUSE_CITY_ID,
    SYRACUSE_DIVISIONS,
    SYRACUSE_DIVISION_BBOXES,
    SYRACUSE_FEED_SPECS,
    SYRACUSE_METRO_BBOX,
    SYRACUSE_SLA_ENDPOINT,
    SYRACUSE_SUBMARKETS,
    REGISTRATION,
    get_syracuse_dataset,
    is_in_syracuse_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


# Newest row by RR_app_received on the 2026-08-27 re-probe (ObjectId 1424):
# a fresh Park St application — RRisValid 'No', completion fields at the
# ESRI null-date placeholder, native coordinates. PII columns included
# verbatim to pin the drop-at-map discipline.
_SLA_FRESH_PARK_ST = {
    "SBL": "007.-30-21.0",
    "PropertyAddress": "1217 Park St",
    "zip": 13208,
    "NeedsRR": "Yes",
    "inspect_period": "2026-08-17T00:00:00+00:00",
    "completion_type_name": None,
    "completion_date": "1900-01-02T00:00:00+00:00",
    "valid_until": "1900-01-02T00:00:00+00:00",
    "RRisValid": "No",
    "RR_app_received": "2026-08-26T00:00:00+00:00",
    "RR_ext_insp_pass": None,
    "RR_ext_insp_fail": None,
    "RR_int_insp_fail": None,
    "RR_int_insp_pass": None,
    "RR_contact_name": "Bich Thuy Tran",
    "pc_owner": "Bich Thuy Tran",
    "Latitude": 43.06616901,
    "Longitude": -76.1528129,
    "SHAPE": None,
    "ObjectId": 1424,
}

# Co-newest fresh application (ObjectId 5427), Outer Comstock belt —
# pins the 905 Comstock Ave sample from the probe.
_SLA_FRESH_COMSTOCK = {
    "SBL": "052.-13-36.0",
    "PropertyAddress": "905 Comstock Ave",
    "zip": 13210,
    "NeedsRR": "Yes",
    "inspect_period": "2026-09-03T00:00:00+00:00",
    "completion_type_name": None,
    "completion_date": "1900-01-02T00:00:00+00:00",
    "valid_until": "1900-01-02T00:00:00+00:00",
    "RRisValid": "No",
    "RR_app_received": "2026-08-26T00:00:00+00:00",
    "RR_ext_insp_pass": None,
    "RR_ext_insp_fail": None,
    "RR_int_insp_fail": None,
    "RR_int_insp_pass": None,
    "RR_contact_name": "Daina Mattis",
    "pc_owner": "Daina Mattis",
    "Latitude": 43.03355107,
    "Longitude": -76.12907112,
    "SHAPE": None,
    "ObjectId": 5427,
}

# Newest granted card (ObjectId 2854): completion_type_name carries the
# license-type grain, valid_until a real 2029 expiry.
_SLA_VALID_BURNS = {
    "SBL": "025.-11-07.0",
    "PropertyAddress": "154 Burns Ave",
    "zip": 13206,
    "NeedsRR": "Yes",
    "inspect_period": "2026-08-12T00:00:00+00:00",
    "completion_type_name": "Rental Registry Card Issued",
    "completion_date": "2026-08-12T00:00:00+00:00",
    "valid_until": "2029-08-12T00:00:00+00:00",
    "RRisValid": "Yes",
    "RR_app_received": "2026-08-07T00:00:00+00:00",
    "RR_ext_insp_pass": "2026-08-12T00:00:00+00:00",
    "RR_ext_insp_fail": None,
    "RR_int_insp_fail": None,
    "RR_int_insp_pass": "2026-08-12T00:00:00+00:00",
    "RR_contact_name": "OIP 154 Burns, LLC",
    "pc_owner": "OIP 154 Burns, LLC",
    "Latitude": 43.06739191,
    "Longitude": -76.09225587,
    "SHAPE": None,
    "ObjectId": 2854,
}

# Second granted card (ObjectId 6609): the exemption completion type.
_SLA_VALID_RAYMOND = {
    "SBL": "075.-04-04.0",
    "PropertyAddress": "107 Raymond Ave",
    "zip": 13205,
    "NeedsRR": "Yes",
    "inspect_period": "2026-08-07T00:00:00+00:00",
    "completion_type_name": "Family Based Exemption Granted",
    "completion_date": "2026-08-07T00:00:00+00:00",
    "valid_until": "2029-08-07T00:00:00+00:00",
    "RRisValid": "Yes",
    "RR_app_received": "2026-08-07T00:00:00+00:00",
    "RR_ext_insp_pass": None,
    "RR_ext_insp_fail": None,
    "RR_int_insp_fail": None,
    "RR_int_insp_pass": None,
    "RR_contact_name": "Kimani Smith, Kimani Smith, Kimani Smith",
    "pc_owner": "Kimani Smith",
    "Latitude": 43.01734838,
    "Longitude": -76.15488205,
    "SHAPE": None,
    "ObjectId": 6609,
}


class TestSyracuseSpatial:
    def test_metro_bbox_sanity(self):
        assert SYRACUSE_METRO_BBOX["min_lat"] < SYRACUSE_METRO_BBOX["max_lat"]
        assert SYRACUSE_METRO_BBOX["min_lng"] < SYRACUSE_METRO_BBOX["max_lng"]

    def test_is_in_syracuse_metro_rejects_missing_coordinates(self):
        assert is_in_syracuse_metro(None, None) is False

    def test_is_in_syracuse_metro_rejects_other_cities(self):
        assert is_in_syracuse_metro(43.1566, -77.6111) is False   # Rochester
        assert is_in_syracuse_metro(42.8864, -78.8784) is False   # Buffalo
        assert is_in_syracuse_metro(40.7128, -74.0060) is False   # NYC
        assert is_in_syracuse_metro(43.0481, -76.1340) is True    # SU hill

    def test_live_fixture_coordinates_are_contained(self):
        assert is_in_syracuse_metro(43.06616901, -76.1528129)
        assert is_in_syracuse_metro(43.03355107, -76.12907112)
        assert is_in_syracuse_metro(43.06739191, -76.09225587)
        assert is_in_syracuse_metro(43.01734838, -76.15488205)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in SYRACUSE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= SYRACUSE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= SYRACUSE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= SYRACUSE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= SYRACUSE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in SYRACUSE_SUBMARKETS.items():
            bbox = SYRACUSE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in SYRACUSE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(SYRACUSE_SUBMARKETS)

    def test_submarkets_carry_the_syracuse_city_id(self):
        assert {m.city_id for m in SYRACUSE_SUBMARKETS.values()} == {"syracuse"}

    def test_city_id_and_registration_shape(self):
        assert SYRACUSE_CITY_ID == "syracuse"
        assert REGISTRATION.metro_bbox is SYRACUSE_METRO_BBOX
        assert REGISTRATION.submarkets is SYRACUSE_SUBMARKETS
        assert len(REGISTRATION.divisions) == 6
        assert len(SYRACUSE_SUBMARKETS) == 8

    def test_required_real_neighborhoods_present(self):
        assert set(SYRACUSE_SUBMARKETS) == {
            "Downtown",
            "Armory Square",
            "University Area",
            "Westcott",
            "Eastwood",
            "Strathmore",
            "North Side",
            "Outer Comstock",
        }


class TestSyracuseFieldMaps:
    def test_sla_map_reads_live_columns(self):
        assert SYRACUSE_SLA_FIELD_MAP["license_id"] == ["SBL"]
        assert SYRACUSE_SLA_FIELD_MAP["effective_date"] == ["RR_app_received"]
        assert SYRACUSE_SLA_FIELD_MAP["expiration_date"] == ["valid_until"]
        assert SYRACUSE_SLA_FIELD_MAP["status"] == ["RRisValid"]
        assert SYRACUSE_SLA_FIELD_MAP["address_street"] == ["PropertyAddress"]

    def test_sla_map_reads_capitalized_native_coordinates(self):
        """The generic chains only read lowercase latitude/longitude keys;
        the live layer's columns are capitalized, so the map is what makes
        native coordinates reach the parser."""
        assert SYRACUSE_SLA_FIELD_MAP["latitude"] == ["Latitude"]
        assert SYRACUSE_SLA_FIELD_MAP["longitude"] == ["Longitude"]
        row = {"Latitude": 43.03355107, "Longitude": -76.12907112}
        assert first_mapped(row, SYRACUSE_SLA_FIELD_MAP, "latitude") == 43.03355107
        assert first_mapped(row, SYRACUSE_SLA_FIELD_MAP, "longitude") == -76.12907112

    def test_license_type_falls_to_needsrr_on_fresh_applications(self):
        row = {"completion_type_name": None, "NeedsRR": "Yes"}
        assert first_mapped(row, SYRACUSE_SLA_FIELD_MAP, "license_type") == "Yes"

    def test_license_type_reads_completion_type_when_granted(self):
        row = {
            "completion_type_name": "Rental Registry Card Issued",
            "NeedsRR": "Yes",
        }
        assert (
            first_mapped(row, SYRACUSE_SLA_FIELD_MAP, "license_type")
            == "Rental Registry Card Issued"
        )

    def test_pii_columns_never_become_candidates(self):
        for values in SYRACUSE_SLA_FIELD_MAP.values():
            for col in values:
                assert col not in DROPPED_PII_COLUMNS
        assert DROPPED_PII_COLUMNS == ("RR_contact_name", "pc_owner")

    def test_map_is_non_empty_and_sla_only(self):
        assert set(FIELD_MAP) == {"sla"}
        assert FIELD_MAP["sla"] is SYRACUSE_SLA_FIELD_MAP


class TestSyracuseSlaParsing:
    """The Rental Registry carries native coordinates, so rows parse without
    the geocode hook. The hook is patched to a no-op so no test can touch
    the network; call counts are deliberately not asserted (spine-stable)."""

    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    @pytest.fixture(autouse=True)
    def _no_geocode(self, monkeypatch):
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )

    def test_fresh_application_parses_all_pinned_fields(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_FRESH_PARK_ST, city_id="syracuse")
        assert event is not None
        assert event.city_id == "syracuse"
        assert event.license_id == "007.-30-21.0"
        assert event.license_type == "Yes"
        assert event.address == "1217 Park St"
        assert event.license_status == "No"
        assert event.effective_date is not None
        assert event.effective_date.year == 2026
        assert event.effective_date.month == 8
        assert event.effective_date.day == 26

    def test_fresh_application_resolves_native_coordinates(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_FRESH_PARK_ST, city_id="syracuse")
        assert event is not None
        assert event.latitude == pytest.approx(43.06616901)
        assert event.longitude == pytest.approx(-76.1528129)
        assert event.h3_res7 is not None
        assert event.h3_res9 is not None

    def test_second_fresh_fixture_h3_and_bbox(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_FRESH_COMSTOCK, city_id="syracuse")
        assert event is not None
        assert event.license_id == "052.-13-36.0"
        assert event.latitude == pytest.approx(43.03355107)
        assert event.longitude == pytest.approx(-76.12907112)
        assert event.h3_res7 is not None
        assert is_in_syracuse_metro(event.latitude, event.longitude)

    def test_granted_card_maps_completion_type_and_valid_until(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_VALID_BURNS, city_id="syracuse")
        assert event is not None
        assert event.license_id == "025.-11-07.0"
        assert event.license_type == "Rental Registry Card Issued"
        assert event.license_status == "Yes"
        assert event.effective_date is not None and event.effective_date.year == 2026
        assert event.expiration_date is not None and event.expiration_date.year == 2029
        assert event.expiration_date.month == 8 and event.expiration_date.day == 12
        assert is_in_syracuse_metro(event.latitude, event.longitude)

    def test_second_granted_fixture_maps_all_fields(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_VALID_RAYMOND, city_id="syracuse")
        assert event is not None
        assert event.license_type == "Family Based Exemption Granted"
        assert event.expiration_date is not None and event.expiration_date.year == 2029
        assert event.latitude == pytest.approx(43.01734838)
        assert event.longitude == pytest.approx(-76.15488205)
        assert event.h3_res9 is not None

    def test_source_neighborhood_is_none_no_neighborhood_column(self, sla, monkeypatch):
        """The layer ships no neighborhood column; source_neighborhood stays
        None and stays None after the spine lands (borough resolution is
        coordinate-derived and is deliberately not asserted here)."""
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_FRESH_PARK_ST, city_id="syracuse")
        assert event is not None
        assert event.source_neighborhood is None

    def test_pii_never_reaches_the_event(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_SLA_FRESH_PARK_ST, city_id="syracuse")
        assert event is not None
        dumped = event.model_dump() if hasattr(event, "model_dump") else event.__dict__
        for value in dumped.values():
            assert value not in ("Bich Thuy Tran", "OIP 154 Burns, LLC")

    def test_coordinate_less_row_stays_null_coord_event(self, sla, monkeypatch):
        """needs_geocode is False (native coords 500/500 on the probe), so a
        coordinate-less row keeps DC-precedent null-lat/lng / null-H3 shape
        instead of dropping."""
        _patch_resolve(monkeypatch, "sla")
        row = {
            k: v
            for k, v in _SLA_FRESH_PARK_ST.items()
            if k not in {"Latitude", "Longitude", "SHAPE"}
        }
        event = sla.parse_socrata_row(row, city_id="syracuse")
        assert event is not None
        assert event.latitude is None
        assert event.longitude is None
        assert event.h3_res7 is None and event.h3_res9 is None
        assert event.license_id == "007.-30-21.0"

    def test_sla_spec_matches_live_layer(self):
        spec = get_syracuse_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == SYRACUSE_SLA_ENDPOINT
        assert spec.watermark_col == "RR_app_received"
        assert spec.id_keys == ["SBL"]
        assert spec.producer_key == "sla"
        assert spec.oid_field == "ObjectId"
        assert spec.max_record_count == 1000
        assert spec.order_by == "RR_app_received DESC"
        assert spec.expected_cadence_days == 1
        assert spec.needs_geocode is False
        assert spec.ingestion_mode == "incremental"
        assert spec.field_map["license_id"] == ["SBL"]
        assert spec.field_map["latitude"] == ["Latitude"]


class TestLeafFeedSpecContract:
    def test_registered_feed_set(self):
        assert set(SYRACUSE_FEED_SPECS) == {"sla"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_syracuse_dataset("311")
        assert "syracuse" in str(exc.value)
        assert "sla" in str(exc.value)

    def test_endpoint_host_is_the_probed_one(self):
        sla = SYRACUSE_FEED_SPECS["sla"]
        assert "services6.arcgis.com/bdPqSfflsdgFRVVM" in sla["endpoint"]
        assert "Syracuse_Rental_Registry/FeatureServer/0" in sla["endpoint"]
