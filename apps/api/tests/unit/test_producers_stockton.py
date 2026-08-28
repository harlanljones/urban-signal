"""Unit tests for the Stockton, CA leaf (US-230): spatial module + field
maps + producer parse wiring.

Stockton is a ONE-FEED PARTIAL metro: SLA only — the city liquor-license
layer (``OpenCounter/OpenCounterMap/MapServer/7`` on the city's own ArcGIS
Server ``gisportal.stocktonca.gov``, 1,363 rows). PERMITS (Accela/
Forerunner folders: 499 Token Required), 311 (Comcate: 499), and deeds
(San Joaquin County publishes no recorder bulk surface) stay Tier 3 — only
``sla`` is registered. The ticket's claimed Hub site
(stocktonca.opendata.arcgis.com) is a dead shell and data.stocktonca.gov
serves the national Socrata catalog — neither is a feed.

Tests pass WITHOUT a spine registration (no CityId.STOCKTON, no REGISTRY
assertions — "stockton" stays a plain string). Spine-stable per the
leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from MapServer/7 (newest rows
via ``orderByFields=OriginalIssueDate DESC`` at ``outSR=4326``; newest
watermark ``1783987200000`` = 2026-07-14T00:00:00+00:00). Fixtures are RAW
ArcGIS features (attributes + geometry); the tests run the real
``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO — before parsing, exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_stockton import (
    DROPPED_MAIL_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.spatial.cities.stockton import (
    DROPPED_MAIL_COLUMNS as CITY_DROPPED_MAIL_COLUMNS,
)
from src.spatial.cities.stockton import (
    REGISTRATION,
    STOCKTON_CITY_ID,
    STOCKTON_DIVISION_BBOXES,
    STOCKTON_DIVISIONS,
    STOCKTON_FEED_SPECS,
    STOCKTON_GEOCODE_CONTEXT,
    STOCKTON_METRO_BBOX,
    STOCKTON_SLA_ENDPOINT,
    STOCKTON_STATE_PLANE_CRS,
    STOCKTON_STATE_PLANE_UNITS,
    STOCKTON_SUBMARKETS,
    get_stockton_dataset,
    is_in_greater_stockton_metro,
    is_in_stockton_metro,
)
from src.spatial.cities.stockton import (
    SLA_FIELD_MAP as CITY_SLA_FIELD_MAP,
)


def _patch_resolve(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["sla"],
    )


def _flatten(feature):
    """Run the real ArcGIS flatten lift over a raw captured feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: OriginalIssueDate and ExpirationDate are esriFieldTypeDate.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        feature, {"OriginalIssueDate", "ExpirationDate"}
    )


# Newest rows on the layer (orderByFields=OriginalIssueDate DESC,
# outSR=4326) — captured byte-verbatim 2026-08-28. Note the mailing-zip
# trap: the first two rows sit at Stockton premises (950 W 11th St / 165 W
# 10th St, south Stockton) while PremiseZipcode reads "95376" (Tracy) —
# mailing zips, never premise geography. PremiseName is a single space on
# both: the owner name (OwnerName) is the populated name field.
_FEATURE_512 = {
    "attributes": {
        "OBJECTID": 512,
        "LicenseCode": 20,
        "FileNumber": 670013,
        "OriginalIssueDate": 1783987200000,
        "ExpirationDate": 1814313600000,
        "PremiseName": " ",
        "PremiseAddress": "950 W 11TH ST",
        "PremiseAddress2": " ",
        "OwnerName": "PLATINUM GAS AND MARKET 3",
        "PremiseZipcode": "95376",
        "MailAddress": "920 EASTLAKE CIRCLE",
        "MailAddress2": " ",
        "MailCity": "TRACY",
        "MailState": "CA",
        "MailZipcode": "95304",
        "PremiseCensusTract": "54.03",
        "LicenseType": "20",
        "Status": "ACTIVE",
    },
    "geometry": {
        "x": -121.27057761977937,
        "y": 37.927051788717606,
    },
}

_FEATURE_1079 = {
    "attributes": {
        "OBJECTID": 1079,
        "LicenseCode": 47,
        "FileNumber": 679040,
        "OriginalIssueDate": 1783382400000,
        "ExpirationDate": 1814313600000,
        "PremiseName": " ",
        "PremiseAddress": "165 W TENTH ST",
        "PremiseAddress2": " ",
        "OwnerName": "JASMIN CORP",
        "PremiseZipcode": "95376",
        "MailAddress": "783 S TRACY BLVD",
        "MailAddress2": "#117",
        "MailCity": "TRACY",
        "MailState": "CA",
        "MailZipcode": "95376",
        "PremiseCensusTract": "54.05",
        "LicenseType": "47",
        "Status": "ACTIVE",
    },
    "geometry": {
        "x": -121.28448342144426,
        "y": 37.92447342483113,
    },
}

