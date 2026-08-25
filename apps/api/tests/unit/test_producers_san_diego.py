"""Unit tests for the US-91 San Diego registration (permits-only, flat-CSV).

Fixtures mirror live rows read 2026-08-24 from
``approvals_issued_2026_datasd.csv``. The approvals table is broader than
permits; non-permit approval classes drop at parse time.
"""

from datetime import date
from unittest.mock import patch

import pytest

from src.producers.csv_client import CSVClient, _row_matches
from src.producers.dob_permits_producer import DOBPermitsProducer, _is_permit_like_approval
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    get_job_name,
    resolve_endpoint,
)

PERMIT_ROW = {
    "development_id": "",
    "project_id": "PRJ-1127510",
    "project_type": "Building Construction",
    "project_status": "Issued",
    "project_title": "General-Standard-Building Construction:2676/Broadway",
    "job_id": "JOB-082970",
    "gis_address": "2680 Broadway, San Diego, CA",
    "gis_apn": "5343022000",
    "gis_latitude": "32.71615107",
    "gis_longitude": "-117.13655017",
    "approval_id": "PMT-3327015",
    "approval_type": "Combination Building Permit",
    "approval_status": "Issued",
    "approval_scope": "GREATER GOLDEN HILL; Combination Building Permit",
    "approval_create_date": "2024-12-09",
    "approval_issue_date": "2026-03-10",
    "approval_valuation": "162522.27",
}

NON_PERMIT_ROW = {
    "development_id": "",
    "project_id": "",
    "project_type": "",
    "gis_latitude": "32.771067",
    "gis_longitude": "-117.073565",
    "approval_id": "PMT-3423211",
    "approval_type": "Zone History Letter",
    "approval_issue_date": "2026-07-17",
}


@pytest.fixture
def producer():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        return DOBPermitsProducer()


def _within(bbox, lat, lng):
    return (
        bbox["min_lat"] <= lat <= bbox["max_lat"]
        and bbox["min_lng"] <= lng <= bbox["max_lng"]
    )


def test_san_diego_permit_row_parses(producer):
    event = producer.parse_socrata_row(PERMIT_ROW)
    assert event is not None
    assert event.city_id == "san_diego"
    assert event.job_id == "PMT-3327015"
    assert event.status == "Issued"
    assert event.issuance_date is not None
    assert event.filing_date is not None
    assert event.estimated_cost == pytest.approx(162522.27)
    assert event.address_street == "2680 Broadway, San Diego, CA"
    assert event.latitude == pytest.approx(32.71615107)
    assert event.longitude == pytest.approx(-117.13655017)
    assert event.h3_res9


def test_non_permit_approval_is_dropped(producer):
    """Zone letters / process agreements / use certificates are not permits."""
    assert producer.parse_socrata_row(NON_PERMIT_ROW) is None


def test_permit_like_classification():
    assert _is_permit_like_approval("Combination Building Permit")
    assert _is_permit_like_approval("Construction Change - Building")
    assert _is_permit_like_approval("Electrical Pmt")
    assert _is_permit_like_approval("Approval - Construction - Demolition Pmt")
    assert not _is_permit_like_approval("Zone History Letter")
    assert not _is_permit_like_approval("Approval - Process - Agreement")
    assert not _is_permit_like_approval("Mills Act Agreement")
    assert not _is_permit_like_approval("Map - Easement Dedication")
    assert not _is_permit_like_approval(None)


def test_san_diego_fixture_lands_inside_metro_bbox(producer):
    event = producer.parse_socrata_row(PERMIT_ROW)
    assert event is not None
    assert _within(REGISTRY[CityId.SAN_DIEGO].metro_bbox, event.latitude, event.longitude)


