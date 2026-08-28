"""Unit tests for the Yakima, WA leaf (US-239): spatial module + field maps
+ permit parse wiring.

Yakima is a ONE-FEED PARTIAL metro: Planning/BuildingPermits/FeatureServer/0
on ``gis.yakimawa.gov`` (city ArcGIS open data, Tier 1, daily-ish, native
outSR=4326 point geometry). YakBack 311 (verified live, native point, ~16,833
rows) stays Tier 3 because its integer ``status`` column drops every row in the
shared 311 producer (pydantic str reject, verified live 2026-08-28). County
sales layers are stale static extracts. Only ``permits`` is registered.

Tests pass WITHOUT a spine registration (no CityId.YAKIMA, no REGISTRY
assertions — "yakima" stays a plain string). Spine-stable per the wave-5 leaf
contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from FeatureServer/0 (newest rows
via ``orderByFields=IssuedOnDate DESC`` at ``outSR=4326``; newest watermark
1787270400000 = 2026-08-21T00:00:00+00:00, two co-newest rows). Fixtures are
RAW ArcGIS features (attributes + geometry); the tests run the real
``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO — before parsing, exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_yakima import (
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.yakima import (
    REGISTRATION,
    YAKIMA_CITY_ID,
    YAKIMA_DIVISION_BBOXES,
    YAKIMA_DIVISIONS,
    YAKIMA_FEED_SPECS,
    YAKIMA_GEOCODE_CONTEXT,
    YAKIMA_METRO_BBOX,
    YAKIMA_PERMITS_ENDPOINT,
    YAKIMA_SUBMARKETS,
    get_yakima_dataset,
    is_in_greater_yakima_metro,
    is_in_yakima_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten(feature):
    """Run the real ArcGIS flatten lift over a raw captured feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: SubmittedOnDate, IssuedOnDate, created_date, and
    last_edited_date are esriFieldTypeDate.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        feature, {"SubmittedOnDate", "IssuedOnDate", "created_date", "last_edited_date"}
    )


# Newest rows on the 2026-08-28 probe (orderByFields=IssuedOnDate DESC,
# outSR=4326) — two rows share the co-newest watermark; a third older row
# shows the 2022-10 -> now window. Byte-verbatim: padded/unpadded address
# columns, numeric epoch-millis dates, native WGS84 geometry.
_FEATURE_13469 = {
    "attributes": {
        "OBJECTID": 13469,
        "PermitID": "B260592",
        "PermitType": "BLD-RES-ADU",
        "PermitStatus": "ISSUED",
        "ProjectDescription": "Constructing a new accessory dwelling unit (ADU)",
        "SiteStreet": "7010 GREGORY PL",
        "SiteCity": "YAKIMA",
        "SiteState": "WA",
        "SiteZipCode": "98908",
        "SiteZone": "R-1",
        "SubmittedOnDate": 1782950400000,
        "IssuedOnDate": 1787270400000,
        "created_date": 1783267214000,
        "last_edited_date": 1787500815000,
        "DaysDifference": 50,
    },
    "geometry": {
        "x": -120.6023313730274,
        "y": 46.580513743920505,
    },
}

_FEATURE_16276 = {
    "attributes": {
        "OBJECTID": 16276,
        "PermitID": "B260780",
        "PermitType": "BLD-COM-ROOF",
        "PermitStatus": "ISSUED",
        "ProjectDescription": "remove existing tile roof and underlayment, install new ice and water shield underlayment and re-use existing and functional tile roofing material.",
        "SiteStreet": "1214 W CHESTNUT AVE",
        "SiteCity": "YAKIMA",
        "SiteState": "WA",
        "SiteZipCode": "98902",
        "SiteZone": "R-1",
        "SubmittedOnDate": 1787270400000,
        "IssuedOnDate": 1787270400000,
        "created_date": 1787500815000,
        "last_edited_date": 1787500815000,
        "DaysDifference": 0,
    },
    "geometry": {
        "x": -120.52639336375447,
        "y": 46.59575975249858,
    },
}

_FEATURE_988 = {
    "attributes": {
        "OBJECTID": 988,
        "PermitID": "B240818",
        "PermitType": "BLD-RES-DUP",
        "PermitStatus": "ISSUED",
        "ProjectDescription": "Demolishing existing garage and constructing new two-family dwelling",
        "SiteStreet": "1614 BONNIE DOON AVE #1-2",
        "SiteCity": "YAKIMA",
        "SiteState": "WA",
        "SiteZipCode": "98902",
        "SiteZone": "R-1",
        "SubmittedOnDate": 1727308800000,
        "IssuedOnDate": 1787184000000,
        "created_date": 1764615462000,
        "last_edited_date": 1787500815000,
        "DaysDifference": 693,
    },
    "geometry": {
        "x": -120.53167036356557,
        "y": 46.58679175157193,
    },
}

