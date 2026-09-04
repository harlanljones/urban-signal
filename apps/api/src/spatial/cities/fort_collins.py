"""Fort Collins, CO — Urban Signal spatial registration (metro bbox, divisions, submarkets).

Leaf module: geometry only. Feed specs live in the corpus YAML beside this
leaf (data/fort_collins.yaml) and are re-bound to this REGISTRATION by the
registry derivation (US-429). US-421 onboarded Building Permits ("Current
Building Permits") from the City of Fort Collins GIS ArcGIS Hub
(services1.arcgis.com/dLpFH5mwVvxSN4OE), per the southwest/mountain
expansion probe (docs/research/southwest-mountain-expansion-probe-2026-08-30.md).

Geographic basis: Fort Collins sits in northern Larimer County along the
Cache la Poudre River, home to Colorado State University. Downtown/Old Town
is at roughly (40.585, -105.077). The metro bbox mirrors the live AGOL
FeatureServer item extent ([-105.145, 40.481] to [-104.990, 40.638]) plus a
small buffer.
"""

from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

FORT_COLLINS_CITY_ID: str = "fort_collins"

# Registration-contract center: Old Town / downtown Fort Collins.
FORT_COLLINS_CENTER: dict[str, float] = {"lat": 40.5853, "lng": -105.0844}

# Metro bbox covering the Fort Collins urbanized area (northern Larimer County).
FORT_COLLINS_METRO_BBOX: dict[str, float] = {
    "min_lat": 40.47,
    "max_lat": 40.65,
    "min_lng": -105.16,
    "max_lng": -104.98,
}

# Division bounding boxes tile the metro bbox: a north band, and a middle
# band split into west / downtown / east thirds.
FORT_COLLINS_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "NORTH_FORT_COLLINS": {"min_lat": 40.605, "max_lat": 40.65, "min_lng": -105.16, "max_lng": -104.98},
    "WEST_FOOTHILLS": {"min_lat": 40.47, "max_lat": 40.605, "min_lng": -105.16, "max_lng": -105.10},
    "DOWNTOWN_OLD_TOWN": {"min_lat": 40.47, "max_lat": 40.605, "min_lng": -105.10, "max_lng": -105.055},
    "EAST_HARMONY": {"min_lat": 40.47, "max_lat": 40.605, "min_lng": -105.055, "max_lng": -104.98},
}


def is_in_fort_collins_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Fort Collins metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        FORT_COLLINS_METRO_BBOX["min_lat"] <= lat <= FORT_COLLINS_METRO_BBOX["max_lat"]
        and FORT_COLLINS_METRO_BBOX["min_lng"] <= lng <= FORT_COLLINS_METRO_BBOX["max_lng"]
    )


FORT_COLLINS_SUBMARKETS: dict[str, SubmarketMeta] = {
    # DOWNTOWN_OLD_TOWN
    "Old Town": SubmarketMeta(
        name="Old Town",
        borough="DOWNTOWN_OLD_TOWN",
        lat=40.5853,
        lng=-105.0772,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.82,
        capex=5600000.0,
        permit_vel=27.0,
        shift_ratio=1.38,
        sla=50.0,
        description="Historic Old Town core with adaptive-reuse and mixed-use infill permitting.",
        city_id=FORT_COLLINS_CITY_ID,
    ),
    "Civic Center": SubmarketMeta(
        name="Civic Center",
        borough="DOWNTOWN_OLD_TOWN",
        lat=40.5670,
        lng=-105.0790,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=4900000.0,
        permit_vel=23.0,
        shift_ratio=1.33,
        sla=47.0,
        description="Civic Center and CSU-adjacent commercial corridor with steady permit churn.",
        city_id=FORT_COLLINS_CITY_ID,
    ),
    # WEST_FOOTHILLS
    "CSU Campus West": SubmarketMeta(
        name="CSU Campus West",
        borough="WEST_FOOTHILLS",
        lat=40.5730,
        lng=-105.1200,
        zoom=13.8,
        pitch=44.0,
        base_lims=0.74,
        capex=4200000.0,
        permit_vel=20.0,
        shift_ratio=1.28,
        sla=44.0,
        description="Colorado State University campus-west student housing and rental infill.",
        city_id=FORT_COLLINS_CITY_ID,
    ),
    "Foothills West": SubmarketMeta(
        name="Foothills West",
        borough="WEST_FOOTHILLS",
        lat=40.5500,
        lng=-105.1400,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.68,
        capex=3600000.0,
        permit_vel=17.0,
        shift_ratio=1.22,
        sla=41.0,
        description="Foothills-facing west edge with low-density residential remodel permitting.",
        city_id=FORT_COLLINS_CITY_ID,
    ),
    # EAST_HARMONY
    "Harmony Corridor": SubmarketMeta(
        name="Harmony Corridor",
        borough="EAST_HARMONY",
        lat=40.5230,
        lng=-105.0300,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=25.0,
        shift_ratio=1.36,
        sla=48.0,
        description="Harmony Rd tech/office corridor with commercial new-build permitting.",
        city_id=FORT_COLLINS_CITY_ID,
    ),
    "Timberline": SubmarketMeta(
        name="Timberline",
        borough="EAST_HARMONY",
        lat=40.5500,
        lng=-105.0000,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.71,
        capex=3900000.0,
        permit_vel=18.0,
        shift_ratio=1.24,
        sla=42.0,
        description="East side residential and light-industrial belt along Timberline Rd.",
        city_id=FORT_COLLINS_CITY_ID,
    ),
    # NORTH_FORT_COLLINS
    "Old Town North": SubmarketMeta(
        name="Old Town North",
        borough="NORTH_FORT_COLLINS",
        lat=40.6200,
        lng=-105.0700,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.76,
        capex=4600000.0,
        permit_vel=22.0,
        shift_ratio=1.31,
        sla=45.0,
        description="Old Town North master-planned area with new-build residential permitting.",
        city_id=FORT_COLLINS_CITY_ID,
    ),
    "Dry Creek": SubmarketMeta(
        name="Dry Creek",
        borough="NORTH_FORT_COLLINS",
        lat=40.6350,
        lng=-105.0300,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.70,
        capex=3800000.0,
        permit_vel=17.0,
        shift_ratio=1.23,
        sla=41.0,
        description="North edge Dry Creek growth area with residential build-out.",
        city_id=FORT_COLLINS_CITY_ID,
    ),
}


