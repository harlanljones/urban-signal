"""Pydantic schemas and data contracts for municipal streams and predictions."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
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


class ViolationEvent(BaseModel):
    """Municipal building / property code-enforcement violation (US-209).

    ISD-style inspection outcomes (unsafe structures, housing code) — a
    signal-family feed distinct from 311 service requests. Never a LIMS input
    without its own ablation study (US-72 family gate)."""

    city_id: str = Field(default="boston")
    violation_id: str = Field(..., description="Unique case / violation number")
    code: str = Field(default="", description="Enforcement code (e.g. 121.2)")
    status: Optional[str] = None
    description: Optional[str] = None
    borough: Optional[str] = None
    address: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    status_date: Optional[datetime] = None
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class InspectionEvent(BaseModel):
    """Municipal food-establishment inspection / licensing outcome (US-209).

    Licensed-business inspection results (result, violation level, license
    category) — a periodic per-license measurement, not a 311 service request.
    Subject to the US-72 ablation rule before any LIMS use."""

    city_id: str = Field(default="boston")
    inspection_id: str = Field(..., description="Unique license / inspection number")
    business_name: Optional[str] = None
    license_category: Optional[str] = None
    license_status: Optional[str] = None
    result: Optional[str] = None
    violation_level: Optional[str] = None
    violation_desc: Optional[str] = None
    borough: Optional[str] = None
    address: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    issued_date: Optional[datetime] = None
    result_date: Optional[datetime] = None
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


class EvictionEvent(BaseModel):
    """NYC Marshal's executed eviction (context/validation only, US-93)."""

    city_id: str = Field(default="nyc")
    eviction_id: str = Field(..., description="Court index / docket number")
    address: Optional[str] = None
    borough: Optional[str] = None
    zipcode: Optional[str] = None
    residential_commercial: Optional[str] = Field(default=None, description="Residential or Commercial")
    executed_date: Optional[datetime] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class ContextObservationEvent(BaseModel):
    """Periodic per-asset context measurement (US-363 §2.7 / §2.8).

    One shape for the whole *context measurement* tier: a building's annual
    energy-benchmarking disclosure and a counter station's daily flow are the
    same kind of fact — a numeric metric attached to a fixed asset for a
    bounded period — and neither is a license, a permit, a deed or a
    complaint. Giving them one typed event instead of one per source is what
    keeps the sweep's new-event budget bounded (§6.3); round two's context
    sources (HRSA sites, IMLS/IPEDS, FRA crossings) reuse it unchanged.

    Never a LIMS term. These are covariates on ``EnrichedH3Feature``, subject
    to the same ablation rule as every other context signal.

    ``value`` is deliberately non-defaulted: an observation with no number is
    not an observation, and the sources encode absence as prose
    (``"Not Available"``, ``"NA"``) that must be dropped upstream rather than
    coerced to 0.0.
    """

    city_id: str = Field(default="nyc")
    observation_id: str = Field(
        ...,
        description="Deterministic id: {source}:{asset_id}:{period}:{metric}",
    )
    source: str = Field(
        ...,
        description="Feed family: energy_benchmark | bike_ped",
    )
    asset_id: str = Field(..., description="Stable per-asset id (building or sensor)")
    asset_name: Optional[str] = None
    metric: str = Field(..., description="Metric name, e.g. site_eui, bike_flow")
    value: float = Field(..., description="Metric value in `unit`")
    unit: Optional[str] = Field(default=None, description="kbtu_per_sqft, score, counts/day, ...")
    period_start: datetime = Field(..., description="Start of the measurement period")
    period_end: Optional[datetime] = Field(default=None, description="End of the measurement period")
    period_type: str = Field(default="year", description="year | month | day | hour")
    category: Optional[str] = Field(default=None, description="Property type / travel mode")
    address: Optional[str] = None
    borough: Optional[str] = None
    source_neighborhood: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class StationChangeEvent(BaseModel):
    """A docked-mobility station appeared or disappeared (US-363 §1.2).

    GBFS station feeds change state **in place**: there is no watermark
    column, and an install or removal is visible only by diffing consecutive
    snapshots of the station set. The event is therefore *detection-dated* —
    ``event_date`` is when we first saw the change, not when the crew bolted
    the dock down — and that bias is a property of the source, not a bug.

    Kept as its own type rather than folded into ``InfrastructureEvent``
    because a bikeshare station carries dock-level state (capacity, docks
    available) that an EV charger or a small cell does not, and because the
    sweep's §6.3 consolidation names it as its own schema.
    """

    city_id: str = Field(default="nyc")
    system_id: str = Field(..., description="GBFS system id, e.g. bkn (Citi Bike)")
    station_id: str = Field(..., description="Operator's station id, unique within the system")
    event_type: str = Field(..., description="station_added | station_removed")
    station_name: Optional[str] = None
    short_name: Optional[str] = None
    capacity: Optional[int] = Field(default=None, ge=0, description="Total docks, when published")
    operator: Optional[str] = Field(default=None, description="Licensed operator, e.g. lyft")
    borough: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    event_date: datetime = Field(..., description="Detection date of the transition")
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class PoiChangeEvent(BaseModel):
    """A business opened or closed, detected from a POI release delta (§1.3).

    Deliberately **not** an ``SLALicenseEvent``. A license is a government
    authorization with an issuing body and a legal effective date; a POI
    detection is a data-vendor observation with a confidence and a release
    date. Conflating them would corrupt the license-based move-in/out
    semantics that the S1 flow features are built on.

    ``event_date`` is the release date, and that is a documented detection
    bias: a vendor's ``date_closed`` is a database date, not the day the
    shutters came down.
    """

    city_id: str = Field(default="nyc")
    poi_id: str = Field(..., description="Native place id from the source")
    source: str = Field(default="fsq", description="fsq | overture | atp | osm")
    event_type: str = Field(..., description="poi_opened | poi_closed")
    name: Optional[str] = None
    category: Optional[str] = None
    category_id: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    release_id: Optional[str] = Field(default=None, description="Source release, e.g. dt=2026-08-11")
    action: Optional[str] = Field(default=None, description="Raw delta action: add|update|remove|merge")
    borough: Optional[str] = None
    address: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    event_date: datetime = Field(..., description="Release date of the delta that revealed the change")
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class AnchorInstitutionEvent(BaseModel):
    """An anchor institution opened, closed or reopened (US-375).

    One shape for the whole *anchor institution* tier — national school churn
    (NCES CCD + EDGE geocodes) today, the Head Start daily feed (US-376)
    tomorrow, which reuses it unchanged via ``category="head_start"`` +
    ``capacity``.

    Latitude/longitude are required: the producer DLQs any directory row the
    EDGE geocode file cannot site, so every emitted event carries geometry.
    """

    city_id: str = Field(default="nyc")
    institution_id: str = Field(..., description="Source's stable id (NCES NCESSCH for schools)")
    source: str = Field(default="nces_ccd", description="nces_ccd | head_start")
    category: str = Field(..., description="school | charter | head_start")
    event_type: str = Field(..., description="opened | closed | reopened")
    name: Optional[str] = None
    address: Optional[str] = None
    zipcode: Optional[str] = None
    capacity: Optional[int] = Field(default=None, ge=0, description="Funded slots (Head Start) / seats (schools) when published")
    status: Optional[str] = Field(default=None, description="Raw source status, e.g. CCD UPDATED_STATUS_TEXT")
    school_year: Optional[str] = Field(default=None, description="Source school year, e.g. 2023-2024")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    event_date: datetime = Field(..., description="CCD EFFECTIVE_DATE (head_start: detection date)")
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)

    @field_validator("category")
    @classmethod
    def _category_vocab(cls, value: str) -> str:
        if value not in ("school", "charter", "head_start"):
            raise ValueError("category must be one of school | charter | head_start")
        return value

    @field_validator("event_type")
    @classmethod
    def _event_type_vocab(cls, value: str) -> str:
        if value not in ("opened", "closed", "reopened"):
            raise ValueError("event_type must be one of opened | closed | reopened")
        return value


