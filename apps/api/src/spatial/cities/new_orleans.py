"""New Orleans Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of New Orleans
and the surrounding metro parishes (Orleans, Jefferson eastbank/westbank, and
St. Bernard), LA.

The metro bbox deliberately EXCLUDES the north shore (Lake Pontchartrain's
north side): the state occupational-license feed leaks Madisonville /
St. Tammany rows around latitude 30.38, which are out-of-parish noise for a
NOLA metro pipeline. max_lat=30.16 keeps every Orleans/Jefferson/St. Bernard
row inside the box while dropping those leaks (verified against live
fixtures on 2026-08-23).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# New Orleans Metro bounding box: Orleans + Jefferson + St. Bernard parishes
# only. North-shore St. Tammany (Madisonville ~30.38) intentionally excluded;
# see licenses-feed leak note in tests/unit/test_producers_new_orleans.py.
NEW_ORLEANS_METRO_BBOX: Dict[str, float] = {
    "min_lat": 29.82,
    "max_lat": 30.16,
    "min_lng": -90.30,
    "max_lng": -89.62,
}

# 9 New Orleans Metro Division Bounding Boxes. Approximate hand-authored
# geographies; borough resolution at ingest comes from coordinates via
# get_division_for_coordinate (council-district strings in the feeds are
# letters like "E", not names), so bboxes need only be sane and disjoint
# enough to resolve unambiguously near their centers.
NOLA_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "CBD_FRENCH_QUARTER":       {"min_lat": 29.93, "max_lat": 30.00, "min_lng": -90.10, "max_lng": -90.02},
    "BYWATER_MARIGNY":          {"min_lat": 29.95, "max_lat": 30.00, "min_lng": -90.05, "max_lng": -89.98},
    "UPTOWN_CARROLLTON":        {"min_lat": 29.90, "max_lat": 30.00, "min_lng": -90.15, "max_lng": -90.05},
    "MID_CITY":                 {"min_lat": 29.96, "max_lat": 30.04, "min_lng": -90.13, "max_lng": -90.05},
    "LAKEVIEW_GENTILLY":        {"min_lat": 29.98, "max_lat": 30.06, "min_lng": -90.15, "max_lng": -90.04},
    "NEW_ORLEANS_EAST":         {"min_lat": 29.99, "max_lat": 30.10, "min_lng": -90.08, "max_lng": -89.62},
    "WEST_BANK_ALGIERS":        {"min_lat": 29.86, "max_lat": 29.98, "min_lng": -90.08, "max_lng": -89.95},
    "JEFFERSON_METAIRIE_KENNER": {"min_lat": 29.87, "max_lat": 30.05, "min_lng": -90.30, "max_lng": -90.10},
    "ST_BERNARD_CHALMETTE":     {"min_lat": 29.82, "max_lat": 29.95, "min_lng": -90.10, "max_lng": -89.80},
}


def is_in_new_orleans_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the New Orleans Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        NEW_ORLEANS_METRO_BBOX["min_lat"] <= lat <= NEW_ORLEANS_METRO_BBOX["max_lat"]
        and NEW_ORLEANS_METRO_BBOX["min_lng"] <= lng <= NEW_ORLEANS_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_nola_metro = is_in_new_orleans_metro


NOLA_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # CBD_FRENCH_QUARTER (3 Submarkets)
    # =======================================================================
    "French Quarter & CBD Towers": SubmarketMeta(
        name="French Quarter & CBD Towers",
        borough="CBD_FRENCH_QUARTER",
        lat=29.9555,
        lng=-90.0685,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.92,
        capex=12000000.0,
        permit_vel=58.0,
        shift_ratio=1.7,
        sla=75.0,
        description="Historic Quarter grid beside the Poydras Street high-rise core, where hospitality-driven ground floor demand meets limited entitled supply.",
        city_id="new_orleans",
    ),
    "BioDistrict & University Medical": SubmarketMeta(
        name="BioDistrict & University Medical",
        borough="CBD_FRENCH_QUARTER",
        lat=29.9665,
        lng=-90.0885,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.84,
        capex=10500000.0,
        permit_vel=47.0,
        shift_ratio=1.56,
        sla=67.0,
        description="University Medical Center and the VA hospital anchoring a bioscience district with institutional expansion and supporting multifamily.",
        city_id="new_orleans",
    ),
    "Warehouse & Arts District": SubmarketMeta(
        name="Warehouse & Arts District",
        borough="CBD_FRENCH_QUARTER",
        lat=29.9455,
        lng=-90.0825,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.87,
        capex=9800000.0,
        permit_vel=44.0,
        shift_ratio=1.6,
        sla=70.0,
        description="Julia Row galleries and converted cotton warehouses carrying condo conversions and hotel-adjacent adaptive reuse.",
        city_id="new_orleans",
    ),
    # =======================================================================
    # BYWATER_MARIGNY (2 Submarkets)
    # =======================================================================
    "Bywater & St. Claude Corridor": SubmarketMeta(
        name="Bywater & St. Claude Corridor",
        borough="BYWATER_MARIGNY",
        lat=29.9685,
        lng=-90.0285,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.8,
        capex=4800000.0,
        permit_vel=38.0,
        shift_ratio=1.45,
        sla=58.0,
        description="Shotgun-grid neighbourhood along the St. Claude arts corridor with sustained small-scale renovation permitting.",
        city_id="new_orleans",
    ),
    "Marigny & Frenchmen Street": SubmarketMeta(
        name="Marigny & Frenchmen Street",
        borough="BYWATER_MARIGNY",
        lat=29.9725,
        lng=-90.0425,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=5200000.0,
        permit_vel=41.0,
        shift_ratio=1.49,
        sla=61.0,
        description="Music-venue economy around Frenchmen Street with Creole-cottage stock and short-term-rental policy shaping values.",
        city_id="new_orleans",
    ),
    # =======================================================================
    # UPTOWN_CARROLLTON (3 Submarkets)
    # =======================================================================
    "Magazine Street Retail Corridor": SubmarketMeta(
        name="Magazine Street Retail Corridor",
        borough="UPTOWN_CARROLLTON",
        lat=29.9325,
        lng=-90.0925,
        zoom=13.5,
        pitch=45.0,
        base_lims=0.86,
        capex=7200000.0,
        permit_vel=43.0,
        shift_ratio=1.53,
        sla=65.0,
        description="Six miles of independent retail and antiques through the Garden District edge, with historic-district review constraining change.",
        city_id="new_orleans",
    ),
    "Audubon & Riverbend": SubmarketMeta(
        name="Audubon & Riverbend",
        borough="UPTOWN_CARROLLTON",
        lat=29.9185,
        lng=-90.1185,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.88,
        capex=8500000.0,
        permit_vel=36.0,
        shift_ratio=1.57,
        sla=68.0,
        description="Zoo- and university-adjacent residential stock with the deepest-demand single-family market in Orleans Parish.",
        city_id="new_orleans",
    ),
    "Carrollton & Oak Street": SubmarketMeta(
        name="Carrollton & Oak Street",
        borough="UPTOWN_CARROLLTON",
        lat=29.9485,
        lng=-90.1325,
        zoom=13.5,
        pitch=43.0,
        base_lims=0.79,
        capex=5600000.0,
        permit_vel=39.0,
        shift_ratio=1.42,
        sla=57.0,
        description="Streetcar-served neighbourhood commercial node with levee-adjacent housing and steady infill renovation.",
        city_id="new_orleans",
    ),
    # =======================================================================
    # MID_CITY (2 Submarkets)
    # =======================================================================
    "City Park & Bayou St. John": SubmarketMeta(
        name="City Park & Bayou St. John",
        borough="MID_CITY",
        lat=29.9825,
        lng=-90.0925,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=6000000.0,
        permit_vel=40.0,
        shift_ratio=1.47,
        sla=60.0,
        description="Park-edge bungalow stock beside the bayou waterway, drawing renovation capital from the museum and festival economy.",
        city_id="new_orleans",
    ),
    "Tulane-Canal Corridor": SubmarketMeta(
        name="Tulane-Canal Corridor",
        borough="MID_CITY",
        lat=29.9785,
        lng=-90.1085,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.74,
        capex=4400000.0,
        permit_vel=46.0,
        shift_ratio=1.36,
        sla=52.0,
        description="Hospital-and-streetcar spine toward Carrollton Avenue with older multifamily stock and clinic-driven demand.",
        city_id="new_orleans",
    ),
    # =======================================================================
    # LAKEVIEW_GENTILLY (2 Submarkets)
    # =======================================================================
    "Lakeview & Lakeshore": SubmarketMeta(
        name="Lakeview & Lakeshore",
        borough="LAKEVIEW_GENTILLY",
        lat=30.0105,
        lng=-90.1105,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.85,
        capex=7600000.0,
        permit_vel=34.0,
        shift_ratio=1.51,
        sla=63.0,
        description="Post-Katrina rebuilt lakefront neighbourhoods behind the outfall canals, with elevated new construction dominating permits.",
        city_id="new_orleans",
    ),
    "Gentilly & Dillard": SubmarketMeta(
        name="Gentilly & Dillard",
        borough="LAKEVIEW_GENTILLY",
        lat=30.0025,
        lng=-90.0725,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.71,
        capex=3800000.0,
        permit_vel=42.0,
        shift_ratio=1.33,
        sla=50.0,
        description="Mid-century tract housing between the university campuses and the Industrial Canal with gradual redevelopment interest.",
        city_id="new_orleans",
    ),
    # =======================================================================
    # NEW_ORLEANS_EAST (2 Submarkets)
    # =======================================================================
    "New Orleans East I-10 Corridor": SubmarketMeta(
        name="New Orleans East I-10 Corridor",
        borough="NEW_ORLEANS_EAST",
        lat=30.0355,
        lng=-89.9455,
        zoom=12.5,
        pitch=40.0,
        base_lims=0.62,
        capex=3400000.0,
        permit_vel=48.0,
        shift_ratio=1.26,
        sla=44.0,
        description="Read Boulevard and I-10 service-road retail with the Michoud industrial reserve driving long-run logistics growth.",
        city_id="new_orleans",
    ),
    "Village de l'Est & Lake Forest": SubmarketMeta(
        name="Village de l'Est & Lake Forest",
        borough="NEW_ORLEANS_EAST",
        lat=30.0605,
        lng=-89.9155,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.55,
        capex=2400000.0,
        permit_vel=32.0,
        shift_ratio=1.16,
        sla=37.0,
        description="Vietnamese-American commercial nodes along Alcee Fortier and Chef Menteur with large-lot residential recovery.",
        city_id="new_orleans",
    ),
    # =======================================================================
    # WEST_BANK_ALGIERS (2 Submarkets)
    # =======================================================================
    "Algiers Point": SubmarketMeta(
        name="Algiers Point",
        borough="WEST_BANK_ALGIERS",
        lat=29.9555,
        lng=-90.0225,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.77,
        capex=4200000.0,
        permit_vel=31.0,
        shift_ratio=1.4,
        sla=54.0,
        description="Ferry-connected historic district across from the Quarter with Victorian stock and skyline-view demand.",
        city_id="new_orleans",
    ),
    "English Turn & Tall Timbers": SubmarketMeta(
        name="English Turn & Tall Timbers",
        borough="WEST_BANK_ALGIERS",
        lat=29.9085,
        lng=-90.0085,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.66,
        capex=3100000.0,
        permit_vel=27.0,
        shift_ratio=1.28,
        sla=45.0,
        description="Golf-course and subdivision growth downriver on the West Bank with parish-edge land supply.",
        city_id="new_orleans",
    ),
    # =======================================================================
    # JEFFERSON_METAIRIE_KENNER (3 Submarkets)
    # =======================================================================
    "Metairie Causeway Boulevard Retail": SubmarketMeta(
        name="Metairie Causeway Boulevard Retail",
        borough="JEFFERSON_METAIRIE_KENNER",
        lat=29.9885,
        lng=-90.1725,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.83,
        capex=6900000.0,
        permit_vel=45.0,
        shift_ratio=1.5,
        sla=64.0,
        description="Jefferson Parish's dominant strip-retail and office corridor running Lakeside Shopping Center to the lakefront.",
        city_id="new_orleans",
    ),
    "Kenner Esplanade & Airport District": SubmarketMeta(
        name="Kenner Esplanade & Airport District",
        borough="JEFFERSON_METAIRIE_KENNER",
        lat=29.9845,
        lng=-90.2465,
        zoom=12.5,
        pitch=42.0,
        base_lims=0.73,
        capex=5000000.0,
        permit_vel=44.0,
        shift_ratio=1.39,
        sla=56.0,
        description="Esplanade mall district and Louis Armstrong International adjacency with hospitality and logistics tenancy.",
        city_id="new_orleans",
    ),
    "Harahan & River Ridge": SubmarketMeta(
        name="Harahan & River Ridge",
        borough="JEFFERSON_METAIRIE_KENNER",
        lat=29.9415,
        lng=-90.1965,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.78,
        capex=4100000.0,
        permit_vel=29.0,
        shift_ratio=1.44,
        sla=59.0,
        description="River-bend single-family suburbs of East-Bank Jefferson with stable owner-occupant demand and Old Jefferson retail edges.",
        city_id="new_orleans",
    ),
    # =======================================================================
    # ST_BERNARD_CHALMETTE (2 Submarkets)
    # =======================================================================
    "Chalmette Refinery Corridor": SubmarketMeta(
        name="Chalmette Refinery Corridor",
        borough="ST_BERNARD_CHALMETTE",
        lat=29.8885,
        lng=-89.9585,
        zoom=12.5,
        pitch=40.0,
        base_lims=0.64,
        capex=2900000.0,
        permit_vel=26.0,
        shift_ratio=1.24,
        sla=41.0,
        description="Refinery-adjacent parish seat with buyout-zone land dynamics and petrochemical payroll underpinning demand.",
        city_id="new_orleans",
    ),
    "Arabi & Meraux": SubmarketMeta(
        name="Arabi & Meraux",
        borough="ST_BERNARD_CHALMETTE",
        lat=29.9185,
        lng=-89.9985,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.68,
        capex=2600000.0,
        permit_vel=23.0,
        shift_ratio=1.21,
        sla=39.0,
        description="River-road communities nearest the Orleans line absorbing first-ring spillover demand from the Bywater.",
        city_id="new_orleans",
    ),
}


NOLA_DIVISIONS: Dict[str, BoroughMeta] = {
    "CBD_FRENCH_QUARTER": BoroughMeta(
        name="CBD_FRENCH_QUARTER",
        center_lat=29.96,
        center_lng=-90.07,
        zoom=12.5,
        bbox=NOLA_DIVISION_BBOXES["CBD_FRENCH_QUARTER"],
        submarkets=[k for k, v in NOLA_SUBMARKETS.items() if v.borough == "CBD_FRENCH_QUARTER"],
        city_id="new_orleans",
    ),
    "BYWATER_MARIGNY": BoroughMeta(
        name="BYWATER_MARIGNY",
        center_lat=29.97,
        center_lng=-90.03,
        zoom=12.5,
        bbox=NOLA_DIVISION_BBOXES["BYWATER_MARIGNY"],
        submarkets=[k for k, v in NOLA_SUBMARKETS.items() if v.borough == "BYWATER_MARIGNY"],
        city_id="new_orleans",
    ),
    "UPTOWN_CARROLLTON": BoroughMeta(
        name="UPTOWN_CARROLLTON",
        center_lat=29.94,
        center_lng=-90.10,
        zoom=12.5,
        bbox=NOLA_DIVISION_BBOXES["UPTOWN_CARROLLTON"],
        submarkets=[k for k, v in NOLA_SUBMARKETS.items() if v.borough == "UPTOWN_CARROLLTON"],
        city_id="new_orleans",
    ),
    "MID_CITY": BoroughMeta(
        name="MID_CITY",
        center_lat=29.99,
        center_lng=-90.09,
        zoom=12.5,
        bbox=NOLA_DIVISION_BBOXES["MID_CITY"],
        submarkets=[k for k, v in NOLA_SUBMARKETS.items() if v.borough == "MID_CITY"],
        city_id="new_orleans",
    ),
    "LAKEVIEW_GENTILLY": BoroughMeta(
        name="LAKEVIEW_GENTILLY",
        center_lat=30.01,
        center_lng=-90.09,
        zoom=12.0,
        bbox=NOLA_DIVISION_BBOXES["LAKEVIEW_GENTILLY"],
        submarkets=[k for k, v in NOLA_SUBMARKETS.items() if v.borough == "LAKEVIEW_GENTILLY"],
        city_id="new_orleans",
    ),
    "NEW_ORLEANS_EAST": BoroughMeta(
        name="NEW_ORLEANS_EAST",
        center_lat=30.04,
        center_lng=-89.92,
        zoom=11.5,
        bbox=NOLA_DIVISION_BBOXES["NEW_ORLEANS_EAST"],
        submarkets=[k for k, v in NOLA_SUBMARKETS.items() if v.borough == "NEW_ORLEANS_EAST"],
        city_id="new_orleans",
    ),
    "WEST_BANK_ALGIERS": BoroughMeta(
        name="WEST_BANK_ALGIERS",
        center_lat=29.93,
        center_lng=-90.01,
        zoom=12.0,
        bbox=NOLA_DIVISION_BBOXES["WEST_BANK_ALGIERS"],
        submarkets=[k for k, v in NOLA_SUBMARKETS.items() if v.borough == "WEST_BANK_ALGIERS"],
        city_id="new_orleans",
    ),
    "JEFFERSON_METAIRIE_KENNER": BoroughMeta(
        name="JEFFERSON_METAIRIE_KENNER",
        center_lat=29.97,
        center_lng=-90.20,
        zoom=12.0,
        bbox=NOLA_DIVISION_BBOXES["JEFFERSON_METAIRIE_KENNER"],
        submarkets=[k for k, v in NOLA_SUBMARKETS.items() if v.borough == "JEFFERSON_METAIRIE_KENNER"],
        city_id="new_orleans",
    ),
    "ST_BERNARD_CHALMETTE": BoroughMeta(
        name="ST_BERNARD_CHALMETTE",
        center_lat=29.89,
        center_lng=-89.97,
        zoom=11.5,
        bbox=NOLA_DIVISION_BBOXES["ST_BERNARD_CHALMETTE"],
        submarkets=[k for k, v in NOLA_SUBMARKETS.items() if v.borough == "ST_BERNARD_CHALMETTE"],
        city_id="new_orleans",
    ),
}

# Verbose aliases mirroring los_angeles.py's LA_*/LOS_ANGELES_* pairs.
NOLA_METRO_BBOX = NEW_ORLEANS_METRO_BBOX
NEW_ORLEANS_DIVISION_BBOXES = NOLA_DIVISION_BBOXES
NEW_ORLEANS_SUBMARKETS = NOLA_SUBMARKETS
NEW_ORLEANS_DIVISIONS = NOLA_DIVISIONS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=NEW_ORLEANS_METRO_BBOX,
    division_bboxes=NEW_ORLEANS_DIVISION_BBOXES,
    submarkets=NEW_ORLEANS_SUBMARKETS,
    divisions=NEW_ORLEANS_DIVISIONS,
    contains=is_in_new_orleans_metro,
)
