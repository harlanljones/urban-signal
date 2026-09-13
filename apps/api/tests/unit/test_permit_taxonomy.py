"""Tests for the unified Bay Area permit-type taxonomy (US-441)."""

from src.features.permit_taxonomy import NormalizedPermitType, normalize_permit_type
from src.schemas.models import JobType


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
