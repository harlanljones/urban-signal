"""FRA rail crossing severance signal — leaf module (US-422, NO spine edits).

Pure geometry/severity helpers that map one FRA (Federal Railroad
Administration) highway-rail grade crossing inventory record — and its
associated Form 57 accident-log incidents — onto the repo's H3 res 7/8/9
spatial units. This is intentionally a *leaf* file: it imports ONLY from
`h3_indexer` (itself a leaf file), so it can land in the repo without
touching any spine file (config / city_registry / geo_utils / submarkets /
producers) — the same "Wave 1 point-event, zero spine risk" pattern used by
`epa_echo.py` and `hpms_context.py`. See
`docs/research/national-environmental-infrastructure-signals-2026-08-30.md`
§2.3 / §7 (Ticket Spec 2, US-411) for the source evaluation and phasing.

FRA maintains a continuously-updated inventory of 250k+ public and private
grade crossings (`LATITUDE`, `LONGITUDE`, `WDCODE` warning device, `TOTTRK`
track count, `DAYTHRU`/`NGTTHRU` train movements) plus a monthly Form 57
accident log. The helpers here compute a **Rail Severance Index** per
crossing (barrier friction from train volume, track count, and passive vs.
active warning devices) and fold Form 57 incidents into a recency-weighted
cell tally — the reusable, spine-free building block a future spine-bound
registration (a producer + FeedType) would call.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict

from src.spatial.h3_indexer import H3SpatialIndexer


# FRA `WDCODE` groups warning devices into passive (signage only) vs. active
# (train-actuated) protection. Passive crossings carry materially higher
# barrier-friction and incident risk in the FRA safety data.
class WarningDeviceClass(str, Enum):
    PASSIVE = "PASSIVE"                # crossbucks / stop signs only
    ACTIVE_FLASHING_LIGHTS = "ACTIVE_FLASHING_LIGHTS"
    ACTIVE_GATES = "ACTIVE_GATES"      # gates + flashing lights (highest protection)
    OTHER = "OTHER"


# Crossing type from FRA `XINGTYP`: public roads carry through-traffic;
# private crossings (driveways, farm/industrial access) generally do not.
class CrossingType(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


# Relative barrier-friction prior per warning device class. Tunable; NOT a
# scoring source until a FeedType is registered (spine change) — mirrors the
# disclaimer on `epa_echo.SEVERITY_WEIGHT`.
WARNING_DEVICE_FRICTION_WEIGHT: Dict[WarningDeviceClass, float] = {
    WarningDeviceClass.PASSIVE: 1.8,
    WarningDeviceClass.ACTIVE_FLASHING_LIGHTS: 1.2,
    WarningDeviceClass.ACTIVE_GATES: 0.6,
    WarningDeviceClass.OTHER: 1.0,
}

# FRA Form 57 accidents show up in the public safety data for ~5 years of
# rolling history in most consumer views; recency weighting uses a half-life
# around that, matching `epa_echo.RECENCY_HALF_LIFE_DAYS`'s convention.
RECENCY_HALF_LIFE_DAYS = 365 * 2.5


@dataclass
class RailCrossing:
    """One FRA grade-crossing inventory record, already geocoded."""

    lat: float
    lng: float
    crossing_id: str
    warning_device: WarningDeviceClass
    crossing_type: CrossingType = CrossingType.PUBLIC
    total_tracks: int = 1
    day_thru: int = 0
    night_thru: int = 0
    max_train_speed: float = 0.0


@dataclass
class RailIncident:
    """One FRA Form 57 accident-log record at a given crossing."""

    lat: float
    lng: float
    crossing_id: str
    incident_date: date
    fatalities: int = 0
    injuries: int = 0


def map_crossing_to_h3(crossing: RailCrossing) -> Dict[str, str]:
    """Resolve a crossing's coordinates to the H3 res 7/8/9 hierarchy."""
    return H3SpatialIndexer.get_multi_res_hierarchy(crossing.lat, crossing.lng)


def map_incident_to_h3(incident: RailIncident) -> Dict[str, str]:
    """Resolve an incident's coordinates to the H3 res 7/8/9 hierarchy."""
    return H3SpatialIndexer.get_multi_res_hierarchy(incident.lat, incident.lng)


def daily_train_movements(crossing: RailCrossing) -> int:
    """Total daily through-train movements (`DAYTHRU` + `NGTTHRU`)."""
    return max(crossing.day_thru, 0) + max(crossing.night_thru, 0)


def rail_severance_index(crossing: RailCrossing) -> float:
    """Urban Severance & Barrier Index for one crossing.

    Combines daily train movements, track count (more tracks = longer
    blockage per event), and the warning-device friction prior. Private
    crossings are scaled down (0.4x): they do not sever a public
    thoroughfare, so they contribute far less severance friction than a
    public crossing carrying the same traffic. The index is intentionally
    unbounded — callers normalize/percentile it across a metro's crossings
    rather than reading it as an absolute scale.
    """
    movements = daily_train_movements(crossing)
    tracks = max(crossing.total_tracks, 1)
    device_weight = WARNING_DEVICE_FRICTION_WEIGHT[crossing.warning_device]
    base = movements * tracks * device_weight
    if crossing.crossing_type is CrossingType.PRIVATE:
        base *= 0.4
    return base


def incident_severity(incident: RailIncident, as_of: date | None = None) -> float:
    """Recency-weighted severity for one Form 57 incident.

    Fatalities are weighted 5x injuries (mirrors the outsized weight the FRA
    safety data gives fatal grade-crossing collisions). Older incidents decay
    exponentially with `RECENCY_HALF_LIFE_DAYS`. Returns 0.0 for incidents
    dated in the future (data-entry noise guard) or with zero fatalities and
    injuries.
    """
    base = 5.0 * incident.fatalities + 1.0 * incident.injuries
    if base <= 0:
        return 0.0
    anchor = as_of or date.today()
    age_days = (anchor - incident.incident_date).days
    if age_days < 0:
        return 0.0
    decay = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
    return base * decay


def accumulate_cell_weight(
    weights_by_cell: Dict[str, float],
    h3_cell: str,
    add: float,
) -> None:
    """Fold one crossing's severance index or incident's severity into a cell tally.

    Callers aggregate per res-9 cell across all crossings/incidents, then
    roll up via `H3SpatialIndexer.get_parent` to res 8 / res 7 for sparse-cell
    smoothing (same `dynamic_spatial_fallback` pattern used elsewhere).
    """
    weights_by_cell[h3_cell] = weights_by_cell.get(h3_cell, 0.0) + add
