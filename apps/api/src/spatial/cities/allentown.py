DEEDS_FIELD_MAP = {
    "doc_id": ["XINSTNUM", "WARDACCTNO"],
    "bbl": ["PIN"],
    "document_amount": ["SPRICE"],
    "address_street": ["PROPERTYADDR"],
    "incident_address": ["PROPERTYADDR"],
    "zipcode": ["ZIP"],
}

FIELD_MAP = {
    "deeds": DEEDS_FIELD_MAP,
}

"""Allentown Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the Allentown–Bethlehem–
Easton (Lehigh Valley) metro, PA. Allentown is the Lehigh County seat on the
Lehigh River; Bethlehem (Northampton County) and Easton (Northampton County
seat) anchor the eastern end of the valley.

Feeds (probed 2026-09-30):

* DEEDS — the city's "Tax Parcels Assessed" layer on ArcGIS Online (service
  ``Tax_Parcels_Assessed_2022``, overwritten in place about monthly). Each
  parcel carries its last sale as a year (``SYEAR``) and a month (``SMON``)
  with no day, so ``compose_deed_date`` below stamps the first of the month.
  It is read as a snapshot, newest sale first, selecting only non-owner
  columns; an ``SPRICE`` of 1 is a nominal transfer. Parcel polygons supply
  coordinates. The ``gis.allentownpa.gov`` host registered until 2026-09-30
  does not exist. Lehigh County's ``ATestParcel`` layer carries the same
  fields county-wide, about a month staler, if the city layer disappears.
* PERMITS / SLA / 311 — not registered.
"""


from typing import Any

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

ALLENTOWN_CITY_ID: str = "allentown"

# Allentown metro bbox (Lehigh Valley core: Allentown, Bethlehem, Easton).
ALLENTOWN_METRO_BBOX: dict[str, float] = {
    "min_lat": 40.45,
    "max_lat": 40.75,
    "min_lng": -75.75,
    "max_lng": -75.15,
}

# Registration-contract center: downtown Allentown (Hamilton St CBD).
ALLENTOWN_CENTER: dict[str, float] = {"lat": 40.6084, "lng": -75.4902}

# 5 Allentown Division Bounding Boxes (strictly nested inside the metro bbox)
ALLENTOWN_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_ALLENTOWN": {"min_lat": 40.585, "max_lat": 40.625, "min_lng": -75.520, "max_lng": -75.470},
    "BETHLEHEM":          {"min_lat": 40.590, "max_lat": 40.625, "min_lng": -75.420, "max_lng": -75.350},
    "EASTON":             {"min_lat": 40.660, "max_lat": 40.705, "min_lng": -75.260, "max_lng": -75.210},
    "SOUTH_SIDE":         {"min_lat": 40.540, "max_lat": 40.585, "min_lng": -75.530, "max_lng": -75.460},
    "WEST_END":           {"min_lat": 40.575, "max_lat": 40.620, "min_lng": -75.570, "max_lng": -75.510},
}


def is_in_allentown_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Allentown metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        ALLENTOWN_METRO_BBOX["min_lat"] <= lat <= ALLENTOWN_METRO_BBOX["max_lat"]
        and ALLENTOWN_METRO_BBOX["min_lng"] <= lng <= ALLENTOWN_METRO_BBOX["max_lng"]
    )


