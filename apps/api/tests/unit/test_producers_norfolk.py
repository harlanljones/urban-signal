"""Unit tests for the Norfolk registration and its producer wiring.

Norfolk is a partial city by design: the 2026-08 re-probe registered exactly
TWO Socrata feeds on data.norfolk.gov — building permits (fahm-yuh4) and
property deeds/sales (qva7-tzrf). The 311 feed (nbyu-xjez) locates incidents
by bare address string and the business-license feed (dpi6-sct5) has no
geometry at all; both are deferred pending address-geocoding capability.

FY rotation caveat: Norfolk publishes sales as annual fiscal-year datasets
(FY23...FY27); the registry pins the current-year file and its dataset ID must
rotate every July 1 — see the ingestion runbook.

Known quirk: the permits feed contains future-dated scheduled filings
(issue/application dates observed out to 2027-01); parsers accept them, but
analytics should filter issuance_date <= now().

Registration tests are RED until the spine adds CityId.NORFOLK to the
registry (orchestrator applies after this leaf lands) — expected.
"""

from unittest.mock import patch

import pytest

from src.spatial.cities.norfolk import (
    NORFOLK_DIVISION_BBOXES,
    NORFOLK_DIVISIONS,
    NORFOLK_METRO_BBOX,
    NORFOLK_SUBMARKETS,
    is_in_norfolk_metro,
)
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    get_job_name,
    normalize_city,
)


class TestNorfolkRegistration:
    def test_registered(self):
        assert CityId.NORFOLK in REGISTRY

    @pytest.mark.parametrize("alias", ["norfolk", "norfolk_va"])
    def test_aliases_resolve(self, alias):
        assert normalize_city(alias) is CityId.NORFOLK

    def test_registration_shape(self):
        reg = REGISTRY[CityId.NORFOLK]
        assert reg.state == "VA"
        assert reg.job_suffix == "norfolk"
        assert reg.submarkets is NORFOLK_SUBMARKETS
        assert reg.divisions is NORFOLK_DIVISIONS
        assert len(reg.divisions) == 5

    def test_center_inside_metro_bbox(self):
        reg = REGISTRY[CityId.NORFOLK]
        assert is_in_norfolk_metro(reg.center["lat"], reg.center["lng"])

    def test_is_in_norfolk_metro_rejects_missing_coordinates(self):
        assert is_in_norfolk_metro(None, None) is False

    def test_is_in_norfolk_metro_rejects_other_cities(self):
        assert is_in_norfolk_metro(47.6062, -122.3321) is False   # Seattle
        assert is_in_norfolk_metro(36.8470, -76.3570) is False    # Portsmouth edge west of box

    def test_live_sample_coordinates_are_contained(self):
        """Newest permit row (B26-01819) and the sales parcel band must sit inside."""
        assert is_in_norfolk_metro(36.9675, -76.28833)
        assert is_in_norfolk_metro(36.85119813, -76.19301345)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in NORFOLK_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= NORFOLK_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= NORFOLK_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= NORFOLK_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= NORFOLK_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in NORFOLK_SUBMARKETS.items():
            bbox = NORFOLK_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in NORFOLK_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(NORFOLK_SUBMARKETS)

    def test_submarkets_carry_the_norfolk_city_id(self):
        assert {m.city_id for m in NORFOLK_SUBMARKETS.values()} == {"norfolk"}

    def test_job_names_are_namespaced(self):
        assert get_job_name(FeedType.PERMITS, CityId.NORFOLK) == "permits_norfolk"


class TestPartialFeedRegistration:
    """Wave G2 (US-75) outcome: 311 registered behind the geocoder; SLA
    evaluated and reverted under G8' (placeholder-address share)."""

    def test_registered_feed_set(self):
        assert set(REGISTRY[CityId.NORFOLK].datasets) == {
            FeedType.PERMITS,
            FeedType.DEEDS,
            FeedType.COMPLAINTS_311,
        }

    def test_watermarks_match_published_schemas(self):
        assert get_dataset(CityId.NORFOLK, FeedType.PERMITS).watermark_col == "issue_date"
        assert get_dataset(CityId.NORFOLK, FeedType.DEEDS).watermark_col == "transfer_date"
        assert get_dataset(CityId.NORFOLK, FeedType.COMPLAINTS_311).watermark_col == "creation_date"

    def test_geocoded_feed_declares_its_address_contract(self):
        extra = get_dataset(CityId.NORFOLK, FeedType.COMPLAINTS_311).extra
        assert extra["needs_geocode"] is True
        assert extra["geocode_context"] == "Norfolk, VA"
        assert extra["expected_cadence_days"] >= 1

    def test_sla_reverted_under_g8_prime(self):
        """US-75 finding: ~34% of newest dpi6-sct5 rows carry the literal
        placeholder 'NO NORFOLK ADDRESS REQUIRED' (special-event licenses),
        so the feed resolves ~65% of coordinates — far above the 5%
        null-H3 ceiling. Reverted, not documented-and-registered."""
        with pytest.raises(KeyError):
            get_dataset(CityId.NORFOLK, FeedType.SLA)


