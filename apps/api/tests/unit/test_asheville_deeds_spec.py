"""Unit tests for the US-399 Buncombe County property roll → Asheville DEEDS.

The spec dict must construct as ``DatasetSpec`` with zero massaging, the field
map must expose the expected canonical keys, and the price-reconstruction /
arm's-length helpers must behave correctly.
"""

import pytest

from src.producers import field_maps_asheville_deeds as maps
from src.producers.asheville_deeds_spec import ASHEVILLE_DEEDS_SPEC
from src.spatial.city_registry import DatasetSpec


class TestSpecShape:
    def test_spec_constructs_as_dataset_spec(self):
        assert DatasetSpec(**ASHEVILLE_DEEDS_SPEC) is not None

    def test_spec_is_snapshot(self):
        assert ASHEVILLE_DEEDS_SPEC["ingestion_mode"] == "snapshot"

    def test_spec_has_deed_date_watermark(self):
        assert ASHEVILLE_DEEDS_SPEC["watermark_col"] == "DeedDate"
        assert ASHEVILLE_DEEDS_SPEC["watermark_type"] == "text"
        assert ASHEVILLE_DEEDS_SPEC["watermark_format"] == "%Y%m%d"

    def test_spec_is_arcgis_platform(self):
        assert ASHEVILLE_DEEDS_SPEC["platform"] == "arcgis"
        assert ASHEVILLE_DEEDS_SPEC["oid_field"] == "objectid"

    def test_spec_is_deeds_topic(self):
        assert ASHEVILLE_DEEDS_SPEC["producer_key"] == "deeds"
        assert ASHEVILLE_DEEDS_SPEC["topic"] is not None

    def test_spec_endpoint_is_buncombe_gis(self):
        assert "buncombecounty" in ASHEVILLE_DEEDS_SPEC["endpoint"]
        assert "FeatureServer/1" in ASHEVILLE_DEEDS_SPEC["endpoint"]


class TestFieldMap:
    def test_field_map_has_deed_canonical_keys(self):
        expected = {
            "doc_id", "bbl", "document_amount", "recorded_date",
            "party1_grantor", "party2_grantee", "doc_type", "borough",
        }
        assert set(maps.ASHEVILLE_DEEDS_FIELD_MAP) == expected

    def test_doc_id_is_pin(self):
        assert "PIN" in maps.ASHEVILLE_DEEDS_FIELD_MAP["doc_id"]

    def test_bbl_is_pin(self):
        assert maps.ASHEVILLE_DEEDS_FIELD_MAP["bbl"] == ["PIN"]

    def test_document_amount_is_stamps(self):
        assert maps.ASHEVILLE_DEEDS_FIELD_MAP["document_amount"] == ["Stamps"]

    def test_recorded_date_is_deed_date(self):
        assert maps.ASHEVILLE_DEEDS_FIELD_MAP["recorded_date"] == ["DeedDate"]

    def test_doc_type_is_instrument(self):
        assert "Instrument" in maps.ASHEVILLE_DEEDS_FIELD_MAP["doc_type"]

    def test_party_maps_to_owner(self):
        assert "Owner" in maps.ASHEVILLE_DEEDS_FIELD_MAP["party1_grantor"]
        assert "Owner" in maps.ASHEVILLE_DEEDS_FIELD_MAP["party2_grantee"]

    def test_borough_is_county(self):
        assert "County" in maps.ASHEVILLE_DEEDS_FIELD_MAP["borough"]
        assert "City" in maps.ASHEVILLE_DEEDS_FIELD_MAP["borough"]

    def test_field_maps_cover_the_ticket_registry(self):
        assert set(maps.FIELD_MAPS) == {"asheville_deeds"}


class TestPriceReconstruction:
    def test_reconstruct_price_zero_stamps(self):
        assert maps.reconstruct_price(0.0) == 0.0
        assert maps.reconstruct_price(None) == 0.0
        assert maps.reconstruct_price(-1.0) == 0.0

    def test_reconstruct_price_typical(self):
        # $670 stamps → $335,000
        assert maps.reconstruct_price(670.0) == 335000.0

    def test_reconstruct_price_small_sale(self):
        # $1 stamp → $500 (overstates sub-$500 sales)
        assert maps.reconstruct_price(1.0) == 500.0

    def test_reconstruct_price_large_sale(self):
        assert maps.reconstruct_price(2000.0) == 1_000_000.0


class TestArmsLength:
    @pytest.mark.parametrize("inst", ["WDT", "SWD", "TR", "EXD", "CWD", "QD", "TD"])
    def test_arms_length_instruments(self, inst):
        assert maps.is_arms_length(inst, "") is True

    @pytest.mark.parametrize("inst", ["ADJ", "CA", "DR", "GC", "GV", "PL", "UX", "VE"])
    def test_non_arms_instruments(self, inst):
        assert maps.is_arms_length(inst, "") is False

    @pytest.mark.parametrize("reason", ["AL", "ATT", "BS", "CO", "CV", "ES", "FD", "FT", "GC", "GV", "LO", "NA", "OT", "SP", "TF", "TX", "VC"])
    def test_non_arms_reasons(self, reason):
        assert maps.is_arms_length("WDT", reason) is False

    def test_missing_values_pass_through(self):
        assert maps.is_arms_length(None, None) is True
        assert maps.is_arms_length("", "") is True

    def test_unknown_instrument_passes_as_arms_length(self):
        assert maps.is_arms_length("UNKNOWN", "") is True