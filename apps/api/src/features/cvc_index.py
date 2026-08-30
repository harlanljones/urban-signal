"""Commercial Vitality Churn (CVC) composite index (US-406).

Leaf-only feature-store computation. Cross-corroborates three independent
per-H3 business-formation/destruction signals — SLA license churn, POI net
churn, ZBP YoY growth — plus SBA approvals and FMCSA carrier adds, into a
single ``cvc_score`` with a ``cvc_confidence`` (1–3 = number of agreeing
sources) and an explicit ``sources`` list. Pure math over already-registered
inputs: no new event schema, no spine edits.

Three independent churn rates per H3:

- ``sla_churn_90d``  — SLA license move-ins minus move-outs over 90d.
- ``poi_delta_90d``  — ``poi_opened`` − ``poi_closed`` over 90d.
- ``zbp_growth``     — ZBP YoY establishment+employment growth (ZIP→H3 via
  ``dynamic_spatial_fallback``, confidentiality flags normalized).

Cross-corroboration (additive to the weighted z-sum):

- SLA and POI agree on direction            → +0.3
- SBA approvals present in the cell         → +0.2
- FMCSA carrier adds in the cell            → +0.1

Caveats honored here (labels surfaced in the result's ``caveats`` list):

- POI deltas carry a ~35-day detection lag — POI churn is always stale vs SLA.
- ZBP suppression flags (D/S/N/X/V/Z) mean a value is withheld, not zero;
  withheld cells are counted and the growth component is treated as missing.
- SBA 504 (fixed-asset) approvals are a stronger leading indicator than 7(a)
  (working capital); 504 approvals are weighted at full strength, 7(a) at half.
- FMCSA trucking is not retail/office vitality — it corroborates at +0.1 only.
- SLA ``license_type`` values are namespaced per registry (``tabc:``,
  ``wa_li:``…) — normalize before cross-registry aggregation
  (``normalize_sla_license_namespace``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

# ZBP confidentiality / availability flag codes (Census Business Patterns).
# A flag on a numeric field means the value is withheld/suppressed, NOT a
# true zero — it must propagate as missing, never as 0. Aligned with
# ``src/spatial/zbp_signal.py``.
ZBP_WITHHELD_FLAGS = frozenset({"D", "S", "N", "X", "V", "Z", ""})

# Per-registry namespaces observed on SLA ``license_type`` values. Stripping
# them is required before churn can be aggregated across registries.
SLA_NAMESPACES = ("tabc:", "wa_li:", "sla:", "li:", "dcra:", "abc:")

# Weights for the three independent churn rates (renormalized to available
# sources when one is missing).
DEFAULT_WEIGHTS: Mapping[str, float] = {
    "sla_churn_90d": 0.4,
    "poi_delta_90d": 0.3,
    "zbp_growth": 0.3,
}

# (mean, std) baselines for the z-transform of each churn component. Defaults
# are reference distributions for a res-8-ish cell; callers may override with
# their own calibrated baselines.
DEFAULT_BASELINES: Mapping[str, tuple[float, float]] = {
    "sla_churn_90d": (0.0, 5.0),
    "poi_delta_90d": (0.0, 10.0),
    "zbp_growth": (0.0, 0.10),
}

# Cross-corroboration bonuses.
BONUS_SLA_POI_AGREE = 0.3
BONUS_SBA = 0.2
BONUS_FMCSA = 0.1

# SBA 504 (fixed-asset) is the stronger leading indicator; 7(a) (working
# capital) corroborates at half weight.
SBA_504_WEIGHT = 1.0
SBA_7A_WEIGHT = 0.5


def normalize_sla_license_namespace(license_type: str | None) -> str | None:
    """Strip a registry namespace prefix from an SLA ``license_type``.

    SLAs are aggregated per registry and different registries namespace their
    license types (``tabc:…`` for Texas TABC, ``wa_li:…`` for Washington
    L&I). Comparing or summing license types across registries without first
    stripping these prefixes double-counts or misses categories, so churn
    aggregation must normalize first. Returns ``None`` for empty input.

    Example:
        ``"tabc:MB"`` -> ``"MB"``
    """
    if not license_type:
        return None
    stripped = str(license_type).strip()
    lowered = stripped.lower()
    for ns in SLA_NAMESPACES:
        if lowered.startswith(ns):
            return stripped[len(ns) :]
    return stripped


def _normalize_zbp_flag(value: Any) -> float | None:
    """Normalize a ZBP cell into a numeric value or None (withheld)."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip().upper()
        if stripped in ZBP_WITHHELD_FLAGS:
            return None
        try:
            return float(stripped.replace(",", ""))
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def compute_zbp_growth(
    current_estab: Any,
    prior_estab: Any,
    current_emp: Any = None,
    prior_emp: Any = None,
    *,
    epsilon: float = 1.0,
) -> tuple[float | None, int]:
    """YoY ZBP establishment+employment growth with suppression handling.

    The two measures are blended (establishments primary, employment a
    corroborating second axis when both present). Any withheld (suppressed)
    component makes the growth estimate ``None`` rather than silently zero.

    Returns ``(growth, suppressed_count)`` where ``suppressed_count`` is the
    number of input cells carrying a suppression flag.
    """
    cur_e = _normalize_zbp_flag(current_estab)
    pri_e = _normalize_zbp_flag(prior_estab)
    cur_m = _normalize_zbp_flag(current_emp)
    pri_m = _normalize_zbp_flag(prior_emp)

    inputs = [current_estab, prior_estab, current_emp, prior_emp]
    suppressed = sum(1 for v in inputs if _normalize_zbp_flag(v) is None and v not in (None, ""))

    if cur_e is None or pri_e is None:
        return None, suppressed
    if pri_e == 0 and (cur_e == 0 or cur_e == pri_e):
        return 0.0, suppressed
    if pri_e == 0:
        return None, suppressed

    estab_growth = (cur_e - pri_e) / (pri_e + epsilon)
    if cur_m is not None and pri_m is not None:
        emp_growth = (cur_m - pri_m) / (pri_m + epsilon)
        growth = 0.6 * estab_growth + 0.4 * emp_growth
    else:
        growth = estab_growth
    return float(growth), suppressed


