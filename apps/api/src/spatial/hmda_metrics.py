"""HMDA mortgage-activity validation helper — leaf-only, NOT wired into the pipeline.

Pure functions to demonstrate that census-tract-level HMDA mortgage metrics
(investor-purchase share, denial rate, government-backed share) can be rolled up
to the repo's H3 / division / submarket units via areal apportionment. This module
is a feasibility proof for the US-165 validation (docs/research/hmda-validation.md).
It is intentionally not imported by any spine or producer code; registering HMDA
as a signal requires a spine/interlock change (new FeedType + bulk-CSV producer).
"""

from typing import Dict, List

import h3

from src.spatial.h3_indexer import H3SpatialIndexer


# Census tract is coarser than H3 res 7-9. The honest rollup target is res 7
# (macro district); res 8/9 would be pure areal smearing with no added signal.
DEFAULT_ROLLUP_RESOLUTION = 7


def investor_purchase_share(investor_purchase_loans: int, total_purchase_loans: int) -> float:
    """Fraction of home-purchase loans made to investors (non-owner-occupied).

    The decisive HMDA axis no event feed (e.g. DEEDS) can reconstruct. Returns 0.0
    when there are no purchase loans (avoid divide-by-zero).
    """
    if total_purchase_loans <= 0:
        return 0.0
    return investor_purchase_loans / total_purchase_loans


def denial_rate(denied: int, total_decisions: int) -> float:
    """Share of acted-upon applications that were denied (action_taken == 3).

    Credit-access / distress axis absent from every current feed. Returns 0.0 when
    there are no decided applications.
    """
    if total_decisions <= 0:
        return 0.0
    return denied / total_decisions


def government_backed_share(fha_va_loans: int, total_loans: int) -> float:
    """Share of loans that are FHA/VA/RHS (government-backed).

    First-time / lower-income buyer-pressure proxy. Returns 0.0 when total is <= 0.
    """
    if total_loans <= 0:
        return 0.0
    return fha_va_loans / total_loans


def _tract_centroid_to_h3(lat: float, lng: float, resolution: int) -> str:
    """Map a census-tract centroid to an H3 cell via the repo's indexer."""
    return H3SpatialIndexer.latlng_to_h3(lat, lng, resolution=resolution)


def rollup_tract_to_h3(
    tract_metrics: Dict[str, Dict[str, float]],
    tract_centroids: Dict[str, tuple],
    resolution: int = DEFAULT_ROLLUP_RESOLUTION,
) -> Dict[str, Dict[str, float]]:
    """Apportion tract-level loan counts onto H3 cells by centroid assignment.

    Given per-tract raw loan counts (e.g. {"22071000100": {"purchase": 120,
    "investor_purchase": 30, "denied": 40, "decided": 200}}) and a matching
    tract->(lat,lng) centroid map, assigns each tract's counts to the single H3
    cell its centroid lands in. Because a tract is larger than an H3 res-7 cell,
    this is a coarse (lossy) assignment — the documented resolution ceiling for
    HMDA. Returns a cell-keyed dict of summed counts.

    NOTE: requires a tract-centroid geometry source (new repo dependency; the LAR
    ships no coordinates). Areal (polygon-area-weighted) apportionment across the
    cells a tract covers is the more correct variant and is left for the producer.
    """
    if set(tract_metrics) != set(tract_centroids):
        raise ValueError("tract_metrics and tract_centroids must have matching keys")
    if not tract_metrics:
        return {}

    return _rollup_tract(tract_metrics, tract_centroids, resolution)


def rollup_tract_to_h7(
    tract_metrics: Dict[str, Dict[str, float]],
    tract_centroids: Dict[str, tuple],
) -> Dict[str, Dict[str, float]]:
    """Convenience alias: rollup to H3 res 7 (the honest HMDA resolution ceiling)."""
    return _rollup_tract(tract_metrics, tract_centroids, DEFAULT_ROLLUP_RESOLUTION)


def _rollup_tract(
    tract_metrics: Dict[str, Dict[str, float]],
    tract_centroids: Dict[str, tuple],
    resolution: int,
) -> Dict[str, Dict[str, float]]:
    """Shared tract->H3 centroid-apportionment implementation."""
    cells: Dict[str, Dict[str, float]] = {}
    metric_keys: List[str] = []
    for tract_id, metrics in tract_metrics.items():
        if tract_id not in tract_centroids:
            raise KeyError(f"missing centroid for tract {tract_id}")
        metric_keys = list(metrics.keys())
        lat, lng = tract_centroids[tract_id]
        cell = _tract_centroid_to_h3(lat, lng, resolution)
        bucket = cells.setdefault(cell, {k: 0.0 for k in metric_keys})
        for k, v in metrics.items():
            bucket[k] += v
    return cells
