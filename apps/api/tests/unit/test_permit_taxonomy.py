"""Tests for the unified Bay Area permit-type taxonomy (US-441)."""

from unittest.mock import patch

import pytest

from src.features.permit_taxonomy import (
    NormalizedPermitType,
    is_trade_permit,
    names_new_building,
    normalize_permit_type,
)
from src.schemas.models import JobType

NEW = NormalizedPermitType.NEW_CONSTRUCTION
MEP = NormalizedPermitType.MECHANICAL_ELECTRICAL_PLUMBING
MAJOR = NormalizedPermitType.MAJOR_RENOVATION
MINOR = NormalizedPermitType.MINOR_ALTERATION


class TestKeywordNormalization:
    def test_new_construction(self):
        assert normalize_permit_type("New Construction - Single Family") == NormalizedPermitType.NEW_CONSTRUCTION
        assert normalize_permit_type("NB - New Building") == NormalizedPermitType.NEW_CONSTRUCTION

    def test_demolition_wins_over_alteration_keywords(self):
        # Oakland-style compound string: DEMOLITION must win even though
        # "ALTERATION" also appears.
        assert normalize_permit_type("DEMOLITION - PARTIAL (ALTERATION)") == NormalizedPermitType.DEMOLITION

    def test_change_of_use(self):
        assert normalize_permit_type("Change of Use / Occupancy") == NormalizedPermitType.CHANGE_OF_USE
        assert normalize_permit_type("Conversion to Residential") == NormalizedPermitType.CHANGE_OF_USE

    def test_mechanical_electrical_plumbing(self):
        assert normalize_permit_type("Electrical Only") == NormalizedPermitType.MECHANICAL_ELECTRICAL_PLUMBING
        assert normalize_permit_type("Plumbing - Repipe") == NormalizedPermitType.MECHANICAL_ELECTRICAL_PLUMBING
        assert normalize_permit_type("Rooftop Solar / PV Installation") == NormalizedPermitType.MECHANICAL_ELECTRICAL_PLUMBING

    def test_major_renovation(self):
        assert normalize_permit_type("Major Alteration - Addition") == NormalizedPermitType.MAJOR_RENOVATION
        assert normalize_permit_type("Tenant Improvement") == NormalizedPermitType.MAJOR_RENOVATION

    def test_minor_alteration(self):
        assert normalize_permit_type("Minor Alteration - Reroof") == NormalizedPermitType.MINOR_ALTERATION
        assert normalize_permit_type("Fence Permit") == NormalizedPermitType.MINOR_ALTERATION

    def test_case_insensitive(self):
        assert normalize_permit_type("new construction") == NormalizedPermitType.NEW_CONSTRUCTION


class TestJobTypeFallback:
    def test_unmatched_raw_string_falls_back_to_job_type(self):
        assert normalize_permit_type("Unrecognized Municipal Code XZ9", job_type=JobType.NB) == NormalizedPermitType.NEW_CONSTRUCTION
        assert normalize_permit_type(None, job_type=JobType.DM) == NormalizedPermitType.DEMOLITION
        assert normalize_permit_type("", job_type=JobType.A3) == NormalizedPermitType.MINOR_ALTERATION

    def test_job_type_value_string_accepted(self):
        assert normalize_permit_type(None, job_type="NB") == NormalizedPermitType.NEW_CONSTRUCTION

    def test_no_signal_defaults_to_minor_alteration(self):
        assert normalize_permit_type(None, None) == NormalizedPermitType.MINOR_ALTERATION
        assert normalize_permit_type("", "") == NormalizedPermitType.MINOR_ALTERATION

    def test_raw_string_keyword_wins_over_job_type(self):
        # A2 alone would fall back to MINOR_ALTERATION, but a raw string
        # naming demolition must win.
        assert normalize_permit_type("Demolition of accessory structure", job_type=JobType.A2) == NormalizedPermitType.DEMOLITION


