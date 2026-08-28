"""Unit tests for the Glendale, AZ leaf (US-250): spatial module + field
maps + producer parse wiring.

Glendale is a TWO-FEED PARTIAL metro on the City of Glendale ArcGIS Server
11.4 (``gismaps.glendaleaz.com/gisserver``): COMPLAINTS_311
(``OpenData/GLENDALEONE_EXTERNAL_REQUESTS_PTS`` MapServer/0, ~107k rows,
native WGS84 point geometry) and SLA (``OpenData/Business_Licenses``
MapServer/1 table, ~9.9k rows, address-only). PERMITS and DEEDS are absent
(SmartGov token-protected; Maricopa County deeds need CSVClient + scheduler
spine gap).

Tests pass WITHOUT a spine registration (no CityId.GLENDALE_AZ, no REGISTRY
assertions — "glendale_az" stays a plain string). Spine-stable per the leaf
contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from MapServer/0 (311) and
MapServer/1 (SLA). 311 fixtures are RAW ArcGIS features (attributes +
geometry); the test runs the real ``ArcGISClient._flatten_feature`` lift —
geometry to latitude/longitude, epoch-ms to ISO — before parsing. SLA
fixtures are table rows (no geometry) with DateOnly string dates.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps_glendale_az import (
    COMPLAINTS_311_FIELD_MAP,
    DROPPED_NONADDRESS_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.spatial.cities.glendale_az import (
    GLENDALE_AZ_311_ENDPOINT,
    GLENDALE_AZ_CITY_ID,
    GLENDALE_AZ_DIVISION_BBOXES,
    GLENDALE_AZ_DIVISIONS,
    GLENDALE_AZ_FEED_SPECS,
    GLENDALE_AZ_GEOCODE_CONTEXT,
    GLENDALE_AZ_METRO_BBOX,
    GLENDALE_AZ_SLA_ENDPOINT,
    GLENDALE_AZ_SUBMARKETS,
    REGISTRATION,
    get_glendale_az_dataset,
    is_in_glendale_az_metro,
    is_in_greater_glendale_az_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten_311(feature):
    """Run the real ArcGIS flatten lift over a raw 311 captured feature.

    Date fields discovered from the live layer's metadata: Request_Date,
    Last_Action_Date, Close_Date, DateLoaded are esriFieldTypeDate.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        feature,
        {"Request_Date", "Last_Action_Date", "Close_Date", "DateLoaded"},
    )