# Third-newest row: a north-county winery premise inside the metro bbox
# but outside every hand-authored division — fringe rows must stay
# contained by the metro bbox even where no division claims them.
_FEATURE_586 = {
    "attributes": {
        "OBJECTID": 586,
        "LicenseCode": 2,
        "FileNumber": 674453,
        "OriginalIssueDate": 1783296000000,
        "ExpirationDate": 1814313600000,
        "PremiseName": "JERA WINERY",
        "PremiseAddress": "22211 N LOWER SACRAMENTO RD",
        "PremiseAddress2": " ",
        "OwnerName": "WHEREABOUT WINES LLC",
        "PremiseZipcode": "95220",
        "MailAddress": "1913 NEWELL AVE",
        "MailAddress2": " ",
        "MailCity": "WALNUT CREEK",
        "MailState": "CA",
        "MailZipcode": "94595",
        "PremiseCensusTract": "46",
        "LicenseType": "2",
        "Status": "ACTIVE",
    },
    "geometry": {
        "x": -121.31044978244714,
        "y": 38.07754846281675,
    },
}

_NEWEST_ISSUE_ISO = "2026-07-14T00:00:00+00:00"
_ABC_LICENSE_YEAR_EXPIRY_ISO = "2027-06-30T00:00:00+00:00"


class TestStocktonSpatial:
    def test_city_id_constant_is_the_leaf_string(self):
        assert STOCKTON_CITY_ID == "stockton"

    def test_metro_bbox_sanity(self):
        assert STOCKTON_METRO_BBOX["min_lat"] < STOCKTON_METRO_BBOX["max_lat"]
        assert STOCKTON_METRO_BBOX["min_lng"] < STOCKTON_METRO_BBOX["max_lng"]

    def test_is_in_stockton_metro_rejects_missing_coordinates(self):
        assert is_in_stockton_metro(None, None) is False
        assert is_in_stockton_metro(37.9577, None) is False
        assert is_in_stockton_metro(None, -121.29) is False

    def test_is_in_stockton_metro_rejects_other_cities(self):
        assert is_in_stockton_metro(37.7397, -121.4252) is False  # Tracy
        assert is_in_stockton_metro(37.7972, -121.2164) is False  # Manteca
        assert is_in_stockton_metro(38.1342, -121.2723) is False  # Lodi
        assert is_in_stockton_metro(38.5816, -121.4944) is False  # Sacramento

    def test_downtown_anchors_are_contained(self):
        assert is_in_stockton_metro(37.9577, -121.2900)  # Downtown core
        assert is_in_stockton_metro(37.9666, -121.3190)  # Miracle Mile
        assert is_in_stockton_metro(37.9330, -121.3130)  # Spanos Park
        assert is_in_stockton_metro(37.9250, -121.2820)  # Weston Ranch
        assert is_in_stockton_metro(38.0775, -121.3104)  # N winery corridor

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_512, _FEATURE_1079, _FEATURE_586):
            assert is_in_stockton_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in STOCKTON_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= STOCKTON_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= STOCKTON_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= STOCKTON_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= STOCKTON_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in STOCKTON_SUBMARKETS.items():
            bbox = STOCKTON_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in STOCKTON_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(STOCKTON_SUBMARKETS)

    def test_submarkets_carry_the_stockton_city_id(self):
        assert {m.city_id for m in STOCKTON_SUBMARKETS.values()} == {"stockton"}

    def test_registration_shape(self):
        assert REGISTRATION.metro_bbox is STOCKTON_METRO_BBOX
        assert REGISTRATION.submarkets is STOCKTON_SUBMARKETS
        assert REGISTRATION.division_bboxes is STOCKTON_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_stockton_metro
        assert len(REGISTRATION.divisions) == 7
        assert len(STOCKTON_SUBMARKETS) == 14

    def test_required_real_neighborhoods_present(self):
        assert {
            "Downtown Core",
            "Banner Island & Waterfront",
            "Miracle Mile",
            "University of the Pacific",
            "Lincoln Village & Park Nine",
            "Eastland Plaza",
            "Brookside",
            "Quail Lakes & Heritage",
            "Spanos Park",
            "Weston Ranch",
            "South Stockton & Fairgrounds",
            "Airport & Arch Road Industrial",
        } <= set(STOCKTON_SUBMARKETS)

    def test_greater_metro_alias(self):
        assert is_in_greater_stockton_metro is is_in_stockton_metro


