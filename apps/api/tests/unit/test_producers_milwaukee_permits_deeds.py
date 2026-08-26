"""Contract tests for Milwaukee PERMITS + DEEDS (US-138 leaf).

These tests pin the live CKAN CSV schema and the registered Milwaukee feed
contracts. The parser tests patch ``resolve_field_map`` to isolate the producer
field-map behavior from the larger city registry.

Two previously-blocking capabilities are asserted as ready:
  * ADR-0004 geocoder — PERMITS ships ``needs_geocode`` (address-only coords).
  * ADR-0005 typed text watermark — DEEDS declares ``watermark_type="text"``
    with a format and sentinel-exclusion path (tested against the helper).
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps_milwaukee_permits_deeds import FIELD_MAP
from src.producers.watermarks import typed_watermark_entry, watermark_exclude_clause
from src.spatial.cities.milwaukee import (
    MILWAUKEE_DEEDS_FIELD_MAP,
    MILWAUKEE_DEEDS_SPEC,
    MILWAUKEE_PERMITS_FIELD_MAP,
    MILWAUKEE_PERMITS_SPEC,
)
from src.spatial.city_registry import FeedType


# ---------------------------------------------------------------------------
# Spec + field-map data shape (spine consumes these verbatim)
# ---------------------------------------------------------------------------


class TestMilwaukeePermitsDeedsSpecShape:
    def test_field_maps_keyed_by_permits_and_deeds(self):
        assert set(FIELD_MAP) == {FeedType.PERMITS, FeedType.DEEDS}

    def test_permits_spec_is_csv_with_geocode_flag(self):
        assert MILWAUKEE_PERMITS_SPEC["platform"] == "csv"
        assert MILWAUKEE_PERMITS_SPEC["watermark_col"] == "date_issued"
        assert MILWAUKEE_PERMITS_SPEC["producer_key"] == "permits"
        assert MILWAUKEE_PERMITS_SPEC["extra"]["expected_cadence_days"] == 90
        assert MILWAUKEE_PERMITS_SPEC["extra"]["needs_geocode"] is True
        assert MILWAUKEE_PERMITS_SPEC["extra"]["geocode_context"] == "Milwaukee, WI"

    def test_deeds_spec_declares_typed_text_watermark(self):
        extra = MILWAUKEE_DEEDS_SPEC["extra"]
        assert MILWAUKEE_DEEDS_SPEC["platform"] == "csv"
        assert MILWAUKEE_DEEDS_SPEC["watermark_col"] == "sale_date"
        assert MILWAUKEE_DEEDS_SPEC["producer_key"] == "deeds"
        assert extra["expected_cadence_days"] == 365
        assert extra["ingestion_mode"] == "snapshot"
        assert extra["watermark_type"] == "text"
        assert extra["watermark_format"] == "%m/%d/%Y"
        assert isinstance(extra["watermark_exclude"], list)

    def test_field_maps_expose_canonical_producer_keys(self):
        # Canonical keys the shared producers actually consult.
        permit_keys = {
            "job_id",
            "address_street",
            "issuance_date",
            "filing_date",
            "job_type",
            "cost",
        }
        deed_keys = {
            "doc_id",
            "bbl",
            "document_amount",
            "recorded_date",
            "doc_type",
            "borough",
        }
        assert permit_keys <= set(MILWAUKEE_PERMITS_FIELD_MAP)
        assert deed_keys <= set(MILWAUKEE_DEEDS_FIELD_MAP)


# ---------------------------------------------------------------------------
# ADR-0005 typed text watermark handling (DEEDS)
# ---------------------------------------------------------------------------


class TestMilwaukeeDeedsTypedWatermark:
    """DEEDS arrives as a text date column; ADR-0005 declares the format and an
    exclusion list so sentinels cannot pin the watermark. Real sentinel
    spellings are discovered live and appended to ``watermark_exclude`` at spine
    time — these tests exercise the mechanism with a representative sentinel."""

    @pytest.fixture
    def fmt(self):
        return MILWAUKEE_DEEDS_SPEC["extra"]["watermark_format"]

    def test_real_date_parses_under_declared_format(self, fmt):
        entry = typed_watermark_entry("06/15/2026", fmt=fmt)
        assert entry is not None
        assert entry[0] == "06/15/2026"
        assert entry[1].year == 2026

    def test_empty_value_is_dropped(self, fmt):
        assert typed_watermark_entry("", fmt=fmt) is None
        assert typed_watermark_entry(None, fmt=fmt) is None

    def test_sentinel_is_excluded(self, fmt):
        # Representative far-future placeholder a source might use to mark an
        # "unknown date" — parses under the declared format so it would win a
        # DESC ordering without exclusion.
        assert typed_watermark_entry("12/31/9999", fmt=fmt, exclude=["12/31/9999"]) is None
        # The same value would be KEPT (and poison a DESC ordering) without the
        # exclusion — the whole point of ADR-0005.
        kept = typed_watermark_entry("12/31/9999", fmt=fmt)
        assert kept is not None

    def test_exclude_clause_builds_for_where(self):
        clause = watermark_exclude_clause(
            MILWAUKEE_DEEDS_SPEC["watermark_col"], ["12/31/9999", "01/01/0001"]
        )
        assert clause == "sale_date NOT IN ('12/31/9999', '01/01/0001')"
        # No exclusions -> no clause (caller skips the param).
        assert watermark_exclude_clause("sale_date", []) is None


# ---------------------------------------------------------------------------
# Producer parsing against the proposed field maps (no spine registration)
# ---------------------------------------------------------------------------


class TestMilwaukeePermitsParsing:
    @pytest.fixture
    def producer(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    @pytest.fixture(autouse=True)
    def _map(self, monkeypatch):
        import src.producers.field_maps as fm

        monkeypatch.setattr(
            fm,
            "resolve_field_map",
            lambda city_value, feed: FIELD_MAP.get(feed, {}),
            raising=True,
        )

    @pytest.fixture
    def permit_row(self):
        # CSVClient-normalized building-permit row. Native coordinates are
        # supplied so this parser contract does not call the live geocoder.
        return {
            "record_id": "BP-2026-012345",
            "address": "123 N Water St",
            "date_issued": "2026-08-15 00:00:00",
            "date_opened": "2026-07-30 00:00:00",
            "permit_type": "Building Alteration",
            "construction_total_cost": 250000,
            "latitude": 43.0389,
            "longitude": -87.9065,
        }

    def test_permits_row_resolves_through_proposed_map(self, producer, permit_row):
        ev = producer.parse_socrata_row(permit_row, city_id="milwaukee")
        assert ev is not None
        assert ev.city_id == "milwaukee"
        assert ev.job_id == "BP-2026-012345"
        assert str(ev.issuance_date).startswith("2026-08-15")
        assert str(ev.filing_date).startswith("2026-07-30")
        assert ev.job_type.value == "A2"  # "ALTERATION" -> A2
        assert ev.estimated_cost == 250000.0
        assert ev.latitude == pytest.approx(43.0389)
        assert ev.longitude == pytest.approx(-87.9065)
        assert ev.h3_res7 is not None


class TestMilwaukeeDeedsParsing:
    @pytest.fixture
    def producer(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @pytest.fixture(autouse=True)
    def _map(self, monkeypatch):
        import src.producers.field_maps as fm

        monkeypatch.setattr(
            fm,
            "resolve_field_map",
            lambda city_value, feed: FIELD_MAP.get(feed, {}),
            raising=True,
        )

    @pytest.fixture
    def deed_row(self):
        return {
            "propertyid": "2026-123456",
            "taxkey": "123-456-789",
            "address": "123 N Water St",
            "sale_price": 350000,
            "sale_date": "06/15/2026",
            "proptype": "Residential",
            "latitude": 42.9998,
            "longitude": -87.9057,
        }

    def test_deeds_row_resolves_through_proposed_map(self, producer, deed_row):
        ev = producer.parse_socrata_row(deed_row, city_id="milwaukee")
        assert ev is not None
        assert ev.city_id == "milwaukee"
        assert ev.doc_id == "2026-123456"
        assert ev.bbl == "123-456-789"
        assert ev.document_amount == 350000.0
        assert str(ev.recorded_date).startswith("2026-06-15")
        assert ev.doc_type == "RESIDENTIAL"
        assert ev.latitude == pytest.approx(42.9998)
        assert ev.longitude == pytest.approx(-87.9057)
        assert ev.h3_res7 is not None