class InfrastructureEvent(BaseModel):
    """New fixed infrastructure appeared — a capex proxy (US-363 §1.5, §5).

    The generic-vs-per-family question §5 asks to "decide once" is decided
    here in favour of **generic**: EV chargers, small cells and grid capacity
    additions are the same shape — a dated, sited, countable unit of physical
    plant — and three near-identical schemas would cost three consumers and
    three sets of feature keys for no analytic gain. ``category`` carries the
    family; ``unit_count`` carries whatever the family counts (charging ports,
    antennas, megawatts).

    Bikeshare stations are the deliberate exception (see
    ``StationChangeEvent``): they carry dock-level state this shape has no
    room for.
    """

    city_id: str = Field(default="nyc")
    asset_id: str = Field(..., description="Source's stable id for the asset")
    category: str = Field(..., description="ev_station | small_cell | grid_capacity")
    event_type: str = Field(default="opened", description="opened | closed | expanded")
    name: Optional[str] = None
    operator: Optional[str] = None
    status: Optional[str] = None
    access_type: Optional[str] = Field(default=None, description="public | private | restricted")
    unit_count: Optional[int] = Field(
        default=None, ge=0, description="Ports / antennas / units, per category"
    )
    fast_unit_count: Optional[int] = Field(
        default=None, ge=0, description="DC-fast ports, where the category distinguishes them"
    )
    address: Optional[str] = None
    borough: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    event_date: datetime = Field(..., description="Open date, or first-seen date where absent")
    date_is_detection: bool = Field(
        default=False,
        description="True when event_date is a first-seen date rather than a published open date",
    )
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)


