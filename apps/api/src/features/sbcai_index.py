"""Small Business Credit Access Index (SBCAI) composite (US-405 / Stream A A8).

Universal index buildable for all registered metros from already-registered
national feeds — no new spine changes for the national components. Emits an
``EnrichedH3Feature`` addition + per-city ``macro_series`` row (feature-store
only; no new event schemas).

Components (all higher-is-better on the oriented scale, per the research
evidence ``creative-feeds-and-supplementation-2026-08-30.md`` §0):

- ``sba_loan_per_estab`` — SBA loan volume per establishment.
- ``bank_branch_density`` — FDIC branch presence per cell.
- ``credit_denial_rate`` — HMDA denial rate; inverted via ``complement``
  (``1 - rate``) so a lower denial rate reads higher.
- ``snap_density`` — SNAP retailer density.
- ``income`` — ACS median household income.

Composite: ``Z(loan_per_estab)*0.25 + Z(branch_density)*0.20 +
Z(1-denial_rate)*0.20 + Z(SNAP_density)*0.15 + Z(income)*0.20``, quintile-banded
when ``band_cutpoints`` is supplied.

Known caveats honored here (never silently trusted):

- ``gross_approval`` is approval, not disbursement; SBA loan addresses are
  truncated ~35-49 chars (geocode street-first, zip+city fallback).
- HMDA is leaf-only today — the denial term is only trusted once the HMDA
  national leg is wired; until then it is emitted minus that term with a lower
  confidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.features.index_math import ORIENT_COMPLEMENT, compute_weighted_index

SBCAI_WEIGHTS: Mapping[str, float] = {
    "sba_loan_per_estab": 0.25,
    "bank_branch_density": 0.20,
    "credit_denial_rate": 0.20,
    "snap_density": 0.15,
    "income": 0.20,
}

# Baselines are on the oriented (post-transform) scale. Reference distributions
# for a res-8-ish cell; callers may override.
SBCAI_BASELINES: Mapping[str, tuple[float, float]] = {
    "sba_loan_per_estab": (0.0, 1.0),
    "bank_branch_density": (0.0, 1.0),
    "credit_denial_rate": (0.5, 0.20),
    "snap_density": (0.0, 1.0),
    "income": (70_000.0, 25_000.0),
}

SBCAI_ORIENTATION: Mapping[str, str] = {
    "credit_denial_rate": ORIENT_COMPLEMENT,
}

SBCAI_SOURCES: Mapping[str, str] = {
    "sba_loan_per_estab": "sba",
    "bank_branch_density": "fdic",
    "credit_denial_rate": "hmda",
    "snap_density": "snap",
    "income": "acs",
}


def compute_sbcai_for_h3(
    h3_index: str,
    sba_loan_per_estab: float | None = None,
    bank_branch_density: float | None = None,
    credit_denial_rate: float | None = None,
    snap_density: float | None = None,
    income: float | None = None,
    *,
    weights: Mapping[str, float] | None = None,
    baselines: Mapping[str, tuple[float, float]] | None = None,
    band_cutpoints: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Compute the Small Business Credit Access composite for one H3 cell.

    Any component left ``None`` is treated as missing for the cell: it is
    excluded from the composite, the remaining weights are renormalized, and
    confidence drops. This is the "emit the index minus missing terms" path the
    evidence doc requires until HMDA/ECHO/LODES national legs are live.
    """
    values = {
        "sba_loan_per_estab": sba_loan_per_estab,
        "bank_branch_density": bank_branch_density,
        "credit_denial_rate": credit_denial_rate,
        "snap_density": snap_density,
        "income": income,
    }
    caveats = [
        "SBA gross_approval != disbursed; loan addresses truncated ~35-49 chars (street-first geocode)"
    ]
    if credit_denial_rate is not None:
        caveats.append(
            "HMDA is leaf-only — denial term trusted once the HMDA national leg is wired"
        )
    return compute_weighted_index(
        h3_index,
        values,
        weights=weights or SBCAI_WEIGHTS,
        baselines=baselines or SBCAI_BASELINES,
        orientation=SBCAI_ORIENTATION,
        return_key="sbcai",
        label="Small Business Credit Access Index",
        sources=SBCAI_SOURCES,
        extra_caveats=caveats,
        band_cutpoints=band_cutpoints,
    )
