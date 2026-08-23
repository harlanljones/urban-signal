"""Seattle Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides comprehensive neighborhood metadata, camera positioning, investment
metrics, division catalog, and geographic bounding boxes for Seattle and the
King County metro area, WA.
"""

from typing import Dict
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Seattle Metro overall bounding box (clamped to King County so that the King
# County Assessor parcel-sales feed stays fully contained).
SEATTLE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 47.28,
    "max_lat": 47.78,
    "min_lng": -122.43,
    "max_lng": -122.00,
}

# 4 Seattle Metro Division Bounding Boxes
SEATTLE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "SEATTLE_CORE": {"min_lat": 47.580, "max_lat": 47.645, "min_lng": -122.370, "max_lng": -122.290},
    "NORTH_KING":   {"min_lat": 47.645, "max_lat": 47.745, "min_lng": -122.425, "max_lng": -122.280},
    "EASTSIDE":     {"min_lat": 47.500, "max_lat": 47.770, "min_lng": -122.260, "max_lng": -122.010},
    "SOUTH_KING":   {"min_lat": 47.290, "max_lat": 47.590, "min_lng": -122.420, "max_lng": -122.150},
}


def is_in_seattle_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Seattle Metropolitan bounds."""
    return (
        SEATTLE_METRO_BBOX["min_lat"] <= lat <= SEATTLE_METRO_BBOX["max_lat"]
        and SEATTLE_METRO_BBOX["min_lng"] <= lng <= SEATTLE_METRO_BBOX["max_lng"]
    )


# ---------------------------------------------------------------------------
# Comprehensive Seattle Submarket Registry (20 Submarkets Across 4 Divisions)
# ---------------------------------------------------------------------------

SEATTLE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # SEATTLE_CORE (5 Submarkets)
    # =======================================================================
    "Downtown Core & Waterfront": SubmarketMeta(
        name="Downtown Core & Waterfront",
        borough="SEATTLE_CORE",
        lat=47.6097,
        lng=-122.3330,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.90,
        capex=13500000.0,
        permit_vel=55.0,
        shift_ratio=1.58,
        sla=66.0,
        description="Pike Place-Third Avenue retail spine, office towers, and waterfront redevelopment core anchored by the Convention Center expansion and waterfront park rebuild.",
        city_id="seattle",
    ),
    "South Lake Union": SubmarketMeta(
        name="South Lake Union",
        borough="SEATTLE_CORE",
        lat=47.6264,
        lng=-122.3381,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.94,
        capex=14000000.0,
        permit_vel=64.0,
        shift_ratio=1.70,
        sla=72.0,
        description="Amazon headquarters biotech and life-science district with the region's densest construction crane count and streetcar-served mixed-use infill.",
        city_id="seattle",
    ),
    "Belltown/Denny Triangle": SubmarketMeta(
        name="Belltown/Denny Triangle",
        borough="SEATTLE_CORE",
        lat=47.6150,
        lng=-122.3450,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.87,
        capex=9800000.0,
        permit_vel=52.0,
        shift_ratio=1.52,
        sla=76.0,
        description="Condo towers, nightlife corridors, and convention-center expansion infill between Denny Park and Elliott Bay.",
        city_id="seattle",
    ),
    "Capitol Hill/First Hill": SubmarketMeta(
        name="Capitol Hill/First Hill",
        borough="SEATTLE_CORE",
        lat=47.6180,
        lng=-122.3150,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.86,
        capex=9200000.0,
        permit_vel=48.0,
        shift_ratio=1.46,
        sla=80.0,
        description="Dense mixed-use nightlife and medical-institutional ridge including Swedish Medical Center, Seattle University, and Link light-rail station areas.",
        city_id="seattle",
    ),
    "Pioneer Square/Chinatown-ID": SubmarketMeta(
        name="Pioneer Square/Chinatown-ID",
        borough="SEATTLE_CORE",
        lat=47.5995,
        lng=-122.3315,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.82,
        capex=8400000.0,
        permit_vel=46.0,
        shift_ratio=1.44,
        sla=68.0,
        description="Historic loft and stadium-district adaptive reuse with light-rail gateway traffic, Climate Pledge Arena demand, and SODO industrial edge dynamics.",
        city_id="seattle",
    ),

    # =======================================================================
    # NORTH_KING (5 Submarkets)
    # =======================================================================
    "Ballard": SubmarketMeta(
        name="Ballard",
        borough="NORTH_KING",
        lat=47.6685,
        lng=-122.3862,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.88,
        capex=10200000.0,
        permit_vel=58.0,
        shift_ratio=1.56,
        sla=74.0,
        description="Maritime-industrial heritage converting to Nordic-themed retail, brewery corridors, and multifamily development along Ballard Avenue and Leary Way.",
        city_id="seattle",
    ),
    "Fremont/Wallingford": SubmarketMeta(
        name="Fremont/Wallingford",
        borough="NORTH_KING",
        lat=47.6580,
        lng=-122.3430,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.87,
        capex=9600000.0,
        permit_vel=54.0,
        shift_ratio=1.50,
        sla=70.0,
        description="Eccentric creative corridor under the Aurora Bridge with tech satellite offices, canal-front retail, and Google campus expansion.",
        city_id="seattle",
    ),
    "University District/Roosevelt": SubmarketMeta(
        name="University District/Roosevelt",
        borough="NORTH_KING",
        lat=47.6605,
        lng=-122.3130,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.85,
        capex=8800000.0,
        permit_vel=56.0,
        shift_ratio=1.48,
        sla=62.0,
        description="University of Washington anchor economy with Link-rail transit-oriented upzoning along Roosevelt Avenue and the Ave commercial spine.",
        city_id="seattle",
    ),
    "Queen Anne/Magnolia": SubmarketMeta(
        name="Queen Anne/Magnolia",
        borough="NORTH_KING",
        lat=47.6350,
        lng=-122.3600,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.84,
        capex=8000000.0,
        permit_vel=38.0,
        shift_ratio=1.34,
        sla=54.0,
        description="Hilltop residential enclaves overlooking Uptown arts retail, Seattle Center, and Interbay rail-served industrial land.",
        city_id="seattle",
    ),
    "Northgate/Lake City": SubmarketMeta(
        name="Northgate/Lake City",
        borough="NORTH_KING",
        lat=47.7120,
        lng=-122.3120,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.81,
        capex=7200000.0,
        permit_vel=50.0,
        shift_ratio=1.38,
        sla=44.0,
        description="Transit-oriented mall redevelopment into the NHL Kraken practice facility and ped-friendly district plus north-end affordable infill frontier.",
        city_id="seattle",
    ),

    # =======================================================================
    # EASTSIDE (5 Submarkets)
    # =======================================================================
    "Downtown Bellevue": SubmarketMeta(
        name="Downtown Bellevue",
        borough="EASTSIDE",
        lat=47.6101,
        lng=-122.2015,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.93,
        capex=13800000.0,
        permit_vel=60.0,
        shift_ratio=1.62,
        sla=64.0,
        description="Second CBD of the metro with Amazon and Microsoft towers, Bellevue Square luxury retail, and East Link light-rail expansion.",
        city_id="seattle",
    ),
    "Kirkland Waterfront": SubmarketMeta(
        name="Kirkland Waterfront",
        borough="EASTSIDE",
        lat=47.6815,
        lng=-122.2087,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.86,
        capex=9000000.0,
        permit_vel=40.0,
        shift_ratio=1.40,
        sla=56.0,
        description="Lakeside Google-corridor office market with MarinaPark civic frontage and boutique downtown retail along Lake Washington.",
        city_id="seattle",
    ),
    "Redmond/Overlake": SubmarketMeta(
        name="Redmond/Overlake",
        borough="EASTSIDE",
        lat=47.6580,
        lng=-122.1250,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.89,
        capex=10600000.0,
        permit_vel=52.0,
        shift_ratio=1.50,
        sla=50.0,
        description="Microsoft campus belt plus light-rail-linked downtown village redevelopment along the Redmond Technology Station corridor.",
        city_id="seattle",
    ),
    "Woodinville Wine Country": SubmarketMeta(
        name="Woodinville Wine Country",
        borough="EASTSIDE",
        lat=47.7546,
        lng=-122.1589,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.79,
        capex=6500000.0,
        permit_vel=30.0,
        shift_ratio=1.26,
        sla=82.0,
        description="Wine-country tourism district with Hollywood Hill tasting rooms, Tourist Mill light-industrial, and SR-522 logistics frontage.",
        city_id="seattle",
    ),
    "Issaquah/Sammamish": SubmarketMeta(
        name="Issaquah/Sammamish",
        borough="EASTSIDE",
        lat=47.5400,
        lng=-122.0350,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.85,
        capex=8600000.0,
        permit_vel=42.0,
        shift_ratio=1.36,
        sla=46.0,
        description="I-90 master-planned growth engine combining Grand Ridge tech campuses, Highlands rooftops, and Costco headquarters roots.",
        city_id="seattle",
    ),

    # =======================================================================
    # SOUTH_KING (5 Submarkets)
    # =======================================================================
    "West Seattle/Junction": SubmarketMeta(
        name="West Seattle/Junction",
        borough="SOUTH_KING",
        lat=47.5612,
        lng=-122.3868,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.83,
        capex=7800000.0,
        permit_vel=44.0,
        shift_ratio=1.40,
        sla=64.0,
        description="Beach-community retail node on California Avenue SW with bridge-constrained supply dynamics and Alki waterfront demand.",
        city_id="seattle",
    ),
    "Beacon Hill/Columbia City": SubmarketMeta(
        name="Beacon Hill/Columbia City",
        borough="SOUTH_KING",
        lat=47.5680,
        lng=-122.2960,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.82,
        capex=7000000.0,
        permit_vel=48.0,
        shift_ratio=1.46,
        sla=58.0,
        description="Link light-rail multicultural corridor with rapid Rainier Valley gentrification, landmark Columbia City historic district, and upzoned station areas.",
        city_id="seattle",
    ),
    "Georgetown/South Park": SubmarketMeta(
        name="Georgetown/South Park",
        borough="SOUTH_KING",
        lat=47.5450,
        lng=-122.3140,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.74,
        capex=5200000.0,
        permit_vel=36.0,
        shift_ratio=1.28,
        sla=48.0,
        description="Artist-industrial enclave amid Duwamish heavy manufacturing, airport freight corridors, and Airport Way adaptive reuse.",
        city_id="seattle",
    ),
    "Renton/Southcenter": SubmarketMeta(
        name="Renton/Southcenter",
        borough="SOUTH_KING",
        lat=47.4620,
        lng=-122.2400,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.80,
        capex=8200000.0,
        permit_vel=46.0,
        shift_ratio=1.32,
        sla=42.0,
        description="Boeing 737 plant plus Southcenter regional mall and the I-405 hotel-office cluster on the Cedar River waterfront.",
        city_id="seattle",
    ),
    "Kent Valley": SubmarketMeta(
        name="Kent Valley",
        borough="SOUTH_KING",
        lat=47.3809,
        lng=-122.2348,
        zoom=13.0,
        pitch=35.0,
        base_lims=0.72,
        capex=4800000.0,
        permit_vel=28.0,
        shift_ratio=1.22,
        sla=35.0,
        description="Puget Sound's largest warehouse and logistics submarket along Valley Freeway and the BNSF rail line.",
        city_id="seattle",
    ),
}


# ---------------------------------------------------------------------------
# Seattle Divisions Catalog
# ---------------------------------------------------------------------------

SEATTLE_DIVISIONS: Dict[str, BoroughMeta] = {
    "SEATTLE_CORE": BoroughMeta(
        name="SEATTLE_CORE",
        center_lat=47.6120,
        center_lng=-122.3300,
        zoom=12.5,
        bbox=SEATTLE_DIVISION_BBOXES["SEATTLE_CORE"],
        submarkets=[k for k, v in SEATTLE_SUBMARKETS.items() if v.borough == "SEATTLE_CORE"],
        city_id="seattle",
    ),
    "NORTH_KING": BoroughMeta(
        name="NORTH_KING",
        center_lat=47.6950,
        center_lng=-122.3530,
        zoom=12.0,
        bbox=SEATTLE_DIVISION_BBOXES["NORTH_KING"],
        submarkets=[k for k, v in SEATTLE_SUBMARKETS.items() if v.borough == "NORTH_KING"],
        city_id="seattle",
    ),
    "EASTSIDE": BoroughMeta(
        name="EASTSIDE",
        center_lat=47.6350,
        center_lng=-122.1350,
        zoom=11.5,
        bbox=SEATTLE_DIVISION_BBOXES["EASTSIDE"],
        submarkets=[k for k, v in SEATTLE_SUBMARKETS.items() if v.borough == "EASTSIDE"],
        city_id="seattle",
    ),
    "SOUTH_KING": BoroughMeta(
        name="SOUTH_KING",
        center_lat=47.4400,
        center_lng=-122.2850,
        zoom=11.5,
        bbox=SEATTLE_DIVISION_BBOXES["SOUTH_KING"],
        submarkets=[k for k, v in SEATTLE_SUBMARKETS.items() if v.borough == "SOUTH_KING"],
        city_id="seattle",
    ),
}
