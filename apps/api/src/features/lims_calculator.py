"""Leading Indicator Momentum Score (LIMS) calculation according to prospectus formula."""

import math
from typing import Dict, Optional, Tuple
import numpy as np


class LIMSCalculator:
    """Computes the Leading Indicator Momentum Score (LIMS).
    
    Formula:
        LIMS_h = alpha * Z(CapEx_h) + beta * Z(PermitVelocity_h) + gamma * Z(DeltaRatio_311_h) + delta * Z(Lic_SLA_h)
        
    Default weights:
        alpha = 0.35 (CapEx Density)
        beta  = 0.25 (Permit Velocity / acceleration)
        gamma = 0.20 (311 Shift Dynamics Ratio)
        delta = 0.20 (SLA Hospitality activations)
    """

    def __init__(
        self,
        alpha: float = 0.35,
        beta: float = 0.25,
        gamma: float = 0.20,
        delta: float = 0.20,
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta

    @staticmethod
    def _z_score(val: float, mean: float, std: float) -> float:
        """Compute standard normal Z-score with division by zero protection."""
        if std <= 1e-6:
            return 0.0
        return (val - mean) / std

    def compute_raw_score(
        self,
        capex: float,
        permit_velocity: float,
        shift_ratio_311: float,
        sla_activations: float,
        baselines: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> float:
        """Compute raw weighted linear combination of Z-scores.
        
        baselines: dict mapping feature -> (mean, std)
        """
        if baselines is None:
            # Standard default NYC urban distribution baselines
            baselines = {
                "capex": (50000.0, 150000.0),
                "permit_velocity": (0.05, 0.25),
                "shift_ratio": (1.0, 1.5),
                "sla_activations": (1.0, 3.0),
            }

        z_capex = self._z_score(capex, *baselines.get("capex", (0.0, 1.0)))
        z_perm = self._z_score(permit_velocity, *baselines.get("permit_velocity", (0.0, 1.0)))
        z_shift = self._z_score(shift_ratio_311, *baselines.get("shift_ratio", (1.0, 1.0)))
        z_sla = self._z_score(sla_activations, *baselines.get("sla_activations", (0.0, 1.0)))

        score = (
            self.alpha * z_capex
            + self.beta * z_perm
            + self.gamma * z_shift
            + self.delta * z_sla
        )
        return float(score)

    def compute_scaled_lims(
        self,
        capex: float,
        permit_velocity: float,
        shift_ratio_311: float,
        sla_activations: float,
        baselines: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> float:
        """Compute LIMS normalized to 0.0 to 100.0 range via standard sigmoid projection."""
        raw_score = self.compute_raw_score(
            capex=capex,
            permit_velocity=permit_velocity,
            shift_ratio_311=shift_ratio_311,
            sla_activations=sla_activations,
            baselines=baselines,
        )

        # Map standard normal-ish sum into [0, 100] using logistic function
        # A raw_score of 0 (average) -> 50.0. Raw score +2.5 -> ~92.4
        scaled = 100.0 / (1.0 + math.exp(-raw_score))
        return round(float(scaled), 2)
