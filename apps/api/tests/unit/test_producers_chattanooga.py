"""Contract tests for Chattanooga's CSV permits and ArcGIS parcel feeds."""

from datetime import datetime
from unittest.mock import patch

import httpx
import pytest

from src.producers.csv_client import CSVClient
from src.spatial.cities.chattanooga import (
    CHATTANOOGA_DIVISION_BBOXES,
    CHATTANOOGA_DIVISIONS,
    CHATTANOOGA_METRO_BBOX,
    CHATTANOOGA_SUBMARKETS,
    is_in_chattanooga_metro,
)
from src.spatial.city_registry import CityId, FeedType

CHATTANOOGA_PERMITS_FIELD_MAP = {
    "job_id": ["permitnum"],
    "issuance_date": ["issueddate"],
    "filing_date": ["applieddate"],
    "job_type": ["permitclass"],
    "cost": ["estprojectcostdec"],
    "status": ["status"],
    "address_street": ["address"],
    "zipcode": ["zipcode", "zip"],
    "bbl": ["pin"],
}

CHATTANOOGA_DEEDS_FIELD_MAP = {
    "doc_id": ["PIN", "PARCELID", "OBJECTID"],
    "recorded_date": ["SALE1DATE"],
    "document_amount": ["SALE1CONSD"],
    "bbl": ["PIN", "PARCELID"],
    "party2_grantee": ["OWNERNAME1"],
    "doc_type": ["SALE1TYPE", "DEEDTYPE", "TYPE"],
    "borough": ["MUNICIPALITY", "CITY"],
}


def test_chattanooga_geometry_is_self_consistent():
    assert is_in_chattanooga_metro(35.0456, -85.3097)
    assert is_in_chattanooga_metro(35.1300, -85.2350)
    assert not is_in_chattanooga_metro(36.1627, -86.7816)  # Nashville
    assert not is_in_chattanooga_metro(None, None)
    for name, bbox in CHATTANOOGA_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= CHATTANOOGA_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= CHATTANOOGA_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= CHATTANOOGA_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= CHATTANOOGA_METRO_BBOX["max_lng"], name
    claimed = [name for division in CHATTANOOGA_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(CHATTANOOGA_SUBMARKETS)
    assert {meta.city_id for meta in CHATTANOOGA_SUBMARKETS.values()} == {"chattanooga"}


def test_chattanooga_registers_permits_deeds_and_snap_sla():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.CHATTANOOGA
    assert normalize_city("chattanooga") is city
    assert normalize_city("hamilton county tn") is city
    assert REGISTRY[city].job_suffix == "chattanooga"
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.DEEDS,
        FeedType.SLA,
    }

    permits = get_dataset(city, FeedType.PERMITS)
    assert permits.platform == "csv"
    assert permits.watermark_col == "issueddate"
    assert permits.id_keys == ["permitnum"]
    assert permits.fallback_endpoints
    assert permits.field_map == CHATTANOOGA_PERMITS_FIELD_MAP

    deeds = get_dataset(city, FeedType.DEEDS)
    assert deeds.platform == "arcgis"
    assert deeds.watermark_col == "SALE1DATE"
    assert deeds.id_keys == ["PIN", "OBJECTID"]
    assert deeds.ingestion_mode == "snapshot"
    assert deeds.field_map == CHATTANOOGA_DEEDS_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.COMPLAINTS_311)


PERMIT_ROW = {
    "permitnum": "2026-00123",
    "applieddate": "2026-08-23",
    "issueddate": "2026-08-24",
    "permitclass": "NEW CONSTRUCTION",
    "estprojectcostdec": "1250000",
    "status": "ISSUED",
    "latitude": "35.0456",
    "longitude": "-85.3097",
    "pin": "123456789",
}

DEED_ROW = {
    "OBJECTID": 42,
    "PIN": "123456789",
    "SALE1DATE": "2026-08-10T00:00:00+00:00",
    "SALE1CONSD": 475000,
    "SALE1TYPE": "WD",
    "OWNERNAME1": "CHATTANOOGA HOLDINGS LLC",
    "MUNICIPALITY": "CHATTANOOGA",
    "latitude": 35.0456,
    "longitude": -85.3097,
}


@pytest.fixture
def producers():
    with (
        patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
        patch("src.producers.deeds_acris_producer.BaseKafkaProducer"),
    ):
        from src.producers.deeds_acris_producer import DeedsACRISProducer
        from src.producers.dob_permits_producer import DOBPermitsProducer

        yield DOBPermitsProducer(), DeedsACRISProducer()


def test_chattanooga_permit_row_parses(producers):
    permits, _ = producers
    with patch(
        "src.producers.field_maps.resolve_field_map",
        return_value=CHATTANOOGA_PERMITS_FIELD_MAP,
    ):
        event = permits.parse_socrata_row(dict(PERMIT_ROW), city_id="chattanooga")
    assert event is not None
    assert event.city_id == "chattanooga"
    assert event.job_id == "2026-00123"
    assert event.estimated_cost == 1250000.0
    assert event.issuance_date == datetime.fromisoformat("2026-08-24")
    assert event.latitude == pytest.approx(35.0456)
    assert event.borough == "CHATTANOOGA_CORE"


def test_chattanooga_deed_polygon_row_parses(producers):
    _, deeds = producers
    with patch(
        "src.producers.field_maps.resolve_field_map",
        return_value=CHATTANOOGA_DEEDS_FIELD_MAP,
    ):
        event = deeds.parse_socrata_row(dict(DEED_ROW), city_id="chattanooga")
    assert event is not None
    assert event.city_id == "chattanooga"
    assert event.doc_id == "123456789"
    assert event.document_amount == 475000.0
    assert event.recorded_date == datetime.fromisoformat("2026-08-10T00:00:00+00:00")
    assert event.party2_grantee == "CHATTANOOGA HOLDINGS LLC"
    assert event.borough == "CHATTANOOGA_CORE"


class _Response:
    def __init__(self, text: str, status_code: int):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "download failed",
                request=httpx.Request("GET", "https://example.test"),
                response=httpx.Response(self.status_code),
            )


class _HTTP:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if len(self.urls) == 1:
            return _Response("unavailable", 500)
        return _Response("permitnum,issueddate\nP-1,2026-08-24\n", 200)


def test_csv_client_falls_back_when_hub_download_is_unavailable():
    http = _HTTP()
    batches = list(
        CSVClient(http_client=http).paginate(
            "https://data.chattanooga.gov/api/download/v1/items/item/csv?layers=0",
            fallback_endpoints=["https://www.arcgis.com/sharing/rest/content/items/item/data"],
        )
    )
    assert http.urls == [
        "https://data.chattanooga.gov/api/download/v1/items/item/csv?layers=0",
        "https://www.arcgis.com/sharing/rest/content/items/item/data",
    ]
    assert batches == [[{"permitnum": "P-1", "issueddate": "2026-08-24"}]]
