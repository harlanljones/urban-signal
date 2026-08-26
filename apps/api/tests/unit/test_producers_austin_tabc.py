"""Unit tests for the Austin TABC liquor-license (SLA) leaf — US-136.

Austin gains a THIRD feed: a TABC statewide liquor-license dataset
(data.texas.gov `7hf9-qc9f` "TABC License Information"). It carries a street
``address`` string but NO latitude/longitude columns, so it registers with
``needs_geocode: True`` and resolves coordinates via the ADR 0004 geocoder.

The shared ``sla_licenses_producer`` is exercised directly with the TABC field
map patched in via ``resolve_field_map``. Geocoding is stubbed except in the
explicit ADR-0004 plumbing test, so the suite never contacts a provider.
"""

from unittest.mock import patch

import pytest

import src.producers.field_maps as fm
from src.producers.field_maps_austin_tabc import FIELD_MAP, TABC_SLA_FIELD_MAP
from src.spatial.cities.austin import AUSTIN_TABC_SLA_SPEC


@pytest.fixture(autouse=True)
def _tabc_maps(monkeypatch):
    """Hand the producer the exact TABC field map used by the registry."""

    def _resolve(city_value, feed):
        key = feed.value if hasattr(feed, "value") else feed
        return FIELD_MAP.get(key, {})

    monkeypatch.setattr(fm, "resolve_field_map", _resolve, raising=True)


@pytest.fixture(autouse=True)
def _no_live_geocoder(monkeypatch):
    """Keep ordinary parser tests deterministic and offline."""

    class OfflineProvider:
        def geocode(self, query):
            return None

    monkeypatch.setattr("src.spatial.geocoder.get_geocoder", lambda: OfflineProvider())


class TestTabcFieldMapSanity:
    def test_field_map_is_keyed_by_sla_feed_value(self):
        assert "sla" in FIELD_MAP
        assert FIELD_MAP["sla"] is TABC_SLA_FIELD_MAP

    def test_canonical_fields_map_to_real_tabc_columns(self):
        assert TABC_SLA_FIELD_MAP["license_id"] == ["license_id"]
        assert TABC_SLA_FIELD_MAP["license_type"] == ["license_type"]
        assert TABC_SLA_FIELD_MAP["effective_date"] == ["current_issued_date"]
        assert TABC_SLA_FIELD_MAP["expiration_date"] == ["expiration_date"]
        assert TABC_SLA_FIELD_MAP["premises_name"] == ["owner"]
        assert TABC_SLA_FIELD_MAP["dba"] == ["trade_name"]
        assert TABC_SLA_FIELD_MAP["address_street"] == ["address"]
        assert TABC_SLA_FIELD_MAP["status"] == ["license_status"]

    def test_lat_long_are_not_mapped_geocoded_instead(self):
        # No latitude/longitude columns exist on 7hf9-qc9f — geocoding the
        # address recovers coordinates at parse time (ADR 0004), so they must
        # NOT appear in the field map.
        for coord in ("latitude", "longitude"):
            assert coord not in TABC_SLA_FIELD_MAP


class TestTabcProposedSpec:
    def test_spec_points_at_live_tabc_resource(self):
        assert (
            AUSTIN_TABC_SLA_SPEC["endpoint"]
            == "https://data.texas.gov/resource/7hf9-qc9f.json"
        )
        assert AUSTIN_TABC_SLA_SPEC["platform"] == "socrata"
        assert AUSTIN_TABC_SLA_SPEC["producer_key"] == "sla"

    def test_spec_declares_geocode_path(self):
        extra = AUSTIN_TABC_SLA_SPEC["extra"]
        assert extra["needs_geocode"] is True
        assert extra["geocode_context"] == "TX"
        assert extra["where"] == "county = 'Travis'"

    def test_spec_watermark_is_current_issued_date(self):
        assert AUSTIN_TABC_SLA_SPEC["watermark_col"] == "current_issued_date"
        assert AUSTIN_TABC_SLA_SPEC["id_keys"] == ["license_id", "master_file_id"]

    def test_spec_field_map_matches_proposed_map(self):
        assert AUSTIN_TABC_SLA_SPEC["extra"]["field_map"] is TABC_SLA_FIELD_MAP


