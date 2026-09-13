"""Redfin/Zillow signal reconciliation + monthly per-hex market series (US-440).

Where Redfin and Zillow both report a view of the same underlying metric —
Redfin's ``median_sale_price`` vs. Zillow's ZHVI for home values, Zillow's
ZORI for rent (Redfin publishes no rent series) — this module blends them
with configurable precedence weights before the area-weighted ZIP-to-H3 join
runs, per the ticket's default:

    sale price:  Redfin 0.6 / Zillow 0.4
    rent:        Redfin 0.0 / Zillow 1.0   (ZORI is the only rent input)

Reconciling before the join, at ZCTA granularity, rather than after
area-weighting each source separately, means a ZIP missing one source for a
given month falls back to the other source alone (renormalized weight)
instead of the hex silently losing that ZIP's contribution to one of the two
signals. :mod:`src.spatial.zip_h3_join` still does the actual area allocation
once a single reconciled per-ZCTA value exists.

``build_hex_monthly_series`` is the orchestration entry point: given
per-ZCTA-per-period observations from both sources and a ZIP-to-H3 weight
table (:func:`src.spatial.zip_h3_join.build_weights`), it returns
``{h3_cell: {period: value}}`` for every registered metric family, feeding
LIMS momentum differencing (:func:`momentum_diff` computes the month-over-
month deltas a momentum-style score consumes; this module does not modify
:class:`~src.features.lims_calculator.LIMSCalculator` itself — that is a
separate, out-of-scope wiring step once a market-momentum weight is added
to the LIMS formula).
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

from src.spatial.zip_h3_join import ZipHexWeight, aggregate_extensive, aggregate_intensive

# metric family -> (redfin_weight, zillow_weight). A weight of 0.0 means that
# source simply never contributes (Redfin has no rent series).
DEFAULT_RECONCILIATION_WEIGHTS: dict[str, tuple[float, float]] = {
    "sale_price": (0.6, 0.4),
    "rent": (0.0, 1.0),
}


@dataclass(frozen=True)
class ReconciliationWeights:
    """Configurable Redfin/Zillow precedence weights per metric family."""

    weights: dict[str, tuple[float, float]] = field(
        default_factory=lambda: dict(DEFAULT_RECONCILIATION_WEIGHTS)
    )

    def for_family(self, family: str) -> tuple[float, float]:
        return self.weights.get(family, (1.0, 0.0))


def reconcile_value(
    redfin_value: float | None,
    zillow_value: float | None,
    weights: tuple[float, float],
) -> float | None:
    """Blend one (redfin, zillow) pair for one ZCTA/period with precedence weights.

    Missing-data fallback: if only one source reported, that source's value
    is used directly (not scaled by its partial weight) — a ZIP where Zillow
    has no ZHVI print this month should not have its Redfin price silently
    discounted to 60% of itself. Weights only matter when both sources agree
    to disagree.
    """
    redfin_weight, zillow_weight = weights
    have_redfin = redfin_value is not None and redfin_weight > 0
    have_zillow = zillow_value is not None and zillow_weight > 0
    if have_redfin and have_zillow:
        total = redfin_weight + zillow_weight
        return (redfin_value * redfin_weight + zillow_value * zillow_weight) / total
    if have_redfin:
        return redfin_value
    if have_zillow:
        return zillow_value
    return None


ObservationTable = Mapping[str, Mapping[date, float]]  # zcta -> period -> value


def reconcile_series(
    redfin_by_zcta: ObservationTable,
    zillow_by_zcta: ObservationTable,
    family: str,
    weights: ReconciliationWeights | None = None,
) -> dict[str, dict[date, float]]:
    """Blend two per-ZCTA-per-period observation tables into one reconciled table."""
    resolved_weights = (weights or ReconciliationWeights()).for_family(family)
    zctas = set(redfin_by_zcta) | set(zillow_by_zcta)
    result: dict[str, dict[date, float]] = {}
    for zcta in zctas:
        redfin_periods = redfin_by_zcta.get(zcta, {})
        zillow_periods = zillow_by_zcta.get(zcta, {})
        periods = set(redfin_periods) | set(zillow_periods)
        for period in periods:
            value = reconcile_value(
                redfin_periods.get(period), zillow_periods.get(period), resolved_weights
            )
            if value is None:
                continue
            result.setdefault(zcta, {})[period] = value
    return result


def build_hex_monthly_series(
    weights_by_hex: Mapping[str, Mapping[str, ZipHexWeight]],
    values_by_zcta_period: ObservationTable,
    intensive: bool,
) -> dict[str, dict[date, float]]:
    """Area-allocate one reconciled per-ZCTA-per-period table onto H3 cells.

    ``intensive=True`` uses the area-weighted-average rule (prices, rates,
    day-on-market counts); ``intensive=False`` uses the proportional-
    allocation rule (homes sold, inventory, pending sales — see
    ``src.producers.redfin_client.INTENSIVE_REDFIN_METRICS`` /
    ``EXTENSIVE_REDFIN_METRICS`` for which Redfin metrics are which).
    A hex with no contributing ZCTA reporting a value that period is simply
    absent from its output series rather than holding a null or zero.
    """
    aggregate = aggregate_intensive if intensive else aggregate_extensive
    all_periods: set = set()
    for periods in values_by_zcta_period.values():
        all_periods.update(periods)

    result: dict[str, dict[date, float]] = {}
    for h3_cell, contributors in weights_by_hex.items():
        for period in all_periods:
            zcta_values = {
                zcta: values_by_zcta_period[zcta][period]
                for zcta in contributors
                if period in values_by_zcta_period.get(zcta, {})
            }
            if not zcta_values:
                continue
            value = aggregate(contributors, zcta_values)
            if value is None:
                continue
            result.setdefault(h3_cell, {})[period] = value
    return result


def momentum_diff(series: Mapping[date, float]) -> dict[date, float]:
    """Month-over-month delta of a per-hex monthly series.

    The input to LIMS momentum differencing: given at least two consecutive
    periods, returns each period's change from the prior one. The first
    period in the series has no prior value and is omitted rather than
    reported as a zero delta.
    """
    ordered_periods: list[date] = sorted(series)
    diffs: dict[date, float] = {}
    for previous, current in itertools.pairwise(ordered_periods):
        diffs[current] = series[current] - series[previous]
    return diffs
