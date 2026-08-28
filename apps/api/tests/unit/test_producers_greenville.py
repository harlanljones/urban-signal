"""Unit tests for the Greenville, SC leaf (US-340): spatial module + field
maps + producer parse wiring.

Greenville is a ONE-FEED PARTIAL metro: BuildingPermits_PriorTwoYears
(ArcGIS Server 10.81 MapServer/0 at ``citygis.greenvillesc.gov``, Tier 1,
daily, native outSR=4326 point geometry). 311 (internal-only ``.ads`` host),
SLA (static 2021-2024 license snapshot), and deeds (parcel CAMA) stay
Tier 3 — only ``permits`` is registered.

Tests pass WITHOUT a spine registration (no CityId.GREENVILLE, no REGISTRY
assertions — "greenville" stays a plain string). Spine-stable per the
wave-5 leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from MapServer/0 (newest rows
via ``orderByFields=NewIssueDate DESC`` at ``outSR=4326``; newest watermark
``1787803200000`` = 2026-08-27T04:00:00+00:00, four co-newest rows).
Fixtures are RAW ArcGIS features (attributes + geometry); the tests run the
real ``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO — before parsing, exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_greenville import (
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.greenville import (
    GREENVILLE_CITY_ID,
    GREENVILLE_DIVISION_BBOXES,
    GREENVILLE_DIVISIONS,
    GREENVILLE_FEED_SPECS,
    GREENVILLE_GEOCODE_CONTEXT,
    GREENVILLE_METRO_BBOX,
    GREENVILLE_PERMITS_ENDPOINT,
    GREENVILLE_SUBMARKETS,
    REGISTRATION,
    get_greenville_dataset,
    is_in_greater_greenville_metro,
    is_in_greenville_metro,
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
    metadata: NewIssueDate is esriFieldTypeDate; APPLICDATE is a numeric
    double and is correctly NOT a date field.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, {"NewIssueDate"})


# Newest rows on the 2026-08-28 resume re-probe (orderByFields=NewIssueDate
# DESC, outSR=4326) — four rows share the co-newest watermark; three below.
# Byte-verbatim: padded street/unit columns, numeric APPLICDATE doubles,
# State Plane X_COORD/Y_COORD feet, native WGS84 geometry.
_FEATURE_490 = {
    "attributes": {
        "OBJECTID": 490,
        "Status": "M",
        "PERMIT_TYPE": "BLDG",
        "APPLICDATE": 20260710.0,
        "APPLIC_DESCRIPTION": "RESIDENTIAL, NEW TOWNHOUSE                   ",
        "BP_STATUS": "IS",
        "PERMIT_NUM": "2600002910",
        "STREETADDRESS": "16   BROAD RIVER ST  ",
        "UNITNUM": "     ",
        "PERMIT_VALUATION": 109591,
        "X_COORD": 1598962.630905,
        "Y_COORD": 1082016.798228,
        "OWNER_NAME": "STANLEY MARTIN HOMES LLC      ",
        "OWNER_ADDR": "13310 S RIDGE DR STE A        ",
        "OWNER_ADDR2": "                              ",
        "OWNER_ZIP": "28273    ",
        "CONTRACTOR_NAME": "STANLEY MARTIN HOMES, LLC     ",
        "CONT_ADDR": "11710 PLAZA AMERICA DR        ",
        "CONT_ADDR2": "STE 1100                      ",
        "CONT_ZIP": "20190    ",
        "PERMIT_LOCATION": "16   BROAD RIVER ST        ",
        "NewIssueDate": 1787803200000,
        "PERMIT_COMMENTS": "New Townhome building  "
    },
    "geometry": {
        "x": -82.33757403747684,
        "y": 34.799886445526745
    }
}

_FEATURE_595 = {
    "attributes": {
        "OBJECTID": 595,
        "Status": "M",
        "PERMIT_TYPE": "BLDG",
        "APPLICDATE": 20260320.0,
        "APPLIC_DESCRIPTION": "RESIDENTIAL, NEW SINGLE FAMILY               ",
        "BP_STATUS": "IS",
        "PERMIT_NUM": "2600001141",
        "STREETADDRESS": "119   WOODVILLE AV  ",
        "UNITNUM": "     ",
        "PERMIT_VALUATION": 800000,
        "X_COORD": 1586730.373046,
        "Y_COORD": 1102577.726412,
        "OWNER_NAME": "HEROMAN FREDERICK JTWROS      ",
        "OWNER_ADDR": "PHILLIPS RAWLSTON DAVID III  J",
        "OWNER_ADDR2": "123 WOODVILLE AVE             ",
        "OWNER_ZIP": "29607    ",
        "CONTRACTOR_NAME": "HOUSTON, JASON                ",
        "CONT_ADDR": "GOOD WOOD BUILDING PRACTICES  ",
        "CONT_ADDR2": "9 IDLEWOOD DR                 ",
        "CONT_ZIP": "29609    ",
        "PERMIT_LOCATION": "119   WOODVILLE AV        ",
        "NewIssueDate": 1787803200000,
        "PERMIT_COMMENTS": "New building  "
    },
    "geometry": {
        "x": -82.37743074178996,
        "y": 34.856073905097084
    }
}

_FEATURE_636 = {
    "attributes": {
        "OBJECTID": 636,
        "Status": "M",
        "PERMIT_TYPE": "BLDG",
        "APPLICDATE": 20260601.0,
        "APPLIC_DESCRIPTION": "RESIDENTIAL, GARAGE/CARPORT/ACCESSORY BLDG   ",
        "BP_STATUS": "IS",
        "PERMIT_NUM": "2600002286",
        "STREETADDRESS": "28   GURLEY AV  ",
        "UNITNUM": "     ",
        "PERMIT_VALUATION": 31714,
        "X_COORD": 1586870.689,
        "Y_COORD": 1084771.403,
        "OWNER_NAME": "CARRINGTON TONY JTWROS        ",
        "OWNER_ADDR": "CARRINGTON KATHERINE  JTWROS  ",
        "OWNER_ADDR2": "28 GURLEY AVE                 ",
        "OWNER_ZIP": "29605    ",
        "CONTRACTOR_NAME": "J D TURNER CONSTRUCTION LLC   ",
        "CONT_ADDR": "2601 FEWS BRIDGE RD           ",
        "CONT_ADDR2": "                              ",
        "CONT_ZIP": "29651    ",
        "PERMIT_LOCATION": "28   GURLEY AV        ",
        "NewIssueDate": 1787803200000,
        "PERMIT_COMMENTS": "Construction of a 28x32 detached garage  - power and water service from existing  home.  "
    },
    "geometry": {
        "x": -82.37621343812552,
        "y": 34.8071480655466
    }
}

_NEWISSUE_ISO = "2026-08-27T04:00:00+00:00"


class TestGreenvilleSpatial:
    def test_metro_bbox_sanity(self):
        assert GREENVILLE_METRO_BBOX["min_lat"] < GREENVILLE_METRO_BBOX["max_lat"]
        assert GREENVILLE_METRO_BBOX["min_lng"] < GREENVILLE_METRO_BBOX["max_lng"]

    def test_is_in_greenville_metro_rejects_missing_coordinates(self):
        assert is_in_greenville_metro(None, None) is False
        assert is_in_greenville_metro(34.8497, None) is False
        assert is_in_greenville_metro(None, -82.3992) is False

    def test_is_in_greenville_metro_rejects_other_cities(self):
        assert is_in_greenville_metro(35.2271, -80.8431) is False   # Charlotte
        assert is_in_greenville_metro(33.7490, -84.3880) is False   # Atlanta
        assert is_in_greenville_metro(34.0007, -81.0348) is False   # Columbia, SC
        assert is_in_greenville_metro(34.7134, -82.2569) is False   # Simpsonville (south, outside)

    def test_downtown_anchors_are_contained(self):
        assert is_in_greenville_metro(34.8453, -82.4015)  # Falls Park on the Reedy
        assert is_in_greenville_metro(34.8448, -82.4022)  # Fluor Field, West End
        assert is_in_greenville_metro(34.8500, -82.3995)  # Main St core

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_490, _FEATURE_595, _FEATURE_636):
            assert is_in_greenville_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in GREENVILLE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= GREENVILLE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= GREENVILLE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= GREENVILLE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= GREENVILLE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in GREENVILLE_SUBMARKETS.items():
            bbox = GREENVILLE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in GREENVILLE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(GREENVILLE_SUBMARKETS)

    def test_submarkets_carry_the_greenville_city_id(self):
        assert {m.city_id for m in GREENVILLE_SUBMARKETS.values()} == {"greenville"}

    def test_city_id_and_registration_shape(self):
        assert GREENVILLE_CITY_ID == "greenville"
        assert REGISTRATION.metro_bbox is GREENVILLE_METRO_BBOX
        assert REGISTRATION.submarkets is GREENVILLE_SUBMARKETS
        assert REGISTRATION.division_bboxes is GREENVILLE_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_greenville_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(GREENVILLE_SUBMARKETS) == 8

    def test_required_real_neighborhoods_present(self):
        assert set(GREENVILLE_SUBMARKETS) == {
            "Downtown",
            "West End",
            "Village of West Greenville",
            "North Main",
            "Augusta Road",
            "Overbrook",
            "Verdae",
            "Paris Mountain Edge",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_greenville_metro is is_in_greenville_metro


class TestGreenvilleFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["PERMIT_NUM", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["NewIssueDate"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["APPLICDATE"]
        assert PERMITS_FIELD_MAP["status"] == ["BP_STATUS", "Status"]
        assert PERMITS_FIELD_MAP["job_type"] == ["PERMIT_TYPE"]
        assert PERMITS_FIELD_MAP["cost"] == ["PERMIT_VALUATION"]
        assert PERMITS_FIELD_MAP["address_street"] == ["STREETADDRESS"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Greenville, SC"
        assert GREENVILLE_GEOCODE_CONTEXT == "Greenville, SC"

    def test_state_plane_coordinates_are_never_candidates(self):
        """X_COORD/Y_COORD are State Plane feet (SC zone, ≈1.58e6/1.08e6;
        some rows carry 0.0) — mapping them would emit feet as degrees.
        Coordinates come only from the outSR=4326 geometry lift."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        attrs = _FEATURE_490["attributes"]
        assert attrs["X_COORD"] > 90 and attrs["Y_COORD"] > 90  # feet, not degrees
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "latitude") is None
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "longitude") is None

    def test_no_borough_candidate_so_source_neighborhood_passes_none(self):
        """No neighborhood/district column exists on the layer (Omaha
        discipline): no borough candidate is declared, so
        source_neighborhood passes through as None on parsed events."""
        assert "borough" not in PERMITS_FIELD_MAP
        assert "neighborhood" not in PERMITS_FIELD_MAP

    def test_no_zipcode_or_bbl_candidates(self):
        """OWNER_ZIP is the owner's mailing zip (not the site zip) and the
        layer has no parcel/APN column — both stay undeclared."""
        assert "zipcode" not in PERMITS_FIELD_MAP
        assert "bbl" not in PERMITS_FIELD_MAP

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for values in PERMITS_FIELD_MAP.values() for c in values}
        assert mapped
        for col in PERMITS_FIELD_MAP["job_id"] + PERMITS_FIELD_MAP["status"]:
            assert col not in DROPPED_PII_COLUMNS
        for values in PERMITS_FIELD_MAP.values():
            for col in values:
                assert col not in DROPPED_PII_COLUMNS
        # The owner/contractor blocks are exactly what is dropped.
        assert {"OWNER_NAME", "OWNER_ADDR", "OWNER_ZIP",
                "CONTRACTOR_NAME", "CONT_ADDR", "CONT_ZIP"} <= set(DROPPED_PII_COLUMNS)

    def test_applidate_is_numeric_not_an_esri_date(self):
        assert first_mapped(_FEATURE_490["attributes"], PERMITS_FIELD_MAP, "filing_date") == 20260710.0
        assert isinstance(
            first_mapped(_FEATURE_636["attributes"], PERMITS_FIELD_MAP, "filing_date"), float
        )


class TestGreenvillePermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_FEATURE_490)
        assert record["latitude"] == pytest.approx(34.799886445526745)
        assert record["longitude"] == pytest.approx(-82.33757403747684)
        # The State Plane attributes ride along unmapped — never as degrees.
        assert record["X_COORD"] == 1598962.630905
        assert record["Y_COORD"] == 1082016.798228

    def test_flatten_iso_normalizes_the_watermark_only(self):
        record = _flatten(_FEATURE_595)
        assert record["NewIssueDate"] == _NEWISSUE_ISO
        # APPLICDATE is a numeric double, not a date field — untouched.
        assert record["APPLICDATE"] == 20260320.0

    def test_townhouse_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_490), city_id="greenville")
        assert event is not None
        assert event.city_id == "greenville"
        assert event.job_id == "2600002910"
        assert event.status == "IS"
        assert event.estimated_cost == pytest.approx(109591.0)
        assert event.address_street == "16   BROAD RIVER ST  "
        assert event.latitude == pytest.approx(34.799886445526745)
        assert event.longitude == pytest.approx(-82.33757403747684)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _NEWISSUE_ISO
        assert event.filing_date is None
        assert event.source_neighborhood is None
        assert event.zipcode == ""
        assert event.bbl is None

    def test_woodville_fixture_indexes_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_595), city_id="greenville")
        assert event is not None
        assert event.estimated_cost == pytest.approx(800000.0)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_greenville_metro(event.latitude, event.longitude)

    def test_gurley_fixture_valuation_and_containment(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_636), city_id="greenville")
        assert event is not None
        assert event.job_id == "2600002286"
        assert event.estimated_cost == pytest.approx(31714.0)
        assert event.address_street == "28   GURLEY AV  "
        assert is_in_greenville_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_share_the_co_newest_watermark(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        events = [
            permits.parse_socrata_row(_flatten(f), city_id="greenville")
            for f in (_FEATURE_490, _FEATURE_595, _FEATURE_636)
        ]
        assert all(e is not None for e in events)
        assert {e.issuance_date.isoformat() for e in events} == {_NEWISSUE_ISO}
        # Distinct permits occupy distinct res-9 cells.
        assert len({e.h3_res9 for e in events}) == 3

    def test_status_falls_back_to_the_status_column(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_490)
        record.pop("BP_STATUS")
        event = permits.parse_socrata_row(record, city_id="greenville")
        assert event is not None
        assert event.status == "M"

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_490)
        record.pop("PERMIT_NUM")
        event = permits.parse_socrata_row(record, city_id="greenville")
        assert event is not None
        assert event.job_id == "490"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_490)
        record.pop("PERMIT_NUM")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="greenville") is None

    def test_geometry_less_row_resolves_through_the_geocode_fallback(
        self, permits, monkeypatch
    ):
        """Rows arriving without geometry resolve via the ADR 0004 geocode
        supplement (needs_geocode=True). Call-args/counts are spine-volatile
        and not asserted — only the event outcome."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_490)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (34.8413, -82.4030),
        )
        event = permits.parse_socrata_row(record, city_id="greenville")
        assert event is not None
        assert event.city_id == "greenville"
        assert event.job_id == "2600002910"
        assert event.latitude == pytest.approx(34.8413)
        assert event.longitude == pytest.approx(-82.4030)
        assert event.h3_res7 is not None

    def test_geometry_less_row_dropped_when_geocode_fails(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_595)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="greenville") is None

    def test_state_plane_values_never_emit_as_degrees(self, permits, monkeypatch):
        """If State Plane feet ever leaked into latitude/longitude (a bad
        future map edit), the producer's projected-coordinate guard nulls
        them; the coordinate-less row then falls to geocode and must not
        carry fake degrees."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_490)
        record["latitude"] = record["X_COORD"]    # 1598962.630905 feet
        record["longitude"] = record["Y_COORD"]   # 1082016.798228 feet
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="greenville") is None

    def test_greenville_type_codes_stay_unclassified_at_the_leaf(
        self, permits, monkeypatch
    ):
        """PERMIT_TYPE codes (BLDG/DEMC/…) pass through as job_type
        candidates; finer classification (APPLIC_DESCRIPTION carries
        'NEW TOWNHOUSE' etc.) is analytics-side. BLDG/DEMC are not among
        the producer's recognized codes, so they land on OT honestly."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_490), city_id="greenville")
        assert event is not None
        assert event.job_type == JobType.OT
        record = _flatten(_FEATURE_636)
        record["PERMIT_TYPE"] = "DEMC"
        event = permits.parse_socrata_row(record, city_id="greenville")
        assert event is not None
        assert event.job_type == JobType.OT


class TestGreenvilleFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_greenville_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == GREENVILLE_PERMITS_ENDPOINT
        assert spec.watermark_col == "NewIssueDate"
        assert spec.id_keys == ["PERMIT_NUM"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 7000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "NewIssueDate DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Greenville, SC"
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_registered_feed_set_is_permits_only(self):
        assert set(GREENVILLE_FEED_SPECS) == {"permits"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_greenville_dataset("sla")
        assert "greenville" in str(exc.value)
        assert "permits" in str(exc.value)

    def test_endpoint_is_the_probed_mapserver(self):
        assert "citygis.greenvillesc.gov" in GREENVILLE_PERMITS_ENDPOINT
        assert (
            "InfoHUB/BuildingPermits_PriorTwoYears/MapServer/0"
            in GREENVILLE_PERMITS_ENDPOINT
        )
