"""311 Citizen Maintenance vs Quality-of-Life complaint shift ratio dynamics."""

from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set, Tuple
import pandas as pd
from src.schemas.models import ComplaintCategory


# Neglect complaints signal legacy structural distress and landlord disinvestment
NEGLECT_COMPLAINT_TYPES: Set[str] = {
    "HEAT/HOT WATER",
    "PLUMBING",
    "WATER LEAK",
    "PAINT/PLASTER",
    "DOOR/WINDOW",
    "ELECTRIC",
    "GENERAL CONSTRUCTION",
    "UNSANITARY CONDITION",
    "RODENT",
    "PESTS",
    "ELEVATOR",
    "STRUCTURAL",
    "SEWAGE",
    "LEAD",
    # Chicago 311 keywords
    "WATER IN BASEMENT",
    "BUILDING VIOLATION",
    "RODENT BAITING",
    "ALLEY LIGHT OUT",
    "STREET LIGHT OUT",
    "POT HOLE",
    "NO HEAT",
    "ABANDONED VEHICLE",
    "SEWAGE BACKUP",
    # San Francisco 311 keywords (Neglect & Infrastructure)
    "BLIGHTED PROPERTIES",
    "DAMAGED PROPERTY",
    "SEWER ISSUES",
    "STREET DEFECTS",
    "SIDEWALK DEFECTS",
    "SIDEWALK OR CURB ISSUES",
    "STREETLIGHTS",
    "STREETLIGHT DAMAGE",
    "ENCAMPMENTS",
    "HOMELESS CONCERNS",
    "POTHOLE",
    "DRAINAGE",
    "SIGN REPAIR",
    "INFRASTRUCTURE",
}

# Quality of Life (QoL) complaints signal demographic transition, active retail, and commercial activity
QOL_COMPLAINT_TYPES: Set[str] = {
    "NOISE - RESIDENTIAL",
    "NOISE - COMMERCIAL",
    "NOISE - STREET/SIDEWALK",
    "NOISE - PARK",
    "NOISE",
    "SIDEWALK SHED",
    "SCAFFOLDING SAFETY",
    "AIR QUALITY",
    "DUST",
    "ILLEGAL TREE DAMAGE",
    "OUTDOOR DINING",
    "DIRTY CONDITIONS",
    "SIDEWALK CONDITION",
    # Chicago 311 keywords
    "GRAFFITI REMOVAL",
    "RESTAURANT NOISE",
    "SPECIAL EVENT",
    "SIDEWALK CAFE",
    "OUTDOOR PATIO",
    "CONSTRUCTION DUST",
    "TREE TRIMMING",
    "FLY DUMPING",
    # San Francisco 311 keywords (Noise, Commercial, Cleanliness, Public Safety QoL)
    "STREET AND SIDEWALK CLEANING",
    "STREET CLEANING",
    "ILLEGAL POSTINGS",
    "NOISE REPORT",
    "COMMERCIAL",
    "TREE MAINTENANCE",
    "BLOCKED PEDESTRIAN WALKWAY",
    "PUBLIC SAFETY",
}


class ComplaintShiftDynamics:
    """Calculates the 311 Complaint Shift Dynamics Ratio.
    
    Formula:
        Delta R_311 = (C_QoL + epsilon) / (C_neglect + epsilon)
    where:
        C_neglect = structural landlord neglect complaints (heat, water, pests, structural)
        C_QoL = quality of life complaints (noise, sidewalk sheds, dust, commercial activity)
        epsilon = smoothing parameter to prevent division by zero (default 1.0)
    """

    def __init__(self, epsilon: float = 1.0):
        self.epsilon = epsilon

    @classmethod
    def classify_complaint_type(cls, complaint_type: str) -> ComplaintCategory:
        """Classify raw municipal complaint type into NEGLECT, QOL, or OTHER."""
        normalized = (complaint_type or "").upper().strip()
        for neglect_kw in NEGLECT_COMPLAINT_TYPES:
            if neglect_kw in normalized:
                return ComplaintCategory.NEGLECT
        for qol_kw in QOL_COMPLAINT_TYPES:
            if qol_kw in normalized:
                return ComplaintCategory.QOL
        return ComplaintCategory.OTHER

    def calculate_ratio(self, count_qol: int, count_neglect: int) -> float:
        """Calculate the shift dynamics ratio."""
        return (float(count_qol) + self.epsilon) / (float(count_neglect) + self.epsilon)

    def calculate_ratio_delta(
        self,
        recent_qol: int,
        recent_neglect: int,
        prior_qol: int,
        prior_neglect: int,
    ) -> Tuple[float, float, float]:
        """Calculate recent ratio, baseline ratio, and acceleration delta.
        
        Returns:
            (recent_ratio, prior_ratio, acceleration_delta)
        """
        r_recent = self.calculate_ratio(recent_qol, recent_neglect)
        r_prior = self.calculate_ratio(prior_qol, prior_neglect)
        delta = r_recent - r_prior
        return r_recent, r_prior, delta
