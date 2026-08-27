"""Norfolk Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides comprehensive neighborhood metadata, camera positioning, investment
metrics, division catalog, and geographic bounding boxes for the independent
City of Norfolk, VA (Hampton Roads).

Feed scope (2026-08 re-probe; supersedes docs/research/socrata-sweep.md):
Norfolk registers TWO Socrata feeds on data.norfolk.gov —
  * PERMITS  ``fahm-yuh4``  (watermark ``issue_date``)
  * DEEDS    ``qva7-tzrf``  (watermark ``transfer_date``)
The 311 feed ``nbyu-xjez`` carries location as a bare address STRING (no point
object) and business licenses ``dpi6-sct5`` carry no geometry at all; both are
DEFERRED pending an address-geocoding capability. Do not register them yet.

FY rotation caveat (DEEDS): Norfolk publishes property-sales as annual
fiscal-year datasets FY23...FY27. Register the current-year file and rotate
the dataset ID each July 1 (see ingestion runbook).

Known quirk: the permits feed contains future-dated rows (scheduled filings,
application/issue dates observed out to 2027-01); watermark polling tolerates
them, downstream analytics should filter issuance_date <= now().
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# City of Norfolk plus its immediate edges. Feeds are city-scoped so all
# permit/sales rows are Norfolk addresses; the box deliberately EXCLUDES
# Portsmouth (-76.36 west), Chesapeake, and Virginia Beach.
NORFOLK_METRO_BBOX: Dict[str, float] = {
    "min_lat": 36.83,
    "max_lat": 37.04,
    "min_lng": -76.35,
    "max_lng": -76.17,
}

# 5 Norfolk Division Bounding Boxes (strictly nested inside the metro bbox)
NORFOLK_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_WATERFRONT":     {"min_lat": 36.840, "max_lat": 36.900, "min_lng": -76.315, "max_lng": -76.280},
    "GHENT_WESTBURG":          {"min_lat": 36.850, "max_lat": 36.905, "min_lng": -76.310, "max_lng": -76.255},
    "OCEAN_VIEW":              {"min_lat": 36.915, "max_lat": 37.040, "min_lng": -76.350, "max_lng": -76.240},
    "CENTRAL_MILITARY_CIRCLE": {"min_lat": 36.870, "max_lat": 36.920, "min_lng": -76.270, "max_lng": -76.205},
    "SOUTH_NORFOLK_BERKLEY":   {"min_lat": 36.830, "max_lat": 36.880, "min_lng": -76.300, "max_lng": -76.230},
}


def is_in_norfolk_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Norfolk Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        NORFOLK_METRO_BBOX["min_lat"] <= lat <= NORFOLK_METRO_BBOX["max_lat"]
        and NORFOLK_METRO_BBOX["min_lng"] <= lng <= NORFOLK_METRO_BBOX["max_lng"]
    )


def is_in_norfolk(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_norfolk_metro`."""
    return is_in_norfolk_metro(lat, lng)


# ---------------------------------------------------------------------------
# Comprehensive Norfolk Submarket Registry (13 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

