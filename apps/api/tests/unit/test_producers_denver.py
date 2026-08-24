"""Contract tests for Denver's ArcGIS permit and 311 registrations."""

from unittest.mock import patch

import pytest

from src.spatial.cities.denver import (
    DENVER_DIVISION_BBOXES,
    DENVER_DIVISIONS,
    DENVER_METRO_BBOX,
    DENVER_SUBMARKETS,
    is_in_denver_metro,
)
from src.spatial.city_registry import CityId, FeedType


def test_denver_geometry_is_self_consistent():
    assert is_in_denver_metro(39.7527, -104.9992)
    assert not is_in_denver_metro(39.1031, -84.5120)
    assert not is_in_denver_metro(None, None)
    for name, bbox in DENVER_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= DENVER_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= DENVER_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= DENVER_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= DENVER_METRO_BBOX["max_lng"], name
    claimed = [name for division in DENVER_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(DENVER_SUBMARKETS)
    assert {meta.city_id for meta in DENVER_SUBMARKETS.values()} == {"denver"}


def test_denver_registers_arcgis_permits_and_311_only():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.DENVER
    assert normalize_city("denver") is city
    assert REGISTRY[city].job_suffix == "denver"
    assert set(REGISTRY[city].datasets) == {FeedType.PERMITS, FeedType.COMPLAINTS_311}
    assert REGISTRY[city].datasets[FeedType.PERMITS].platform == "arcgis"
    assert REGISTRY[city].datasets[FeedType.COMPLAINTS_311].platform == "arcgis"
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.SLA)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.DEEDS)


def test_denver_arcgis_specs_pin_date_and_coordinate_quirks():
    from src.spatial.city_registry import REGISTRY

    reg = REGISTRY[CityId.DENVER]
    permits = reg.datasets[FeedType.PERMITS]
    complaints = reg.datasets[FeedType.COMPLAINTS_311]
    assert permits.extra["field_map"]["issuance_date"] == ["DATE_ISSUED"]
    assert complaints.watermark_col == "Case_Created_Date"
    assert complaints.extra["field_map"]["latitude"] == ["Latitude"]
    assert complaints.extra["field_map"]["longitude"] == ["Longitude"]
    assert permits.extra["companion_endpoints"]["commercial"].endswith("/FeatureServer/317")


def test_denver_live_shaped_permit_row_parses():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        producer = DOBPermitsProducer()
    row = {
        "OBJECTID": 289755,
        "DATE_ISSUED": "2012-11-15T00:00:00+00:00",
        "DATE_RECEIVED": "2012-11-14T00:00:00+00:00",
        "PERMIT_NUM": "2012-RESCON-0000004625",
        "ADDRESS": "3729 N LIPAN ST",
        "CLASS": "NEW BUILDING",
        "VALUATION": 14285,
        "UNITS": 1,
        "NEIGHBORHOOD": "Highland",
        "latitude": 39.7690,
        "longitude": -105.0100,
    }
    event = producer.parse_socrata_row(row, city_id="denver")
    assert event is not None
    assert event.job_id == "2012-RESCON-0000004625"
    assert event.address_street == "3729 N LIPAN ST"
    assert event.latitude == pytest.approx(39.7690)


def test_denver_live_shaped_311_row_parses_uppercase_coordinates():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        producer = Complaints311Producer()
    row = {
        "OBJECTID": 376730884,
        "Case_Summary": "Pothole",
        "Case_Status": "Closed - Answer Provided",
        "Case_Created_dttm": "12/31/2025 11:32:50 AM",
        "Incident_Address_1": "1700 LINCOLN ST",
        "Incident_Zip_Code": "80203",
        "Latitude": 39.7430,
        "Longitude": -104.9850,
        "Type": "Street Maintenance",
    }
    event = producer.parse_socrata_row(row, city_id="denver")
    assert event is not None
    assert event.incident_id == "376730884"
    assert event.latitude == pytest.approx(39.7430)
    assert event.incident_address == "1700 LINCOLN ST"
