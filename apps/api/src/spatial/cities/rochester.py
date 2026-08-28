"""Rochester Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Rochester,
NY (Monroe County seat on the Genesee — deliberately not overlapping the
sibling Buffalo/Syracuse leaf boxes).

Feed scope (probed 2026-08-27, docs/research/probe-rochester.md; re-probed
live 2026-08-28 at implementation). Rochester is a DEEDS-led partial metro:
the city Hub's ``Tax Parcel Records: Open Data`` layer carries per-parcel
``SALE_DATE``/``SALE_PRICE``/``BOOK``/``PAGE``/``DEED_TYPE`` — the closest
ACRIS-shape feed this project has seen outside a county clerk. The feed is
an on-prem ArcGIS polygon service (``maps.cityofrochester.gov``, not the
services2.arcgis.com AGOL org), served by the existing ``ArcGISClient``:

* DEEDS — ``Open_Data/Tax_Parcels_Open_Data/FeatureServer/0``. Watermark
  ``SALE_DATE`` is TEXT ``MM/DD/YYYY`` (len 50). Text ``ORDER BY DESC``
  LIES (``12/31/2025`` sorts above ``07/22/2026`` string-wise) — ADR 0005
  text-watermark with the declared ``%m/%d/%Y`` format is mandatory.
  Native parcel polygons (``outSR=4326`` rings → centroid) supply every
  row's coordinates, so ``needs_geocode`` stays False — no ADR-0004 hook.
* PERMITS — absent. No permit/construction/building dataset exists on the
  Hub (keyword sweep surfaces zoning districts and footprints only). Tier 3.
* SLA/licenses — absent. No license dataset on the Hub. Tier 3.
* COMPLAINTS_311 — frozen 2022 archive (``311_Case_Data``: 51,721 rows,
  newest ``Request_Date`` 2022-02-07, 0 since; the CSV companion is
  literally ``311_Case_Data_-_2021_DRAFT.csv``). Tier 3 — do not register
  unless the city resumes the extract.

Implementation re-probe (2026-08-28, live, watermark confirmed): total
64,746 parcels; 2026 YTD 2,279 sales through Jul 22; monthly windows Jul
141 / Jun 350 / May 485; Aug 2026 = 0 — the monthly-roll lag from the probe
holds. Newest sale 2026-07-22 (547 Avis St, $110,000, ``DEED_TYPE='W'``,
BOOK 13214/PAGE 320) re-captured byte-verbatim as OBJECTID 5294, with the
$1 quitclaim OBJECTID 61058 (396 Brooks Ave, ``DEED_TYPE='Q'``) as the
noise fixture. ``CITY <> 'ROCHESTER'`` count is 0 — the layer is city
parcels only, so the probe's conditional "Pittsford village edge" submarket
is NOT evidenced (Pittsford village coordinates hit 0 parcels) and is
excluded. Noise contract: $1 quitclaims are kept at ingest (shared producer
has no per-city ``where``; VB precedent) — the arm's-length ``VALID`` flag
is empty on 64,632/64,746 rows, so market-sale filtering belongs on the
analysis side. Re-probe within 72 h of any spine change; if September still
shows 0 new sale rows after a full month, treat the roll as stalled.
"""

from typing import Dict

from src.producers.field_maps_rochester import (
    DEEDS_FIELD_MAP,
    FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

ROCHESTER_CITY_ID: str = "rochester"

# City-parcel bbox (the live layer's declared Web-Mercator extent converted
# to WGS84: SW corner -77.7015/43.1034, NE corner -77.5325/43.2676). The
# north edge is Lake Ontario, the west edge the Greece line, the east edge
# the Irondequoit Bay/Penfield line; Pittsford and Brighton villages sit
# outside the parcel extent and must stay out of the box.
ROCHESTER_METRO_BBOX: Dict[str, float] = {
    "min_lat": 43.10,
    "max_lat": 43.27,
    "min_lng": -77.71,
    "max_lng": -77.53,
}

# Registration-contract center: downtown Rochester (Main St CBD).
ROCHESTER_CENTER: Dict[str, float] = {"lat": 43.1560, "lng": -77.6120}

# 6 Rochester Division Bounding Boxes (strictly nested inside the metro bbox)
ROCHESTER_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_RIVER":    {"min_lat": 43.130, "max_lat": 43.170, "min_lng": -77.650, "max_lng": -77.600},
    "EAST_SIDE_CULTURAL": {"min_lat": 43.140, "max_lat": 43.165, "min_lng": -77.610, "max_lng": -77.575},
    "NORTH_LAKESHORE":   {"min_lat": 43.210, "max_lat": 43.270, "min_lng": -77.600, "max_lng": -77.535},
    "NORTHWEST_GORGE":   {"min_lat": 43.160, "max_lat": 43.210, "min_lng": -77.660, "max_lng": -77.610},
    "SOUTHWEST_WARD":    {"min_lat": 43.100, "max_lat": 43.140, "min_lng": -77.670, "max_lng": -77.615},
    "NORTHEAST_UPPER":   {"min_lat": 43.165, "max_lat": 43.200, "min_lng": -77.610, "max_lng": -77.555},
}


