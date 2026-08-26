"""Austin Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Austin and
the greater metro's northern edges (Pflugerville / Round Rock corridor), TX.

Austin registers as a THREE-FEED partial city like Los Angeles: PERMITS
(`quv8-5ckq` Issued Building Permits), COMPLAINTS_311 (`xwdj-i9he`), and an
SLA liquor-license feed pulled from TABC's statewide open data (data.texas.gov
`7hf9-qc9f` "TABC License Information"). DEEDS remains deliberately absent:
the Travis County portal (data.traviscountytx.gov) is a FedRAMP Socrata shell
whose catalog API answers "Domain not found".

The TABC feed locates each license with a STREET ``address`` string but carries
NO latitude/longitude columns — exactly the address-only case ADR 0004 was
written for. It registers with ``needs_geocode: True`` and recovers coordinates
through the Postgres-replay geocoder at parse time. The companion legacy
cross-reference `kguh-7q9z` ("TABCLicenses") is NOT a registration target: it
is a 2021 AIMS migration cross-walk with trailing-space-padded addresses and no
authoritative status/issue dates. See docs/research/
new-orleans-austin-verification.md and US-136.
"""

from typing import Dict

from src.config import settings
from src.spatial.submarkets import BoroughMeta, SubmarketMeta
from src.producers.field_maps_austin_tabc import FIELD_MAP as _TABC_FIELD_MAPS

# Greater Austin metro bounding box: Travis County plus the Round Rock /
# Pflugerville growth corridor to the north. Both registered feeds are
# City-of-Austin-scoped in practice (~0.6% null-geocoded rows aside), so
# metro-bbox filtering is permissive here; it only has to keep every live
# sample inside (Parmer Commons ~30.367,-97.612; downtown ~30.27,-97.74;
# Slaughter Ln south ~30.19; far NW ~-97.90).
AUSTIN_METRO_BBOX: Dict[str, float] = {
    "min_lat": 30.10,
    "max_lat": 30.62,
    "min_lng": -98.05,
    "max_lng": -97.52,
}

# 6 Austin Division Bounding Boxes. Approximate hand-authored geographies;
# borough resolution at ingest comes from coordinates via
# get_division_for_coordinate (council-district strings in both feeds are
# bare numerals like "1"/"5", not division names), so bboxes need only be
# sane and disjoint enough to resolve unambiguously near their centers.
AUSTIN_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_CAPITOL":       {"min_lat": 30.25,  "max_lat": 30.29,  "min_lng": -97.765, "max_lng": -97.725},
    "EAST_AUSTIN_MUELLER":    {"min_lat": 30.25,  "max_lat": 30.31,  "min_lng": -97.72,  "max_lng": -97.66},
    "SOUTH_AUSTIN_SOCO":      {"min_lat": 30.16,  "max_lat": 30.25,  "min_lng": -97.81,  "max_lng": -97.72},
    "NORTH_AUSTIN_DOMAIN":    {"min_lat": 30.305, "max_lat": 30.48,  "min_lng": -97.76,  "max_lng": -97.655},
    "WEST_AUSTIN_HILLS":      {"min_lat": 30.25,  "max_lat": 30.40,  "min_lng": -97.865, "max_lng": -97.755},
    "PFLUGERVILLE_ROUND_ROCK_EDGE": {"min_lat": 30.39, "max_lat": 30.55, "min_lng": -97.72, "max_lng": -97.52},
}


def is_in_austin_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Austin Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        AUSTIN_METRO_BBOX["min_lat"] <= lat <= AUSTIN_METRO_BBOX["max_lat"]
        and AUSTIN_METRO_BBOX["min_lng"] <= lng <= AUSTIN_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_greater_austin_metro = is_in_austin_metro