def _z_score(value: float | None, mean: float, std: float) -> float:
    """Standard normal Z-score with division-by-zero protection."""
    if value is None or std <= 1e-6:
        return 0.0
    return (value - mean) / std


def _direction(value: float | None) -> int:
    """+1 / -1 / 0 for a component's net direction; None is neutral 0."""
    if value is None:
        return 0
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _consensus_direction(directions: Sequence[int]) -> int:
    """Sign of the summed non-zero directions; 0 on a split/empty vote."""
    non_zero = [d for d in directions if d != 0]
    if not non_zero:
        return 0
    total = sum(non_zero)
    return 1 if total > 0 else (-1 if total < 0 else 0)


def _agreement_count(directions: Sequence[int], consensus: int) -> int:
    """Number of non-zero sources matching the consensus direction."""
    if consensus == 0:
        return 0
    return sum(1 for d in directions if d != 0 and d == consensus)


def _sba_breakdown(value: Any) -> tuple[float, int, int, bool]:
    """(weighted_count, fixed_asset_count, working_capital_count, available).

    Accepts a plain count (treated as unspecified program, full weight) or a
    mapping keyed by program — ``504``/``7a`` or ``fixed_asset``/
    ``working_capital``.
    """
    if value is None:
        return 0.0, 0, 0, False
    if isinstance(value, Mapping):
        fa = value.get("504") or value.get("fixed_asset") or 0
        wc = value.get("7a") or value.get("working_capital") or 0
        try:
            fa_n, wc_n = float(fa), float(wc)
        except (TypeError, ValueError):
            return 0.0, 0, 0, False
        weighted = fa_n * SBA_504_WEIGHT + wc_n * SBA_7A_WEIGHT
        return weighted, int(fa_n), int(wc_n), weighted > 0
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0, 0, 0, False
    return float(n), int(n), 0, n > 0