def test_san_diego_registration_scope_and_job_names():
    # Permits (US-91) + Get It Done 311 (US-124) + Business Tax Certificates
    # (US-125) registered; no sales feed exists in the SD open-data inventory,
    # and the remaining families are CSV-only too.
    reg = REGISTRY[CityId.SAN_DIEGO]
    assert FeedType.PERMITS in reg.datasets
    assert FeedType.COMPLAINTS_311 in reg.datasets
    assert FeedType.SLA in reg.datasets
    assert FeedType.DEEDS not in reg.datasets
    assert get_job_name(FeedType.PERMITS, CityId.SAN_DIEGO) == "permits_sd"
    assert get_job_name(FeedType.COMPLAINTS_311, CityId.SAN_DIEGO) == "311_sd"
    assert get_job_name(FeedType.SLA, CityId.SAN_DIEGO) == "sla_sd"


def test_san_diego_spec_declares_csv_platform_and_year_rollover():
    spec = get_dataset(CityId.SAN_DIEGO, FeedType.PERMITS)
    assert spec.platform == "csv"
    assert spec.watermark_col == "approval_issue_date"
    assert spec.topic == "raw.municipal.permits"
    assert spec.endpoint.startswith("https://seshat.datasd.org/")
    by_year = spec.extra["endpoint_by_year"]
    assert by_year["2026"].endswith("approvals_issued_2026_datasd.csv")
    assert by_year["2027"].endswith("approvals_issued_2027_datasd.csv")
    assert resolve_endpoint_resolves_current_year(spec)


def resolve_endpoint_resolves_current_year(spec) -> bool:
    from datetime import date

    from src.spatial.city_registry import resolve_endpoint

    resolved = resolve_endpoint(spec, today=date(2026, 8, 24))
    return resolved == spec.extra["endpoint_by_year"]["2026"]


# ---------------------------------------------------------------------------
# CSVClient: static-CSV ingestion (download once, filter client-side)
# ---------------------------------------------------------------------------

SAMPLE_CSV = (
    "APPROVAL_ID,APPROVAL_TYPE,APPROVAL_ISSUE_DATE\n"
    '"PMT-1","Combination Building Permit","2026-01-15"\n'
    '"PMT-2","Zone History Letter","2026-02-20"\n'
    '"PMT-3","Electrical Pmt","2026-03-25"\n'
)


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class _FakeHTTP:
    def __init__(self, text):
        self.text = text

    def get(self, url):
        return _FakeResponse(self.text)


def test_csv_client_filters_rows_by_watermark_predicate():
    client = CSVClient(http_client=_FakeHTTP(SAMPLE_CSV))
    rows = list(
        client.paginate(
            "https://seshat.datasd.org/development_permits/approvals_issued_2026_datasd.csv",
            where_clause="approval_issue_date > '2026-02-01'",
        )
    )
    ids = [r["approval_id"] for batch in rows for r in batch]
    assert ids == ["PMT-2", "PMT-3"]


def test_csv_client_lowercases_headers_and_batches():
    client = CSVClient(http_client=_FakeHTTP(SAMPLE_CSV))
    batches = list(client.paginate("https://x/y.csv", batch_size=2))
    assert sum(len(b) for b in batches) == 3
    assert set(batches[0][0].keys()) == {"approval_id", "approval_type", "approval_issue_date"}


def test_row_matches_handles_null_guard():
    row = {"a": "", "b": "x"}
    assert _row_matches("a is not null", row) is False
    assert _row_matches("b is not null", row) is True
    assert _row_matches(None, row) is True


# ---------------------------------------------------------------------------
# US-124: San Diego Get It Done 311 (flat CSV, native lat/lng)
# ---------------------------------------------------------------------------

SD_311_ROW = {
    "service_request_id": "5481990",
    "service_request_parent_id": "",
    "sap_notification_number": "",
    "date_requested": "2025-12-08 14:42:00.000",
    "case_age_days": "32",
    "case_record_type": "ESD Complaint/Report",
    "service_name": "ESD Complaint/Report",
    "service_name_detail": "ESD Collections",
    "date_closed": "2026-01-09",
    "status": "Closed",
    "lat": "32.76011506",
    "lng": "-117.13107145",
    "street_address": "4545 KANSAS ST, San Diego, CA 92116",
    "zipcode": "92116",
    "council_district": "3",
    "comm_plan_code": "28",
    "comm_plan_name": "NORTH PARK",
    "park_name": "",
    "case_origin": "Phone",
    "referred": "",
    "iamfloc": "SS-034889-PV1",
    "floc": "SA-002143-PV1",
    "public_description": "REHRIG, gray onsite, remove single home, T92184091",
}