def is_in_allentown(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_allentown_metro`."""
    return is_in_allentown_metro(lat, lng)


# ---------------------------------------------------------------------------
# Allentown Submarket Registry (7 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

ALLENTOWN_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_ALLENTOWN (2 Submarkets)
    # =======================================================================
    "Center City Allentown": SubmarketMeta(
        name="Center City Allentown",
        borough="DOWNTOWN_ALLENTOWN",
        lat=40.6005,
        lng=-75.4900,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.84,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=54.0,
        description="The Hamilton Street CBD with office-to-residential conversions, the PPL Center anchor, and the densest mixed-use pipeline in the Lehigh Valley.",
        city_id="allentown",
    ),
    "West End Theatre District": SubmarketMeta(
        name="West End Theatre District",
        borough="DOWNTOWN_ALLENTOWN",
        lat=40.6100,
        lng=-75.5000,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.80,
        capex=4000000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=46.0,
        description="The West End grid around the Nineteenth Street theatre row with pre-war housing stock and steady renovation trades.",
        city_id="allentown",
    ),
    # =======================================================================
    # BETHLEHEM (2 Submarkets)
    # =======================================================================
    "South Bethlehem": SubmarketMeta(
        name="South Bethlehem",
        borough="BETHLEHEM",
        lat=40.6000,
        lng=-75.3850,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.82,
        capex=4500000.0,
        permit_vel=27.0,
        shift_ratio=1.38,
        sla=50.0,
        description="The Lehigh University-adjacent South Side with student-housing conversions, restaurant-row licensing, and industrial-reuse projects.",
        city_id="allentown",
    ),
    "Downtown Bethlehem": SubmarketMeta(
        name="Downtown Bethlehem",
        borough="BETHLEHEM",
        lat=40.6210,
        lng=-75.3790,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.81,
        capex=4300000.0,
        permit_vel=26.0,
        shift_ratio=1.36,
        sla=48.0,
        description="The historic Moravian district and Banana Factory arts corridor with boutique retail and hospitality licensing.",
        city_id="allentown",
    ),
    # =======================================================================
    # EASTON (2 Submarkets)
    # =======================================================================
    "Downtown Easton": SubmarketMeta(
        name="Downtown Easton",
        borough="EASTON",
        lat=40.6900,
        lng=-75.2110,
        zoom=15.0,
        pitch=38.0,
        base_lims=0.74,
        capex=3300000.0,
        permit_vel=21.0,
        shift_ratio=1.26,
        sla=42.0,
        description="The confluence of the Lehigh and Delaware rivers with the Crayola-adjacent retail core and the redeveloped silk-mill district.",
        city_id="allentown",
    ),
    "College Hill": SubmarketMeta(
        name="College Hill",
        borough="EASTON",
        lat=40.7000,
        lng=-75.2400,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.70,
        capex=3000000.0,
        permit_vel=19.0,
        shift_ratio=1.22,
        sla=38.0,
        description="The Lafayette College hill neighborhood with solid Victorian stock and investor renovation flow.",
        city_id="allentown",
    ),
    # =======================================================================
    # SOUTH_SIDE (1 Submarket)
    # =======================================================================
    "South Allentown": SubmarketMeta(
        name="South Allentown",
        borough="SOUTH_SIDE",
        lat=40.5700,
        lng=-75.4900,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2900000.0,
        permit_vel=18.0,
        shift_ratio=1.20,
        sla=36.0,
        description="The southward ward along the Lehigh River with craftsman-bungalow stock, a deep rental register, and block-by-block reinvestment.",
        city_id="allentown",
    ),
    # =======================================================================
    # WEST_END (1 Submarket)
    # =======================================================================
    "West End": SubmarketMeta(
        name="West End",
        borough="WEST_END",
        lat=40.6000,
        lng=-75.5400,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.72,
        capex=3200000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The west-of-downtown grid toward the Lehigh Valley Hospital campus with pre-war housing and investor renovation flow.",
        city_id="allentown",
    ),
}


# ---------------------------------------------------------------------------
# Allentown Divisions Catalog
# ---------------------------------------------------------------------------

ALLENTOWN_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_ALLENTOWN": BoroughMeta(
        name="DOWNTOWN_ALLENTOWN",
        center_lat=40.6050,
        center_lng=-75.4950,
        zoom=13.5,
        bbox=ALLENTOWN_DIVISION_BBOXES["DOWNTOWN_ALLENTOWN"],
        submarkets=[k for k, v in ALLENTOWN_SUBMARKETS.items() if v.borough == "DOWNTOWN_ALLENTOWN"],
        city_id="allentown",
    ),
    "BETHLEHEM": BoroughMeta(
        name="BETHLEHEM",
        center_lat=40.6050,
        center_lng=-75.3820,
        zoom=13.5,
        bbox=ALLENTOWN_DIVISION_BBOXES["BETHLEHEM"],
        submarkets=[k for k, v in ALLENTOWN_SUBMARKETS.items() if v.borough == "BETHLEHEM"],
        city_id="allentown",
    ),
    "EASTON": BoroughMeta(
        name="EASTON",
        center_lat=40.6950,
        center_lng=-75.2250,
        zoom=13.0,
        bbox=ALLENTOWN_DIVISION_BBOXES["EASTON"],
        submarkets=[k for k, v in ALLENTOWN_SUBMARKETS.items() if v.borough == "EASTON"],
        city_id="allentown",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=40.5620,
        center_lng=-75.4950,
        zoom=13.0,
        bbox=ALLENTOWN_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in ALLENTOWN_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="allentown",
    ),
    "WEST_END": BoroughMeta(
        name="WEST_END",
        center_lat=40.6000,
        center_lng=-75.5400,
        zoom=13.0,
        bbox=ALLENTOWN_DIVISION_BBOXES["WEST_END"],
        submarkets=[k for k, v in ALLENTOWN_SUBMARKETS.items() if v.borough == "WEST_END"],
        city_id="allentown",
    ),
}

ALL_CITY_DIVISION_BBOXES = ALLENTOWN_DIVISION_BBOXES
ALL_CITY_SUBMARKETS = ALLENTOWN_SUBMARKETS
ALL_CITY_DIVISIONS = ALLENTOWN_DIVISIONS


def _to_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def compose_deed_date(row: dict[str, Any]) -> str | None:
    """The first of the sale month, from ``SYEAR`` and ``SMON`` (the layer has no day).

    ``DeedsACRISProducer`` calls this when ``recorded_date`` is unmapped;
    returns None for a missing year or a month outside 1-12.
    """
    year, month = _to_int(row.get("SYEAR")), _to_int(row.get("SMON"))
    if year is None or month is None or not (1 <= month <= 12 and year >= 1900):
        return None
    return f"{year:04d}-{month:02d}-01"


# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Allentown deeds: the city's Tax Parcels Assessed layer (sale year + month).
# ---------------------------------------------------------------------------
ALLENTOWN_DEEDS_ENDPOINT = (
    "https://services1.arcgis.com/WUqVDRuvIiIiH2Pl/arcgis/rest/services/Tax_Parcels_Assessed_2022/"
    "FeatureServer/0"
)

ALLENTOWN_FEED_SPECS: dict[str, dict[str, object]] = {
    "deeds": {
        "endpoint": ALLENTOWN_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "",
        "id_keys": ["WARDACCTNO", "XINSTNUM"],
        "topic_key": "topic_deeds",
        "interval_seconds": 1800.0,
        "producer_key": "deeds",
        "extra": {
            "order_by": "SYEAR DESC, SMON DESC, OBJECTID DESC",
            "select": "OBJECTID,WARDACCTNO,PIN,PARNUM,XINSTNUM,SYEAR,SMON,SPRICE,PROPERTYADDR,ZIP",
            "where": "SYEAR >= 1900 AND SMON <> '00' AND SMON <> ''",
            "ingestion_mode": "snapshot",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "expected_cadence_days": 45,
            "non_spatial": False,
            "composite_id": True,
            "scope": (
                "Allentown PA deeds from the city's Tax Parcels Assessed layer: each parcel's last "
                "sale (SYEAR + SMON, composed by compose_deed_date), newest first; owner columns "
                "are never selected."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_allentown_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Allentown feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (permits/SLA/
    311 are not registered for Allentown).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in ALLENTOWN_FEED_SPECS:
        available = ", ".join(sorted(ALLENTOWN_FEED_SPECS))
        raise KeyError(
            f"'{ALLENTOWN_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = ALLENTOWN_FEED_SPECS[feed_name]
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
    metro_bbox=ALLENTOWN_METRO_BBOX,
    division_bboxes=ALLENTOWN_DIVISION_BBOXES,
    submarkets=ALLENTOWN_SUBMARKETS,
    divisions=ALLENTOWN_DIVISIONS,
    contains=is_in_allentown_metro,
)

__all__ = [
    "ALLENTOWN_CENTER",
    "ALLENTOWN_CITY_ID",
    "ALLENTOWN_DEEDS_ENDPOINT",
    "ALLENTOWN_DIVISIONS",
    "ALLENTOWN_DIVISION_BBOXES",
    "ALLENTOWN_FEED_SPECS",
    "ALLENTOWN_METRO_BBOX",
    "ALLENTOWN_SUBMARKETS",
    "ALL_CITY_DIVISIONS",
    "ALL_CITY_DIVISION_BBOXES",
    "ALL_CITY_SUBMARKETS",
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "REGISTRATION",
    "get_allentown_dataset",
    "is_in_allentown",
    "is_in_allentown_metro",
]