AUSTIN_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CAPITOL (3 Submarkets)
    # =======================================================================
    "Rainey Street & Riverfront": SubmarketMeta(
        name="Rainey Street & Riverfront",
        borough="DOWNTOWN_CAPITOL",
        lat=30.2565,
        lng=-97.7370,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.93,
        capex=12000000.0,
        permit_vel=58.0,
        shift_ratio=1.7,
        sla=75.0,
        description="Bungalow-to-tower conversion district on Lady Bird Lake's north shore, where hotel and residential towers dominate the permit pipeline.",
        city_id="austin",
    ),
    "Warehouse District": SubmarketMeta(
        name="Warehouse District",
        borough="DOWNTOWN_CAPITOL",
        lat=30.2685,
        lng=-97.7505,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.89,
        capex=9800000.0,
        permit_vel=44.0,
        shift_ratio=1.61,
        sla=70.0,
        description="Historic supply-warehouse blocks west of Congress now carrying office-to-residential conversions and ground-floor hospitality.",
        city_id="austin",
    ),
    "Congress Ave & Capitol Complex": SubmarketMeta(
        name="Congress Ave & Capitol Complex",
        borough="DOWNTOWN_CAPITOL",
        lat=30.2745,
        lng=-97.7355,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.87,
        capex=11000000.0,
        permit_vel=46.0,
        shift_ratio=1.57,
        sla=67.0,
        description="Capitol-view office spine with the Texas Capitol complex and state-tenant demand anchoring the state government economy.",
        city_id="austin",
    ),
    # =======================================================================
    # EAST_AUSTIN_MUELLER (3 Submarkets)
    # =======================================================================
    "East Cesar Chavez & Holly": SubmarketMeta(
        name="East Cesar Chavez & Holly",
        borough="EAST_AUSTIN_MUELLER",
        lat=30.2575,
        lng=-97.7165,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=7800000.0,
        permit_vel=47.0,
        shift_ratio=1.56,
        sla=64.0,
        description="Former industrial riverfront edge east of I-35 with townhome infill, music-venue adaptive reuse, and sustained small-lot development.",
        city_id="austin",
    ),
    "East 6th Street Corridor": SubmarketMeta(
        name="East 6th Street Corridor",
        borough="EAST_AUSTIN_MUELLER",
        lat=30.2645,
        lng=-97.7105,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=6400000.0,
        permit_vel=43.0,
        shift_ratio=1.51,
        sla=60.0,
        description="Bar-and-venue strip turned mixed-use corridor with mid-rise multifamily replacing single-story commercial east of the highway.",
        city_id="austin",
    ),
    "Mueller & Cherrywood": SubmarketMeta(
        name="Mueller & Cherrywood",
        borough="EAST_AUSTIN_MUELLER",
        lat=30.2975,
        lng=-97.7075,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.88,
        capex=9200000.0,
        permit_vel=52.0,
        shift_ratio=1.59,
        sla=63.0,
        description="Master-planned airport redevelopment with continued buildout phases adjacent to Cherrywood and Windsor Park bungalow stock.",
        city_id="austin",
    ),
    # =======================================================================
    # SOUTH_AUSTIN_SOCO (3 Submarkets)
    # =======================================================================
    "South Congress (SoCo)": SubmarketMeta(
        name="South Congress (SoCo)",
        borough="SOUTH_AUSTIN_SOCO",
        lat=30.2455,
        lng=-97.7505,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=8600000.0,
        permit_vel=41.0,
        shift_ratio=1.54,
        sla=62.0,
        description="Hotel-and-retail flagship corridor with boutique lodging conversions and skyline-view multifamily on its side streets.",
        city_id="austin",
    ),
    "Travis Heights": SubmarketMeta(
        name="Travis Heights",
        borough="SOUTH_AUSTIN_SOCO",
        lat=30.2395,
        lng=-97.7415,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.84,
        capex=6900000.0,
        permit_vel=33.0,
        shift_ratio=1.49,
        sla=58.0,
        description="Historic district of craftsman and mid-century stock south of Lake Shore Drive, with renovation-heavy permitting and strict tree ordinances.",
        city_id="austin",
    ),
    "Bouldin Creek": SubmarketMeta(
        name="Bouldin Creek",
        borough="SOUTH_AUSTIN_SOCO",
        lat=30.2475,
        lng=-97.7625,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.82,
        capex=6100000.0,
        permit_vel=35.0,
        shift_ratio=1.46,
        sla=57.0,
        description="Cottage-grid neighbourhood between S 1st and Lamar with teardown/rebuild pressure and independent retail spines.",
        city_id="austin",
    ),
    # =======================================================================
    # NORTH_AUSTIN_DOMAIN (2 Submarkets)
    # =======================================================================
    "The Domain & North Burnet": SubmarketMeta(
        name="The Domain & North Burnet",
        borough="NORTH_AUSTIN_DOMAIN",
        lat=30.4005,
        lng=-97.7245,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.9,
        capex=12000000.0,
        permit_vel=55.0,
        shift_ratio=1.65,
        sla=68.0,
        description="Apple-, Amazon- and Meta-anchored secondary downtown under the Burnet/Braker overlay, with the metro's densest office pipeline outside the core.",
        city_id="austin",
    ),
    "Hyde Park & North Loop": SubmarketMeta(
        name="Hyde Park & North Loop",
        borough="NORTH_AUSTIN_DOMAIN",
        lat=30.3135,
        lng=-97.7255,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=29.0,
        shift_ratio=1.38,
        sla=54.0,
        description="Streetcar-era bungalow historic district meeting the North Loop indie-retail strip, with renovation-led permits and neighborhood-conservation overlays.",
        city_id="austin",
    ),
    # =======================================================================
    # WEST_AUSTIN_HILLS (3 Submarkets)
    # =======================================================================
    "Westlake Hills Edge": SubmarketMeta(
        name="Westlake Hills Edge",
        borough="WEST_AUSTIN_HILLS",
        lat=30.2905,
        lng=-97.8055,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.91,
        capex=10500000.0,
        permit_vel=22.0,
        shift_ratio=1.52,
        sla=50.0,
        description="Hill-country estate stock at the Westlake village boundary with teardown-rebuild mansions dominating a low-volume, high-value permit mix.",
        city_id="austin",
    ),
    "Barton Hills & Zilker": SubmarketMeta(
        name="Barton Hills & Zilker",
        borough="WEST_AUSTIN_HILLS",
        lat=30.2535,
        lng=-97.7805,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.79,
        capex=5600000.0,
        permit_vel=28.0,
        shift_ratio=1.4,
        sla=56.0,
        description="Park-adjacent post-war residential hills beside Zilker Park, drawing renovation capital from greenbelt access.",
        city_id="austin",
    ),
    "South Lamar Corridor": SubmarketMeta(
        name="South Lamar Corridor",
        borough="WEST_AUSTIN_HILLS",
        lat=30.2625,
        lng=-97.7725,
        zoom=13.5,
        pitch=45.0,
        base_lims=0.81,
        capex=6500000.0,
        permit_vel=38.0,
        shift_ratio=1.47,
        sla=59.0,
        description="Strip-retail arterial undergoing station-area densification with multifamily replacements of aging retail and motel stock.",
        city_id="austin",
    ),
    # =======================================================================
    # PFLUGERVILLE_ROUND_ROCK_EDGE (2 Submarkets)
    # =======================================================================
    "Tech Ridge & Pflugerville South": SubmarketMeta(
        name="Tech Ridge & Pflugerville South",
        borough="PFLUGERVILLE_ROUND_ROCK_EDGE",
        lat=30.4155,
        lng=-97.6835,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.62,
        capex=3400000.0,
        permit_vel=36.0,
        shift_ratio=1.24,
        sla=41.0,
        description="Transit-oriented park-and-ride node shading into Pflugerville's southern subdivisions along the I-35 growth spine.",
        city_id="austin",
    ),
    "Round Rock Edge & La Frontera": SubmarketMeta(
        name="Round Rock Edge & La Frontera",
        borough="PFLUGERVILLE_ROUND_ROCK_EDGE",
        lat=30.5055,
        lng=-97.7005,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.58,
        capex=2900000.0,
        permit_vel=24.0,
        shift_ratio=1.18,
        sla=37.0,
        description="Williamson County commercial edge at the metro's northern boundary, permitted through Round Rock rather than the City of Austin.",
        city_id="austin",
    ),
}


