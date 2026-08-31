GEOCODE_CONTEXT = "Virginia Beach, VA"

PERMITS_FIELD_MAP = {
    "job_id": ["PermitNumber", "OBJECTID"],
    "job_type": ["WorkType", "PermitType"],
    "issuance_date": ["IssueDate"],
    "filing_date": ["ApplicationDate"],
    "address_street": ["StreetAddress"],
    "bbl": ["GPIN"],
    "borough": ["City"],
    "zipcode": ["Zip"],
}

SLA_FIELD_MAP = {
    "license_id": ["Trade_Name", "Owner_Name", "Business_Address"],
    "dba": ["Trade_Name"],
    "premises_name": ["Owner_Name"],
    "license_type": ["Business_Classification", "NAICS"],
    "effective_date": ["Begin_Date"],
    "address_street": ["Business_Address"],
    "borough": ["Business_City"],
    "zipcode": ["Business_ZipCode"],
}

DEEDS_FIELD_MAP = {
    "doc_id": ["Document_Number", "OBJECTID"],
    "bbl": ["GPIN"],
    "document_amount": ["Sale_Price"],
    "recorded_date": ["Sales_Date"],
    "address_street": ["Street_Address"],
    "incident_address": ["Street_Address"],
    "borough": ["Neighborhood"],
    "zipcode": ["Zip_Code"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

DROPPED_PII_COLUMNS = (
    "Telephone",
    "Mailing_Address",
    "Mailing_City",
    "Mailing_State",
    "Mailing_Zip_Code",
    "Mailing_ZipCode_Ext",
)

"""Virginia Beach Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the independent City of
Virginia Beach, VA (Hampton Roads — not a division of any county, and not
Norfolk/Chesapeake, whose sibling leaf boxes this module deliberately avoids
overlapping beyond shared water edges).

Feed scope (probed 2026-08-27/28, docs/research/probe-virginia_beach.md;
re-probed live 2026-08-27 at implementation). All three feeds are hosted
ArcGIS tables on the city AGOL org ``CyVvlIiUfRBmMQuu`` behind the
data.virginiabeach.gov Hub — existing ``ArcGISClient``, no fifth client:

* PERMITS — ``Building_Permits_Applications_view/FeatureServer/0`` (table).
  Watermark ``IssueDate`` TEXT ``YYYY/MM/DD`` (ADR 0005). Register the view,
  not the monthly-refresh joined point mirror ``Building_Permits`` (lags to
  2026-07-31). 7d=247 at re-probe — live, daily.
* SLA — ``Business_Licenses_view/FeatureServer/0`` (table). Watermark
  ``Begin_Date`` TEXT ``MM/DD/YYYY``; volume is an annual-license trickle.
  LEXICAL-SORT TRAP: ``ORDER BY Begin_Date DESC`` ranks "12/31/2025" above
  "07/31/2026" — watermark windows must use the declared-format typed
  comparison, never a naive DESC first row. ``Telephone`` and the mailing
  block are PII and dropped at the field map.
* DEEDS — ``Property_Sales_/FeatureServer/0`` — a TABLE (the probe's
  "native points" note is stale; live service exposes no point layer).
  Watermark ``Sales_Date`` is date-typed (epoch ms on the wire, ISO after
  flatten). BATCH CADENCE CAVEAT: publication lands every ~2-3 weeks
  (7d=0 / 60d=1,474 at re-probe); register ``expected_cadence_days=14``
  and treat as stalled if no rows land by mid-September. ``Sale_Price=0``
  non-arms-length transfers are kept.

All three feeds are address-only live (no server-side geometry on any of
them), so every spec declares ``needs_geocode=True`` (ADR 0004); the GPIN
parcel key is the T1 upgrade path. COMPLAINTS_311 is absent: VB 311 is a
phone/app service with no published CRM extract — do not register.

Implementation re-probe (2026-08-28, live, all three watermarks confirmed):
PERMITS newest IssueDate 2026/08/21, total 105,454, strict 7d window
(>=2026/08/20) 247, 60d 4,790. SLA newest Begin_Date 07/31/2026, total
41,646, zero Aug-Dec 2026 rows; typed-2026 total is 2,862 — the probe's
"2026 YTD 77" was only the newest-cohort window, not true YTD. DEEDS newest
Sales_Date 2026-08-10, total 594,771, 7d=0 / 60d=1,474 (batch not yet
landed; inside the probe's mid-September stall watch). SLA max-OBJECTID rows
carry 2019-2025 Begin_Dates — OBJECTID DESC is NOT a viable watermark
ordering; the declared ``%m/%d/%Y`` typed window is mandatory (ADR 0005).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

VIRGINIA_BEACH_CITY_ID: str = "virginia_beach"
VIRGINIA_BEACH_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Independent-city bbox. The Atlantic (Cape Henry) is the east edge, the
# North Carolina line the south edge, the Chesapeake line the west edge.
# West edge is clipped at -76.22 so the box does not claim Norfolk's Ocean
# View / Willoughby or Portsmouth; the resort strip, Kempsville, and Town
# Center must all sit inside.
VIRGINIA_BEACH_METRO_BBOX: Dict[str, float] = {
    "min_lat": 36.54,
    "max_lat": 36.96,
    "min_lng": -76.22,
    "max_lng": -75.91,
}

# Registration-contract center: Virginia Beach Town Center (the modern CBD).
VIRGINIA_BEACH_CENTER: Dict[str, float] = {"lat": 36.8528, "lng": -76.1089}

# 5 Virginia Beach Division Bounding Boxes (strictly nested inside the metro bbox)
VIRGINIA_BEACH_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "RESORT_AREA":          {"min_lat": 36.83, "max_lat": 36.95, "min_lng": -76.00, "max_lng": -75.91},
    "TOWN_CENTER":          {"min_lat": 36.82, "max_lat": 36.90, "min_lng": -76.14, "max_lng": -76.07},
    "KEMPSVILLE":           {"min_lat": 36.75, "max_lat": 36.86, "min_lng": -76.22, "max_lng": -76.10},
    "BAYSIDE_GREAT_NECK":   {"min_lat": 36.86, "max_lat": 36.96, "min_lng": -76.20, "max_lng": -76.10},
    "PUNGO_PRINCESS_ANNE":  {"min_lat": 36.54, "max_lat": 36.78, "min_lng": -76.14, "max_lng": -75.91},
}


def is_in_virginia_beach_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Virginia Beach metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        VIRGINIA_BEACH_METRO_BBOX["min_lat"] <= lat <= VIRGINIA_BEACH_METRO_BBOX["max_lat"]
        and VIRGINIA_BEACH_METRO_BBOX["min_lng"] <= lng <= VIRGINIA_BEACH_METRO_BBOX["max_lng"]
    )


def is_in_virginia_beach(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_virginia_beach_metro`."""
    return is_in_virginia_beach_metro(lat, lng)


# ---------------------------------------------------------------------------
# Virginia Beach Submarket Registry (15 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

VIRGINIA_BEACH_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # RESORT_AREA (3 Submarkets)
    # =======================================================================
    "Oceanfront Resort District": SubmarketMeta(
        name="Oceanfront Resort District",
        borough="RESORT_AREA",
        lat=36.8529,
        lng=-75.9780,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.90,
        capex=9200000.0,
        permit_vel=52.0,
        shift_ratio=1.60,
        sla=68.0,
        description="Atlantic Avenue hotel-and-entertainment strip between Rudee Inlet and 40th Street with relentless hotel renovation and height-driven permitting.",
        city_id="virginia_beach",
    ),
    "North End & Cape Henry": SubmarketMeta(
        name="North End & Cape Henry",
        borough="RESORT_AREA",
        lat=36.9100,
        lng=-75.9880,
        zoom=14.5,
        pitch=40.0,
        base_lims=0.88,
        capex=8100000.0,
        permit_vel=38.0,
        shift_ratio=1.50,
        sla=62.0,
        description="Guarded residential beach enclave of shingle-style homes from 52nd to 88th Street with teardown-and-rebuild pressure on oceanfront lots.",
        city_id="virginia_beach",
    ),
    "Cavalier Beach": SubmarketMeta(
        name="Cavalier Beach",
        borough="RESORT_AREA",
        lat=36.8890,
        lng=-75.9790,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.86,
        capex=7400000.0,
        permit_vel=34.0,
        shift_ratio=1.46,
        sla=58.0,
        description="Cavalier Hotel and Cardinal Road district mixing landmark-hotel restoration with premium condo infill at the North End gate.",
        city_id="virginia_beach",
    ),
    # =======================================================================
    # TOWN_CENTER (3 Submarkets)
    # =======================================================================
    "Virginia Beach Town Center": SubmarketMeta(
        name="Virginia Beach Town Center",
        borough="TOWN_CENTER",
        lat=36.8528,
        lng=-76.1089,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.91,
        capex=11800000.0,
        permit_vel=56.0,
        shift_ratio=1.64,
        sla=72.0,
        description="The city's planned high-rise CBD around Pembroke Avenue and Constitution Drive with office towers, a Westin anchor, and the densest commercial pipeline.",
        city_id="virginia_beach",
    ),
    "Pembroke / Independence": SubmarketMeta(
        name="Pembroke / Independence",
        borough="TOWN_CENTER",
        lat=36.8610,
        lng=-76.1290,
        zoom=14.5,
        pitch=40.0,
        base_lims=0.84,
        capex=6800000.0,
        permit_vel=40.0,
        shift_ratio=1.44,
        sla=56.0,
        description="Independence Boulevard office-and-retail spine north of Town Center absorbing older strip parcels into mixed-use redevelopment.",
        city_id="virginia_beach",
    ),
    "Lynnhaven Mall District": SubmarketMeta(
        name="Lynnhaven Mall District",
        borough="TOWN_CENTER",
        lat=36.8450,
        lng=-76.1280,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.80,
        capex=5900000.0,
        permit_vel=36.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Regional-mall retail core at Virginia Beach Blvd and Independence with outparcel medical and hospitality refits.",
        city_id="virginia_beach",
    ),
    # =======================================================================
    # KEMPSVILLE (3 Submarkets)
    # =======================================================================
    "Kempsville": SubmarketMeta(
        name="Kempsville",
        borough="KEMPSVILLE",
        lat=36.8200,
        lng=-76.1750,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.76,
        capex=4800000.0,
        permit_vel=32.0,
        shift_ratio=1.30,
        sla=48.0,
        description="Mature residential crossroads at Kempsville Road and Providence Road with steady additions, roof-and-HVAC trades, and neighborhood retail.",
        city_id="virginia_beach",
    ),
    "Princess Anne Plaza": SubmarketMeta(
        name="Princess Anne Plaza",
        borough="KEMPSVILLE",
        lat=36.7980,
        lng=-76.1300,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.72,
        capex=3900000.0,
        permit_vel=26.0,
        shift_ratio=1.22,
        sla=42.0,
        description="Post-war plaza-and-ranch grid near the Municipal Center with municipal-adjacent services and investor renovation flow.",
        city_id="virginia_beach",
    ),
    "Indian Lakes": SubmarketMeta(
        name="Indian Lakes",
        borough="KEMPSVILLE",
        lat=36.8250,
        lng=-76.1400,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.74,
        capex=4100000.0,
        permit_vel=28.0,
        shift_ratio=1.26,
        sla=44.0,
        description="Golf-course community of lakeside colonials east of Kempsville with kitchen-and-deck renovation demand.",
        city_id="virginia_beach",
    ),
    # =======================================================================
    # BAYSIDE_GREAT_NECK (3 Submarkets)
    # =======================================================================
    "Shore Drive Corridor": SubmarketMeta(
        name="Shore Drive Corridor",
        borough="BAYSIDE_GREAT_NECK",
        lat=36.9050,
        lng=-76.1550,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.82,
        capex=5600000.0,
        permit_vel=38.0,
        shift_ratio=1.42,
        sla=54.0,
        description="Chesapeake Bay resort corridor from Lynnhaven Inlet to First Landing State Park with condo-repurposing and restaurant-row licensing.",
        city_id="virginia_beach",
    ),
    "Bayside & Little Neck": SubmarketMeta(
        name="Bayside & Little Neck",
        borough="BAYSIDE_GREAT_NECK",
        lat=36.8850,
        lng=-76.1500,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.72,
        capex=3700000.0,
        permit_vel=26.0,
        shift_ratio=1.24,
        sla=40.0,
        description="Working residential grid between Shore Drive and Independence with starter-stock turnover and accessory-dwelling interest.",
        city_id="virginia_beach",
    ),
    "Great Neck": SubmarketMeta(
        name="Great Neck",
        borough="BAYSIDE_GREAT_NECK",
        lat=36.8950,
        lng=-76.1150,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.84,
        capex=6200000.0,
        permit_vel=34.0,
        shift_ratio=1.46,
        sla=58.0,
        description="Affluent peninsula of school-adjacent subdivisions and Deep Creek estates with high-value addition permitting.",
        city_id="virginia_beach",
    ),
    # =======================================================================
    # PUNGO_PRINCESS_ANNE (3 Submarkets)
    # =======================================================================
    "Princess Anne Commons": SubmarketMeta(
        name="Princess Anne Commons",
        borough="PUNGO_PRINCESS_ANNE",
        lat=36.7750,
        lng=-76.0600,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=40.0,
        shift_ratio=1.40,
        sla=50.0,
        description="Institutional growth node at the Aquarium and Sportsplex with the city's newest tract-housing and medical-office clusters.",
        city_id="virginia_beach",
    ),
    "Pungo": SubmarketMeta(
        name="Pungo",
        borough="PUNGO_PRINCESS_ANNE",
        lat=36.7000,
        lng=-76.0100,
        zoom=13.0,
        pitch=30.0,
        base_lims=0.62,
        capex=2900000.0,
        permit_vel=22.0,
        shift_ratio=1.18,
        sla=34.0,
        description="Rural-agricultural flats of field roads and farmettes under aggressive-by-right estate-lot conversion pressure.",
        city_id="virginia_beach",
    ),
    "Sandbridge": SubmarketMeta(
        name="Sandbridge",
        borough="PUNGO_PRINCESS_ANNE",
        lat=36.6468,
        lng=-75.9290,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.70,
        capex=4600000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=38.0,
        description="Barrier-island village of rental cottages and dune-line houses at the North Carolina line with storm-rebuild and elevation work.",
        city_id="virginia_beach",
    ),
}


# ---------------------------------------------------------------------------
# Virginia Beach Divisions Catalog
# ---------------------------------------------------------------------------

VIRGINIA_BEACH_DIVISIONS: Dict[str, BoroughMeta] = {
    "RESORT_AREA": BoroughMeta(
        name="RESORT_AREA",
        center_lat=36.8850,
        center_lng=-75.9650,
        zoom=13.0,
        bbox=VIRGINIA_BEACH_DIVISION_BBOXES["RESORT_AREA"],
        submarkets=[k for k, v in VIRGINIA_BEACH_SUBMARKETS.items() if v.borough == "RESORT_AREA"],
        city_id="virginia_beach",
    ),
    "TOWN_CENTER": BoroughMeta(
        name="TOWN_CENTER",
        center_lat=36.8550,
        center_lng=-76.1089,
        zoom=13.5,
        bbox=VIRGINIA_BEACH_DIVISION_BBOXES["TOWN_CENTER"],
        submarkets=[k for k, v in VIRGINIA_BEACH_SUBMARKETS.items() if v.borough == "TOWN_CENTER"],
        city_id="virginia_beach",
    ),
    "KEMPSVILLE": BoroughMeta(
        name="KEMPSVILLE",
        center_lat=36.8150,
        center_lng=-76.1650,
        zoom=13.0,
        bbox=VIRGINIA_BEACH_DIVISION_BBOXES["KEMPSVILLE"],
        submarkets=[k for k, v in VIRGINIA_BEACH_SUBMARKETS.items() if v.borough == "KEMPSVILLE"],
        city_id="virginia_beach",
    ),
    "BAYSIDE_GREAT_NECK": BoroughMeta(
        name="BAYSIDE_GREAT_NECK",
        center_lat=36.8950,
        center_lng=-76.1400,
        zoom=13.0,
        bbox=VIRGINIA_BEACH_DIVISION_BBOXES["BAYSIDE_GREAT_NECK"],
        submarkets=[k for k, v in VIRGINIA_BEACH_SUBMARKETS.items() if v.borough == "BAYSIDE_GREAT_NECK"],
        city_id="virginia_beach",
    ),
    "PUNGO_PRINCESS_ANNE": BoroughMeta(
        name="PUNGO_PRINCESS_ANNE",
        center_lat=36.7100,
        center_lng=-76.0200,
        zoom=12.0,
        bbox=VIRGINIA_BEACH_DIVISION_BBOXES["PUNGO_PRINCESS_ANNE"],
        submarkets=[k for k, v in VIRGINIA_BEACH_SUBMARKETS.items() if v.borough == "PUNGO_PRINCESS_ANNE"],
        city_id="virginia_beach",
    ),
}

VB_DIVISION_BBOXES = VIRGINIA_BEACH_DIVISION_BBOXES
VB_SUBMARKETS = VIRGINIA_BEACH_SUBMARKETS
VB_DIVISIONS = VIRGINIA_BEACH_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27/28 and re-probed live 2026-08-27 against AGOL org
# CyVvlIiUfRBmMQuu (data.virginiabeach.gov Hub). Sketch matches
# docs/research/probe-virginia_beach.md with two live corrections: the
# Property_Sales_ service exposes a TABLE (no point layer), and SLA
# ordering must be typed (MM/DD/YYYY text sorts lexically).
# ---------------------------------------------------------------------------
VIRGINIA_BEACH_PERMITS_ENDPOINT = (
    "https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services/"
    "Building_Permits_Applications_view/FeatureServer/0"
)
VIRGINIA_BEACH_SLA_ENDPOINT = (
    "https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services/"
    "Business_Licenses_view/FeatureServer/0"
)
VIRGINIA_BEACH_DEEDS_ENDPOINT = (
    "https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services/"
    "Property_Sales_/FeatureServer/0"
)

VIRGINIA_BEACH_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": VIRGINIA_BEACH_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "IssueDate",
        "id_keys": ["PermitNumber", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "needs_geocode": True,
            "geocode_context": VIRGINIA_BEACH_GEOCODE_CONTEXT,
            "watermark_type": "text",
            "watermark_format": "%Y/%m/%d",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "expected_cadence_days": 1,
            "non_spatial": True,
            "scope": (
                "Virginia Beach building-permit applications table "
                "(text YYYY/MM/DD watermark, ADR-0005). Address-only; GPIN "
                "is the T1 parcel-join path. Register the view, not the "
                "monthly joined point mirror."
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": VIRGINIA_BEACH_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Begin_Date",
        "id_keys": ["Trade_Name", "Owner_Name", "Business_Address"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "needs_geocode": True,
            "geocode_context": VIRGINIA_BEACH_GEOCODE_CONTEXT,
            "watermark_type": "text",
            "watermark_format": "%m/%d/%Y",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "expected_cadence_days": 365,
            "non_spatial": True,
            "scope": (
                "Virginia Beach business licenses (annual-license cadence; "
                "no license-number column, id falls back to trade/owner/"
                "address). Text MM/DD/YYYY watermark sorts lexically — "
                "typed comparison required. Telephone and mailing block "
                "dropped at ingest (PII)."
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "deeds": {
        "endpoint": VIRGINIA_BEACH_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Sales_Date",
        "id_keys": ["Document_Number", "GPIN", "Sales_Date"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            "needs_geocode": True,
            "geocode_context": VIRGINIA_BEACH_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "expected_cadence_days": 14,
            "non_spatial": True,
            "scope": (
                "Virginia Beach property-sales TABLE (Memphis monthly-"
                "cadence precedent). BATCH PUBLICATION every ~2-3 weeks: "
                "7d=0 / 60d=1,474 at the 2026-08-27 re-probe with newest "
                "row 2026-08-10 — re-probe within 72h of any spine or "
                "schedule change and treat as stalled if no rows land by "
                "mid-September. Sale_Price=0 non-arms-length transfers "
                "kept. Address-only (no server-side geometry); GPIN is "
                "the T1 parcel-join path."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_virginia_beach_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Virginia Beach feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent (311 is a phone/app service with no CRM extract).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in VIRGINIA_BEACH_FEED_SPECS:
        available = ", ".join(sorted(VIRGINIA_BEACH_FEED_SPECS))
        raise KeyError(
            f"'{VIRGINIA_BEACH_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = VIRGINIA_BEACH_FEED_SPECS[feed_name]
    extra_kwargs = {
        k: v for k, v in payload.get("extra", {}).items() if k != "scope"
    }
    return DatasetSpec(
        endpoint=payload["endpoint"],
        platform=payload["platform"],
        watermark_col=payload["watermark_col"],
        id_keys=payload["id_keys"],
        topic=getattr(settings, payload["topic_key"]),
        interval_seconds=payload["interval_seconds"],
        producer_key=payload["producer_key"],
        **extra_kwargs,
    )


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=VIRGINIA_BEACH_METRO_BBOX,
    division_bboxes=VIRGINIA_BEACH_DIVISION_BBOXES,
    submarkets=VIRGINIA_BEACH_SUBMARKETS,
    divisions=VIRGINIA_BEACH_DIVISIONS,
    contains=is_in_virginia_beach_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "REGISTRATION",
    "SLA_FIELD_MAP",
    "VB_DIVISIONS",
    "VB_DIVISION_BBOXES",
    "VB_SUBMARKETS",
    "VIRGINIA_BEACH_CENTER",
    "VIRGINIA_BEACH_CITY_ID",
    "VIRGINIA_BEACH_DEEDS_ENDPOINT",
    "VIRGINIA_BEACH_DIVISIONS",
    "VIRGINIA_BEACH_DIVISION_BBOXES",
    "VIRGINIA_BEACH_FEED_SPECS",
    "VIRGINIA_BEACH_GEOCODE_CONTEXT",
    "VIRGINIA_BEACH_METRO_BBOX",
    "VIRGINIA_BEACH_PERMITS_ENDPOINT",
    "VIRGINIA_BEACH_SLA_ENDPOINT",
    "VIRGINIA_BEACH_SUBMARKETS",
    "get_virginia_beach_dataset",
    "is_in_virginia_beach",
    "is_in_virginia_beach_metro",
]
