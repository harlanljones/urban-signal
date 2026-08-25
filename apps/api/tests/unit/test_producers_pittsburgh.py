"""Contract tests for Pittsburgh, PA (CKAN WPRDC PLI Permits, US-89/129)."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.spatial.cities.pittsburgh import (
    PITTSBURGH_DIVISION_BBOXES,
    PITTSBURGH_DIVISIONS,
    PITTSBURGH_METRO_BBOX,
    PITTSBURGH_SUBMARKETS,
    is_in_pittsburgh_metro,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType

# Recommended DatasetSpec.extra["field_map"] for US-89. Every entry spells a
# WPRDC column the shared producer fallback chains cannot reach (the chains
# say `permit_number`/`issued_date`/`revised_cost`); latitude/longitude ride
# native lowercase keys the chains already read.
PITTSBURGH_FIELD_MAP = {
    "job_id": ["permit_id"],
    "issuance_date": ["issue_date"],
    "cost": ["total_project_value"],
    "address_street": ["address"],
    "status": ["status"],
    "job_type": ["permit_type", "work_type"],
    "zipcode": ["zip_code"],
}

# DatasetSpec.extra["field_map"] for US-129 (Pittsburgh deeds). The WPRDC
# property-sales schema is all-uppercase; every entry spells a column the shared
# deeds chains cannot reach bare (`sale_price`/`document_number`/`recording_date`
# don't exist). address is FULL_ADDRESS; there is no latitude/longitude on the
# wire (address-only / PARID-only).
PITTSBURGH_DEEDS_FIELD_MAP = {
    "doc_id": ["PARID", "DEEDBOOK", "DEEDPAGE"],
    "bbl": ["PARID"],
    "document_amount": ["PRICE"],
    "recorded_date": ["RECORDDATE"],
    "doc_type": ["INSTRTYP"],
    "borough": ["MUNIDESC", "PROPERTYCITY"],
    "incident_address": ["FULL_ADDRESS"],
}

# DatasetSpec.extra["field_map"] for US-132 (Pittsburgh 311, WPRDC "Pittsburgh
# 311 Data"). The schema is lowercase with `subject` as the category and
# `latitude`/`longitude` as TEXT (5-dec EXACT / 2-dec APPROXIMATE — the 311
# producer casts to float). `unique_id` is the stable id; `case_number` is the
# shared public case-id fallback. Borough maps neighborhood/council_district/ward.
PITTSBURGH_311_FIELD_MAP = {
    "incident_id": ["unique_id", "case_number"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
    "created_date": ["created_date_utc"],
    "closed_date": ["closed_date_utc"],
    "complaint_type": ["subject"],
    "incident_address": ["street"],
    "borough": ["neighborhood", "council_district", "ward"],
}


def test_pittsburgh_geometry_is_self_consistent():
    assert is_in_pittsburgh_metro(40.4417, -80.0000)  # Downtown center
    assert is_in_pittsburgh_metro(40.4486022823, -79.9903585214)  # observed live-row
    assert is_in_pittsburgh_metro(40.466871193, -79.9806746886)  # observed live-row
    assert not is_in_pittsburgh_metro(40.5697, -79.7549)  # New Kensington, NE of the city
    assert not is_in_pittsburgh_metro(None, None)
    for name, bbox in PITTSBURGH_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= PITTSBURGH_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= PITTSBURGH_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= PITTSBURGH_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= PITTSBURGH_METRO_BBOX["max_lng"], name
    claimed = [name for division in PITTSBURGH_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(PITTSBURGH_SUBMARKETS)
    assert {meta.city_id for meta in PITTSBURGH_SUBMARKETS.values()} == {"pittsburgh"}


def test_pittsburgh_registers_ckan_permits_deeds_and_311():
    from src.spatial.city_registry import get_dataset, normalize_city

    city = CityId.PITTSBURGH
    assert normalize_city("pittsburgh") is city
    assert normalize_city("pgh") is city
    assert REGISTRY[city].job_suffix == "pgh"
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.DEEDS,
        FeedType.COMPLAINTS_311,
    }

    permits = REGISTRY[city].datasets[FeedType.PERMITS]
    assert permits.platform == "ckan"
    assert permits.watermark_col == "issue_date"
    assert permits.interval_seconds == 300.0
    assert permits.producer_key == "permits"
    assert permits.extra["expected_cadence_days"] == 7
    assert permits.extra["field_map"] == PITTSBURGH_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.SLA)


def test_pittsburgh_deeds_spec_pins_ckan_source_and_field_map():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.PITTSBURGH, FeedType.DEEDS)
    assert spec.platform == "ckan"
    assert spec.watermark_col == "RECORDDATE"
    assert spec.topic == "raw.municipal.deeds"
    assert spec.producer_key == "deeds"
    assert spec.id_keys == ["PARID", "RECORDDATE", "SALEDATE", "DEEDBOOK", "DEEDPAGE"]
    assert spec.extra["expected_cadence_days"] == 7
    assert spec.extra["field_map"] == PITTSBURGH_DEEDS_FIELD_MAP


PGH_PERMIT_ROW = {
    # Live newest-rows sample via the WPRDC datastore on 2026-08-24, exactly
    # as CkanClient delivers it (flat JSON record; native lat/lng keys).
    "permit_id": "EP-2026-04291",
    "permit_type": "ELECTRICAL",
    "owner_name": None,
    "work_description": "MAIN SERVICE REPLACEMENT",
    "work_type": "Existing (alteration/addition)",
    "commercial_or_residential": "Residential",
    "total_project_value": 148968,
    "issue_date": "2026-08-21",
    "parcel_num": "0028N00146000000",
    "address": "1447 SMALLMAN ST, Pittsburgh, PA 15222-",
    "latitude": 40.4486022823,
    "longitude": -79.9903585214,
    "council_district": "6",
    "neighborhood": "Bluff",
    "ward": "19",
    "zip_code": "15222",
    "status": "Issued",
}


class TestPittsburghPermitParsing:
    """Parse pins against the shared DOBPermitsProducer (US-89)."""

    @pytest.fixture
    def producer(self):
        with (
            patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
            patch(
                "src.producers.field_maps.resolve_field_map",
                return_value=PITTSBURGH_FIELD_MAP,
            ),
        ):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            yield DOBPermitsProducer()

    def test_live_row_parses_wprdc_schema(self, producer):
        event = producer.parse_socrata_row(dict(PGH_PERMIT_ROW), city_id="pittsburgh")
        assert event is not None
        assert event.city_id == "pittsburgh"
        assert event.job_id == "EP-2026-04291"
        assert event.status == "Issued"
        assert event.estimated_cost == pytest.approx(148968)
        assert event.zipcode == "15222"
        assert event.issuance_date is not None
        assert (event.issuance_date.year, event.issuance_date.month, event.issuance_date.day) == (
            2026,
            8,
            21,
        )
        assert event.latitude == pytest.approx(40.4486022823)
        assert event.longitude == pytest.approx(-79.9903585214)

    def test_missing_permit_id_returns_none(self, producer):
        row = dict(PGH_PERMIT_ROW)
        row.pop("permit_id")
        assert producer.parse_socrata_row(row, city_id="pittsburgh") is None


# Live newest-rows sample via the WPRDC datastore on 2026-08-25, exactly as
# CkanClient delivers it (flat JSON record; original-case keys — note the schema
# is all-uppercase).
PGH_DEED_ROW = {
    "_id": 153124489,
    "PARID": "1010G00075000000",
    "FULL_ADDRESS": "0 HILL ST, SOUTH PARK, PA 15129",
    "PROPERTYHOUSENUM": "0",
    "PROPERTYADDRESSSTREET": "HILL",
    "PROPERTYADDRESSSUF": "ST",
    "PROPERTYCITY": "SOUTH PARK",
    "PROPERTYSTATE": "PA",
    "PROPERTYZIP": "15129",
    "MUNIDESC": "South Park  ",
    "RECORDDATE": "2022-07-06",
    "SALEDATE": "2022-06-21",
    "PRICE": 1,
    "DEEDBOOK": "18965",
    "DEEDPAGE": "534",
    "SALECODE": "H",
    "SALEDESC": "MULTI-PARCEL SALE",
    "INSTRTYP": "DE",
    "INSTRTYPDESC": "DEED",
}


class TestPittsburghDeedsParsing:
    """Parse rows against the shared DeedsACRISProducer (US-129)."""

    @pytest.fixture
    def producer(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            yield DeedsACRISProducer()

    def test_live_row_parses_via_field_map(self, producer):
        ev = producer.parse_socrata_row(dict(PGH_DEED_ROW), city_id="pittsburgh")
        assert ev is not None
        assert ev.city_id == "pittsburgh"
        assert ev.doc_id == "1010G00075000000"
        assert ev.bbl == "1010G00075000000"
        assert ev.document_amount == 1.0
        assert ev.doc_type == "DE"
        assert ev.source_neighborhood.strip() == "South Park"
        assert ev.recorded_date == datetime.fromisoformat("2022-07-06")

    def test_live_row_is_address_only_null_coords_h3(self, producer):
        ev = producer.parse_socrata_row(dict(PGH_DEED_ROW), city_id="pittsburgh")
        assert ev.latitude is None
        assert ev.longitude is None
        assert ev.h3_res7 is None
        assert ev.h3_res8 is None
        assert ev.h3_res9 is None

    def test_deed_row_autodetects_without_city_id(self, producer):
        ev = producer.parse_socrata_row(dict(PGH_DEED_ROW))
        assert ev is not None
        assert ev.city_id == "pittsburgh"

    def test_null_price_and_null_deedbook_still_parse(self, producer):
        """PRICE can be null/0/1 on non-market sales and DEEDBOOK may blank out;
        the amount chain falls through to 0.0 but the row still emits (a price
        is optional, the doc_id isn't)."""
        row = dict(PGH_DEED_ROW)
        row["PRICE"] = None
        row["DEEDBOOK"] = None
        ev = producer.parse_socrata_row(row, city_id="pittsburgh")
        assert ev is not None
        assert ev.document_amount == 0.0
        assert ev.doc_id == "1010G00075000000"


def test_pittsburgh_311_spec_pins_ckan_source_and_field_map():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.PITTSBURGH, FeedType.COMPLAINTS_311)
    assert spec.platform == "ckan"
    assert spec.endpoint == "ckan://data.wprdc.org/5202679a-d243-402e-b82a-63189995a942"
    assert spec.watermark_col == "created_date_utc"
    assert spec.id_keys == ["unique_id", "case_number"]
    assert spec.topic == "raw.municipal.311"
    assert spec.producer_key == "311"
    assert spec.interval_seconds == 180.0
    assert spec.extra["expected_cadence_days"] == 7
    assert spec.extra["field_map"] == PITTSBURGH_311_FIELD_MAP


