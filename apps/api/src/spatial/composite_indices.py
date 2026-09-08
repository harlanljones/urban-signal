"""Universal derived composite indices: SBCAI, AISI, WCS (US-405 / Stream A).

Exposes the three universal derived composite indices built by combining datasets
already in scope across all registered metros:

1. SBCAI (A8) — Small Business Credit Access Index:
   SBA loans + FDIC branches + HMDA denial rate + SNAP retailers + ACS income.
   Composite: Z(loan_per_estab)*0.25 + Z(branch_density)*0.20 +
              Z(1-denial_rate)*0.20 + Z(SNAP_density)*0.15 + Z(income)*0.20

2. AISI (A9) — Anchor Institution Stability Index:
   NCES schools + NPPES medical providers + SNAP food access + anchor churn + crime rate.
   Composite: Z(anchor_density)*0.25 + Z(medical_density)*0.20 +
              Z(food_access)*0.15 + Z(1-anchor_churn)*0.20 + Z(1-crime_rate)*0.20

3. WCS (A10) — Workforce Commute-Shed Score:
   LODES jobs-housing imbalance + ACS WFH + bike/ped active transport + EV readiness + commute time.
   Composite: Z(1/jobs_housing_imbalance)*0.30 + Z(work_from_home)*0.15 +
              Z(active_transport)*0.25 + Z(ev_readiness)*0.15 + Z(1/commute_time)*0.15

Pure feature-store compositing math over registered national inputs (leaf-only,
no spine edits, no new event schemas).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.features.aisi_index import (
    AISI_BASELINES,
    AISI_ORIENTATION,
    AISI_SOURCES,
    AISI_WEIGHTS,
    compute_aisi_for_h3,
)
from src.features.index_math import (
    ORIENT_COMPLEMENT,
    ORIENT_NONE,
    ORIENT_RECIPROCAL,
    compute_weighted_index,
    orient,
    quintile_band,
    z_score,
)
from src.features.sbcai_index import (
    SBCAI_BASELINES,
    SBCAI_ORIENTATION,
    SBCAI_SOURCES,
    SBCAI_WEIGHTS,
    compute_sbcai_for_h3,
)
from src.features.wcs_index import (
    WCS_BASELINES,
    WCS_ORIENTATION,
    WCS_SOURCES,
    WCS_WEIGHTS,
    compute_wcs_for_h3,
)


def compute_all_composite_indices_for_h3(
    h3_index: str,
    *,
    sbcai_inputs: Mapping[str, float | None] | None = None,
    aisi_inputs: Mapping[str, float | None] | None = None,
    wcs_inputs: Mapping[str, float | None] | None = None,
    sbcai_band_cutpoints: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Compute all three universal composite indices for a single H3 cell.

    Args:
        h3_index: H3 cell identifier.
        sbcai_inputs: Optional dict of SBCAI terms (sba_loan_per_estab,
            bank_branch_density, credit_denial_rate, snap_density, income).
        aisi_inputs: Optional dict of AISI terms (anchor_density,
            medical_density, food_access, anchor_churn, crime_rate).
        wcs_inputs: Optional dict of WCS terms (jobs_housing_imbalance,
            work_from_home, active_transport, ev_readiness, commute_time).
        sbcai_band_cutpoints: Optional cutpoints for SBCAI quintile banding.

    Returns:
        Dict containing individual results for 'sbcai', 'aisi', and 'wcs'.
    """
    sbcai_kwargs = dict(sbcai_inputs or {})
    aisi_kwargs = dict(aisi_inputs or {})
    wcs_kwargs = dict(wcs_inputs or {})

    return {
        "h3_index": h3_index,
        "sbcai": compute_sbcai_for_h3(
            h3_index,
            sba_loan_per_estab=sbcai_kwargs.get("sba_loan_per_estab"),
            bank_branch_density=sbcai_kwargs.get("bank_branch_density"),
            credit_denial_rate=sbcai_kwargs.get("credit_denial_rate"),
            snap_density=sbcai_kwargs.get("snap_density"),
            income=sbcai_kwargs.get("income"),
            band_cutpoints=sbcai_band_cutpoints,
        ),
        "aisi": compute_aisi_for_h3(
            h3_index,
            anchor_density=aisi_kwargs.get("anchor_density"),
            medical_density=aisi_kwargs.get("medical_density"),
            food_access=aisi_kwargs.get("food_access"),
            anchor_churn=aisi_kwargs.get("anchor_churn"),
            crime_rate=aisi_kwargs.get("crime_rate"),
        ),
        "wcs": compute_wcs_for_h3(
            h3_index,
            jobs_housing_imbalance=wcs_kwargs.get("jobs_housing_imbalance"),
            work_from_home=wcs_kwargs.get("work_from_home"),
            active_transport=wcs_kwargs.get("active_transport"),
            ev_readiness=wcs_kwargs.get("ev_readiness"),
            commute_time=wcs_kwargs.get("commute_time"),
        ),
    }


__all__ = [
    "AISI_BASELINES",
    "AISI_ORIENTATION",
    "AISI_SOURCES",
    "AISI_WEIGHTS",
    "ORIENT_COMPLEMENT",
    "ORIENT_NONE",
    "ORIENT_RECIPROCAL",
    "SBCAI_BASELINES",
    "SBCAI_ORIENTATION",
    "SBCAI_SOURCES",
    "SBCAI_WEIGHTS",
    "WCS_BASELINES",
    "WCS_ORIENTATION",
    "WCS_SOURCES",
    "WCS_WEIGHTS",
    "compute_aisi_for_h3",
    "compute_all_composite_indices_for_h3",
    "compute_sbcai_for_h3",
    "compute_wcs_for_h3",
    "compute_weighted_index",
    "orient",
    "quintile_band",
    "z_score",
]
