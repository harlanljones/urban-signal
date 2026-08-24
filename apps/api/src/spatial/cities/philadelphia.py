"""Philadelphia Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides comprehensive neighborhood metadata, camera positioning, investment
metrics, division catalog, and geographic bounding boxes for the City of
Philadelphia, PA — the first all-CARTO city (all four feeds register with
``platform="carto"`` against phl.carto.com).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Philadelphia Metro bounding box, clamped to the City of Philadelphia proper
# (no NJ river edge) so every CARTO feed row geocodes inside it. Live fixture
# coordinates verified inside on 2026-08-23 (permits/licenses/rtt WKB points,
# public_cases_fc lat/lon).
PHILADELPHIA_METRO_BBOX: Dict[str, float] = {
    "min_lat": 39.87,
    "max_lat": 40.14,
    "min_lng": -75.28,
    "max_lng": -74.95,
}

# 8 Philadelphia Metro Division Bounding Boxes (nested inside the metro bbox).
PHL_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "CENTER_CITY_RITTENHOUSE":   {"min_lat": 39.938, "max_lat": 39.972, "min_lng": -75.195, "max_lng": -75.152},
    "OLD_CITY_NORTHERN_LIBERTIES": {"min_lat": 39.946, "max_lat": 39.982, "min_lng": -75.152, "max_lng": -75.118},
    "SOUTH_PHILLY_PASSYUNK":     {"min_lat": 39.908, "max_lat": 39.952, "min_lng": -75.200, "max_lng": -75.150},
    "WEST_PHILLY_UNIVERSITY_CITY": {"min_lat": 39.933, "max_lat": 39.972, "min_lng": -75.230, "max_lng": -75.188},
    "NORTH_PHILLY_TEMPLE":       {"min_lat": 39.963, "max_lat": 40.040, "min_lng": -75.235, "max_lng": -75.130},
    "NORTHEAST_ROOSEVELT_BLVD":  {"min_lat": 40.005, "max_lat": 40.090, "min_lng": -75.115, "max_lng": -75.030},
    "GERMANTOWN_MT_AIRY":        {"min_lat": 40.032, "max_lat": 40.100, "min_lng": -75.210, "max_lng": -75.160},
    "RIVER_WARDS_KENSINGTON":    {"min_lat": 39.960, "max_lat": 40.010, "min_lng": -75.150, "max_lng": -75.105},
}


def is_in_philadelphia_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Philadelphia Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        PHILADELPHIA_METRO_BBOX["min_lat"] <= lat <= PHILADELPHIA_METRO_BBOX["max_lat"]
        and PHILADELPHIA_METRO_BBOX["min_lng"] <= lng <= PHILADELPHIA_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_philadelphia = is_in_philadelphia_metro


# ---------------------------------------------------------------------------
# Comprehensive Philadelphia Submarket Registry (18 Submarkets Across 8 Divisions)
# ---------------------------------------------------------------------------

PHL_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # CENTER_CITY_RITTENHOUSE (2 Submarkets)
    # =======================================================================
    "Rittenhouse Square": SubmarketMeta(
        name="Rittenhouse Square",
        borough="CENTER_CITY_RITTENHOUSE",
        lat=39.9526,
        lng=-75.1700,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.92,
        capex=11000000.0,
        permit_vel=56.0,
        shift_ratio=1.68,
        sla=72.0,
        description="The region's premier retail-and-residence square: Walnut Street luxury corridor, office towers converting to residential, and sustained high-rise infill demand.",
        city_id="philadelphia",
    ),
    "Market East": SubmarketMeta(
        name="Market East",
        borough="CENTER_CITY_RITTENHOUSE",
        lat=39.9523,
        lng=-75.1600,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=44.0,
        shift_ratio=1.44,
        sla=58.0,
        description="Jefferson and Convention Center district undergoing the Gallery/East Market redevelopment, hospital-anchor demand, and adaptive-reuse of former department stores.",
        city_id="philadelphia",
    ),

    # =======================================================================
    # OLD_CITY_NORTHERN_LIBERTIES (1 Submarket)
    # =======================================================================
    "Old City & Northern Liberties": SubmarketMeta(
        name="Old City & Northern Liberties",
        borough="OLD_CITY_NORTHERN_LIBERTIES",
        lat=39.9560,
        lng=-75.1420,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.86,
        capex=8000000.0,
        permit_vel=48.0,
        shift_ratio=1.48,
        sla=54.0,
        description="Colonial-grid gallery district meeting the Piazza nightlife corridor; condo conversions, boutique hotel demand, and I-95 cap waterfront spillover.",
        city_id="philadelphia",
    ),

    # =======================================================================
    # SOUTH_PHILLY_PASSYUNK (3 Submarkets)
    # =======================================================================
    "East Passyunk": SubmarketMeta(
        name="East Passyunk",
        borough="SOUTH_PHILLY_PASSYUNK",
        lat=39.9270,
        lng=-75.1670,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.82,
        capex=5800000.0,
        permit_vel=38.0,
        shift_ratio=1.42,
        sla=48.0,
        description="Restaurant-row rowhouse corridor with rapid appreciation, BYO dining economy, and tight two-story brick housing stock feeding renovation permits.",
        city_id="philadelphia",
    ),
    "Pennsport": SubmarketMeta(
        name="Pennsport",
        borough="SOUTH_PHILLY_PASSYUNK",
        lat=39.9250,
        lng=-75.1540,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.76,
        capex=4600000.0,
        permit_vel=42.0,
        shift_ratio=1.38,
        sla=40.0,
        description="Moyamensing builder belt between Queen Village and the stadiums; trio-to-condo redevelopment pressure from the Delaware waterfront spillover.",
        city_id="philadelphia",
    ),
    "Graduate Hospital": SubmarketMeta(
        name="Graduate Hospital",
        borough="SOUTH_PHILLY_PASSYUNK",
        lat=39.9455,
        lng=-75.1770,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=40.0,
        shift_ratio=1.46,
        sla=52.0,
        description="G-Ho brownstone revival around South Street West with first-in-class school demand, medical-office anchors, and dense triplex conversion activity.",
        city_id="philadelphia",
    ),

    # =======================================================================
    # WEST_PHILLY_UNIVERSITY_CITY (2 Submarkets)
    # =======================================================================
    "University City & Drexel uCity": SubmarketMeta(
        name="University City & Drexel uCity",
        borough="WEST_PHILLY_UNIVERSITY_CITY",
        lat=39.9530,
        lng=-75.1920,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.88,
        capex=10500000.0,
        permit_vel=52.0,
        shift_ratio=1.62,
        sla=64.0,
        description="Penn/Drexel innovation district: uCity Square lab build-out, Schuylkill Yards towers, and institutional demand driving the region's deepest crane count outside Center City.",
        city_id="philadelphia",
    ),
    "Spruce Hill": SubmarketMeta(
        name="Spruce Hill",
        borough="WEST_PHILLY_UNIVERSITY_CITY",
        lat=39.9580,
        lng=-75.2050,
        zoom=14.5,
        pitch=40.0,
        base_lims=0.79,
        capex=4800000.0,
        permit_vel=30.0,
        shift_ratio=1.32,
        sla=44.0,
        description="Victorian twin-and-mansion academic enclave with Penn faculty demand, landmark districts, and steady single-family restoration permitting.",
        city_id="philadelphia",
    ),

    # =======================================================================
    # NORTH_PHILLY_TEMPLE (3 Submarkets)
    # =======================================================================
    "Temple/Liacouras Corridor": SubmarketMeta(
        name="Temple/Liacouras Corridor",
        borough="NORTH_PHILLY_TEMPLE",
        lat=39.9810,
        lng=-75.1550,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.62,
        capex=3400000.0,
        permit_vel=36.0,
        shift_ratio=1.24,
        sla=34.0,
        description="Student-housing frontier around Temple's main campus: purpose-built dorm supply, corner-store commercial revival, and high-yield rental spreads.",
        city_id="philadelphia",
    ),
    "Fairmount & Brewerytown": SubmarketMeta(
        name="Fairmount & Brewerytown",
        borough="NORTH_PHILLY_TEMPLE",
        lat=39.9730,
        lng=-75.1850,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.81,
        capex=5600000.0,
        permit_vel=42.0,
        shift_ratio=1.44,
        sla=50.0,
        description="Museum-district rowhouses meeting Brewerytown's brewer-row redevelopment along Girard Avenue with Art Museum spillover and brewery-heritage branding.",
        city_id="philadelphia",
    ),
    "Manayunk": SubmarketMeta(
        name="Manayunk",
        borough="NORTH_PHILLY_TEMPLE",
        lat=40.0230,
        lng=-75.2270,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.77,
        capex=5000000.0,
        permit_vel=32.0,
        shift_ratio=1.36,
        sla=46.0,
        description="Canal-side hillside village with Main Street retail, towpath recreation demand, and steep-street new construction on former mill land.",
        city_id="philadelphia",
    ),

    # =======================================================================
    # NORTHEAST_ROOSEVELT_BLVD (2 Submarkets)
    # =======================================================================
    "Mayfair": SubmarketMeta(
        name="Mayfair",
        borough="NORTHEAST_ROOSEVELT_BLVD",
        lat=40.0260,
        lng=-75.0880,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.68,
        capex=3200000.0,
        permit_vel=26.0,
        shift_ratio=1.20,
        sla=32.0,
        description="Frankford-El terminus neighborhood of twins and corner stores along Roosevelt Boulevard with value-priced entry stock and steady owner-occupant demand.",
        city_id="philadelphia",
    ),
    "Fox Chase": SubmarketMeta(
        name="Fox Chase",
        borough="NORTHEAST_ROOSEVELT_BLVD",
        lat=40.0770,
        lng=-75.0750,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.72,
        capex=2900000.0,
        permit_vel=20.0,
        shift_ratio=1.16,
        sla=28.0,
        description="Rail-commuter leafy Northeast edge with Fox Chase Cancer Center anchor, detached and twin housing stock, and low-turnover family ownership.",
        city_id="philadelphia",
    ),

    # =======================================================================
    # GERMANTOWN_MT_AIRY (2 Submarkets)
    # =======================================================================
    "Germantown Ave Corridor": SubmarketMeta(
        name="Germantown Ave Corridor",
        borough="GERMANTOWN_MT_AIRY",
        lat=40.0400,
        lng=-75.1800,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.55,
        capex=2400000.0,
        permit_vel=24.0,
        shift_ratio=1.14,
        sla=26.0,
        description="Historic colonial commercial spine through Germantown with surplus church and mill stock, deep-discount acquisition, and historic-tax-credit rehabilitation upside.",
        city_id="philadelphia",
    ),
    "Chestnut Hill": SubmarketMeta(
        name="Chestnut Hill",
        borough="GERMANTOWN_MT_AIRY",
        lat=40.0650,
        lng=-75.2060,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.83,
        capex=6800000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=56.0,
        description="Garden-suburb estate district at the regional rail terminus with Germantown Avenue boutiques, arboretum anchors, and preservation-constrained premium stock.",
        city_id="philadelphia",
    ),

    # =======================================================================
    # RIVER_WARDS_KENSINGTON (3 Submarkets)
    # =======================================================================
    "Fishtown": SubmarketMeta(
        name="Fishtown",
        borough="RIVER_WARDS_KENSINGTON",
        lat=39.9700,
        lng=-75.1310,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.87,
        capex=7200000.0,
        permit_vel=50.0,
        shift_ratio=1.56,
        sla=62.0,
        description="The city's bar-and-restaurant capital turned fastest-appreciating rowhouse market; Frankford Avenue corridors and Delaware-adjacent new construction.",
        city_id="philadelphia",
    ),
    "Port Richmond": SubmarketMeta(
        name="Port Richmond",
        borough="RIVER_WARDS_KENSINGTON",
        lat=39.9780,
        lng=-75.1170,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=46.0,
        shift_ratio=1.46,
        sla=44.0,
        description="Polish-cathedral river ward absorbing Fishtown spillover: affordable brick twins, I-95 industrial edge, and builder townhome assemblies.",
        city_id="philadelphia",
    ),
    "Kensington/Frankford Ave": SubmarketMeta(
        name="Kensington/Frankford Ave",
        borough="RIVER_WARDS_KENSINGTON",
        lat=39.9860,
        lng=-75.1330,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.52,
        capex=2000000.0,
        permit_vel=34.0,
        shift_ratio=1.10,
        sla=30.0,
        description="Post-industrial creative frontier along the El: vacant-lot assemblies, artist-live-work conversions, and the widest value spread in the River Wards.",
        city_id="philadelphia",
    ),
}


# ---------------------------------------------------------------------------
# Philadelphia Divisions Catalog
# ---------------------------------------------------------------------------

PHL_DIVISIONS: Dict[str, BoroughMeta] = {
    "CENTER_CITY_RITTENHOUSE": BoroughMeta(
        name="CENTER_CITY_RITTENHOUSE",
        center_lat=39.9525,
        center_lng=-75.1700,
        zoom=13.5,
        bbox=PHL_DIVISION_BBOXES["CENTER_CITY_RITTENHOUSE"],
        submarkets=[k for k, v in PHL_SUBMARKETS.items() if v.borough == "CENTER_CITY_RITTENHOUSE"],
        city_id="philadelphia",
    ),
    "OLD_CITY_NORTHERN_LIBERTIES": BoroughMeta(
        name="OLD_CITY_NORTHERN_LIBERTIES",
        center_lat=39.9570,
        center_lng=-75.1400,
        zoom=14.0,
        bbox=PHL_DIVISION_BBOXES["OLD_CITY_NORTHERN_LIBERTIES"],
        submarkets=[k for k, v in PHL_SUBMARKETS.items() if v.borough == "OLD_CITY_NORTHERN_LIBERTIES"],
        city_id="philadelphia",
    ),
    "SOUTH_PHILLY_PASSYUNK": BoroughMeta(
        name="SOUTH_PHILLY_PASSYUNK",
        center_lat=39.9310,
        center_lng=-75.1700,
        zoom=13.0,
        bbox=PHL_DIVISION_BBOXES["SOUTH_PHILLY_PASSYUNK"],
        submarkets=[k for k, v in PHL_SUBMARKETS.items() if v.borough == "SOUTH_PHILLY_PASSYUNK"],
        city_id="philadelphia",
    ),
    "WEST_PHILLY_UNIVERSITY_CITY": BoroughMeta(
        name="WEST_PHILLY_UNIVERSITY_CITY",
        center_lat=39.9540,
        center_lng=-75.1980,
        zoom=13.5,
        bbox=PHL_DIVISION_BBOXES["WEST_PHILLY_UNIVERSITY_CITY"],
        submarkets=[k for k, v in PHL_SUBMARKETS.items() if v.borough == "WEST_PHILLY_UNIVERSITY_CITY"],
        city_id="philadelphia",
    ),
    "NORTH_PHILLY_TEMPLE": BoroughMeta(
        name="NORTH_PHILLY_TEMPLE",
        center_lat=39.9920,
        center_lng=-75.1900,
        zoom=12.5,
        bbox=PHL_DIVISION_BBOXES["NORTH_PHILLY_TEMPLE"],
        submarkets=[k for k, v in PHL_SUBMARKETS.items() if v.borough == "NORTH_PHILLY_TEMPLE"],
        city_id="philadelphia",
    ),
    "NORTHEAST_ROOSEVELT_BLVD": BoroughMeta(
        name="NORTHEAST_ROOSEVELT_BLVD",
        center_lat=40.0450,
        center_lng=-75.0780,
        zoom=12.5,
        bbox=PHL_DIVISION_BBOXES["NORTHEAST_ROOSEVELT_BLVD"],
        submarkets=[k for k, v in PHL_SUBMARKETS.items() if v.borough == "NORTHEAST_ROOSEVELT_BLVD"],
        city_id="philadelphia",
    ),
    "GERMANTOWN_MT_AIRY": BoroughMeta(
        name="GERMANTOWN_MT_AIRY",
        center_lat=40.0520,
        center_lng=-75.1880,
        zoom=12.5,
        bbox=PHL_DIVISION_BBOXES["GERMANTOWN_MT_AIRY"],
        submarkets=[k for k, v in PHL_SUBMARKETS.items() if v.borough == "GERMANTOWN_MT_AIRY"],
        city_id="philadelphia",
    ),
    "RIVER_WARDS_KENSINGTON": BoroughMeta(
        name="RIVER_WARDS_KENSINGTON",
        center_lat=39.9780,
        center_lng=-75.1270,
        zoom=13.0,
        bbox=PHL_DIVISION_BBOXES["RIVER_WARDS_KENSINGTON"],
        submarkets=[k for k, v in PHL_SUBMARKETS.items() if v.borough == "RIVER_WARDS_KENSINGTON"],
        city_id="philadelphia",
    ),
}