_ISSUANCE_ISO = "2026-08-21T00:00:00+00:00"


class TestYakimaSpatial:
    def test_metro_bbox_sanity(self):
        assert YAKIMA_METRO_BBOX["min_lat"] < YAKIMA_METRO_BBOX["max_lat"]
        assert YAKIMA_METRO_BBOX["min_lng"] < YAKIMA_METRO_BBOX["max_lng"]

    def test_is_in_yakima_metro_rejects_missing_coordinates(self):
        assert is_in_yakima_metro(None, None) is False
        assert is_in_yakima_metro(46.6021, None) is False
        assert is_in_yakima_metro(None, -120.5059) is False

    def test_is_in_yakima_metro_rejects_other_cities(self):
        assert is_in_yakima_metro(47.6062, -122.3321) is False   # Seattle
        assert is_in_yakima_metro(47.6588, -117.4260) is False   # Spokane
        assert is_in_yakima_metro(45.5152, -122.6784) is False   # Portland
        assert is_in_yakima_metro(46.7310, -117.1797) is False   # Pullman (far east)

    def test_downtown_anchors_are_contained(self):
        assert is_in_yakima_metro(46.6021, -120.5059)  # City Hall / Downtown
        assert is_in_yakima_metro(46.5850, -120.6300)  # West Valley
        assert is_in_yakima_metro(46.6060, -120.4470)  # Terrace Heights

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_13469, _FEATURE_16276, _FEATURE_988):
            assert is_in_yakima_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in YAKIMA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= YAKIMA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= YAKIMA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= YAKIMA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= YAKIMA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in YAKIMA_SUBMARKETS.items():
            bbox = YAKIMA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in YAKIMA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(YAKIMA_SUBMARKETS)

    def test_submarkets_carry_the_yakima_city_id(self):
        assert {m.city_id for m in YAKIMA_SUBMARKETS.values()} == {"yakima"}

    def test_city_id_and_registration_shape(self):
        assert YAKIMA_CITY_ID == "yakima"
        assert REGISTRATION.metro_bbox is YAKIMA_METRO_BBOX
        assert REGISTRATION.submarkets is YAKIMA_SUBMARKETS
        assert REGISTRATION.division_bboxes is YAKIMA_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_yakima_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(YAKIMA_SUBMARKETS) == 9

    def test_required_real_neighborhoods_present(self):
        assert set(YAKIMA_SUBMARKETS) == {
            "Downtown",
            "Nob Hill",
            "North Yakima",
            "Summitview",
            "West Valley",
            "South 16th",
            "South Yakima",
            "Terrace Heights",
            "East Valley",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_yakima_metro is is_in_yakima_metro


class TestYakimaFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["PermitID", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["IssuedOnDate"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["SubmittedOnDate"]
        assert PERMITS_FIELD_MAP["status"] == ["PermitStatus"]
        assert PERMITS_FIELD_MAP["job_type"] == ["PermitType"]
        assert PERMITS_FIELD_MAP["address_street"] == ["SiteStreet"]
        assert PERMITS_FIELD_MAP["zipcode"] == ["SiteZipCode"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Yakima, WA"
        assert YAKIMA_GEOCODE_CONTEXT == "Yakima, WA"

    def test_native_geometry_means_latitude_longitude_are_never_candidates(self):
        """Coordinates come from the outSR=4326 geometry lift, not attributes.
        There are no State Plane X_COORD/Y_COORD feet columns on this layer,
        so unlike Greenville, there is no projected-coordinate trap.
        """
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        attrs = _FEATURE_13469["attributes"]
        # All values are small enough that the projected-coordinate guard
        # (abs > 90) would NOT fire — but the geometry lift is the sole
        # source, so the guard is an honest redundant net.
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "latitude") is None
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "longitude") is None

    def test_no_borough_candidate_so_source_neighborhood_passes_none(self):
        assert "borough" not in PERMITS_FIELD_MAP
        assert "neighborhood" not in PERMITS_FIELD_MAP

    def test_no_cost_column_so_cost_stays_unmapped(self):
        assert "cost" not in PERMITS_FIELD_MAP

    def test_no_bbl_or_units_columns(self):
        assert "bbl" not in PERMITS_FIELD_MAP
        assert "proposed_units" not in PERMITS_FIELD_MAP
        assert "existing_units" not in PERMITS_FIELD_MAP

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for values in PERMITS_FIELD_MAP.values() for c in values}
        assert mapped
        for values in PERMITS_FIELD_MAP.values():
            for col in values:
                assert col not in DROPPED_PII_COLUMNS
        # The YakBack PII block is what is dropped.
        assert {"name", "email", "phone", "GlobalID"} <= set(DROPPED_PII_COLUMNS)


class TestYakimaPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_FEATURE_13469)
        assert record["latitude"] == pytest.approx(46.580513743920505)
        assert record["longitude"] == pytest.approx(-120.6023313730274)

    def test_flatten_iso_normalizes_dates_only(self):
        record = _flatten(_FEATURE_16276)
        assert record["IssuedOnDate"] == _ISSUANCE_ISO
        assert record["SubmittedOnDate"] == _ISSUANCE_ISO
        # OBJECTID is not a date field and stays untouched.
        assert record["OBJECTID"] == 16276
        # DaysDifference is an integer, not a date.
        assert record["DaysDifference"] == 0

    def test_adu_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_13469), city_id="yakima")
        assert event is not None
        assert event.city_id == "yakima"
        assert event.job_id == "B260592"
        assert event.status == "ISSUED"
        assert event.estimated_cost == pytest.approx(0.0)
        assert event.address_street == "7010 GREGORY PL"
        assert event.latitude == pytest.approx(46.580513743920505)
        assert event.longitude == pytest.approx(-120.6023313730274)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _ISSUANCE_ISO
        assert event.filing_date is not None
        assert event.filing_date.isoformat() == "2026-07-02T00:00:00+00:00"
        assert event.source_neighborhood is None
        assert event.zipcode == "98908"
        assert event.bbl is None

    def test_roof_fixture_indexes_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_16276), city_id="yakima")
        assert event is not None
        assert event.estimated_cost == pytest.approx(0.0)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_yakima_metro(event.latitude, event.longitude)

    def test_duplex_fixture_valuation_and_containment(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_988), city_id="yakima")
        assert event is not None
        assert event.job_id == "B240818"
        assert event.estimated_cost == pytest.approx(0.0)
        assert event.address_street == "1614 BONNIE DOON AVE #1-2"
        assert is_in_yakima_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_share_the_co_newest_watermark(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        events = [
            permits.parse_socrata_row(_flatten(f), city_id="yakima")
            for f in (_FEATURE_13469, _FEATURE_16276, _FEATURE_988)
        ]
        assert all(e is not None for e in events)
        issuances = {e.issuance_date.isoformat() for e in events}
        assert _ISSUANCE_ISO in issuances
        # Distinct permits occupy distinct res-9 cells.
        assert len({e.h3_res9 for e in events}) == 3

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_13469)
        record.pop("PermitID")
        event = permits.parse_socrata_row(record, city_id="yakima")
        assert event is not None
        assert event.job_id == "13469"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_13469)
        record.pop("PermitID")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="yakima") is None

    def test_geometry_less_row_resolves_through_the_geocode_fallback(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_13469)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (46.6021, -120.5059),
        )
        event = permits.parse_socrata_row(record, city_id="yakima")
        assert event is not None
        assert event.city_id == "yakima"
        assert event.job_id == "B260592"
        assert event.latitude == pytest.approx(46.6021)
        assert event.longitude == pytest.approx(-120.5059)
        assert event.h3_res7 is not None

    def test_geometry_less_row_dropped_when_geocode_fails(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_16276)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="yakima") is None

    def test_yakima_type_codes_stay_unclassified_at_the_leaf(
        self, permits, monkeypatch
    ):
        """PermitType codes (BLD-RES-ADU, BLD-COM-ROOF, BLD-RES-DUP) pass
        through as job_type candidates; they are not among the producer's
        recognized codes, so they land on OT honestly."""
        _patch_resolve(monkeypatch, "permits")
        for fixture in (_FEATURE_13469, _FEATURE_16276, _FEATURE_988):
            event = permits.parse_socrata_row(_flatten(fixture), city_id="yakima")
            assert event is not None
            assert event.job_type == JobType.OT


class TestYakimaFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_yakima_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == YAKIMA_PERMITS_ENDPOINT
        assert spec.watermark_col == "IssuedOnDate"
        assert spec.id_keys == ["PermitID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 14
        assert spec.order_by == "IssuedOnDate DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Yakima, WA"
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_registered_feed_set_is_permits_only(self):
        assert set(YAKIMA_FEED_SPECS) == {"permits"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_yakima_dataset("sla")
        assert "yakima" in str(exc.value)
        assert "permits" in str(exc.value)

    def test_endpoint_is_the_probed_featureserver(self):
        assert "gis.yakimawa.gov" in YAKIMA_PERMITS_ENDPOINT
        assert "Planning/BuildingPermits/FeatureServer/0" in YAKIMA_PERMITS_ENDPOINT