NORFOLK_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_WATERFRONT (3 Submarkets)
    # =======================================================================
    "Downtown Norfolk & Waterfront": SubmarketMeta(
        name="Downtown Norfolk & Waterfront",
        borough="DOWNTOWN_WATERFRONT",
        lat=36.8505,
        lng=-76.2930,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.90,
        capex=8600000.0,
        permit_vel=50.0,
        shift_ratio=1.62,
        sla=66.0,
        description="Elizabeth River waterfront CBD anchored by USS Wisconsin, Nauticus, Waterside District, and the Dominion Enterprises tower boom along Main Street.",
        city_id="norfolk",
    ),
    "NEON Arts District": SubmarketMeta(
        name="NEON Arts District",
        borough="DOWNTOWN_WATERFRONT",
        lat=36.8620,
        lng=-76.2905,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.78,
        capex=4200000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=58.0,
        description="Gallery-and-mural arts corridor on Granby Street's north end converting warehouses into studios, breweries, and infill apartments.",
        city_id="norfolk",
    ),
    "Lamberts Point": SubmarketMeta(
        name="Lamberts Point",
        borough="DOWNTOWN_WATERFRONT",
        lat=36.8720,
        lng=-76.3060,
        zoom=14.5,
        pitch=35.0,
        base_lims=0.66,
        capex=3200000.0,
        permit_vel=24.0,
        shift_ratio=1.22,
        sla=46.0,
        description="Coal-pier and rail-front neighborhood beside Old Dominion University rebuilding its rowhouse stock amid industrial-buffer redevelopment.",
        city_id="norfolk",
    ),

    # =======================================================================
    # GHENT_WESTBURG (3 Submarkets)
    # =======================================================================
    "Ghent": SubmarketMeta(
        name="Ghent",
        borough="GHENT_WESTBURG",
        lat=36.8640,
        lng=-76.2820,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.88,
        capex=7200000.0,
        permit_vel=44.0,
        shift_ratio=1.52,
        sla=62.0,
        description="Historic brick rowhouse district around the Harrison Opera House and Colley Avenue retail spine with relentless renovation demand.",
        city_id="norfolk",
    ),
    "West Ghent & Page Point": SubmarketMeta(
        name="West Ghent & Page Point",
        borough="GHENT_WESTBURG",
        lat=36.8700,
        lng=-76.3000,
        zoom=14.5,
        pitch=35.0,
        base_lims=0.82,
        capex=5800000.0,
        permit_vel=34.0,
        shift_ratio=1.42,
        sla=54.0,
        description="Colonial Place-adjacent enclave of craftsman homes fronting the Elizabeth River with steady high-end remodel activity.",
        city_id="norfolk",
    ),
    "Wards Corner": SubmarketMeta(
        name="Wards Corner",
        borough="GHENT_WESTBURG",
        lat=36.8980,
        lng=-76.2650,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=32.0,
        shift_ratio=1.30,
        sla=48.0,
        description="Mid-century commercial crossroads of Hampton Blvd and Granby undergoing planned mixed-use redevelopment at the Talbot Park edge.",
        city_id="norfolk",
    ),

    # =======================================================================
    # OCEAN_VIEW (3 Submarkets)
    # =======================================================================
    "Ocean View": SubmarketMeta(
        name="Ocean View",
        borough="OCEAN_VIEW",
        lat=36.9450,
        lng=-76.3300,
        zoom=14.5,
        pitch=35.0,
        base_lims=0.72,
        capex=4600000.0,
        permit_vel=28.0,
        shift_ratio=1.28,
        sla=44.0,
        description="Chesapeake Bay beach-strip cottages and condo corridors along Ocean View Avenue with Naval Station Norfolk visible across Willoughby Bay.",
        city_id="norfolk",
    ),
    "East Beach": SubmarketMeta(
        name="East Beach",
        borough="OCEAN_VIEW",
        lat=36.9670,
        lng=-76.2850,
        zoom=15.0,
        pitch=35.0,
        base_lims=0.84,
        capex=6900000.0,
        permit_vel=38.0,
        shift_ratio=1.48,
        sla=52.0,
        description="New Urbanist master-planned bayfront community of cottage courts and marina village commanding premium coastal pricing.",
        city_id="norfolk",
    ),
    "Willoughby Spit": SubmarketMeta(
        name="Willoughby Spit",
        borough="OCEAN_VIEW",
        lat=36.9230,
        lng=-76.3180,
        zoom=15.0,
        pitch=35.0,
        base_lims=0.68,
        capex=3400000.0,
        permit_vel=22.0,
        shift_ratio=1.20,
        sla=40.0,
        description="Slim sand-spit peninsula of bungalow stock between the Bay and the HRBT approach with flood-resilience retrofit demand.",
        city_id="norfolk",
    ),

    # =======================================================================
    # CENTRAL_MILITARY_CIRCLE (2 Submarkets)
    # =======================================================================
    "Military Circle": SubmarketMeta(
        name="Military Circle",
        borough="CENTRAL_MILITARY_CIRCLE",
        lat=36.8880,
        lng=-76.2450,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.70,
        capex=5200000.0,
        permit_vel=34.0,
        shift_ratio=1.34,
        sla=50.0,
        description="Mall-redevelopment district near Sentara Norfolk General Hospital's Janaf corridor pivoting from retail boxes to medical-adjacent mixed use.",
        city_id="norfolk",
    ),
    "Norview": SubmarketMeta(
        name="Norview",
        borough="CENTRAL_MILITARY_CIRCLE",
        lat=36.8990,
        lng=-76.2300,
        zoom=14.0,
        pitch=30.0,
        base_lims=0.64,
        capex=2900000.0,
        permit_vel=24.0,
        shift_ratio=1.18,
        sla=38.0,
        description="Post-war starter-home neighborhoods under the NAS Norfolk flight path with affordable entry pricing and steady investor rehab flow.",
        city_id="norfolk",
    ),

    # =======================================================================
    # SOUTH_NORFOLK_BERKLEY (2 Submarkets)
    # =======================================================================
    "Berkley": SubmarketMeta(
        name="Berkley",
        borough="SOUTH_NORFOLK_BERKLEY",
        lat=36.8520,
        lng=-76.2830,
        zoom=15.0,
        pitch=35.0,
        base_lims=0.62,
        capex=2600000.0,
        permit_vel=22.0,
        shift_ratio=1.16,
        sla=34.0,
        description="Historic shipyard-worker grid south of the Elizabeth River with century-old foursquares and early-stage riverfront reinvestment.",
        city_id="norfolk",
    ),
    "Campostella": SubmarketMeta(
        name="Campostella",
        borough="SOUTH_NORFOLK_BERKLEY",
        lat=36.8580,
        lng=-76.2640,
        zoom=14.5,
        pitch=30.0,
        base_lims=0.60,
        capex=2500000.0,
        permit_vel=22.0,
        shift_ratio=1.15,
        sla=30.0,
        description="Riverside residential district near the Virginia Zoo and Campostella Bridge anchoring South Norfolk's gradual appreciation curve.",
        city_id="norfolk",
    ),
}