FORT_COLLINS_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_OLD_TOWN": BoroughMeta(
        name="DOWNTOWN_OLD_TOWN",
        center_lat=40.578,
        center_lng=-105.078,
        zoom=13.8,
        bbox=FORT_COLLINS_DIVISION_BBOXES["DOWNTOWN_OLD_TOWN"],
        submarkets=[k for k, v in FORT_COLLINS_SUBMARKETS.items() if v.borough == "DOWNTOWN_OLD_TOWN"],
        city_id=FORT_COLLINS_CITY_ID,
    ),
    "WEST_FOOTHILLS": BoroughMeta(
        name="WEST_FOOTHILLS",
        center_lat=40.560,
        center_lng=-105.130,
        zoom=13.0,
        bbox=FORT_COLLINS_DIVISION_BBOXES["WEST_FOOTHILLS"],
        submarkets=[k for k, v in FORT_COLLINS_SUBMARKETS.items() if v.borough == "WEST_FOOTHILLS"],
        city_id=FORT_COLLINS_CITY_ID,
    ),
    "EAST_HARMONY": BoroughMeta(
        name="EAST_HARMONY",
        center_lat=40.535,
        center_lng=-105.015,
        zoom=13.0,
        bbox=FORT_COLLINS_DIVISION_BBOXES["EAST_HARMONY"],
        submarkets=[k for k, v in FORT_COLLINS_SUBMARKETS.items() if v.borough == "EAST_HARMONY"],
        city_id=FORT_COLLINS_CITY_ID,
    ),
    "NORTH_FORT_COLLINS": BoroughMeta(
        name="NORTH_FORT_COLLINS",
        center_lat=40.627,
        center_lng=-105.050,
        zoom=12.8,
        bbox=FORT_COLLINS_DIVISION_BBOXES["NORTH_FORT_COLLINS"],
        submarkets=[k for k, v in FORT_COLLINS_SUBMARKETS.items() if v.borough == "NORTH_FORT_COLLINS"],
        city_id=FORT_COLLINS_CITY_ID,
    ),
}

REGISTRATION = SpatialRegistration(
    metro_bbox=FORT_COLLINS_METRO_BBOX,
    division_bboxes=FORT_COLLINS_DIVISION_BBOXES,
    submarkets=FORT_COLLINS_SUBMARKETS,
    divisions=FORT_COLLINS_DIVISIONS,
    contains=is_in_fort_collins_metro,
)

__all__ = [
    "FORT_COLLINS_CENTER",
    "FORT_COLLINS_CITY_ID",
    "FORT_COLLINS_DIVISIONS",
    "FORT_COLLINS_DIVISION_BBOXES",
    "FORT_COLLINS_METRO_BBOX",
    "FORT_COLLINS_SUBMARKETS",
    "REGISTRATION",
    "is_in_fort_collins_metro",
]
