"""Unit tests for the Bozeman, MT leaf (US-236): spatial module + field
maps + producer parse wiring.

Bozeman is a TWO-FEED PARTIAL metro on the City of Bozeman ArcGIS stack:
PERMITS (``BP_Comm_Dev_Report_Data_view/FeatureServer/0`` on hosted AGOL,
Tier 1, 24,338 rows, daily) and CRIME (``BPD_CFS_Public_30_Days``, Tier 1,
5,202 rows, 30-day rolling window, ADR 0004 native coordinates). 311 (no bulk
feed), SLA (no business-license registry), and Gallatin County deeds
(recorder not bulk-accessible) stay Tier 3.

Tests pass WITHOUT a spine registration (no CityId.BOZEMAN, no REGISTRY
assertions — "bozeman" stays a plain string). Spine-stable per the wave-7
leaf contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions.

Fixtures captured byte-verbatim 2026-08-28 (orderByFields=<watermark> DESC,
outFields=*, outSR=4326; newest watermark 1787814000000 =
2026-08-27T07:00:00+00:00 on both feeds). Fixtures are RAW ArcGIS features
(attributes + geometry); the tests run the real ``ArcGISClient._flatten_feature``
lift — geometry to latitude/longitude, epoch-ms to ISO — exactly as the live
producer path does. The permits view's LATITUDE/LONGITUDE attribute columns
are Montana State Plane feet (mixed-CRS trap) and are pinned unmapped.
"""

from unittest.mock import patch

