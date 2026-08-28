"""Bowling Green / Warren County Metro Submarket Registry and Spatial Layer.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the city of Bowling
Green, KY — the Warren County seat and the largest city in the county
(settled where the Barren River oxbows beneath the South Central Kentucky
highway crossroads of I-65 / I-165 / US-31W / US-231). This module's metro
box is County-scale: it covers the incorporated city and the immediate
unincorporated Warren County development ring, then clips at the county
frame. It does not reach into the neighboring-county seats adjacent to the
county line (south into Simpson and Allen, east into Barren, north into
Edmonson, west into Butler and Logan).

Feed scope (probed 2026-08-28, docs/research/se-probe-bowling_green.md;
re-probed LIVE 2026-08-28 at implementation). Only ONE feed is live and
registered:

* PERMITS — ``https://webgis.bgky.org/server/rest/services/CCPC/
  CCPC_Building_Permits_2010/FeatureServer/5`` "Building Permits 2010+"
  (ArcGIS Server 11.5, city-owned). Watermark ``created_date``, the
  date-typed ArcGIS editor-tracking column. **Native point geometry** in
  KY-North State Plane 102680/2247; the client always requests
  ``outSR=4326`` so every row rides in as WGS84 ``latitude``/``longitude``
  (verified live). ``needs_geocode`` is declared defensively only — a
  native-point feed must never fall through to an address geocode.
  Registered whole: no server-side status/type filter.

The other three candidate families are deliberately NOT registered (partial
registration is allowed; ``get_bowling_green_dataset`` raises for them):

* COMPLAINTS_311 — NOT-VIABLE. ``Code_Cases/13`` froze 2023-01-31;
  ``CCPC_Compliance_Inspections/2`` is EPSC/construction compliance, not
  citizen 311.
* SLA — NOT-VIABLE. No license register in the 978-dataset org.
* DEEDS — NOT-VIABLE. ``WARCO/Parcel_Reference`` is a parcel snapshot with
  no fresh sales; warrenpva.com is unreachable; the KY geoportal only covers
  Webster Co.

Host quirks (documented here; ``watermarks.py`` / ``geocoder.py`` NOT edited):

* ``webgis.bgky.org`` is **ANSI-date-literal**: the where clause must spell
  ``created_date > DATE 'YYYY-MM-DD HH:MM:SS'``. A bare ISO string
  (``'2026-08-24T18:06:08+00:00'``) returns ArcGIS error 400. This is a host
  string-comparison limitation, not a schema property — the watermark column
  is a true date, so no ADR-0005 text-watermark declaration is needed.
  Note in spine delta.
* ``_STATE_RE`` false positive: street names such as "MT VICTOR LANE" carry a
  ``M T`` token that ``_STATE_RE`` matches as the MT state token, so an
  address context append is skipped for a Mt Victor geocode fallback. That
  path is never taken here (native coords), documented only.

OID/ordering contract: layer 5 publishes ``OBJECTID`` as its ``objectIdField``
and honors ``orderByFields=OBJECTID``. ``maxRecordCount`` is 2000 (verified
live), so the spec declares ``max_record_count=2000``.

Implementation re-probe (2026-08-28, live): newest ``created_date``
2026-08-24T18:06:08+00:00 (PermitNum 2026-1314, a 24-unit apartment project at
2633 Mt Victor Lane, OBJECTID 113479), 7d=22, 60d=386, total=29,691. Feed
extent (outSR=4326): lat 36.795-37.179, lng -86.661--86.125 — the metro box
is padded to that extent.
"""

from typing import Dict

