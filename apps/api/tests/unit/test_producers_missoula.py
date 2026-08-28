"""Unit tests for the Missoula, MT leaf (US-235): spatial module + field
maps + producer parse wiring.

Missoula is a ONE-FEED PARTIAL metro on the city's official AGOL org
(``services.arcgis.com/HfwHS0BxZBQ1E5DY``, behind the
``missoulamaps-cityofmissoula.hub.arcgis.com`` Hub):
``AddressesWithPermits_mso`` (Tier 1, 122,448 rows). 311 (no general feed;
the county's ``311_Debris_Overgrowth`` is a stale Pittsburgh mirror), SLA (no
feed), and deeds (no bulk feed) stay unregistered — rejection evidence lives
in the city module docstring.

Tests pass WITHOUT a spine registration (no CityId.MISSOULA, no REGISTRY
assertions — "missoula" stays a plain string). Spine-stable per the leaf
contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from
``AddressesWithPermits_mso/FeatureServer/0`` (newest rows,
``orderByFields=ApplicationDate DESC``, ``outSR=4326``); newest watermark
``1787788800000`` = 2026-08-27T00:00:00+00:00. The store SR is WKID 102700
(Montana State Plane, meters) but the host honors outSR, so geometry arrives
as WGS84 degrees.

Fixtures are RAW ArcGIS features (attributes + geometry); the tests run the
real ``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO for the layer's two esriFieldTypeDate columns
(ApplicationDate, RecordStatusDate) — before parsing, exactly as the live
producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_missoula import (
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.missoula import (
    MISSOULA_CITY_ID,
    MISSOULA_DIVISION_BBOXES,
    MISSOULA_DIVISIONS,
    MISSOULA_FEED_SPECS,
    MISSOULA_GEOCODE_CONTEXT,
    MISSOULA_METRO_BBOX,
    MISSOULA_PERMITS_ENDPOINT,
    MISSOULA_SUBMARKETS,
    REGISTRATION,
    get_missoula_dataset,
    is_in_greater_missoula_metro,
    is_in_missoula_metro,
)

PERMITS_DATE_FIELDS = {"ApplicationDate", "RecordStatusDate"}


def _patch_resolve(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["permits"],
    )


def _flatten_permits(feature):
    """Run the real ArcGIS flatten lift over a raw captured permit feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: ApplicationDate and RecordStatusDate are esriFieldTypeDate.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, PERMITS_DATE_FIELDS)


# ---------------------------------------------------------------------------
# Byte-verbatim permit fixtures — 2026-08-28 probe (newest ApplicationDate
# rows, all 1787788800000 = 2026-08-27). No cost/valuation column exists on
# the layer, so none appears in the fixtures.
# ---------------------------------------------------------------------------
_PERMIT_1 = {
    "attributes": {
        "B1_PER_TYPE": "Utility Excavation",
        "B1_PER_SUB_TYPE": "Sanitary Sewer Service",
        "ApplicationDate": 1787788800000,
        "RecordID": "2026-MSS-SWR-00946",
        "RecordStatus": "Open",
        "RecordStatusDate": 1787829825393,
        "StatusFilter": "Open",
        "RecordName": "Sanitary Sewer Service Permit",
        "AddressID": 1049062,
        "Address": "7206 SOPHIE DR",
        "DescriptionOfWork": "NSFR / VB / R3-U / SINGLE STORY / 6.12 // Install new gravity sewer service connection from stub to building.",
        "FullAddress": "7206 SOPHIE DR",
        "OBJECTID": 1,
    },
    "geometry": {
        "x": -114.07397537540095,
        "y": 46.805069919284485,
    },
}

