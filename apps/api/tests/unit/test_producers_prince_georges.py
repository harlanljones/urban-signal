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


def test_prince_georges_registers_311_and_sdat_deeds():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.PRINCE_GEORGES
    assert normalize_city("pgco") is city
    assert normalize_city("prince george's county") is city
    assert REGISTRY[city].job_suffix == "pgmd"
    assert set(REGISTRY[city].datasets) == {FeedType.COMPLAINTS_311, FeedType.DEEDS}

    c311 = REGISTRY[city].datasets[FeedType.COMPLAINTS_311]
    assert c311.watermark_col == "date_request_opened"
    # G11 exception: monthly batch publishing, alarms at 60d not 14d
    assert c311.expected_cadence_days == 30
    assert c311.field_map["incident_id"] == ["service_request"]
    assert c311.field_map["created_date"] == ["date_request_opened"]

    # US-128: the MD SDAT deeds feed (opendata.maryland.gov/w3eb-4mzd) is
    # registered Point-geocoded and sidesteps the held qzrv-2tnv parcel table.
    deeds = REGISTRY[city].datasets[FeedType.DEEDS]
    assert deeds.endpoint.endswith("/resource/w3eb-4mzd.json")
    assert deeds.platform == "socrata"
    assert deeds.watermark_col == (
        "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89"
    )
    assert deeds.ingestion_mode == "snapshot"
    assert deeds.field_map["doc_id"] == ["account_id_mdp_field_acctid"]

    # The held qzrv-2tnv parcel table stays unregistered (HJ-125: deed geometry
    # extraction missing MultiPolygon handling — see TestPrinceGeorgesParcelSnapshotFinding).
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


PG_SDAT_DEED = {
    # Live shaped row from opendata.maryland.gov/resource/w3eb-4mzd (2026-08-25).
    "account_id_mdp_field_acctid": "17125627082",
    "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89": "2026.07.13",
    "sales_segment_1_consideration_mdp_field_considr1_sdat_field_90": "10",
    "sales_segment_1_grantor_name_mdp_field_grntnam1_sdat_field_80": "NH HAVEN APARTMENTS LLC",
    "sales_segment_1_transfer_number_mdp_field_transno1_sdat_field_79": "000789",
    "mdp_latitude_mdp_field_digycord_converted_to_wgs84": 38.78358949000099,
    "mdp_longitude_mdp_field_digxcord_converted_to_wgs84": -77.01234729604383,
    "mappable_latitude_and_longitude": "POINT (-77.01234729604383 38.78358949000099)",
    "county_name_mdp_field_cntyname": "Prince George's County",
}


class TestPrinceGeorgesSdatDeeds:
    """US-128: MD SDAT real-property deeds for Prince George's County — the
    Point-geocoded SDAT feed that sidesteps the held qzrv-2tnv parcel table."""

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_live_shaped_row_parses_through_field_map(self, deeds):
        event = deeds.parse_socrata_row(dict(PG_SDAT_DEED), city_id="prince_georges")
        assert event is not None
        assert event.city_id == "prince_georges"
        assert event.doc_id == "17125627082"
        assert event.bbl == "17125627082"
        assert event.document_amount == pytest.approx(10.0)
        assert event.party1_grantor == "NH HAVEN APARTMENTS LLC"
        assert event.latitude == pytest.approx(38.78358949000099)
        assert event.longitude == pytest.approx(-77.01234729604383)

    def test_dotted_watermark_parses_to_real_recorded_date(self, deeds):
        event = deeds.parse_socrata_row(dict(PG_SDAT_DEED), city_id="prince_georges")
        assert event is not None
        assert (event.recorded_date.year, event.recorded_date.month, event.recorded_date.day) == (
            2026,
            7,
            13,
        )

    def test_wkt_point_string_geocodes_when_native_columns_absent(self, deeds):
        row = dict(PG_SDAT_DEED)
        row.pop("mdp_latitude_mdp_field_digycord_converted_to_wgs84")
        row.pop("mdp_longitude_mdp_field_digxcord_converted_to_wgs84")
        event = deeds.parse_socrata_row(row, city_id="prince_georges")
        assert event is not None
        assert event.latitude == pytest.approx(38.78358949000099)
        assert event.longitude == pytest.approx(-77.01234729604383)

    def test_row_autodetects_prince_georges_by_county_name(self, deeds):
        event = deeds.parse_socrata_row(dict(PG_SDAT_DEED))
        assert event is not None
        assert event.city_id == "prince_georges"