from src.producers.field_maps_bowling_green import (
    BOWLING_GREEN_PERMITS_FIELD_MAP,
    GEOCODE_CONTEXT,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BOWLING_GREEN_CITY_ID: str = "bowling_green"
BOWLING_GREEN_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# County-scale metro bbox, grounded in the live 2026-08-28 feed extent
# (returnExtentOnly, outSR=4326): lat 36.795-37.179, lng -86.661--86.125,
# padded to the hundredth. Covers the incorporated city and the Warren
# County development ring; clipped at the county frame.
BOWLING_GREEN_METRO_BBOX: Dict[str, float] = {
    "min_lat": 36.79,
    "max_lat": 37.19,
    "min_lng": -86.67,
    "max_lng": -86.12,
}

# Registration-contract center: Bowling Green courthouse square.
BOWLING_GREEN_CENTER: Dict[str, float] = {"lat": 36.9892, "lng": -86.4436}

# 7 Bowling Green Division Bounding Boxes (strictly nested inside the metro bbox)
BOWLING_GREEN_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_UNIVERSITY":   {"min_lat": 36.945, "max_lat": 37.010, "min_lng": -86.510, "max_lng": -86.400},
    "EAST_LOOP":             {"min_lat": 36.945, "max_lat": 37.005, "min_lng": -86.420, "max_lng": -86.310},
    "SCOTTSVILLE_CORRIDOR":  {"min_lat": 36.830, "max_lat": 36.945, "min_lng": -86.450, "max_lng": -86.350},
    "NASHVILLE_SOUTHWEST":   {"min_lat": 36.800, "max_lat": 36.945, "min_lng": -86.600, "max_lng": -86.450},
    "CAMPBELL_SOUTH":        {"min_lat": 36.800, "max_lat": 36.900, "min_lng": -86.450, "max_lng": -86.300},
    "RUSSELLVILLE_NORTHWEST": {"min_lat": 36.950, "max_lat": 37.080, "min_lng": -86.670, "max_lng": -86.500},
    "EAST_COUNTY_TRANSPARK": {"min_lat": 36.900, "max_lat": 37.050, "min_lng": -86.350, "max_lng": -86.120},
}


def is_in_bowling_green_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Bowling Green metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        BOWLING_GREEN_METRO_BBOX["min_lat"] <= lat <= BOWLING_GREEN_METRO_BBOX["max_lat"]
        and BOWLING_GREEN_METRO_BBOX["min_lng"] <= lng <= BOWLING_GREEN_METRO_BBOX["max_lng"]
    )