AUSTIN_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CAPITOL": BoroughMeta(
        name="DOWNTOWN_CAPITOL",
        center_lat=30.267,
        center_lng=-97.74,
        zoom=13.5,
        bbox=AUSTIN_DIVISION_BBOXES["DOWNTOWN_CAPITOL"],
        submarkets=[k for k, v in AUSTIN_SUBMARKETS.items() if v.borough == "DOWNTOWN_CAPITOL"],
        city_id="austin",
    ),
    "EAST_AUSTIN_MUELLER": BoroughMeta(
        name="EAST_AUSTIN_MUELLER",
        center_lat=30.28,
        center_lng=-97.69,
        zoom=13.0,
        bbox=AUSTIN_DIVISION_BBOXES["EAST_AUSTIN_MUELLER"],
        submarkets=[k for k, v in AUSTIN_SUBMARKETS.items() if v.borough == "EAST_AUSTIN_MUELLER"],
        city_id="austin",
    ),
    "SOUTH_AUSTIN_SOCO": BoroughMeta(
        name="SOUTH_AUSTIN_SOCO",
        center_lat=30.21,
        center_lng=-97.75,
        zoom=13.0,
        bbox=AUSTIN_DIVISION_BBOXES["SOUTH_AUSTIN_SOCO"],
        submarkets=[k for k, v in AUSTIN_SUBMARKETS.items() if v.borough == "SOUTH_AUSTIN_SOCO"],
        city_id="austin",
    ),
    "NORTH_AUSTIN_DOMAIN": BoroughMeta(
        name="NORTH_AUSTIN_DOMAIN",
        center_lat=30.36,
        center_lng=-97.72,
        zoom=12.5,
        bbox=AUSTIN_DIVISION_BBOXES["NORTH_AUSTIN_DOMAIN"],
        submarkets=[k for k, v in AUSTIN_SUBMARKETS.items() if v.borough == "NORTH_AUSTIN_DOMAIN"],
        city_id="austin",
    ),
    "WEST_AUSTIN_HILLS": BoroughMeta(
        name="WEST_AUSTIN_HILLS",
        center_lat=30.28,
        center_lng=-97.79,
        zoom=12.5,
        bbox=AUSTIN_DIVISION_BBOXES["WEST_AUSTIN_HILLS"],
        submarkets=[k for k, v in AUSTIN_SUBMARKETS.items() if v.borough == "WEST_AUSTIN_HILLS"],
        city_id="austin",
    ),
    "PFLUGERVILLE_ROUND_ROCK_EDGE": BoroughMeta(
        name="PFLUGERVILLE_ROUND_ROCK_EDGE",
        center_lat=30.46,
        center_lng=-97.65,
        zoom=11.5,
        bbox=AUSTIN_DIVISION_BBOXES["PFLUGERVILLE_ROUND_ROCK_EDGE"],
        submarkets=[k for k, v in AUSTIN_SUBMARKETS.items() if v.borough == "PFLUGERVILLE_ROUND_ROCK_EDGE"],
        city_id="austin",
    ),
}

