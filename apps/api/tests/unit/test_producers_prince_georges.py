"""Contract tests for Prince George's County, MD (311 + parcel snapshot)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.prince_georges import (
    PRINCE_GEORGES_DIVISION_BBOXES,
    PRINCE_GEORGES_DIVISIONS,
    PRINCE_GEORGES_METRO_BBOX,
    PRINCE_GEORGES_SUBMARKETS,
    is_in_prince_georges_metro,
)
from src.spatial.city_registry import CityId, FeedType


def test_prince_georges_geometry_is_self_consistent():
    assert is_in_prince_georges_metro(38.72, -76.75)
    assert is_in_prince_georges_metro(38.9072, -77.0369)  # DC line neighbor
    assert not is_in_prince_georges_metro(39.2904, -76.6122)  # Baltimore
    assert not is_in_prince_georges_metro(None, None)
    for name, bbox in PRINCE_GEORGES_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= PRINCE_GEORGES_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= PRINCE_GEORGES_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= PRINCE_GEORGES_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= PRINCE_GEORGES_METRO_BBOX["max_lng"], name
    claimed = [name for division in PRINCE_GEORGES_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(PRINCE_GEORGES_SUBMARKETS)
    assert {meta.city_id for meta in PRINCE_GEORGES_SUBMARKETS.values()} == {"prince_georges"}


def test_prince_georges_registers_311_and_defers_parcel_snapshot():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.PRINCE_GEORGES
    assert normalize_city("pgco") is city
    assert normalize_city("prince george's county") is city
    assert REGISTRY[city].job_suffix == "pgmd"
    assert set(REGISTRY[city].datasets) == {FeedType.COMPLAINTS_311}

    c311 = REGISTRY[city].datasets[FeedType.COMPLAINTS_311]
    assert c311.watermark_col == "date_request_opened"
    # G11 exception: monthly batch publishing, alarms at 60d not 14d
    assert c311.extra["expected_cadence_days"] == 30
    assert c311.extra["field_map"]["incident_id"] == ["service_request"]
    assert c311.extra["field_map"]["created_date"] == ["date_request_opened"]

    # HJ-125 finding: qzrv-2tnv stays unregistered until deed geometry
    # extraction handles MultiPolygon parcel shapes (see parse test below).
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.DEEDS)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.PERMITS)


PG_311_ROW = {
    # Live newest row via REST on 2026-08-24 ($order=date_request_opened DESC).
    "service_request": "26-00075635",
    "date_request_opened": "2026-07-17T00:00:00.000",
    "request_name": "Bulk Trash Pickup",
    "request_status": "open",
    "agency_responsible": "DPW&T",
    "street_address": "123 TEST ST",
    "city": "CAPITOL HEIGHTS",
    "zipcode": "20743",
    "latitude": 38.904183000003000,
    "longitude": -76.899730500001000,
}


class TestPrinceGeorges311Parsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_live_row_parses_through_field_map(self, complaints):
        event = complaints.parse_socrata_row(dict(PG_311_ROW), city_id="prince_georges")
        assert event is not None
        assert event.city_id == "prince_georges"
        assert event.incident_id == "26-00075635"
        assert event.complaint_type == "Bulk Trash Pickup"
        assert event.status == "open"
        assert event.incident_address == "123 TEST ST"
        assert event.zipcode == "20743"
        assert event.latitude == PG_311_ROW["latitude"]
        assert event.created_date is not None and event.created_date.year == 2026

    def test_missing_id_returns_none(self, complaints):
        row = dict(PG_311_ROW)
        row.pop("service_request")
        assert complaints.parse_socrata_row(row, city_id="prince_georges") is None


PG_PARCEL_ROW = {
    # Live first row via REST on 2026-08-24 ($limit=1).
    "account": "0339093",
    "objectid": 1,
    "transfer_date": "20210505",
    "sales_price": "405000",
    "owner_name": "SOME OWNER",
}


class TestPrinceGeorgesParcelSnapshotFinding:
    """HJ-125 evidence for deferring the qzrv-2tnv registration.

    Two independent blockers, both verified live 2026-08-24:

    1. Every parcel carries a MultiPolygon ``the_geom``;
       ``DeedsACRISProducer.parse_socrata_row`` extracts coordinates only
       from POINT shapes, so real rows crash the extraction ("list index
       out of range") and parse to None.
    2. The id chain has no ``account`` fallback (only generic ``id``), so
       without the registration-time field_map even geomless rows cannot
       form a document id. The deferred registration supplies
       ``field_map={"doc_id": ["account"], ...}``.

    These tests pin both so the future hardening delta flips them green.
    """

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_multipolygon_parcel_rows_currently_parse_to_none(self, deeds):
        row = dict(
            PG_PARCEL_ROW,
            the_geom={"type": "MultiPolygon", "coordinates": [[[-76.8, 38.7], [-76.7, 38.7]]]},
        )
        assert deeds.parse_socrata_row(row, city_id="prince_georges") is None

    def test_unmapped_account_ids_currently_parse_to_none(self, deeds):
        assert deeds.parse_socrata_row(dict(PG_PARCEL_ROW), city_id="prince_georges") is None

    def test_yyyymmdd_text_dates_parse_as_real_transfer_dates(self):
        from src.producers.deeds_acris_producer import _parse_datetime

        parsed = _parse_datetime("20210505")
        assert parsed is not None
        assert (parsed.year, parsed.month, parsed.day) == (2021, 5, 5)
        # Sentinel spellings stay unparseable rather than becoming dates.
        assert _parse_datetime("ZZZZZZZZ") is None
        assert _parse_datetime("XXXXXXXX") is None
