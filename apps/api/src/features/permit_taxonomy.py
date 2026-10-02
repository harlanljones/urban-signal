"""Unified Bay Area building-permit type taxonomy (US-441).

Every jurisdiction in the Bay Area permits pipeline (SF DBI, Oakland, San
Jose CKAN, Santa Clara County Socrata, ...) publishes its own permit-type
vocabulary — SF calls it ``permit_type_definition``, Oakland/Santa Clara
County call it a work-type or permit-subtype string, San Jose's CKAN
datastore exposes ``FOLDERNAME``/``FOLDERDESC``/``SUBTYPEDESCRIPTION``. None
of them agree on spelling or granularity, so the derived per-hex features
(``permit_velocity_60_180``, ``residential_unit_delta``) would be comparing
apples to oranges across jurisdictions without a shared vocabulary first.

:func:`normalize_permit_type` maps any of those raw strings — plus the
existing NYC/Chicago-style :class:`~src.schemas.models.JobType` code that the
shared ``DOBPermitsProducer`` already assigns to every ``PermitEvent`` — onto
one :class:`NormalizedPermitType` enum. Keyword matching is
jurisdiction-agnostic and case-insensitive so it degrades gracefully for any
Bay Area feed added later (Alameda, Contra Costa, Marin, San Mateo) without a
new per-city branch.

The type names of 98 permits feeds, surveyed on 2026-10-02, call a new
building many other things: "New Single Family Residence" (Abilene,
Spartanburg), "Residential New Dwelling" (Spokane), "COMMERCIAL NEW"
(Medford), "BLD-COM-NEW" (Yakima), "Bldg-New" (Los Angeles), and a home built
from a plan approved once is a "ProdHome" (Las Vegas) or a "Residential Model
Permit" (Tucson). :func:`names_new_building` reads those, and
:func:`is_trade_permit` keeps a trade's permit for a new building (Texarkana's
"Plumbing Permit -New construction & major remodels") a trade permit. The
shared producer applies both to the job type code as well.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any


class NormalizedPermitType(str, Enum):
    """Unified permit-type vocabulary shared across every Bay Area jurisdiction."""

    NEW_CONSTRUCTION = "NEW_CONSTRUCTION"
    MAJOR_RENOVATION = "MAJOR_RENOVATION"
    DEMOLITION = "DEMOLITION"
    CHANGE_OF_USE = "CHANGE_OF_USE"
    MINOR_ALTERATION = "MINOR_ALTERATION"
    MECHANICAL_ELECTRICAL_PLUMBING = "MECHANICAL_ELECTRICAL_PLUMBING"


# Keyword buckets, most-specific-first: a raw type string is tested against
# each bucket in this order and the first match wins. Order matters because
# some raw strings straddle categories in casual municipal phrasing (e.g.
# Oakland's "DEMOLITION - PARTIAL (ALTERATION)" must resolve to DEMOLITION,
# not MAJOR_RENOVATION, so DEMOLITION is checked before the renovation
# keywords that also appear in the string).
_KEYWORD_ORDER: tuple[tuple[NormalizedPermitType, tuple[str, ...]], ...] = (
    (
        NormalizedPermitType.DEMOLITION,
        ("DEMOLITION", "DEMO", "WRECKING", "RAZE"),
    ),
    (
        NormalizedPermitType.NEW_CONSTRUCTION,
        ("NEW CONSTRUCTION", "NEW BUILDING", "NEW DWELLING", "GROUND UP"),
    ),
    (
        NormalizedPermitType.CHANGE_OF_USE,
        ("CHANGE OF USE", "CHANGE OF OCCUPANCY", "CONVERSION", "OCCUPANCY CHANGE", "USE PERMIT"),
    ),
    (
        NormalizedPermitType.MECHANICAL_ELECTRICAL_PLUMBING,
        (
            "MECHANICAL",
            "ELECTRICAL",
            "PLUMBING",
            "HVAC",
            "BOILER",
            "MEP",
            "SOLAR",
            "PHOTOVOLTAIC",
            "FIRE SPRINKLER",
            "FIRE ALARM",
        ),
    ),
    (
        NormalizedPermitType.MAJOR_RENOVATION,
        (
            "MAJOR ALTERATION",
            "MAJOR RENOVATION",
            "ADDITION",
            "REMODEL",
            "STRUCTURAL",
            "REHABILITATION",
            "TENANT IMPROVEMENT",
        ),
    ),
    (
        NormalizedPermitType.MINOR_ALTERATION,
        (
            "MINOR ALTERATION",
            "MINOR WORK",
            "REPAIR",
            "SIGN",
            "SCAFFOLD",
            "FENCE",
            "REROOF",
            "RE-ROOF",
            "WINDOW",
            "ACCESSORY",
        ),
    ),
)

# The bare code for a new building counts only as a whole word: as a
# substring it read Los Angeles's "Nonbldg-New" and "Nonbldg-Alter/Repair"
# (structures that are not buildings) as new construction.
_NB_CODE = re.compile(r"\bNB\b")

# A trade's permit names the trade first, even when it serves a new building.
_TRADE_FIRST = re.compile(r"^\W*(PLUMBING|ELECTRICAL|ELECTRIC|MECHANICAL|HVAC)\b")

# What the surveyed vocabularies call a new building or its use.
_BUILDING = (
    r"(CONSTRUCTION|CONST|BUILDINGS?|BLDGS?|BLD|DWELLINGS?|RESIDENCES?|RESIDENTIAL"
    r"|SINGLE[\s-]*FAMILY|(1|ONE)\s*(&|AND)\s*(2|TWO)[\s-]*FAMILY|TWO[\s-]*FAMILY"
    r"|MULTI[\s-]*(FAMILY|UNIT)|MULTIFAMILY|DUPLEX(ES)?|TOWN\s*HOUSES?|TOWN\s*HOMES?"
    r"|APARTMENTS?|COMMERCIAL|HOMES?|HOUSES?|SFR|SFD)"
)
# "New" beside one of those, at most one word between, in either order: "New
# Single Family Residence", "Residential New Dwelling", "COMMERCIAL NEW",
# "BLD-COM-NEW". Further apart, "new" can name something else, as in a San
# Jose description that opens with a project name holding "HOME" and goes on
# to a "NEW SHADE CANOPY".
_NEW_BUILDING = re.compile(rf"\bNEW\W+(\w+\W+)?{_BUILDING}\b|\b{_BUILDING}\W+(\w+\W+)?NEW\b")
# Homes built from a plan the city approved once (Las Vegas's "ProdHome" and
# "Model", Tucson's "Residential Model Permit").
_PLANNED_HOME = re.compile(r"\b(MODEL|PRODHOME|PRODUCTION\s+HOMES?)\b")
# New, but not a building: a non-building structure, a mobile home moved or
# set up, a pool, sign, fence, deck, solar array or elevator.
_NOT_A_BUILDING = re.compile(
    r"\bNON[\s-]*(BUILDING|BLDG)|\b(MOBILE|MANUFACTURED|USED|SIGNS?|POOLS?|SPA|FENCE|DECK|SOLAR|ELEVATOR)\b"
)
# Work on a building that already stands keeps its own class.
_EXISTING_BUILDING = re.compile(
    r"\b(ADDITIONS?|ALTERATIONS?|ALTER|REMODEL\w*|RENOVAT\w*|REPAIRS?|CONVERSIONS?|REHAB\w*|TENANT"
    r"|ACCESSORY|RE-?ROOF\w*|ROOF\w*)\b"
)


def is_trade_permit(raw_type: Any) -> bool:
    """True when ``raw_type`` names one trade first ("Plumbing Permit -New
    construction & major remodels", "HVAC for New Construction or Major
    Remodel"): a trade's permit, whatever building it serves."""
    return bool(_TRADE_FIRST.match(str(raw_type or "").upper()))


def names_new_building(raw_type: Any) -> bool:
    """True when ``raw_type`` names a new building without saying "new
    construction" or "new building": a new home or commercial building, or a
    home built from an approved model plan. A trade's permit, a structure that
    is not a building and work on a standing building never count."""
    text = str(raw_type or "").upper()
    if is_trade_permit(text) or _NOT_A_BUILDING.search(text) or _EXISTING_BUILDING.search(text):
        return False
    return bool(_NEW_BUILDING.search(text) or _PLANNED_HOME.search(text))


# Fallback when no raw-string keyword matches: the existing NYC/Chicago-style
# JobType code already assigned by DOBPermitsProducer.parse_socrata_row.
# A1 is deliberately mapped to MAJOR_RENOVATION rather than a generic default
# — its own docstring says "structural/change in use", and structural work
# without a use-change keyword in the raw string reads as renovation, not a
# use change.
_JOB_TYPE_FALLBACK: dict[str, NormalizedPermitType] = {
    "NB": NormalizedPermitType.NEW_CONSTRUCTION,
    "DM": NormalizedPermitType.DEMOLITION,
    "A1": NormalizedPermitType.MAJOR_RENOVATION,
    "A2": NormalizedPermitType.MINOR_ALTERATION,
    "A3": NormalizedPermitType.MINOR_ALTERATION,
    "SG": NormalizedPermitType.MINOR_ALTERATION,
    "OT": NormalizedPermitType.MINOR_ALTERATION,
}


def normalize_permit_type(raw_type: Any = None, job_type: Any = None) -> NormalizedPermitType:
    """Normalize one jurisdiction's raw permit-type string to the unified enum.

    ``raw_type`` is matched case-insensitively against jurisdiction-agnostic
    keyword buckets first (works for SF's ``permit_type_definition``,
    Oakland's work-type string, San Jose's ``FOLDERDESC``/
    ``SUBTYPEDESCRIPTION``, Santa Clara County's permit-subtype string, or any
    future Bay Area feed). A new building named some other way counts as new
    construction (:func:`names_new_building`), and a trade's permit that
    mentions the new building it serves stays a trade permit. When
    ``raw_type`` is missing or matches nothing, falls back to the
    already-assigned NYC/Chicago-style ``JobType`` code (accepts either a
    :class:`~src.schemas.models.JobType` member or its ``.value`` string) so
    every ``PermitEvent`` — Bay Area or not — always resolves to a normalized
    type rather than raising.
    """
    text = str(raw_type or "").strip().upper()
    if text:
        for normalized, keywords in _KEYWORD_ORDER:
            matched = any(keyword in text for keyword in keywords)
            if normalized is NormalizedPermitType.NEW_CONSTRUCTION:
                matched = matched or bool(_NB_CODE.search(text)) or names_new_building(text)
                if matched and is_trade_permit(text):
                    return NormalizedPermitType.MECHANICAL_ELECTRICAL_PLUMBING
            if matched:
                return normalized

    code = getattr(job_type, "value", job_type)
    if code is not None:
        mapped = _JOB_TYPE_FALLBACK.get(str(code).strip().upper())
        if mapped is not None:
            return mapped

    return NormalizedPermitType.MINOR_ALTERATION
