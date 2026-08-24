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
    ALIASES,
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
    """Norfolk registers two feeds; 311 and licenses are deferred by design."""

    def test_only_permits_and_deeds_are_registered(self):
        assert set(REGISTRY[CityId.NORFOLK].datasets) == {
            FeedType.PERMITS,
            FeedType.DEEDS,
        }

    def test_watermarks_match_published_schemas(self):
        assert get_dataset(CityId.NORFOLK, FeedType.PERMITS).watermark_col == "issue_date"
        assert get_dataset(CityId.NORFOLK, FeedType.DEEDS).watermark_col == "transfer_date"

    @pytest.mark.parametrize("feed", [FeedType.COMPLAINTS_311, FeedType.SLA])
    def test_deferred_feeds_raise_a_readable_error(self, feed):
        with pytest.raises(KeyError) as exc:
            get_dataset(CityId.NORFOLK, feed)
        message = str(exc.value)
        assert "norfolk" in message
        assert feed.value in message


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
