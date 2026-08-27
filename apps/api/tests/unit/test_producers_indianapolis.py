"""Contract tests for Indianapolis, IN (ArcGIS RIMAC 311 service requests)."""

import pytest

from src.spatial.cities.indianapolis import (
    INDIANAPOLIS_DIVISION_BBOXES,
    INDIANAPOLIS_DIVISIONS,
    INDIANAPOLIS_METRO_BBOX,
    INDIANAPOLIS_SUBMARKETS,
    is_in_indianapolis_metro,
)
from src.spatial.city_registry import CityId, FeedType

COMPLAINTS_311_FIELD_MAP = {
    "incident_id": ["SERVICEREQUESTID", "EXTERNALSERVICEREQUEST"],
    "created_date": ["REQUESTEDDATETIME"],
    "closed_date": ["CLOSEDDATETIME"],
    "status": ["STATUS"],
    "complaint_type": ["ACTIVITY", "SERVICENAME"],
    "incident_address": ["ADDRESS"],
    "borough": ["COUNCILDISTRICT"],
    "zipcode": ["ZIPCODE"],
    "latitude": ["LAT"],
    "longitude": ["LONG_"],
}


def test_indianapolis_geometry_is_self_consistent():
    assert is_in_indianapolis_metro(39.7684, -86.1581)
    # Live row coordinates captured 2026-08-24 (W Epler Ave, W McCarty St, Congress Ave).
    assert is_in_indianapolis_metro(39.68581414, -86.18702727)
    assert is_in_indianapolis_metro(39.75639245, -86.19856652)
    assert is_in_indianapolis_metro(39.81226184, -86.1667799)
    assert not is_in_indianapolis_metro(41.8781, -87.6298)  # Chicago
    assert not is_in_indianapolis_metro(None, None)
    for name, bbox in INDIANAPOLIS_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= INDIANAPOLIS_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= INDIANAPOLIS_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= INDIANAPOLIS_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= INDIANAPOLIS_METRO_BBOX["max_lng"], name
    claimed = [name for division in INDIANAPOLIS_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(INDIANAPOLIS_SUBMARKETS)
    assert {meta.city_id for meta in INDIANAPOLIS_SUBMARKETS.values()} == {"indianapolis"}
    assert {meta.borough for meta in INDIANAPOLIS_SUBMARKETS.values()} == set(INDIANAPOLIS_DIVISIONS)


def test_indianapolis_registers_only_the_311_feed():
    from src.spatial.city_registry import REGISTRY, normalize_city

    city = CityId.INDIANAPOLIS
    assert normalize_city("indianapolis") is city
    assert normalize_city("indianapolis_in") is city
    assert normalize_city("indy") is city
    assert REGISTRY[city].job_suffix == "indianapolis"
    assert set(REGISTRY[city].datasets) == {FeedType.COMPLAINTS_311}


def test_indianapolis_311_spec_pins_the_live_schema():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.INDIANAPOLIS, FeedType.COMPLAINTS_311)
    assert spec.platform == "arcgis"
    assert spec.endpoint.endswith("/ODP_RIMACServiceRequests/FeatureServer/0")
    assert spec.watermark_col == "REQUESTEDDATETIME"
    assert spec.id_keys == ["SERVICEREQUESTID", "OBJECTID"]
    assert spec.expected_cadence_days == 7
    assert spec.oid_field == "OBJECTID"
    assert spec.max_record_count == 2000
    assert spec.field_map == COMPLAINTS_311_FIELD_MAP


def test_indianapolis_hard_excludes_unregistered_feeds():
    """311-only registration: permits (Accela ACA), licenses (INBiz SOS paid),
    and deeds (nightly parcel snapshot) have no open feed — get_dataset must
    raise a readable KeyError for them."""
    from src.spatial.city_registry import get_dataset

    for feed in (FeedType.PERMITS, FeedType.SLA, FeedType.DEEDS):
        with pytest.raises(KeyError) as excinfo:
            get_dataset(CityId.INDIANAPOLIS, feed)
        message = str(excinfo.value)
        assert CityId.INDIANAPOLIS.value in message and feed.value in message


def _flatten_feature(attributes: dict, geometry: dict) -> dict:
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry},
        date_fields={"REQUESTEDDATETIME", "UPDATEDDATETIME", "CLOSEDDATETIME"},
    )


COMPLAINTS_311_ROW = {
    # Live newest-by-REQUESTEDDATETIME row (OBJECTID 842538) via REST on
    # 2026-08-24; asserted fields verbatim. ArcGISClient converts
    # REQUESTEDDATETIME/UPDATEDDATETIME/CLOSEDDATETIME epoch-ms to ISO on flatten.
    "OBJECTID": 842538,
    "SERVICEREQUESTID": "26-00124733",
    "EXTERNALSERVICEREQUEST": None,
    "SERVICENAME": "Streets and Alley Repair",
    "ACTIVITY": "Depression",
    "SERVICEDEPARTMENT": "Department of Public Works - Operations",
    "ADDRESS": "1496 W EPLER AVE, INDIANAPOLIS, 46217",
    "TOWNSHIP": None,
    "ZIPCODE": 46217,
    "COUNCILDISTRICT": None,
    "REQUESTEDDATETIME": 1787543627000,
    "UPDATEDDATETIME": 1787543628000,
    "CLOSEDDATETIME": None,
    "STATUS": "open",
    "ORIGIN": "API",
    "LAT": 39.68581414,
    "LONG_": -86.18702727,
}
COMPLAINTS_311_GEOMETRY = {"x": -86.18702726999999, "y": 39.68581414000005}


class TestIndianapolis311Parsing:
    @pytest.fixture
    def complaints(self):
        from unittest.mock import patch

        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def _row(self):
        return _flatten_feature(COMPLAINTS_311_ROW, COMPLAINTS_311_GEOMETRY)

    def test_live_newest_row_parses(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="indianapolis")
        assert event is not None
        assert event.city_id == "indianapolis"
        assert event.incident_id == "26-00124733"

    def test_lat_lon_resolve_from_native_columns(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="indianapolis")
        assert event.latitude == pytest.approx(39.68581414)
        assert event.longitude == pytest.approx(-86.18702727)

    def test_watermark_date_maps_from_epoch_ms(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="indianapolis")
        assert event.created_date.date().isoformat() == "2026-08-24"
        assert event.closed_date is None

    def test_status_and_complaint_type_map_via_field_map(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="indianapolis")
        assert event.status == "open"
        assert event.complaint_type == "Depression"

    def test_address_zip_and_division_map(self, complaints):
        event = complaints.parse_socrata_row(self._row(), city_id="indianapolis")
        assert event.incident_address == "1496 W EPLER AVE, INDIANAPOLIS, 46217"
        assert event.zipcode == "46217"
        assert event.borough is not None

    def test_missing_service_request_id_drops_the_row(self, complaints):
        attrs = {k: v for k, v in COMPLAINTS_311_ROW.items() if k != "SERVICEREQUESTID"}
        row = _flatten_feature(attrs, COMPLAINTS_311_GEOMETRY)
        assert complaints.parse_socrata_row(row, city_id="indianapolis") is None