def _flatten_sla(feature):
    """Run the real ArcGIS flatten lift over a raw SLA captured feature.

    Only DateLoaded is esriFieldTypeDate on the table; IssuedOn/ExpiresOn
    are esriFieldTypeDateOnly (stay as YYYY-MM-DD strings).
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, {"DateLoaded"})


# ---------------------------------------------------------------------------
# 311 fixtures — newest rows by Request_Date DESC (2026-08-05 co-newest)
# ---------------------------------------------------------------------------

_FEATURE_311_107646 = {
    "attributes": {
        "OBJECTID": 107646,
        "DateLoaded": 1785981615723,
        "Request_Number": 189761,
        "Status": "Open",
        "Request_Date": 1785888000000,
        "Last_Action_Date": 1785888000000,
        "Close_Date": None,
        "Request_Type_Group": "Water/Sewer Services",
        "Request_Type": "Turn On Water (After Temporary Turn Off)",
        "Latitude": 33.563,
        "Longitude": -112.198,
        "Cross_Streets": None,
        "Council_District": "BARREL",
        "Responsible_Department_Name": "Customer Service Center",
        "ANON_BLOCK": 8500,
        "FULL_ADDRESS": "8500 BLOCK N 64TH LN",
    },
    "geometry": {
        "x": -112.19845707799999,
        "y": 33.56285964500006,
    },
}

_FEATURE_311_107645 = {
    "attributes": {
        "OBJECTID": 107645,
        "DateLoaded": 1785981615723,
        "Request_Number": 189760,
        "Status": "Open",
        "Request_Date": 1785888000000,
        "Last_Action_Date": 1785888000000,
        "Close_Date": None,
        "Request_Type_Group": "Traffic Safety",
        "Request_Type": "Traffic Enforcement - Public Property",
        "Latitude": 33.544,
        "Longitude": -112.22,
        "Cross_Streets": None,
        "Council_District": "CHOLLA",
        "Responsible_Department_Name": "Police Department",
        "ANON_BLOCK": 7400,
        "FULL_ADDRESS": "7400 BLOCK N 74TH DR",
    },
    "geometry": {
        "x": -112.21980653199995,
        "y": 33.54441091700005,
    },
}

_FEATURE_311_107643 = {
    "attributes": {
        "OBJECTID": 107643,
        "DateLoaded": 1785981615723,
        "Request_Number": 189757,
        "Status": "Open",
        "Request_Date": 1785888000000,
        "Last_Action_Date": 1785888000000,
        "Close_Date": None,
        "Request_Type_Group": "Streets/Sidewalks/Medians/Corners",
        "Request_Type": "Street Pavement Condition",
        "Latitude": 33.537,
        "Longitude": -112.166,
        "Cross_Streets": None,
        "Council_District": "CACTUS",
        "Responsible_Department_Name": "Transportation",
        "ANON_BLOCK": 5000,
        "FULL_ADDRESS": "5000 BLOCK W LAMAR RD",
    },
    "geometry": {
        "x": -112.16592634399996,
        "y": 33.536695218000034,
    },
}

_REQUEST_DATE_ISO = "2026-08-05T00:00:00+00:00"

# ---------------------------------------------------------------------------
# SLA fixtures — newest rows by IssuedOn DESC (2026-08-22/21)
# ---------------------------------------------------------------------------

_FEATURE_SLA_4629 = {
    "attributes": {
        "OBJECTID": 4629,
        "DateLoaded": 1787842811000,
        "LicenseType": "GBL - GLENDALE BUSINESS LICENSE-9898",
        "BusinessType": "COMMERCIAL RENTAL PROPERTY",
        "BusinessName": "YELLOW SUBMARINE LLC",
        "AddressLine1": "5213 W LAMAR RD STE 1",
        "City": "GLENDALE",
        "State": "AZ",
        "ZipCode": "85301",
        "District": "OCOTILLO",
        "IssuedOn": "2026-08-22",
        "LicenseStatus": "VALID",
        "ExpiresOn": "2027-08-31",
        "ParcelLegalDesc": "",
    },
}

_FEATURE_SLA_5950 = {
    "attributes": {
        "OBJECTID": 5950,
        "DateLoaded": 1787842811000,
        "LicenseType": "GBL - GLENDALE BUSINESS LICENSE-9898",
        "BusinessType": "SERVICE ONLY",
        "BusinessName": "SOUTHWEST LAW FIRM",
        "AddressLine1": "5616 W GLENDALE AVE",
        "City": "GLENDALE",
        "State": "AZ",
        "ZipCode": "85301",
        "District": "OCOTILLO",
        "IssuedOn": "2026-08-21",
        "LicenseStatus": "VALID",
        "ExpiresOn": "2027-07-09",
        "ParcelLegalDesc": (
            "COMMERCIAL/INDUSTRIAL REAL PROPERTY AND IMPROVEMENTS "
            "NOT IN OTHER CLASSES"
        ),
    },
}

_FEATURE_SLA_5997 = {
    "attributes": {
        "OBJECTID": 5997,
        "DateLoaded": 1787842811000,
        "LicenseType": "GBL - GLENDALE BUSINESS LICENSE-9898",
        "BusinessType": "RETAIL",
        "BusinessName": "SPACETEL AZ LLC",
        "AddressLine1": "6530 W GLENDALE AVE STE 98",
        "City": "GLENDALE",
        "State": "AZ",
        "ZipCode": "85301",
        "District": "OCOTILLO",
        "IssuedOn": "2026-08-21",
        "LicenseStatus": "VALID",
        "ExpiresOn": "2027-09-12",
        "ParcelLegalDesc": "",
    },
}


class TestGlendaleAzSpatial:
    def test_metro_bbox_sanity(self):
        assert GLENDALE_AZ_METRO_BBOX["min_lat"] < GLENDALE_AZ_METRO_BBOX["max_lat"]
        assert GLENDALE_AZ_METRO_BBOX["min_lng"] < GLENDALE_AZ_METRO_BBOX["max_lng"]

    def test_is_in_glendale_az_metro_rejects_missing_coordinates(self):
        assert is_in_glendale_az_metro(None, None) is False
        assert is_in_glendale_az_metro(33.5628, None) is False
        assert is_in_glendale_az_metro(None, -112.1985) is False

    def test_is_in_glendale_az_metro_rejects_other_cities(self):
        assert is_in_glendale_az_metro(33.4484, -112.0740) is False  # Phoenix
        assert is_in_glendale_az_metro(33.3478, -111.9780) is False  # Chandler
        assert is_in_glendale_az_metro(33.4260, -111.9370) is False  # Tempe

    def test_downtown_anchors_are_contained(self):
        assert is_in_glendale_az_metro(33.5388, -112.1859)  # Downtown Glendale
        assert is_in_glendale_az_metro(33.5381, -112.2599)  # Westgate
        assert is_in_glendale_az_metro(33.6289, -112.1697)  # Arrowhead
        assert is_in_glendale_az_metro(33.6300, -112.2139)  # Sahuaro Ranch

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_311_107646, _FEATURE_311_107645, _FEATURE_311_107643):
            assert is_in_glendale_az_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in GLENDALE_AZ_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= GLENDALE_AZ_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= GLENDALE_AZ_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= GLENDALE_AZ_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= GLENDALE_AZ_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in GLENDALE_AZ_SUBMARKETS.items():
            bbox = GLENDALE_AZ_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in GLENDALE_AZ_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(GLENDALE_AZ_SUBMARKETS)

    def test_submarkets_carry_the_glendale_az_city_id(self):
        assert {m.city_id for m in GLENDALE_AZ_SUBMARKETS.values()} == {"glendale_az"}

    def test_city_id_and_registration_shape(self):
        assert GLENDALE_AZ_CITY_ID == "glendale_az"
        assert REGISTRATION.metro_bbox is GLENDALE_AZ_METRO_BBOX
        assert REGISTRATION.submarkets is GLENDALE_AZ_SUBMARKETS
        assert REGISTRATION.division_bboxes is GLENDALE_AZ_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_glendale_az_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(GLENDALE_AZ_SUBMARKETS) == 9

    def test_required_real_neighborhoods_present(self):
        assert set(GLENDALE_AZ_SUBMARKETS) == {
            "Downtown Glendale",
            "Ocotillo / 43rd Ave Corridor",
            "Westgate",
            "Manistee Estates",
            "Grand Avenue / Barrel Corridor",
            "51st Ave / Cactus District",
            "Arrowhead",
            "Thunderbird",
            "Sahuaro Ranch",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_glendale_az_metro is is_in_glendale_az_metro


class TestGlendaleAzFieldMaps:
    def test_311_map_reads_live_columns(self):
        assert COMPLAINTS_311_FIELD_MAP["incident_id"] == ["Request_Number", "OBJECTID"]
        assert COMPLAINTS_311_FIELD_MAP["complaint_type"] == ["Request_Type", "Request_Type_Group"]
        assert COMPLAINTS_311_FIELD_MAP["created_date"] == ["Request_Date"]
        assert COMPLAINTS_311_FIELD_MAP["closed_date"] == ["Close_Date"]
        assert COMPLAINTS_311_FIELD_MAP["status"] == ["Status"]
        assert COMPLAINTS_311_FIELD_MAP["borough"] == ["Council_District"]
        assert COMPLAINTS_311_FIELD_MAP["incident_address"] == ["FULL_ADDRESS"]

    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["OBJECTID"]
        assert SLA_FIELD_MAP["license_type"] == ["BusinessType", "LicenseType"]
        assert SLA_FIELD_MAP["premises_name"] == ["BusinessName"]
        assert SLA_FIELD_MAP["dba"] == ["BusinessName"]
        assert SLA_FIELD_MAP["effective_date"] == ["IssuedOn"]
        assert SLA_FIELD_MAP["expiration_date"] == ["ExpiresOn"]
        assert SLA_FIELD_MAP["status"] == ["LicenseStatus"]
        assert SLA_FIELD_MAP["borough"] == ["District"]
        assert SLA_FIELD_MAP["address_street"] == ["AddressLine1"]
        assert SLA_FIELD_MAP["zipcode"] == ["ZipCode"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"311": COMPLAINTS_311_FIELD_MAP, "sla": SLA_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Glendale, AZ"
        assert GLENDALE_AZ_GEOCODE_CONTEXT == "Glendale, AZ"

    def test_311_coordinates_from_geometry_only(self):
        """No latitude/longitude candidates in the field map — coordinates
        come only from the geometry lift, not the truncated attribute
        values. Verify the attribute values are indeed truncated (3 decimals)
        while geometry gives full precision."""
        assert "latitude" not in COMPLAINTS_311_FIELD_MAP
        assert "longitude" not in COMPLAINTS_311_FIELD_MAP
        attrs = _FEATURE_311_107646["attributes"]
        assert attrs["Latitude"] == 33.563  # truncated placeholder
        assert attrs["Longitude"] == -112.198  # truncated
        geom = _FEATURE_311_107646["geometry"]
        assert geom["y"] != attrs["Latitude"]  # geometry has full precision
        assert geom["x"] != attrs["Longitude"]

    def test_311_no_borough_candidate_so_source_neighborhood_comes_from_map(self):
        """borough is mapped to Council_District, so source_neighborhood is
        populated from the feed's district label."""
        assert "borough" in COMPLAINTS_311_FIELD_MAP
        assert COMPLAINTS_311_FIELD_MAP["borough"] == ["Council_District"]

    def test_sla_has_no_geometry_candidates(self):
        """SLA table has no geometry — no latitude/longitude candidates."""
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP

    def test_pii_and_nonaddress_columns_never_become_candidates(self):
        for feed_map in (COMPLAINTS_311_FIELD_MAP, SLA_FIELD_MAP):
            for values in feed_map.values():
                for col in values:
                    assert col not in DROPPED_NONADDRESS_COLUMNS
        assert {"Latitude", "Longitude", "City", "State", "ParcelLegalDesc"} <= set(
            DROPPED_NONADDRESS_COLUMNS
        )