class TestNorfolkRowParsing:
    """Fixtures captured live from data.norfolk.gov on 2026-08-23."""

    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @pytest.fixture
    def permit_row(self):
        # Live newest-by-issue_date row from fahm-yuh4 (2026-08-23 capture).
        return {
            "permit_number": "B26-01819",
            "address": "6160 KEMPSVILLE CIRCLE",
            "gpin": "1457778616",
            "tax_account": "24977650",
            "latitude": "36.85119813",
            "longitude": "-76.19301345",
            "type": "Building",
            "use_class": "Commercial",
            "work_type": "Alteration/Repair - Renovate Existing Square Footage",
            "status": "Issued",
            "application_date": "2026-06-23T00:00:00.000",
            "issue_date": "2026-12-24T00:00:00.000",
            "total_fee": "1378.98",
            "project_cost": "310000.0",
        }

    @pytest.fixture
    def deed_row(self):
        # Live newest-by-transfer_date row from qva7-tzrf (2026-08-23 capture).
        return {
            "lrsn": "1413",
            "parcel_id": "1003200",
            "extension": "R01",
            "gpin": "1437889293",
            "property_street_number": "2703",
            "property_street_name": "Beachmont",
            "property_street_type": "AV",
            "property_city": "Norfolk",
            "transfer_date": "2026-08-19T00:00:00.000",
            "grantor": "Scott, Karen F",
            "grantee": "Alford, Chase & Qunell, Rachael",
            "consideration": "400000",
            "document_number": "260016116",
        }

    # -- PERMITS -----------------------------------------------------------

    def test_permit_parses_today(self, permits, permit_row):
        assert permits.parse_socrata_row(permit_row, city_id="norfolk") is not None

    def test_permit_id_comes_from_permit_number(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="norfolk")
        assert ev.job_id == "B26-01819"

    def test_permit_reads_direct_latitude_longitude_strings(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="norfolk")
        assert ev.latitude == pytest.approx(36.85119813)
        assert ev.longitude == pytest.approx(-76.19301345)

    def test_permit_cost_parses_via_total_fee_today(self, permits, permit_row):
        """The cost chain lacks project_cost but DOES read total_fee, which the
        feed publishes — so estimated_cost parses today (>0). Once the field_map
        adds project_cost it will carry the real project value instead."""
        ev = permits.parse_socrata_row(permit_row, city_id="norfolk")
        assert ev.estimated_cost > 0

    def test_permit_issuance_date_maps(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="norfolk")
        assert str(ev.issuance_date).startswith("2026-12-24")

    def test_permit_filing_date_comes_from_application_date(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="norfolk")
        assert str(ev.filing_date).startswith("2026-06-23")

    def test_permit_classifies_new_work_as_nb(self, permits, permit_row):
        from src.schemas.models import JobType

        ev = permits.parse_socrata_row(permit_row, city_id="norfolk")
        assert ev.job_type == JobType.A2

    def test_permit_resolves_to_a_division(self, permits, permit_row):
        ev = permits.parse_socrata_row(permit_row, city_id="norfolk")
        assert ev.borough is not None

    # -- DEEDS -------------------------------------------------------------

    def test_deed_parses_today(self, deeds, deed_row):
        assert deeds.parse_socrata_row(deed_row, city_id="norfolk") is not None

    def test_deed_doc_id_comes_from_document_number(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="norfolk")
        assert ev.doc_id == "260016116"

    def test_deed_parties_and_consideration_map(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="norfolk")
        assert ev.party1_grantor == "Scott, Karen F"
        assert ev.party2_grantee == "Alford, Chase & Qunell, Rachael"
        assert ev.document_amount == 400000.0

    def test_deed_recorded_date_reads_transfer_date(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="norfolk")
        assert str(ev.recorded_date).startswith("2026-08-19")

    def test_deed_without_geometry_yields_null_lat_lng_and_h3(self, deeds, deed_row):
        """The sales feed carries no coordinates — like Chicago's geocode-less
        rows, the deeds producer tolerates this and leaves H3 cells null."""
        ev = deeds.parse_socrata_row(deed_row, city_id="norfolk")
        assert ev.latitude is None
        assert ev.longitude is None
        assert ev.h3_res7 is None

    def test_deed_bbl_comes_from_gpin_or_parcel_id(self, deeds, deed_row):
        ev = deeds.parse_socrata_row(deed_row, city_id="norfolk")
        assert ev.bbl == "1437889293"