class InsuranceLossEvent(BaseModel):
    """A paid NFIP flood claim — distress context (US-363 §1.4).

    **The published coordinate is not usable for H3.** FEMA truncates claim
    latitude/longitude to 0.1 degrees (~11 km) for privacy — coarser than a
    res-7 hexagon, let alone res-9 — so the raw point can land in the wrong
    city entirely. Tagging goes through ``census_geoid`` (a full block-group
    GEOID, present on the v3 rows) resolved to its tract centroid, with the
    reported ZIP centroid as the fallback. ``geometry_source`` records which
    path produced the tags so a consumer can weight them.

    Context only, and single-direction: flood loss is a distress signal, never
    a LIMS term.
    """

    city_id: str = Field(default="nyc")
    claim_id: str = Field(..., description="FEMA claim id")
    event_date: datetime = Field(..., description="dateOfLoss")
    # NOT constrained to >= 0. NFIP claim payments go negative when a
    # recovery, subrogation or salvage reverses part of an earlier payment —
    # observed live on 2026-08-28 (a NY claim at -8,627.72). Clamping those to
    # zero would overstate paid losses in exactly the hexes with the most
    # complicated claim histories.
    amount_paid_building: float = Field(default=0.0)
    amount_paid_contents: float = Field(default=0.0)
    building_damage_amount: Optional[float] = Field(default=None)
    flood_event: Optional[str] = Field(default=None, description="Named event, e.g. Hurricane Harvey")
    rated_flood_zone: Optional[str] = None
    census_geoid: Optional[str] = None
    county_code: Optional[str] = None
    zipcode: Optional[str] = None
    state: Optional[str] = None
    borough: Optional[str] = None
    occupancy_type: Optional[int] = None
    water_depth: Optional[float] = None
    geometry_source: str = Field(
        default="tract_centroid",
        description="tract_centroid | zip_centroid — never the published lat/lng",
    )
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
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
    # POI release-delta context (US-369). These vendor observations are
    # context-only and intentionally never feed the LIMS formula.
    poi_opened_count_90d: int = Field(default=0)
    poi_closed_count_90d: int = Field(default=0)
    poi_net_churn_90d: int = Field(default=0)
    # NFIP flood-loss distress context (US-370). These fields are deliberately
    # excluded from the LIMS calculation until separately ablated.
    nfip_claim_count_180d: int = Field(default=0)
    nfip_paid_amount_180d: float = Field(default=0.0)
    # Building-stock performance context (US-363 §2.7). Annual cadence, three
    # metros (NYC LL84 / Chicago / Seattle). Means are over the buildings that
    # actually reported the metric — a null disclosure is excluded, never
    # counted as zero. Context only: never a LIMS term.
    energy_site_eui_mean: Optional[float] = Field(default=None)
    energy_star_score_mean: Optional[float] = Field(default=None)
    energy_ghg_intensity_mean: Optional[float] = Field(default=None)
    energy_non_compliant_share: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    energy_low_score_share: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    energy_benchmarked_buildings: int = Field(default=0)
    # Foot/bike traffic vitality context (US-363 §2.8). Daily flow per hex,
    # aggregated from 15-minute (NYC) and hourly (Seattle) counter rows.
    bike_flow_daily_mean: Optional[float] = Field(default=None)
    ped_flow_daily_mean: Optional[float] = Field(default=None)
    counter_sensor_count: int = Field(default=0)
    lims_score: float = Field(default=0.0, description="Leading Indicator Momentum Score [0..100]")
    created_at: datetime = Field(default_factory=_utc_now)


