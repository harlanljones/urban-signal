"""Contract tests for Pittsburgh, PA (CKAN WPRDC PLI Permits)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.pittsburgh import (
    PITTSBURGH_DIVISION_BBOXES,
    PITTSBURGH_DIVISIONS,
    PITTSBURGH_METRO_BBOX,
    PITTSBURGH_SUBMARKETS,
    is_in_pittsburgh_metro,
)
from src.spatial.city_registry import CityId, FeedType

# Recommended DatasetSpec.extra["field_map"] for US-89. Every entry spells a
# WPRDC column the shared producer fallback chains cannot reach (the chains
# say `permit_number`/`issued_date`/`revised_cost`); latitude/longitude ride
# native lowercase keys the chains already read.
PITTSBURGH_FIELD_MAP = {
    "job_id": ["permit_id"],
    "issuance_date": ["issue_date"],
    "cost": ["total_project_value"],
    "address_street": ["address"],
    "status": ["status"],
    "job_type": ["permit_type", "work_type"],
    "zipcode": ["zip_code"],
}


def test_pittsburgh_geometry_is_self_consistent():
    assert is_in_pittsburgh_metro(40.4417, -80.0000)  # Downtown center
    assert is_in_pittsburgh_metro(40.4486022823, -79.9903585214)  # observed live-row
    assert is_in_pittsburgh_metro(40.466871193, -79.9806746886)  # observed live-row
    assert not is_in_pittsburgh_metro(40.5697, -79.7549)  # New Kensington, NE of the city
    assert not is_in_pittsburgh_metro(None, None)
    for name, bbox in PITTSBURGH_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= PITTSBURGH_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= PITTSBURGH_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= PITTSBURGH_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= PITTSBURGH_METRO_BBOX["max_lng"], name
    claimed = [name for division in PITTSBURGH_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(PITTSBURGH_SUBMARKETS)
    assert {meta.city_id for meta in PITTSBURGH_SUBMARKETS.values()} == {"pittsburgh"}


def test_pittsburgh_registers_ckan_permits_only():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.PITTSBURGH
    assert normalize_city("pittsburgh") is city
    assert normalize_city("pgh") is city
    assert REGISTRY[city].job_suffix == "pgh"
    assert set(REGISTRY[city].datasets) == {FeedType.PERMITS}

    permits = REGISTRY[city].datasets[FeedType.PERMITS]
    assert permits.platform == "ckan"
    assert permits.watermark_col == "issue_date"
    assert permits.interval_seconds == 300.0
    assert permits.producer_key == "permits"
    assert permits.extra["expected_cadence_days"] == 7
    assert permits.extra["field_map"] == PITTSBURGH_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.COMPLAINTS_311)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.SLA)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.DEEDS)


PGH_PERMIT_ROW = {
    # Live newest-rows sample via the WPRDC datastore on 2026-08-24, exactly
    # as CkanClient delivers it (flat JSON record; native lat/lng keys).
    "permit_id": "EP-2026-04291",
    "permit_type": "ELECTRICAL",
    "owner_name": None,
    "work_description": "MAIN SERVICE REPLACEMENT",
    "work_type": "Existing (alteration/addition)",
    "commercial_or_residential": "Residential",
    "total_project_value": 148968,
    "issue_date": "2026-08-21",
    "parcel_num": "0028N00146000000",
    "address": "1447 SMALLMAN ST, Pittsburgh, PA 15222-",
    "latitude": 40.4486022823,
    "longitude": -79.9903585214,
    "council_district": "6",
    "neighborhood": "Bluff",
    "ward": "19",
    "zip_code": "15222",
    "status": "Issued",
}


class TestPittsburghPermitParsing:
    """Parse pins against the shared DOBPermitsProducer (US-89)."""

    @pytest.fixture
    def producer(self):
        with (
            patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
            patch(
                "src.producers.field_maps.resolve_field_map",
                return_value=PITTSBURGH_FIELD_MAP,
            ),
        ):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            yield DOBPermitsProducer()

    def test_live_row_parses_wprdc_schema(self, producer):
        event = producer.parse_socrata_row(dict(PGH_PERMIT_ROW), city_id="pittsburgh")
        assert event is not None
        assert event.city_id == "pittsburgh"
        assert event.job_id == "EP-2026-04291"
        assert event.status == "Issued"
        assert event.estimated_cost == pytest.approx(148968)
        assert event.zipcode == "15222"
        assert event.issuance_date is not None
        assert (event.issuance_date.year, event.issuance_date.month, event.issuance_date.day) == (
            2026,
            8,
            21,
        )
        assert event.latitude == pytest.approx(40.4486022823)
        assert event.longitude == pytest.approx(-79.9903585214)

    def test_missing_permit_id_returns_none(self, producer):
        row = dict(PGH_PERMIT_ROW)
        row.pop("permit_id")
        assert producer.parse_socrata_row(row, city_id="pittsburgh") is None