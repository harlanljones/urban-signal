"""5-Borough Submarket Registry and Spatial Layer for NYC Urban Signal.

Provides comprehensive neighborhood metadata, camera positioning, investment
metrics, and distance/borough lookup helpers for all 5 NYC boroughs.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List, Optional, Tuple

NYC_METRO_BBOX: Dict[str, float] = {
    "min_lat": 40.480,
    "max_lat": 40.930,
    "min_lng": -74.280,
    "max_lng": -73.680,
}

NYC_BOROUGH_BBOXES: Dict[str, Dict[str, float]] = {
    "MANHATTAN":     {"min_lat": 40.700, "max_lat": 40.882, "min_lng": -74.020, "max_lng": -73.907},
    "BROOKLYN":      {"min_lat": 40.570, "max_lat": 40.740, "min_lng": -74.050, "max_lng": -73.830},
    "QUEENS":        {"min_lat": 40.540, "max_lat": 40.800, "min_lng": -73.960, "max_lng": -73.700},
    "BRONX":         {"min_lat": 40.785, "max_lat": 40.915, "min_lng": -73.935, "max_lng": -73.765},
    "STATEN_ISLAND": {"min_lat": 40.495, "max_lat": 40.650, "min_lng": -74.255, "max_lng": -74.050},
}


@dataclass
class SubmarketMeta:
    """Metadata and baseline metrics for an urban submarket corridor."""

    name: str
    borough: str  # NYC Borough or Chicago Division
    lat: float
    lng: float
    zoom: float
    pitch: float
    base_lims: float
    capex: float
    permit_vel: float
    shift_ratio: float
    sla: float
    description: str
    city_id: str = "nyc"

    @property
    def division(self) -> str:
        """Alias for borough/division."""
        return self.borough


@dataclass
class BoroughMeta:
    """Metadata and catalog boundaries for an NYC Borough or City Division."""

    name: str
    center_lat: float
    center_lng: float
    zoom: float
    bbox: Dict[str, float]
    submarkets: List[str]
    city_id: str = "nyc"


DivisionMeta = BoroughMeta


# ---------------------------------------------------------------------------
# Comprehensive Submarket Registry: 65 Submarkets Across All 5 Boroughs
# ---------------------------------------------------------------------------

NYC_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # MANHATTAN (18 Submarkets)
    # =======================================================================
    "SoHo": SubmarketMeta(
        name="SoHo",
        borough="MANHATTAN",
        lat=40.7233,
        lng=-74.0030,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.88,
        capex=8500000.0,
        permit_vel=42.0,
        shift_ratio=1.45,
        sla=48.0,
        description="Cast-iron historic district with luxury retail, high capex conversions, and thriving hospitality.",
    ),
    "Tribeca": SubmarketMeta(
        name="Tribeca",
        borough="MANHATTAN",
        lat=40.7163,
        lng=-74.0086,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.92,
        capex=12500000.0,
        permit_vel=38.0,
        shift_ratio=1.52,
        sla=36.0,
        description="Cobblestone enclave featuring ultra-luxury residential lofts and Michelin-caliber dining.",
    ),
    "West Village": SubmarketMeta(
        name="West Village",
        borough="MANHATTAN",
        lat=40.7358,
        lng=-74.0036,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.85,
        capex=7200000.0,
        permit_vel=31.0,
        shift_ratio=1.38,
        sla=55.0,
        description="Historic brownstone core with premier pedestrian retail corridors and boutique nightlife.",
    ),
    "Greenwich Village": SubmarketMeta(
        name="Greenwich Village",
        borough="MANHATTAN",
        lat=40.7336,
        lng=-73.9969,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=35.0,
        shift_ratio=1.34,
        sla=62.0,
        description="Academic and cultural hub centered around Washington Square Park with high retail footfall.",
    ),
    "East Village": SubmarketMeta(
        name="East Village",
        borough="MANHATTAN",
        lat=40.7265,
        lng=-73.9815,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.79,
        capex=5400000.0,
        permit_vel=48.0,
        shift_ratio=1.29,
        sla=78.0,
        description="High-density nightlife corridor with dense tenement stock and active hospitality licensing.",
    ),
    "Lower East Side": SubmarketMeta(
        name="Lower East Side",
        borough="MANHATTAN",
        lat=40.7150,
        lng=-73.9843,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.81,
        capex=6100000.0,
        permit_vel=52.0,
        shift_ratio=1.41,
        sla=82.0,
        description="Dynamic submarket undergoing rapid mixed-use redevelopment and nightlife densification.",
    ),
    "Chinatown": SubmarketMeta(
        name="Chinatown",
        borough="MANHATTAN",
        lat=40.7158,
        lng=-73.9970,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.68,
        capex=4200000.0,
        permit_vel=29.0,
        shift_ratio=1.18,
        sla=44.0,
        description="Historic cultural district with dense ground-floor commercial activity and adaptive reuse.",
    ),
    "Financial District": SubmarketMeta(
        name="Financial District",
        borough="MANHATTAN",
        lat=40.7075,
        lng=-74.0090,
        zoom=14.0,
        pitch=60.0,
        base_lims=0.86,
        capex=11000000.0,
        permit_vel=56.0,
        shift_ratio=1.60,
        sla=52.0,
        description="Downtown financial center transitioning rapidly into 24/7 mixed-use residential towers.",
    ),
    "Chelsea": SubmarketMeta(
        name="Chelsea",
        borough="MANHATTAN",
        lat=40.7465,
        lng=-74.0014,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.87,
        capex=8900000.0,
        permit_vel=44.0,
        shift_ratio=1.42,
        sla=58.0,
        description="Art gallery epicenter adjacent to High Line with high-value residential and tech offices.",
    ),
    "Flatiron / NoMad": SubmarketMeta(
        name="Flatiron / NoMad",
        borough="MANHATTAN",
        lat=40.7411,
        lng=-73.9897,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.90,
        capex=9800000.0,
        permit_vel=46.0,
        shift_ratio=1.48,
        sla=64.0,
        description="Premier commercial innovation and lifestyle corridor with Michelin dining and luxury hotels.",
    ),
    "Hell's Kitchen": SubmarketMeta(
        name="Hell's Kitchen",
        borough="MANHATTAN",
        lat=40.7638,
        lng=-73.9918,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.78,
        capex=5900000.0,
        permit_vel=40.0,
        shift_ratio=1.25,
        sla=72.0,
        description="Theater-adjacent hospitality and residential corridor with sustained permit activity.",
    ),
    "Midtown East": SubmarketMeta(
        name="Midtown East",
        borough="MANHATTAN",
        lat=40.7527,
        lng=-73.9772,
        zoom=14.0,
        pitch=60.0,
        base_lims=0.89,
        capex=14000000.0,
        permit_vel=58.0,
        shift_ratio=1.55,
        sla=60.0,
        description="Global corporate headquarters hub anchored by Grand Central Terminal redevelopment.",
    ),
    "Upper East Side": SubmarketMeta(
        name="Upper East Side",
        borough="MANHATTAN",
        lat=40.7736,
        lng=-73.9566,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.83,
        capex=7800000.0,
        permit_vel=36.0,
        shift_ratio=1.22,
        sla=42.0,
        description="Established affluent residential enclave along Central Park and Museum Mile.",
    ),
    "Upper West Side": SubmarketMeta(
        name="Upper West Side",
        borough="MANHATTAN",
        lat=40.7870,
        lng=-73.9754,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.82,
        capex=7400000.0,
        permit_vel=34.0,
        shift_ratio=1.20,
        sla=40.0,
        description="Historic residential district flanked by Central and Riverside Parks with strong family demographics.",
    ),
    "Harlem": SubmarketMeta(
        name="Harlem",
        borough="MANHATTAN",
        lat=40.8116,
        lng=-73.9465,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=45.0,
        shift_ratio=1.35,
        sla=38.0,
        description="Historic cultural hub with active 125th Street commercial corridor and brownstone revitalization.",
    ),
    "East Harlem": SubmarketMeta(
        name="East Harlem",
        borough="MANHATTAN",
        lat=40.7957,
        lng=-73.9389,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.69,
        capex=4100000.0,
        permit_vel=39.0,
        shift_ratio=1.28,
        sla=30.0,
        description="Up-zoned residential corridor experiencing influx of affordable and market-rate developments.",
    ),
    "Washington Heights": SubmarketMeta(
        name="Washington Heights",
        borough="MANHATTAN",
        lat=40.8417,
        lng=-73.9387,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.65,
        capex=3600000.0,
        permit_vel=32.0,
        shift_ratio=1.19,
        sla=28.0,
        description="Uptown medical and educational anchor centered around Columbia University Irving Medical Center.",
    ),
    "Inwood": SubmarketMeta(
        name="Inwood",
        borough="MANHATTAN",
        lat=40.8677,
        lng=-73.9212,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.62,
        capex=3200000.0,
        permit_vel=28.0,
        shift_ratio=1.16,
        sla=24.0,
        description="Northernmost tip of Manhattan with significant rezoning-driven multifamily development.",
    ),

    # =======================================================================
    # BROOKLYN (20 Submarkets)
    # =======================================================================
    "Williamsburg": SubmarketMeta(
        name="Williamsburg",
        borough="BROOKLYN",
        lat=40.7145,
        lng=-73.9555,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.91,
        capex=9500000.0,
        permit_vel=64.0,
        shift_ratio=1.65,
        sla=85.0,
        description="Global creative epicenter with waterfront high-rises, thriving retail, and dense entertainment.",
    ),
    "Greenpoint": SubmarketMeta(
        name="Greenpoint",
        borough="BROOKLYN",
        lat=40.7305,
        lng=-73.9515,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.86,
        capex=8200000.0,
        permit_vel=49.0,
        shift_ratio=1.54,
        sla=56.0,
        description="North Brooklyn waterfront neighborhood seeing massive luxury residential expansion along the East River.",
    ),
    "Bushwick": SubmarketMeta(
        name="Bushwick",
        borough="BROOKLYN",
        lat=40.6944,
        lng=-73.9213,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.76,
        capex=4900000.0,
        permit_vel=58.0,
        shift_ratio=1.48,
        sla=68.0,
        description="Industrial-to-creative conversion zone with high nightlife velocity and loft conversions.",
    ),
    "DUMBO": SubmarketMeta(
        name="DUMBO",
        borough="BROOKLYN",
        lat=40.7033,
        lng=-73.9890,
        zoom=15.0,
        pitch=55.0,
        base_lims=0.94,
        capex=11500000.0,
        permit_vel=33.0,
        shift_ratio=1.58,
        sla=41.0,
        description="Boutique tech, advertising, and luxury residential enclave beneath the Manhattan & Brooklyn Bridges.",
    ),
    "Downtown Brooklyn": SubmarketMeta(
        name="Downtown Brooklyn",
        borough="BROOKLYN",
        lat=40.6925,
        lng=-73.9870,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.88,
        capex=10200000.0,
        permit_vel=67.0,
        shift_ratio=1.62,
        sla=54.0,
        description="Brooklyn's civic and commercial core undergoing skyscraper residential boom.",
    ),
    "Brooklyn Heights": SubmarketMeta(
        name="Brooklyn Heights",
        borough="BROOKLYN",
        lat=40.6960,
        lng=-73.9933,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.89,
        capex=8100000.0,
        permit_vel=26.0,
        shift_ratio=1.24,
        sla=32.0,
        description="Historic landmarked district with premier promenade views and high-value brownstones.",
    ),
    "Cobble Hill / Boerum Hill": SubmarketMeta(
        name="Cobble Hill / Boerum Hill",
        borough="BROOKLYN",
        lat=40.6865,
        lng=-73.9930,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.84,
        capex=6700000.0,
        permit_vel=30.0,
        shift_ratio=1.31,
        sla=46.0,
        description="Charming tree-lined rowhouse district with flourishing boutique dining corridors along Atlantic and Court.",
    ),
    "Fort Greene": SubmarketMeta(
        name="Fort Greene",
        borough="BROOKLYN",
        lat=40.6920,
        lng=-73.9742,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.83,
        capex=6400000.0,
        permit_vel=37.0,
        shift_ratio=1.36,
        sla=44.0,
        description="Cultural hub anchored by BAM and Fort Greene Park with active historic conversions.",
    ),
    "Clinton Hill": SubmarketMeta(
        name="Clinton Hill",
        borough="BROOKLYN",
        lat=40.6894,
        lng=-73.9644,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.80,
        capex=5800000.0,
        permit_vel=36.0,
        shift_ratio=1.33,
        sla=38.0,
        description="Victorian mansion and Pratt-adjacent enclave experiencing sustained residential demand.",
    ),
    "Bed-Stuy": SubmarketMeta(
        name="Bed-Stuy",
        borough="BROOKLYN",
        lat=40.6872,
        lng=-73.9418,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.75,
        capex=4600000.0,
        permit_vel=54.0,
        shift_ratio=1.42,
        sla=45.0,
        description="Historic brownstone district undergoing extensive gut rehabilitation and commercial revitalization.",
    ),
    "Crown Heights": SubmarketMeta(
        name="Crown Heights",
        borough="BROOKLYN",
        lat=40.6694,
        lng=-73.9422,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.73,
        capex=4300000.0,
        permit_vel=47.0,
        shift_ratio=1.37,
        sla=41.0,
        description="Franklin and Nostrand corridor renewal with accelerating food/beverage and multifamily investments.",
    ),
    "Park Slope": SubmarketMeta(
        name="Park Slope",
        borough="BROOKLYN",
        lat=40.6710,
        lng=-73.9777,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.87,
        capex=7600000.0,
        permit_vel=33.0,
        shift_ratio=1.27,
        sla=49.0,
        description="Prime residential community along Prospect Park with exceptional school districts and high property equity.",
    ),
    "Gowanus": SubmarketMeta(
        name="Gowanus",
        borough="BROOKLYN",
        lat=40.6734,
        lng=-73.9903,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.85,
        capex=8800000.0,
        permit_vel=61.0,
        shift_ratio=1.70,
        sla=47.0,
        description="Post-industrial canal corridor undergoing massive city rezoning for thousands of new residential units.",
    ),
    "Prospect Heights": SubmarketMeta(
        name="Prospect Heights",
        borough="BROOKLYN",
        lat=40.6774,
        lng=-73.9665,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.84,
        capex=6900000.0,
        permit_vel=38.0,
        shift_ratio=1.39,
        sla=43.0,
        description="Vibrant enclave anchored by Barclays Center, Brooklyn Museum, and Vanderbilt Avenue dining.",
    ),
    "Prospect Lefferts Gardens": SubmarketMeta(
        name="Prospect Lefferts Gardens",
        borough="BROOKLYN",
        lat=40.6590,
        lng=-73.9514,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.71,
        capex=4100000.0,
        permit_vel=39.0,
        shift_ratio=1.32,
        sla=29.0,
        description="Historic manor district seeing new mid-rise multifamily development near Prospect Park's east side.",
    ),
    "Sunset Park": SubmarketMeta(
        name="Sunset Park",
        borough="BROOKLYN",
        lat=40.6455,
        lng=-74.0124,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.69,
        capex=4500000.0,
        permit_vel=35.0,
        shift_ratio=1.26,
        sla=31.0,
        description="Waterfront innovation campus (Industry City) and vibrant multi-ethnic commercial corridors.",
    ),
    "Bay Ridge": SubmarketMeta(
        name="Bay Ridge",
        borough="BROOKLYN",
        lat=40.6262,
        lng=-74.0329,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.67,
        capex=3800000.0,
        permit_vel=27.0,
        shift_ratio=1.15,
        sla=35.0,
        description="Stable southwestern waterfront neighborhood with commercial avenues (3rd & 5th) and harbor views.",
    ),
    "Flatbush": SubmarketMeta(
        name="Flatbush",
        borough="BROOKLYN",
        lat=40.6520,
        lng=-73.9590,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.70,
        capex=4200000.0,
        permit_vel=43.0,
        shift_ratio=1.30,
        sla=33.0,
        description="Central Brooklyn hub with high transit connectivity, commercial density, and major mid-rise development.",
    ),
    "Red Hook": SubmarketMeta(
        name="Red Hook",
        borough="BROOKLYN",
        lat=40.6750,
        lng=-74.0100,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.77,
        capex=5500000.0,
        permit_vel=25.0,
        shift_ratio=1.35,
        sla=37.0,
        description="Maritime and artisanal warehouse district with strong destination retail and last-mile logistics.",
    ),
    "Coney Island": SubmarketMeta(
        name="Coney Island",
        borough="BROOKLYN",
        lat=40.5749,
        lng=-73.9859,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.63,
        capex=3900000.0,
        permit_vel=23.0,
        shift_ratio=1.21,
        sla=26.0,
        description="Iconic oceanfront amusement and residential area with large-scale affordable and market developments.",
    ),

    # =======================================================================
    # QUEENS (12 Submarkets)
    # =======================================================================
    "Long Island City": SubmarketMeta(
        name="Long Island City",
        borough="QUEENS",
        lat=40.7447,
        lng=-73.9485,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.92,
        capex=10800000.0,
        permit_vel=72.0,
        shift_ratio=1.68,
        sla=66.0,
        description="Rapidly expanding high-density waterfront skyline with unmatched transit proximity to Midtown.",
    ),
    "Astoria": SubmarketMeta(
        name="Astoria",
        borough="QUEENS",
        lat=40.7644,
        lng=-73.9235,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.81,
        capex=5900000.0,
        permit_vel=46.0,
        shift_ratio=1.37,
        sla=70.0,
        description="Premier cultural and culinary enclave with resilient retail corridors and steady multifamily infill.",
    ),
    "Sunnyside": SubmarketMeta(
        name="Sunnyside",
        borough="QUEENS",
        lat=40.7433,
        lng=-73.9196,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.75,
        capex=4500000.0,
        permit_vel=31.0,
        shift_ratio=1.25,
        sla=39.0,
        description="Close-knit residential enclave featuring Sunnyside Gardens historic planned community and Queens Blvd retail.",
    ),
    "Woodside": SubmarketMeta(
        name="Woodside",
        borough="QUEENS",
        lat=40.7454,
        lng=-73.9030,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.72,
        capex=4100000.0,
        permit_vel=33.0,
        shift_ratio=1.22,
        sla=36.0,
        description="Key transit interchange with diverse commercial spine along Roosevelt Avenue.",
    ),
    "Jackson Heights": SubmarketMeta(
        name="Jackson Heights",
        borough="QUEENS",
        lat=40.7557,
        lng=-73.8831,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.74,
        capex=4300000.0,
        permit_vel=37.0,
        shift_ratio=1.28,
        sla=48.0,
        description="Historic garden apartment district renowned for multicultural gastronomy and commercial vitality.",
    ),
    "Elmhurst": SubmarketMeta(
        name="Elmhurst",
        borough="QUEENS",
        lat=40.7368,
        lng=-73.8784,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.71,
        capex=4200000.0,
        permit_vel=35.0,
        shift_ratio=1.24,
        sla=34.0,
        description="Major commercial center with Queens Center Mall anchor and medical institutional presence.",
    ),
    "Corona": SubmarketMeta(
        name="Corona",
        borough="QUEENS",
        lat=40.7448,
        lng=-73.8643,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.68,
        capex=3700000.0,
        permit_vel=32.0,
        shift_ratio=1.20,
        sla=30.0,
        description="Dense family community bordering Flushing Meadows Corona Park with vibrant street retail.",
    ),
    "Flushing": SubmarketMeta(
        name="Flushing",
        borough="QUEENS",
        lat=40.7675,
        lng=-73.8331,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=8700000.0,
        permit_vel=55.0,
        shift_ratio=1.51,
        sla=62.0,
        description="Major Asian commercial, financial, and residential hub with intense development around Main Street.",
    ),
    "Ridgewood": SubmarketMeta(
        name="Ridgewood",
        borough="QUEENS",
        lat=40.7081,
        lng=-73.9015,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.78,
        capex=4800000.0,
        permit_vel=41.0,
        shift_ratio=1.39,
        sla=51.0,
        description="National historic brick rowhouse district attracting Bushwick spillover and artisanal retail.",
    ),
    "Forest Hills": SubmarketMeta(
        name="Forest Hills",
        borough="QUEENS",
        lat=40.7181,
        lng=-73.8448,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.79,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.23,
        sla=42.0,
        description="Prestigious neighborhood with Austin Street commercial core and historic Forest Hills Gardens.",
    ),
    "Jamaica": SubmarketMeta(
        name="Jamaica",
        borough="QUEENS",
        lat=40.7027,
        lng=-73.7890,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.73,
        capex=5400000.0,
        permit_vel=44.0,
        shift_ratio=1.36,
        sla=35.0,
        description="Key intermodal transit hub (JFK AirTrain / LIRR) driving major high-density downtown redevelopment.",
    ),
    "Long Island City / Sunnyside Yards": SubmarketMeta(
        name="Long Island City / Sunnyside Yards",
        borough="QUEENS",
        lat=40.7505,
        lng=-73.9350,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.87,
        capex=9200000.0,
        permit_vel=58.0,
        shift_ratio=1.59,
        sla=49.0,
        description="Strategic master-planned corridor linking Queensboro Plaza with Sunnyside Yards rail infrastructure.",
    ),

    # =======================================================================
    # BRONX (9 Submarkets)
    # =======================================================================
    "Mott Haven": SubmarketMeta(
        name="Mott Haven",
        borough="BRONX",
        lat=40.8090,
        lng=-73.9225,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.79,
        capex=6700000.0,
        permit_vel=53.0,
        shift_ratio=1.53,
        sla=44.0,
        description="Waterfront renaissance corridor with high-volume luxury rental developments and creative conversions.",
    ),
    "Port Morris": SubmarketMeta(
        name="Port Morris",
        borough="BRONX",
        lat=40.8010,
        lng=-73.9140,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.76,
        capex=5800000.0,
        permit_vel=42.0,
        shift_ratio=1.46,
        sla=38.0,
        description="Industrial waterfront district featuring craft breweries, film studios, and commercial conversion.",
    ),
    "South Bronx / Hub": SubmarketMeta(
        name="South Bronx / Hub",
        borough="BRONX",
        lat=40.8175,
        lng=-73.9180,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.72,
        capex=4800000.0,
        permit_vel=45.0,
        shift_ratio=1.34,
        sla=33.0,
        description="The historic 'Hub' retail core at 149th & 3rd Avenue with major civic and retail foot traffic.",
    ),
    "Grand Concourse": SubmarketMeta(
        name="Grand Concourse",
        borough="BRONX",
        lat=40.8380,
        lng=-73.9185,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.70,
        capex=4400000.0,
        permit_vel=38.0,
        shift_ratio=1.27,
        sla=29.0,
        description="Grand Art Deco residential boulevard anchored by the Bronx Museum of the Arts and courthouse district.",
    ),
    "Highbridge": SubmarketMeta(
        name="Highbridge",
        borough="BRONX",
        lat=40.8375,
        lng=-73.9270,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.66,
        capex=3600000.0,
        permit_vel=29.0,
        shift_ratio=1.21,
        sla=22.0,
        description="Hilly residential community adjacent to High Bridge pedestrian span and Harlem River crossings.",
    ),
    "Fordham / Belmont (Arthur Ave)": SubmarketMeta(
        name="Fordham / Belmont (Arthur Ave)",
        borough="BRONX",
        lat=40.8530,
        lng=-73.8885,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.75,
        capex=4700000.0,
        permit_vel=36.0,
        shift_ratio=1.30,
        sla=53.0,
        description="Arthur Avenue 'Little Italy' food corridor and Fordham University institutional anchor.",
    ),
    "Kingsbridge": SubmarketMeta(
        name="Kingsbridge",
        borough="BRONX",
        lat=40.8810,
        lng=-73.9035,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.68,
        capex=3900000.0,
        permit_vel=31.0,
        shift_ratio=1.23,
        sla=27.0,
        description="Broadway commercial shopping corridor with Kingsbridge Armory redevelopment potential.",
    ),
    "Riverdale": SubmarketMeta(
        name="Riverdale",
        borough="BRONX",
        lat=40.8930,
        lng=-73.9125,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.73,
        capex=4900000.0,
        permit_vel=22.0,
        shift_ratio=1.14,
        sla=24.0,
        description="Scenic estate and cooperative residential community overlooking the Hudson River and Palisades.",
    ),
    "Pelham Bay": SubmarketMeta(
        name="Pelham Bay",
        borough="BRONX",
        lat=40.8505,
        lng=-73.8320,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.67,
        capex=3500000.0,
        permit_vel=25.0,
        shift_ratio=1.17,
        sla=28.0,
        description="Eastern Bronx coastal neighborhood near Pelham Bay Park and City Island with strong residential stability.",
    ),

    # =======================================================================
    # STATEN ISLAND (6 Submarkets)
    # =======================================================================
    "St. George": SubmarketMeta(
        name="St. George",
        borough="STATEN_ISLAND",
        lat=40.6437,
        lng=-74.0764,
        zoom=14.0,
        pitch=45.0,
        base_lims=0.74,
        capex=5200000.0,
        permit_vel=34.0,
        shift_ratio=1.35,
        sla=31.0,
        description="Civic capital and Staten Island Ferry terminal district with waterfront outlet retail and bay views.",
    ),
    "Tompkinsville": SubmarketMeta(
        name="Tompkinsville",
        borough="STATEN_ISLAND",
        lat=40.6275,
        lng=-74.0775,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.68,
        capex=3800000.0,
        permit_vel=26.0,
        shift_ratio=1.24,
        sla=25.0,
        description="North Shore transit corridor undergoing Bay Street zoning-led revitalization.",
    ),
    "Stapleton": SubmarketMeta(
        name="Stapleton",
        borough="STATEN_ISLAND",
        lat=40.6269,
        lng=-74.0772,
        zoom=14.0,
        pitch=40.0,
        base_lims=0.70,
        capex=4100000.0,
        permit_vel=28.0,
        shift_ratio=1.28,
        sla=27.0,
        description="Historic maritime waterfront district seeing modern URBY residential development and craft culinary scene.",
    ),
    "Port Richmond": SubmarketMeta(
        name="Port Richmond",
        borough="STATEN_ISLAND",
        lat=40.6350,
        lng=-74.1250,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.64,
        capex=3200000.0,
        permit_vel=21.0,
        shift_ratio=1.18,
        sla=22.0,
        description="Kill Van Kull waterfront neighborhood with commercial avenue retail and industrial legacy.",
    ),
    "New Dorp": SubmarketMeta(
        name="New Dorp",
        borough="STATEN_ISLAND",
        lat=40.5735,
        lng=-74.1165,
        zoom=13.5,
        pitch=35.0,
        base_lims=0.69,
        capex=3600000.0,
        permit_vel=24.0,
        shift_ratio=1.19,
        sla=32.0,
        description="East Shore commercial center anchored by New Dorp Lane dining and shopping.",
    ),
    "Tottenville": SubmarketMeta(
        name="Tottenville",
        borough="STATEN_ISLAND",
        lat=40.5125,
        lng=-74.2470,
        zoom=13.0,
        pitch=30.0,
        base_lims=0.65,
        capex=3400000.0,
        permit_vel=18.0,
        shift_ratio=1.12,
        sla=19.0,
        description="South Shore historic residential community on the Arthur Kill with single-family suburban character.",
    ),
}


# ---------------------------------------------------------------------------
# Borough Catalog
# ---------------------------------------------------------------------------

NYC_BOROUGHS: Dict[str, BoroughMeta] = {
    "MANHATTAN": BoroughMeta(
        name="MANHATTAN",
        center_lat=40.7831,
        center_lng=-73.9712,
        zoom=12.0,
        bbox=NYC_BOROUGH_BBOXES["MANHATTAN"],
        submarkets=[k for k, v in NYC_SUBMARKETS.items() if v.borough == "MANHATTAN"],
    ),
    "BROOKLYN": BoroughMeta(
        name="BROOKLYN",
        center_lat=40.6782,
        center_lng=-73.9442,
        zoom=12.0,
        bbox=NYC_BOROUGH_BBOXES["BROOKLYN"],
        submarkets=[k for k, v in NYC_SUBMARKETS.items() if v.borough == "BROOKLYN"],
    ),
    "QUEENS": BoroughMeta(
        name="QUEENS",
        center_lat=40.7282,
        center_lng=-73.7949,
        zoom=11.5,
        bbox=NYC_BOROUGH_BBOXES["QUEENS"],
        submarkets=[k for k, v in NYC_SUBMARKETS.items() if v.borough == "QUEENS"],
    ),
    "BRONX": BoroughMeta(
        name="BRONX",
        center_lat=40.8448,
        center_lng=-73.8648,
        zoom=12.0,
        bbox=NYC_BOROUGH_BBOXES["BRONX"],
        submarkets=[k for k, v in NYC_SUBMARKETS.items() if v.borough == "BRONX"],
    ),
    "STATEN_ISLAND": BoroughMeta(
        name="STATEN_ISLAND",
        center_lat=40.5795,
        center_lng=-74.1502,
        zoom=11.5,
        bbox=NYC_BOROUGH_BBOXES["STATEN_ISLAND"],
        submarkets=[k for k, v in NYC_SUBMARKETS.items() if v.borough == "STATEN_ISLAND"],
    ),
}


# ---------------------------------------------------------------------------
# Helper Functions & Multi-City Registry
# ---------------------------------------------------------------------------

def _haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the Great Circle distance between two points in kilometers."""
    radius = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def get_city_catalog() -> Dict[str, Dict[str, Any]]:
    """Retrieve catalog of all supported metropolitan regions and their configuration."""
    from src.spatial.city_registry import REGISTRY

    return {
        cid.value: {
            "city_id": cid.value,
            "name": reg.name,
            "state": reg.state,
            "bbox": reg.metro_bbox,
            "center": reg.center,
            "divisions_count": len(reg.divisions),
            "divisions": list(reg.divisions.keys()),
            "submarkets_count": len(reg.submarkets),
        }
        for cid, reg in REGISTRY.items()
    }