class TestStocktonFieldMaps:
    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["FileNumber", "OBJECTID"]
        assert SLA_FIELD_MAP["dba"] == ["PremiseName"]
        assert SLA_FIELD_MAP["premises_name"] == ["OwnerName"]
        assert SLA_FIELD_MAP["license_type"] == ["LicenseType", "LicenseCode"]
        assert SLA_FIELD_MAP["status"] == ["Status"]
        assert SLA_FIELD_MAP["effective_date"] == ["OriginalIssueDate"]
        assert SLA_FIELD_MAP["expiration_date"] == ["ExpirationDate"]
        assert SLA_FIELD_MAP["address_street"] == ["PremiseAddress", "PremiseAddress2"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"sla": SLA_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Stockton, CA"
        assert STOCKTON_GEOCODE_CONTEXT == "Stockton, CA"
        assert CITY_SLA_FIELD_MAP is SLA_FIELD_MAP
        assert CITY_DROPPED_MAIL_COLUMNS is DROPPED_MAIL_COLUMNS

    def test_no_coordinate_candidates_because_store_sr_is_state_plane(self):
        """The layer's store SR is NAD83 California Zone 3 ftUS (WKID
        102643/latest 2227). Unlike Aurora there are NO X/Y attribute
        columns at all — coordinates may only come from the outSR=4326
        geometry lift, so no latitude/longitude candidates are declared."""
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP
        assert STOCKTON_STATE_PLANE_CRS == "EPSG:2227"
        assert STOCKTON_STATE_PLANE_UNITS == "ftUS"
        for feature in (_FEATURE_512, _FEATURE_1079, _FEATURE_586):
            for col in feature["attributes"]:
                assert not col.lower().startswith(("gps", "x", "y"))

    def test_first_mapped_finds_no_coordinates_in_live_rows(self):
        for feature in (_FEATURE_512, _FEATURE_1079, _FEATURE_586):
            attrs = feature["attributes"]
            assert first_mapped(attrs, SLA_FIELD_MAP, "latitude") is None
            assert first_mapped(attrs, SLA_FIELD_MAP, "longitude") is None

    def test_mailing_columns_never_become_candidates(self):
        mapped = {c for values in SLA_FIELD_MAP.values() for c in values}
        assert mapped
        for col in DROPPED_MAIL_COLUMNS:
            assert col not in mapped
        # The mailing block is exactly what is dropped — PremiseZipcode is
        # the mailing-zip trap (Tracy zips on Stockton premises).
        assert {"MailAddress", "MailCity", "MailZipcode", "PremiseZipcode"} <= set(
            DROPPED_MAIL_COLUMNS
        )
        for feature in (_FEATURE_512, _FEATURE_1079):
            attrs = feature["attributes"]
            assert first_mapped(attrs, SLA_FIELD_MAP, "zipcode") is None

    def test_no_borough_candidate_so_source_neighborhood_passes_none(self):
        """No neighborhood/district column exists on the layer: no borough
        candidate is declared, so source_neighborhood stays None."""
        assert "borough" not in SLA_FIELD_MAP
        assert "neighborhood" not in SLA_FIELD_MAP


class TestStocktonSLAParsing:
    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_FEATURE_512)
        assert record["latitude"] == pytest.approx(37.927051788717606)
        assert record["longitude"] == pytest.approx(-121.27057761977937)

    def test_flatten_iso_normalizes_the_date_columns_only(self):
        record = _flatten(_FEATURE_512)
        assert record["OriginalIssueDate"] == _NEWEST_ISSUE_ISO
        assert record["ExpirationDate"] == _ABC_LICENSE_YEAR_EXPIRY_ISO
        assert record["LicenseCode"] == 20  # smallint, not a date — untouched

    def test_newest_fixture_parses_through_the_producer(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_flatten(_FEATURE_512), city_id="stockton")
        assert event is not None
        assert event.city_id == "stockton"
        assert event.license_id == "670013"
        assert event.license_status == "ACTIVE"
        assert event.license_type == "20"
        assert event.dba == " "  # byte-verbatim blank trade name
        assert event.premises_name == "PLATINUM GAS AND MARKET 3"
        assert event.address == "950 W 11TH ST"
        assert event.latitude == pytest.approx(37.927051788717606)
        assert event.longitude == pytest.approx(-121.27057761977937)
        assert event.effective_date.isoformat() == _NEWEST_ISSUE_ISO
        assert event.expiration_date.isoformat() == _ABC_LICENSE_YEAR_EXPIRY_ISO
        assert event.source_neighborhood is None
        assert event.zipcode if hasattr(event, "zipcode") else True

    def test_second_fixture_h3_and_containment(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_flatten(_FEATURE_1079), city_id="stockton")
        assert event is not None
        assert event.license_id == "679040"
        assert event.license_type == "47"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_stockton_metro(event.latitude, event.longitude)
        # South-Stockton premises land in the southeast division bbox —
        # pure leaf-bbox math, not division resolution (spine-volatile).
        bbox = STOCKTON_DIVISION_BBOXES["SOUTHEAST_WESTON"]
        assert bbox["min_lat"] <= event.latitude <= bbox["max_lat"]
        assert bbox["min_lng"] <= event.longitude <= bbox["max_lng"]

    def test_fringe_winery_fixture_is_contained_outside_all_divisions(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(_flatten(_FEATURE_586), city_id="stockton")
        assert event is not None
        assert event.dba == "JERA WINERY"
        assert event.premises_name == "WHEREABOUT WINES LLC"
        assert event.address == "22211 N LOWER SACRAMENTO RD"
        assert event.license_type == "2"
        assert event.effective_date.isoformat() == "2026-07-06T00:00:00+00:00"
        assert is_in_stockton_metro(event.latitude, event.longitude)
        assert event.latitude > max(b["max_lat"] for b in STOCKTON_DIVISION_BBOXES.values())

    def test_license_id_falls_back_to_objectid(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        record = _flatten(_FEATURE_512)
        record.pop("FileNumber")
        event = sla.parse_socrata_row(record, city_id="stockton")
        assert event is not None
        assert event.license_id == "512"

    def test_row_without_any_id_is_dropped(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        record = _flatten(_FEATURE_512)
        record.pop("FileNumber")
        record.pop("OBJECTID")
        assert sla.parse_socrata_row(record, city_id="stockton") is None

    def test_row_without_geometry_stays_an_event_with_null_coords(
        self, sla, monkeypatch
    ):
        """Live layer has 0 null geometries today, but a future
        null-geometry row must not crash: it resolves via the ADR-0004
        geocode supplement (needs_geocode=True). Call-args/counts are
        spine-volatile and not asserted — only the event outcome."""
        _patch_resolve(monkeypatch)
        record = _flatten(_FEATURE_586)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (38.0775, -121.3104),
        )
        event = sla.parse_socrata_row(record, city_id="stockton")
        assert event is not None
        assert event.city_id == "stockton"
        assert event.license_id == "674453"
        assert event.latitude == pytest.approx(38.0775)
        assert event.longitude == pytest.approx(-121.3104)
        assert event.h3_res7 is not None

    def test_null_geometry_row_keeps_null_coords_when_geocode_fails(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch)
        record = _flatten(_FEATURE_586)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = sla.parse_socrata_row(record, city_id="stockton")
        assert event is not None  # keyed on the license id, null H3
        assert event.latitude is None
        assert event.longitude is None
        assert event.h3_res7 is None

    def test_placeholder_zero_coords_never_index_h3(self, sla, monkeypatch):
        """LA-style 0.0/0.0 placeholders are falsy in the parser's
        coordinate chain, so they resolve as coordinate-less (never a Gulf
        of Guinea H3 cell) and fall to geocode (None here)."""
        _patch_resolve(monkeypatch)
        record = _flatten(_FEATURE_512)
        record["latitude"] = 0.0
        record["longitude"] = 0.0
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = sla.parse_socrata_row(record, city_id="stockton")
        assert event is not None
        assert event.latitude is None
        assert event.longitude is None
        assert event.h3_res7 is None


class TestStocktonFeedSpec:
    def test_sla_spec_matches_live_layer(self):
        spec = get_stockton_dataset("sla")
        assert spec.platform == "arcgis"
        assert spec.endpoint == STOCKTON_SLA_ENDPOINT
        assert spec.watermark_col == "OriginalIssueDate"
        assert spec.id_keys == ["FileNumber", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 7
        assert spec.order_by == "OriginalIssueDate DESC"
        assert spec.interval_seconds == 600.0
        assert spec.ingestion_mode == "snapshot"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Stockton, CA"
        assert spec.where is None
        assert spec.alarm_exempt is True
        assert "watermark" in spec.alarm_exempt_reason
        assert spec.state_plane_crs == "EPSG:2227"
        assert spec.state_plane_units == "ftUS"
        assert spec.state_plane_x_col is None
        assert spec.state_plane_y_col is None
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"

    def test_registered_feed_set_is_sla_only(self):
        assert set(STOCKTON_FEED_SPECS) == {"sla"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_stockton_dataset("permits")
        assert "stockton" in str(exc.value)
        assert "sla" in str(exc.value)

    def test_endpoint_is_the_probed_mapserver(self):
        assert "gisportal.stocktonca.gov" in STOCKTON_SLA_ENDPOINT
        assert (
            "OpenCounter/OpenCounterMap/MapServer/7" in STOCKTON_SLA_ENDPOINT
        )
