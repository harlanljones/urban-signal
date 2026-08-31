FIELD_MAP = {
    # ------------------------------------------------------------------
    # PERMITS — Clark County Building Permits (ArcGIS table)
    # ------------------------------------------------------------------
    "permits": {
        "job_id": ["APNO", "APBLDGKEY", "ObjectId"],
        "cost": [
            "DECLVLTN",
            "CALCVLTN",
        ],
        "job_type": ["WORKTYPE", "APTYPE"],
        "issuance_date": ["ISSDTTM"],
        "status": ["BLDGAPPLSTATUS"],
        "address_street": ["APL_ADDRESS", "ADDR1"],
        "zipcode": ["ZIP"],
        "borough": ["CITY", "SUBDIV"],
        "bbl": ["PRCLID"],
    },
    # ------------------------------------------------------------------
    # DEEDS — Clark County real-property parcel sales / recorded deeds
    # (ArcGIS table, address-only -> ADR-0004 geocoded at enrichment)
    # ------------------------------------------------------------------
    "deeds": {
        "doc_id": ["DOCNO", "ObjectId"],
        "bbl": ["PARCEL", "APN"],
        "document_amount": ["SALEPRICE"],
        "recorded_date": ["SALEDATE", "DOCDATE"],
        "borough": ["COMNAME", "WARD"],
        "address_street": ["ADDRESS1", "ADDRESS2"],
        "zipcode": ["ZIP", "ZIPCODE"],
    },
}

