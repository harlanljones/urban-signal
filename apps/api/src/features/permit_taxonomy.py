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
"""

from __future__ import annotations

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
        ("NEW CONSTRUCTION", "NEW BUILDING", "NEW DWELLING", "GROUND UP", "NB"),
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
    future Bay Area feed). When ``raw_type`` is missing or matches nothing,
    falls back to the already-assigned NYC/Chicago-style ``JobType`` code
    (accepts either a :class:`~src.schemas.models.JobType` member or its
    ``.value`` string) so every ``PermitEvent`` — Bay Area or not — always
    resolves to a normalized type rather than raising.
    """
    text = str(raw_type or "").strip().upper()
    if text:
        for normalized, keywords in _KEYWORD_ORDER:
            if any(keyword in text for keyword in keywords):
                return normalized

    code = getattr(job_type, "value", job_type)
    if code is not None:
        mapped = _JOB_TYPE_FALLBACK.get(str(code).strip().upper())
        if mapped is not None:
            return mapped

    return NormalizedPermitType.MINOR_ALTERATION