@pytest.fixture
def complaints():
    from src.producers.complaints_311_producer import Complaints311Producer

    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        return Complaints311Producer()


def test_san_diego_311_spec_declares_csv_platform_and_rollover():
    spec = get_dataset(CityId.SAN_DIEGO, FeedType.COMPLAINTS_311)
    assert spec.platform == "csv"
    assert spec.watermark_col == "date_requested"
    assert spec.id_keys == ["service_request_id"]
    assert spec.topic == "raw.municipal.311"
    assert spec.endpoint.startswith("https://seshat.datasd.org/get_it_done_reports/")
    by_year = spec.extra["endpoint_by_year"]
    assert by_year["2026"].endswith("get_it_done_requests_closed_2026_datasd.csv")
    assert by_year["2027"].endswith("get_it_done_requests_closed_2027_datasd.csv")
    assert by_year["2016"].endswith("get_it_done_requests_closed_2016_datasd.csv")
    assert resolve_endpoint(spec, today=date(2026, 8, 24)) == by_year["2026"]
    assert spec.extra["companion_endpoints"]["open"].endswith(
        "get_it_done_requests_open_datasd.csv"
    )


def test_san_diego_311_field_map_is_lowercase():
    from src.producers.field_maps import resolve_field_map

    field_map = resolve_field_map("san_diego", FeedType.COMPLAINTS_311)
    assert field_map["incident_id"] == ["service_request_id"]
    assert field_map["created_date"] == ["date_requested"]
    assert field_map["closed_date"] == ["date_closed"]
    assert field_map["complaint_type"] == ["service_name", "service_name_detail"]
    assert field_map["latitude"] == ["lat"]
    assert field_map["longitude"] == ["lng"]
    assert field_map["incident_address"] == ["street_address"]
    assert field_map["zipcode"] == ["zipcode"]
    assert field_map["borough"] == ["council_district", "comm_plan_name"]
    assert all(all(k in SD_311_ROW for k in candidates) for candidates in field_map.values())


def test_san_diego_311_row_parses(complaints):
    event = complaints.parse_socrata_row(SD_311_ROW, city_id="san_diego")
    assert event is not None
    assert event.city_id == "san_diego"
    assert event.incident_id == "5481990"
    assert event.complaint_type == "ESD Complaint/Report"
    assert event.latitude == pytest.approx(32.76011506)
    assert event.longitude == pytest.approx(-117.13107145)
    assert event.zipcode == "92116"
    assert event.status == "Closed"
    assert event.source_neighborhood == "3"


def test_san_diego_311_dates_and_address_map(complaints):
    event = complaints.parse_socrata_row(SD_311_ROW, city_id="san_diego")
    assert event is not None
    assert event.created_date is not None
    assert str(event.created_date).startswith("2025-12-08")
    assert str(event.closed_date).startswith("2026-01-09")
    assert event.incident_address == "4545 KANSAS ST, San Diego, CA 92116"


def test_san_diego_311_autodetects_without_city_id(complaints):
    assert complaints.parse_socrata_row(SD_311_ROW).city_id == "san_diego"


def test_san_diego_311_fixture_lands_inside_metro_bbox(complaints):
    event = complaints.parse_socrata_row(SD_311_ROW, city_id="san_diego")
    assert event is not None
    assert _within(REGISTRY[CityId.SAN_DIEGO].metro_bbox, event.latitude, event.longitude)


def test_san_diego_311_rejects_null_island_placeholder(complaints):
    row = dict(SD_311_ROW, lat="0.0", lng="0.0")
    assert complaints.parse_socrata_row(row, city_id="san_diego") is None


def test_san_diego_311_autodetect_does_not_shadow_san_francisco(complaints):
    sf_row = {
        "service_request_id": "SF-100",
        "service_name": "Illegal Dumping",
        "service_details": "sidewalk",
        "requested_datetime": "2026-08-01T10:00:00.000",
        "latitude": "37.7749",
        "longitude": "-122.4194",
    }
    event = complaints.parse_socrata_row(sf_row)
    assert event is not None
    assert event.city_id == "san_francisco"