def get_all_submarkets(city_id: Optional[str] = "nyc") -> Dict[str, SubmarketMeta]:
    """Retrieve all registered submarkets for the specified city (default 'nyc').
    
    If city_id is 'all' or '*', returns namespaced submarkets across all registered cities
    keyed as '{city_id}:{submarket_name}'.
    """
    from src.spatial.city_registry import REGISTRY, normalize_city

    if not city_id:
        city_id = "nyc"

    norm_str = city_id.strip().lower()
    if norm_str in ("all", "*"):
        return {
            f"{reg.city_id.value}:{name}": meta
            for reg in REGISTRY.values()
            for name, meta in reg.submarkets.items()
        }

    cid = normalize_city(norm_str)
    if cid and cid in REGISTRY:
        return REGISTRY[cid].submarkets

    return {}


def get_submarkets(
    city_id: Optional[str] = "nyc",
    borough_or_division: Optional[str] = None,
    *,
    borough: Optional[str] = None,
) -> Dict[str, SubmarketMeta]:
    """Retrieve submarkets, optionally filtered by city and borough/division.
    
    Supports backward-compatible invocations:
        get_submarkets() -> NYC submarkets
        get_submarkets("MANHATTAN") -> Manhattan submarkets
        get_submarkets(borough="BROOKLYN") -> Brooklyn submarkets
        get_submarkets("chicago") -> Chicago submarkets
        get_submarkets("chicago", "NORTH_SIDE") -> Chicago North Side submarkets
        get_submarkets("san_francisco") -> SF submarkets
        get_submarkets("san_francisco", "SAN_FRANCISCO_CORE") -> SF Core submarkets
        get_submarkets(city_id="san_francisco", borough_or_division="EAST_BAY") -> East Bay
    """
    from src.spatial.city_registry import ALIASES, REGISTRY, normalize_city

    target_borough = borough or borough_or_division
    target_city = city_id

    # If first positional argument is not a known city or alias (e.g. "MANHATTAN"), treat as borough
    if target_city:
        c_clean = target_city.strip().lower()
        if c_clean not in ALIASES and c_clean not in ("all", "*"):
            target_borough = target_city
            target_city = "nyc"

    if not target_city:
        target_city = "nyc"

    c_clean = target_city.strip().lower()
    if c_clean in ("all", "*"):
        base = get_all_submarkets("all")
    else:
        cid = normalize_city(c_clean)
        if cid and cid in REGISTRY:
            base = REGISTRY[cid].submarkets
        else:
            return {}

    if not target_borough:
        return base

    normalized = target_borough.strip().upper().replace(" ", "_").replace("-", "_")
    return {k: v for k, v in base.items() if v.borough == normalized}


