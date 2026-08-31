"""Shared compositing engine for Stream A derived composite indices (US-405).

The three universal composite indices — SBCAI (A8), AISI (A9), WCS (A10) —
share one construction. Each is a weighted **z-sum** of available per-H3
component terms, renormalized to whatever combination of terms is actually
present, with an explicit higher-is-better orientation applied per component
before z-scoring, a **confidence** equal to the number of terms present, and a
transparent caveat list. Compute is pure math over already-registered national
inputs: no new event schema, no spine edits.

Orientation matters because a composite index must be monotone in the same
direction as the underlying signal. Two raw terms run the wrong way and are
inverted before z-scoring:

* ``complement`` — ``1 - x`` for a rate/count where a *low* value is already a
  healthy one (credit denial rate, anchor churn, crime rate).
* ``reciprocal`` — ``1 / x`` for a duration/blance where a *high* value is the
  unhealthy one (commute time, jobs-housing imbalance). A non-positive input
  cannot be oriented and is treated as missing, never as zero.

``baselines`` are on the **oriented** (post-transform) scale: callers supply a
``(mean, std)`` pair describing the transformed reference distribution, exactly
as ``cvc_index.py`` documents its own per-component baselines. The weighted
z-sum then reads as a standard normal score where higher means the index's
headline signal is stronger.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

ORIENT_NONE = "none"
ORIENT_COMPLEMENT = "complement"
ORIENT_RECIPROCAL = "reciprocal"


def orient(value: float | None, mode: str = ORIENT_NONE) -> float | None:
    """Map a raw component onto a higher-is-better scale, or None if missing."""
    if value is None:
        return None
    v = float(value)
    if mode == ORIENT_COMPLEMENT:
        return 1.0 - v
    if mode == ORIENT_RECIPROCAL:
        # A duration or imbalance of zero has no reciprocal; treat it as
        # unorientable (missing) rather than emitting +inf.
        if v <= 0.0:
            return None
        return 1.0 / v
    return v


def z_score(value: float | None, mean: float = 0.0, std: float = 1.0) -> float:
    """Standard normal z-score with division-by-zero protection."""
    if value is None or std <= 1e-6:
        return 0.0
    return (value - mean) / std


def quintile_band(score: float, cutpoints: Sequence[float]) -> int:
    """Band a score into 1..N+1 using N cutpoints (4 cutpoints -> quintiles)."""
    for index, cutpoint in enumerate(cutpoints, start=1):
        if score < cutpoint:
            return index
    return len(cutpoints) + 1


def compute_weighted_index(
    h3_index: str,
    values: Mapping[str, float | None],
    *,
    weights: Mapping[str, float],
    baselines: Mapping[str, tuple[float, float]],
    return_key: str,
    label: str,
    orientation: Mapping[str, str] | None = None,
    sources: Mapping[str, str] | None = None,
    extra_caveats: Sequence[str] = (),
    band_cutpoints: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Compute one weighted-z composite index for one H3 cell.

    Args:
        h3_index: the H3 cell id this row belongs to.
        values: raw per-component values keyed by component name; ``None`` means
            the term is absent for this cell (it is excluded and the remaining
            weights renormalized).
        weights: per-component weights. Their key order is the canonical
            component order used for output.
        baselines: per-component ``(mean, std)`` on the oriented scale.
        return_key: short key prefix; the result carries ``<return_key>_score``
            and ``<return_key>_confidence``.
        label: human name of the index, used for caveat text.
        orientation: per-component orientation mode (``"none"`` /
            ``"complement"`` / ``"reciprocal"``); unlisted components default to
            ``"none"``.
        sources: per-component source name to surface in the ``sources`` list.
        extra_caveats: caveats to include verbatim (index-specific).
        band_cutpoints: if given, bucket the score into ``band`` 1..N+1.

    Returns:
        Dict with ``h3_index``, ``<return_key>_score`` (float), 
        ``<return_key>_confidence`` (int = number of present terms),
        ``coverage`` (present / total), ``sources``, ``components`` and
        ``caveats``; plus ``band`` when ``band_cutpoints`` is provided.
    """
    orientation = orientation or {}
    sources = sources or {}
    component_names = list(weights)

    oriented: dict[str, float | None] = {
        name: orient(values.get(name), orientation.get(name, ORIENT_NONE))
        for name in component_names
    }
    available = [name for name in component_names if oriented[name] is not None]
    total = len(component_names)
    coverage = len(available) / total if total else 0.0

    weight_total = sum(weights.get(name, 0.0) for name in available)
    if weight_total > 0:
        z_total = sum(
            z_score(oriented[name], *baselines.get(name, (0.0, 1.0)))
            * (weights.get(name, 0.0) / weight_total)
            for name in available
        )
    else:
        z_total = 0.0

    score = float(round(z_total, 4))

    components_out: dict[str, Any] = {}
    for name in component_names:
        oriented_value = oriented[name]
        components_out[name] = {
            "value": values.get(name),
            "oriented": round(oriented_value, 6) if oriented_value is not None else None,
            "weight": weights.get(name, 0.0),
            "available": name in available,
        }

    source_list = [sources[name] for name in available if name in sources]

    caveats = list(extra_caveats)
    missing = [name for name in component_names if name not in available]
    if missing:
        caveats.append(f"missing inputs lower confidence: {', '.join(sorted(missing))}")

    result: dict[str, Any] = {
        "h3_index": h3_index,
        f"{return_key}_score": score,
        f"{return_key}_confidence": len(available),
        "coverage": round(coverage, 4),
        "sources": source_list,
        "components": components_out,
        "caveats": caveats,
    }
    if band_cutpoints is not None:
        result["band"] = quintile_band(score, band_cutpoints)
    return result