"""Las Vegas Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Las Vegas and
the greater Clark County metro (Summerlin, Henderson, North Las Vegas).

Las Vegas registers as a TWO-FEED partial city like Los Angeles and Austin:
PERMITS (Clark County Building Permits, address-only ArcGIS table) and DEEDS
(Clark County real-property parcel sales, address-only -> geocoder-ready under
ADR-0004). SLA / COMPLAINTS_311 are deliberately absent for this ticket — US-145
scopes only PERMITS + sales/deeds; the 311 and business-license layers are a
separate registration and left for their own ticket so `get_dataset` raises a
readable error for them.

The feed specs below are imported by the spine `city_registry.py` REGISTRY
entry (applied during the interlock). The field maps come from
`src/producers/field_maps_las_vegas.FIELD_MAP` so shared `field_maps.py` is
never edited.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Greater Las Vegas / Clark County metro bounding box. Permissive: it must keep
# every live sample (Summerlin NW ~36.25,-115.28; Henderson ~36.03,-115.11;
# North Las Vegas ~36.27,-115.13; the Strip ~36.11,-115.17) inside.
LAS_VEGAS_METRO_BBOX: Dict[str, float] = {
    "min_lat": 35.90,
    "max_lat": 36.34,
    "min_lng": -115.50,
    "max_lng": -114.90,
}

# Division bounding boxes. Approximate hand-authored geographies; resolution at
# ingest comes from coordinates via get_division_for_coordinate, so bboxes need
# only be sane and contain their own submarkets.
LAS_VEGAS_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_STRIP": {
        "min_lat": 36.10,
        "max_lat": 36.20,
        "min_lng": -115.30,
        "max_lng": -115.10,
    },
    "LAS_VEGAS_CITY": {
        "min_lat": 36.15,
        "max_lat": 36.28,
        "min_lng": -115.30,
        "max_lng": -115.10,
    },
    "SUMMERLIN_NW": {
        "min_lat": 36.15,
        "max_lat": 36.30,
        "min_lng": -115.45,
        "max_lng": -115.25,
    },
    "HENDERSON_SOUTH": {
        "min_lat": 35.92,
        "max_lat": 36.10,
        "min_lng": -115.20,
        "max_lng": -114.95,
    },
    "NORTH_LAS_VEGAS": {
        "min_lat": 36.20,
        "max_lat": 36.33,
        "min_lng": -115.20,
        "max_lng": -115.00,
    },
}


def is_in_las_vegas_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Las Vegas Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        LAS_VEGAS_METRO_BBOX["min_lat"] <= lat <= LAS_VEGAS_METRO_BBOX["max_lat"]
        and LAS_VEGAS_METRO_BBOX["min_lng"] <= lng <= LAS_VEGAS_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_greater_las_vegas_metro = is_in_las_vegas_metro


LAS_VEGAS_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_STRIP (4 Submarkets)
    # =======================================================================
    "The Las Vegas Strip": SubmarketMeta(
        name="The Las Vegas Strip",
        borough="DOWNTOWN_STRIP",
        lat=36.1147,
        lng=-115.1728,
        zoom=14.0,
        pitch=55.0,
        base_lims=0.95,
        capex=14000000.0,
        permit_vel=62.0,
        shift_ratio=1.7,
        sla=70.0,
        description="Resort-corridor spine on Las Vegas Blvd with the metro's densest hospitality and high-rise residential pipeline.",
        city_id="las_vegas",
    ),
    "Fremont East & 18b Arts District": SubmarketMeta(
        name="Fremont East & 18b Arts District",
        borough="DOWNTOWN_STRIP",
        lat=36.1620,
        lng=-115.1410,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=41.0,
        shift_ratio=1.5,
        sla=58.0,
        description="Downtown revival node east of Fremont Street with adaptive reuse, boutique hospitality, and gallery density.",
        city_id="las_vegas",
    ),
    "Paradise & Winchester": SubmarketMeta(
        name="Paradise & Winchester",
        borough="DOWNTOWN_STRIP",
        lat=36.1300,
        lng=-115.1500,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=8600000.0,
        permit_vel=44.0,
        shift_ratio=1.52,
        sla=60.0,
        description="Unincorporated township flanking the Strip with mid-rise multifamily and convention-adjacent commercial.",
        city_id="las_vegas",
    ),
    "Spring Valley": SubmarketMeta(
        name="Spring Valley",
        borough="DOWNTOWN_STRIP",
        lat=36.1200,
        lng=-115.2500,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=6400000.0,
        permit_vel=37.0,
        shift_ratio=1.46,
        sla=55.0,
        description="Established west-side residential grid with steady infill and small-lot redevelopment.",
        city_id="las_vegas",
    ),
    # =======================================================================
    # LAS_VEGAS_CITY (4 Submarkets)
    # =======================================================================
    "Downtown Las Vegas (Fremont St)": SubmarketMeta(
        name="Downtown Las Vegas (Fremont St)",
        borough="LAS_VEGAS_CITY",
        lat=36.1716,
        lng=-115.1391,
        zoom=14.0,
        pitch=52.0,
        base_lims=0.86,
        capex=9100000.0,
        permit_vel=48.0,
        shift_ratio=1.55,
        sla=63.0,
        description="Municipal core around Fremont Street with office-to-residential conversions and Zappos-era retail renewal.",
        city_id="las_vegas",
    ),
    "Medical District & UMC": SubmarketMeta(
        name="Medical District & UMC",
        borough="LAS_VEGAS_CITY",
        lat=36.1600,
        lng=-115.1550,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5400000.0,
        permit_vel=31.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Institutional health corridor anchored by UMC with renovation-led permitting and nearby commercial reuse.",
        city_id="las_vegas",
    ),
    "Southeast Las Vegas (Whitney)": SubmarketMeta(
        name="Southeast Las Vegas (Whitney)",
        borough="LAS_VEGAS_CITY",
        lat=36.2100,
        lng=-115.1600,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.76,
        capex=4900000.0,
        permit_vel=34.0,
        shift_ratio=1.4,
        sla=50.0,
        description="Post-war residential belt along the Boulder Highway with teardown/rebuild pressure and indie retail.",
        city_id="las_vegas",
    ),
    "West Las Vegas": SubmarketMeta(
        name="West Las Vegas",
        borough="LAS_VEGAS_CITY",
        lat=36.1750,
        lng=-115.2200,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4600000.0,
        permit_vel=29.0,
        shift_ratio=1.36,
        sla=48.0,
        description="Historic west-side neighborhoods with renovation permits and neighborhood-commercial frontage.",
        city_id="las_vegas",
    ),
    # =======================================================================
    # SUMMERLIN_NW (3 Submarkets)
    # =======================================================================
    "Summerlin South": SubmarketMeta(
        name="Summerlin South",
        borough="SUMMERLIN_NW",
        lat=36.1600,
        lng=-115.3200,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.88,
        capex=10500000.0,
        permit_vel=39.0,
        shift_ratio=1.5,
        sla=58.0,
        description="Master-planned southwest edge with continued buildout phases and high-value residential permits.",
        city_id="las_vegas",
    ),
    "Downtown Summerlin": SubmarketMeta(
        name="Downtown Summerlin",
        borough="SUMMERLIN_NW",
        lat=36.2500,
        lng=-115.3000,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.9,
        capex=12000000.0,
        permit_vel=52.0,
        shift_ratio=1.6,
        sla=66.0,
        description="Anchor retail-and-office downtown of the Summerlin master plan under the Red Rock overlay.",
        city_id="las_vegas",
    ),
    "Centennial Hills": SubmarketMeta(
        name="Centennial Hills",
        borough="SUMMERLIN_NW",
        lat=36.2700,
        lng=-115.2800,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=27.0,
        shift_ratio=1.3,
        sla=44.0,
        description="Northwest growth area at the metro's edge with new construction, infrastructure extension, and parcel turnover.",
        city_id="las_vegas",
    ),
    # =======================================================================
    # HENDERSON_SOUTH (3 Submarkets)
    # =======================================================================
    "Green Valley": SubmarketMeta(
        name="Green Valley",
        borough="HENDERSON_SOUTH",
        lat=36.0300,
        lng=-115.1100,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.85,
        capex=7800000.0,
        permit_vel=36.0,
        shift_ratio=1.43,
        sla=56.0,
        description="Mature master-planned Henderson community with renovation-heavy permitting and strict design overlays.",
        city_id="las_vegas",
    ),
    "Henderson (Water St)": SubmarketMeta(
        name="Henderson (Water St)",
        borough="HENDERSON_SOUTH",
        lat=36.0400,
        lng=-114.9800,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.8,
        capex=6300000.0,
        permit_vel=33.0,
        shift_ratio=1.39,
        sla=52.0,
        description="Henderson civic core along Water Street with mixed-use infill and ground-floor hospitality.",
        city_id="las_vegas",
    ),
    "Anthem & MacDonald Ranch": SubmarketMeta(
        name="Anthem & MacDonald Ranch",
        borough="HENDERSON_SOUTH",
        lat=35.9700,
        lng=-115.0100,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.79,
        capex=5900000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=45.0,
        description="Southeast foothill estate stock with teardown-rebuild mansions dominating a low-volume, high-value permit mix.",
        city_id="las_vegas",
    ),
    # =======================================================================
    # NORTH_LAS_VEGAS (2 Submarkets)
    # =======================================================================
    "North Las Vegas (Craig Rd)": SubmarketMeta(
        name="North Las Vegas (Craig Rd)",
        borough="NORTH_LAS_VEGAS",
        lat=36.2400,
        lng=-115.1200,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.7,
        capex=4100000.0,
        permit_vel=35.0,
        shift_ratio=1.33,
        sla=43.0,
        description="Working-class north-side city with logistics investment, redevelopment, and active parcel sales.",
        city_id="las_vegas",
    ),
    "Aliante": SubmarketMeta(
        name="Aliante",
        borough="NORTH_LAS_VEGAS",
        lat=36.3000,
        lng=-115.1500,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.66,
        capex=3500000.0,
        permit_vel=24.0,
        shift_ratio=1.26,
        sla=38.0,
        description="Master-planned northwest community with new housing, infrastructure extension, and unincorporated county development meeting it.",
        city_id="las_vegas",
    ),
}


LAS_VEGAS_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_STRIP": BoroughMeta(
        name="DOWNTOWN_STRIP",
        center_lat=36.13,
        center_lng=-115.16,
        zoom=13.0,
        bbox=LAS_VEGAS_DIVISION_BBOXES["DOWNTOWN_STRIP"],
        submarkets=[k for k, v in LAS_VEGAS_SUBMARKETS.items() if v.borough == "DOWNTOWN_STRIP"],
        city_id="las_vegas",
    ),
    "LAS_VEGAS_CITY": BoroughMeta(
        name="LAS_VEGAS_CITY",
        center_lat=36.20,
        center_lng=-115.18,
        zoom=12.5,
        bbox=LAS_VEGAS_DIVISION_BBOXES["LAS_VEGAS_CITY"],
        submarkets=[k for k, v in LAS_VEGAS_SUBMARKETS.items() if v.borough == "LAS_VEGAS_CITY"],
        city_id="las_vegas",
    ),
    "SUMMERLIN_NW": BoroughMeta(
        name="SUMMERLIN_NW",
        center_lat=36.22,
        center_lng=-115.32,
        zoom=12.0,
        bbox=LAS_VEGAS_DIVISION_BBOXES["SUMMERLIN_NW"],
        submarkets=[k for k, v in LAS_VEGAS_SUBMARKETS.items() if v.borough == "SUMMERLIN_NW"],
        city_id="las_vegas",
    ),
    "HENDERSON_SOUTH": BoroughMeta(
        name="HENDERSON_SOUTH",
        center_lat=36.03,
        center_lng=-115.07,
        zoom=12.0,
        bbox=LAS_VEGAS_DIVISION_BBOXES["HENDERSON_SOUTH"],
        submarkets=[k for k, v in LAS_VEGAS_SUBMARKETS.items() if v.borough == "HENDERSON_SOUTH"],
        city_id="las_vegas",
    ),
    "NORTH_LAS_VEGAS": BoroughMeta(
        name="NORTH_LAS_VEGAS",
        center_lat=36.26,
        center_lng=-115.10,
        zoom=11.5,
        bbox=LAS_VEGAS_DIVISION_BBOXES["NORTH_LAS_VEGAS"],
        submarkets=[k for k, v in LAS_VEGAS_SUBMARKETS.items() if v.borough == "NORTH_LAS_VEGAS"],
        city_id="las_vegas",
    ),
}

# Verbose aliases mirroring las_vegas / LV_ pairs used elsewhere.
GREATER_LAS_VEGAS_METRO_BBOX = LAS_VEGAS_METRO_BBOX
LV_DIVISION_BBOXES = LAS_VEGAS_DIVISION_BBOXES
LV_SUBMARKETS = LAS_VEGAS_SUBMARKETS
LV_DIVISIONS = LAS_VEGAS_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (imported by the spine REGISTRY entry during interlock).
# Both endpoints were live-verified on 2026-08-26.
# ---------------------------------------------------------------------------
LAS_VEGAS_PERMITS_ENDPOINT = (
    "https://services1.arcgis.com/F1v0ufATbBQScMtY/ArcGIS/rest/services/"
    "OpenData_Building_Permits_/FeatureServer/0"
)
LAS_VEGAS_DEEDS_ENDPOINT = (
    "https://services1.arcgis.com/F1v0ufATbBQScMtY/ArcGIS/rest/services/"
    "parcels/FeatureServer/0"
)

LAS_VEGAS_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": LAS_VEGAS_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ISSDTTM",
        "id_keys": ["APNO", "APBLDGKEY", "ObjectId"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 7,
            "oid_field": "ObjectId",
            "max_record_count": 1000,
            "order_by": "ISSDTTM DESC",
            "needs_geocode": True,
            "geocode_context": "Las Vegas, NV",
            "scope": "Clark County Building Permits (address-only ArcGIS table)",
            "field_map": FIELD_MAP["permits"],
        },
    },
    "deeds": {
        "endpoint": LAS_VEGAS_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SALEDATE",
        "id_keys": ["PARCEL", "DOCNO", "ObjectId"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            "expected_cadence_days": 7,
            "oid_field": "ObjectId",
            "max_record_count": 2000,
            "order_by": "SALEDATE DESC",
            "needs_geocode": True,
            "geocode_context": "Las Vegas, NV",
            "scope": "Clark County real-property parcel sales / recorded deeds (address-only ArcGIS table)",
            "field_map": FIELD_MAP["deeds"],
        },
    },
}


def get_las_vegas_dataset(feed: object) -> object:
    """Return a leaf-local DatasetSpec without importing the registry at load time."""
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in LAS_VEGAS_FEED_SPECS:
        available = ", ".join(sorted(LAS_VEGAS_FEED_SPECS))
        raise KeyError(f"'las_vegas' has no '{feed_name}' feed; available: {available}")
    payload = LAS_VEGAS_FEED_SPECS[feed_name]
    # Promote the former free-form extra keys (minus the dead `scope`) to typed
    # DatasetSpec fields.
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
    metro_bbox=LAS_VEGAS_METRO_BBOX,
    division_bboxes=LAS_VEGAS_DIVISION_BBOXES,
    submarkets=LAS_VEGAS_SUBMARKETS,
    divisions=LAS_VEGAS_DIVISIONS,
    contains=is_in_las_vegas_metro,
)