class TestNewBuildingsNamedOtherWays:
    """Type names from the 2026-10-02 survey of 98 permits feeds that name a
    new building without saying "new construction" or "new building"."""

    @pytest.mark.parametrize(
        "raw",
        [
            "New Single Family Residence",  # Abilene, Spartanburg
            "New Single Family Attached - Duplex,Townhouse etc.",  # Abilene
            "New 1 & 2 Family Dwellings, and Townhouses",  # Billings
            "New Multi-Unit Residential (Apartments)",  # Billings
            "New Commercial",  # Billings
            "New Residential Construction",  # Anaheim
            "Residential New Single Family Detached",  # Fort Collins
            "Commercial New Com-Ind-Mixed-Use Building",  # Fort Collins
            "New Single Family Residential",  # Tempe
            "COMMERCIAL NEW",  # Medford
            "BLD-COM-NEW",  # Yakima
            "Bldg-New",  # Los Angeles
            "New Const.",  # St. Louis
            "ProdHome",  # Las Vegas's production homes
            "Model",  # Las Vegas
            "Residential Model Permit",  # Tucson
        ],
    )
    def test_reads_as_new_construction(self, raw):
        assert names_new_building(raw)
        assert normalize_permit_type(raw) == NEW

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Nonbldg-New", MINOR),  # Los Angeles: a structure that is not a building
            ("New Non-Building Structure", MINOR),  # Denver
            ("New Pool and / or Spa", MINOR),  # Anaheim
            ("New/Used Mobile Home Move And Setup", MINOR),  # Spartanburg
            ("New Elevator", MINOR),  # Norfolk
            ("New Residential Addition", MAJOR),  # work on a standing building
            ("Residential New Roof", MINOR),
            # "New" three words from "HOME" names the canopy, not the home.
            ("EXAMPLE HOME (B 100%) NEW SHADE CANOPY", MINOR),
        ],
    )
    def test_new_but_not_a_building(self, raw, expected):
        assert not names_new_building(raw)
        assert normalize_permit_type(raw) == expected

    def test_the_new_building_code_counts_as_a_whole_word_only(self):
        assert normalize_permit_type("NB") == NEW
        # Inside "NONBLDG" it once read Los Angeles's non-building repairs as
        # new construction.
        assert normalize_permit_type("Nonbldg-Alter/Repair") == MINOR


class TestTradePermits:
    @pytest.mark.parametrize(
        "raw",
        [
            # Texarkana's trade permits name the new construction they serve.
            "Plumbing Permit -New construction & major remodels - commercial and residential",
            "Electrical Permit (New construction & remodels for commercial and residential)",
            "HVAC for New Construction or Major Remodel for Commercial and Residential",
        ],
    )
    def test_a_trade_permit_for_new_construction_stays_a_trade_permit(self, raw):
        assert is_trade_permit(raw)
        assert not names_new_building(raw)
        assert normalize_permit_type(raw) == MEP

    def test_a_permit_that_does_not_open_with_a_trade_is_not_a_trade_permit(self):
        assert not is_trade_permit("Residential - New Construction")
        assert normalize_permit_type("Residential - New Construction") == NEW
        # Orlando names the trade after "New".
        assert not is_trade_permit("New Plumbing")
        assert normalize_permit_type("New Plumbing") == MEP


class TestPermitsProducerJobType:
    """The permits producer applies the same two rules to the job type code."""

    @pytest.fixture
    def producer(self):
        with patch("src.producers.base_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    @pytest.mark.parametrize(
        ("raw", "job_type", "normalized"),
        [
            ("New Single Family Residence", JobType.NB, NEW),
            ("ProdHome", JobType.NB, NEW),
            ("Plumbing Permit -New construction & major remodels", JobType.A2, MEP),
            ("Residential - New Construction", JobType.NB, NEW),
            # An addition keeps the job type its keyword gives it.
            ("New Residential Addition", JobType.A2, MAJOR),
            ("Nonbldg-New", JobType.OT, MINOR),
        ],
    )
    def test_job_type_and_normalized_type(self, producer, raw, job_type, normalized):
        row = {"permit_number": "X1", "latitude": "40.75", "longitude": "-73.99", "permit_type": raw}

        event = producer.parse_socrata_row(row, city_id="nyc")

        assert event is not None
        assert (event.job_type, event.normalized_permit_type) == (job_type, normalized.value)
