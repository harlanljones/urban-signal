"""Census ZIP Code Business Patterns (ZBP) → H3 projection helpers.

Leaf module only — no spine file is imported or edited. This is a building block
for a *future* spine-gated REGISTER of ZBP as a commercial-profile context source
(see docs/research/zbp-validation.md, Linear US-167). It is intentionally
self-contained: it depends only on ``h3`` and the leaf ``H3SpatialIndexer``.

ZBP rows carry a ZIP code and no coordinates, and its confidentiality flags
(``D``/``S``/``N``/``X``/``V``/``Z``) mean some counts are withheld rather than zero.
The helpers below (1) normalize those flags so withheld values never silently
become 0, and (2) project a ZIP's representative point (resolved externally via a
ZIP→ZCTA→centroid crosswalk) into the repo's H3 res 7/8/9 hierarchy, rolling up
with the existing dynamic-spatial-fallback contract.
"""

from typing import Dict, List, Optional, Tuple

from src.spatial.h3_indexer import H3SpatialIndexer

# ZBP confidentiality / availability flag codes (Census Business Patterns convention).
# Any of these on a numeric field means the value is withheld/suppressed/unavailable,
# NOT a true zero — callers must propagate None, never coerce to 0.
_WITHHELD_FLAGS = frozenset({"D", "S", "N", "X", "V", "Z", ""})


def normalize_zbp_flag(value) -> Optional[float]:
    """Normalize a ZBP cell into a numeric value or None (withheld).

    ZBP publishes confidentiality flags in place of suppressed numbers. A flag
    (``D``/``S``/``N``/``X``/``V``/``Z`` or empty string/None) means the value is
    not available and must be treated as missing, not as zero. Numeric strings and
    numbers pass through; ``"0"`` is a legitimate zero and is preserved.

    Args:
        value: raw ZBP field (str, int, float, or None).

    Returns:
        float value if present, else None when withheld/unavailable.
    """
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip().upper()
        if stripped in _WITHHELD_FLAGS:
            return None
        try:
            # ZBP bulk files sometimes carry thousands separators (e.g. "1,234").
            return float(stripped.replace(",", ""))
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def zip_to_h3_record(
    zip_code: str,
    estab: object,
    emp: object,
    payroll: object,
    lat: float,
    lng: float,
    naics: Optional[str] = None,
) -> Dict:
    """Project a single ZBP ZIP record to the repo's H3 res 7/8/9 hierarchy.

    The ``lat``/``lng`` are the ZIP's representative point, resolved externally
    (ZIP → dominant ZCTA via the HUD USPS crosswalk → ZCTA centroid). The rollup
    keys on establishment count so sparse cells fall back to a coarser parent
    (``H3SpatialIndexer.dynamic_spatial_fallback``), which also dilutes confidentiality
    suppression across more establishments.

    Returns a dict with the effective H3 cell, resolution, and flag-normalized
    measures (withheld values carried as None, never 0).
    """
    hierarchy = H3SpatialIndexer.get_multi_res_hierarchy(lat, lng)
    estab_val = normalize_zbp_flag(estab)
    density = int(estab_val) if estab_val is not None else 0
    effective_cell, effective_res = H3SpatialIndexer.dynamic_spatial_fallback(
        hierarchy["h3_res9"], density
    )
    return {
        "zip_code": zip_code,
        "naics": naics,
        "h3_res7": hierarchy["h3_res7"],
        "h3_res8": hierarchy["h3_res8"],
        "h3_res9": hierarchy["h3_res9"],
        "effective_h3": effective_cell,
        "effective_resolution": effective_res,
        "establishments": estab_val,
        "employment": normalize_zbp_flag(emp),
        "payroll_annual": normalize_zbp_flag(payroll),
    }


def rollup_zbp_to_h3(records: List[Dict]) -> List[Dict]:
    """Aggregate per-ZIP ZBP records into H3 cells (bulk-synthesis output shape).

    Sums establishments/employment/payroll per effective H3 cell. Suppressed
    (None) measures are excluded from the sum and tallied separately so a cell
    is never over-stated by coercing withheld values to zero.
    """
    acc: Dict[str, Dict] = {}
    for rec in records:
        cell = rec["effective_h3"]
        bucket = acc.setdefault(
            cell,
            {
                "effective_h3": cell,
                "effective_resolution": rec["effective_resolution"],
                "establishments": 0.0,
                "employment": 0.0,
                "payroll_annual": 0.0,
                "suppressed_estab": 0,
                "suppressed_emp": 0,
                "suppressed_payroll": 0,
                "zip_count": 0,
            },
        )
        bucket["zip_count"] += 1
        for key, suppressed_key in (
            ("establishments", "suppressed_estab"),
            ("employment", "suppressed_emp"),
            ("payroll_annual", "suppressed_payroll"),
        ):
            val = rec.get(key)
            if val is None:
                bucket[suppressed_key] += 1
            else:
                bucket[key] += val
    return list(acc.values())