class TestGeocodedFeedParsing:
    """US-75: address-string rows resolve coordinates at parse time for specs
    declaring needs_geocode (ADR 0004); everyone else keeps legacy behavior."""

    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_norfolk_311_address_row_geocodes_at_parse(self, complaints, monkeypatch):

        calls = []

        def fake_resolve(city_id, feed_value, address, context=None):
            calls.append((city_id, feed_value, address, context))
            return (36.8508, -76.2859)

        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared", fake_resolve
        )
        row = {
            "service_request_number": "NR-1",
            "service_request_type": "Missed Trash Pickup",
            "service_request_category": "Waste Services",
            "status": "OPEN",
            "creation_date": "2026-08-21T22:39:12.000",
            "location": "8020 MEADOW CREEK ROAD, NORFOLK, VA",
        }
        event = complaints.parse_socrata_row(row, city_id="norfolk")
        assert event is not None
        assert event.latitude == 36.8508 and event.longitude == -76.2859
        assert event.incident_id == "NR-1"
        assert event.h3_res7 is not None  # real coords index into H3
        # The hook receives the registry context suffix decision internally;
        # the producer passes the raw address string.
        assert calls == [("norfolk", "311", "8020 MEADOW CREEK ROAD, NORFOLK, VA", None)]

    def test_undeclared_city_still_drops_coordinate_less_rows(self, complaints, monkeypatch):
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        row = {
            "unique_key": "NYC-1",
            "complaint_type": "Noise",
            "created_date": "2026-08-21T10:00:00.000",
            "incident_address": "1 Static Ave",
        }
        assert complaints.parse_socrata_row(row, city_id="nyc") is None

    def test_geocode_failure_drops_declared_rows(self, complaints, monkeypatch):
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        row = {
            "service_request_number": "NR-2",
            "creation_date": "2026-08-21T10:00:00.000",
            "location": "INTERSECTION OF UNKNOWN AND VOID",
        }
        assert complaints.parse_socrata_row(row, city_id="norfolk") is None


NORFOLK_SLA_CANDIDATE_MAP = {
    "license_id": ["trading_as_name", "primary_owner"],
    "premises_name": ["trading_as_name"],
    "license_type": ["naics"],
    "effective_date": ["business_opened_date"],
    "address_street": ["location_address"],
}


class TestNorfolkSlaParsing:
    """Producer-capability pins for the reverted dpi6-sct5 registration: with
    the candidate field map supplied (and coordinates resolved), rows parse;
    placeholder-address rows fall through to null-coord events."""

    @pytest.fixture
    def sla(self, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city_value, feed: NORFOLK_SLA_CANDIDATE_MAP
            if getattr(feed, "value", feed) == "sla"
            else {},
        )
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_norfolk_license_row_geocodes_and_maps(self, sla, monkeypatch):

        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (
                (36.87, -76.29)
                if address == "3549 SHARPLEY AVE 23513"
                else None
            ),
        )
        row = {
            "trading_as_name": "MEEKINS FIELD SERVICES",
            "location_address": "3549 SHARPLEY AVE 23513",
            "business_opened_date": "2026-08-24T00:00:00.000",
            "naics": "561790",
            "primary_owner": "J MEEKINS",
        }
        event = sla.parse_socrata_row(row, city_id="norfolk")
        assert event is not None
        assert event.latitude == 36.87 and event.longitude == -76.29
        assert event.effective_date is not None and event.effective_date.year == 2026
        assert event.h3_res9 is not None

    def test_placeholder_address_falls_through_to_null_coord_event(self, sla, monkeypatch):
        """'NO NORFOLK ADDRESS REQUIRED' rows cannot geocode; the SLA producer's
        coordinate-less tolerance (DC precedent) keeps them as null-H3 events."""
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        row = {
            "trading_as_name": "SUNDAE SCOOP (SPECIAL EVENT)",
            "location_address": "NO NORFOLK ADDRESS REQUIRED 99999",
            "business_opened_date": "2026-08-24T00:00:00.000",
        }
        event = sla.parse_socrata_row(row, city_id="norfolk")
        assert event is not None
        assert event.latitude is None and event.h3_res7 is None
