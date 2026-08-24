"""Washington DC Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, division catalog, and
geographic bounding boxes for the District of Columbia (city_id
"washington_dc"). All four municipal feeds register against ArcGIS Hub REST
services over maps2.dcgis.dc.gov; two of them (Building Permits, 311 Service
Requests) publish ONE LAYER PER CALENDAR YEAR, so their specs carry an
``endpoint_by_year`` map consumed by ``resolve_endpoint``.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# District of Columbia bounding box. Verified to contain live samples from all
# four feeds probed 2026-08-23 (permits 38.9260,-77.0765; 311 38.9509,-77.0696).
DC_METRO_BBOX: Dict[str, float] = {
    "min_lat": 38.79,
    "max_lat": 38.995,
    "min_lng": -77.12,
    "max_lng": -76.909,
}


def is_in_dc_metro(lat: float | None, lng: float | None) -> bool:
    """Check if a coordinate lies within the District of Columbia bounds."""
    if lat is None or lng is None:
        return False
    return (
        DC_METRO_BBOX["min_lat"] <= lat <= DC_METRO_BBOX["max_lat"]
        and DC_METRO_BBOX["min_lng"] <= lng <= DC_METRO_BBOX["max_lng"]
    )


# Backwards/forwards-compatible alias used by registry-driven callers that
# spell cities out ("washington_dc" -> is_in_washington_dc_metro).
is_in_washington_dc_metro = is_in_dc_metro


# ---------------------------------------------------------------------------
# 8 Washington DC Division Bounding Boxes (real ward / neighborhood geography)
# ---------------------------------------------------------------------------

DC_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    # Downtown, Penn Quarter, NoMa, Union Market, SW Waterfront (Wards 2/5/6)
    "DOWNTOWN_NOMA_CAPITOL_RIVERFRONT": {
        "min_lat": 38.877, "max_lat": 38.913, "min_lng": -77.036, "max_lng": -76.995,
    },
    # Capitol Hill ridge through Eastern Market (Ward 6)
    "CAPITOL_HILL_EAST_END": {
        "min_lat": 38.879, "max_lat": 38.900, "min_lng": -76.995, "max_lng": -76.972,
    },
    # Dupont-Kalorama ridge up through Adams Morgan and U Street/NW corridor
    # (Wards 1/2)
    "DUPONT_KALORAMA_UPTOWN": {
        "min_lat": 38.900, "max_lat": 38.926, "min_lng": -77.062, "max_lng": -77.022,
    },
    # Georgetown waterfront, Foggy Bottom, West End (Ward 2)
    "GEORGETOWN_FOGGY_BOTTOM": {
        "min_lat": 38.893, "max_lat": 38.915, "min_lng": -77.100, "max_lng": -77.045,
    },
    # Uptown DC along the 14th/Georgia corridors (Wards 1/4)
    "COLUMBIA_HEIGHTS_PETWORTH": {
        "min_lat": 38.926, "max_lat": 38.962, "min_lng": -77.040, "max_lng": -77.000,
    },
    # Brookland/CUA and the Rhode Island Ave corridor in NE (Ward 5)
    "BROOKLAND_RHODE_ISLAND_AVE": {
        "min_lat": 38.926, "max_lat": 38.948, "min_lng": -77.000, "max_lng": -76.955,
    },
    # Hill East / Fairlinton toward the RFK stadium site (Wards 6/7)
    "HILL_EAST_FAIRLINTON": {
        "min_lat": 38.868, "max_lat": 38.884, "min_lng": -76.986, "max_lng": -76.952,
    },
    # Everything east of the Anacostia River (Wards 7/8)
    "ANACOSTIA_EAST_OF_THE_RIVER": {
        "min_lat": 38.845, "max_lat": 38.878, "min_lng": -76.988, "max_lng": -76.930,
    },
}


# ---------------------------------------------------------------------------
# Comprehensive Washington DC Submarket Registry (18 Submarkets Across 8 Divisions)
# ---------------------------------------------------------------------------

DC_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_NOMA_CAPITOL_RIVERFRONT (4 Submarkets)
    # =======================================================================
    "Penn Quarter": SubmarketMeta(
        name="Penn Quarter",
        borough="DOWNTOWN_NOMA_CAPITOL_RIVERFRONT",
        lat=38.8963,
        lng=-77.0230,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.92,
        capex=12000000.0,
        permit_vel=58.0,
        shift_ratio=1.70,
        sla=75.0,
        description="Museum-and-theater core between the Mall and Gallery Place with Capital One Arena foot traffic, office-to-residential conversions, and the heaviest downtown permit velocity.",
        city_id="washington_dc",
    ),
    "Southwest Waterfront/The Wharf": SubmarketMeta(
        name="Southwest Waterfront/The Wharf",
        borough="DOWNTOWN_NOMA_CAPITOL_RIVERFRONT",
        lat=38.8795,
        lng=-77.0185,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.88,
        capex=10500000.0,
        permit_vel=44.0,
        shift_ratio=1.55,
        sla=62.0,
        description="Phased mixed-use waterfront rebuild along Maine Avenue with The Wharf's concert piers, hotel inventory, and continued phase-two infill toward the Arena Stage axis.",
        city_id="washington_dc",
    ),
    "NoMa/H Street NE": SubmarketMeta(
        name="NoMa/H Street NE",
        borough="DOWNTOWN_NOMA_CAPITOL_RIVERFRONT",
        lat=38.9065,
        lng=-77.0015,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=9800000.0,
        permit_vel=52.0,
        shift_ratio=1.58,
        sla=58.0,
        description="Red Line-anchored high-density residential boom north of Union Station feeding the H Street NE streetcar nightlife spine across the Florida Avenue gap.",
        city_id="washington_dc",
    ),
    "Union Market": SubmarketMeta(
        name="Union Market",
        borough="DOWNTOWN_NOMA_CAPITOL_RIVERFRONT",
        lat=38.9085,
        lng=-77.0055,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.84,
        capex=9000000.0,
        permit_vel=48.0,
        shift_ratio=1.52,
        sla=55.0,
        description="Food-hall epicenter of a master-planned five-million-square-foot development district where Edison-era warehouse fabric meets tower cranes along Neal Place.",
        city_id="washington_dc",
    ),

    # =======================================================================
    # CAPITOL_HILL_EAST_END (2 Submarkets)
    # =======================================================================
    "Capitol Hill": SubmarketMeta(
        name="Capitol Hill",
        borough="CAPITOL_HILL_EAST_END",
        lat=38.8850,
        lng=-76.9890,
        zoom=14.5,
        pitch=40.0,
        base_lims=0.90,
        capex=8600000.0,
        permit_vel=30.0,
        shift_ratio=1.44,
        sla=70.0,
        description="Rowhouse historic district of congressional staff housing east of the Capitol grounds with Barracks Row retail and tight single-family supply.",
        city_id="washington_dc",
    ),
    "Eastern Market": SubmarketMeta(
        name="Eastern Market",
        borough="CAPITOL_HILL_EAST_END",
        lat=38.8843,
        lng=-76.9930,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.87,
        capex=7200000.0,
        permit_vel=26.0,
        shift_ratio=1.36,
        sla=66.0,
        description="Landmark 1873 public-market square anchoring weekend vendor crowds, 7th Street SE boutiques, and premium rowhouse renovations on Capitol Hill's north slope.",
        city_id="washington_dc",
    ),

    # =======================================================================
    # DUPONT_KALORAMA_UPTOWN (4 Submarkets)
    # =======================================================================
    "Dupont Circle": SubmarketMeta(
        name="Dupont Circle",
        borough="DUPONT_KALORAMA_UPTOWN",
        lat=38.9097,
        lng=-77.0444,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.91,
        capex=10200000.0,
        permit_vel=34.0,
        shift_ratio=1.50,
        sla=72.0,
        description="Embassy-row traffic circle with Connecticut Avenue Class-B office stock converting to residential, gallery retail, and Metro Red Line density.",
        city_id="washington_dc",
    ),
    "Kalorama Heights": SubmarketMeta(
        name="Kalorama Heights",
        borough="DUPONT_KALORAMA_UPTOWN",
        lat=38.9145,
        lng=-77.0500,
        zoom=14.5,
        pitch=35.0,
        base_lims=0.89,
        capex=11500000.0,
        permit_vel=22.0,
        shift_ratio=1.46,
        sla=68.0,
        description="Mansion-belt enclave of presidential residencies and embassy compounds where turnover is rare and renovation permits carry outsized contract values.",
        city_id="washington_dc",
    ),
    "Adams Morgan": SubmarketMeta(
        name="Adams Morgan",
        borough="DUPONT_KALORAMA_UPTOWN",
        lat=38.9165,
        lng=-77.0437,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.83,
        capex=7000000.0,
        permit_vel=32.0,
        shift_ratio=1.42,
        sla=60.0,
        description="Nightlife-and-immigration commercial strip on 18th Street with aging walk-up stock primed for repositioning and Columbia Road corridor investment.",
        city_id="washington_dc",
    ),
    "U Street Corridor": SubmarketMeta(
        name="U Street Corridor",
        borough="DUPONT_KALORAMA_UPTOWN",
        lat=38.9160,
        lng=-77.0280,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.85,
        capex=9200000.0,
        permit_vel=50.0,
        shift_ratio=1.56,
        sla=64.0,
        description="Black Broadway heritage corridor of music venues and Victorian rowhouses now ringed by Green/Yellow Line transit-oriented tower development.",
        city_id="washington_dc",
    ),

    # =======================================================================
    # GEORGETOWN_FOGGY_BOTTOM (2 Submarkets)
    # =======================================================================
    "Georgetown Waterfront": SubmarketMeta(
        name="Georgetown Waterfront",
        borough="GEORGETOWN_FOGGY_BOTTOM",
        lat=38.9050,
        lng=-77.0690,
        zoom=14.5,
        pitch=40.0,
        base_lims=0.90,
        capex=11000000.0,
        permit_vel=28.0,
        shift_ratio=1.54,
        sla=74.0,
        description="Federal-row retail and Washington Harbour park frontage on the Potomac with luxury condo scarcity value and C&O Canal-adjacent restoration work.",
        city_id="washington_dc",
    ),
    "Foggy Bottom/West End": SubmarketMeta(
        name="Foggy Bottom/West End",
        borough="GEORGETOWN_FOGGY_BOTTOM",
        lat=38.9000,
        lng=-77.0510,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.87,
        capex=9600000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=63.0,
        description="George Washington University hospital-and-dormitory economy beside the Kennedy Center, with State Department demand and West End condo redevelopment.",
        city_id="washington_dc",
    ),

    # =======================================================================
    # COLUMBIA_HEIGHTS_PETWORTH (3 Submarkets)
    # =======================================================================
    "Columbia Heights": SubmarketMeta(
        name="Columbia Heights",
        borough="COLUMBIA_HEIGHTS_PETWORTH",
        lat=38.9288,
        lng=-77.0277,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.82,
        capex=7600000.0,
        permit_vel=46.0,
        shift_ratio=1.50,
        sla=56.0,
        description="Green/Yellow Line retail hub around DC USA with dense multifamily conversion pipeline along 14th Street NW's northern stretch.",
        city_id="washington_dc",
    ),
    "Petworth": SubmarketMeta(
        name="Petworth",
        borough="COLUMBIA_HEIGHTS_PETWORTH",
        lat=38.9378,
        lng=-77.0234,
        zoom=14.5,
        pitch=40.0,
        base_lims=0.78,
        capex=6000000.0,
        permit_vel=40.0,
        shift_ratio=1.44,
        sla=48.0,
        description="Porched-rowhouse family market around Upshur Street strip retail with steady gut-renovation velocity and Georgia Avenue investment frontage.",
        city_id="washington_dc",
    ),
    "Takoma DC": SubmarketMeta(
        name="Takoma DC",
        borough="COLUMBIA_HEIGHTS_PETWORTH",
        lat=38.9565,
        lng=-77.0140,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.72,
        capex=4800000.0,
        permit_vel=24.0,
        shift_ratio=1.28,
        sla=40.0,
        description="Historic bungalow quarter at the Maryland line around the Takoma Metro station with craftsman restoration work and small-lot infill.",
        city_id="washington_dc",
    ),

    # =======================================================================
    # BROOKLAND_RHODE_ISLAND_AVE (1 Submarket)
    # =======================================================================
    "Brookland/CUA": SubmarketMeta(
        name="Brookland/CUA",
        borough="BROOKLAND_RHODE_ISLAND_AVE",
        lat=38.9332,
        lng=-76.9860,
        zoom=14.5,
        pitch=40.0,
        base_lims=0.68,
        capex=5200000.0,
        permit_vel=34.0,
        shift_ratio=1.36,
        sla=44.0,
        description="Little Rome university district where Catholic University institutional demand meets Arts Walk mixed-use build-out on the Rhode Island Avenue bridge.",
        city_id="washington_dc",
    ),

    # =======================================================================
    # HILL_EAST_FAIRLINTON (0 standalone submarkets — covered by adjacency)
    # =======================================================================

    # =======================================================================
    # ANACOSTIA_EAST_OF_THE_RIVER (2 Submarkets)
    # =======================================================================
    "Anacostia Historic District": SubmarketMeta(
        name="Anacostia Historic District",
        borough="ANACOSTIA_EAST_OF_THE_RIVER",
        lat=38.8676,
        lng=-76.9846,
        zoom=14.5,
        pitch=40.0,
        base_lims=0.62,
        capex=3800000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=36.0,
        description="Frederick Douglass home-side cottage district around the 11th Street Bridge landing where the Bridge District waterfront project resets East-of-the-River values.",
        city_id="washington_dc",
    ),
    "Congress Heights/St. Elizabeths": SubmarketMeta(
        name="Congress Heights/St. Elizabeths",
        borough="ANACOSTIA_EAST_OF_THE_RIVER",
        lat=38.8490,
        lng=-76.9665,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.55,
        capex=3000000.0,
        permit_vel=22.0,
        shift_ratio=1.12,
        sla=30.0,
        description="Camp Simms retail rebuild and the St. Elizabeths campus conversion — DHS headquarters, hospital shell reuse, and the district's largest land-bank opportunity.",
        city_id="washington_dc",
    ),
}


# ---------------------------------------------------------------------------
# Washington DC Divisions Catalog
# ---------------------------------------------------------------------------

DC_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_NOMA_CAPITOL_RIVERFRONT": BoroughMeta(
        name="DOWNTOWN_NOMA_CAPITOL_RIVERFRONT",
        center_lat=38.8970,
        center_lng=-77.0120,
        zoom=13.0,
        bbox=DC_DIVISION_BBOXES["DOWNTOWN_NOMA_CAPITOL_RIVERFRONT"],
        submarkets=[k for k, v in DC_SUBMARKETS.items() if v.borough == "DOWNTOWN_NOMA_CAPITOL_RIVERFRONT"],
        city_id="washington_dc",
    ),
    "CAPITOL_HILL_EAST_END": BoroughMeta(
        name="CAPITOL_HILL_EAST_END",
        center_lat=38.8895,
        center_lng=-76.9835,
        zoom=13.5,
        bbox=DC_DIVISION_BBOXES["CAPITOL_HILL_EAST_END"],
        submarkets=[k for k, v in DC_SUBMARKETS.items() if v.borough == "CAPITOL_HILL_EAST_END"],
        city_id="washington_dc",
    ),
    "DUPONT_KALORAMA_UPTOWN": BoroughMeta(
        name="DUPONT_KALORAMA_UPTOWN",
        center_lat=38.9140,
        center_lng=-77.0420,
        zoom=13.0,
        bbox=DC_DIVISION_BBOXES["DUPONT_KALORAMA_UPTOWN"],
        submarkets=[k for k, v in DC_SUBMARKETS.items() if v.borough == "DUPONT_KALORAMA_UPTOWN"],
        city_id="washington_dc",
    ),
    "GEORGETOWN_FOGGY_BOTTOM": BoroughMeta(
        name="GEORGETOWN_FOGGY_BOTTOM",
        center_lat=38.9025,
        center_lng=-77.0620,
        zoom=13.5,
        bbox=DC_DIVISION_BBOXES["GEORGETOWN_FOGGY_BOTTOM"],
        submarkets=[k for k, v in DC_SUBMARKETS.items() if v.borough == "GEORGETOWN_FOGGY_BOTTOM"],
        city_id="washington_dc",
    ),
    "COLUMBIA_HEIGHTS_PETWORTH": BoroughMeta(
        name="COLUMBIA_HEIGHTS_PETWORTH",
        center_lat=38.9410,
        center_lng=-77.0200,
        zoom=13.0,
        bbox=DC_DIVISION_BBOXES["COLUMBIA_HEIGHTS_PETWORTH"],
        submarkets=[k for k, v in DC_SUBMARKETS.items() if v.borough == "COLUMBIA_HEIGHTS_PETWORTH"],
        city_id="washington_dc",
    ),
    "BROOKLAND_RHODE_ISLAND_AVE": BoroughMeta(
        name="BROOKLAND_RHODE_ISLAND_AVE",
        center_lat=38.9370,
        center_lng=-76.9780,
        zoom=13.5,
        bbox=DC_DIVISION_BBOXES["BROOKLAND_RHODE_ISLAND_AVE"],
        submarkets=[k for k, v in DC_SUBMARKETS.items() if v.borough == "BROOKLAND_RHODE_ISLAND_AVE"],
        city_id="washington_dc",
    ),
    "HILL_EAST_FAIRLINTON": BoroughMeta(
        name="HILL_EAST_FAIRLINTON",
        center_lat=38.8760,
        center_lng=-76.9690,
        zoom=13.5,
        bbox=DC_DIVISION_BBOXES["HILL_EAST_FAIRLINTON"],
        # Claimed as a geographic division with no dedicated submarket yet —
        # RFK-site redevelopment will seed its first entry.
        submarkets=[k for k, v in DC_SUBMARKETS.items() if v.borough == "HILL_EAST_FAIRLINTON"],
        city_id="washington_dc",
    ),
    "ANACOSTIA_EAST_OF_THE_RIVER": BoroughMeta(
        name="ANACOSTIA_EAST_OF_THE_RIVER",
        center_lat=38.8580,
        center_lng=-76.9620,
        zoom=13.0,
        bbox=DC_DIVISION_BBOXES["ANACOSTIA_EAST_OF_THE_RIVER"],
        submarkets=[k for k, v in DC_SUBMARKETS.items() if v.borough == "ANACOSTIA_EAST_OF_THE_RIVER"],
        city_id="washington_dc",
    ),
}
