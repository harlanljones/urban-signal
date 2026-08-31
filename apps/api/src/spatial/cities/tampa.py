FIELD_MAP = {
    "job_id": ["RECORD_ID"],
    "issuance_date": ["LASTUPDATE"],
    "status": ["PROJECTSTATUS"],
    "job_type": ["RECORDTYPE", "PROJECTDESCRIPTION", "OCCUPANCYTYPE"],
    "cost": ["NEWCONSTRUCTIONSF"],
    "address_street": ["ADDRESS"],
    "zipcode": ["ZIP"],
    "borough": ["NEIGHBORHOOD", "COUNCIL"],
    "proposed_units": ["NBROFUNITS"],
}

SLA_FIELD_MAP = {
    "license_id": ["ORD_PERMIT", "APP_NUM"],
    "license_type": ["ABSALETYPE", "AB_CLASS_PREFIX", "AB_CLASS_SUFFIX"],
    "premises_name": ["BUS_NAME"],
    "dba": ["BUS_NAME"],
    "effective_date": ["HISTORY_ACT_DT"],
    "expiration_date": ["MTH24_END_DT"],
    "status": ["HISTORY_ACTION"],
    "address_street": ["PERMIT_ADDR", "BUS_OWNER_MAIL_ADD"],
    "zipcode": ["PERMIT_ZIP"],
}

