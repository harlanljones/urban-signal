"""Anchor Institution Stability Index (AISI) composite (US-405 / Stream A A9).

Universal index buildable for all registered metros from already-registered
national feeds — no new spine changes for the national components. Emits an
``EnrichedH3Feature`` addition + per-city ``macro_series`` row.

Components (all higher-is-better on the oriented scale):

- ``anchor_density`` — NCES schools + Head Start anchor institutions.
- ``medical_density`` — NPPES medical providers.
- ``food_access`` — SNAP retailer food access.
- ``anchor_churn`` — anchor-institution turnover; inverted via ``complement``
  (``1 - churn``) so stability reads higher.
- ``crime_rate`` — local crime rate; inverted via ``complement`` (``1 - rate``).

Composite: ``Z(anchor_density)*0.25 + Z(medical_density)*0.20 +
Z(food_access)*0.15 + Z(1-anchor_churn)*0.20 + Z(1-crime_rate)*0.20``.

Caveats honored here:

- NCES school data carries an ~8-12-mo lag; school closures are sparse.
- NPPES deactivation resolves the address from our own state store.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.features.index_math import ORIENT_COMPLEMENT, compute_weighted_index

AISI_WEIGHTS: Mapping[str, float] = {
    "anchor_density": 0.25,
    "medical_density": 0.20,
    "food_access": 0.15,
    "anchor_churn": 0.20,
    "crime_rate": 0.20,
}

# Baselines are on the oriented (post-transform) scale; reference (res-8-ish)
# distributions, overridable by callers.
AISI_BASELINES: Mapping[str, tuple[float, float]] = {
    "anchor_density": (0.0, 1.0),
    "medical_density": (0.0, 1.0),
    "food_access": (0.0, 1.0),
    "anchor_churn": (0.5, 0.15),
    "crime_rate": (0.10, 0.05),
}

AISI_ORIENTATION: Mapping[str, str] = {
    "anchor_churn": ORIENT_COMPLEMENT,
    "crime_rate": ORIENT_COMPLEMENT,
}

AISI_SOURCES: Mapping[str, str] = {
    "anchor_density": "nces",
    "medical_density": "nppes",
    "food_access": "snap",
    "anchor_churn": "anchor_churn",
    "crime_rate": "crime",
}


def compute_aisi_for_h3(
    h3_index: str,
    anchor_density: float | None = None,
    medical_density: float | None = None,
    food_access: float | None = None,
    anchor_churn: float | None = None,
    crime_rate: float | None = None,
    *,
    weights: Mapping[str, float] | None = None,
    baselines: Mapping[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Compute the Anchor Institution Stability composite for one H3 cell.

    Any component left ``None`` is treated as missing for the cell: it is
    excluded from the composite, the remaining weights are renormalized, and
    confidence drops.
    """
    values = {
        "anchor_density": anchor_density,
        "medical_density": medical_density,
        "food_access": food_access,
        "anchor_churn": anchor_churn,
        "crime_rate": crime_rate,
    }
    caveats = ["NCES school data carries ~8-12-mo lag; school closures are sparse"]
    if medical_density is not None:
        caveats.append("NPPES deactivation resolves address from our own state store")
    return compute_weighted_index(
        h3_index,
        values,
        weights=weights or AISI_WEIGHTS,
        baselines=baselines or AISI_BASELINES,
        orientation=AISI_ORIENTATION,
        return_key="aisi",
        label="Anchor Institution Stability Index",
        sources=AISI_SOURCES,
        extra_caveats=caveats,
    )
