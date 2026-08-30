"""Tests for SBA 7(a)/504 loan producer (US-378)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.producers.sba_loan_producer import (
    SbaLoanProducer,
    _date_val,
    _first_of,
    _float_val,
    _row_key,
)
from src.schemas.models import SbaLoanEvent


# --------------------------------------------------------------------------- #
# helper factories                                                             #
# --------------------------------------------------------------------------- #

def _mock_geocoder(lat=40.7128, lng=-74.0060):
    """Return a geocoder mock that yields the given coordinates on every call."""
    geo = MagicMock()
    result = MagicMock()
    result.latitude = lat
    result.longitude = lng
    geo.geocode.return_value = result
    return geo


def _make_row(**overrides):
    """A representative FOIA CSV row with defaults."""
    return {
        "locationid": "1234567",
        "program": "7a",
        "approvaldate": "2024-03-15",
        "grossapproval": "500000",
        "sbaguaranteedapproval": "375000",
        "naicscode": "541330",
        "borrowername": "ACME Corp",
        "borrstreet": "1 Main St",
        "borrcity": "New York",
        "borrstate": "NY",
        "borrzip": "10001",
        "status": "PIF",
        **overrides,
    }


def _producer(client=None, crosswalk=None, indexer=None, geocoder=None):
    if crosswalk is None:
        crosswalk = MagicMock()
        crosswalk.city_for_point.return_value = None
    return SbaLoanProducer(
        client=client or MagicMock(),
        crosswalk=crosswalk,
        indexer=indexer or MagicMock(),
        geocoder=geocoder or _mock_geocoder(),
    )


# --------------------------------------------------------------------------- #
# column helpers                                                               #
# --------------------------------------------------------------------------- #

class TestFirstOf:
    def test_returns_first_non_none(self):
        row = {"a": None, "b": "", "c": "   ", "d": "value"}
        assert _first_of(row, ("a", "b", "c", "d")) == "value"

    def test_returns_none_when_all_empty(self):
        assert _first_of({"a": None, "b": ""}, ("a", "b")) is None

    def test_skips_whitespace_only(self):
        assert _first_of({"a": "   "}, ("a",)) is None


class TestFloatVal:
    def test_parses_plain_number(self):
        assert _float_val("500000") == 500000.0

    def test_strips_dollar_and_commas(self):
        assert _float_val("$1,234,567.89") == 1234567.89

    def test_returns_none_for_empty_string(self):
        assert _float_val("") is None

    def test_returns_none_for_na(self):
        assert _float_val("N/A") is None

    def test_returns_none_for_none(self):
        assert _float_val(None) is None

    def test_passes_through_float(self):
        assert _float_val(75000.0) == 75000.0

    def test_returns_default_on_parse_error(self):
        assert _float_val("not-a-number", default=0.0) == 0.0


class TestDateVal:
    def test_returns_none_for_none(self):
        assert _date_val(None) is None

    def test_isoformat_object_returns_iso(self):
        dt = datetime(2024, 3, 15, tzinfo=timezone.utc)
        assert _date_val(dt) == "2024-03-15T00:00:00+00:00"

    def test_y_m_d_string(self):
        assert _date_val("2024-03-15") == "2024-03-15"

    def test_m_d_y_string(self):
        assert _date_val("03/15/2024") == "2024-03-15"

    def test_returns_none_for_empty(self):
        assert _date_val("") is None

    def test_returns_none_for_na(self):
        assert _date_val("N/A") is None

    def test_falls_back_to_trimmed(self):
        assert _date_val("2024-03-15 extra") == "2024-03-15"


class TestRowKey:
    def test_uses_location_id_and_program(self):
        row = {"locationid": "1234567.0", "program": "7a"}
        assert _row_key(row) == "1234567:7a"

    def test_falls_back_when_no_key(self):
        row = {"borrowername": "test"}
        key = _row_key(row)
        assert key.startswith("no_key:")

    def test_handles_location_id_variant(self):
        row = {"location_id": "7654321", "programtype": "504"}
        assert _row_key(row) == "7654321:504"


# --------------------------------------------------------------------------- #
# build_event                                                                  #
# --------------------------------------------------------------------------- #

class TestBuildEvent:
    def test_basic_conversion(self):
        producer = _producer()
        event = producer.build_event(_make_row())
        assert event is not None
        assert event.location_id == "1234567"
        assert event.program == "7a"
        assert event.borrower_name == "ACME Corp"
        assert event.borrower_street == "1 Main St"
        assert event.borrower_city == "New York"
        assert event.borrower_state == "NY"
        assert event.borrower_zip == "10001"

    def test_missing_location_id_returns_none(self):
        producer = _producer()
        event = producer.build_event({"program": "7a"})
        assert event is None

    def test_missing_program_returns_none(self):
        producer = _producer()
        event = producer.build_event({"locationid": "123"})
        assert event is None

    def test_status_normalization(self):
        producer = _producer()
        event = producer.build_event(_make_row(status="P I F"))
        assert event.status == "pif"

    @pytest.mark.parametrize("program,expected_fixed", [("7a", False), ("504", True)])
    def test_fixed_asset_flag(self, program, expected_fixed):
        producer = _producer()
        event = producer.build_event(_make_row(program=program))
        assert event.fixed_asset is expected_fixed

    def test_naics_sector_extraction(self):
        producer = _producer()
        event = producer.build_event(_make_row(naicscode="541330"))
        assert event.naics_sector == 54

    def test_naics_sector_none_when_missing(self):
        producer = _producer()
        event = producer.build_event(_make_row(naicscode=""))
        assert event.naics_sector is None

    def test_gross_approval_parsing(self):
        producer = _producer()
        event = producer.build_event(_make_row(grossapproval="$1,000,000"))
        assert event.gross_approval == 1000000.0

    def test_sba_guaranteed_approval(self):
        producer = _producer()
        event = producer.build_event(_make_row(sbaguaranteedapproval="750000"))
        assert event.sba_guaranteed_approval == 750000.0

    def test_approval_date_parsing(self):
        producer = _producer()
        event = producer.build_event(_make_row(approvaldate="03/15/2024"))
        from datetime import datetime
        assert isinstance(event.approval_date, datetime)
        assert event.approval_date.strftime("%Y-%m-%d") == "2024-03-15"

    def test_project_county_carried_forward(self):
        producer = _producer()
        event = producer.build_event(_make_row(projectcounty="New York"))
        assert event.project_county == "New York"

    def test_city_id_defaults_to_national_when_no_coords(self):
        crosswalk = MagicMock()
        crosswalk.zip_point.return_value = None
        producer = _producer(crosswalk=crosswalk)
        producer.geocoder = MagicMock()
        producer.geocoder.geocode.return_value = None
        event = producer.build_event(_make_row(borrstreet="", borrzip=""))
        assert event.city_id == "national"
        assert event.latitude is None

    def test_street_geocode_success(self):
        geo = _mock_geocoder(lat=40.7128, lng=-74.0060)
        crosswalk = MagicMock()
        crosswalk.city_for_point.return_value = "nyc"
        indexer = MagicMock()
        indexer.get_multi_res_hierarchy.return_value = {
            "h3_res7": "87", "h3_res8": "88", "h3_res9": "89",
        }
        producer = _producer(geocoder=geo, crosswalk=crosswalk, indexer=indexer)
        event = producer.build_event(_make_row())
        assert event.city_id == "nyc"
        assert event.latitude == 40.7128
        assert event.longitude == -74.0060
        assert event.h3_res9 == "89"

    def test_geocode_fallback_to_zip(self):
        geo = MagicMock()
        geo.geocode.return_value = None
        crosswalk = MagicMock()
        point = MagicMock()
        point.latitude = 41.8781
        point.longitude = -87.6298
        crosswalk.zip_point.return_value = point
        crosswalk.city_for_point.return_value = "chicago"
        indexer = MagicMock()
        indexer.get_multi_res_hierarchy.return_value = {
            "h3_res7": "77", "h3_res8": "78", "h3_res9": "79",
        }
        producer = _producer(geocoder=geo, crosswalk=crosswalk, indexer=indexer)
        event = producer.build_event(_make_row(borrstreet="", borrzip="60601"))
        crosswalk.zip_point.assert_called_once_with("60601")
        assert event.city_id == "chicago"
        assert event.latitude == 41.8781
        assert event.longitude == -87.6298

    def test_as_of_date_on_event(self):
        producer = _producer()
        as_of = datetime(2026, 6, 30, tzinfo=timezone.utc)
        event = producer.build_event(_make_row(), as_of_date=as_of)
        assert event.as_of_date == as_of

    def test_invalid_program_rejected(self):
        producer = _producer()
        event = producer.build_event(_make_row(program="invalid"))
        assert event is None


# --------------------------------------------------------------------------- #
# _geocode                                                                     #
# --------------------------------------------------------------------------- #

class TestGeocode:
    def test_street_geocode_called_with_address_parts(self):
        geo = _mock_geocoder()
        producer = _producer(geocoder=geo)
        row = _make_row()
        lat, lng = producer._geocode(row)
        geo.geocode.assert_called_once()
        call_arg = geo.geocode.call_args[0][0]
        assert "1 Main St" in call_arg
        assert "New York" in call_arg
        assert "NY" in call_arg

    def test_zip_fallback_when_street_empty(self):
        geo = MagicMock()
        geo.geocode.return_value = None
        crosswalk = MagicMock()
        point = MagicMock()
        point.latitude = 34.0522
        point.longitude = -118.2437
        crosswalk.zip_point.return_value = point
        producer = _producer(geocoder=geo, crosswalk=crosswalk)
        lat, lng = producer._geocode(_make_row(borrstreet="", borrzip="90001"))
        crosswalk.zip_point.assert_called_once_with("90001")
        assert lat == 34.0522
        assert lng == -118.2437

    def test_returns_none_when_no_address_or_zip(self):
        geocoder = MagicMock()
        geocoder.geocode.return_value = None
        producer = _producer(geocoder=geocoder)
        lat, lng = producer._geocode(_make_row(borrstreet="", borrcity="", borrstate="", borrzip=""))
        assert lat is None
        assert lng is None


# --------------------------------------------------------------------------- #
# run_stream                                                                   #
# --------------------------------------------------------------------------- #

class TestRunStream:
    def test_emits_events_for_both_programs(self):
        client = MagicMock()

        def mock_primary_file(program):
            ref = MagicMock()
            ref.as_of_date = datetime(2026, 6, 30, tzinfo=timezone.utc)
            ref.url = f"https://example.com/{program}.csv"
            return ref
        client.primary_file.side_effect = mock_primary_file

        rows_7a = [
            {"locationid": "100", "program": "7a", "grossapproval": "100000",
             "borrstreet": "1 Main St", "borrcity": "NYC", "borrstate": "NY",
             "borrzip": "10001", "naicscode": "541330", "approvaldate": "2024-01-01"},
            {"locationid": "101", "program": "7a", "grossapproval": "200000",
             "borrstreet": "2 Oak Ave", "borrcity": "NYC", "borrstate": "NY",
             "borrzip": "10002", "naicscode": "236220", "approvaldate": "2024-02-01"},
        ]
        rows_504 = [
            {"locationid": "200", "program": "504", "grossapproval": "300000",
             "borrstreet": "3 Broad St", "borrcity": "NYC", "borrstate": "NY",
             "borrzip": "10003", "naicscode": "531110", "projectcounty": "New York",
             "approvaldate": "2024-03-01"},
        ]
        client.loan_rows.side_effect = [
            iter([rows_7a]),
            iter([rows_504]),
        ]

        geo = _mock_geocoder()
        crosswalk = MagicMock()
        crosswalk.city_for_point.return_value = "nyc"
        indexer = MagicMock()
        indexer.get_multi_res_hierarchy.return_value = {
            "h3_res7": "87", "h3_res8": "88", "h3_res9": "89",
        }

        producer = _producer(client=client, geocoder=geo, crosswalk=crosswalk, indexer=indexer)
        producer.producer = MagicMock()

        emitted = producer.run_stream()

        assert emitted == 3
        assert producer.producer.produce.call_count == 3
        for call in producer.producer.produce.call_args_list:
            args, kwargs = call
            assert len(args) >= 1 and args[0] == "raw.sba.loans"
        assert producer.producer.flush.called

    def test_dlq_routing_for_build_failures(self):
        client = MagicMock()
        client.primary_file.return_value.as_of_date = datetime(2026, 6, 30, tzinfo=timezone.utc)
        rows = [
            {"locationid": "100", "program": "7a", "grossapproval": "100000"},
            {"program": "7a"},
        ]
        client.loan_rows.return_value = iter([rows])

        producer = _producer(client=client)
        producer.producer = MagicMock()

        emitted = producer.run_stream()
        assert emitted == 1
        assert producer.producer.route_to_dlq.called

    def test_skips_program_when_no_primary_file(self):
        client = MagicMock()
        client.primary_file.side_effect = ValueError("no primary file")
        producer = _producer(client=client)
        producer.producer = MagicMock()
        emitted = producer.run_stream()
        assert emitted == 0

    def test_honors_limit(self):
        client = MagicMock()
        client.primary_file.return_value.as_of_date = datetime(2026, 6, 30, tzinfo=timezone.utc)
        rows = [{"locationid": str(i), "program": "7a", "grossapproval": str(i * 1000)}
                for i in range(10)]
        client.loan_rows.return_value = iter([rows])

        geo = _mock_geocoder()
        crosswalk = MagicMock()
        crosswalk.city_for_point.return_value = "nyc"

        producer = _producer(client=client, geocoder=geo, crosswalk=crosswalk)
        producer.producer = MagicMock()

        emitted = producer.run_stream(limit=3)
        assert emitted == 3


# --------------------------------------------------------------------------- #
# SbaLoanEvent model                                                           #
# --------------------------------------------------------------------------- #

class TestSbaLoanEventModel:
    def test_minimal_event(self):
        event = SbaLoanEvent(program="7a", location_id="100")
        assert event.city_id == "national"
        assert event.fixed_asset is False

    def test_504_defaults_fixed_asset_true_via_producer(self):
        """fixed_asset is set by the producer based on program, not by the model default."""
        event = SbaLoanEvent(program="504", location_id="100", fixed_asset=True)
        assert event.fixed_asset is True

    def test_validation_rejects_bad_program(self):
        with pytest.raises(ValueError, match="program must be one of"):
            SbaLoanEvent(program="bad", location_id="100")

    def test_ingested_at_is_set(self):
        event = SbaLoanEvent(program="7a", location_id="100")
        assert event.ingested_at is not None

    def test_negative_gross_approval_rejected(self):
        with pytest.raises(ValueError, match="gross_approval"):
            SbaLoanEvent(program="7a", location_id="100", gross_approval=-1.0)


# --------------------------------------------------------------------------- #
# edge cases and invariants                                                    #
# --------------------------------------------------------------------------- #

class TestEdgeCases:
    def test_column_name_variants(self):
        geo = _mock_geocoder()
        crosswalk = MagicMock()
        crosswalk.city_for_point.return_value = "la"
        producer = _producer(geocoder=geo, crosswalk=crosswalk)
        row = {
            "location_id": "999",
            "programtype": "504",
            "borrname": "Widget Co",
            "borrower_street": "99 Harbor Blvd",
            "borrower_city": "Los Angeles",
            "borrower_state": "CA",
            "borrower_zip": "90001",
            "gross_amount": "999999",
            "loanstatus": "CHGOFF",
        }
        event = producer.build_event(row)
        assert event is not None
        assert event.location_id == "999"
        assert event.program == "504"
        assert event.borrower_name == "Widget Co"
        assert event.gross_approval == 999999.0
        assert event.status == "chgoff"

    def test_truncated_street_preserved(self):
        producer = _producer()
        event = producer.build_event(_make_row(
            borrstreet="123 Main St......................."
        ))
        assert event.borrower_street == "123 Main St......................."

    def test_nullable_float_fields(self):
        event = SbaLoanEvent(program="7a", location_id="100")
        assert event.gross_approval is None
        assert event.sba_guaranteed_approval is None

    def test_h3_is_none_when_no_coords(self):
        event = SbaLoanEvent(program="7a", location_id="100")
        assert event.h3_res7 is None
        assert event.h3_res8 is None
        assert event.h3_res9 is None