"""Tampa Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Tampa and
greater Hillsborough County, FL.

Tampa registers as a PARTIAL city like Austin/Los Angeles. Live ArcGIS
verification found a full permits layer and an alcohol-beverage action-history
layer that supports a partial SLA signal. Both are point feeds with date
watermarks; the permits watermark is an edit stamp rather than an issuance date.
311 remains token-gated and no usable deeds feed was found, so those families
are deliberately absent; ``get_tampa_dataset()`` raises a readable error for
them, exactly like the shared ``get_dataset()`` contract.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Canonical, stable city id string for Tampa. Imported by the leaf field-map
# module (field_maps_tampa.py) so the two leaf files cannot drift apart.
TAMPA_CITY_ID: str = "tampa"

# Greater Tampa / Hillsborough County metro bounding box. The metro bbox is
# permissive enough to contain every declared division, submarket, and live
# permit/SLA sample.
TAMPA_METRO_BBOX: Dict[str, float] = {
    "min_lat": 27.84,
    "max_lat": 28.16,
    "min_lng": -82.60,
    "max_lng": -82.22,
}

# 7 Tampa/Hillsborough Division Bounding Boxes. Hand-authored geographies;
# borough resolution at ingest comes from coordinates via
# get_division_for_coordinate, so bboxes need only be sane and disjoint enough
# to resolve unambiguously near their centers.
TAMPA_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_CHANNEL":          {"min_lat": 27.920, "max_lat": 27.970, "min_lng": -82.470, "max_lng": -82.410},
    "HYDE_PARK_BAYSHORE":        {"min_lat": 27.900, "max_lat": 27.950, "min_lng": -82.490, "max_lng": -82.440},
    "WESTSHORE_INTERNATIONAL":   {"min_lat": 27.930, "max_lat": 27.980, "min_lng": -82.570, "max_lng": -82.500},
    "SOUTH_TAMPA_PALMA":         {"min_lat": 27.860, "max_lat": 27.930, "min_lng": -82.520, "max_lng": -82.450},
    "TAMPA_HEIGHTS_SEMINOLE":    {"min_lat": 27.970, "max_lat": 28.020, "min_lng": -82.430, "max_lng": -82.370},
    "CARROLLWOOD_NORTH":         {"min_lat": 28.030, "max_lat": 28.100, "min_lng": -82.520, "max_lng": -82.430},
    "BRANDON_EAST":              {"min_lat": 27.900, "max_lat": 27.990, "min_lng": -82.350, "max_lng": -82.250},
}


def is_in_tampa_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Tampa Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        TAMPA_METRO_BBOX["min_lat"] <= lat <= TAMPA_METRO_BBOX["max_lat"]
        and TAMPA_METRO_BBOX["min_lng"] <= lng <= TAMPA_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_greater_tampa_metro = is_in_tampa_metro


TAMPA_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CHANNEL (3 Submarkets)
    # =======================================================================
    "Downtown Tampa Core": SubmarketMeta(
        name="Downtown Tampa Core",
        borough="DOWNTOWN_CHANNEL",
        lat=27.948,
        lng=-82.458,
        zoom=15.0,
        pitch=55.0,
        base_lims=0.90,
        capex=11000000.0,
        permit_vel=52.0,
        shift_ratio=1.68,
        sla=70.0,
        description="Central business district around Curtis Hixon Park with riverwalk towers, office-to-residential conversions, and the Tampa Convention Center spine.",
        city_id="tampa",
    ),
    "Channel District & Water Street": SubmarketMeta(
        name="Channel District & Water Street",
        borough="DOWNTOWN_CHANNEL",
        lat=27.938,
        lng=-82.450,
        zoom=15.0,
        pitch=52.0,
        base_lims=0.92,
        capex=12500000.0,
        permit_vel=58.0,
        shift_ratio=1.72,
        sla=72.0,
        description="Water Street mixed-use redevelopment and luxury residential towers on the former ship channel, the metro's densest permit pipeline.",
        city_id="tampa",
    ),
    "Marina & Tampa Riverwalk": SubmarketMeta(
        name="Marina & Tampa Riverwalk",
        borough="DOWNTOWN_CHANNEL",
        lat=27.945,
        lng=-82.465,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=8800000.0,
        permit_vel=44.0,
        shift_ratio=1.55,
        sla=64.0,
        description="Ashley Drive marina frontage and riverwalk-adjacent mid-rise infill between downtown and Hyde Park.",
        city_id="tampa",
    ),
    # =======================================================================
    # HYDE_PARK_BAYSHORE (3 Submarkets)
    # =======================================================================
    "Hyde Park Village": SubmarketMeta(
        name="Hyde Park Village",
        borough="HYDE_PARK_BAYSHORE",
        lat=27.935,
        lng=-82.465,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.88,
        capex=9200000.0,
        permit_vel=47.0,
        shift_ratio=1.57,
        sla=66.0,
        description="Historic streetcar suburb of bungalow and masonry stock around Hyde Park Village, with teardown/rebuild pressure on large lots.",
        city_id="tampa",
    ),
    "Bayshore Boulevard": SubmarketMeta(
        name="Bayshore Boulevard",
        borough="HYDE_PARK_BAYSHORE",
        lat=27.915,
        lng=-82.470,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.87,
        capex=9600000.0,
        permit_vel=42.0,
        shift_ratio=1.54,
        sla=63.0,
        description="Tampa's signature waterfront boulevard with estate-scale homes and consistent luxury renovation permits.",
        city_id="tampa",
    ),
    "SoHo (South Howard)": SubmarketMeta(
        name="SoHo (South Howard)",
        borough="HYDE_PARK_BAYSHORE",
        lat=27.930,
        lng=-82.480,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.84,
        capex=7000000.0,
        permit_vel=39.0,
        shift_ratio=1.49,
        sla=60.0,
        description="South Howard Avenue hospitality and retail corridor with apartment-infill and adaptive reuse of commercial storefronts.",
        city_id="tampa",
    ),
    # =======================================================================
    # WESTSHORE_INTERNATIONAL (3 Submarkets)
    # =======================================================================
    "International Plaza & Westshore": SubmarketMeta(
        name="International Plaza & Westshore",
        borough="WESTSHORE_INTERNATIONAL",
        lat=27.955,
        lng=-82.540,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.90,
        capex=11500000.0,
        permit_vel=50.0,
        shift_ratio=1.64,
        sla=67.0,
        description="Westshore business district anchored by International Plaza and Tampa International Airport, with office-to-residential conversion interest.",
        city_id="tampa",
    ),
    "Tampa Airport & Carrollwood Commons": SubmarketMeta(
        name="Tampa Airport & Carrollwood Commons",
        borough="WESTSHORE_INTERNATIONAL",
        lat=27.970,
        lng=-82.555,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=34.0,
        shift_ratio=1.41,
        sla=54.0,
        description="Airport-adjacent commercial edge and hotel/warehouse permitting northwest of the Westshore core.",
        city_id="tampa",
    ),
    "Rocky Point & Bayport": SubmarketMeta(
        name="Rocky Point & Bayport",
        borough="WESTSHORE_INTERNATIONAL",
        lat=27.965,
        lng=-82.545,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=37.0,
        shift_ratio=1.45,
        sla=58.0,
        description="Rocky Point peninsula resort and office campus with bayfront redevelopment and limited single-family turnover.",
        city_id="tampa",
    ),
    # =======================================================================
    # SOUTH_TAMPA_PALMA (3 Submarkets)
    # =======================================================================
    "Palma Ceia & Swann": SubmarketMeta(
        name="Palma Ceia & Swann",
        borough="SOUTH_TAMPA_PALMA",
        lat=27.910,
        lng=-82.490,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.86,
        capex=8500000.0,
        permit_vel=40.0,
        shift_ratio=1.52,
        sla=62.0,
        description="Established south Tampa neighborhood of masonry homes and palm-lined streets with steady renovation permitting.",
        city_id="tampa",
    ),
    "Gandy / MacDill Access": SubmarketMeta(
        name="Gandy / MacDill Access",
        borough="SOUTH_TAMPA_PALMA",
        lat=27.880,
        lng=-82.500,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=31.0,
        shift_ratio=1.38,
        sla=50.0,
        description="Gandy Boulevard corridor and MacDill AFB gateway with light industrial and workforce-housing permitting.",
        city_id="tampa",
    ),
    "Culbreath & Beach Park": SubmarketMeta(
        name="Culbreath & Beach Park",
        borough="SOUTH_TAMPA_PALMA",
        lat=27.905,
        lng=-82.510,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.83,
        capex=7200000.0,
        permit_vel=33.0,
        shift_ratio=1.43,
        sla=56.0,
        description="Bay-front estate pocket southwest of Palma Ceia with low-volume, high-value teardown-rebuild activity.",
        city_id="tampa",
    ),
    # =======================================================================
    # TAMPA_HEIGHTS_SEMINOLE (3 Submarkets)
    # =======================================================================
    "Tampa Heights & Armature Works": SubmarketMeta(
        name="Tampa Heights & Armature Works",
        borough="TAMPA_HEIGHTS_SEMINOLE",
        lat=27.995,
        lng=-82.410,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.85,
        capex=7800000.0,
        permit_vel=46.0,
        shift_ratio=1.53,
        sla=61.0,
        description="Riverfront revival north of downtown around Armature Works with food-hall and mid-rise residential infill.",
        city_id="tampa",
    ),
    "Ybor City & Historic District": SubmarketMeta(
        name="Ybor City & Historic District",
        borough="TAMPA_HEIGHTS_SEMINOLE",
        lat=27.970,
        lng=-82.425,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.84,
        capex=7400000.0,
        permit_vel=43.0,
        shift_ratio=1.50,
        sla=59.0,
        description="Historic cigar-worker district turned nightlife and mixed-use quarter with adaptive reuse and infill townhomes.",
        city_id="tampa",
    ),
    "Seminole Heights Bungalows": SubmarketMeta(
        name="Seminole Heights Bungalows",
        borough="TAMPA_HEIGHTS_SEMINOLE",
        lat=28.005,
        lng=-82.400,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.80,
        capex=5800000.0,
        permit_vel=38.0,
        shift_ratio=1.44,
        sla=54.0,
        description="Craftsman-bungalow streetcar suburb with renovation-led permits and Historic District overlay constraints.",
        city_id="tampa",
    ),
    # =======================================================================
    # CARROLLWOOD_NORTH (2 Submarkets)
    # =======================================================================
    "Carrollwood & Village Lake": SubmarketMeta(
        name="Carrollwood & Village Lake",
        borough="CARROLLWOOD_NORTH",
        lat=28.070,
        lng=-82.490,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=30.0,
        shift_ratio=1.32,
        sla=47.0,
        description="North Tampa suburban lake community with pool-home turnover and scattered teardown-rebuild on large lots.",
        city_id="tampa",
    ),
    "North Dale Mabry Corridor": SubmarketMeta(
        name="North Dale Mabry Corridor",
        borough="CARROLLWOOD_NORTH",
        lat=28.050,
        lng=-82.500,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.72,
        capex=4400000.0,
        permit_vel=27.0,
        shift_ratio=1.29,
        sla=44.0,
        description="Dale Mabry highway spine with commercial-strip redevelopment and garden-apartment infill north of the airport.",
        city_id="tampa",
    ),
    # =======================================================================
    # BRANDON_EAST (2 Submarkets)
    # =======================================================================
    "Brandon Town Center": SubmarketMeta(
        name="Brandon Town Center",
        borough="BRANDON_EAST",
        lat=27.940,
        lng=-82.300,
        zoom=13.0,
        pitch=38.0,
        base_lims=0.66,
        capex=3800000.0,
        permit_vel=34.0,
        shift_ratio=1.26,
        sla=41.0,
        description="East Hillsborough retail and apartment hub around Westfield Brandon with ongoing multifamily infill.",
        city_id="tampa",
    ),
    "FishHawk & Lithia (east edge)": SubmarketMeta(
        name="FishHawk & Lithia (east edge)",
        borough="BRANDON_EAST",
        lat=27.920,
        lng=-82.270,
        zoom=12.5,
        pitch=38.0,
        base_lims=0.58,
        capex=3000000.0,
        permit_vel=22.0,
        shift_ratio=1.18,
        sla=35.0,
        description="Master-planned exurban edge at the metro's eastern boundary, permitted through Hillsborough County rather than the City of Tampa.",
        city_id="tampa",
    ),
}


TAMPA_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CHANNEL": BoroughMeta(
        name="DOWNTOWN_CHANNEL",
        center_lat=27.944,
        center_lng=-82.444,
        zoom=13.5,
        bbox=TAMPA_DIVISION_BBOXES["DOWNTOWN_CHANNEL"],
        submarkets=[k for k, v in TAMPA_SUBMARKETS.items() if v.borough == "DOWNTOWN_CHANNEL"],
        city_id="tampa",
    ),
    "HYDE_PARK_BAYSHORE": BoroughMeta(
        name="HYDE_PARK_BAYSHORE",
        center_lat=27.925,
        center_lng=-82.465,
        zoom=13.5,
        bbox=TAMPA_DIVISION_BBOXES["HYDE_PARK_BAYSHORE"],
        submarkets=[k for k, v in TAMPA_SUBMARKETS.items() if v.borough == "HYDE_PARK_BAYSHORE"],
        city_id="tampa",
    ),
    "WESTSHORE_INTERNATIONAL": BoroughMeta(
        name="WESTSHORE_INTERNATIONAL",
        center_lat=27.957,
        center_lng=-82.535,
        zoom=13.0,
        bbox=TAMPA_DIVISION_BBOXES["WESTSHORE_INTERNATIONAL"],
        submarkets=[k for k, v in TAMPA_SUBMARKETS.items() if v.borough == "WESTSHORE_INTERNATIONAL"],
        city_id="tampa",
    ),
    "SOUTH_TAMPA_PALMA": BoroughMeta(
        name="SOUTH_TAMPA_PALMA",
        center_lat=27.895,
        center_lng=-82.487,
        zoom=13.0,
        bbox=TAMPA_DIVISION_BBOXES["SOUTH_TAMPA_PALMA"],
        submarkets=[k for k, v in TAMPA_SUBMARKETS.items() if v.borough == "SOUTH_TAMPA_PALMA"],
        city_id="tampa",
    ),
    "TAMPA_HEIGHTS_SEMINOLE": BoroughMeta(
        name="TAMPA_HEIGHTS_SEMINOLE",
        center_lat=27.990,
        center_lng=-82.415,
        zoom=13.0,
        bbox=TAMPA_DIVISION_BBOXES["TAMPA_HEIGHTS_SEMINOLE"],
        submarkets=[k for k, v in TAMPA_SUBMARKETS.items() if v.borough == "TAMPA_HEIGHTS_SEMINOLE"],
        city_id="tampa",
    ),
    "CARROLLWOOD_NORTH": BoroughMeta(
        name="CARROLLWOOD_NORTH",
        center_lat=28.060,
        center_lng=-82.485,
        zoom=12.5,
        bbox=TAMPA_DIVISION_BBOXES["CARROLLWOOD_NORTH"],
        submarkets=[k for k, v in TAMPA_SUBMARKETS.items() if v.borough == "CARROLLWOOD_NORTH"],
        city_id="tampa",
    ),
    "BRANDON_EAST": BoroughMeta(
        name="BRANDON_EAST",
        center_lat=27.935,
        center_lng=-82.290,
        zoom=12.5,
        bbox=TAMPA_DIVISION_BBOXES["BRANDON_EAST"],
        submarkets=[k for k, v in TAMPA_SUBMARKETS.items() if v.borough == "BRANDON_EAST"],
        city_id="tampa",
    ),
}

# Verbose aliases mirroring los_angeles.py / austin.py *_SUBMARKETS pairs.
GREATER_TAMPA_METRO_BBOX = TAMPA_METRO_BBOX
TPA_DIVISION_BBOXES = TAMPA_DIVISION_BBOXES
TPA_SUBMARKETS = TAMPA_SUBMARKETS
TPA_DIVISIONS = TAMPA_DIVISIONS


# ---------------------------------------------------------------------------
# Feed registration (leaf-local plain data; the spine copies this into REGISTRY).
# ---------------------------------------------------------------------------
# The field_map data lives in the leaf module field_maps_tampa.py (imported
# here) so the leaf is self-contained and testable without the spine registry.


TAMPA_PERMITS_ENDPOINT = "https://arcgis.tampagov.net/arcgis/rest/services/Planning/PermitsAll/FeatureServer/0"
TAMPA_SLA_ENDPOINT = "https://arcgis.tampagov.net/arcgis/rest/services/Planning/AlcoholBeverage/FeatureServer/0"

TAMPA_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": TAMPA_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "LASTUPDATE",
        "id_keys": ["RECORD_ID", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "LASTUPDATE DESC",
            "scope": "Tampa/Hillsborough full permits (edit-stamp watermark)",
            "field_map": FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": TAMPA_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "HISTORY_ACT_DT",
        "id_keys": ["ORD_PERMIT", "APP_NUM", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "scope": "Tampa alcohol-beverage sale locations and action history (partial SLA)",
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_tampa_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Tampa feed, or raises ``KeyError`` naming
    the city and available feeds when the feed is absent.
    """
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in TAMPA_FEED_SPECS:
        available = ", ".join(sorted(TAMPA_FEED_SPECS))
        raise KeyError(
            f"'{TAMPA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = TAMPA_FEED_SPECS[feed_name]
    from src.config import settings

    # Promote the former free-form extra keys (minus the dead `scope`) to typed
    # DatasetSpec fields.
    extra_kwargs = {
        k: v for k, v in payload.get("extra", {}).items() if k != "scope"
    }

    return DatasetSpec(
        endpoint=payload["endpoint"],
        platform=payload["platform"],
        watermark_col=payload["watermark_col"],
        id_keys=payload["id_keys"],
        topic=getattr(settings, payload["topic_key"]),
        interval_seconds=payload["interval_seconds"],
        producer_key=payload["producer_key"],
        **extra_kwargs,
    )


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=TAMPA_METRO_BBOX,
    division_bboxes=TAMPA_DIVISION_BBOXES,
    submarkets=TAMPA_SUBMARKETS,
    divisions=TAMPA_DIVISIONS,
    contains=is_in_tampa_metro,
)