def get_submarket_by_name(name: str, city_id: Optional[str] = None) -> Optional[SubmarketMeta]:
    """Retrieve a submarket by its exact or case-insensitive name, optionally filtered by city_id.
    
    If name contains a city prefix (e.g. 'nyc:SoHo' or 'sf:Mission'), resolves against that city.
    If name exists in multiple cities and city_id is not specified, raises ValueError for ambiguity.
    """
    if not name:
        return None

    from src.spatial.city_registry import REGISTRY, normalize_city

    # Check for namespaced prefix (e.g., 'nyc:SoHo', 'san_francisco:Mission')
    if ":" in name:
        prefix, clean_name = name.split(":", 1)
        cid = normalize_city(prefix)
        if cid and cid in REGISTRY:
            submarkets_dict = REGISTRY[cid].submarkets
            if clean_name in submarkets_dict:
                return submarkets_dict[clean_name]
            clean_lower = clean_name.strip().lower()
            for sm_name, meta in submarkets_dict.items():
                if sm_name.lower() == clean_lower:
                    return meta

    norm_name = name.strip().lower()

    if city_id:
        cid = normalize_city(city_id)
        if not cid or cid not in REGISTRY:
            return None
        submarkets_dict = REGISTRY[cid].submarkets
        if name in submarkets_dict:
            return submarkets_dict[name]
        for sm_name, meta in submarkets_dict.items():
            if sm_name.lower() == norm_name:
                return meta
        return None

    # Search across all registered cities
    matches: List[Tuple[str, SubmarketMeta]] = []
    for cid, reg in REGISTRY.items():
        if name in reg.submarkets:
            matches.append((cid.value, reg.submarkets[name]))
        else:
            for sm_name, meta in reg.submarkets.items():
                if sm_name.lower() == norm_name:
                    matches.append((cid.value, meta))
                    break

    if len(matches) == 1:
        return matches[0][1]
    elif len(matches) > 1:
        matched_cities = [c for c, _ in matches]
        raise ValueError(
            f"Ambiguous submarket name '{name}' exists in multiple cities: {matched_cities}. "
            f"Please specify city_id."
        )

    return None


