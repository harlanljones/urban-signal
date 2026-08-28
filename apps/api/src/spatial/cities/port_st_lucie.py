"""Port St. Lucie Metro Submarket Registry for Urban Signal (US-289).

Leaf-local geometry and camera metadata, plus feed hints for Port St. Lucie, FL.
The spine mirrors geometry from this leaf into REGISTRY (US-177) and wires
datasets from the handwritten registry.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Canonical, stable city id string for Port St. Lucie.
PSL_CITY_ID: str = "port_st_lucie"

# Port St. Lucie metro bounding box — permissive to contain all divisions and samples.
PORT_ST_LUCIE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 27.15,
    "max_lat": 27.40,
    "min_lng": -80.50,
    "max_lng": -80.20,
}


def is_in_port_st_lucie_metro(lat: float, lng: float) -> bool:
    if lat is None or lng is None:
        return False
    b = PORT_ST_LUCIE_METRO_BBOX
    return b["min_lat"] <= lat <= b["max_lat"] and b["min_lng"] <= lng <= b["max_lng"]


# Three coarse divisions across the city
PORT_ST_LUCIE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "TRADITION_WEST": {"min_lat": 27.23, "max_lat": 27.34, "min_lng": -80.48, "max_lng": -80.38},
    "CENTRAL": {"min_lat": 27.22, "max_lat": 27.34, "min_lng": -80.38, "max_lng": -80.30},
    "EAST_RIVER": {"min_lat": 27.23, "max_lat": 27.36, "min_lng": -80.30, "max_lng": -80.22},
}


# Submarkets with camera presets and synthetic base signal metadata
PORT_ST_LUCIE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # TRADITION_WEST
    "Tradition & Western PSL": SubmarketMeta(
        name="Tradition & Western PSL",
        borough="TRADITION_WEST",
        lat=27.275,
        lng=-80.430,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.35,
        sla=48.0,
        description="Master-planned Tradition area and western growth corridor along I-95.",
        city_id=PSL_CITY_ID,
    ),
    "St. Lucie West": SubmarketMeta(
        name="St. Lucie West",
        borough="TRADITION_WEST",
        lat=27.320,
        lng=-80.405,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.80,
        capex=5600000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=50.0,
        description="St. Lucie West town center, retail and multifamily infill.",
        city_id=PSL_CITY_ID,
    ),
    # CENTRAL
    "Crosstown Parkway Corridor": SubmarketMeta(
        name="Crosstown Parkway Corridor",
        borough="CENTRAL",
        lat=27.285,
        lng=-80.363,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=4800000.0,
        permit_vel=26.0,
        shift_ratio=1.32,
        sla=46.0,
        description="East–west spine through central PSL with steady residential permitting.",
        city_id=PSL_CITY_ID,
    ),
    "PSL Blvd Central": SubmarketMeta(
        name="PSL Blvd Central",
        borough="CENTRAL",
        lat=27.271,
        lng=-80.327,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=4400000.0,
        permit_vel=24.0,
        shift_ratio=1.28,
        sla=44.0,
        description="Port St. Lucie Boulevard central corridor small-lot teardowns and renovations.",
        city_id=PSL_CITY_ID,
    ),
    # EAST_RIVER
    "US-1 & East PSL": SubmarketMeta(
        name="US-1 & East PSL",
        borough="EAST_RIVER",
        lat=27.300,
        lng=-80.285,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=22.0,
        shift_ratio=1.24,
        sla=42.0,
        description="US-1 commercial corridor and east-side infill near the North Fork St. Lucie River.",
        city_id=PSL_CITY_ID,
    ),
    "Jensen Beach South Edge": SubmarketMeta(
        name="Jensen Beach South Edge",
        borough="EAST_RIVER",
        lat=27.240,
        lng=-80.267,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.70,
        capex=3800000.0,
        permit_vel=20.0,
        shift_ratio=1.20,
        sla=40.0,
        description="Northern/eastern edge near Jensen Beach, river-adjacent residential renewal.",
        city_id=PSL_CITY_ID,
    ),
}


PORT_ST_LUCIE_DIVISIONS: Dict[str, BoroughMeta] = {
    "TRADITION_WEST": BoroughMeta(
        name="TRADITION_WEST",
        center_lat=27.300,
        center_lng=-80.430,
        zoom=12.8,
        bbox=PORT_ST_LUCIE_DIVISION_BBOXES["TRADITION_WEST"],
        submarkets=[k for k, v in PORT_ST_LUCIE_SUBMARKETS.items() if v.borough == "TRADITION_WEST"],
        city_id=PSL_CITY_ID,
    ),
    "CENTRAL": BoroughMeta(
        name="CENTRAL",
        center_lat=27.285,
        center_lng=-80.345,
        zoom=12.8,
        bbox=PORT_ST_LUCIE_DIVISION_BBOXES["CENTRAL"],
        submarkets=[k for k, v in PORT_ST_LUCIE_SUBMARKETS.items() if v.borough == "CENTRAL"],
        city_id=PSL_CITY_ID,
    ),
    "EAST_RIVER": BoroughMeta(
        name="EAST_RIVER",
        center_lat=27.300,
        center_lng=-80.270,
        zoom=12.8,
        bbox=PORT_ST_LUCIE_DIVISION_BBOXES["EAST_RIVER"],
        submarkets=[k for k, v in PORT_ST_LUCIE_SUBMARKETS.items() if v.borough == "EAST_RIVER"],
        city_id=PSL_CITY_ID,
    ),
}

# Verbose aliases for export symmetry
PSL_METRO_BBOX = PORT_ST_LUCIE_METRO_BBOX
PORT_ST_LUCIE_SUBMARKETS_MAP = PORT_ST_LUCIE_SUBMARKETS
PORT_ST_LUCIE_DIVISION_BBOXES_MAP = PORT_ST_LUCIE_DIVISION_BBOXES
PORT_ST_LUCIE_DIVISIONS_MAP = PORT_ST_LUCIE_DIVISIONS

# Feed registration (leaf-local plain data; the spine copies this into REGISTRY).
from src.producers.field_maps_port_st_lucie import FIELD_MAP as PSL_FIELD_MAP  # noqa: E402

PSL_PERMITS_ENDPOINT = (
    "https://services1.arcgis.com/YdUP5V6WwzeG8T8r/arcgis/rest/services/Permits/FeatureServer/0"
)

PSL_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": PSL_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "DateIssued",
        "id_keys": ["PermitID", "AddressID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 7,
            "oid_field": "PermitID",
            "max_record_count": 2000,
            "order_by": "DateIssued DESC",
            "field_map": PSL_FIELD_MAP,
        },
    },
}


def get_port_st_lucie_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset`` for PSL."""
    from src.spatial.city_registry import DatasetSpec
    from src.config import settings

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in PSL_FEED_SPECS:
        available = ", ".join(sorted(PSL_FEED_SPECS))
        raise KeyError(f"'{PSL_CITY_ID}' has no '{feed_name}' feed; available: {available}")
    payload = PSL_FEED_SPECS[feed_name]
    extra_kwargs = {k: v for k, v in payload.get("extra", {}).items() if k != "scope"}
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
    metro_bbox=PORT_ST_LUCIE_METRO_BBOX,
    division_bboxes=PORT_ST_LUCIE_DIVISION_BBOXES,
    submarkets=PORT_ST_LUCIE_SUBMARKETS,
    divisions=PORT_ST_LUCIE_DIVISIONS,
    contains=is_in_port_st_lucie_metro,
)

