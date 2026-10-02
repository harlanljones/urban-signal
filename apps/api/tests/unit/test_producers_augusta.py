"""Contract tests for Augusta, GA registration (US-287)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.augusta import (
    AUGUSTA_DIVISION_BBOXES,
    AUGUSTA_DIVISIONS,
    AUGUSTA_METRO_BBOX,
    AUGUSTA_SUBMARKETS,
    is_in_augusta_metro,
)
from src.spatial.city_registry import CityId, FeedType


def test_augusta_geometry_is_self_consistent():
    assert is_in_augusta_metro(33.476, -82.010)
    assert not is_in_augusta_metro(34.0522, -118.2437)  # Los Angeles, outside GA bbox
    assert not is_in_augusta_metro(None, None)
    for name, bbox in AUGUSTA_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= AUGUSTA_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= AUGUSTA_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= AUGUSTA_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= AUGUSTA_METRO_BBOX["max_lng"], name
    claimed = [name for division in AUGUSTA_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(AUGUSTA_SUBMARKETS)
    assert {meta.city_id for meta in AUGUSTA_SUBMARKETS.values()} == {"augusta"}


def test_augusta_registry_carries_permits_311_and_sla_specs():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.AUGUSTA
    assert normalize_city("augusta") is city
    assert normalize_city("augusta_ga") is city
    assert set(REGISTRY[city].datasets) == {FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.SLA}

    permits = REGISTRY[city].datasets[FeedType.PERMITS]
    assert permits.platform == "arcgis"
    assert permits.producer_key == "permits"
    assert permits.needs_geocode is True
    # The iasWorld permits table has no object id; the permit number keys its rows.
    assert permits.oid_field == "PERMITNUMBER"
    assert "PERMITNUMBER" in permits.id_keys

    # Unregistered feeds raise readable errors
    for feed in (FeedType.DEEDS,):
        try:
            get_dataset(city, feed)
            assert False, "get_dataset should raise for unregistered feeds"
        except KeyError as e:
            msg = str(e)
            assert "augusta" in msg and feed.value in msg




@pytest.mark.parametrize(
    ("code", "kind", "job_type", "normalized"),
    [
        # PERMCODE names the trade the type leaves out (2026-10-02, newest 1,000).
        ("PRMH", "Change Out", "OT", "MECHANICAL_ELECTRICAL_PLUMBING"),
        ("PREL", "Service Change", "A2", "MECHANICAL_ELECTRICAL_PLUMBING"),
        ("PRPL", "Repair", "A2", "MECHANICAL_ELECTRICAL_PLUMBING"),
        ("PRBD", "Repair", "A2", "MINOR_ALTERATION"),
        ("PRBD", "New - Single Family Detached Residential", "NB", "NEW_CONSTRUCTION"),
        ("PRBD", "New - 2 Family Residential", "NB", "NEW_CONSTRUCTION"),
    ],
)
def test_augusta_permit_type_names_its_trade(code, kind, job_type, normalized):
    from src.spatial.cities.augusta import compose_permit_type
    from src.spatial.city_registry import get_dataset

    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        producer = DOBPermitsProducer()
    row = {
        "PERMITNUMBER": "2026-00001",
        "PERMCODE": code,
        "PERM_TYPE": kind,
        "PERMIT_STATUS": "Permits Issued",
        "DATE_ISSUE": "2026-09-30T00:00:00",
        "JOBADDRESS": "535 TELFAIR ST",
    }
    permits_map = get_dataset(CityId.AUGUSTA, FeedType.PERMITS).field_map
    with (
        patch("src.producers.field_maps.resolve_field_map", return_value=permits_map),
        patch("src.spatial.geocoder.geocode_row_if_declared", return_value=(33.474, -81.968)),
    ):
        event = producer.parse_socrata_row(row, city_id="augusta")
    assert event is not None
    assert (event.job_type.value, event.normalized_permit_type) == (job_type, normalized)
    assert (compose_permit_type(row) is None) == (code == "PRBD")
