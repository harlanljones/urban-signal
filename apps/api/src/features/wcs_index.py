"""Workforce Commute-Shed Score (WCS) composite (US-405 / Stream A A10).

Universal index buildable for all registered metros from already-registered
national feeds — no new spine changes for the national components. Emits an
``EnrichedH3Feature`` addition + per-city ``macro_series`` row.

Components (all higher-is-better on the oriented scale):

- ``jobs_housing_imbalance`` — LODES jobs-housing imbalance; inverted via
  ``reciprocal`` (``1 / imbalance``) so a balanced shed reads higher.
- ``work_from_home`` — share working from home (ACS).
- ``active_transport`` — bike/ped share (ACS / GBFS).
- ``ev_readiness`` — EV charging readiness.
- ``commute_time`` — mean commute time; inverted via ``reciprocal``
  (``1 / time``) so a shorter commute reads higher.

Composite: ``Z(1/jobs_housing_imbalance)*0.30 + Z(work_from_home)*0.15 +
Z(active_transport)*0.25 + Z(ev_readiness)*0.15 + Z(1/commute_time)*0.15``.

Caveats honored here:

- LODES is 2023 vintage.
- Jobs-housing balance is misleading at res 9 — compute at division/submarket
  (res 7).

A non-positive ``jobs_housing_imbalance`` or ``commute_time`` cannot be
oriented: it is treated as missing (never zeroed).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.features.index_math import ORIENT_RECIPROCAL, compute_weighted_index

WCS_WEIGHTS: Mapping[str, float] = {
    "jobs_housing_imbalance": 0.30,
    "work_from_home": 0.15,
    "active_transport": 0.25,
    "ev_readiness": 0.15,
    "commute_time": 0.15,
}

# Baselines are on the oriented (post-transform) scale; reference (res-8-ish)
# distributions, overridable by callers. For the reciprocal terms the mean/std
# describe the oriented (1/x) value, not the raw duration/imbalance.
WCS_BASELINES: Mapping[str, tuple[float, float]] = {
    "jobs_housing_imbalance": (1.0, 0.5),
    "work_from_home": (0.15, 0.05),
    "active_transport": (0.05, 0.03),
    "ev_readiness": (0.0, 1.0),
    "commute_time": (1.0, 0.2),
}

WCS_ORIENTATION: Mapping[str, str] = {
    "jobs_housing_imbalance": ORIENT_RECIPROCAL,
    "commute_time": ORIENT_RECIPROCAL,
}

WCS_SOURCES: Mapping[str, str] = {
    "jobs_housing_imbalance": "lodes",
    "work_from_home": "acs",
    "active_transport": "bike_ped",
    "ev_readiness": "ev",
    "commute_time": "acs",
}


def compute_wcs_for_h3(
    h3_index: str,
    jobs_housing_imbalance: float | None = None,
    work_from_home: float | None = None,
    active_transport: float | None = None,
    ev_readiness: float | None = None,
    commute_time: float | None = None,
    *,
    weights: Mapping[str, float] | None = None,
    baselines: Mapping[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Compute the Workforce Commute-Shed composite for one H3 cell.

    Any component left ``None`` is treated as missing for the cell: it is
    excluded from the composite, the remaining weights are renormalized, and
    confidence drops.
    """
    values = {
        "jobs_housing_imbalance": jobs_housing_imbalance,
        "work_from_home": work_from_home,
        "active_transport": active_transport,
        "ev_readiness": ev_readiness,
        "commute_time": commute_time,
    }
    caveats = ["LODES is 2023 vintage"]
    if jobs_housing_imbalance is not None:
        caveats.append(
            "jobs-housing balance is misleading at res 9 — compute at division/submarket (res 7)"
        )
    return compute_weighted_index(
        h3_index,
        values,
        weights=weights or WCS_WEIGHTS,
        baselines=baselines or WCS_BASELINES,
        orientation=WCS_ORIENTATION,
        return_key="wcs",
        label="Workforce Commute-Shed Score",
        sources=WCS_SOURCES,
        extra_caveats=caveats,
    )