def find_nearest_submarket(
    lat: float,
    lng: float,
    city_id: Optional[str] = None,
    max_distance_km: Optional[float] = 25.0,
) -> Tuple[Optional[str], float]:
    """Find the nearest submarket to a given coordinate pair.
    
    If city_id is specified, searches within that city.
    If city_id is None, infers city from coordinates or searches across all submarkets.
    If max_distance_km is specified and nearest submarket exceeds it, returns (None, min_dist).
    
    Returns:
        Tuple of (submarket_name or None, distance_in_km)
    """
    from src.spatial.city_registry import REGISTRY, normalize_city
    from src.spatial.geo_utils import get_city_for_coordinate

    if city_id:
        cid = normalize_city(city_id)
        if cid and cid in REGISTRY:
            candidate_dicts = [REGISTRY[cid].submarkets]
        else:
            candidate_dicts = [reg.submarkets for reg in REGISTRY.values()]
    else:
        inferred = get_city_for_coordinate(lat, lng)
        cid = normalize_city(inferred) if inferred else None
        if cid and cid in REGISTRY:
            candidate_dicts = [REGISTRY[cid].submarkets]
        else:
            candidate_dicts = [reg.submarkets for reg in REGISTRY.values()]

    nearest_name: Optional[str] = None
    min_dist = float("inf")

    for c_dict in candidate_dicts:
        for name, meta in c_dict.items():
            dist = _haversine_distance_km(lat, lng, meta.lat, meta.lng)
            if dist < min_dist:
                min_dist = dist
                nearest_name = name

    if max_distance_km is not None and min_dist > max_distance_km:
        return None, min_dist

    return nearest_name, min_dist


def get_borough_catalog(city_id: str = "nyc") -> Dict[str, Dict[str, Any]]:
    """Retrieve structured catalog of all divisions/boroughs for a city (default 'nyc')."""
    from src.spatial.city_registry import REGISTRY, normalize_city

    cid = normalize_city(city_id)
    if not cid or cid not in REGISTRY:
        return {}

    source = REGISTRY[cid].divisions

    return {
        div_name: {
            "name": meta.name,
            "center_lat": meta.center_lat,
            "center_lng": meta.center_lng,
            "zoom": meta.zoom,
            "bbox": meta.bbox,
            "submarkets": list(meta.submarkets),
            "submarket_count": len(meta.submarkets),
        }
        for div_name, meta in source.items()
    }


get_division_catalog = get_borough_catalog


