"""Orlando Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Orlando, FL
(Orange County seat) and its inner corridors (College Park, Baldwin Park,
International Drive, Lake Nona).

Orlando registers as a PARTIAL metro like Austin/LA: two SLA-typed Socrata
feeds, no PERMITS / 311 / DEEDS in this ticket.

* SLA (primary) — Business Tax Receipts ``7388-4re5``. Live window is
  address-only (``business_address``); the archive ``geocoded_column`` is not
  populated on new rows (0/250 of 60d-received, probed 2026-08-27). ADR 0004
  geocodes at parse time. ``gpsx``/``gpsy`` are Florida State Plane, not WGS84.
* SLA (companion) — Short Term Rental Licenses ``ssrj-rbua``. Address-only
  street lines with no native coordinates. Registers as SLA (existing type);
  do not invent a FeedType. The STR occupancy / investor-buyout reading is a
  later signal-family decision, not this leaf.

Both endpoints were live-verified on 2026-08-27. Permits ``ryhf-m453`` is
also live+geocoded and is deliberately **out of ticket scope**.
"""

from typing import Dict

from src.producers.field_maps_orlando import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
    STR_SLA_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

ORLANDO_CITY_ID: str = "orlando"
ORLANDO_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Orlando plus inner Orange County corridors that appear in the BTR
# and STR samples (Lake Nona South, Metro West, Baldwin Park, I-Drive).
ORLANDO_METRO_BBOX: Dict[str, float] = {
    "min_lat": 28.34,
    "max_lat": 28.64,
    "min_lng": -81.52,
    "max_lng": -81.22,
}

ORLANDO_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_LAKE_EOLA": {
        "min_lat": 28.52,
        "max_lat": 28.56,
        "min_lng": -81.40,
        "max_lng": -81.35,
    },
    "NORTH_COLLEGE_PARK": {
        "min_lat": 28.555,
        "max_lat": 28.62,
        "min_lng": -81.42,
        "max_lng": -81.36,
    },
    "EAST_BALDWIN_PARK": {
        "min_lat": 28.54,
        "max_lat": 28.60,
        "min_lng": -81.36,
        "max_lng": -81.28,
    },
    "SOUTH_ORANGE_CONWAY": {
        "min_lat": 28.48,
        "max_lat": 28.535,
        "min_lng": -81.40,
        "max_lng": -81.30,
    },
    "WEST_IDRIVE_METROWEST": {
        "min_lat": 28.43,
        "max_lat": 28.54,
        "min_lng": -81.52,
        "max_lng": -81.40,
    },
    "SOUTHEAST_LAKE_NONA": {
        "min_lat": 28.34,
        "max_lat": 28.48,
        "min_lng": -81.36,
        "max_lng": -81.22,
    },
}


def is_in_orlando_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Orlando Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        ORLANDO_METRO_BBOX["min_lat"] <= lat <= ORLANDO_METRO_BBOX["max_lat"]
        and ORLANDO_METRO_BBOX["min_lng"] <= lng <= ORLANDO_METRO_BBOX["max_lng"]
    )


is_in_greater_orlando_metro = is_in_orlando_metro