class SbaLoanEvent(BaseModel):
    """An SBA 7(a) or 504 loan approval (US-378).

    Every row in the cumulative FOIA file is inventory. The watermark is the
    file as-of date; there is no per-row watermark. Status repeats across
    program runs for the same LocationID (a 504 PIF and a 7a CHGOFF are
    separate events sharing the borrower address).

    The borrower address is SBA-truncated (up to 49 chars, ending with a
    literal ``.``), so the geocode contract is street-first with a zip+city
    fallback; 504 rows additionally carry ``project_county`` for county-join
    downstream.
    """

    city_id: str = Field(default="national")
    program: str = Field(..., description="504 | 7a")
    location_id: str = Field(..., description="SBA LocationID, float-string normalized to integer digits")
    approval_date: Optional[datetime] = Field(default=None, description="ApprovalDate")
    gross_approval: Optional[float] = Field(default=None, ge=0.0)
    sba_guaranteed_approval: Optional[float] = Field(default=None, ge=0.0)
    naics_sector: Optional[int] = Field(default=None, ge=0, le=99)
    fixed_asset: bool = Field(default=False, description="504 = True (real estate/machinery), 7a = False (working capital)")
    status: Optional[str] = Field(default=None, description="pif | chgoff | exempt | cancld | raw text")
    borrower_name: Optional[str] = None
    borrower_street: Optional[str] = Field(default=None, description="SBA-truncated street (up to 49 chars)")
    borrower_city: Optional[str] = None
    borrower_state: Optional[str] = None
    borrower_zip: Optional[str] = None
    project_county: Optional[str] = Field(default=None, description="504-only: project county for fallback precision")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    as_of_date: Optional[datetime] = Field(default=None, description="File as-of date parsed from the FOIA filename")
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)

    @field_validator("program")
    @classmethod
    def _program_vocab(cls, value: str) -> str:
        if value not in ("504", "7a"):
            raise ValueError(f"program must be one of ('504', '7a'), got {value!r}")
        return value


class BankBranchEvent(BaseModel):
    """A full-service FDIC-insured branch opened or closed (US-379).

    FDIC publishes openings but not an end date. A missing UNINUM in a
    completed locations snapshot is consequently a detection-dated close.
    ``deposits_thousands`` is the latest annual SOD DEPSUMBR value, retained
    as context rather than treated as an event measure.
    """

    city_id: str = Field(default="national")
    branch_id: str = Field(..., description="FDIC UNINUM branch identifier")
    event_type: str = Field(..., description="opened | closed")
    category: str = Field(default="full_service", description="SERVTYPE category")
    institution_cert: Optional[str] = None
    institution_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    county: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    established_date: Optional[datetime] = None
    event_date: datetime
    date_is_detection: bool = False
    deposits_year: Optional[int] = Field(default=None, ge=0)
    deposits_thousands: Optional[float] = Field(default=None, ge=0.0)
    h3_res7: Optional[str] = None
    h3_res8: Optional[str] = None
    h3_res9: Optional[str] = None
    ingested_at: datetime = Field(default_factory=_utc_now)

    @field_validator("event_type")
    @classmethod
    def _event_type_vocab(cls, value: str) -> str:
        if value not in ("opened", "closed"):
            raise ValueError("event_type must be opened or closed")
        return value


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