import h3
import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_bozeman import (
    CRIME_FIELD_MAP,
    DROPPED_NONADDRESS_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.bozeman import (
    BOZEMAN_CFS_ENDPOINT,
    BOZEMAN_CITY_ID,
    BOZEMAN_DIVISION_BBOXES,
    BOZEMAN_DIVISIONS,
    BOZEMAN_FEED_SPECS,
    BOZEMAN_GEOCODE_CONTEXT,
    BOZEMAN_METRO_BBOX,
    BOZEMAN_PERMITS_ENDPOINT,
    BOZEMAN_SUBMARKETS,
    REGISTRATION,
    get_bozeman_dataset,
    is_in_bozeman_metro,
    is_in_greater_bozeman_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten_permits(feature):
    """Run the real ArcGIS flatten lift over a raw captured permit feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: PERMIT_ISSUE_DATE / PERMIT_EXPIRATION_DATE / PERMIT_STATUS_DATE /
    APPLICATION_DATE / APPL_STATUS_DATE / C_O_DATE_YMD are esriFieldTypeDate.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        feature,
        {
            "PERMIT_ISSUE_DATE",
            "PERMIT_EXPIRATION_DATE",
            "PERMIT_STATUS_DATE",
            "APPLICATION_DATE",
            "APPL_STATUS_DATE",
            "C_O_DATE_YMD",
        },
    )


def _flatten_crime(feature):
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, {"DATE"})


# Newest rows on the 2026-08-28 probe (orderByFields=PERMIT_ISSUE_DATE DESC,
# outSR=4326) from BP_Comm_Dev_Report_Data_view/FeatureServer/0. Byte-verbatim:
# Montana State Plane LATITUDE/LONGITUDE attribute feet (≈5.06e6/4.9e5),
# native WGS84 geometry, epoch-ms esri dates.
_FEATURE_REROOF_50000 = {
    "attributes": {
        "OBJECTID": 27621,
        "PERMIT_NUMBER": "2600041509",
        "PERMIT_ISSUE_DATE": 1787814000000,
        "VALUATION": 50000,
        "PERMIT_ADDL_DESCRIPTION": "RE-ROOF",
        "PERMIT_EXPIRATION_DATE": 1803366000000,
        "PERMIT_TYPE": "BUILDING PERMIT - VALUATION",
        "PERMIT_STATUS_DATE": 1787814000000,
        "APPLICATION_NUMBER": 41509,
        "APPLICATION_TYPE_CODE": "RR01",
        "APPLICATION_DATE": 1787727600000,
        "APPLICATION_TYPE": "RES REROOF",
        "APPLICATION_STATUS": "PERMITS ISSUED",
        "APPL_STATUS_DATE": 1787814000000,
        "APPLICATION_DESC": "asp to asp",
        "APPLICATION_SQUARE_FOOTAGE": 0,
        "APPLICATION_YEAR": 2026,
        "PLAN_REVIEWED_BY": "DH2",
        "TENANT_NAME": None,
        "LOCATION": "2411 PAR CT UNITS A & B",
        "LOCATION_ID": 55050,
        "C_O_DATE_YMD": None,
        "WORK_CATEGORY_DESC": "BRI RESIDENTIAL IMPROVE",
        "INTERNAL_REPORT_CATEGORY": "RE",
        "LATITUDE": 5061199.951859,
        "LONGITUDE": 498128.810838,
        "PERMIT_STATUS": "Permit Printed",
        "New_Dwelling_Units": None,
    },
    "geometry": {"x": -111.02403777763685, "y": 45.70435061183428},
}

_FEATURE_REROOF_13191 = {
    "attributes": {
        "OBJECTID": 27620,
        "PERMIT_NUMBER": "2600041506",
        "PERMIT_ISSUE_DATE": 1787814000000,
        "VALUATION": 13191,
        "PERMIT_ADDL_DESCRIPTION": "RE-ROOF",
        "PERMIT_EXPIRATION_DATE": 1803366000000,
        "PERMIT_TYPE": "BUILDING PERMIT - VALUATION",
        "PERMIT_STATUS_DATE": 1787814000000,
        "APPLICATION_NUMBER": 41506,
        "APPLICATION_TYPE_CODE": "RR01",
        "APPLICATION_DATE": 1787727600000,
        "APPLICATION_TYPE": "RES REROOF",
        "APPLICATION_STATUS": "PERMITS ISSUED",
        "APPL_STATUS_DATE": 1787814000000,
        "APPLICATION_DESC": "Asphalt to asphalt reroof.",
        "APPLICATION_SQUARE_FOOTAGE": 0,
        "APPLICATION_YEAR": 2026,
        "PLAN_REVIEWED_BY": "DH2",
        "TENANT_NAME": None,
        "LOCATION": "1116 S CEDARVIEW DR",
        "LOCATION_ID": 49510,
        "C_O_DATE_YMD": None,
        "WORK_CATEGORY_DESC": "BRI RESIDENTIAL IMPROVE",
        "INTERNAL_REPORT_CATEGORY": "RE",
        "LATITUDE": 5056251.82,
        "LONGITUDE": 498371.61,
        "PERMIT_STATUS": "Permit Printed",
        "New_Dwelling_Units": None,
    },
    "geometry": {"x": -111.0209021260546, "y": 45.65981384807137},
}

_FEATURE_SIGN_8213 = {
    "attributes": {
        "OBJECTID": 27617,
        "PERMIT_NUMBER": "2600041035",
        "PERMIT_ISSUE_DATE": 1787814000000,
        "VALUATION": 8213,
        "PERMIT_ADDL_DESCRIPTION": "SIGN PERMIT - NO ELECTRIC",
        "PERMIT_EXPIRATION_DATE": 1803366000000,
        "PERMIT_TYPE": "SIGN PERMIT",
        "PERMIT_STATUS_DATE": 1787814000000,
        "APPLICATION_NUMBER": 41035,
        "APPLICATION_TYPE_CODE": "SIGN",
        "APPLICATION_DATE": 1782370800000,
        "APPLICATION_TYPE": "SIGN PERMIT",
        "APPLICATION_STATUS": "PERMITS ISSUED",
        "APPL_STATUS_DATE": 1787814000000,
        "APPLICATION_DESC": "Fabricate and install (1) double-sided push-throug",
        "APPLICATION_SQUARE_FOOTAGE": 0,
        "APPLICATION_YEAR": 2026,
        "PLAN_REVIEWED_BY": "SLS",
        "TENANT_NAME": "Quaking Aspen",
        "LOCATION": "611 N WALLACE AVE",
        "LOCATION_ID": 32000,
        "C_O_DATE_YMD": None,
        "WORK_CATEGORY_DESC": "ELECTRICAL PERMITS",
        "INTERNAL_REPORT_CATEGORY": None,
        "LATITUDE": 5059182.29,
        "LONGITUDE": 497726.91,
        "PERMIT_STATUS": "Permit Printed",
        "New_Dwelling_Units": None,
    },
    "geometry": {"x": -111.02919124831567, "y": 45.686188786641985},
}

_WATERMARK_ISO = "2026-08-27T07:00:00+00:00"

# Newest rows on the 2026-08-28 probe (orderByFields=DATE DESC, outSR=4326)
# from BPD_CFS_Public_30_Days/FeatureServer/0. Byte-verbatim: native WGS84
# geometry, DATE epoch-ms, TIME as a string.
_CFS_NOISE = {
    "attributes": {
        "OBJECTID": 380470,
        "INCIDENT_NUMBER": "CFS26-125439",
        "ALL_CALL_TYPES": "NOISE - NOISE",
        "PRIMARY_CODE": "NOISE",
        "PRIMARY_DESCRIPTION": None,
        "DATE": 1787814000000,
        "TIME": "22:32",
        "RESPONDING_AGENCIES": "BPD",
        "RESULT": "Gone on Arival/Unable to Locate",
        "CASE_NUMBER": "N/A",
    },
    "geometry": {"x": -111.05831324416214, "y": 45.68214647539046},
}

_CFS_FOLLOW_UP = {
    "attributes": {
        "OBJECTID": 380469,
        "INCIDENT_NUMBER": "CFS26-125427",
        "ALL_CALL_TYPES": "FOLLOW UP - FOLLOW UP",
        "PRIMARY_CODE": "FOLLOW UP",
        "PRIMARY_DESCRIPTION": None,
        "DATE": 1787814000000,
        "TIME": "22:16",
        "RESPONDING_AGENCIES": "BPD",
        "RESULT": "Documented",
        "CASE_NUMBER": "N/A",
    },
    "geometry": {"x": -111.05706687931614, "y": 45.67936267388674},
}

_CFS_TRAFFIC_CRIME = {
    "attributes": {
        "OBJECTID": 380467,
        "INCIDENT_NUMBER": "CFS26-125396",
        "ALL_CALL_TYPES": "TRAFFIC CRIME - TRAFFIC CRIME - TC",
        "PRIMARY_CODE": "TRAFFIC CRIME",
        "PRIMARY_DESCRIPTION": None,
        "DATE": 1787814000000,
        "TIME": "21:37",
        "RESPONDING_AGENCIES": "BPD",
        "RESULT": "Case Generated",
        "CASE_NUMBER": "BI26-03732",
    },
    "geometry": {"x": -111.05706687931614, "y": 45.67936267388674},
}


class TestBozemanSpatial:
    def test_metro_bbox_sanity(self):
        assert BOZEMAN_METRO_BBOX["min_lat"] < BOZEMAN_METRO_BBOX["max_lat"]
        assert BOZEMAN_METRO_BBOX["min_lng"] < BOZEMAN_METRO_BBOX["max_lng"]

    def test_is_in_bozeman_metro_rejects_missing_coordinates(self):
        assert is_in_bozeman_metro(None, None) is False
        assert is_in_bozeman_metro(45.6777, None) is False
        assert is_in_bozeman_metro(None, -111.0387) is False

    def test_is_in_bozeman_metro_rejects_other_cities(self):
        assert is_in_bozeman_metro(45.695, -110.573) is False   # Livingston, MT
        assert is_in_bozeman_metro(45.7833, -108.5007) is False  # Billings, MT
        assert is_in_bozeman_metro(46.8797, -113.9933) is False  # Missoula, MT

    def test_downtown_anchors_are_contained(self):
        assert is_in_bozeman_metro(45.6777, -111.0387)  # Downtown Main & Willson
        assert is_in_bozeman_metro(45.6699, -111.0482)  # MSU campus
        assert is_in_bozeman_metro(45.6870, -111.0280)  # Story Mill

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (
            _FEATURE_REROOF_50000,
            _FEATURE_REROOF_13191,
            _FEATURE_SIGN_8213,
            _CFS_NOISE,
            _CFS_FOLLOW_UP,
            _CFS_TRAFFIC_CRIME,
        ):
            assert is_in_bozeman_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in BOZEMAN_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= BOZEMAN_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= BOZEMAN_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= BOZEMAN_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= BOZEMAN_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in BOZEMAN_SUBMARKETS.items():
            bbox = BOZEMAN_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in BOZEMAN_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(BOZEMAN_SUBMARKETS)

    def test_submarkets_carry_the_bozeman_city_id(self):
        assert {m.city_id for m in BOZEMAN_SUBMARKETS.values()} == {"bozeman"}

    def test_city_id_and_registration_shape(self):
        assert BOZEMAN_CITY_ID == "bozeman"
        assert REGISTRATION.metro_bbox is BOZEMAN_METRO_BBOX
        assert REGISTRATION.submarkets is BOZEMAN_SUBMARKETS
        assert REGISTRATION.division_bboxes is BOZEMAN_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_bozeman_metro
        assert len(REGISTRATION.divisions) == 7
        assert len(BOZEMAN_SUBMARKETS) == 10

    def test_required_real_neighborhoods_present(self):
        assert set(BOZEMAN_SUBMARKETS) == {
            "Downtown",
            "Bozeman Armory",
            "North 7th Avenue",
            "Bozeman Health",
            "North Park",
            "Story Mill",
            "South Bozeman Tech",
            "Valley West",
            "Bridger College",
            "Baxter/Highland",
        }

    def test_divisions_are_evidence_anchored(self):
        # All seven divisions map to real Bozeman geographies (TIF/URD
        # districts + named corridors), not fabricated grid cells.
        assert set(BOZEMAN_DIVISION_BBOXES) == {
            "DOWNTOWN",
            "MIDTOWN",
            "NORTH_PARK",
            "STORY_MILL",
            "SOUTH_TECH",
            "VALLEY_WEST",
            "BRIDGER_COLLEGE",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_bozeman_metro is is_in_bozeman_metro


class TestBozemanFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == [
            "PERMIT_NUMBER", "APPLICATION_NUMBER", "OBJECTID",
        ]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["PERMIT_ISSUE_DATE"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["APPLICATION_DATE"]
        assert PERMITS_FIELD_MAP["status"] == ["PERMIT_STATUS", "APPLICATION_STATUS"]
        assert PERMITS_FIELD_MAP["job_type"] == ["PERMIT_TYPE", "APPLICATION_TYPE"]
        assert PERMITS_FIELD_MAP["cost"] == ["VALUATION"]
        assert PERMITS_FIELD_MAP["address_street"] == ["LOCATION"]
        assert PERMITS_FIELD_MAP["proposed_units"] == ["New_Dwelling_Units"]

    def test_crime_map_reads_live_columns(self):
        assert CRIME_FIELD_MAP["incident_id"] == [
            "INCIDENT_NUMBER", "CASE_NUMBER", "OBJECTID",
        ]
        assert CRIME_FIELD_MAP["offense_type"] == [
            "ALL_CALL_TYPES", "PRIMARY_CODE", "PRIMARY_DESCRIPTION",
        ]
        assert CRIME_FIELD_MAP["occurred_date"] == ["DATE"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP, "crime": CRIME_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Bozeman, MT"
        assert BOZEMAN_GEOCODE_CONTEXT == "Bozeman, MT"

    def test_state_plane_coordinates_are_never_candidates(self):
        """LATITUDE/LONGITUDE attribute columns are Montana State Plane
        (NAD83 26912) feet — mapping them would emit feet as degrees.
        Coordinates come only from the outSR=4326 geometry lift."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        assert "latitude" not in CRIME_FIELD_MAP
        assert "longitude" not in CRIME_FIELD_MAP
        attrs = _FEATURE_REROOF_50000["attributes"]
        assert attrs["LATITUDE"] > 90 and attrs["LONGITUDE"] > 90  # feet, not degrees
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "latitude") is None
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "longitude") is None

    def test_no_borough_or_zip_candidates(self):
        """No neighborhood/district or site-zip column exists on either layer
        (Omaha discipline): borough and zipcode stay undeclared."""
        assert "borough" not in PERMITS_FIELD_MAP
        assert "neighborhood" not in PERMITS_FIELD_MAP
        assert "borough" not in CRIME_FIELD_MAP
        assert "zipcode" not in PERMITS_FIELD_MAP
        assert "zipcode" not in CRIME_FIELD_MAP
        assert "bbl" not in PERMITS_FIELD_MAP

    def test_dropped_columns_are_never_candidates(self):
        mapped = {
            c
            for values in (*PERMITS_FIELD_MAP.values(), *CRIME_FIELD_MAP.values())
            for c in values
        }
        assert mapped
        for col in DROPPED_NONADDRESS_COLUMNS:
            assert col not in mapped, col
        # The State Plane feet columns are exactly what is dropped.
        assert {"LATITUDE", "LONGITUDE"} <= set(DROPPED_NONADDRESS_COLUMNS)


class TestBozemanPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten_permits(_FEATURE_REROOF_50000)
        assert record["latitude"] == pytest.approx(45.70435061183428)
        assert record["longitude"] == pytest.approx(-111.02403777763685)
        # The State Plane attributes ride along unmapped — never as degrees.
        assert record["LATITUDE"] == 5061199.951859
        assert record["LONGITUDE"] == 498128.810838

    def test_flatten_iso_normalizes_the_dates(self):
        record = _flatten_permits(_FEATURE_REROOF_13191)
        assert record["PERMIT_ISSUE_DATE"] == _WATERMARK_ISO
        assert record["APPLICATION_DATE"] == "2026-08-26T07:00:00+00:00"
        assert record["PERMIT_EXPIRATION_DATE"] == "2027-02-23T07:00:00+00:00"

    def test_reroof_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten_permits(_FEATURE_REROOF_50000), city_id="bozeman")
        assert event is not None
        assert event.city_id == "bozeman"
        assert event.job_id == "2600041509"
        assert event.status == "Permit Printed"
        assert event.estimated_cost == pytest.approx(50000.0)
        assert event.address_street == "2411 PAR CT UNITS A & B"
        assert event.latitude == pytest.approx(45.70435061183428)
        assert event.longitude == pytest.approx(-111.02403777763685)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _WATERMARK_ISO
        assert event.source_neighborhood is None
        assert event.zipcode == ""
        assert event.bbl is None

    def test_cedarview_fixture_indexes_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten_permits(_FEATURE_REROOF_13191), city_id="bozeman")
        assert event is not None
        assert event.estimated_cost == pytest.approx(13191.0)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_bozeman_metro(event.latitude, event.longitude)

    def test_sign_fixture_valuation_and_containment(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten_permits(_FEATURE_SIGN_8213), city_id="bozeman")
        assert event is not None
        assert event.job_id == "2600041035"
        assert event.estimated_cost == pytest.approx(8213.0)
        assert event.address_street == "611 N WALLACE AVE"
        assert is_in_bozeman_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_share_the_watermark(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        events = [
            permits.parse_socrata_row(_flatten_permits(f), city_id="bozeman")
            for f in (_FEATURE_REROOF_50000, _FEATURE_REROOF_13191, _FEATURE_SIGN_8213)
        ]
        assert all(e is not None for e in events)
        assert {e.issuance_date.isoformat() for e in events} == {_WATERMARK_ISO}
        # Distinct permits occupy distinct res-9 cells.
        assert len({e.h3_res9 for e in events}) == 3

    def test_status_falls_back_to_application_status(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_FEATURE_REROOF_50000)
        record.pop("PERMIT_STATUS")
        event = permits.parse_socrata_row(record, city_id="bozeman")
        assert event is not None
        assert event.status == "PERMITS ISSUED"

    def test_job_id_falls_back_to_application_number(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_FEATURE_REROOF_50000)
        record.pop("PERMIT_NUMBER")
        event = permits.parse_socrata_row(record, city_id="bozeman")
        assert event is not None
        assert event.job_id == "41509"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_FEATURE_REROOF_50000)
        record.pop("PERMIT_NUMBER")
        record.pop("APPLICATION_NUMBER")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="bozeman") is None

    def test_geometry_less_row_resolves_through_the_geocode_fallback(
        self, permits, monkeypatch
    ):
        """Rows arriving without geometry resolve via the ADR 0004 geocode
        supplement (needs_geocode=True). Call-args/counts are spine-volatile
        and not asserted — only the event outcome."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_FEATURE_REROOF_50000)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (45.6777, -111.0387),
        )
        event = permits.parse_socrata_row(record, city_id="bozeman")
        assert event is not None
        assert event.city_id == "bozeman"
        assert event.job_id == "2600041509"
        assert event.latitude == pytest.approx(45.6777)
        assert event.longitude == pytest.approx(-111.0387)
        assert event.h3_res7 is not None

    def test_geometry_less_row_dropped_when_geocode_fails(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_FEATURE_REROOF_50000)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="bozeman") is None

    def test_state_plane_values_never_emit_as_degrees(self, permits, monkeypatch):
        """If State Plane feet ever leaked into latitude/longitude (a bad
        future map edit), the producer's projected-coordinate guard nulls
        them; the coordinate-less row then falls to geocode and must not
        carry fake degrees."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_FEATURE_REROOF_50000)
        record["latitude"] = record["LATITUDE"]   # 5061199.951859 feet
        record["longitude"] = record["LONGITUDE"]  # 498128.810838 feet
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="bozeman") is None

    def test_bozeman_type_codes_classify_honestly(self, permits, monkeypatch):
        """PERMIT_TYPE strings (RES REROOF) land on OT honestly; SIGN PERMIT
        is recognized by the producer's SIGN keyword chain (JobType.SG)."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten_permits(_FEATURE_REROOF_50000), city_id="bozeman")
        assert event is not None
        assert event.job_type == JobType.OT
        event = permits.parse_socrata_row(_flatten_permits(_FEATURE_SIGN_8213), city_id="bozeman")
        assert event is not None
        assert event.job_type == JobType.SG


class TestBozemanCrimeParsing:
    @pytest.fixture
    def crime(self):
        with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
            from src.producers.crime_incidents_producer import CrimeIncidentsProducer

            return CrimeIncidentsProducer()

    def test_noise_fixture_parses_with_native_geometry(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(_flatten_crime(_CFS_NOISE), city_id="bozeman")
        assert event is not None
        assert event.city_id == "bozeman"
        assert event.incident_id == "CFS26-125439"
        assert event.offense_type == "NOISE - NOISE"
        assert event.offense_class == "PART2"
        assert event.latitude == pytest.approx(45.68214647539046)
        assert event.longitude == pytest.approx(-111.05831324416214)
        assert is_in_bozeman_metro(event.latitude, event.longitude)
        assert event.h3_res7 is not None
        assert (event.occurred_date.year, event.occurred_date.month, event.occurred_date.day) == (
            2026, 8, 27,
        )

    def test_traffic_crime_fixture_classifies_part2(self, crime, monkeypatch):
        """TRAFFIC CRIME / NOISE / FOLLOW UP are all Part-2 under the UCR
        keyword classifier — none carry PART1 keywords."""
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(_flatten_crime(_CFS_TRAFFIC_CRIME), city_id="bozeman")
        assert event is not None
        assert event.incident_id == "CFS26-125396"
        assert event.offense_type == "TRAFFIC CRIME - TRAFFIC CRIME - TC"
        assert event.offense_class == "PART2"
        assert event.address is None

    def test_h3_hierarchy_is_consistent(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(_flatten_crime(_CFS_FOLLOW_UP), city_id="bozeman")
        assert event is not None
        assert h3.cell_to_parent(event.h3_res9, 8) == event.h3_res8
        assert h3.cell_to_parent(event.h3_res9, 7) == event.h3_res7

    def test_null_geometry_row_drops_not_geocoded(self, crime, monkeypatch):
        """needs_geocode stays False for crime: no address column means a
        geocoder has nothing to geocode, so null-geometry rows drop."""
        _patch_resolve(monkeypatch, "crime")
        row = _flatten_crime(_CFS_NOISE)
        row.pop("latitude")
        row.pop("longitude")
        assert crime.parse_socrata_row(row, city_id="bozeman") is None


class TestBozemanFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_bozeman_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == BOZEMAN_PERMITS_ENDPOINT
        assert spec.watermark_col == "PERMIT_ISSUE_DATE"
        assert spec.id_keys == ["PERMIT_NUMBER", "APPLICATION_NUMBER", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 1000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "PERMIT_ISSUE_DATE DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Bozeman, MT"
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_crime_spec_matches_live_layer(self):
        spec = get_bozeman_dataset(FeedType.CRIME)
        assert spec.platform == "arcgis"
        assert spec.endpoint == BOZEMAN_CFS_ENDPOINT
        assert spec.watermark_col == "DATE"
        assert spec.id_keys == ["INCIDENT_NUMBER", "CASE_NUMBER", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 20000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "DATE DESC"
        assert spec.interval_seconds == 300.0
        assert spec.needs_geocode is False
        assert spec.field_map == CRIME_FIELD_MAP
        assert spec.topic == "raw.municipal.crime"

    def test_registered_feed_set_is_permits_and_crime_only(self):
        assert set(BOZEMAN_FEED_SPECS) == {"permits", "crime"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_bozeman_dataset("sla")
        assert "bozeman" in str(exc.value)
        assert "permits" in str(exc.value)
        assert "crime" in str(exc.value)

    def test_endpoints_are_the_probed_services(self):
        assert "services3.arcgis.com/f4hk1qcfxRJ0L2BU" in BOZEMAN_PERMITS_ENDPOINT
        assert "BP_Comm_Dev_Report_Data_view/FeatureServer/0" in BOZEMAN_PERMITS_ENDPOINT
        assert "gisweb.bozeman.net/hosted" in BOZEMAN_CFS_ENDPOINT
        assert "BPD_CFS_Public_30_Days/FeatureServer/0" in BOZEMAN_CFS_ENDPOINT
