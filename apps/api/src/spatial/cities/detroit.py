"""Detroit Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Detroit, MI.

Detroit registers up to four feeds, all ``platform="arcgis"`` through the
existing ArcGISClient. Two live-probed quirks (2026-08-23) are load-bearing:

* **DateOnly fields.** BSEED permits (``submitted_date``/``issued_date``),
  business licenses (``expiration_date``), and Assessor property sales
  (``sale_date``) are typed ``esriFieldTypeDateOnly`` and arrive as plain
  ``"YYYY-MM-DD"`` strings — ArcGISClient's epoch-ms conversion is a no-op on
  them (it short-circuits on str). Values are already parser-friendly; do not
  "fix" them into timestamps.
* **OID field is ``ObjectId``** (camelCase), not King County's ``OBJECTID``,
  on every layer. Pagination still works because the client reads
  ``objectIdField`` from layer metadata, but each DatasetSpec must pin
  ``oid_field="ObjectId"``.

The Improve Detroit 311 feed geocodes via flat ``longitude``/``latitude``
attributes even when its point geometry comes back null, so no dotted-path
field_map entries are needed for coordinates.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# City of Detroit bounding box. The feeds are city-scoped; the Assessor sales
# view can spill slightly into adjacent communities, so this bbox doubles as
# the clamp. Validated against live extents: Hub dataset extent lat
# 42.2562-42.4500 / lng -83.2874 to -82.9111; sampled sales max_lat 42.44996,
# max_lng -82.9116, far-east Jefferson-Chalmers rows near -82.95, and far-west
# Brightmoor/Old Redford rows approaching -83.28.
DETROIT_METRO_BBOX: Dict[str, float] = {
    "min_lat": 42.25,
    "max_lat": 42.49,
    "min_lng": -83.35,
    "max_lng": -82.88,
}

# 6 Detroit Division Bounding Boxes
DETROIT_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_MIDTOWN_CORKTOWN":        {"min_lat": 42.310, "max_lat": 42.365, "min_lng": -83.100, "max_lng": -83.020},
    "EAST_SIDE_JEFFERSON":              {"min_lat": 42.325, "max_lat": 42.375, "min_lng": -83.030, "max_lng": -82.940},
    "WEST_SIDE_GRAND_RIVER":            {"min_lat": 42.380, "max_lat": 42.425, "min_lng": -83.290, "max_lng": -83.150},
    "SOUTHWEST_MEXICANTOWN":            {"min_lat": 42.295, "max_lat": 42.330, "min_lng": -83.150, "max_lng": -83.080},
    "NORTH_END_HIGHLAND_PARK":          {"min_lat": 42.365, "max_lat": 42.440, "min_lng": -83.120, "max_lng": -83.060},
    "EAST_ENGLISH_VILLAGE_MORNINGSIDE": {"min_lat": 42.350, "max_lat": 42.395, "min_lng": -82.995, "max_lng": -82.920},
}


def is_in_detroit_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Detroit Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        DETROIT_METRO_BBOX["min_lat"] <= lat <= DETROIT_METRO_BBOX["max_lat"]
        and DETROIT_METRO_BBOX["min_lng"] <= lng <= DETROIT_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_detroit = is_in_detroit_metro


DETROIT_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_MIDTOWN_CORKTOWN (3 Submarkets)
    # =======================================================================
    "Campus Martius & CBD": SubmarketMeta(
        name="Campus Martius & CBD",
        borough="DOWNTOWN_MIDTOWN_CORKTOWN",
        lat=42.3314,
        lng=-83.0458,
        zoom=15.0,
        pitch=55.0,
        base_lims=0.90,
        capex=11000000.0,
        permit_vel=55.0,
        shift_ratio=1.70,
        sla=72.0,
        description="Downtown core around Campus Martius park with Hudson's-site tower construction, office-to-residential conversions, and the Woodward retail spine.",
        city_id="detroit",
    ),
    "Midtown Cultural District": SubmarketMeta(
        name="Midtown Cultural District",
        borough="DOWNTOWN_MIDTOWN_CORKTOWN",
        lat=42.3555,
        lng=-83.0632,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.87,
        capex=8500000.0,
        permit_vel=44.0,
        shift_ratio=1.52,
        sla=58.0,
        description="DIA, Wayne State University, MOCAD, and the College for Creative Studies anchoring institutional demand, mixed-use infill, and Woodward corridor recovery.",
        city_id="detroit",
    ),
    "Corktown & Michigan Central Station": SubmarketMeta(
        name="Corktown & Michigan Central Station",
        borough="DOWNTOWN_MIDTOWN_CORKTOWN",
        lat=42.3232,
        lng=-83.0765,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.88,
        capex=9200000.0,
        permit_vel=48.0,
        shift_ratio=1.60,
        sla=54.0,
        description="Michigan Central Station's Ford-led innovation campus driving restaurant rows on Michigan Avenue and townhouse infill across Corktown.",
        city_id="detroit",
    ),

    # =======================================================================
    # EAST_SIDE_JEFFERSON (3 Submarkets)
    # =======================================================================
    "East Riverfront Growth": SubmarketMeta(
        name="East Riverfront Growth",
        borough="EAST_SIDE_JEFFERSON",
        lat=42.3330,
        lng=-83.0150,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.78,
        capex=7200000.0,
        permit_vel=38.0,
        shift_ratio=1.42,
        sla=44.0,
        description="RiverWalk-adjacent apartment towers and the Aretha Franklin Amphitheatre extending redevelopment pressure east from the CBD along Jefferson.",
        city_id="detroit",
    ),
    "West Village": SubmarketMeta(
        name="West Village",
        borough="EAST_SIDE_JEFFERSON",
        lat=42.3500,
        lng=-82.9770,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.68,
        capex=3800000.0,
        permit_vel=26.0,
        shift_ratio=1.28,
        sla=38.0,
        description="Historic rowhouse district with Kercheval boutique retail and cafe culture, a stable anchor of Detroit's east-side revival.",
        city_id="detroit",
    ),
    "Jefferson-Chalmers": SubmarketMeta(
        name="Jefferson-Chalmers",
        borough="EAST_SIDE_JEFFERSON",
        lat=42.3619,
        lng=-82.9511,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.56,
        capex=2600000.0,
        permit_vel=21.0,
        shift_ratio=1.16,
        sla=27.0,
        description="Far-east lakefront business district and canal neighborhoods with National Register historic commercial frontage and slow but real reinvestment.",
        city_id="detroit",
    ),

    # =======================================================================
    # WEST_SIDE_GRAND_RIVER (2 Submarkets)
    # =======================================================================
    "Brightmoor": SubmarketMeta(
        name="Brightmoor",
        borough="WEST_SIDE_GRAND_RIVER",
        lat=42.3980,
        lng=-83.2280,
        zoom=13.5,
        pitch=30.0,
        base_lims=0.50,
        capex=2000000.0,
        permit_vel=20.0,
        shift_ratio=1.10,
        sla=25.0,
        description="Northwest residential belt of bungalows and large-lot vacancy where community land trusts and blight removal set the redevelopment tempo.",
        city_id="detroit",
    ),
    "Grandmont-Rosedale": SubmarketMeta(
        name="Grandmont-Rosedale",
        borough="WEST_SIDE_GRAND_RIVER",
        lat=42.4050,
        lng=-83.1870,
        zoom=14.0,
        pitch=30.0,
        base_lims=0.66,
        capex=3400000.0,
        permit_vel=24.0,
        shift_ratio=1.22,
        sla=32.0,
        description="Five-neighborhood Tudor and brick-ranch enclave with an active community development corporation and steady Grand River commercial rehab.",
        city_id="detroit",
    ),

    # =======================================================================
    # SOUTHWEST_MEXICANTOWN (2 Submarkets)
    # =======================================================================
    "Mexicantown & Clark Park": SubmarketMeta(
        name="Mexicantown & Clark Park",
        borough="SOUTHWEST_MEXICANTOWN",
        lat=42.3230,
        lng=-83.1010,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.64,
        capex=3200000.0,
        permit_vel=27.0,
        shift_ratio=1.30,
        sla=46.0,
        description="Bagley-Fernandez commercial corridors with Mexican bakeries and restaurants around Clark Park, plus the international freight village at the Ambassador Bridge.",
        city_id="detroit",
    ),
    "Southwest Industrial Corridor": SubmarketMeta(
        name="Southwest Industrial Corridor",
        borough="SOUTHWEST_MEXICANTOWN",
        lat=42.3060,
        lng=-83.1310,
        zoom=13.5,
        pitch=30.0,
        base_lims=0.55,
        capex=4600000.0,
        permit_vel=31.0,
        shift_ratio=1.18,
        sla=28.0,
        description="Vigor-industrial district between Fort Street and the river with heavy-manufacturing sites, rail spurs, and brownfield logistics conversions.",
        city_id="detroit",
    ),

    # =======================================================================
    # NORTH_END_HIGHLAND_PARK (3 Submarkets)
    # =======================================================================
    "New Center & Fisher Building": SubmarketMeta(
        name="New Center & Fisher Building",
        borough="NORTH_END_HIGHLAND_PARK",
        lat=42.3730,
        lng=-83.0780,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.74,
        capex=6200000.0,
        permit_vel=36.0,
        shift_ratio=1.40,
        sla=42.0,
        description="Albert Kahn's Fisher and GM-era skyline with the Amtrak station hub, Henry Ford Health expansion, and mixed-use infill on West Grand Boulevard.",
        city_id="detroit",
    ),
    "Bagley & Fitzgerald Revival Zone": SubmarketMeta(
        name="Bagley & Fitzgerald Revival Zone",
        borough="NORTH_END_HIGHLAND_PARK",
        lat=42.4210,
        lng=-83.0840,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.58,
        capex=2800000.0,
        permit_vel=23.0,
        shift_ratio=1.24,
        sla=30.0,
        description="Livernois Avenue of Fashion galleries and the Fitzgerald master-planned rehabilitation of hundreds of vacant structures around Marygrove and University of Detroit Mercy.",
        city_id="detroit",
    ),
    "Palmer Woods & University District": SubmarketMeta(
        name="Palmer Woods & University District",
        borough="NORTH_END_HIGHLAND_PARK",
        lat=42.4300,
        lng=-83.1060,
        zoom=14.0,
        pitch=30.0,
        base_lims=0.72,
        capex=3600000.0,
        permit_vel=22.0,
        shift_ratio=1.18,
        sla=34.0,
        description="Estate-scale Palmer Woods historic district and Sherwood Forest adjoining the Detroit Golf Club, the metro's most resilient north-side housing stock.",
        city_id="detroit",
    ),

    # =======================================================================
    # EAST_ENGLISH_VILLAGE_MORNINGSIDE (3 Submarkets)
    # =======================================================================
    "Indian Village": SubmarketMeta(
        name="Indian Village",
        borough="EAST_ENGLISH_VILLAGE_MORNINGSIDE",
        lat=42.3595,
        lng=-82.9840,
        zoom=15.0,
        pitch=35.0,
        base_lims=0.70,
        capex=3000000.0,
        permit_vel=22.0,
        shift_ratio=1.20,
        sla=33.0,
        description="Albert Kahn-designed mansion district on Burns, Iroquois, and Seminole with an annual house tour and deeply held preservation ethos.",
        city_id="detroit",
    ),
    "Morningside": SubmarketMeta(
        name="Morningside",
        borough="EAST_ENGLISH_VILLAGE_MORNINGSIDE",
        lat=42.3740,
        lng=-82.9460,
        zoom=14.0,
        pitch=30.0,
        base_lims=0.54,
        capex=2400000.0,
        permit_vel=21.0,
        shift_ratio=1.14,
        sla=26.0,
        description="Balduck Park brick-bungalow community with Gratiot-strip storefronts in early-stage acquisition-and-rehab recovery.",
        city_id="detroit",
    ),
    "East English Village": SubmarketMeta(
        name="East English Village",
        borough="EAST_ENGLISH_VILLAGE_MORNINGSIDE",
        lat=42.3860,
        lng=-82.9320,
        zoom=14.0,
        pitch=30.0,
        base_lims=0.62,
        capex=2700000.0,
        permit_vel=24.0,
        shift_ratio=1.19,
        sla=31.0,
        description="Brick-tudor homeowner enclave east of Morningside prized for stability, active block clubs, and Harper Avenue retail nodes.",
        city_id="detroit",
    ),
}


# ---------------------------------------------------------------------------
# Detroit Divisions Catalog
# ---------------------------------------------------------------------------

DETROIT_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_MIDTOWN_CORKTOWN": BoroughMeta(
        name="DOWNTOWN_MIDTOWN_CORKTOWN",
        center_lat=42.3367,
        center_lng=-83.0618,
        zoom=13.5,
        bbox=DETROIT_DIVISION_BBOXES["DOWNTOWN_MIDTOWN_CORKTOWN"],
        submarkets=[k for k, v in DETROIT_SUBMARKETS.items() if v.borough == "DOWNTOWN_MIDTOWN_CORKTOWN"],
        city_id="detroit",
    ),
    "EAST_SIDE_JEFFERSON": BoroughMeta(
        name="EAST_SIDE_JEFFERSON",
        center_lat=42.3483,
        center_lng=-82.9810,
        zoom=12.5,
        bbox=DETROIT_DIVISION_BBOXES["EAST_SIDE_JEFFERSON"],
        submarkets=[k for k, v in DETROIT_SUBMARKETS.items() if v.borough == "EAST_SIDE_JEFFERSON"],
        city_id="detroit",
    ),
    "WEST_SIDE_GRAND_RIVER": BoroughMeta(
        name="WEST_SIDE_GRAND_RIVER",
        center_lat=42.4015,
        center_lng=-83.2070,
        zoom=12.5,
        bbox=DETROIT_DIVISION_BBOXES["WEST_SIDE_GRAND_RIVER"],
        submarkets=[k for k, v in DETROIT_SUBMARKETS.items() if v.borough == "WEST_SIDE_GRAND_RIVER"],
        city_id="detroit",
    ),
    "SOUTHWEST_MEXICANTOWN": BoroughMeta(
        name="SOUTHWEST_MEXICANTOWN",
        center_lat=42.3145,
        center_lng=-83.1155,
        zoom=13.0,
        bbox=DETROIT_DIVISION_BBOXES["SOUTHWEST_MEXICANTOWN"],
        submarkets=[k for k, v in DETROIT_SUBMARKETS.items() if v.borough == "SOUTHWEST_MEXICANTOWN"],
        city_id="detroit",
    ),
    "NORTH_END_HIGHLAND_PARK": BoroughMeta(
        name="NORTH_END_HIGHLAND_PARK",
        center_lat=42.4080,
        center_lng=-83.0893,
        zoom=12.5,
        bbox=DETROIT_DIVISION_BBOXES["NORTH_END_HIGHLAND_PARK"],
        submarkets=[k for k, v in DETROIT_SUBMARKETS.items() if v.borough == "NORTH_END_HIGHLAND_PARK"],
        city_id="detroit",
    ),
    "EAST_ENGLISH_VILLAGE_MORNINGSIDE": BoroughMeta(
        name="EAST_ENGLISH_VILLAGE_MORNINGSIDE",
        center_lat=42.3732,
        center_lng=-82.9540,
        zoom=12.5,
        bbox=DETROIT_DIVISION_BBOXES["EAST_ENGLISH_VILLAGE_MORNINGSIDE"],
        submarkets=[k for k, v in DETROIT_SUBMARKETS.items() if v.borough == "EAST_ENGLISH_VILLAGE_MORNINGSIDE"],
        city_id="detroit",
    ),
}


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=DETROIT_METRO_BBOX,
    division_bboxes=DETROIT_DIVISION_BBOXES,
    submarkets=DETROIT_SUBMARKETS,
    divisions=DETROIT_DIVISIONS,
    contains=is_in_detroit_metro,
)
