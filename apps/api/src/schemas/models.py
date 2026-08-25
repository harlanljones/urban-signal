"""Pydantic schemas and data contracts for municipal streams and predictions."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobType(str, Enum):
    A1 = "A1"  # Major alteration (structural/change in use)
    A2 = "A2"  # Multiple work types, no change in use/occupancy
    A3 = "A3"  # Minor work (curb cuts, scaffolding)
    NB = "NB"  # New Building
    DM = "DM"  # Demolition
    SG = "SG"  # Sign
    OT = "OT"  # Other


class PermitEvent(BaseModel):
    """NYC DOB / Municipal Building Permit Filing Event."""

    city_id: str = Field(default="nyc", description="City identifier")
    job_id: str = Field(..., description="Unique municipal job filing number")
    job_type: JobType = Field(default=JobType.A1, description="Permit type code")
    borough: Optional[str] = Field(default=None, description="Borough or division name")
    source_neighborhood: Optional[str] = Field(default=None, description="Raw source municipal neighborhood string")
    block: Optional[str] = Field(default=None, description="Tax lot block")
    lot: Optional[str] = Field(default=None, description="Tax lot number")
    bbl: Optional[str] = Field(default=None, description="Borough-Block-Lot 10-digit identifier")
    address_street: Optional[str] = None
    address_num: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    estimated_cost: float = Field(default=0.0, ge=0.0, description="Estimated total job cost in USD")
    proposed_dwelling_units: Optional[int] = Field(default=None, ge=0)
    existing_dwelling_units: Optional[int] = Field(default=None, ge=0)
    proposed_stories: Optional[int] = Field(default=None, ge=0)
    filing_date: Optional[datetime] = None
    issuance_date: Optional[datetime] = None
    status: Optional[str] = Field(default="ISSUED")
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)

    @field_validator("estimated_cost", mode="before")
    @classmethod
    def parse_cost(cls, v):
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            clean = v.replace("$", "").replace(",", "").strip()
            try:
                return float(clean)
            except ValueError:
                return 0.0
        return 0.0


class ComplaintCategory(str, Enum):
    NEGLECT = "NEGLECT"  # Structural, Heat/Hot Water, Unsanitary, Water Leak, Lead
    QOL = "QOL"          # Noise, Sidewalk Shed, Dust, Illegal Commercial, Air Quality
    OTHER = "OTHER"


class Complaint311Event(BaseModel):
    """NYC 311 Citizen Maintenance & Quality-of-Life Complaint."""

    city_id: str = Field(default="nyc")
    incident_id: str = Field(..., description="Unique 311 service request ID")
    complaint_type: str = Field(..., description="Agency complaint category")
    descriptor: Optional[str] = None
    category: ComplaintCategory = Field(default=ComplaintCategory.OTHER)
    incident_address: Optional[str] = None
    borough: Optional[str] = None
    source_neighborhood: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    created_date: datetime
    closed_date: Optional[datetime] = None
    status: Optional[str] = "Open"
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class SLALicenseEvent(BaseModel):
    """NY State Liquor Authority / Commercial Hospitality Filing."""

    city_id: str = Field(default="nyc")
    license_id: str = Field(..., description="State SLA License Serial Number")
    license_type: str = Field(..., description="On-Premises, Off-Premises, Wholesale, Club")
    premises_name: Optional[str] = None
    dba: Optional[str] = None
    address: Optional[str] = None
    borough: Optional[str] = None
    source_neighborhood: Optional[str] = None
    # Optional: non-spatial license registries (DC Basic Business Licenses)
    # emit null-coordinate events, mirroring DeedEvent below.
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    license_status: str = Field(default="ACTIVE")
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class DeedEvent(BaseModel):
    """ACRIS Property Deed / Commercial Mortgage Transaction Event."""

    city_id: str = Field(default="nyc")
    doc_id: str = Field(..., description="Unique ACRIS document ID")
    doc_type: str = Field(default="DEED", description="DEED, MTGE, ASST, etc.")
    bbl: Optional[str] = None
    borough: Optional[str] = None
    source_neighborhood: Optional[str] = None
    block: Optional[str] = None
    lot: Optional[str] = None
    document_amount: float = Field(default=0.0, ge=0.0)
    recorded_date: datetime
    party1_grantor: Optional[str] = None
    party2_grantee: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class CrimeEvent(BaseModel):
    """Municipal crime incident (NIBRS-classified)."""

    city_id: str = Field(default="nyc")
    incident_id: str = Field(..., description="Unique incident / offense report number")
    offense_type: str = Field(default="Unknown", description="Offense description (e.g. THEFT, FELONY ASSAULT)")
    # UCR Part-1 vs Part-2 (US-71): carried on the event so the model stage can
    # drop Part-2 noise before the signal ever reaches LIMS. Best-effort
    # keyword classification; NOT itself a LIMS input.
    offense_class: str = Field(default="PART2", description="PART1 (UCR Part-I) or PART2 (everything else)")
    description: Optional[str] = None
    borough: Optional[str] = None
    source_neighborhood: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    occurred_date: Optional[datetime] = None
    reported_date: Optional[datetime] = None
    resolution: Optional[str] = None
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class StreetCutEvent(BaseModel):
    """Street-cut / utility permit / street-closure event (US-81).

    Disruption context signal only: never a fourth term in LIMS. Chicago's
    CDOT street-closure feed is the registered source (native coordinates).
    NYC's DOT street-construction permits stay deferred — current rows are
    address-only (the ``wkt`` State-Plane geometry exists only on 2016-2023
    rows), so they cannot produce H3 events until geocoding lands.
    """

    city_id: str = Field(default="chicago")
    permit_id: str = Field(..., description="Unique permit / application number")
    permit_type: str = Field(default="Unknown", description="Application type (e.g. DOT_PWO)")
    work_type: Optional[str] = Field(default=None, description="Work-type description (e.g. GenOpening)")
    status: Optional[str] = Field(default=None, description="Application status / current milestone")
    street_name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    issued_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    fees: Optional[float] = None
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class EnrichedH3Feature(BaseModel):
    """Spatio-Temporal Aggregated Feature Record per H3 Cell."""

    city_id: str = Field(default="nyc", description="City identifier")
    h3_index: str = Field(..., description="Uber H3 hexagon index string")
    h3_resolution: int = Field(..., ge=7, le=9)
    timestamp: datetime = Field(..., description="Aggregation window timestamp")
    capex_density_decayed: float = Field(default=0.0, description="Time-decayed CapEx per km²")
    permit_count_60d: int = Field(default=0)
    permit_count_180d: int = Field(default=0)
    permit_velocity: float = Field(default=0.0, description="Rate of change in permit filings")
    complaints_neglect_count: int = Field(default=0)
    complaints_qol_count: int = Field(default=0)
    shift_ratio_311: float = Field(default=1.0, description="(QoL + eps) / (Neglect + eps)")
    sla_active_licenses: int = Field(default=0)
    sla_new_filings_90d: int = Field(default=0)
    # S1 license flow signals (US-27): first-seen (move-ins) and closed
    # (move-outs) per hex per 90d window. Ablation-gated — never feed LIMS.
    sla_move_ins_90d: int = Field(default=0)
    sla_move_outs_90d: int = Field(default=0)
    deed_total_volume_180d: float = Field(default=0.0)
    deed_transaction_count_180d: int = Field(default=0)
    lims_score: float = Field(default=0.0, description="Leading Indicator Momentum Score [0..100]")
    created_at: datetime = Field(default_factory=_utc_now)


class CatalystAlert(BaseModel):
    """Catalyst High-Momentum Parcel / Submarket Alert."""

    city_id: str = Field(default="nyc", description="City identifier")
    alert_id: str
    h3_index: str
    h3_resolution: int = 9
    lims_score: float = Field(..., ge=0.0, le=100.0)
    predicted_delta_6m: float = Field(..., description="Predicted 6m price appreciation delta")
    predicted_delta_12m: float = Field(..., description="Predicted 12m appreciation delta")
    macro_outperformance_prob_18m: float = Field(..., description="Probability of >15% outperformance")
    top_catalyst_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    centroid_lat: float
    centroid_lng: float
    timestamp: datetime = Field(default_factory=_utc_now)


class PredictionRequest(BaseModel):
    """Inference request payload."""

    h3_index: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    resolution: int = Field(default=9, ge=7, le=9)
    include_shap: bool = Field(default=True)


class PredictionResponse(BaseModel):
    """Inference response payload."""

    h3_index: str
    resolution: int
    centroid_lat: float
    centroid_lng: float
    lims_score: float
    delta_6m_p10: float
    delta_6m_p50: float
    delta_6m_p90: float
    delta_12m_spillover: float
    prob_18m_macro_outperformance: float
    is_catalyst: bool
    shap_attributions: Optional[Dict[str, float]] = None
    inference_latency_ms: float
