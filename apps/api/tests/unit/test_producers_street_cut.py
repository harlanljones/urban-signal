"""Unit tests for the US-81 street-cut / street-closure feeds (CHI).

Fixtures mirror live rows probed 2026-08-24 from Chicago's CDOT street-closure
dataset (``jdis-5sry``). NYC's DOT street-construction permits stay deferred —
current rows are address-only.
"""

from unittest.mock import patch

import pytest

from src.producers.street_cut_permits_producer import StreetCutPermitsProducer
from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset, get_job_name

CHICAGO_ROW = {
    "applicationnumber": "320086",
    "uniquekey": "1031414668790",
    "applicationtype": "DOT_PWO",
    "applicationstatus": "Open",
    "currentmilestone": "Inspection",
    "applicationissueddate": "2026-08-23T12:54:52.000",
    "applicationstartdate": "2026-08-18T00:00:00.000",
    "applicationenddate": "2026-09-18T23:59:59.000",
    "worktype": "GenOpening",
    "worktypedescription": "Opening in the Public Way",
    "streetname": "LATROBE",
    "streetnumberfrom": "1736",
    "direction": "N",
    "suffix": "AVE",
    "streetclosure": "Curblane",
    "totalfees": "1557.08",
    "latitude": "41.9124265497",
    "longitude": "-87.7571380905",
    "location": {"type": "Point", "coordinates": [-87.75713809046576, 41.912426549693755]},
}


@pytest.fixture
def producer():
    with patch("src.producers.street_cut_permits_producer.BaseKafkaProducer"):
        return StreetCutPermitsProducer()


def _within(bbox, lat, lng):
    return (
        bbox["min_lat"] <= lat <= bbox["max_lat"]
        and bbox["min_lng"] <= lng <= bbox["max_lng"]
    )


def test_chicago_street_cut_row_parses(producer):
    event = producer.parse_socrata_row(CHICAGO_ROW)
    assert event is not None
    assert event.city_id == "chicago"
    assert event.permit_id == "320086"
    assert event.permit_type == "DOT_PWO"
    assert event.work_type == "Opening in the Public Way"
    assert event.status == "Open"
    assert event.issued_date is not None
    assert event.fees == pytest.approx(1557.08)
    assert event.h3_res9


def test_chicago_row_coordinates_from_latlon_attrs(producer):
    row = {k: v for k, v in CHICAGO_ROW.items() if k != "location"}
    event = producer.parse_socrata_row(row)
    assert event is not None
    assert event.latitude == pytest.approx(41.9124265497)
    assert event.longitude == pytest.approx(-87.7571380905)


def test_chicago_row_coordinates_from_geojson_point(producer):
    row = {k: v for k, v in CHICAGO_ROW.items() if k not in ("latitude", "longitude")}
    event = producer.parse_socrata_row(row)
    assert event is not None
    assert event.latitude == pytest.approx(41.912426549693755)
    assert event.longitude == pytest.approx(-87.75713809046576)


def test_chicago_fixture_lands_inside_metro_bbox(producer):
    event = producer.parse_socrata_row(CHICAGO_ROW)
    assert event is not None
    assert _within(REGISTRY[CityId.CHICAGO].metro_bbox, event.latitude, event.longitude)


def test_street_cut_row_without_coordinates_is_dropped(producer):
    row = {"applicationnumber": "1", "latitude": "0.0", "longitude": "0.0"}
    assert producer.parse_socrata_row(row) is None
    row2 = {"applicationnumber": "2"}
    assert producer.parse_socrata_row(row2) is None


def test_street_cut_row_without_id_is_dropped(producer):
    row = {k: v for k, v in CHICAGO_ROW.items() if k not in ("applicationnumber", "uniquekey", "id")}
    assert producer.parse_socrata_row(row) is None


def test_nyc_street_cut_row_without_coordinates_is_dropped(producer):
    """NYC current rows are address-only; without coordinates they drop."""
    row = {"permitnumber": "X123", "onstreetname": "CHESTER AVENUE"}
    assert producer.parse_socrata_row(row, city_id="nyc") is None


def test_street_cut_registration_scope_and_job_names():
    # Chicago registers the geocodable CDOT street-closure feed; NYC stays out
    # (current rows address-only, blocked on geocoding) and so do all other
    # metros for this signal.
    for city, reg in REGISTRY.items():
        registered = FeedType.STREET_CUT in reg.datasets
        assert registered == (city == CityId.CHICAGO), (city, registered)
    assert get_job_name(FeedType.STREET_CUT, CityId.CHICAGO) == "street_cut_chicago"
    # NYC carries no job suffix, so any feed on it gets the plain name.
    assert get_job_name(FeedType.STREET_CUT, CityId.NYC) == "street_cut"


def test_chicago_street_cut_declares_daily_cadence_and_topic():
    spec = get_dataset(CityId.CHICAGO, FeedType.STREET_CUT)
    assert spec.extra["expected_cadence_days"] == 7
    assert spec.endpoint.endswith("jdis-5sry.json")
    assert spec.topic == "raw.municipal.street_cut"
    assert spec.watermark_col == "applicationissueddate"