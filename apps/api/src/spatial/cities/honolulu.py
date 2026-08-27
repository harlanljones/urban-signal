"""Honolulu Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City and County of
Honolulu (the island of Oahu).

Honolulu is a TWO-FEED PARTIAL metro like Austin/LA: COMPLAINTS_311
(`data.honolulu.gov` `jdy7-ftwe` "HNL 311 Reports") and PERMITS
(`4vab-c87q` "Building Permits"). Both feeds are address-only and therefore
declare ``needs_geocode`` (ADR 0004). SLA / DEEDS are absent.

Live-probe caveats that define this leaf (2026-08-27):

* 311 is a **rolling 30-day snapshot**, refreshed daily. Nine columns, no
  coordinate field of any kind. Address is split across `street` / `city` /
  `state` / `zip_code`. The `state` value is the full word ``Hawaii``, which
  does **not** match the geocoder's ``_STATE_RE`` (abbreviation ``HI`` only),
  so the field map must pass `street` alone and let ``geocode_context``
  ("Honolulu, HI") suffix the query. `date_created` is a month-name text
  watermark (``August 26, 2026 at 11:52 PM``); lexical Socrata ORDER BY on
  that column is wrong, and the shared 311 ``_parse_datetime`` does not yet
  know this format (spine follow-up).
* PERMITS `4vab-c87q` is a **closed archive** titled through 2025-06-30
  (newest `issuedate` 2025-07-01, zero 2026 rows, `rowsUpdatedAt` 2025-08-12).
  The field map below is authored against the live schema so a successor
  resource can wire it; the spine must not register this snapshot as a live
  incremental feed. Address is `joblocation` (and sometimes `address`).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Greater Honolulu / Oahu bounding box. City-and-County-of-Honolulu-scoped:
# Kaena Point west, Makapuu east, Hawaii Kai south, Kahuku Point north.
# Both feeds are island-wide; the metro bbox only has to keep every live
# sample inside.
HONOLULU_METRO_BBOX: Dict[str, float] = {
    "min_lat": 21.24,
    "max_lat": 21.73,
    "min_lng": -158.29,
    "max_lng": -157.64,
}

# 6 Oahu Division Bounding Boxes. Approximate hand-authored geographies;
# borough resolution at ingest comes from coordinates via
# get_division_for_coordinate, so bboxes need only be sane and contain their
# own submarket centers.
HONOLULU_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_HNL": {
        "min_lat": 21.285,
        "max_lat": 21.325,
        "min_lng": -157.875,
        "max_lng": -157.835,
    },
    "WAIKIKI_EAST": {
        "min_lat": 21.250,
        "max_lat": 21.295,
        "min_lng": -157.845,
        "max_lng": -157.700,
    },
    "WINDWARD": {
        "min_lat": 21.370,
        "max_lat": 21.500,
        "min_lng": -157.830,
        "max_lng": -157.680,
    },
    "CENTRAL_OAHU": {
        "min_lat": 21.360,
        "max_lat": 21.520,
        "min_lng": -158.050,
        "max_lng": -157.900,
    },
    "LEEWARD": {
        "min_lat": 21.300,
        "max_lat": 21.490,
        "min_lng": -158.230,
        "max_lng": -157.990,
    },
    "NORTH_SHORE": {
        "min_lat": 21.550,
        "max_lat": 21.720,
        "min_lng": -158.200,
        "max_lng": -157.880,
    },
}


def is_in_honolulu_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Honolulu / Oahu bounds."""
    if lat is None or lng is None:
        return False
    return (
        HONOLULU_METRO_BBOX["min_lat"] <= lat <= HONOLULU_METRO_BBOX["max_lat"]
        and HONOLULU_METRO_BBOX["min_lng"] <= lng <= HONOLULU_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_greater_honolulu_metro = is_in_honolulu_metro


HONOLULU_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_HNL (3 Submarkets)
    # =======================================================================
    "Downtown Honolulu": SubmarketMeta(
        name="Downtown Honolulu",
        borough="DOWNTOWN_HNL",
        lat=21.3069,
        lng=-157.8583,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.90,
        capex=10500000.0,
        permit_vel=48.0,
        shift_ratio=1.55,
        sla=68.0,
        description="Financial-district and civic core around Aloha Tower with office-to-residential conversions and the densest 311 volume on the island.",
        city_id="honolulu",
    ),
    "Chinatown": SubmarketMeta(
        name="Chinatown",
        borough="DOWNTOWN_HNL",
        lat=21.3124,
        lng=-157.8635,
        zoom=15.0,
        pitch=52.0,
        base_lims=0.82,
        capex=6200000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=61.0,
        description="Historic low-rise commercial enclave with renovation-heavy permitting, night-market density, and preservation overlays.",
        city_id="honolulu",
    ),
    "Kakaako": SubmarketMeta(
        name="Kakaako",
        borough="DOWNTOWN_HNL",
        lat=21.2980,
        lng=-157.8600,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.93,
        capex=14000000.0,
        permit_vel=62.0,
        shift_ratio=1.72,
        sla=74.0,
        description="Ward Village / Our Kakaako high-rise spine turning former industrial blocks into the metro's densest residential pipeline.",
        city_id="honolulu",
    ),
    # =======================================================================
    # WAIKIKI_EAST (3 Submarkets)
    # =======================================================================
    "Waikiki": SubmarketMeta(
        name="Waikiki",
        borough="WAIKIKI_EAST",
        lat=21.2766,
        lng=-157.8278,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.91,
        capex=12800000.0,
        permit_vel=55.0,
        shift_ratio=1.64,
        sla=72.0,
        description="Resort-corridor spine on Kalakaua with hotel renovation, timeshare conversion, and the island's highest short-stay pressure.",
        city_id="honolulu",
    ),
    "Diamond Head & Kahala": SubmarketMeta(
        name="Diamond Head & Kahala",
        borough="WAIKIKI_EAST",
        lat=21.2650,
        lng=-157.7790,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.88,
        capex=9600000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=54.0,
        description="High-value coastal estate stock east of Waikiki dominated by renovation permits and strict shoreline setbacks.",
        city_id="honolulu",
    ),
    "Hawaii Kai": SubmarketMeta(
        name="Hawaii Kai",
        borough="WAIKIKI_EAST",
        lat=21.2856,
        lng=-157.7175,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=31.0,
        shift_ratio=1.42,
        sla=56.0,
        description="Marina-planned east-Oahu community with ADU and waterfront-renovation activity at the island's southeastern edge.",
        city_id="honolulu",
    ),
    # =======================================================================
    # WINDWARD (2 Submarkets)
    # =======================================================================
    "Kailua": SubmarketMeta(
        name="Kailua",
        borough="WINDWARD",
        lat=21.4022,
        lng=-157.7394,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.86,
        capex=7800000.0,
        permit_vel=34.0,
        shift_ratio=1.46,
        sla=58.0,
        description="Windward beach town with cottage-to-estate renovations and STR-driven small-lot pressure around Kailua Beach.",
        city_id="honolulu",
    ),
    "Kaneohe": SubmarketMeta(
        name="Kaneohe",
        borough="WINDWARD",
        lat=21.4183,
        lng=-157.8036,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=29.0,
        shift_ratio=1.40,
        sla=52.0,
        description="Bayfront suburban grid under the Pali with steady single-family infill and military-adjacent rental demand.",
        city_id="honolulu",
    ),
    # =======================================================================
    # CENTRAL_OAHU (3 Submarkets)
    # =======================================================================
    "Aiea & Pearl City": SubmarketMeta(
        name="Aiea & Pearl City",
        borough="CENTRAL_OAHU",
        lat=21.3972,
        lng=-157.9731,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=6100000.0,
        permit_vel=33.0,
        shift_ratio=1.44,
        sla=55.0,
        description="Pearl Harbor-adjacent mid-island suburbs with rail-station infill and aging post-war tract replacement.",
        city_id="honolulu",
    ),
    "Mililani": SubmarketMeta(
        name="Mililani",
        borough="CENTRAL_OAHU",
        lat=21.4510,
        lng=-158.0110,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.83,
        capex=6800000.0,
        permit_vel=32.0,
        shift_ratio=1.43,
        sla=57.0,
        description="Master-planned central plateau community with townhome infill and renovation-led permitting on the H-2 corridor.",
        city_id="honolulu",
    ),
    "Wahiawa": SubmarketMeta(
        name="Wahiawa",
        borough="CENTRAL_OAHU",
        lat=21.5020,
        lng=-158.0230,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.72,
        capex=3800000.0,
        permit_vel=22.0,
        shift_ratio=1.28,
        sla=44.0,
        description="Pineapple-town grid at the island's saddle with sparse permitting and Schofield Barracks-adjacent rental stock.",
        city_id="honolulu",
    ),
    # =======================================================================
    # LEEWARD (3 Submarkets)
    # =======================================================================
    "Kapolei": SubmarketMeta(
        name="Kapolei",
        borough="LEEWARD",
        lat=21.3356,
        lng=-158.0808,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.87,
        capex=9200000.0,
        permit_vel=46.0,
        shift_ratio=1.58,
        sla=64.0,
        description="Second-city civic and commercial node with the island's largest new-construction pipeline west of downtown.",
        city_id="honolulu",
    ),
    "Ewa Beach": SubmarketMeta(
        name="Ewa Beach",
        borough="LEEWARD",
        lat=21.3169,
        lng=-158.0122,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.79,
        capex=5600000.0,
        permit_vel=35.0,
        shift_ratio=1.45,
        sla=53.0,
        description="South-loeward tract and Hoakalei marina growth edge with high single-family permit velocity.",
        city_id="honolulu",
    ),
    "Waianae": SubmarketMeta(
        name="Waianae",
        borough="LEEWARD",
        lat=21.4389,
        lng=-158.1814,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.64,
        capex=2900000.0,
        permit_vel=18.0,
        shift_ratio=1.18,
        sla=38.0,
        description="Leeward coast townships with sparse, shoreline-constrained development and high 311 volume relative to permit activity.",
        city_id="honolulu",
    ),
    # =======================================================================
    # NORTH_SHORE (2 Submarkets)
    # =======================================================================
    "Haleiwa & Waialua": SubmarketMeta(
        name="Haleiwa & Waialua",
        borough="NORTH_SHORE",
        lat=21.5906,
        lng=-158.1036,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.78,
        capex=5100000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=48.0,
        description="North Shore surf-town commercial spine with STR-driven cottage renovations and agricultural-lot pressure.",
        city_id="honolulu",
    ),
    "Laie & Sunset": SubmarketMeta(
        name="Laie & Sunset",
        borough="NORTH_SHORE",
        lat=21.6477,
        lng=-157.9253,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.74,
        capex=4300000.0,
        permit_vel=20.0,
        shift_ratio=1.26,
        sla=42.0,
        description="Windward-north coastal villages with limited new construction and seasonal STR occupancy around Sunset Beach and Laie.",
        city_id="honolulu",
    ),
}