ORLANDO_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_LAKE_EOLA (3)
    # =======================================================================
    "Downtown Orlando": SubmarketMeta(
        name="Downtown Orlando",
        borough="DOWNTOWN_LAKE_EOLA",
        lat=28.5383,
        lng=-81.3792,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.90,
        capex=11000000.0,
        permit_vel=48.0,
        shift_ratio=1.60,
        sla=70.0,
        description="Church Street and Lake Eola civic core with office-to-residential conversions and the densest business-tax pipeline.",
        city_id="orlando",
    ),
    "Thornton Park": SubmarketMeta(
        name="Thornton Park",
        borough="DOWNTOWN_LAKE_EOLA",
        lat=28.543,
        lng=-81.368,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=8200000.0,
        permit_vel=36.0,
        shift_ratio=1.48,
        sla=64.0,
        description="Brick-street bungalow grid east of Lake Eola with renovation-led licensing and neighborhood retail.",
        city_id="orlando",
    ),
    "SoDo": SubmarketMeta(
        name="SoDo",
        borough="DOWNTOWN_LAKE_EOLA",
        lat=28.530,
        lng=-81.376,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=34.0,
        shift_ratio=1.45,
        sla=61.0,
        description="South of Downtown warehouse and creative-office conversions along Orange Avenue.",
        city_id="orlando",
    ),
    # =======================================================================
    # NORTH_COLLEGE_PARK (3)
    # =======================================================================
    "College Park": SubmarketMeta(
        name="College Park",
        borough="NORTH_COLLEGE_PARK",
        lat=28.577,
        lng=-81.393,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.85,
        capex=7200000.0,
        permit_vel=33.0,
        shift_ratio=1.46,
        sla=60.0,
        description="North-of-downtown streetcar suburb with Edgewater Drive retail and high STR turnover.",
        city_id="orlando",
    ),
    "Ivanhoe Village": SubmarketMeta(
        name="Ivanhoe Village",
        borough="NORTH_COLLEGE_PARK",
        lat=28.568,
        lng=-81.377,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=6800000.0,
        permit_vel=31.0,
        shift_ratio=1.43,
        sla=58.0,
        description="Mills Avenue corridor between downtown and College Park with adaptive-reuse commercial.",
        city_id="orlando",
    ),
    "Princeton / Silver Star": SubmarketMeta(
        name="Princeton / Silver Star",
        borough="NORTH_COLLEGE_PARK",
        lat=28.585,
        lng=-81.405,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=26.0,
        shift_ratio=1.32,
        sla=50.0,
        description="Industrial-adjacent north side with contractor and service-license density along Silver Star.",
        city_id="orlando",
    ),
    # =======================================================================
    # EAST_BALDWIN_PARK (3)
    # =======================================================================
    "Baldwin Park": SubmarketMeta(
        name="Baldwin Park",
        borough="EAST_BALDWIN_PARK",
        lat=28.570,
        lng=-81.325,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.88,
        capex=9400000.0,
        permit_vel=38.0,
        shift_ratio=1.52,
        sla=66.0,
        description="Master-planned New Urbanist village on the former Navy base with mixed-use and professional offices.",
        city_id="orlando",
    ),
    "Milk District": SubmarketMeta(
        name="Milk District",
        borough="EAST_BALDWIN_PARK",
        lat=28.548,
        lng=-81.351,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.82,
        capex=6100000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=57.0,
        description="Colonialtown east-of-downtown grid with brewery/retail conversions and short-term rental pressure.",
        city_id="orlando",
    ),
    "Audubon Park": SubmarketMeta(
        name="Audubon Park",
        borough="EAST_BALDWIN_PARK",
        lat=28.569,
        lng=-81.351,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.80,
        capex=5600000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=54.0,
        description="Garden-district bungalows along Corrine Drive with independent retail and renovation licenses.",
        city_id="orlando",
    ),
    # =======================================================================
    # SOUTH_ORANGE_CONWAY (3)
    # =======================================================================
    "South Orange": SubmarketMeta(
        name="South Orange",
        borough="SOUTH_ORANGE_CONWAY",
        lat=28.522,
        lng=-81.377,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.81,
        capex=7000000.0,
        permit_vel=30.0,
        shift_ratio=1.41,
        sla=56.0,
        description="Orlando Health medical corridor on South Orange Avenue with professional and clinical licensing.",
        city_id="orlando",
    ),
    "Conway": SubmarketMeta(
        name="Conway",
        borough="SOUTH_ORANGE_CONWAY",
        lat=28.498,
        lng=-81.331,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=24.0,
        shift_ratio=1.30,
        sla=46.0,
        description="Lakeside residential south of downtown with small-lot infill and neighborhood services.",
        city_id="orlando",
    ),
    "Airport North": SubmarketMeta(
        name="Airport North",
        borough="SOUTH_ORANGE_CONWAY",
        lat=28.490,
        lng=-81.320,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.68,
        capex=3900000.0,
        permit_vel=22.0,
        shift_ratio=1.26,
        sla=42.0,
        description="MCO-adjacent logistics and hospitality licensing north of the airfield.",
        city_id="orlando",
    ),
    # =======================================================================
    # WEST_IDRIVE_METROWEST (3)
    # =======================================================================
    "International Drive / Florida Center": SubmarketMeta(
        name="International Drive / Florida Center",
        borough="WEST_IDRIVE_METROWEST",
        lat=28.460,
        lng=-81.467,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.87,
        capex=12500000.0,
        permit_vel=52.0,
        shift_ratio=1.58,
        sla=68.0,
        description="Tourist-corridor hospitality, retail, and body-art licensing along International Drive.",
        city_id="orlando",
    ),
    "Metro West": SubmarketMeta(
        name="Metro West",
        borough="WEST_IDRIVE_METROWEST",
        lat=28.513,
        lng=-81.485,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=27.0,
        shift_ratio=1.34,
        sla=50.0,
        description="West-side planned community and office park with service and contractor licenses.",
        city_id="orlando",
    ),
    "Kirkman / Universal Edge": SubmarketMeta(
        name="Kirkman / Universal Edge",
        borough="WEST_IDRIVE_METROWEST",
        lat=28.490,
        lng=-81.455,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.79,
        capex=6300000.0,
        permit_vel=29.0,
        shift_ratio=1.38,
        sla=53.0,
        description="Kirkman Road hospitality and contractor spine at the Universal resort edge.",
        city_id="orlando",
    ),
    # =======================================================================
    # SOUTHEAST_LAKE_NONA (3)
    # =======================================================================
    "Lake Nona South / Medical City": SubmarketMeta(
        name="Lake Nona South / Medical City",
        borough="SOUTHEAST_LAKE_NONA",
        lat=28.368,
        lng=-81.275,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.89,
        capex=13000000.0,
        permit_vel=44.0,
        shift_ratio=1.56,
        sla=67.0,
        description="Nemours / UCF Medical City campus with physician and professional-firm licensing.",
        city_id="orlando",
    ),
    "Lake Nona Central": SubmarketMeta(
        name="Lake Nona Central",
        borough="SOUTHEAST_LAKE_NONA",
        lat=28.425,
        lng=-81.255,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.84,
        capex=8800000.0,
        permit_vel=36.0,
        shift_ratio=1.49,
        sla=62.0,
        description="Town-center mixed-use and residential buildout east of the airport.",
        city_id="orlando",
    ),
    "Airport South": SubmarketMeta(
        name="Airport South",
        borough="SOUTHEAST_LAKE_NONA",
        lat=28.431,
        lng=-81.308,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.70,
        capex=4100000.0,
        permit_vel=23.0,
        shift_ratio=1.28,
        sla=44.0,
        description="Airside industrial and cargo licensing south of MCO.",
        city_id="orlando",
    ),
}


