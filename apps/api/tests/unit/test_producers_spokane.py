"""Contract tests for Spokane County DEEDS, permits, and WA LCB SLA feeds."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.producers.excel_client import ExcelClient, _normalize_where
from src.spatial.cities.spokane import (
    SPOKANE_DIVISION_BBOXES,
    SPOKANE_DIVISIONS,
    SPOKANE_METRO_BBOX,
    SPOKANE_SUBMARKETS,
    is_in_spokane_metro,
)
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    normalize_city,
)

SPOKANE_PERMITS_FIELD_MAP = {
    "job_id": ["permit_number"],
    "issuance_date": ["issued_date"],
    "filing_date": ["issued_date"],
    "job_type": ["permit_type", "project_description"],
    "status": ["status", "status_description"],
    "address_street": ["site_address"],
    "zipcode": ["site_zip"],
    "bbl": ["parcel_number"],
}


def test_spokane_geometry_is_self_consistent():
    assert is_in_spokane_metro(47.6588, -117.4260)
    assert is_in_spokane_metro(47.67117, -117.34622)
    assert not is_in_spokane_metro(47.6062, -122.3321)
    assert not is_in_spokane_metro(None, None)
    for name, bbox in SPOKANE_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= SPOKANE_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= SPOKANE_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= SPOKANE_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= SPOKANE_METRO_BBOX["max_lng"], name
    claimed = [name for division in SPOKANE_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(SPOKANE_SUBMARKETS)
    assert {meta.city_id for meta in SPOKANE_SUBMARKETS.values()} == {"spokane"}


def test_spokane_registers_deeds_permits_and_sla():
    city = CityId.SPOKANE
    assert normalize_city("spokane wa") is city
    assert normalize_city("spokane county") is city
    assert set(REGISTRY[city].datasets) == {FeedType.DEEDS, FeedType.PERMITS, FeedType.SLA}

    deeds = get_dataset(city, FeedType.DEEDS)
    assert deeds.platform == "arcgis"
    assert deeds.watermark_col == "document_date"
    assert deeds.id_keys == ["Parcel", "OBJECTID"]
    assert deeds.endpoint_by_year["2015"].endswith("/MapServer/7")
    assert deeds.endpoint_by_year["2026"].endswith("/MapServer/20")

    permits = get_dataset(city, FeedType.PERMITS)
    assert permits.platform == "excel"
    assert permits.watermark_col == "issued_date"
    assert permits.needs_geocode is True
    assert permits.field_map == SPOKANE_PERMITS_FIELD_MAP

    sla = get_dataset(city, FeedType.SLA)
    assert sla.platform == "socrata"
    assert sla.watermark_col == "renewaldate"
    assert sla.where == "city = 'SPOKANE'"


def test_excel_client_normalizes_headers_filters_and_batches():
    response = MagicMock(content=b"xls-bytes")
    response.raise_for_status.return_value = None
    http = MagicMock()
    http.get.return_value = response
    frame = pd.DataFrame(
        [
            {"Permit Number": "A-1", "Issued Date": "2026-08-24", "Site Zip": "99201"},
            {"Permit Number": "A-2", "Issued Date": "2026-08-01", "Site Zip": "99202"},
        ]
    )
    with patch("src.producers.excel_client.pd.read_excel", return_value=frame) as read_excel:
        batches = list(
            ExcelClient(http).paginate(
                "https://example.test/permits.xls",
                where_clause="Issued Date > '2026-08-20'",
                batch_size=1,
            )
        )
    read_excel.assert_called_once()
    assert batches == [[{"permit_number": "A-1", "issued_date": "2026-08-24", "site_zip": "99201"}]]
    assert _normalize_where("Issued Date > '2026-08-20'") == "issued_date > '2026-08-20'"


def _flatten_feature(attributes: dict, geometry: dict) -> dict:
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry}, date_fields={"document_date"}
    )


@pytest.fixture
def producers():
    with (
        patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
        patch("src.producers.deeds_acris_producer.BaseKafkaProducer"),
        patch("src.producers.sla_licenses_producer.BaseKafkaProducer"),
    ):
        from src.producers.deeds_acris_producer import DeedsACRISProducer
        from src.producers.dob_permits_producer import DOBPermitsProducer
        from src.producers.sla_licenses_producer import SLALicensesProducer

        yield DOBPermitsProducer(), DeedsACRISProducer(), SLALicensesProducer()


def test_spokane_polygon_sale_parses_with_centroid(producers):
    _, deeds, _ = producers
    row = _flatten_feature(
        {
            "OBJECTID": 256405,
            "Parcel": "04364.0609",
            "gross_sale_price": 225000.0,
            "document_date": 1787558400000,
            "prop_use_code": "14",
        },
        {"rings": [[[-117.7010, 47.5269], [-117.7008, 47.5268], [-117.7010, 47.5269]]]},
    )
    event = deeds.parse_socrata_row(row, city_id="spokane")
    assert event is not None
    assert event.city_id == "spokane"
    assert event.doc_id == "04364.0609"
    assert event.document_amount == pytest.approx(225000.0)
    assert event.recorded_date is not None
    assert event.latitude == pytest.approx(47.5268, abs=0.001)
    assert event.longitude == pytest.approx(-117.7009, abs=0.001)


def test_spokane_xls_permit_row_uses_declared_geocoder(producers):
    permits, _, _ = producers
    row = {
        "permit_number": "B2601234",
        "issued_date": "2026-08-24",
        "permit_type": "Residential Minor Alteration",
        "status": "ISSUED",
        "site_address": "421 W MAIN AVE",
        "site_zip": "99201",
        "parcel_number": 1234.5678,
    }
    with patch(
        "src.spatial.geocoder.geocode_row_if_declared", return_value=(47.65905, -117.419)
    ):
        event = permits.parse_socrata_row(row, city_id="spokane")
    assert event is not None
    assert event.job_id == "B2601234"
    assert event.address_street == "421 W MAIN AVE"
    assert event.bbl == "1234.5678"
    assert event.latitude == pytest.approx(47.65905)
    assert event.longitude == pytest.approx(-117.419)


def test_spokane_lcb_row_parses_native_point(producers):
    _, _, sla = producers
    event = sla.parse_socrata_row(
        {
            "license": "426885",
            "l_a_type": "Liquor Renewal",
            "tradename": "LOCUST CIDER",
            "designatedsignee": "CITY OF SPOKANE",
            "streetaddress": "421 W MAIN AVE",
            "cityname": "SPOKANE",
            "renewaldate": "20260630",
            "location": {"latitude": "47.65905", "longitude": "-117.419"},
        },
        city_id="spokane",
    )
    assert event is not None
    assert event.license_id == "426885"
    assert event.dba == "LOCUST CIDER"
    assert event.license_type == "Liquor Renewal"
    assert event.address == "421 W MAIN AVE"
    assert event.expiration_date is not None
    assert event.expiration_date.year == 2026
    assert event.latitude == pytest.approx(47.65905)
    assert event.longitude == pytest.approx(-117.419)