_PERMIT_2 = {
    "attributes": {
        "B1_PER_TYPE": "Utility Excavation",
        "B1_PER_SUB_TYPE": "Water Service",
        "ApplicationDate": 1787788800000,
        "RecordID": "2026-MSS-WTR-01054",
        "RecordStatus": "Issued",
        "RecordStatusDate": 1787788800000,
        "StatusFilter": "Open",
        "RecordName": "Water Service Permit",
        "AddressID": 16844,
        "Address": "2140 W KENT AVE",
        "DescriptionOfWork": "Replacing the curb box and removing the tree in front lawn.",
        "FullAddress": "2140 W KENT AVE",
        "OBJECTID": 2,
    },
    "geometry": {
        "x": -114.03120952738442,
        "y": 46.8516829403805,
    },
}

_PERMIT_7 = {
    "attributes": {
        "B1_PER_TYPE": "Commercial Construction",
        "B1_PER_SUB_TYPE": "NA",
        "ApplicationDate": 1787788800000,
        "RecordID": "2026-MSS-COM-00161",
        "RecordStatus": "Open",
        "RecordStatusDate": 1787825628277,
        "StatusFilter": "Open",
        "RecordName": "Building Commercial",
        "AddressID": 35743,
        "Address": "5280 GRANT CREEK RD",
        "DescriptionOfWork": "126 Guestroom renovations, Replacing tubs and fixtures in bathrooms, moving outlets for new furniture layout in living space  \n\nInstall AFCI  in each room",
        "FullAddress": "5280 GRANT CREEK RD",
        "OBJECTID": 7,
    },
    "geometry": {
        "x": -114.03186490398394,
        "y": 46.91345980770687,
    },
}

_NEWEST_APPLICATION_ISO = "2026-08-27T00:00:00+00:00"


