"""Lakeland, FL Metro Submarket Registry and Spatial Layer for Urban Signal.

Leaf-only module (US-286). Declares:
- metro/division bounding boxes
- submarket metadata
- a verified ArcGIS permits feed spec (iMS Public CED)

SLA falls back to statewide SNAP (declared in the spine via snap_sla_spec('FL')).
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Canonical city identifier. Keep in sync with the module filename.
LAKELAND_CITY_ID: str = "lakeland"

# Lakeland city extent — permissive enough to contain all divisions/submarkets.
# Downtown Lakeland approx: 28.0395, -81.9498
LAKELAND_METRO_BBOX: Dict[str, float] = {
    "min_lat": 27.95,
    "max_lat": 28.13,
    "min_lng": -82.10,
    "max_lng": -81.80,
}

# Single-division layout to start (high fit, can expand later if needed).
LAKELAND_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "LAKELAND_CORE": {"min_lat": 28.00, "max_lat": 28.08, "min_lng": -82.01, "max_lng": -81.90},
}


def is_in_lakeland_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Lakeland metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        LAKELAND_METRO_BBOX["min_lat"] <= lat <= LAKELAND_METRO_BBOX["max_lat"]
        and LAKELAND_METRO_BBOX["min_lng"] <= lng <= LAKELAND_METRO_BBOX["max_lng"]
    )


# Minimal submarket slate (3) — centers verified against the bbox above.
LAKELAND_SUBMARKETS: Dict[str, SubmarketMeta] = {
    "Downtown Lakeland": SubmarketMeta(
        name="Downtown Lakeland",
        borough="LAKELAND_CORE",
        lat=28.041,
        lng=-81.949,
        zoom=15.0,
        pitch=48.0,
        base_lims=0.70,
        capex=4000000.0,
        permit_vel=20.0,
        shift_ratio=1.20,
        sla=45.0,
        description="Historic downtown core around Munn Park and Lake Mirror with steady renovation permits.",
        city_id="lakeland",
    ),
    "South Lakeland Strips": SubmarketMeta(
        name="South Lakeland Strips",
        borough="LAKELAND_CORE",
        lat=28.015,
        lng=-81.955,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.62,
        capex=3200000.0,
        permit_vel=16.0,
        shift_ratio=1.12,
        sla=40.0,
        description="Commercial corridors south of downtown with retail renovation and small infill.",
        city_id="lakeland",
    ),
    "Lakeland Highlands": SubmarketMeta(
        name="Lakeland Highlands",
        borough="LAKELAND_CORE",
        lat=28.06,
        lng=-81.93,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.58,
        capex=2800000.0,
        permit_vel=14.0,
        shift_ratio=1.08,
        sla=38.0,
        description="Residential pockets north/east with scattered teardown-rebuild and additions.",
        city_id="lakeland",
    ),
}

LAKELAND_DIVISIONS: Dict[str, BoroughMeta] = {
    "LAKELAND_CORE": BoroughMeta(
        name="LAKELAND_CORE",
        center_lat=28.041,
        center_lng=-81.949,
        zoom=13.0,
        bbox=LAKELAND_DIVISION_BBOXES["LAKELAND_CORE"],
        submarkets=[k for k, v in LAKELAND_SUBMARKETS.items() if v.borough == "LAKELAND_CORE"],
        city_id="lakeland",
    ),
}

# Verbose aliases for symmetry with other modules
LAKELAND_METRO = LAKELAND_METRO_BBOX
LAKELAND_BBOXES = LAKELAND_DIVISION_BBOXES
LAKELAND_MARKETS = LAKELAND_SUBMARKETS
LAKELAND_BOROUGHS = LAKELAND_DIVISIONS


# ---------------------------------------------------------------------------
# Feed registration (leaf-local plain data; the spine copies this into REGISTRY).
# ---------------------------------------------------------------------------
# Endpoint declared in Settings as arcgis_lakeland_permits_url; the leaf stays
# self-contained/testable with its own spec mirror like other cities.

LAKELAND_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        # Keep literal in leaf for unit parity; spine will reference settings field.
        "endpoint": "https://gismims.lakelandgov.net/portal/rest/services/Public_CED/Lakeland_CED_Permits/MapServer/0",
        "platform": "arcgis",
        # Conservatively use an edit/issue style watermark — adjust when field-audited
        "watermark_col": "ISSUEDATE",
        "id_keys": ["PERMIT_NO", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 7,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            # No city-specific field map yet — defaults cover common shapes
            "field_map": {},
        },
    },
}


def get_lakeland_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset`` for Lakeland."""
    from src.spatial.city_registry import DatasetSpec
    from src.config import settings

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in LAKELAND_FEED_SPECS:
        available = ", ".join(sorted(LAKELAND_FEED_SPECS))
        raise KeyError(f"'{LAKELAND_CITY_ID}' has no '{feed_name}' feed; available: {available}")
    payload = LAKELAND_FEED_SPECS[feed_name]

    extra_kwargs = {k: v for k, v in payload.get("extra", {}).items() if k != "scope"}
    # Promote to typed DatasetSpec
    return DatasetSpec(
        endpoint=getattr(settings, "arcgis_lakeland_permits_url"),
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
    metro_bbox=LAKELAND_METRO_BBOX,
    division_bboxes=LAKELAND_DIVISION_BBOXES,
    submarkets=LAKELAND_SUBMARKETS,
    divisions=LAKELAND_DIVISIONS,
    contains=is_in_lakeland_metro,
)

