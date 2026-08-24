"""Exponential time-decay CapEx density calculations according to prospectus mathematical formulation."""

import math
from datetime import datetime, timezone
from typing import Iterable, List, Sequence, Tuple, Union
import numpy as np
import pandas as pd


class TimeDecayedCapExCalculator:
    """Calculates time-decayed municipal capital expenditure density.
    
    Formula:
        CapEx_Density(h, t) = (1 / Area(h)) * SUM_i [ Cost_i * exp(-lambda * (t - t_i)) ]
        where lambda = ln(2) / halflife_days (default 180 days)
    """

    def __init__(self, halflife_days: float = 180.0):
        self.halflife_days = halflife_days
        self.decay_constant = math.log(2.0) / self.halflife_days

    def calculate_decay_weight(self, current_date: datetime, event_date: datetime) -> float:
        """Calculate single event exponential weight exp(-lambda * delta_days)."""
        delta_days = (current_date - event_date).total_seconds() / 86400.0
        if delta_days < 0:
            # Future event protection
            return 1.0
        return math.exp(-self.decay_constant * delta_days)

    def compute_cell_capex_density(
        self,
        permits: Sequence[Tuple[float, datetime]],  # list of (cost, issuance_date)
        cell_area_km2: float,
        as_of_date: datetime,
    ) -> float:
        """Calculate total decayed CapEx per square kilometer for a single H3 cell."""
        if not permits or cell_area_km2 <= 0:
            return 0.0

        decayed_sum = sum(
            cost * self.calculate_decay_weight(as_of_date, dt)
            for cost, dt in permits
            if cost > 0 and dt <= as_of_date
        )

        return decayed_sum / cell_area_km2

    def compute_batch_decay(
        self,
        df: pd.DataFrame,
        cost_col: str = "estimated_cost",
        date_col: str = "issuance_date",
        cell_area_km2: float = 0.1053,
        as_of_date: Union[str, datetime] = None,
    ) -> float:
        """Vectorized computation for a dataframe of permit filings."""
        if df.empty:
            return 0.0

        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc)
        else:
            as_of_date = pd.to_datetime(as_of_date, utc=True)

        dates = pd.to_datetime(df[date_col], utc=True)
        delta_days = (as_of_date - dates).dt.total_seconds() / 86400.0
        valid_mask = delta_days >= 0

        if not valid_mask.any():
            return 0.0

        weights = np.exp(-self.decay_constant * np.maximum(delta_days[valid_mask].to_numpy(), 0.0))
        costs = df.loc[valid_mask, cost_col].fillna(0.0).to_numpy()

        decayed_total = np.sum(costs * weights)
        return float(decayed_total / cell_area_km2)