def test_san_diego_311_csv_client_filters_by_watermark():
    # date_requested is ISO with a time component; the scheduler renders a
    # string-compare watermark predicate that CSVClient evaluates client-side.
    sample = (
        "service_request_id,service_name,date_requested,date_closed,lat,lng,zipcode\n"
        '"5481990","ESD Complaint/Report","2025-12-08 14:42:00.000","2026-01-09","32.76","-117.13","92116"\n'
        '"5482056","Parking","2026-08-24 19:32:00.000","2026-08-25","32.71","-117.14","92102"\n'
    )
    client = CSVClient(http_client=_FakeHTTP(sample))
    rows = list(
        client.paginate(
            "https://seshat.datasd.org/get_it_done_reports/get_it_done_requests_closed_2026_datasd.csv",
            where_clause="date_requested > '2026-08-01'",
        )
    )
    ids = [r["service_request_id"] for batch in rows for r in batch]
    assert ids == ["5482056"]
    assert set(rows[0][0].keys()) == {
        "service_request_id",
        "service_name",
        "date_requested",
        "date_closed",
        "lat",
        "lng",
        "zipcode",
    }


# ---------------------------------------------------------------------------
# US-125: San Diego Business Tax Certificates (flat CSV SNAPSHOT, native lat/lng)
# ---------------------------------------------------------------------------

SD_SLA_ROW = {
    "account_key": "1974007524.0",
    "account_status": "Active",
    "date_account_creation": "1974-07-01 12:00:00",
    "date_cert_expiration": "2027-06-30 00:00:00",
    "date_cert_effective": "2026-07-01 00:00:00",
    "business_owner_name": "FILLIPPIS PIZZA GROTTO PACIFIC BEACH INC",
    "ownership_type": "INC",
    "date_business_start": "1974-07-01 12:00:00",
    "dba_name": "FILIPPIS PIZZA GROTTO",
    "naics_sector": "72",
    "naics_code": "722",
    "naics_description": "FULL-SERVICE RESTAURANTS",
    "address_no": "962",
    "address_pd": "",
    "address_road": "GARNET",
    "address_sfx": "AVE",
    "address_no_fraction": "",
    "address_city": "SAN DIEGO",
    "address_state": "CA",
    "address_zip": "92109-2728",
    "address_suite": "",
    "address_pmb_box": "",
    "address_po_box": "",
    "bid": "24.0",
    "council_district": "2.0",
    "lat": "32.79727277",
    "lng": "-117.2525396",
}


@pytest.fixture
def sla():
    from src.producers.sla_licenses_producer import SLALicensesProducer

    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        return SLALicensesProducer()


def test_san_diego_sla_spec_declares_csv_platform_and_snapshot():
    spec = get_dataset(CityId.SAN_DIEGO, FeedType.SLA)
    assert spec.platform == "csv"
    assert spec.watermark_col == "date_account_creation"
    assert spec.id_keys == ["account_key"]
    assert spec.topic == "raw.municipal.sla"
    assert spec.endpoint.startswith("https://seshat.datasd.org/business_tax_certificates/")
    assert spec.endpoint.endswith("sd_businesses_active_datasd.csv")
    assert spec.extra["ingestion_mode"] == "snapshot"
    assert spec.producer_key == "sla"


def test_san_diego_sla_field_map_is_lowercase():
    from src.producers.field_maps import resolve_field_map

    field_map = resolve_field_map("san_diego", FeedType.SLA)
    assert field_map["license_id"] == ["account_key"]
    assert field_map["effective_date"] == ["date_cert_effective"]
    assert field_map["expiration_date"] == ["date_cert_expiration"]
    assert field_map["license_type"] == ["naics_description", "naics_sector"]
    assert field_map["dba"] == ["dba_name"]
    assert field_map["latitude"] == ["lat"]
    assert field_map["longitude"] == ["lng"]
    assert field_map["borough"] == ["council_district", "bid"]
    assert field_map["address_street"] == ["address_road"]
    assert all(all(k in SD_SLA_ROW for k in candidates) for candidates in field_map.values())


