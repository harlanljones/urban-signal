"""Contract tests for Milwaukee PERMITS + DEEDS (US-138 leaf).

These tests run WITHOUT spine registration: Milwaukee is still SLA-only in
``city_registry.REGISTRY`` (the PERMITS/DEEDS specs live as data in
``src/spatial/cities/milwaukee.py`` and are lifted into the registry by the
interlock orchestrator). The parser tests patch ``resolve_field_map`` to hand
back the exact field maps proposed for Milwaukee, proving every column spelling
resolves through the shared producers before the registry edit lands.

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

    def test_permits_spec_is_arcgis_with_geocode_flag(self):
        assert MILWAUKEE_PERMITS_SPEC["platform"] == "arcgis"
        assert MILWAUKEE_PERMITS_SPEC["watermark_col"] == "ISSUE_DATE"
        assert MILWAUKEE_PERMITS_SPEC["producer_key"] == "permits"
        assert MILWAUKEE_PERMITS_SPEC["extra"]["needs_geocode"] is True
        assert MILWAUKEE_PERMITS_SPEC["extra"]["geocode_context"] == "Milwaukee, WI"

    def test_deeds_spec_declares_typed_text_watermark(self):
        extra = MILWAUKEE_DEEDS_SPEC["extra"]
        assert MILWAUKEE_DEEDS_SPEC["platform"] == "arcgis"
        assert MILWAUKEE_DEEDS_SPEC["watermark_col"] == "RECORDING_DATE"
        assert MILWAUKEE_DEEDS_SPEC["producer_key"] == "deeds"
        assert extra["watermark_type"] == "text"
        assert extra["watermark_format"] == "%Y-%m-%d"
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
            "borough",
            "zipcode",
        }
        deed_keys = {
            "doc_id",
            "bbl",
            "document_amount",
            "recorded_date",
            "party1_grantor",
            "party2_grantee",
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
        entry = typed_watermark_entry("2026-06-15", fmt=fmt)
        assert entry is not None
        assert entry[0] == "2026-06-15"
        assert entry[1].year == 2026

    def test_empty_value_is_dropped(self, fmt):
        assert typed_watermark_entry("", fmt=fmt) is None
        assert typed_watermark_entry(None, fmt=fmt) is None

    def test_sentinel_is_excluded(self, fmt):
        # Representative far-future placeholder a source might use to mark an
        # "unknown date" — parses under the declared format so it would win a
        # DESC ordering without exclusion.
        assert typed_watermark_entry("9999-12-31", fmt=fmt, exclude=["9999-12-31"]) is None
        # The same value would be KEPT (and poison a DESC ordering) without the
        # exclusion — the whole point of ADR-0005.
        kept = typed_watermark_entry("9999-12-31", fmt=fmt)
        assert kept is not None

    def test_exclude_clause_builds_for_arcgis_where(self):
        clause = watermark_exclude_clause(
            MILWAUKEE_DEEDS_SPEC["watermark_col"], ["9999-12-31", "0000-00-00"]
        )
        assert clause == "RECORDING_DATE NOT IN ('9999-12-31', '0000-00-00')"
        # No exclusions -> no clause (caller skips the param).
        assert watermark_exclude_clause("RECORDING_DATE", []) is None


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
        # ArcGIS-flattened building-permit row (uppercase attrs; DateOnly
        # ISSUE_DATE as a "YYYY-MM-DD" string, native point geometry lifted to
        # latitude/longitude so no geocode call is required for this test).
        return {
            "PERMIT_NO": "BP-2026-012345",
            "OBJECTID": 88231,
            "ADDRESS": "123 N Water St",
            "ISSUE_DATE": "2026-08-15",
            "APPLICATION_DATE": "2026-07-30",
            "PERMIT_TYPE": "Building Alteration",
            "ESTIMATED_COST": 250000,
            "NEIGHBORHOOD": "DOWNTOWN",
            "ZIP_CODE": "53202",
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
        assert ev.source_neighborhood == "DOWNTOWN"
        assert ev.zipcode == "53202"
        assert ev.address_street == "123 N Water St"
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
            "DOCUMENT_NO": "2026-123456",
            "OBJECTID": 990012,
            "PARCEL_NO": "123-456-789",
            "SALE_PRICE": 350000,
            "RECORDING_DATE": "2026-06-15",
            "GRANTOR": "JOHN DOE TRUST",
            "GRANTEE": "JANE SMITH LLC",
            "NEIGHBORHOOD": "BAY VIEW",
            "ZIP_CODE": "53207",
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
        assert ev.party1_grantor == "JOHN DOE TRUST"
        assert ev.party2_grantee == "JANE SMITH LLC"
        assert ev.source_neighborhood == "BAY VIEW"
        assert ev.latitude == pytest.approx(42.9998)
        assert ev.longitude == pytest.approx(-87.9057)
        assert ev.h3_res7 is not None