class TestMissoulaSpatial:
    def test_metro_bbox_sanity(self):
        assert MISSOULA_METRO_BBOX["min_lat"] < MISSOULA_METRO_BBOX["max_lat"]
        assert MISSOULA_METRO_BBOX["min_lng"] < MISSOULA_METRO_BBOX["max_lng"]

    def test_is_in_missoula_metro_rejects_missing_coordinates(self):
        assert is_in_missoula_metro(None, None) is False
        assert is_in_missoula_metro(46.8721, None) is False
        assert is_in_missoula_metro(None, -113.9940) is False

    def test_is_in_missoula_metro_rejects_other_cities(self):
        assert is_in_missoula_metro(46.5857, -112.0272) is False   # Helena
        assert is_in_missoula_metro(45.6770, -111.0429) is False   # Bozeman
        assert is_in_missoula_metro(47.6588, -117.4260) is False   # Spokane
        assert is_in_missoula_metro(46.6061, -112.0232) is False   # Boulder, MT

    def test_missoula_anchors_are_contained(self):
        assert is_in_missoula_metro(46.8721, -113.9940)  # Heart of Missoula
        assert is_in_missoula_metro(46.8595, -113.9842)  # University District
        assert is_in_missoula_metro(46.8380, -114.0200)  # Southgate Triangle
        assert is_in_missoula_metro(46.8780, -114.0070)  # Rose Park
        assert is_in_missoula_metro(46.8010, -114.0550)  # Miller Creek
        assert is_in_missoula_metro(46.9100, -114.0650)  # Grant Creek

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_PERMIT_1, _PERMIT_2, _PERMIT_7):
            assert is_in_missoula_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in MISSOULA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= MISSOULA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= MISSOULA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= MISSOULA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= MISSOULA_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in MISSOULA_SUBMARKETS.items():
            bbox = MISSOULA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in MISSOULA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(MISSOULA_SUBMARKETS)

    def test_submarkets_carry_the_missoula_city_id(self):
        assert {m.city_id for m in MISSOULA_SUBMARKETS.values()} == {"missoula"}

    def test_city_id_and_registration_shape(self):
        assert MISSOULA_CITY_ID == "missoula"
        assert REGISTRATION.metro_bbox is MISSOULA_METRO_BBOX
        assert REGISTRATION.submarkets is MISSOULA_SUBMARKETS
        assert REGISTRATION.division_bboxes is MISSOULA_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_missoula_metro
        assert len(REGISTRATION.divisions) == 7
        assert len(MISSOULA_SUBMARKETS) == 20

    def test_required_real_neighborhoods_present(self):
        """All 20 submarkets are official City of Missoula neighborhoods from
        the live Neighborhoods_mso layer (2026-08-28 probe)."""
        assert set(MISSOULA_SUBMARKETS) == {
            "Heart of Missoula",
            "Riverfront",
            "University District",
            "Franklin to the Fort",
            "Lewis & Clark",
            "Southgate Triangle",
            "South 39th Street",
            "Two Rivers",
            "Westside",
            "Rose Park",
            "River Road",
            "Moose Can Gully",
            "Northside",
            "Grant Creek",
            "Marshall Canyon",
            "Lower Rattlesnake",
            "Upper Rattlesnake",
            "Captain John Mullan",
            "Miller Creek",
            "Farviews / Pattee Canyon",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_missoula_metro is is_in_missoula_metro


class TestMissoulaFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["RecordID", "OBJECTID"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["ApplicationDate"]
        assert PERMITS_FIELD_MAP["status"] == ["RecordStatus"]
        assert PERMITS_FIELD_MAP["job_type"] == ["B1_PER_TYPE", "B1_PER_SUB_TYPE"]
        assert PERMITS_FIELD_MAP["description"] == ["DescriptionOfWork"]
        assert PERMITS_FIELD_MAP["address_street"] == ["Address", "FullAddress"]

    def test_no_issuance_or_cost_candidates(self):
        """The live layer carries no issuance-date and no cost/valuation
        column; the map must not invent candidates for either."""
        assert "issuance_date" not in PERMITS_FIELD_MAP
        assert "cost" not in PERMITS_FIELD_MAP

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Missoula, MT"
        assert MISSOULA_GEOCODE_CONTEXT == "Missoula, MT"

    def test_no_coordinate_candidates_on_the_map(self):
        """Coordinates come only from the outSR=4326 geometry lift — no
        latitude/longitude candidates may exist."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        attrs = _PERMIT_1["attributes"]
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "latitude") is None
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "longitude") is None

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for v in PERMITS_FIELD_MAP.values() for c in v}
        assert mapped
        assert all(c not in DROPPED_PII_COLUMNS for c in mapped)
        # The live layer carries no person/contractor/phone columns at all.
        assert DROPPED_PII_COLUMNS == ()

    def test_record_status_date_is_never_a_candidate(self):
        """RecordStatusDate is the status-change timestamp, not an issuance
        date — it must never be mapped onto issuance_date."""
        mapped = {c for v in PERMITS_FIELD_MAP.values() for c in v}
        assert "RecordStatusDate" not in mapped


class TestMissoulaPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten_permits(_PERMIT_1)
        assert record["latitude"] == pytest.approx(46.805069919284485)
        assert record["longitude"] == pytest.approx(-114.07397537540095)

    def test_flatten_iso_normalizes_the_date_columns(self):
        record = _flatten_permits(_PERMIT_1)
        assert record["ApplicationDate"] == _NEWEST_APPLICATION_ISO
        assert record["RecordStatusDate"] == "2026-08-27T11:23:45.393000+00:00"

    def test_sohpie_drive_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch)
        event = permits.parse_socrata_row(_flatten_permits(_PERMIT_1), city_id="missoula")
        assert event is not None
        assert event.city_id == "missoula"
        assert event.job_id == "2026-MSS-SWR-00946"
        assert event.status == "Open"
        assert event.address_street == "7206 SOPHIE DR"
        assert event.latitude == pytest.approx(46.805069919284485)
        assert event.longitude == pytest.approx(-114.07397537540095)
        assert event.estimated_cost == 0.0
        assert event.issuance_date is None
        assert event.filing_date is not None
        assert event.filing_date.isoformat() == _NEWEST_APPLICATION_ISO
        assert event.h3_res7 is not None
        assert is_in_missoula_metro(event.latitude, event.longitude)

    def test_kent_ave_fixture_parses_and_indexes_h3(self, permits, monkeypatch):
        _patch_resolve(monkeypatch)
        event = permits.parse_socrata_row(_flatten_permits(_PERMIT_2), city_id="missoula")
        assert event is not None
        assert event.job_id == "2026-MSS-WTR-01054"
        assert event.status == "Issued"
        assert event.address_street == "2140 W KENT AVE"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_missoula_metro(event.latitude, event.longitude)

    def test_grant_creek_fixture_parses_commercial_construction(self, permits, monkeypatch):
        _patch_resolve(monkeypatch)
        event = permits.parse_socrata_row(_flatten_permits(_PERMIT_7), city_id="missoula")
        assert event is not None
        assert event.job_id == "2026-MSS-COM-00161"
        assert event.status == "Open"
        assert event.address_street == "5280 GRANT CREEK RD"
        assert is_in_missoula_metro(event.latitude, event.longitude)

    def test_missoula_work_types_stay_unclassified_at_the_leaf(self, permits, monkeypatch):
        """B1_PER_TYPE spellings ('Utility Excavation', 'Commercial
        Construction') carry none of the producer's recognized codes, so they
        land on OT honestly."""
        _patch_resolve(monkeypatch)
        for feature in (_PERMIT_1, _PERMIT_2, _PERMIT_7):
            event = permits.parse_socrata_row(_flatten_permits(feature), city_id="missoula")
            assert event is not None
            assert event.job_type == JobType.OT

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch)
        record = _flatten_permits(_PERMIT_1)
        record.pop("RecordID")
        event = permits.parse_socrata_row(record, city_id="missoula")
        assert event is not None
        assert event.job_id == "1"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch)
        record = _flatten_permits(_PERMIT_1)
        record.pop("RecordID")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="missoula") is None

    def test_geometry_less_row_dropped_when_geocode_fails(self, permits, monkeypatch):
        """The layer's geometry lift is the sole locator; a row that arrives
        without coordinates and cannot geocode must be dropped, not emit fake
        degrees."""
        _patch_resolve(monkeypatch)
        record = _flatten_permits(_PERMIT_1)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="missoula") is None

    def test_state_plane_feet_never_emit_as_degrees(self, permits, monkeypatch):
        """The store SR is WKID 102700 state-plane meters; if projected values
        ever leaked into latitude/longitude (a bad future map edit), the
        producer's projected-coordinate guard nulls them and the coordinate-
        less row falls to geocode. With geocode failing, the row must not
        carry fake degrees."""
        _patch_resolve(monkeypatch)
        record = _flatten_permits(_PERMIT_1)
        record["latitude"] = 824367.0090716924     # WKID 102700 meters for this parcel
        record["longitude"] = 964909.1837052852
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="missoula") is None


class TestMissoulaFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_missoula_dataset("permits")
        assert spec.platform == "arcgis"
        assert spec.endpoint == MISSOULA_PERMITS_ENDPOINT
        assert spec.watermark_col == "ApplicationDate"
        assert spec.id_keys == ["RecordID", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 1000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "ApplicationDate DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_registered_feed_set_is_permits_only(self):
        assert set(MISSOULA_FEED_SPECS) == {"permits"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_missoula_dataset("sla")
        assert "missoula" in str(exc.value)
        assert "permits" in str(exc.value)

    def test_endpoint_is_the_probed_city_agol_layer(self):
        assert "services.arcgis.com/HfwHS0BxZBQ1E5DY" in MISSOULA_PERMITS_ENDPOINT
        assert "AddressesWithPermits_mso/FeatureServer/0" in MISSOULA_PERMITS_ENDPOINT
