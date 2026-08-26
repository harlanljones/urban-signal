"""EPA ECHO compliance-event signal — leaf module (US-170, NO spine edits).

Pure geometry/severity helpers that map one EPA ECHO facility compliance event
(facility lat/lng + regulatory program + event class + date) onto the repo's
H3 res 7/8/9 spatial units. This is intentionally a *leaf* file: it imports
ONLY from `h3_indexer` (itself a leaf file), so it can land in the repo without
touching any spine file (config / city_registry / geo_utils / submarkets /
producers). Registering ECHO as a live `FeedType` would be an interlock/spine
change and is explicitly out of scope for this stream — see
`docs/research/epa-echo-validation.md` (recommendation: DEFER). The helpers
here are the reusable, spine-free building block a future spine-bound
registration would call.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict

from src.spatial.h3_indexer import H3SpatialIndexer

# Programs ECHO consolidates. "MULTI" covers cross-program facilities.
class EchoProgram(str, Enum):
    CAA = "CAA"        # Clean Air Act (stationary sources)
    CWA = "CWA"        # Clean Water Act (NPDES discharges)
    RCRA = "RCRA"      # Resource Conservation & Recovery Act (hazardous waste)
    SDWA = "SDWA"      # Safe Drinking Water Act (public water systems)
    CERCLA = "CERCLA"  # Superfund
    EPCRA = "EPCRA"    # Emergency Planning & Community Right-to-Know
    MULTI = "MULTI"    # cross-program


# Event classes ECHO exposes at the facility level. These are *compliance
# events* (timestamped), which makes ECHO closer to the repo's event feeds
# than to a stateless bulk aggregate such as LODES.
class EchoEventClass(str, Enum):
    INSPECTION = "INSPECTION"      # compliance evaluation / site visit
    VIOLATION = "VIOLATION"        # recorded non-compliance
    ENFORCEMENT = "ENFORCEMENT"    # formal enforcement action / case
    PENALTY = "PENALTY"            # monetary penalty assessed


# Severity priors for a simple division/submarket compliance-risk score.
# Tunable; NOT a scoring source until a FeedType is registered (spine change).
SEVERITY_WEIGHT: Dict[EchoEventClass, float] = {
    EchoEventClass.INSPECTION: 0.2,
    EchoEventClass.VIOLATION: 1.0,
    EchoEventClass.ENFORCEMENT: 1.5,
    EchoEventClass.PENALTY: 1.8,
}

# ECHO shows ~5 years of inspection/enforcement in facility search and ~10 on
# the Detailed Facility Report; recency weighting uses a half-life around that.
RECENCY_HALF_LIFE_DAYS = 365 * 2.5


@dataclass
class EchoEvent:
    """One facility compliance event, already geocoded via FRS coordinates."""

    lat: float
    lng: float
    program: EchoProgram
    event_class: EchoEventClass
    event_date: date
    facility_id: str


def event_severity(event: EchoEvent, as_of: date | None = None) -> float:
    """Recency-weighted severity for one event.

    Older events decay exponentially with `RECENCY_HALF_LIFE_DAYS`, so a
    stale violation contributes less than a fresh one. Returns 0.0 for events
    dated in the future (data-entry noise guard).
    """
    base = SEVERITY_WEIGHT[event.event_class]
    anchor = as_of or date.today()
    age_days = (anchor - event.event_date).days
    if age_days < 0:
        return 0.0
    decay = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
    return base * decay


def map_event_to_h3(event: EchoEvent) -> Dict[str, str]:
    """Resolve an event's coordinates to the H3 res 7/8/9 hierarchy.

    Mirrors exactly how event feeds resolve a row to H3 in the repo, so a
    future ECHO producer can reuse `H3SpatialIndexer.get_multi_res_hierarchy`
    without any new joiner. Raises on invalid coordinates (delegates to h3).
    """
    return H3SpatialIndexer.get_multi_res_hierarchy(event.lat, event.lng)


def accumulate_cell_weight(
    weights_by_cell: Dict[str, float],
    h3_res9: str,
    add: float,
) -> None:
    """Fold one event's recency-weighted severity into a res-9 cell tally.

    Callers aggregate per res-9 cell across all events, then roll up via
    `H3SpatialIndexer.get_parent` to res 8 / res 7 for sparse-cell smoothing
    (same `dynamic_spatial_fallback` pattern the repo uses elsewhere).
    """
    weights_by_cell[h3_res9] = weights_by_cell.get(h3_res9, 0.0) + add
