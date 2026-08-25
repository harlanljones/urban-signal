"""Unit tests for the US-91 San Diego registration (permits-only, flat-CSV).

Fixtures mirror live rows read 2026-08-24 from
``approvals_issued_2026_datasd.csv``. The approvals table is broader than
permits; non-permit approval classes drop at parse time.
"""

from unittest.mock import patch

import pytest

from src.producers.csv_client import CSVClient, _row_matches
from src.producers.dob_permits_producer import DOBPermitsProducer, _is_permit_like_approval
from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset, get_job_name

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
    # Permits-only partial registration: no sales feed exists in the SD open-
    # data inventory, and the remaining families are CSV-only too.
    reg = REGISTRY[CityId.SAN_DIEGO]
    assert FeedType.PERMITS in reg.datasets
    for feed in (FeedType.COMPLAINTS_311, FeedType.SLA, FeedType.DEEDS):
        assert feed not in reg.datasets
    assert get_job_name(FeedType.PERMITS, CityId.SAN_DIEGO) == "permits_sd"


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