def test_san_diego_sla_row_parses_and_normalizes_account_key(sla):
    event = sla.parse_socrata_row(SD_SLA_ROW, city_id="san_diego")
    assert event is not None
    assert event.city_id == "san_diego"
    assert event.license_id == "1974007524"  # float-string "…524.0" normalized
    assert event.dba == "FILIPPIS PIZZA GROTTO"
    assert event.license_type == "FULL-SERVICE RESTAURANTS"
    assert event.effective_date is not None
    assert str(event.effective_date).startswith("2026-07-01")
    assert str(event.expiration_date).startswith("2027-06-30")
    assert event.latitude == pytest.approx(32.79727277)
    assert event.longitude == pytest.approx(-117.2525396)
    assert event.h3_res9


def test_san_diego_sla_autodetects_without_city_id(sla):
    assert sla.parse_socrata_row(SD_SLA_ROW).city_id == "san_diego"


def test_san_diego_sla_fixture_lands_inside_metro_bbox(sla):
    event = sla.parse_socrata_row(SD_SLA_ROW, city_id="san_diego")
    assert event is not None
    assert _within(REGISTRY[CityId.SAN_DIEGO].metro_bbox, event.latitude, event.longitude)


def test_san_diego_sla_autodetect_does_not_shadow_san_francisco(sla):
    sf_row = {
        "location_id": "SF-100",
        "dba_name": "SF BAR",
        "naics_code_description": "Drinking Places",
        "lic_code_description": "On-Sale",
        "business_start_date": "2020-01-01",
        "latitude": "37.7749",
        "longitude": "-122.4194",
    }
    event = sla.parse_socrata_row(sf_row)
    assert event is not None
    assert event.city_id == "san_francisco"
    # SD ships dba_name + naics_* too — but without the account_key id the
    # row cannot be the SD business-cert feed and must NOT be claimed as SD.
    ambig = dict(SD_SLA_ROW)
    del ambig["account_key"]
    assert sla.parse_socrata_row(ambig) is None
    # A 0.0/0.0 placeholder is rejected (null-island guard).
    assert sla.parse_socrata_row(dict(SD_SLA_ROW, lat="0.0", lng="0.0"), city_id="san_diego") is None


def test_san_diego_sla_snapshot_csv_client_lowercases_headers():
    # Snapshot feed: full re-download; CSVClient lowercases the UPPERCASE
    # source headers so the lowercase field_map applies.
    sample = (
        "ACCOUNT_KEY,DATE_ACCOUNT_CREATION,DATE_CERT_EFFECTIVE,DATE_CERT_EXPIRATION,"
        "NAICS_DESCRIPTION,NAICS_SECTOR,DBA_NAME,LAT,LNG,COUNCIL_DISTRICT,BID\n"
        '"1974007524.0","1974-07-01 12:00:00","2026-07-01 00:00:00","2027-06-30 00:00:00",'
        '"FULL-SERVICE RESTAURANTS","72","FILIPPIS PIZZA GROTTO","32.79727277","-117.2525396","2.0","24.0"\n'
        '"1974007530.0","2020-05-01 00:00:00","2026-07-01 00:00:00","2027-06-30 00:00:00",'
        '"DEPT STORES","44","NORDSTROM","32.71","-117.14","6.0",""\n'
    )
    client = CSVClient(http_client=_FakeHTTP(sample))
    rows = list(
        client.paginate(
            "https://seshat.datasd.org/business_tax_certificates/sd_businesses_active_datasd.csv",
            where_clause="date_cert_effective > '2026-01-01'",
        )
    )
    assert len(rows[0]) == 2
    assert set(rows[0][0].keys()) == {
        "account_key",
        "date_account_creation",
        "date_cert_effective",
        "date_cert_expiration",
        "naics_description",
        "naics_sector",
        "dba_name",
        "lat",
        "lng",
        "council_district",
        "bid",
    }
    assert rows[0][0]["account_key"] == "1974007524.0"