class TestGlendaleAz311Parsing:
    @pytest.fixture
    def producer(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten_311(_FEATURE_311_107646)
        # geometry lift gives full-precision degrees
        assert record["latitude"] == pytest.approx(33.56285964500006)
        assert record["longitude"] == pytest.approx(-112.19845707799999)
        # truncated attribute values ride along unmapped
        assert record["Latitude"] == 33.563
        assert record["Longitude"] == -112.198

    def test_flatten_iso_normalizes_the_watermark(self):
        record = _flatten_311(_FEATURE_311_107645)
        assert record["Request_Date"] == _REQUEST_DATE_ISO
        assert record["DateLoaded"] == "2026-08-06T02:00:15.723000+00:00"

    def test_water_fixture_parses_through_the_producer(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = producer.parse_socrata_row(
            _flatten_311(_FEATURE_311_107646), city_id="glendale_az"
        )
        assert event is not None
        assert event.city_id == "glendale_az"
        assert event.incident_id == "189761"
        assert event.complaint_type == "Turn On Water (After Temporary Turn Off)"
        assert event.status == "Open"
        assert event.latitude == pytest.approx(33.56285964500006)
        assert event.longitude == pytest.approx(-112.19845707799999)
        assert event.created_date is not None
        assert event.created_date.isoformat() == _REQUEST_DATE_ISO
        assert event.closed_date is None
        assert event.incident_address == "8500 BLOCK N 64TH LN"
        assert event.source_neighborhood == "BARREL"

    def test_traffic_fixture_h3_and_containment(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = producer.parse_socrata_row(
            _flatten_311(_FEATURE_311_107645), city_id="glendale_az"
        )
        assert event is not None
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_glendale_az_metro(event.latitude, event.longitude)

    def test_street_fixture_parses_anonymized_address(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = producer.parse_socrata_row(
            _flatten_311(_FEATURE_311_107643), city_id="glendale_az"
        )
        assert event is not None
        assert event.incident_id == "189757"
        assert event.incident_address == "5000 BLOCK W LAMAR RD"
        assert event.source_neighborhood == "CACTUS"
        assert is_in_glendale_az_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_share_the_co_newest_watermark(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        events = [
            producer.parse_socrata_row(_flatten_311(f), city_id="glendale_az")
            for f in (_FEATURE_311_107646, _FEATURE_311_107645, _FEATURE_311_107643)
        ]
        assert all(e is not None for e in events)
        assert {e.created_date.isoformat() for e in events} == {_REQUEST_DATE_ISO}
        assert len({e.h3_res9 for e in events}) == 3

    def test_row_without_any_id_is_dropped(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten_311(_FEATURE_311_107646)
        record.pop("Request_Number")
        record.pop("OBJECTID")
        assert producer.parse_socrata_row(record, city_id="glendale_az") is None

    def test_geometry_less_311_row_uses_geocode_fallback(
        self, producer, monkeypatch
    ):
        _patch_resolve(monkeypatch, "311")
        record = _flatten_311(_FEATURE_311_107646)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (33.5410, -112.1910),
        )
        event = producer.parse_socrata_row(record, city_id="glendale_az")
        assert event is not None
        assert event.latitude == pytest.approx(33.5410)
        assert event.longitude == pytest.approx(-112.1910)

    def test_geometry_less_311_row_dropped_when_geocode_fails(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten_311(_FEATURE_311_107645)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert producer.parse_socrata_row(record, city_id="glendale_az") is None


class TestGlendaleAzSLAParsing:
    @pytest.fixture
    def producer(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_flatten_preserves_dateonly_strings(self):
        record = _flatten_sla(_FEATURE_SLA_4629)
        # IssuedOn/ExpiresOn are esriFieldTypeDateOnly — stay as strings
        assert record["IssuedOn"] == "2026-08-22"
        assert record["ExpiresOn"] == "2027-08-31"
        # DateLoaded is esriFieldTypeDate — ISO-normalized
        assert record["DateLoaded"] == "2026-08-27T15:00:11+00:00"

    def test_license_parses_through_producer_with_geocode(
        self, producer, monkeypatch
    ):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (33.5370, -112.1830),
        )
        event = producer.parse_socrata_row(
            _flatten_sla(_FEATURE_SLA_4629), city_id="glendale_az"
        )
        assert event is not None
        assert event.city_id == "glendale_az"
        assert event.license_id == "4629"
        assert event.dba == "YELLOW SUBMARINE LLC"
        assert event.premises_name == "YELLOW SUBMARINE LLC"
        assert event.license_type == "COMMERCIAL RENTAL PROPERTY"
        assert event.license_status == "VALID"
        assert event.address == "5213 W LAMAR RD STE 1"
        assert event.latitude == pytest.approx(33.5370)
        assert event.longitude == pytest.approx(-112.1830)
        assert event.effective_date is not None
        assert event.expiration_date is not None
        assert event.source_neighborhood == "OCOTILLO"

    def test_law_firm_fixture_parses_district_and_parcel(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (33.5370, -112.1830),
        )
        event = producer.parse_socrata_row(
            _flatten_sla(_FEATURE_SLA_5950), city_id="glendale_az"
        )
        assert event is not None
        assert event.license_id == "5950"
        assert event.license_type == "SERVICE ONLY"
        assert event.address == "5616 W GLENDALE AVE"
        assert event.source_neighborhood == "OCOTILLO"

    def test_retail_fixture_parses_zipcode(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (33.5370, -112.1830),
        )
        event = producer.parse_socrata_row(
            _flatten_sla(_FEATURE_SLA_5997), city_id="glendale_az"
        )
        assert event is not None
        assert event.license_id == "5997"
        assert event.license_type == "RETAIL"
        assert event.effective_date.date().isoformat() == "2026-08-21"
        assert event.expiration_date.date().isoformat() == "2027-09-12"

    def test_row_without_license_id_dropped(self, producer, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten_sla(_FEATURE_SLA_4629)
        record.pop("OBJECTID")
        assert producer.parse_socrata_row(record, city_id="glendale_az") is None

    def test_geocode_failure_emits_null_coordinate_event(self, producer, monkeypatch):
        """SLA has no geometry; if the ADR-0004 geocode supplement fails the
        producer tolerates coordinate-less rows (DC BBL precedent) — the event
        is still emitted with null lat/lng and null H3, keyed on license_id."""
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = producer.parse_socrata_row(
            _flatten_sla(_FEATURE_SLA_4629), city_id="glendale_az"
        )
        assert event is not None
        assert event.license_id == "4629"
        assert event.latitude is None
        assert event.longitude is None
        assert event.h3_res7 is None
        assert event.h3_res8 is None
        assert event.h3_res9 is None


class TestGlendaleAzFeedSpec:
    def test_311_spec_matches_live_layer(self):
        spec = get_glendale_az_dataset(FeedType.COMPLAINTS_311)
        assert spec.platform == "arcgis"
        assert spec.endpoint == GLENDALE_AZ_311_ENDPOINT
        assert spec.watermark_col == "Request_Date"
        assert spec.id_keys == ["Request_Number", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "Request_Date DESC, Request_Number DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map == COMPLAINTS_311_FIELD_MAP
        assert spec.topic == "raw.municipal.311"

    def test_sla_spec_matches_live_table(self):
        spec = get_glendale_az_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == GLENDALE_AZ_SLA_ENDPOINT
        assert spec.watermark_col == "IssuedOn"
        assert spec.id_keys == ["OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "IssuedOn DESC"
        assert spec.interval_seconds == 600.0
        assert spec.ingestion_mode == "snapshot"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Glendale, AZ"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"

    def test_registered_feed_set_is_311_and_sla(self):
        assert set(GLENDALE_AZ_FEED_SPECS) == {"311", "sla"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_glendale_az_dataset("permits")
        assert "glendale_az" in str(exc.value)
        assert "311" in str(exc.value)
        assert "sla" in str(exc.value)

    def test_deeds_also_raises(self):
        with pytest.raises(KeyError) as exc:
            get_glendale_az_dataset("deeds")
        assert "glendale_az" in str(exc.value)

    def test_endpoints_are_the_probed_mapserver(self):
        assert "gismaps.glendaleaz.com" in GLENDALE_AZ_311_ENDPOINT
        assert "GLENDALEONE_EXTERNAL_REQUESTS_PTS" in GLENDALE_AZ_311_ENDPOINT
        assert "gismaps.glendaleaz.com" in GLENDALE_AZ_SLA_ENDPOINT
        assert "Business_Licenses" in GLENDALE_AZ_SLA_ENDPOINT