# ---------------------------------------------------------------------------
# Norfolk Divisions Catalog
# ---------------------------------------------------------------------------

NORFOLK_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_WATERFRONT": BoroughMeta(
        name="DOWNTOWN_WATERFRONT",
        center_lat=36.8580,
        center_lng=-76.2930,
        zoom=13.5,
        bbox=NORFOLK_DIVISION_BBOXES["DOWNTOWN_WATERFRONT"],
        submarkets=[k for k, v in NORFOLK_SUBMARKETS.items() if v.borough == "DOWNTOWN_WATERFRONT"],
        city_id="norfolk",
    ),
    "GHENT_WESTBURG": BoroughMeta(
        name="GHENT_WESTBURG",
        center_lat=36.8770,
        center_lng=-76.2820,
        zoom=13.5,
        bbox=NORFOLK_DIVISION_BBOXES["GHENT_WESTBURG"],
        submarkets=[k for k, v in NORFOLK_SUBMARKETS.items() if v.borough == "GHENT_WESTBURG"],
        city_id="norfolk",
    ),
    "OCEAN_VIEW": BoroughMeta(
        name="OCEAN_VIEW",
        center_lat=36.9450,
        center_lng=-76.2950,
        zoom=12.5,
        bbox=NORFOLK_DIVISION_BBOXES["OCEAN_VIEW"],
        submarkets=[k for k, v in NORFOLK_SUBMARKETS.items() if v.borough == "OCEAN_VIEW"],
        city_id="norfolk",
    ),
    "CENTRAL_MILITARY_CIRCLE": BoroughMeta(
        name="CENTRAL_MILITARY_CIRCLE",
        center_lat=36.8930,
        center_lng=-76.2380,
        zoom=13.0,
        bbox=NORFOLK_DIVISION_BBOXES["CENTRAL_MILITARY_CIRCLE"],
        submarkets=[k for k, v in NORFOLK_SUBMARKETS.items() if v.borough == "CENTRAL_MILITARY_CIRCLE"],
        city_id="norfolk",
    ),
    "SOUTH_NORFOLK_BERKLEY": BoroughMeta(
        name="SOUTH_NORFOLK_BERKLEY",
        center_lat=36.8550,
        center_lng=-76.2740,
        zoom=13.5,
        bbox=NORFOLK_DIVISION_BBOXES["SOUTH_NORFOLK_BERKLEY"],
        submarkets=[k for k, v in NORFOLK_SUBMARKETS.items() if v.borough == "SOUTH_NORFOLK_BERKLEY"],
        city_id="norfolk",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=NORFOLK_METRO_BBOX,
    division_bboxes=NORFOLK_DIVISION_BBOXES,
    submarkets=NORFOLK_SUBMARKETS,
    divisions=NORFOLK_DIVISIONS,
    contains=is_in_norfolk_metro,
)