def is_in_bowling_green(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_bowling_green_metro`."""
    return is_in_bowling_green_metro(lat, lng)


# ---------------------------------------------------------------------------
# Bowling Green Submarket Registry (10 Submarkets Across 7 Divisions)
# ---------------------------------------------------------------------------

BOWLING_GREEN_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_UNIVERSITY (2 Submarkets)
    # =======================================================================
    "Fountain Square": SubmarketMeta(
        name="Fountain Square",
        borough="DOWNTOWN_UNIVERSITY",
        lat=36.9900,
        lng=-86.4420,
        zoom=15.0,
        pitch=42.0,
        base_lims=0.86,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=52.0,
        description="Court-square retail and civic core between the Barren River and Center Street, dense with renovation, infill apartments, and restaurant refits.",
        city_id="bowling_green",
    ),
    "WKU": SubmarketMeta(
        name="WKU",
        borough="DOWNTOWN_UNIVERSITY",
        lat=36.9865,
        lng=-86.4580,
        zoom=14.5,
        pitch=40.0,
        base_lims=0.83,
        capex=4800000.0,
        permit_vel=30.0,
        shift_ratio=1.40,
        sla=50.0,
        description="Western Kentucky University campus corridor and its Hilltopper student-housing ring feeding multi-family and street-retail GI on Normal and State Streets.",
        city_id="bowling_green",
    ),
    # =======================================================================
    # EAST_LOOP (2 Submarkets)
    # =======================================================================
    "Mt Victor": SubmarketMeta(
        name="Mt Victor",
        borough="EAST_LOOP",
        lat=36.9780,
        lng=-86.3940,
        zoom=14.0,
        pitch=36.0,
        base_lims=0.80,
        capex=4600000.0,
        permit_vel=27.0,
        shift_ratio=1.37,
        sla=48.0,
        description="Mt Victor Lane and the Loop-side apartment/multifamily corridor east of downtown absorbing the 2025+ large-scale multifamily filings.",
        city_id="bowling_green",
    ),
    "Lovers Lane": SubmarketMeta(
        name="Lovers Lane",
        borough="EAST_LOOP",
        lat=36.9600,
        lng=-86.4000,
        zoom=14.0,
        pitch=34.0,
        base_lims=0.76,
        capex=3400000.0,
        permit_vel=20.0,
        shift_ratio=1.30,
        sla=42.0,
        description="Established Lovers Lane subdivisions between the Loop and Us-31W, mixing owner-occupied infill, deck/fence permits, and turn-by-investor resales.",
        city_id="bowling_green",
    ),
    # =======================================================================
    # SCOTTSVILLE_CORRIDOR (1 Submarket)
    # =======================================================================
    "Scottsville Rd": SubmarketMeta(
        name="Scottsville Rd",
        borough="SCOTTSVILLE_CORRIDOR",
        lat=36.8800,
        lng=-86.3950,
        zoom=13.5,
        pitch=34.0,
        base_lims=0.72,
        capex=2900000.0,
        permit_vel=18.0,
        shift_ratio=1.27,
        sla=40.0,
        description="US-231 Scottsville Road retail-and-residential corridor running south-east to the county line, fed by Alvaton/Plano commuter infill.",
        city_id="bowling_green",
    ),
    # =======================================================================
    # NASHVILLE_SOUTHWEST (1 Submarket)
    # =======================================================================
    "Nashville Rd": SubmarketMeta(
        name="Nashville Rd",
        borough="NASHVILLE_SOUTHWEST",
        lat=36.8800,
        lng=-86.5200,
        zoom=13.5,
        pitch=34.0,
        base_lims=0.70,
        capex=2700000.0,
        permit_vel=17.0,
        shift_ratio=1.25,
        sla=38.0,
        description="US-31W Nashville Road southwest of the river toward the I-65/I-165 interchange, a legacy highway strip with steady retail refit and light industrial.",
        city_id="bowling_green",
    ),
    # =======================================================================
    # CAMPBELL_SOUTH (1 Submarket)
    # =======================================================================
    "Three Springs Rd": SubmarketMeta(
        name="Three Springs Rd",
        borough="CAMPBELL_SOUTH",
        lat=36.8600,
        lng=-86.4000,
        zoom=13.0,
        pitch=32.0,
        base_lims=0.66,
        capex=2200000.0,
        permit_vel=15.0,
        shift_ratio=1.22,
        sla=36.0,
        description="Three Springs Road and the Campbell-area south-side neighborhoods, a family-residential ring converting past working land to infill lots.",
        city_id="bowling_green",
    ),
    # =======================================================================
    # RUSSELLVILLE_NORTHWEST (1 Submarket)
    # =======================================================================
    "Russellville Rd": SubmarketMeta(
        name="Russellville Rd",
        borough="RUSSELLVILLE_NORTHWEST",
        lat=37.0200,
        lng=-86.5600,
        zoom=13.5,
        pitch=33.0,
        base_lims=0.71,
        capex=2800000.0,
        permit_vel=17.0,
        shift_ratio=1.24,
        sla=38.0,
        description="Russellville Road northwest toward the county line, pockets of estate infill and minor commercial off the US-68/231 junction.",
        city_id="bowling_green",
    ),
    # =======================================================================
    # EAST_COUNTY_TRANSPARK (2 Submarkets)
    # =======================================================================
    "KY Transpark": SubmarketMeta(
        name="KY Transpark",
        borough="EAST_COUNTY_TRANSPARK",
        lat=36.9800,
        lng=-86.3050,
        zoom=13.0,
        pitch=32.0,
        base_lims=0.74,
        capex=3200000.0,
        permit_vel=19.0,
        shift_ratio=1.29,
        sla=41.0,
        description="Kentucky Transpark industrial/advanced-manufacturing campus on the east edge, drawing warehouse, flex, and build-to-suit filings off the I-65 exits.",
        city_id="bowling_green",
    ),
    "Bluestem Sheldrake": SubmarketMeta(
        name="Bluestem Sheldrake",
        borough="EAST_COUNTY_TRANSPARK",
        lat=36.9450,
        lng=-86.2700,
        zoom=13.0,
        pitch=30.0,
        base_lims=0.65,
        capex=2000000.0,
        permit_vel=14.0,
        shift_ratio=1.20,
        sla=34.0,
        description="Far-east Bluestem and Sheldrake district low-density acreage, infill single-family and agricultural-periphery permits seeded by Transpark employment.",
        city_id="bowling_green",
    ),
}


# ---------------------------------------------------------------------------
# Bowling Green Divisions Catalog
# ---------------------------------------------------------------------------

BOWLING_GREEN_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_UNIVERSITY": BoroughMeta(
        name="DOWNTOWN_UNIVERSITY",
        center_lat=36.9880,
        center_lng=-86.4500,
        zoom=14.0,
        bbox=BOWLING_GREEN_DIVISION_BBOXES["DOWNTOWN_UNIVERSITY"],
        submarkets=[k for k, v in BOWLING_GREEN_SUBMARKETS.items() if v.borough == "DOWNTOWN_UNIVERSITY"],
        city_id="bowling_green",
    ),
    "EAST_LOOP": BoroughMeta(
        name="EAST_LOOP",
        center_lat=36.9700,
        center_lng=-86.3960,
        zoom=13.5,
        bbox=BOWLING_GREEN_DIVISION_BBOXES["EAST_LOOP"],
        submarkets=[k for k, v in BOWLING_GREEN_SUBMARKETS.items() if v.borough == "EAST_LOOP"],
        city_id="bowling_green",
    ),
    "SCOTTSVILLE_CORRIDOR": BoroughMeta(
        name="SCOTTSVILLE_CORRIDOR",
        center_lat=36.8900,
        center_lng=-86.4000,
        zoom=13.0,
        bbox=BOWLING_GREEN_DIVISION_BBOXES["SCOTTSVILLE_CORRIDOR"],
        submarkets=[k for k, v in BOWLING_GREEN_SUBMARKETS.items() if v.borough == "SCOTTSVILLE_CORRIDOR"],
        city_id="bowling_green",
    ),
    "NASHVILLE_SOUTHWEST": BoroughMeta(
        name="NASHVILLE_SOUTHWEST",
        center_lat=36.9000,
        center_lng=-86.5100,
        zoom=13.0,
        bbox=BOWLING_GREEN_DIVISION_BBOXES["NASHVILLE_SOUTHWEST"],
        submarkets=[k for k, v in BOWLING_GREEN_SUBMARKETS.items() if v.borough == "NASHVILLE_SOUTHWEST"],
        city_id="bowling_green",
    ),
    "CAMPBELL_SOUTH": BoroughMeta(
        name="CAMPBELL_SOUTH",
        center_lat=36.8600,
        center_lng=-86.3800,
        zoom=12.5,
        bbox=BOWLING_GREEN_DIVISION_BBOXES["CAMPBELL_SOUTH"],
        submarkets=[k for k, v in BOWLING_GREEN_SUBMARKETS.items() if v.borough == "CAMPBELL_SOUTH"],
        city_id="bowling_green",
    ),
    "RUSSELLVILLE_NORTHWEST": BoroughMeta(
        name="RUSSELLVILLE_NORTHWEST",
        center_lat=37.0100,
        center_lng=-86.5800,
        zoom=13.0,
        bbox=BOWLING_GREEN_DIVISION_BBOXES["RUSSELLVILLE_NORTHWEST"],
        submarkets=[k for k, v in BOWLING_GREEN_SUBMARKETS.items() if v.borough == "RUSSELLVILLE_NORTHWEST"],
        city_id="bowling_green",
    ),
    "EAST_COUNTY_TRANSPARK": BoroughMeta(
        name="EAST_COUNTY_TRANSPARK",
        center_lat=36.9650,
        center_lng=-86.2900,
        zoom=12.5,
        bbox=BOWLING_GREEN_DIVISION_BBOXES["EAST_COUNTY_TRANSPARK"],
        submarkets=[k for k, v in BOWLING_GREEN_SUBMARKETS.items() if v.borough == "EAST_COUNTY_TRANSPARK"],
        city_id="bowling_green",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28 and re-probed live 2026-08-28 against the city's single
# CCPC ArcGIS Server. Only PERMITS is live and registered; 311/SLA/DEEDS are
# deliberately absent (partial registration).
# ---------------------------------------------------------------------------
BOWLING_GREEN_PERMITS_ENDPOINT = (
    "https://webgis.bgky.org/server/rest/services/CCPC/"
    "CCPC_Building_Permits_2010/FeatureServer/5"
)

BOWLING_GREEN_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": BOWLING_GREEN_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "created_date",
        "id_keys": ["PermitNum", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 600.0,
        "producer_key": "permits",
        "extra": {
            "needs_geocode": True,
            "geocode_context": BOWLING_GREEN_GEOCODE_CONTEXT,
            "order_by": "OBJECTID",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "expected_cadence_days": 1,
            "scope": (
                "Bowling Green CCPC Building Permits 2010+ (ArcGIS Server "
                "11.5, city-owned) — date-typed created_date editor-tracking "
                "watermark (ISO after client flatten; the client always "
                "requests outSR=4326). NATIVE point geometry in KY-North "
                "State Plane 102680/2247, so needs_geocode is defensive only "
                "and non_spatial is NOT set. Host is ANSI-date-literal: the "
                "where clause must spell DATE 'YYYY-MM-DD HH:MM:SS' — a bare "
                "ISO comparison 400s (verified live). Registered whole — no "
                "server-side status/type filter. Split St_Number/St_Name "
                "address with no single line; source_neighborhood is absent."
            ),
            "field_map": BOWLING_GREEN_PERMITS_FIELD_MAP,
        },
    },
}


def get_bowling_green_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Bowling Green feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is absent
    (311 / SLA / deeds have no viable live feed here).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in BOWLING_GREEN_FEED_SPECS:
        available = ", ".join(sorted(BOWLING_GREEN_FEED_SPECS))
        raise KeyError(
            f"'{BOWLING_GREEN_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = BOWLING_GREEN_FEED_SPECS[feed_name]
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
    metro_bbox=BOWLING_GREEN_METRO_BBOX,
    division_bboxes=BOWLING_GREEN_DIVISION_BBOXES,
    submarkets=BOWLING_GREEN_SUBMARKETS,
    divisions=BOWLING_GREEN_DIVISIONS,
    contains=is_in_bowling_green_metro,
)

__all__ = [
    "BOWLING_GREEN_PERMITS_FIELD_MAP",
    "BOWLING_GREEN_CENTER",
    "BOWLING_GREEN_CITY_ID",
    "BOWLING_GREEN_DIVISIONS",
    "BOWLING_GREEN_DIVISION_BBOXES",
    "BOWLING_GREEN_FEED_SPECS",
    "BOWLING_GREEN_GEOCODE_CONTEXT",
    "BOWLING_GREEN_METRO_BBOX",
    "BOWLING_GREEN_PERMITS_ENDPOINT",
    "BOWLING_GREEN_SUBMARKETS",
    "GEOCODE_CONTEXT",
    "REGISTRATION",
    "get_bowling_green_dataset",
    "is_in_bowling_green",
    "is_in_bowling_green_metro",
]