# Verbose aliases mirroring los_angeles.py's LA_*/LOS_ANGELES_* pairs.
GREATER_AUSTIN_METRO_BBOX = AUSTIN_METRO_BBOX
ATX_DIVISION_BBOXES = AUSTIN_DIVISION_BBOXES
ATX_SUBMARKETS = AUSTIN_SUBMARKETS
ATX_DIVISIONS = AUSTIN_DIVISIONS

# ---------------------------------------------------------------------------
# Proposed TABC liquor-license (SLA) feed spec — US-136, ADR 0004 geocode path.
# ---------------------------------------------------------------------------
# LEAF PROPOSAL. This is NOT wired into REGISTRY yet; the orchestrator imports
# the data below into ``city_registry.REGISTRY[CityId.AUSTIN].datasets`` at the
# interlock. Pinned against the live data.texas.gov view `7hf9-qc9f`
# ("TABC License Information") schema pulled 2026-08-26.
#
# The feed has no latitude/longitude columns — only a street ``address`` string —
# so it declares ``needs_geocode: True`` and ``geocode_context``; the ADR 0004
# geocoder recovers real coordinates at parse time. ``status_change_date`` is the
# watermark: it is the only column that advances on every Primary Status change
# (new issuances, renewals, suspensions, surrenders), so it is the correct
# incremental-poll cursor for a slowly-churning license file.
AUSTIN_TABC_SLA_SPEC: Dict[str, object] = {
    "endpoint": "https://data.texas.gov/resource/7hf9-qc9f.json",
    "platform": "socrata",
    "watermark_col": "status_change_date",
    "id_keys": ["license_id"],
    "topic": settings.topic_sla,
    "interval_seconds": 600.0,
    "producer_key": "sla",
    "extra": {
        "expected_cadence_days": 7,
        "needs_geocode": True,
        "geocode_context": "Austin, TX",
        "field_map": _TABC_FIELD_MAPS["sla"],
    },
}