def compute_cvc_for_h3(
    h3_index: str,
    sla_churn_90d: float | None,
    poi_delta_90d: float | None,
    zbp_growth: float | None,
    sba_approvals: Any = None,
    fmcsa_adds: float | None = None,
    *,
    weights: Mapping[str, float] | None = None,
    baselines: Mapping[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Compute the Commercial Vitality Churn composite for one H3 cell.

    Args:
        h3_index: the H3 cell id this row belongs to.
        sla_churn_90d: SLA net churn (move-ins − move-outs) over 90d, or None
            when the cell has no SLA coverage.
        poi_delta_90d: POI net churn (``poi_opened`` − ``poi_closed``) over
            90d, or None when POI coverage is missing.
        zbp_growth: ZBP YoY establishment+employment growth, or None when the
            cell's ZBP data is withheld/suppressed or absent.
        sba_approvals: SBA approval count in the cell (int/float), or a
            mapping with per-program counts (``{"504": n, "7a": m}`` or
            ``{"fixed_asset": n, "working_capital": m}``). 504 (fixed-asset)
            approvals corroborate at full strength, 7(a) at half.
        fmcsa_adds: FMCSA carrier adds in the cell; corroborates at +0.1 only
            (trucking is not retail/office vitality).
        weights: optional per-component weights (defaults
            ``sla 0.4 / poi 0.3 / zbp 0.3``); renormalized to available
            sources.
        baselines: optional per-component ``(mean, std)`` z-transform
            baselines.

    Returns:
        Dict with at least ``cvc_score`` (float), ``cvc_confidence`` (int
        1–3 = number of agreeing sources; 0 when no churn source exists) and
        ``sources`` (list of corroborating source names), plus ``h3_index``,
        ``components`` and ``caveats`` for transparency.
    """
    weights = dict(weights or DEFAULT_WEIGHTS)
    baselines = dict(baselines or DEFAULT_BASELINES)

    components: dict[str, Any] = {
        "sla_churn_90d": {"value": sla_churn_90d, "available": sla_churn_90d is not None},
        "poi_delta_90d": {"value": poi_delta_90d, "available": poi_delta_90d is not None},
        "zbp_growth": {"value": zbp_growth, "available": zbp_growth is not None},
    }

    churn_names = ("sla_churn_90d", "poi_delta_90d", "zbp_growth")
    available = [n for n in churn_names if components[n]["available"]]

    directions = [_direction(components[n]["value"]) for n in available]
    consensus = _consensus_direction(directions)
    agreement = _agreement_count(directions, consensus)
    confidence = agreement if agreement > 0 else (1 if available else 0)

    available_weights = {n: weights.get(n, 0.0) for n in available}
    weight_total = sum(available_weights.values())
    if weight_total > 0:
        z_total = sum(
            _z_score(components[n]["value"], *baselines.get(n, (0.0, 1.0)))
            * (available_weights[n] / weight_total)
            for n in available
        )
    else:
        z_total = 0.0

    sla_poi_agree = (
        components["sla_churn_90d"]["available"]
        and components["poi_delta_90d"]["available"]
        and _direction(sla_churn_90d) != 0
        and _direction(sla_churn_90d) == _direction(poi_delta_90d)
    )
    sba_weighted, sba_fa, sba_wc, sba_available = _sba_breakdown(sba_approvals)
    fmcsa_available = fmcsa_adds is not None and float(fmcsa_adds) > 0

    bonuses = {
        "sla_poi_agree": BONUS_SLA_POI_AGREE if sla_poi_agree else 0.0,
        "sba": BONUS_SBA if sba_available else 0.0,
        "fmcsa": BONUS_FMCSA if fmcsa_available else 0.0,
    }

    cvc_score = float(round(z_total + sum(bonuses.values()), 4))

    sources: list[str] = []
    for name in available:
        sources.append({"sla_churn_90d": "sla", "poi_delta_90d": "poi", "zbp_growth": "zbp"}[name])
    if sla_poi_agree:
        sources.append("sla+poi_agree")
    if sba_available:
        sources.append("sba")
    if fmcsa_available:
        sources.append("fmcsa")

    caveats: list[str] = []
    if components["poi_delta_90d"]["available"]:
        caveats.append("poi_delta_90d carries a ~35-day lag — POI churn is always stale vs SLA")
    if not components["zbp_growth"]["available"]:
        caveats.append("zbp_growth missing — suppressed or withheld cell")
    if sba_fa > 0:
        caveats.append("SBA 504 fixed-asset approvals are a stronger leading indicator than 7(a)")
    if fmcsa_available:
        caveats.append("FMCSA trucking is not retail/office vitality — weighted at +0.1")
    missing = [n for n in churn_names if not components[n]["available"]]
    if missing:
        caveats.append(f"missing inputs lower confidence: {', '.join(sorted(missing))}")

    components["sba_approvals"] = {
        "weighted_count": round(sba_weighted, 4),
        "fixed_asset": sba_fa,
        "working_capital": sba_wc,
        "available": sba_available,
    }
    components["fmcsa_adds"] = {
        "value": fmcsa_adds,
        "available": fmcsa_available,
    }

    return {
        "h3_index": h3_index,
        "cvc_score": cvc_score,
        "cvc_confidence": confidence,
        "sources": sources,
        "components": components,
        "bonuses": bonuses,
        "caveats": caveats,
    }
