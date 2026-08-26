"""San Jose Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of San Jose, CA
(Santa Clara County seat) and its southern/edge corridors (Almaden, Cambrian,
Evergreen, Milpitas edge).

San Jose registers as a TWO-FEED city like Los Angeles and Austin: PERMITS
(San Jose Building Permits) and COMPLAINTS_311 (San Jose 311 Service Requests).
Both feeds live on the City's **CKAN datastore**. The geocoding caveats that
define this registration:

* The 311 layer carries native decimal-degree coordinates, but the 2026
  resource has no address column and roughly 49% of sampled rows are `0,0`.
  Those rows are deliberately dropped by the shared parser rather than sent
  to the Gulf of Guinea; this is the G8' null-H3 caveat tracked by US-147.
* The PERMITS layer is address-only (`gx_location`) and therefore declares
  ``needs_geocode`` (ADR 0004). It also uses an M/D/YYYY text watermark, which
  is typed in the registry so incremental queries compare calendar dates.
* San Jose addresses already end in "SAN JOSE, CA"; the geocoder's state regex
  detects `CA` and does NOT append the `geocode_context` ("San Jose, CA")
  suffix, avoiding a doubled-context query.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Greater San Jose metro bounding box: Santa Clara County's urban core plus the
# Almaden Valley to the south, Evergreen to the east, and the Milpitas/Santa
# Clara edge to the north. Both feeds are City-of-San-Jose-scoped; the metro
# bbox only has to keep every live sample inside.
SAN_JOSE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 37.15,
    "max_lat": 37.45,
    "min_lng": -122.06,
    "max_lng": -121.55,
}

# 6 San Jose Division Bounding Boxes. Approximate hand-authored geographies;
# borough resolution at ingest comes from coordinates via
# get_division_for_coordinate, so bboxes need only be sane and disjoint enough
# to resolve unambiguously near their centers.
SAN_JOSE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_SJ":     {"min_lat": 37.32,  "max_lat": 37.35,  "min_lng": -121.91,  "max_lng": -121.86},
    "NORTH_SJ":        {"min_lat": 37.37,  "max_lat": 37.43,  "min_lng": -121.99,  "max_lng": -121.86},
    "SOUTH_SJ":        {"min_lat": 37.15,  "max_lat": 37.25,  "min_lng": -121.95,  "max_lng": -121.78},
    "EAST_SJ":         {"min_lat": 37.28,  "max_lat": 37.40,  "min_lng": -121.85,  "max_lng": -121.73},
    "WEST_SJ":         {"min_lat": 37.28,  "max_lat": 37.33,  "min_lng": -121.95,  "max_lng": -121.88},
    "SANTA_CLARA_EDGE":{"min_lat": 37.33,  "max_lat": 37.41,  "min_lng": -121.97,  "max_lng": -121.87},
}


def is_in_san_jose_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater San Jose Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        SAN_JOSE_METRO_BBOX["min_lat"] <= lat <= SAN_JOSE_METRO_BBOX["max_lat"]
        and SAN_JOSE_METRO_BBOX["min_lng"] <= lng <= SAN_JOSE_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_greater_san_jose_metro = is_in_san_jose_metro


SAN_JOSE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_SJ (3 Submarkets)
    # =======================================================================
    "Downtown San Jose": SubmarketMeta(
        name="Downtown San Jose",
        borough="DOWNTOWN_SJ",
        lat=37.3370,
        lng=-121.8860,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.92,
        capex=11000000.0,
        permit_vel=54.0,
        shift_ratio=1.62,
        sla=71.0,
        description="High-rise residential and office core around Diridon and the Google transit village, with the densest permit pipeline in the metro.",
        city_id="san_jose",
    ),
    "SoFA District": SubmarketMeta(
        name="SoFA District",
        borough="DOWNTOWN_SJ",
        lat=37.3300,
        lng=-121.8860,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.86,
        capex=8200000.0,
        permit_vel=41.0,
        shift_ratio=1.51,
        sla=64.0,
        description="South-of-First arts and nightlife district turning former industrial blocks into mixed-use and creative-office conversions.",
        city_id="san_jose",
    ),
    "Japantown": SubmarketMeta(
        name="Japantown",
        borough="DOWNTOWN_SJ",
        lat=37.3480,
        lng=-121.8950,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.84,
        capex=6900000.0,
        permit_vel=33.0,
        shift_ratio=1.46,
        sla=60.0,
        description="Historic low-rise commercial enclave with renovation-heavy permitting and strict preservation overlays.",
        city_id="san_jose",
    ),
    # =======================================================================
    # NORTH_SJ (3 Submarkets)
    # =======================================================================
    "North San Jose": SubmarketMeta(
        name="North San Jose",
        borough="NORTH_SJ",
        lat=37.4000,
        lng=-121.9000,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.9,
        capex=11500000.0,
        permit_vel=56.0,
        shift_ratio=1.66,
        sla=69.0,
        description="Cisco-era office sprawl being rezoned to high-density residential and life-science lab space along the BART alignment.",
        city_id="san_jose",
    ),
    "Berryessa": SubmarketMeta(
        name="Berryessa",
        borough="NORTH_SJ",
        lat=37.3900,
        lng=-121.8700,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=7200000.0,
        permit_vel=38.0,
        shift_ratio=1.47,
        sla=58.0,
        description="BART-adjacent infill suburb with townhome and multifamily replacement of aging auto-oriented retail.",
        city_id="san_jose",
    ),
    "Alviso": SubmarketMeta(
        name="Alviso",
        borough="NORTH_SJ",
        lat=37.4300,
        lng=-121.9700,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.62,
        capex=3100000.0,
        permit_vel=21.0,
        shift_ratio=1.22,
        sla=40.0,
        description="Bayland-edge former township with sparse, flood-prone development and teardown-rebuild pressure near the salt ponds.",
        city_id="san_jose",
    ),
    # =======================================================================
    # SOUTH_SJ (3 Submarkets)
    # =======================================================================
    "Almaden Valley": SubmarketMeta(
        name="Almaden Valley",
        borough="SOUTH_SJ",
        lat=37.2000,
        lng=-121.8700,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.88,
        capex=9400000.0,
        permit_vel=29.0,
        shift_ratio=1.4,
        sla=55.0,
        description="Hill-county estate and large-lot residential stock at the south valley floor, dominated by high-value renovation permits.",
        city_id="san_jose",
    ),
    "Cambrian Park": SubmarketMeta(
        name="Cambrian Park",
        borough="SOUTH_SJ",
        lat=37.2500,
        lng=-121.9300,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.83,
        capex=6400000.0,
        permit_vel=32.0,
        shift_ratio=1.45,
        sla=57.0,
        description="Post-war bungalow and cottage-grid neighborhood with renovation-led permits and independent retail spines.",
        city_id="san_jose",
    ),
    "Blossom Valley": SubmarketMeta(
        name="Blossom Valley",
        borough="SOUTH_SJ",
        lat=37.2000,
        lng=-121.8500,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.8,
        capex=6000000.0,
        permit_vel=31.0,
        shift_ratio=1.43,
        sla=56.0,
        description="Mid-century residential flatlands south of Almaden Expressway with steady small-lot infill and ADU construction.",
        city_id="san_jose",
    ),
    # =======================================================================
    # EAST_SJ (2 Submarkets)
    # =======================================================================
    "Evergreen": SubmarketMeta(
        name="Evergreen",
        borough="EAST_SJ",
        lat=37.3200,
        lng=-121.8000,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.84,
        capex=7000000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=58.0,
        description="East-foothill residential community with new-construction permits and hillside teardown-rebuild activity.",
        city_id="san_jose",
    ),
    "Eastridge": SubmarketMeta(
        name="Eastridge",
        borough="EAST_SJ",
        lat=37.3500,
        lng=-121.8200,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.79,
        capex=5600000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=54.0,
        description="Mall-adjacent commercial node transitioning to mixed-use residential under the Eastridge transit-oriented plan.",
        city_id="san_jose",
    ),
    # =======================================================================
    # WEST_SJ (2 Submarkets)
    # =======================================================================
    "Willow Glen": SubmarketMeta(
        name="Willow Glen",
        borough="WEST_SJ",
        lat=37.3100,
        lng=-121.9000,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.85,
        capex=7800000.0,
        permit_vel=34.0,
        shift_ratio=1.47,
        sla=59.0,
        description="Storybook-bungalow historic district on the west side with renovation-heavy permitting and strict tree ordinances.",
        city_id="san_jose",
    ),
    "West San Carlos": SubmarketMeta(
        name="West San Carlos",
        borough="WEST_SJ",
        lat=37.3200,
        lng=-121.9200,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.8,
        capex=6100000.0,
        permit_vel=33.0,
        shift_ratio=1.45,
        sla=57.0,
        description="CalTrain-adjacent corridor undergoing station-area densification with multifamily replacements of aging retail.",
        city_id="san_jose",
    ),
    # =======================================================================
    # SANTA_CLARA_EDGE (3 Submarkets)
    # =======================================================================
    "Santa Clara Edge": SubmarketMeta(
        name="Santa Clara Edge",
        borough="SANTA_CLARA_EDGE",
        lat=37.3500,
        lng=-121.9600,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.83,
        capex=8600000.0,
        permit_vel=45.0,
        shift_ratio=1.52,
        sla=62.0,
        description="Levi's Stadium / Mission College edge with mixed commercial and residential intensification spilling from Santa Clara.",
        city_id="san_jose",
    ),
    "Lawrence Station": SubmarketMeta(
        name="Lawrence Station",
        borough="SANTA_CLARA_EDGE",
        lat=37.3700,
        lng=-121.9500,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=39.0,
        shift_ratio=1.48,
        sla=59.0,
        description="Light-rail-adjacent office-to-residential conversion corridor on the San Jose/Santa Clara border.",
        city_id="san_jose",
    ),
    "Milpitas Edge": SubmarketMeta(
        name="Milpitas Edge",
        borough="SANTA_CLARA_EDGE",
        lat=37.3800,
        lng=-121.8900,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.74,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Northern metro boundary shading into Milpitas; BART/Berryessa-adjacent infill permitted through San Jose.",
        city_id="san_jose",
    ),
}


SAN_JOSE_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_SJ": BoroughMeta(
        name="DOWNTOWN_SJ",
        center_lat=37.338,
        center_lng=-121.886,
        zoom=13.5,
        bbox=SAN_JOSE_DIVISION_BBOXES["DOWNTOWN_SJ"],
        submarkets=[k for k, v in SAN_JOSE_SUBMARKETS.items() if v.borough == "DOWNTOWN_SJ"],
        city_id="san_jose",
    ),
    "NORTH_SJ": BoroughMeta(
        name="NORTH_SJ",
        center_lat=37.40,
        center_lng=-121.90,
        zoom=13.0,
        bbox=SAN_JOSE_DIVISION_BBOXES["NORTH_SJ"],
        submarkets=[k for k, v in SAN_JOSE_SUBMARKETS.items() if v.borough == "NORTH_SJ"],
        city_id="san_jose",
    ),
    "SOUTH_SJ": BoroughMeta(
        name="SOUTH_SJ",
        center_lat=37.20,
        center_lng=-121.87,
        zoom=13.0,
        bbox=SAN_JOSE_DIVISION_BBOXES["SOUTH_SJ"],
        submarkets=[k for k, v in SAN_JOSE_SUBMARKETS.items() if v.borough == "SOUTH_SJ"],
        city_id="san_jose",
    ),
    "EAST_SJ": BoroughMeta(
        name="EAST_SJ",
        center_lat=37.34,
        center_lng=-121.81,
        zoom=13.0,
        bbox=SAN_JOSE_DIVISION_BBOXES["EAST_SJ"],
        submarkets=[k for k, v in SAN_JOSE_SUBMARKETS.items() if v.borough == "EAST_SJ"],
        city_id="san_jose",
    ),
    "WEST_SJ": BoroughMeta(
        name="WEST_SJ",
        center_lat=37.32,
        center_lng=-121.91,
        zoom=13.5,
        bbox=SAN_JOSE_DIVISION_BBOXES["WEST_SJ"],
        submarkets=[k for k, v in SAN_JOSE_SUBMARKETS.items() if v.borough == "WEST_SJ"],
        city_id="san_jose",
    ),
    "SANTA_CLARA_EDGE": BoroughMeta(
        name="SANTA_CLARA_EDGE",
        center_lat=37.37,
        center_lng=-121.93,
        zoom=12.5,
        bbox=SAN_JOSE_DIVISION_BBOXES["SANTA_CLARA_EDGE"],
        submarkets=[k for k, v in SAN_JOSE_SUBMARKETS.items() if v.borough == "SANTA_CLARA_EDGE"],
        city_id="san_jose",
    ),
}

# Verbose aliases mirroring los_angeles.py's LA_*/LOS_ANGELES_* pairs.
GREATER_SAN_JOSE_METRO_BBOX = SAN_JOSE_METRO_BBOX
SJ_DIVISION_BBOXES = SAN_JOSE_DIVISION_BBOXES
SJ_SUBMARKETS = SAN_JOSE_SUBMARKETS
SJ_DIVISIONS = SAN_JOSE_DIVISIONS


# ---------------------------------------------------------------------------
# Per-feed field maps (US-147 / ADR 0004). Exported so the shared parser chains
# consult them for San Jose before falling back to generics, and so the spine
# registration can pin them into DatasetSpec.extra["field_map"] (see the leaf
# report). The 311 map's latitude/longitude candidates lead with the
# `Y_COORD`/`X_COORD` decimal-degree columns SanGIS publishes, then fall back to
# `LATITUDE`/`LONGITUDE` spellings; rows with neither route to the geocoder via
# the `incident_address` / `ADDRESS` candidates and the needs_geocode declaration.
# ---------------------------------------------------------------------------
SAN_JOSE_PERMITS_FIELD_MAP: Dict[str, list[str]] = {
    "job_id": ["FOLDERNUMBER", "FOLDERRSN"],
    "issuance_date": ["ISSUEDATE"],
    "job_type": ["FOLDERNAME", "FOLDERDESC", "SUBTYPEDESCRIPTION"],
    "cost": ["PERMITVALUATION"],
    "status": ["Status", "PERMITAPPROVALS"],
    "address_street": ["gx_location"],
    "zipcode": ["gx_location"],
    "bbl": ["ASSESSORS_PARCEL_NUMBER"],
}

SAN_JOSE_311_FIELD_MAP: Dict[str, list[str]] = {
    "incident_id": ["Incident_ID"],
    "complaint_type": ["Service Type", "Category"],
    "created_date": ["Date Created"],
    "closed_date": ["Date Last Updated"],
    "status": ["Status"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
    "descriptor": ["Category", "Department", "Source"],
}


# Context suffix fed to the ADR-0004 geocoder. San Jose addresses already carry
# "CA", so the geocoder's _STATE_RE short-circuits and never appends this
# (avoiding a doubled-context query like "123 MAIN ST, SAN JOSE, CA, San Jose, CA").
SAN_JOSE_GEOCODE_CONTEXT = "San Jose, CA"


# Single dispatch surface consumed by field_maps_san_jose.FIELD_MAP. Keyed by
# FeedType value string so the spine can wire either feed independently.
SAN_JOSE_FIELD_MAPS: Dict[str, Dict[str, list[str]]] = {
    "permits": SAN_JOSE_PERMITS_FIELD_MAP,
    "311": SAN_JOSE_311_FIELD_MAP,
}
