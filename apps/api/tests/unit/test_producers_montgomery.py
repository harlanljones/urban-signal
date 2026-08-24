"""Contract tests for Montgomery County's Socrata permit and ABS feeds."""

from unittest.mock import patch

import pytest

from src.spatial.cities.montgomery import (
    MONTGOMERY_DIVISION_BBOXES,
    MONTGOMERY_DIVISIONS,
    MONTGOMERY_METRO_BBOX,
    MONTGOMERY_SUBMARKETS,
    is_in_montgomery_metro,
)
from src.spatial.city_registry import ALIASES, REGISTRY, CityId, FeedType


def test_montgomery_geometry_and_aliases_are_registered():
    assert is_in_montgomery_metro(39.140, -77.190)
    assert not is_in_montgomery_metro(42.355, -71.065)
    assert not is_in_montgomery_metro(None, None)
    for name, bbox in MONTGOMERY_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= MONTGOMERY_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= MONTGOMERY_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= MONTGOMERY_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= MONTGOMERY_METRO_BBOX["max_lng"], name
    assert sorted(MONTGOMERY_DIVISIONS["MONTGOMERY_CORE"].submarkets) == sorted(MONTGOMERY_SUBMARKETS)
    assert {ALIASES[name] for name in ("montgomery", "montgomery_county", "moco")} == {CityId.MONTGOMERY}


def test_montgomery_registers_only_geocoded_permits_and_liquor():
    reg = REGISTRY[CityId.MONTGOMERY]
    assert set(reg.datasets) == {FeedType.PERMITS, FeedType.SLA}
    assert all(spec.platform == "socrata" for spec in reg.datasets.values())
    assert FeedType.COMPLAINTS_311 not in reg.datasets  # MC311 xtyh-brr2 fails G5: no coordinates.
    assert FeedType.DEEDS not in reg.datasets
    permits = reg.datasets[FeedType.PERMITS]
    assert permits.endpoint.endswith("/resource/m88u-pqki.json")
    assert permits.extra["companion_endpoints"] == {
        "commercial": "https://data.montgomerycountymd.gov/resource/i26v-w6bd.json",
        "demolition": "https://data.montgomerycountymd.gov/resource/b6ht-fw3x.json",
        "electrical": "https://data.montgomerycountymd.gov/resource/qxie-8qnp.json",
    }
    assert permits.extra["field_map"]["latitude"] == ["location.latitude"]
    licenses = reg.datasets[FeedType.SLA]
    assert licenses.endpoint.endswith("/resource/c6rw-fazn.json")
    assert licenses.extra["ingestion_mode"] == "snapshot"
    assert licenses.extra["field_map"]["license_id"] == ["licensee_number"]


def test_montgomery_permit_row_parses_nested_location():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer
        producer = DOBPermitsProducer()
    event = producer.parse_socrata_row(
        {"permitno": "RES-26-000001", "issueddate": "2026-08-20T00:00:00.000", "stno": "100", "stname": "MONTGOMERY", "suffix": "AVE", "location": {"latitude": 39.140, "longitude": -77.190}},
        city_id="montgomery",
    )
    assert event is not None
    assert event.job_id == "RES-26-000001"
    assert event.latitude == pytest.approx(39.140)
    assert event.longitude == pytest.approx(-77.190)


def test_montgomery_license_row_parses_nested_location():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer
        producer = SLALicensesProducer()
    event = producer.parse_socrata_row(
        {"licensee_number": "ABS-0001", "licensee_name": "Example Market", "channel_type": "Beer/Wine", "street": "100 MONTGOMERY AVE", "location": {"latitude": 39.140, "longitude": -77.190}},
        city_id="montgomery",
    )
    assert event is not None
    assert event.license_id == "ABS-0001"
    assert event.latitude == pytest.approx(39.140)