HONOLULU_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_HNL": BoroughMeta(
        name="DOWNTOWN_HNL",
        center_lat=21.307,
        center_lng=-157.858,
        zoom=13.5,
        bbox=HONOLULU_DIVISION_BBOXES["DOWNTOWN_HNL"],
        submarkets=[k for k, v in HONOLULU_SUBMARKETS.items() if v.borough == "DOWNTOWN_HNL"],
        city_id="honolulu",
    ),
    "WAIKIKI_EAST": BoroughMeta(
        name="WAIKIKI_EAST",
        center_lat=21.276,
        center_lng=-157.780,
        zoom=12.5,
        bbox=HONOLULU_DIVISION_BBOXES["WAIKIKI_EAST"],
        submarkets=[k for k, v in HONOLULU_SUBMARKETS.items() if v.borough == "WAIKIKI_EAST"],
        city_id="honolulu",
    ),
    "WINDWARD": BoroughMeta(
        name="WINDWARD",
        center_lat=21.410,
        center_lng=-157.770,
        zoom=12.5,
        bbox=HONOLULU_DIVISION_BBOXES["WINDWARD"],
        submarkets=[k for k, v in HONOLULU_SUBMARKETS.items() if v.borough == "WINDWARD"],
        city_id="honolulu",
    ),
    "CENTRAL_OAHU": BoroughMeta(
        name="CENTRAL_OAHU",
        center_lat=21.420,
        center_lng=-157.975,
        zoom=12.5,
        bbox=HONOLULU_DIVISION_BBOXES["CENTRAL_OAHU"],
        submarkets=[k for k, v in HONOLULU_SUBMARKETS.items() if v.borough == "CENTRAL_OAHU"],
        city_id="honolulu",
    ),
    "LEEWARD": BoroughMeta(
        name="LEEWARD",
        center_lat=21.370,
        center_lng=-158.090,
        zoom=12.0,
        bbox=HONOLULU_DIVISION_BBOXES["LEEWARD"],
        submarkets=[k for k, v in HONOLULU_SUBMARKETS.items() if v.borough == "LEEWARD"],
        city_id="honolulu",
    ),
    "NORTH_SHORE": BoroughMeta(
        name="NORTH_SHORE",
        center_lat=21.630,
        center_lng=-158.030,
        zoom=12.0,
        bbox=HONOLULU_DIVISION_BBOXES["NORTH_SHORE"],
        submarkets=[k for k, v in HONOLULU_SUBMARKETS.items() if v.borough == "NORTH_SHORE"],
        city_id="honolulu",
    ),
}