ORLANDO_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_LAKE_EOLA": BoroughMeta(
        name="DOWNTOWN_LAKE_EOLA",
        center_lat=28.538,
        center_lng=-81.374,
        zoom=13.5,
        bbox=ORLANDO_DIVISION_BBOXES["DOWNTOWN_LAKE_EOLA"],
        submarkets=[k for k, v in ORLANDO_SUBMARKETS.items() if v.borough == "DOWNTOWN_LAKE_EOLA"],
        city_id="orlando",
    ),
    "NORTH_COLLEGE_PARK": BoroughMeta(
        name="NORTH_COLLEGE_PARK",
        center_lat=28.577,
        center_lng=-81.392,
        zoom=13.0,
        bbox=ORLANDO_DIVISION_BBOXES["NORTH_COLLEGE_PARK"],
        submarkets=[k for k, v in ORLANDO_SUBMARKETS.items() if v.borough == "NORTH_COLLEGE_PARK"],
        city_id="orlando",
    ),
    "EAST_BALDWIN_PARK": BoroughMeta(
        name="EAST_BALDWIN_PARK",
        center_lat=28.562,
        center_lng=-81.342,
        zoom=13.0,
        bbox=ORLANDO_DIVISION_BBOXES["EAST_BALDWIN_PARK"],
        submarkets=[k for k, v in ORLANDO_SUBMARKETS.items() if v.borough == "EAST_BALDWIN_PARK"],
        city_id="orlando",
    ),
    "SOUTH_ORANGE_CONWAY": BoroughMeta(
        name="SOUTH_ORANGE_CONWAY",
        center_lat=28.503,
        center_lng=-81.343,
        zoom=12.5,
        bbox=ORLANDO_DIVISION_BBOXES["SOUTH_ORANGE_CONWAY"],
        submarkets=[k for k, v in ORLANDO_SUBMARKETS.items() if v.borough == "SOUTH_ORANGE_CONWAY"],
        city_id="orlando",
    ),
    "WEST_IDRIVE_METROWEST": BoroughMeta(
        name="WEST_IDRIVE_METROWEST",
        center_lat=28.488,
        center_lng=-81.469,
        zoom=12.5,
        bbox=ORLANDO_DIVISION_BBOXES["WEST_IDRIVE_METROWEST"],
        submarkets=[k for k, v in ORLANDO_SUBMARKETS.items() if v.borough == "WEST_IDRIVE_METROWEST"],
        city_id="orlando",
    ),
    "SOUTHEAST_LAKE_NONA": BoroughMeta(
        name="SOUTHEAST_LAKE_NONA",
        center_lat=28.408,
        center_lng=-81.279,
        zoom=12.0,
        bbox=ORLANDO_DIVISION_BBOXES["SOUTHEAST_LAKE_NONA"],
        submarkets=[k for k, v in ORLANDO_SUBMARKETS.items() if v.borough == "SOUTHEAST_LAKE_NONA"],
        city_id="orlando",
    ),
}