def is_in_rochester_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Rochester metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        ROCHESTER_METRO_BBOX["min_lat"] <= lat <= ROCHESTER_METRO_BBOX["max_lat"]
        and ROCHESTER_METRO_BBOX["min_lng"] <= lng <= ROCHESTER_METRO_BBOX["max_lng"]
    )


def is_in_rochester(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_rochester_metro`."""
    return is_in_rochester_metro(lat, lng)


# ---------------------------------------------------------------------------
# Rochester Submarket Registry (8 Submarkets Across 6 Divisions)
# Every anchor coordinate below was verified to intersect a live parcel on
# the 2026-08-28 re-probe (esriSpatialRelIntersects point-in-parcel = 1).
# ---------------------------------------------------------------------------

ROCHESTER_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_RIVER (2 Submarkets)
    # =======================================================================
    "Center City": SubmarketMeta(
        name="Center City",
        borough="DOWNTOWN_RIVER",
        lat=43.1510,
        lng=-77.6180,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.86,
        capex=6500000.0,
        permit_vel=34.0,
        shift_ratio=1.48,
        sla=58.0,
        description="The Main Street CBD west of the Genesee with office-to-residential conversions, theROC anchor projects, and the city's densest mixed-use pipeline.",
        city_id="rochester",
    ),
    "Corn Hill": SubmarketMeta(
        name="Corn Hill",
        borough="DOWNTOWN_RIVER",
        lat=43.1430,
        lng=-77.6240,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.82,
        capex=4200000.0,
        permit_vel=24.0,
        shift_ratio=1.35,
        sla=46.0,
        description="The third-oldest residential neighborhood in Rochester: Italianate and Victorian rowhouses on the bluff southwest of downtown with steady restoration trades.",
        city_id="rochester",
    ),
    # =======================================================================
    # EAST_SIDE_CULTURAL (2 Submarkets)
    # =======================================================================
    "Park Avenue": SubmarketMeta(
        name="Park Avenue",
        borough="EAST_SIDE_CULTURAL",
        lat=43.1500,
        lng=-77.5960,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.84,
        capex=5100000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=54.0,
        description="The East Avenue corridor's boutique retail spine of mansions cut into apartments, restaurant-row licensing, and high-turnover condo stock.",
        city_id="rochester",
    ),
    "Neighborhood of the Arts": SubmarketMeta(
        name="Neighborhood of the Arts",
        borough="EAST_SIDE_CULTURAL",
        lat=43.1530,
        lng=-77.5880,
        zoom=15.0,
        pitch=40.0,
        base_lims=0.83,
        capex=4800000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=52.0,
        description="The Memorial Art Gallery / Village Gate district around University Avenue where loft conversions and gallery-space retrofits drive the permit mix.",
        city_id="rochester",
    ),
    # =======================================================================
    # NORTH_LAKESHORE (1 Submarket)
    # =======================================================================
    "Charlotte": SubmarketMeta(
        name="Charlotte",
        borough="NORTH_LAKESHORE",
        lat=43.2270,
        lng=-77.5630,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.68,
        capex=2900000.0,
        permit_vel=18.0,
        shift_ratio=1.20,
        sla=36.0,
        description="The Ontario lakeshore village at the river mouth with seasonal cottage turnover, pier-adjacent hospitality licensing, and flood-zone rebuild work.",
        city_id="rochester",
    ),
    # =======================================================================
    # NORTHWEST_GORGE (1 Submarket)
    # =======================================================================
    "Maplewood": SubmarketMeta(
        name="Maplewood",
        borough="NORTHWEST_GORGE",
        lat=43.1720,
        lng=-77.6250,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.74,
        capex=3400000.0,
        permit_vel=22.0,
        shift_ratio=1.26,
        sla=42.0,
        description="The Dewey Avenue grid west of the Genesee gorge around Maplewood Park with solid pre-war housing stock and investor renovation flow.",
        city_id="rochester",
    ),
    # =======================================================================
    # SOUTHWEST_WARD (1 Submarket)
    # =======================================================================
    "19th Ward": SubmarketMeta(
        name="19th Ward",
        borough="SOUTHWEST_WARD",
        lat=43.1200,
        lng=-77.6430,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=40.0,
        description="The Thurston Road/Arnett Boulevard ward south of the UR campus with craftsman-bungalow stock, a deep rental register, and block-by-block reinvestment.",
        city_id="rochester",
    ),
    # =======================================================================
    # NORTHEAST_UPPER (1 Submarket)
    # =======================================================================
    "Upper Falls": SubmarketMeta(
        name="Upper Falls",
        borough="NORTHEAST_UPPER",
        lat=43.1770,
        lng=-77.5960,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.66,
        capex=2700000.0,
        permit_vel=16.0,
        shift_ratio=1.18,
        sla=34.0,
        description="The north-central ward along Upper Falls Boulevard where the city's lowest sale prices meet the heaviest vacancy-to-acquisition conversion flow.",
        city_id="rochester",
    ),
}


# ---------------------------------------------------------------------------
# Rochester Divisions Catalog
# ---------------------------------------------------------------------------

ROCHESTER_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_RIVER": BoroughMeta(
        name="DOWNTOWN_RIVER",
        center_lat=43.1470,
        center_lng=-77.6210,
        zoom=13.5,
        bbox=ROCHESTER_DIVISION_BBOXES["DOWNTOWN_RIVER"],
        submarkets=[k for k, v in ROCHESTER_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIVER"],
        city_id="rochester",
    ),
    "EAST_SIDE_CULTURAL": BoroughMeta(
        name="EAST_SIDE_CULTURAL",
        center_lat=43.1515,
        center_lng=-77.5920,
        zoom=13.5,
        bbox=ROCHESTER_DIVISION_BBOXES["EAST_SIDE_CULTURAL"],
        submarkets=[k for k, v in ROCHESTER_SUBMARKETS.items() if v.borough == "EAST_SIDE_CULTURAL"],
        city_id="rochester",
    ),
    "NORTH_LAKESHORE": BoroughMeta(
        name="NORTH_LAKESHORE",
        center_lat=43.2270,
        center_lng=-77.5630,
        zoom=13.0,
        bbox=ROCHESTER_DIVISION_BBOXES["NORTH_LAKESHORE"],
        submarkets=[k for k, v in ROCHESTER_SUBMARKETS.items() if v.borough == "NORTH_LAKESHORE"],
        city_id="rochester",
    ),
    "NORTHWEST_GORGE": BoroughMeta(
        name="NORTHWEST_GORGE",
        center_lat=43.1850,
        center_lng=-77.6350,
        zoom=13.0,
        bbox=ROCHESTER_DIVISION_BBOXES["NORTHWEST_GORGE"],
        submarkets=[k for k, v in ROCHESTER_SUBMARKETS.items() if v.borough == "NORTHWEST_GORGE"],
        city_id="rochester",
    ),
    "SOUTHWEST_WARD": BoroughMeta(
        name="SOUTHWEST_WARD",
        center_lat=43.1200,
        center_lng=-77.6430,
        zoom=13.0,
        bbox=ROCHESTER_DIVISION_BBOXES["SOUTHWEST_WARD"],
        submarkets=[k for k, v in ROCHESTER_SUBMARKETS.items() if v.borough == "SOUTHWEST_WARD"],
        city_id="rochester",
    ),
    "NORTHEAST_UPPER": BoroughMeta(
        name="NORTHEAST_UPPER",
        center_lat=43.1770,
        center_lng=-77.5960,
        zoom=13.0,
        bbox=ROCHESTER_DIVISION_BBOXES["NORTHEAST_UPPER"],
        submarkets=[k for k, v in ROCHESTER_SUBMARKETS.items() if v.borough == "NORTHEAST_UPPER"],
        city_id="rochester",
    ),
}

ROC_DIVISION_BBOXES = ROCHESTER_DIVISION_BBOXES
ROC_SUBMARKETS = ROCHESTER_SUBMARKETS
ROC_DIVISIONS = ROCHESTER_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27 and re-probed live 2026-08-28 against the on-prem server
# maps.cityofrochester.gov (NOT the services2.arcgis.com AGOL org). Sketch
# matches docs/research/probe-rochester.md with the live confirmations
# recorded in the module docstring: watermark 07/22/2026, monthly-roll lag
# holds (Aug = 0), CITY field is 'ROCHESTER' on all 64,746 rows.
# ---------------------------------------------------------------------------
ROCHESTER_DEEDS_ENDPOINT = (
    "https://maps.cityofrochester.gov/server/rest/services/"
    "Open_Data/Tax_Parcels_Open_Data/FeatureServer/0"
)

ROCHESTER_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "deeds": {
        "endpoint": ROCHESTER_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SALE_DATE",
        "id_keys": ["PRINTKEY", "PARCELID", "SALE_DATE"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            # Native parcel polygons (outSR=4326 rings -> centroid) supply
            # every row's coordinates; the ADR-0004 geocode hook is NOT
            # declared. SITEADDRESS/ZIP5 were complete on sampled sale rows.
            "needs_geocode": False,
            "watermark_type": "text",
            "watermark_format": "%m/%d/%Y",
            "oid_field": "OBJECTID",
            "max_record_count": 100000,
            "expected_cadence_days": 30,
            "non_spatial": False,
            "scope": (
                "Rochester DEEDS/sales via the Tax Parcel Records: Open Data "
                "layer (Monroe County RPS extract; native parcel polygons, "
                "NOT address-only). TEXT MM/DD/YYYY watermark sorts "
                "lexically — typed comparison required (ADR-0005). MONTHLY "
                "ROLL WITH LAG: Jul rows stop 07/22, Aug=0 at the 2026-08-28 "
                "re-probe with 2026 YTD 2,279 — re-probe within 72h of any "
                "spine or schedule change and treat as stalled if September "
                "still shows 0 after a full month. $1 DEED_TYPE='Q' "
                "quitclaim transfers are KEPT at ingest (no per-city where; "
                "arm's-length VALID flag empty layer-wide — market-sale "
                "filtering is analysis-side). No owner-name columns exist; "
                "party fields stay None. BOOK/PAGE ride id_keys as the "
                "recorded-deed references; PRINTKEY/PARCELID are the parcel "
                "keys. Pittsford village edge is NOT evidenced (0 parcel "
                "hits — city parcels only)."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_rochester_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Rochester feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent (permits/SLA are absent from the Hub; 311 is a frozen 2022
    archive).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in ROCHESTER_FEED_SPECS:
        available = ", ".join(sorted(ROCHESTER_FEED_SPECS))
        raise KeyError(
            f"'{ROCHESTER_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = ROCHESTER_FEED_SPECS[feed_name]
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
    metro_bbox=ROCHESTER_METRO_BBOX,
    division_bboxes=ROCHESTER_DIVISION_BBOXES,
    submarkets=ROCHESTER_SUBMARKETS,
    divisions=ROCHESTER_DIVISIONS,
    contains=is_in_rochester_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "REGISTRATION",
    "ROC_DIVISIONS",
    "ROC_DIVISION_BBOXES",
    "ROC_SUBMARKETS",
    "ROCHESTER_CENTER",
    "ROCHESTER_CITY_ID",
    "ROCHESTER_DEEDS_ENDPOINT",
    "ROCHESTER_DIVISIONS",
    "ROCHESTER_DIVISION_BBOXES",
    "ROCHESTER_FEED_SPECS",
    "ROCHESTER_METRO_BBOX",
    "ROCHESTER_SUBMARKETS",
    "get_rochester_dataset",
    "is_in_rochester",
    "is_in_rochester_metro",
]
