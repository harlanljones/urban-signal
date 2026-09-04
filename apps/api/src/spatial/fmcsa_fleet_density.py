"""FMCSA fleet power-unit / hazmat freight-density leaf module (US-423, NO spine edits).

The existing FMCSA integration (``carrier_license_producer.py`` /
``fmcsa_specs.py``, US-373) rides the ``SLALicenseEvent`` classify->geocode->H3
path for carrier *registration* status (census add/status, authority history,
out-of-service actions). It deliberately does not carry fleet-scale fields
(``TOTAL_POWER_UNITS``, ``TOTAL_DRIVERS``) or ``HAZMAT_FLAG`` — those are not
part of the SLA license-event shape.

This module is the missing piece for the freight & logistics density index
this ticket asks for: given a carrier's base-of-operations geocode, fleet
power-unit count, and hazmat authorization, place a weighted contribution on
the H3 grid and accumulate it into a per-cell density score, corroborating
commercial building permits (distribution centers, cross-dock logistics) per
``docs/research/federal-mobility-energy-financial-signals-2026-08-30.md``.

Leaf module only, matching the established convention for this wave
(``epa_echo.py``, ``eia_electricity.py``, ``cfpb_hmda.py``): no imports from
``config`` / ``city_registry`` / ``geo_utils`` / ``submarkets`` / ``producers``.
Wiring this into a scheduled national feed (a fleet-density
``NationalFeedSpec`` distinct from the existing license-event flow) remains a
follow-up spine change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from src.spatial.h3_indexer import H3SpatialIndexer

# Hazmat-authorized carriers weight more heavily: they mark the corridors the
# research doc calls out ("hazardous material freight concentration
# corridors"), a distinct risk/logistics axis from raw power-unit count.
HAZMAT_WEIGHT_MULTIPLIER = 1.5

# A carrier's power-unit count is capped before contributing to the index so
# a single mega-fleet HQ record cannot dominate/wash out a hex's density
# score relative to every small operator around it.
MAX_POWER_UNITS_CONTRIBUTION = 500


@dataclass
class CarrierFleetRecord:
    """One FMCSA carrier's base-of-operations geocode + fleet scale."""

    dot_number: str
    lat: float
    lng: float
    total_power_units: int
    hazmat_flag: bool = False
    carrier_operation: Optional[str] = None  # "A" | "B" | "C" per MCS-150


def _clamped_power_units(total_power_units: int) -> int:
    if total_power_units is None or total_power_units < 0:
        return 0
    return min(total_power_units, MAX_POWER_UNITS_CONTRIBUTION)


def carrier_freight_weight(record: CarrierFleetRecord) -> float:
    """Freight-density contribution for one carrier.

    Base weight is the clamped power-unit count (a carrier with zero
    reported power units still contributes a floor weight of 1.0 — it is a
    registered base of operations, not zero logistics presence). Hazmat
    authorization multiplies the weight per ``HAZMAT_WEIGHT_MULTIPLIER``.
    """
    base = max(_clamped_power_units(record.total_power_units), 1.0)
    if record.hazmat_flag:
        base *= HAZMAT_WEIGHT_MULTIPLIER
    return float(base)


def map_carrier_to_h3(record: CarrierFleetRecord) -> Dict[str, str]:
    """Resolve a carrier's base-of-operations coordinates to H3 res 7/8/9.

    Mirrors ``epa_echo.map_event_to_h3`` / the repo's standard event->H3
    resolution so a future producer can reuse
    ``H3SpatialIndexer.get_multi_res_hierarchy`` without a new joiner.
    """
    return H3SpatialIndexer.get_multi_res_hierarchy(record.lat, record.lng)


def accumulate_fleet_density(
    density_by_cell: Dict[str, float],
    h3_cell: str,
    record: CarrierFleetRecord,
) -> None:
    """Fold one carrier's freight weight into a cell's density tally."""
    density_by_cell[h3_cell] = density_by_cell.get(h3_cell, 0.0) + carrier_freight_weight(record)


def hazmat_share(density_records: list) -> float:
    """Fraction of carriers in a batch that are hazmat-authorized.

    Accepts a list of ``CarrierFleetRecord``. Returns 0.0 for an empty batch
    rather than dividing by zero — the honest "no data" signal for a hex with
    no registered carriers.
    """
    if not density_records:
        return 0.0
    hazmat_count = sum(1 for r in density_records if r.hazmat_flag)
    return hazmat_count / len(density_records)