GREATER_ORLANDO_METRO_BBOX = ORLANDO_METRO_BBOX
MCO_DIVISION_BBOXES = ORLANDO_DIVISION_BBOXES
MCO_SUBMARKETS = ORLANDO_SUBMARKETS
MCO_DIVISIONS = ORLANDO_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27 against data.cityoforlando.net.
# ---------------------------------------------------------------------------
ORLANDO_BTR_ENDPOINT = "https://data.cityoforlando.net/resource/7388-4re5.json"
ORLANDO_STR_ENDPOINT = "https://data.cityoforlando.net/resource/ssrj-rbua.json"

ORLANDO_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "sla": {
        "endpoint": ORLANDO_BTR_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "received_date",
        "id_keys": ["case_number"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 1,
            "order_by": "received_date DESC",
            "needs_geocode": True,
            "geocode_context": ORLANDO_GEOCODE_CONTEXT,
            "companion_endpoints": {"str_licenses": ORLANDO_STR_ENDPOINT},
            "scope": "Orlando Business Tax Receipts (address-only live window; ADR-0004)",
            "field_map": SLA_FIELD_MAP,
        },
    },
}

# Companion STR payload for the spine to copy into companion_endpoints / a
# follow-on ingest job. Same producer_key as SLA; not a new FeedType.
ORLANDO_STR_SLA_SPEC: Dict[str, object] = {
    "endpoint": ORLANDO_STR_ENDPOINT,
    "platform": "socrata",
    "watermark_col": "last_action_date",
    "id_keys": ["license_number"],
    "topic_key": "topic_sla",
    "interval_seconds": 600.0,
    "producer_key": "sla",
    "extra": {
        "expected_cadence_days": 7,
        "order_by": "last_action_date DESC",
        "needs_geocode": True,
        "geocode_context": ORLANDO_GEOCODE_CONTEXT,
        "scope": "Orlando Short Term Rental Licenses (address-only; SLA companion)",
        "field_map": STR_SLA_FIELD_MAP,
    },
}


def get_orlando_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Orlando feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in ORLANDO_FEED_SPECS:
        available = ", ".join(sorted(ORLANDO_FEED_SPECS))
        raise KeyError(
            f"'{ORLANDO_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = ORLANDO_FEED_SPECS[feed_name]
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
    metro_bbox=ORLANDO_METRO_BBOX,
    division_bboxes=ORLANDO_DIVISION_BBOXES,
    submarkets=ORLANDO_SUBMARKETS,
    divisions=ORLANDO_DIVISIONS,
    contains=is_in_orlando_metro,
)
