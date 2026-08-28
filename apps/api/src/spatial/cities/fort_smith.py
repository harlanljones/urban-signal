"""Fort Smith, Arkansas spatial registry and geometry.

Fort Smith registers initially as a SNAP-as-SLA-only metro (US-275) — no
public municipal permits API was verified at claim time (CityView portal is
present; no open ArcGIS/Socrata/CKAN endpoint found). The spine will wire
`snap_sla_spec("AR")` for the SLA slice; permits/311/deeds remain unregistered
and `get_dataset()` will raise readable errors for them.

This leaf defines the metro/division bboxes and submarket catalog so the
interlock containment gate passes and the dashboard snapshot/grid layers can
cover the metro on registration.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Fort Smith metro bounding box (permissive extent around the city)
FORT_SMITH_METRO_BBOX: Dict[str, float] = {
    "min_lat": 35.28,
    "max_lat": 35.45,
    "min_lng": -94.49,
    "max_lng": -94.25,
}

# Single division covering the city core
FORT_SMITH_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "FORT_SMITH_CORE": {
        "min_lat": 35.30,
        "max_lat": 35.43,
        "min_lng": -94.46,
        "max_lng": -94.28,
    },
}


def is_in_fort_smith_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate is inside the registered Fort Smith extent."""
    if lat is None or lng is None:
        return False
    return (
        FORT_SMITH_METRO_BBOX["min_lat"] <= lat <= FORT_SMITH_METRO_BBOX["max_lat"]
        and FORT_SMITH_METRO_BBOX["min_lng"] <= lng <= FORT_SMITH_METRO_BBOX["max_lng"]
    )


# Submarket catalog (centroids and presentation metadata)
FORT_SMITH_SUBMARKETS: Dict[str, SubmarketMeta] = {
    "Downtown & Garrison Ave": SubmarketMeta(
        name="Downtown & Garrison Ave",
        borough="FORT_SMITH_CORE",
        lat=35.3875,
        lng=-94.4210,
        zoom=13.6,
        pitch=46.0,
        base_lims=0.79,
        capex=2400000.0,
        permit_vel=18.0,
        shift_ratio=1.22,
        sla=42.0,
        description="Historic core and entertainment corridor with adaptive reuse and small mixed-use infill.",
        city_id="fort_smith",
    ),
    "Rogers Avenue Corridor": SubmarketMeta(
        name="Rogers Avenue Corridor",
        borough="FORT_SMITH_CORE",
        lat=35.3540,
        lng=-94.3580,
        zoom=13.2,
        pitch=42.0,
        base_lims=0.77,
        capex=2100000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=40.0,
        description="Primary east–west commercial spine with incremental retail reinvestment and site upgrades.",
        city_id="fort_smith",
    ),
    "Fianna Hills & Southside": SubmarketMeta(
        name="Fianna Hills & Southside",
        borough="FORT_SMITH_CORE",
        lat=35.3120,
        lng=-94.3760,
        zoom=12.9,
        pitch=40.0,
        base_lims=0.75,
        capex=1950000.0,
        permit_vel=14.0,
        shift_ratio=1.15,
        sla=39.0,
        description="Southside neighborhoods with renovation-led residential activity and neighborhood services.",
        city_id="fort_smith",
    ),
    "Chaffee Crossing": SubmarketMeta(
        name="Chaffee Crossing",
        borough="FORT_SMITH_CORE",
        lat=35.3340,
        lng=-94.2840,
        zoom=13.2,
        pitch=42.0,
        base_lims=0.78,
        capex=2300000.0,
        permit_vel=17.0,
        shift_ratio=1.20,
        sla=41.0,
        description="Redeveloping east-side district with mixed-use and residential growth near the river bend.",
        city_id="fort_smith",
    ),
    "Riverfront & Belle Grove": SubmarketMeta(
        name="Riverfront & Belle Grove",
        borough="FORT_SMITH_CORE",
        lat=35.3940,
        lng=-94.4090,
        zoom=13.4,
        pitch=44.0,
        base_lims=0.76,
        capex=2050000.0,
        permit_vel=15.0,
        shift_ratio=1.17,
        sla=40.0,
        description="Arkansas Riverfront and adjacent historic residential fabric; steady renovation and public-realm work.",
        city_id="fort_smith",
    ),
}


FORT_SMITH_DIVISIONS: Dict[str, BoroughMeta] = {
    "FORT_SMITH_CORE": BoroughMeta(
        name="Fort Smith Core",
        center_lat=35.3859,
        center_lng=-94.3985,
        zoom=11.7,
        bbox=FORT_SMITH_DIVISION_BBOXES["FORT_SMITH_CORE"],
        submarkets=list(FORT_SMITH_SUBMARKETS),
        city_id="fort_smith",
    ),
}

# Verbose aliases for symmetry with other modules
GREATER_FORT_SMITH_METRO_BBOX = FORT_SMITH_METRO_BBOX
FORT_SMITH_DIVISION_BBOXES = FORT_SMITH_DIVISION_BBOXES
FORT_SMITH_DIVISIONS = FORT_SMITH_DIVISIONS
FORT_SMITH_SUBMARKETS = FORT_SMITH_SUBMARKETS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=FORT_SMITH_METRO_BBOX,
    division_bboxes=FORT_SMITH_DIVISION_BBOXES,
    submarkets=FORT_SMITH_SUBMARKETS,
    divisions=FORT_SMITH_DIVISIONS,
    contains=is_in_fort_smith_metro,
)

