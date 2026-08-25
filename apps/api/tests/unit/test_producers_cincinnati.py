"""Contract tests for the Cincinnati registration: Socrata three-feeds + CSV deeds (US-126)."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.producers.csv_client import CSVClient, _row_matches
from src.spatial.cities.cincinnati import (
    CINCINNATI_DIVISION_BBOXES,
    CINCINNATI_DIVISIONS,
    CINCINNATI_METRO_BBOX,
    CINCINNATI_SUBMARKETS,
    is_in_cincinnati_metro,
)
from src.spatial.city_registry import CityId, FeedType


def test_cincinnati_geometry_is_self_consistent():
    assert is_in_cincinnati_metro(39.1031, -84.5120)
    assert not is_in_cincinnati_metro(41.8781, -87.6298)
    assert not is_in_cincinnati_metro(None, None)
    for name, bbox in CINCINNATI_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= CINCINNATI_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= CINCINNATI_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= CINCINNATI_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= CINCINNATI_METRO_BBOX["max_lng"], name
    claimed = [name for division in CINCINNATI_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(CINCINNATI_SUBMARKETS)
    assert {meta.city_id for meta in CINCINNATI_SUBMARKETS.values()} == {"cincinnati"}


def test_cincinnati_registers_four_verified_feeds():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.CINCINNATI
    assert normalize_city("cinci") is city
    assert REGISTRY[city].job_suffix == "cinci"
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
        FeedType.SLA,
        FeedType.DEEDS,
    }
    assert REGISTRY[city].datasets[FeedType.PERMITS].watermark_col == "issueddate"
    assert REGISTRY[city].datasets[FeedType.COMPLAINTS_311].watermark_col == "date_time_received"
    assert REGISTRY[city].datasets[FeedType.SLA].watermark_col == "entered_date"
    spec = get_dataset(city, FeedType.DEEDS)
    assert spec.platform == "csv"
    assert spec.watermark_col == "SaleDate"
    assert spec.id_keys == ["conveyancenumber", "propertynumber"]


@pytest.mark.parametrize(
    ("feed", "endpoint", "watermark"),
    [
        (FeedType.PERMITS, "uhjb-xac9", "issueddate"),
        (FeedType.COMPLAINTS_311, "gcej-gmiw", "date_time_received"),
        (FeedType.SLA, "ehdi-ajku", "entered_date"),
        (FeedType.DEEDS, "transfer_dailysales_new.csv", "SaleDate"),
    ],
)
def test_cincinnati_specs_pin_researched_sources(feed, endpoint, watermark):
    from src.spatial.city_registry import REGISTRY

    spec = REGISTRY[CityId.CINCINNATI].datasets[feed]
    assert endpoint in spec.endpoint
    assert spec.watermark_col == watermark


def test_cincinnati_deeds_spec_pins_field_map_and_filters():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.CINCINNATI, FeedType.DEEDS)
    assert spec.topic == "raw.municipal.deeds"
    assert spec.extra["ingestion_mode"] == "snapshot"
    assert spec.extra["where"] == "valid = 'Y'"
    assert spec.extra["needs_geocode"] is True
    assert spec.extra["geocode_context"] == "Hamilton County, OH"
    assert spec.extra["field_map"]["document_amount"] == ["saleamount"]
    assert spec.extra["field_map"]["doc_id"] == ["conveyancenumber"]


# Live row captured 2026-08-25 from transfer_dailysales_new.csv, headers
# lowercased exactly as CSVClient normalizes them.
CINCINNATI_SALE_ROW = {
    "book": "571",
    "plat": "0003",
    "parcel": "0150",
    "parcelid": "00",
    "taxdistrict": "222",
    "ownername1": "GUTLACHT HOLDINGS LLC",
    "ownername2": "",
    "land100": "2000",
    "impr100": "0",
    "propertyclass": "500",
    "house#": "153",
    "streetname": "SECOND",
    "streetsuffix": "ST",
    "locationzipcode": "45001-0000",
    "monthsale": "8",
    "daysale": "13",
    "yearsale": "2026",
    "numberpropertiesinsale": "2",
    "saleamount": "27000",
    "valid": "Y",
    "conveyancenumber": "415593",
    "deedtype": "WD",
    "appraisalarea": "ADDYSTON",
    "previousowner": "DAVIS KRISTEN",
    "propertynumber": "571-0003-0150-00",
}


@pytest.fixture
def deeds():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        return DeedsACRISProducer()


def test_cincinnati_deed_row_parses_via_field_map(deeds):
    ev = deeds.parse_socrata_row(dict(CINCINNATI_SALE_ROW), city_id="cincinnati")
    assert ev is not None
    assert ev.city_id == "cincinnati"
    assert ev.doc_id == "415593"
    assert ev.bbl == "571-0003-0150-00"
    assert ev.document_amount == 27000.0
    assert ev.party1_grantor == "DAVIS KRISTEN"
    assert ev.party2_grantee == "GUTLACHT HOLDINGS LLC"
    assert ev.doc_type == "WD"
    assert ev.source_neighborhood == "ADDYSTON"
    assert ev.recorded_date == datetime.fromisoformat("2026-08-13")


def test_cincinnati_deed_is_address_only_null_coords_h3(deeds):
    ev = deeds.parse_socrata_row(dict(CINCINNATI_SALE_ROW), city_id="cincinnati")
    assert ev.latitude is None
    assert ev.longitude is None
    assert ev.h3_res7 is None
    assert ev.h3_res8 is None
    assert ev.h3_res9 is None


def test_cincinnati_deed_row_autodetects_without_city_id(deeds):
    ev = deeds.parse_socrata_row(dict(CINCINNATI_SALE_ROW))
    assert ev is not None
    assert ev.city_id == "cincinnati"


def test_cincinnati_non_arms_length_row_still_parses_parser_never_filters(deeds):
    """Valid='N' rows are filtered by the registry where clause, never dropped
    silently in the parser (Denver $0-transfer precedent: filtering is a
    registry/scheduler concern)."""
    row = dict(CINCINNATI_SALE_ROW)
    row["valid"] = "N"
    ev = deeds.parse_socrata_row(row, city_id="cincinnati")
    assert ev is not None
    assert ev.document_amount == 27000.0


def test_row_matches_strips_wrapping_parentheses():
    """The scheduler wraps base_where in parens before joining; _row_matches
    must see through a bare predicate like '(valid = 'Y')'."""
    row = {"valid": "Y", "saleamount": "27000"}
    assert _row_matches("(valid = 'Y')", row) is True
    assert _row_matches("(valid = 'N')", row) is False
    assert _row_matches("valid = 'Y'", row) is True
    assert _row_matches(None, row) is True


CINCINNATI_CSV_SAMPLE = (
    '"ConveyanceNumber","PropertyNumber","SaleAmount","Valid","PreviousOwner",'
    '"OwnerName1","MonthSale","DaySale","YearSale","DeedType","AppraisalArea"\n'
    '"415593","571-0003-0150-00","27000","Y","DAVIS KRISTEN",'
    '"GUTLACHT HOLDINGS LLC","8","13","2026","WD","ADDYSTON"\n'
    '"415594","571-0003-0151-00","27000","N","DAVIS KRISTEN",'
    '"GUTLACHT HOLDINGS LLC","8","13","2026","WD","ADDYSTON"\n'
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


def test_csv_client_lowercases_headers_and_applies_parenthesized_valid_filter():
    client = CSVClient(http_client=_FakeHTTP(CINCINNATI_CSV_SAMPLE))
    batches = list(
        client.paginate(
            "https://www.hamiltoncountyauditor.org/download/transfer_dailysales_new.csv",
            where_clause="(valid = 'Y')",
        )
    )
    rows = [r for batch in batches for r in batch]
    assert len(rows) == 1
    assert rows[0]["conveyancenumber"] == "415593"
    assert rows[0]["valid"] == "Y"