def test_pittsburgh_311_field_map_resolves():
    from src.producers.field_maps import resolve_field_map

    assert resolve_field_map("pittsburgh", FeedType.COMPLAINTS_311) == PITTSBURGH_311_FIELD_MAP


# Live newest-rows sample via the WPRDC datastore on 2026-08-25, exactly as
# CkanClient delivers it (flat JSON record; lowercase keys, lat/lng as TEXT).
PGH_311_ROW = {
    "unique_id": "26-00090264-26",
    "case_number": "26-00090264",
    "subject": "Signal Repair",
    "subject_code": "SIGNALREP",
    "created_date_utc": "2026-08-25T17:47:36",
    "closed_date_utc": None,
    "status": "Open",
    "latitude": "40.44714",
    "longitude": "-79.89516",
    "geo_accuracy": "EXACT",
    "neighborhood": "Bloomfield",
    "council_district": "D8",
    "ward": "12",
    "street": "Liberty Ave",
    "city": "PITTSBURGH",
    "last_modified_date_utc": "2026-08-25T17:47:38",
}


class TestPittsburgh311Parsing:
    """Parse rows against the shared Complaints311Producer (US-132)."""

    @pytest.fixture
    def complaints(self):
        from src.producers.complaints_311_producer import Complaints311Producer

        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            yield Complaints311Producer()

    def test_live_row_parses_via_field_map(self, complaints):
        ev = complaints.parse_socrata_row(dict(PGH_311_ROW), city_id="pittsburgh")
        assert ev is not None
        assert ev.city_id == "pittsburgh"
        assert ev.incident_id == "26-00090264-26"
        assert ev.complaint_type == "Signal Repair"
        assert ev.status == "Open"
        assert ev.incident_address == "Liberty Ave"
        assert ev.source_neighborhood == "Bloomfield"

    def test_lat_lng_text_casts_to_float(self, complaints):
        ev = complaints.parse_socrata_row(dict(PGH_311_ROW), city_id="pittsburgh")
        assert ev is not None
        assert ev.latitude == pytest.approx(40.44714)
        assert ev.longitude == pytest.approx(-79.89516)

    def test_approx_lat_lng_text_casts_to_float(self, complaints):
        row = dict(
            PGH_311_ROW,
            latitude="40.44",
            longitude="-79.95",
            geo_accuracy="APPROXIMATE",
        )
        ev = complaints.parse_socrata_row(row, city_id="pittsburgh")
        assert ev is not None
        assert ev.latitude == pytest.approx(40.44)
        assert ev.longitude == pytest.approx(-79.95)

    def test_dates_and_watermark_parse(self, complaints):
        ev = complaints.parse_socrata_row(dict(PGH_311_ROW), city_id="pittsburgh")
        assert ev is not None
        assert ev.created_date is not None
        assert str(ev.created_date).startswith("2026-08-25")
        assert ev.closed_date is None

    def test_fixture_lands_inside_metro_bbox(self, complaints):
        ev = complaints.parse_socrata_row(dict(PGH_311_ROW), city_id="pittsburgh")
        assert ev is not None
        bbox = REGISTRY[CityId.PITTSBURGH].metro_bbox
        assert bbox["min_lat"] <= ev.latitude <= bbox["max_lat"]
        assert bbox["min_lng"] <= ev.longitude <= bbox["max_lng"]

    def test_legacy_null_coords_are_dropped(self, complaints):
        # Legacy 2015-2025 rows carry null lat/lng; Pittsburgh declares no
        # needs_geocode, so the producer's hard drop returns None.
        row = dict(PGH_311_ROW, latitude=None, longitude=None, geo_accuracy=None)
        assert complaints.parse_socrata_row(row, city_id="pittsburgh") is None