# Verbose aliases mirroring los_angeles.py's LA_*/LOS_ANGELES_* pairs.
GREATER_HONOLULU_METRO_BBOX = HONOLULU_METRO_BBOX
HNL_DIVISION_BBOXES = HONOLULU_DIVISION_BBOXES
HNL_SUBMARKETS = HONOLULU_SUBMARKETS
HNL_DIVISIONS = HONOLULU_DIVISIONS


# ---------------------------------------------------------------------------
# Per-feed field maps (US-193 / ADR 0004). Exported so the shared parser chains
# consult them for Honolulu before falling back to generics, and so the spine
# registration can pin them into DatasetSpec["field_map"].
#
# 311 has no lat/lng — `street` is the geocode input. Do not concatenate
# `city`+`state` into the address: `state` is the full word "Hawaii", which
# fails `_STATE_RE` and would double-append geocode_context.
#
# Permits are address-only via `joblocation` (fallback `address`). `tmk` is
# the Hawaii Tax Map Key, treated as the parcel identifier (bbl analogue).
# `buildingpermitno` is null on cancelled jobs; `externalfilenum` / `objectid`
# are the fallbacks.
# ---------------------------------------------------------------------------
HONOLULU_PERMITS_FIELD_MAP: Dict[str, list[str]] = {
    "job_id": ["buildingpermitno", "externalfilenum", "objectid"],
    "issuance_date": ["issuedate"],
    "filing_date": ["createddate"],
    "job_type": ["proposeduse", "buildingpermittype", "occupancygroupassessed"],
    "cost": ["estimatedvalueofwork"],
    "status": ["statusdescription"],
    "address_street": ["joblocation", "address"],
    "zipcode": ["joblocation", "address"],
    "bbl": ["tmk"],
    "proposed_units": ["numunitsadd"],
    "proposed_stories": ["finalstories"],
    "borough": ["commercialresidential"],
}