class TestTabcRowParsing:
    """Live-shape row from data.texas.gov `7hf9-qc9f` (schema pulled
    2026-08-26). Values mirror the dataset's real top/cached contents."""

    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            return __import__(
                "src.producers.sla_licenses_producer", fromlist=["SLALicensesProducer"]
            ).SLALicensesProducer()

    @pytest.fixture
    def tabc_row(self):
        return {
            "master_file_id": 2100008680,
            "license_type": "MB",
            "license_id": 200207279,
            "primary_status": "Active",
            "secondary_status": None,
            "license_status": "Active",
            "current_issued_date": "2026-08-25T00:00:00.000",
            "status_change_date": "2026-08-26T05:00:02.240",
            "expiration_date": "2027-08-31T00:00:00.000",
            "original_issue_date": "2022-05-26T00:00:00.000",
            "tier": "Retail",
            "trade_name": "WINGSTOP",
            "owner": "DOLGENCORP OF TEXAS INC.",
            "address": "2701 S Lamar Blvd",
            "address_2": "STE 100",
            "city": "Austin",
            "state": "TX",
            "zip": "78704",
            "county": "Travis",
        }

    def test_first_mapped_resolves_every_proposed_spelling(self, tabc_row):
        m = TABC_SLA_FIELD_MAP
        assert fm.first_mapped(tabc_row, m, "license_id") == 200207279
        assert fm.first_mapped(tabc_row, m, "license_type") == "MB"
        assert fm.first_mapped(tabc_row, m, "effective_date") == "2026-08-25T00:00:00.000"
        assert fm.first_mapped(tabc_row, m, "expiration_date") == "2027-08-31T00:00:00.000"
        assert fm.first_mapped(tabc_row, m, "premises_name") == "DOLGENCORP OF TEXAS INC."
        assert fm.first_mapped(tabc_row, m, "dba") == "WINGSTOP"
        assert fm.first_mapped(tabc_row, m, "address_street") == "2701 S Lamar Blvd"
        assert fm.first_mapped(tabc_row, m, "status") == "Active"

    def test_first_mapped_returns_none_for_unmapped_latitude(self, tabc_row):
        assert fm.first_mapped(tabc_row, TABC_SLA_FIELD_MAP, "latitude") is None

    def test_event_is_produced_and_typed(self, sla, tabc_row):
        ev = sla.parse_socrata_row(tabc_row, city_id="austin")
        assert ev is not None
        assert ev.city_id == "austin"

    def test_event_carries_mapped_identifiers(self, sla, tabc_row):
        ev = sla.parse_socrata_row(tabc_row, city_id="austin")
        assert ev.license_id == "200207279"
        assert ev.license_type == "MB"
        assert ev.premises_name == "DOLGENCORP OF TEXAS INC."
        assert ev.dba == "WINGSTOP"
        assert ev.license_status == "Active"

    def test_event_dates_parse(self, sla, tabc_row):
        ev = sla.parse_socrata_row(tabc_row, city_id="austin")
        assert str(ev.effective_date).startswith("2026-08-25")
        assert str(ev.expiration_date).startswith("2027-08-31")

    def test_geocode_input_address_is_captured(self, sla, tabc_row):
        ev = sla.parse_socrata_row(tabc_row, city_id="austin")
        assert ev.address == "2701 S Lamar Blvd"
        assert ev.latitude is None
        assert ev.longitude is None

    def test_adr0004_geocoder_resolves_travis_address(self, sla, tabc_row, monkeypatch):
        calls = {}

        def fake_geocode(city, feed, address, context=None):
            calls.update(city=city, feed=feed, address=address, context=context)
            return (30.2672, -97.7431)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        ev = sla.parse_socrata_row(tabc_row, city_id="austin")

        assert (ev.latitude, ev.longitude) == (30.2672, -97.7431)
        assert calls == {
            "city": "austin",
            "feed": "sla",
            "address": "2701 S Lamar Blvd",
            "context": None,
        }

    def test_adr0004_adds_texas_context_to_provider_query(self, monkeypatch):
        from src.spatial import geocoder

        calls = []

        class FakeProvider:
            def geocode(self, query):
                calls.append(query)
                return type("Point", (), {"lat": 30.2672, "lon": -97.7431})()

        monkeypatch.setattr(geocoder, "get_geocoder", lambda: FakeProvider())
        assert geocoder.geocode_row_if_declared("austin", "sla", "2701 S Lamar Blvd") == (
            30.2672,
            -97.7431,
        )
        assert calls == ["2701 S Lamar Blvd, TX"]
