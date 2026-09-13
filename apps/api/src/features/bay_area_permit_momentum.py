"""Bay Area permit momentum features, per H3 res-9 hex (US-441).

Three derived features distinct from the shared national LIMS pipeline
(``src.features.pipeline.SpatialFeaturePipeline.compute_h3_cell_features``,
which already computes its own differently-defined ``permit_velocity`` /
``capex_density_decayed`` at a 180-day half-life and feeds every registered
city's LIMS score). Reusing that formula here would silently change every
city's existing score, so this module is a standalone leaf that reuses the
underlying decay math (:class:`~src.features.time_decay.TimeDecayedCapExCalculator`)
without touching the shared pipeline:

* ``permit_velocity_60_180`` — 60-day count over a third of the 180-day
  count (a straight per-60-day-window acceleration ratio, distinct from the
  national pipeline's z-score-friendly "excess over baseline" ratio).
* ``capex_density_decayed`` — sum(cost * e^(-lambda * dt)) / cell_area, with
  a configurable half-life defaulting to 60 days (``lambda = ln(2) /
  halflife_days``), rather than the national pipeline's 180-day default.
* ``residential_unit_delta`` — proposed_units - existing_units, a net-new
  -housing signal.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from src.features.time_decay import TimeDecayedCapExCalculator

DEFAULT_HALFLIFE_DAYS = 60.0


def permit_velocity_60_180(count_60d: int, count_180d: int) -> float:
    """Acceleration ratio: 60-day count / (180-day count / 3).

    The 180-day count is divided into three 60-day-equivalent buckets so the
    numerator and the baseline are directly comparable rates. A cell with no
    180-day history (``count_180d == 0``) has no baseline to accelerate
    against; it returns 0.0 rather than dividing by zero or inflating to
    infinity.
    """
    if count_180d <= 0:
        return 0.0
    baseline = count_180d / 3.0
    return float(count_60d) / baseline


def compute_capex_density_decayed(
    permits: Iterable[tuple[float, Any]],
    cell_area_km2: float,
    as_of_date: datetime | None = None,
    halflife_days: float = DEFAULT_HALFLIFE_DAYS,
) -> float:
    """Exponentially-decayed CapEx density for one hex, at a configurable half-life.

    ``permits`` is an iterable of ``(cost, issuance_date)`` pairs, matching
    :meth:`TimeDecayedCapExCalculator.compute_cell_capex_density`. Defaults to
    a 60-day half-life per US-441 (the shared national pipeline's default
    remains 180 days and is untouched by this module).
    """
    if as_of_date is None:
        as_of_date = datetime.now(UTC)
    calculator = TimeDecayedCapExCalculator(halflife_days=halflife_days)
    return calculator.compute_cell_capex_density(list(permits), cell_area_km2, as_of_date)


def residential_unit_delta(proposed_units: Any, existing_units: Any) -> int | None:
    """Net new housing units: proposed - existing.

    Returns ``None`` when neither value is available (no residential-unit
    signal on this permit), treating a missing side of a known value as 0
    (e.g. a new-construction permit with ``existing_units`` absent implies
    zero prior units on the parcel).
    """
    if proposed_units is None and existing_units is None:
        return None
    proposed = int(proposed_units) if proposed_units is not None else 0
    existing = int(existing_units) if existing_units is not None else 0
    return proposed - existing


def compute_bay_area_permit_hex_features(
    permits_df: pd.DataFrame,
    h3_index: str,
    h3_col: str = "h3_res9",
    cost_col: str = "estimated_cost",
    date_col: str = "issuance_date",
    proposed_units_col: str = "proposed_dwelling_units",
    existing_units_col: str = "existing_dwelling_units",
    cell_area_km2: float = 0.1053,
    as_of_date: datetime | None = None,
    halflife_days: float = DEFAULT_HALFLIFE_DAYS,
) -> Mapping[str, Any]:
    """Compute all three US-441 momentum features for one hex from a permits frame.

    ``permits_df`` holds every jurisdiction's normalized permit rows (already
    geocoded/H3-assigned — see ``geocode_row_if_declared`` and
    ``H3SpatialIndexer``), filtered to a single ``h3_col`` value by the
    caller's cell loop. Rows with a null ``date_col`` are excluded from every
    windowed count so a permit still awaiting an issuance date does not
    silently count toward velocity or CapEx.
    """
    if as_of_date is None:
        as_of_date = datetime.now(UTC)

    cell_rows = permits_df[permits_df[h3_col] == h3_index] if h3_col in permits_df.columns else permits_df.iloc[0:0]
    dates = pd.to_datetime(cell_rows.get(date_col), utc=True, errors="coerce") if not cell_rows.empty else pd.Series(dtype="datetime64[ns, UTC]")
    valid = cell_rows.loc[dates.notna()].copy()
    valid["_dt"] = dates.loc[dates.notna()]

    as_of_ts = pd.Timestamp(as_of_date)
    if as_of_ts.tzinfo is None:
        as_of_ts = as_of_ts.tz_localize("UTC")

    delta_days = (as_of_ts - valid["_dt"]).dt.total_seconds() / 86400.0
    count_60d = int(((delta_days >= 0) & (delta_days <= 60)).sum())
    count_180d = int(((delta_days >= 0) & (delta_days <= 180)).sum())

    permits_pairs = [
        (float(cost) if cost is not None else 0.0, dt.to_pydatetime())
        for cost, dt in zip(valid.get(cost_col, pd.Series(dtype=float)), valid["_dt"])
    ]
    capex_density = compute_capex_density_decayed(
        permits_pairs, cell_area_km2, as_of_date, halflife_days=halflife_days
    )

    total_proposed = valid.get(proposed_units_col)
    total_existing = valid.get(existing_units_col)
    unit_delta = residential_unit_delta(
        total_proposed.sum() if total_proposed is not None and total_proposed.notna().any() else None,
        total_existing.sum() if total_existing is not None and total_existing.notna().any() else None,
    )

    return {
        "h3_index": h3_index,
        "as_of_date": as_of_date,
        "permit_count_60d": count_60d,
        "permit_count_180d": count_180d,
        "permit_velocity_60_180": round(permit_velocity_60_180(count_60d, count_180d), 4),
        "capex_density_decayed": round(capex_density, 2),
        "capex_halflife_days": halflife_days,
        "residential_unit_delta": unit_delta,
    }