HONOLULU_311_FIELD_MAP: Dict[str, list[str]] = {
    "incident_id": ["id"],
    "complaint_type": ["request_type"],
    "created_date": ["date_created"],
    "status": ["status"],
    "incident_address": ["street"],
    "zipcode": ["zip_code"],
    "descriptor": ["description"],
    "borough": ["city"],
}


# Context suffix fed to the ADR-0004 geocoder. Honolulu 311 `street` values
# carry no state token, so this suffix IS appended. Permit `joblocation`
# strings name the neighborhood ("Honolulu / Waialae Kahala") but not `HI`,
# so they also receive the suffix (the whole "Honolulu, HI" token is absent).
HONOLULU_GEOCODE_CONTEXT = "Honolulu, HI"


# Single dispatch surface consumed by field_maps_honolulu.FIELD_MAP. Keyed by
# FeedType value string so the spine can wire either feed independently.
HONOLULU_FIELD_MAPS: Dict[str, Dict[str, list[str]]] = {
    "permits": HONOLULU_PERMITS_FIELD_MAP,
    "311": HONOLULU_311_FIELD_MAP,
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=HONOLULU_METRO_BBOX,
    division_bboxes=HONOLULU_DIVISION_BBOXES,
    submarkets=HONOLULU_SUBMARKETS,
    divisions=HONOLULU_DIVISIONS,
    contains=is_in_honolulu_metro,
)
