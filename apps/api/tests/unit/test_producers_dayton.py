"""Contract tests for Dayton's rolling-window 311 ArcGIS feed."""

from unittest.mock import patch

import pytest

from src.spatial.cities.dayton import (
    DAYTON_DIVISION_BBOXES,
    DAYTON_DIVISIONS,
    DAYTON_METRO_BBOX,
    DAYTON_SUBMARKETS,
    is_in_dayton_metro,
)
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    normalize_city,
)

DAYTON_FIELD_MAP = {
    "incident_id": ["SERVNO", "RowNumber", "REFNO"],
    "created_date": ["ADDDTTM"],
    "closed_date": ["RESDTTM", "ModDTTM"],
    "status": ["RESFLAG", "RESCODE"],
    "complaint_type": ["PROBDESC", "CatName", "ProbDesc2"],
    "incident_address": ["ADDRESS", "LOC"],
    "borough": ["NEIGH_COM", "DISTRICT"],
}


def test_dayton_geometry_is_self_consistent():
    assert is_in_dayton_metro(39.7589, -84.1916)
    assert is_in_dayton_metro(39.7623, -84.1830)
    assert not is_in_dayton_metro(40.7128, -74.0060)
    assert not is_in_dayton_metro(None, None)
    for name, bbox in DAYTON_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= DAYTON_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= DAYTON_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= DAYTON_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= DAYTON_METRO_BBOX["max_lng"], name
    claimed = [name for division in DAYTON_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(DAYTON_SUBMARKETS)
    assert {meta.city_id for meta in DAYTON_SUBMARKETS.values()} == {"dayton"}


def test_dayton_registers_rolling_311_and_snap_sla():
    city = CityId.DAYTON
    assert normalize_city("dayton oh") is city
    assert normalize_city("montgomery county oh") is city
    assert set(REGISTRY[city].datasets) == {FeedType.COMPLAINTS_311, FeedType.SLA}
    complaints = get_dataset(city, FeedType.COMPLAINTS_311)
    assert complaints.platform == "arcgis"
    assert complaints.watermark_col == "ADDDTTM"
    # RowNumber renumbers the rolling 90-day window (1..N), so the stable
    # service-request number leads; the layer has no objectIdField, so the
    # client's default OBJECTID sort 400s and the spec sorts on SERVNO.
    assert complaints.id_keys == ["SERVNO", "RowNumber", "REFNO"]
    assert complaints.order_by == "SERVNO ASC"
    assert complaints.rolling_window_days == 90
    assert complaints.retention_days == 90
    assert complaints.field_map == DAYTON_FIELD_MAP
    for feed in (FeedType.PERMITS, FeedType.DEEDS):
        with pytest.raises(KeyError, match="no.*feed"):
            get_dataset(city, feed)


@pytest.fixture
def producer():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        yield Complaints311Producer()


def test_dayton_live_shaped_row_parses(producer):
    row = {
        "RowNumber": 19965,
        "ADDDTTM": "2026-08-25T17:48:01.603+00:00",
        "ADDRESS": "2235 W SECOND ST",
        "PROBDESC": "GRASS COMPLAINTS",
        "RESCODE": "COMPLETED",
        "RESFLAG": "Closed",
        "CatName": "Housing Inspection",
        "STSUB": " ",
        "latitude": 39.762331682620243,
        "longitude": -84.183016648036542,
    }
    event = producer.parse_socrata_row(row, city_id="dayton")
    assert event is not None
    assert event.city_id == "dayton"
    assert event.incident_id == "19965"
    assert event.complaint_type == "GRASS COMPLAINTS"
    assert event.incident_address == "2235 W SECOND ST"
    assert event.status == "Closed"
    assert event.latitude == pytest.approx(39.762331682620243)
    assert event.longitude == pytest.approx(-84.183016648036542)


def test_dayton_incident_id_is_the_service_request_number(producer):
    """RowNumber 19965 on 2026-08-25 was about RowNumber 11721 by 2026-09-30
    as older requests left the window; SERVNO does not move."""
    row = {
        "RowNumber": 11721,
        "SERVNO": 2107815,
        "ADDDTTM": "2026-08-25T17:45:55+00:00",
        "PROBDESC": "GRASS COMPLAINTS",
        "latitude": 39.7623,
        "longitude": -84.1830,
    }
    event = producer.parse_socrata_row(row, city_id="dayton")
    assert event is not None
    assert event.incident_id == "2107815"


def test_dayton_augusta_and_peoria_hosts_take_date_literals():
    """ArcGIS Server 10.91 and 11.4 on these hosts answer an ISO string
    comparison with 400 "Unable to complete operation" (verified 2026-09-30)."""
    from src.producers.watermarks import watermark_comparison

    for endpoint in (
        "https://maps.daytonohio.gov/gisservices/rest/services/PublicWorks/COD_ServiceRequests_Last90/MapServer/0",
        "https://gismap.augustaga.gov/arcgis/rest/services/EnterpriseApps/iasWorld_Permit/MapServer/1",
        "https://gis.peoriacounty.gov/arcgis/rest/services/DP/ResidentialSales/MapServer/5",
    ):
        clause = watermark_comparison("ADDDTTM", ">", "2026-09-22T05:31:07", endpoint=endpoint)
        assert clause == "ADDDTTM > date '2026-09-22'", endpoint
