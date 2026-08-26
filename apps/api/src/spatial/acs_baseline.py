"""Census ACS neighborhood-baseline feature rollup (leaf module, US-166).

Pure, network-free helpers that turn block-group ACS estimates + margins of error into
H3-rolled baseline features. This module is intentionally decoupled from the live API
and from `H3SpatialIndexer`: the caller supplies a ``bg_to_h3`` resolver so this leaf
stays testable and free of transport/spine concerns.

ACS margins of error are 90%-CI. Aggregation follows the Census Statistical Working
Papers MOE formulas:
  * Sum of counts:        MOE = sqrt(sum(MOE_i ** 2))
  * Ratio X / Y:          SE = sqrt(SE_x**2/Y**2 + X**2*SE_y**2/Y**4 - 2*X*SE_x*SE_y/Y**3)
                          MOE = 1.645 * SE   (rho assumed 0)
Medians cannot be summed; they are rolled up as a population-weighted mean of the
block-group medians (a documented approximation).
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

Z = 1.645  # 90% confidence multiplier for ACS margins of error


@dataclass(frozen=True)
class ACSFeature:
    """A baseline feature and how to aggregate it from block-group rows."""

    name: str
    estimate_var: str
    moe_var: Optional[str]
    agg: str  # "sum" | "ratio" | "weighted_median_approx"
    # For "ratio": numerator/denominator are the estimate vars of component features.
    numerator_var: Optional[str] = None
    denominator_var: Optional[str] = None
    weight_var: Optional[str] = None  # for weighted_median_approx
    concept: str = ""


# Catalog of proposed neighborhood baseline features (all `acs5`, estimate + MOE).
# Variable codes verified live against api.census.gov/data/2023/acs/acs5/variables.
ACS_BASELINE_FEATURES: Dict[str, ACSFeature] = {
    "total_population": ACSFeature(
        "total_population", "B01003_001E", "B01003_001M", "sum",
        concept="Total population",
    ),
    "median_age": ACSFeature(
        "median_age", "B01002_001E", "B01002_001M", "weighted_median_approx",
        weight_var="B01003_001E", concept="Median age by block group",
    ),
    "median_household_income": ACSFeature(
        "median_household_income", "B19013_001E", "B19013_001M", "weighted_median_approx",
        weight_var="B19013_001M", concept="Median household income (inflation-adj)",
    ),
    "per_capita_income": ACSFeature(
        "per_capita_income", "B19301_001E", "B19301_001M", "weighted_median_approx",
        weight_var="B19301_001M", concept="Per-capita income",
    ),
    "poverty_rate": ACSFeature(
        "poverty_rate", None, None, "ratio",
        numerator_var="B17020_002E", denominator_var="B17020_001E",
        concept="Poverty status share (ratio of poverty pop / total)",
    ),
    "total_housing_units": ACSFeature(
        "total_housing_units", "B25001_001E", "B25001_001M", "sum",
        concept="Total housing units",
    ),
    "owner_occupied_share": ACSFeature(
        "owner_occupied_share", None, None, "ratio",
        numerator_var="B25003_002E", denominator_var="B25003_001E",
        concept="Owner-occupied housing share",
    ),
    "renter_occupied_share": ACSFeature(
        "renter_occupied_share", None, None, "ratio",
        numerator_var="B25003_003E", denominator_var="B25003_001E",
        concept="Renter-occupied housing share",
    ),
    "median_gross_rent": ACSFeature(
        "median_gross_rent", "B25064_001E", "B25064_001M", "weighted_median_approx",
        weight_var="B25064_001M", concept="Median gross rent",
    ),
    "median_home_value": ACSFeature(
        "median_home_value", "B25077_001E", "B25077_001M", "weighted_median_approx",
        weight_var="B25077_001M", concept="Median home value",
    ),
    "cost_burden_30pct_share": ACSFeature(
        "cost_burden_30pct_share", None, None, "ratio",
        numerator_var="B25070_010E", denominator_var="B25070_001E",
        concept="Housing cost burden >= 30% share",
    ),
    "median_travel_time": ACSFeature(
        "median_travel_time", "B08303_001E", "B08303_001M", "weighted_median_approx",
        weight_var="B08303_001M", concept="Median travel time to work (minutes)",
    ),
    "worked_from_home_share": ACSFeature(
        "worked_from_home_share", None, None, "ratio",
        numerator_var="B08302_001E", denominator_var="B08006_001E",
        concept="Worked-from-home share of workers",
    ),
}


@dataclass
class BGRow:
    """One block-group observation: variable code -> (estimate, moe)."""

    bg_fips12: str
    values: Dict[str, Tuple[float, float]]  # var -> (estimate, moe)


def sum_with_moe(estimates: List[float], moes: List[float]) -> Tuple[float, float]:
    """Aggregate a sum of independent counts and propagate the 90% MOE.

    Census sum formula: MOE_sum = sqrt(Σ MOE_i²). Missing (NaN/None) MOEs are treated
    as zero uncertainty contribution (a conservatism floor: callers should flag these).
    """
    if not estimates:
        return 0.0, 0.0
    total = sum(estimates)
    se_sq = sum((m or 0.0) ** 2 for m in moes)
    return total, (se_sq ** 0.5)


def ratio_with_moe(
    num: float, num_moe: float, den: float, den_moe: float
) -> Tuple[float, float]:
    """Ratio X/Y with 90% MOE (rho assumed 0). Returns (ratio, moe); moe is 0 if den<=0."""
    if den <= 0:
        return 0.0, 0.0
    ratio = num / den
    se_x = (num_moe or 0.0) / Z
    se_y = (den_moe or 0.0) / Z
    se_sq = (se_x ** 2 / den ** 2) + (num ** 2 * se_y ** 2 / den ** 4) - (
        2 * num * se_x * se_y / den ** 3
    )
    if se_sq < 0:
        se_sq = 0.0
    return ratio, Z * (se_sq ** 0.5)


def weighted_median_approx(
    medians: List[float], weights: List[float]
) -> float:
    """Population-weighted mean of block-group medians (approximation of the true median).

    True medians cannot be summed from component medians; this is a documented proxy.
    """
    pairs = [(m, w) for m, w in zip(medians, weights) if m is not None and w is not None]
    if not pairs:
        return 0.0
    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return 0.0
    return sum(m * w for m, w in pairs) / total_w


def block_fips_to_bg(block_fips15: str) -> str:
    """Derive the 12-digit block-group FIPS from a 15-digit census block FIPS.

    Used to attach block-group centroids from the LODES crosswalk's 15-char
    `tabblk2020` (the first 12 chars are the block group). Validates length only.
    """
    if len(block_fips15) != 15 or not block_fips15.isdigit():
        raise ValueError(f"Expected 15-digit block FIPS, got {block_fips15!r}")
    return block_fips15[:12]


@dataclass
class H3Baseline:
    h3_index: str
    features: Dict[str, Tuple[float, float]]  # feature name -> (estimate, moe)


def aggregate_blockgroup_to_h3(
    rows: List[BGRow],
    bg_to_h3: Callable[[str], str],
    feature_names: Optional[List[str]] = None,
) -> List[H3Baseline]:
    """Roll block-group rows up to H3 cells following each feature's aggregation rule.

    ``bg_to_h3`` maps a 12-digit BG FIPS to an H3 cell string (caller wires
    H3SpatialIndexer). Count features sum estimates + MOE in quadrature; ratio features
    aggregate numerator/denominator then apply ``ratio_with_moe``; median features use a
    population-weighted mean (approximation). Returns one ``H3Baseline`` per occupied cell.
    """
    names = feature_names or list(ACS_BASELINE_FEATURES.keys())
    cells: Dict[str, List[BGRow]] = {}
    for row in rows:
        cell = bg_to_h3(row.bg_fips12)
        cells.setdefault(cell, []).append(row)

    out: List[H3Baseline] = []
    for cell, cell_rows in cells.items():
        feats: Dict[str, Tuple[float, float]] = {}
        for name in names:
            f = ACS_BASELINE_FEATURES[name]
            if f.agg == "sum":
                ests, moes = [], []
                for r in cell_rows:
                    if f.estimate_var in r.values:
                        e, m = r.values[f.estimate_var]
                        ests.append(e)
                        moes.append(m)
                feats[name] = sum_with_moe(ests, moes)
            elif f.agg == "ratio":
                num_e = sum(r.values[f.numerator_var][0] for r in cell_rows if f.numerator_var in r.values)
                num_m = sum_with_moe(
                    [r.values[f.numerator_var][0] for r in cell_rows if f.numerator_var in r.values],
                    [r.values[f.numerator_var][1] for r in cell_rows if f.numerator_var in r.values],
                )[1]
                den_e = sum(r.values[f.denominator_var][0] for r in cell_rows if f.denominator_var in r.values)
                den_m = sum_with_moe(
                    [r.values[f.denominator_var][0] for r in cell_rows if f.denominator_var in r.values],
                    [r.values[f.denominator_var][1] for r in cell_rows if f.denominator_var in r.values],
                )[1]
                feats[name] = ratio_with_moe(num_e, num_m, den_e, den_m)
            elif f.agg == "weighted_median_approx":
                meds, wts = [], []
                for r in cell_rows:
                    if f.estimate_var in r.values and f.weight_var in r.values:
                        meds.append(r.values[f.estimate_var][0])
                        # weight by the count beneath the median; fall back to MOE if needed
                        wts.append(abs(r.values[f.weight_var][0]) or 1.0)
                feats[name] = (weighted_median_approx(meds, wts), 0.0)
        out.append(H3Baseline(h3_index=cell, features=feats))
    return out
