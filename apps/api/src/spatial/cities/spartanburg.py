GEOCODE_CONTEXT = "Spartanburg, SC"

PERMITS_FIELD_MAP = {
    "job_id": ["CaseNumber", "OBJECTID"],
    "job_type": ["WorkClass", "CaseType"],
    "issuance_date": ["ApplicationDate"],
}

SLA_FIELD_MAP = {
    "license_id": ["CaseNumber", "CaseID", "OBJECTID"],
    "dba": ["ProjectName", "CaseNumber"],
    "premises_name": ["ProjectName", "CaseNumber"],
    "license_type": ["CaseType"],
    "effective_date": ["ApplicationDate"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

SPARTANBURG_FIELD_MAP = FIELD_MAP

"""Spartanburg County Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for Spartanburg County, SC —
an inland driving-market metro between the Blue Ridge escarpment and the
Columbia Piedmont, centered on the City of Spartanburg and the I-85
Greenville–Spartanburg urban corridor.

Feed scope (probed and re-verified live 2026-08-28,
docs/research/se-probe-spartanburg.md — this is a REBUILD of the batch-1 leaf
lost to a branch switch). Both registered feeds are ONE shared EnerGov layer on
the county's on-prem ArcGIS Server 11.5:

* The ArcGIS site root is ``https://maps.spartanburgcounty.org/server/rest/services``
  (the naive ``/arcgis/rest/services`` prefix returns an IIS 404). The service
  is ``EnerGov/EnerGov_Spatial_Collections``, and both feeds are layer **5**
  ("History Points", esriGeometryPoint, outSR=4326 on query).
* PERMITS — layer 5 with ``where ModuleName='PermitManagement'``. Watermark
  ``ApplicationDate`` (esriFieldTypeDate — epoch-ms on the wire, ISO after the
  ArcGISClient flatten). Same-day live at implementation: newest
  2026-08-28T16:08:53Z. Total 41,555 rows; 30d 1,420; 2026 YTD 9,640.
* SLA — same layer 5 with ``where ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')``.
  Watermark ``ApplicationDate``; union newest 2026-07-08T11:55:00Z, total 187
  (Entity 79 + Management 108), 2026 YTD 9, recent window 0. A slow trickle
  (~2-3/mo) — registered at cadence 30 and flagged for orchestrator review.
* COMPLAINTS_311 — NOT-VIABLE: the only citizen-request-ish module is
  ``CodeManagement`` (code enforcement, 25,137 rows); there is no
  ``RequestManagement`` module. Do not register.
* DEEDS — NOT-VIABLE: no recorded-deeds layer (ROD search portal only);
  ``GIS/CAMA_Parcels`` is a parcel/assessment snapshot, not sales.

Delivery contract and host quirks (all verified live 2026-08-28):

* The layer carries NO address columns. Every row has ``SpatialType='Address'``
  (a server-side geocode flag) plus a ``SpatialID`` GUID — so coordinates are
  native (geometry lifted by the client to ``latitude``/``longitude``) and
  ``needs_geocode`` stays False. There is no address string for ADR-0004 to
  consume.
* **Host quirk:** ``maps.spartanburgcounty.org`` is ANSI-date-literal. A plain
  ISO string comparison (``ApplicationDate >= '2026-08-01T00:00:00'``) returns
  ArcGIS error ``400 "Unable to complete operation"``, while
  ``ApplicationDate >= date '2026-08-01'`` works. This host MUST be added to
  ``ANSI_DATE_LITERAL_HOSTS`` in ``src/producers/watermarks.py`` (spine delta —
  not edited here) so the shared ``watermark_comparison`` renders the ANSI
  literal.
* Layer 5 publishes ``objectIdField`` = ``OBJECTID`` (edit counter, unique), so
  the spec declares ``order_by="OBJECTID"`` / ``oid_field="OBJECTID"``.
* ``WorkClass`` is the specific sub-type; ``CaseType`` the permit class. The
  permits field map reads ``job_type`` as ``["WorkClass","CaseType"]`` so the
  producer's classifier gets DM/A2 signals; ``New Single Family Residence`` does
  not match the producer's NB keywords — a documented classifier gap.
* The SLA Entity module carries the business NAME as ``CaseNumber``
  (e.g. ``Brat &amp; Curry Co``, byte-verbatim HTML-escaped; the producer does
  not unescape), so the SLA id chain falls back to the ``CaseID`` GUID then
  ``OBJECTID``.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SPARTANBURG_CITY_ID: str = "spartanburg"
SPARTANBURG_GEOCODE_CONTEXT: str = "Spartanburg, SC"

# County-scale metro bbox, grounded in the live County_Line FeatureServer/0
# extent (EPSG:3361 -> EPSG:4326): lng -82.2316..-81.7104, lat
# 34.5771..35.2001. Padded to the hundredth. Following the Miami-Dade "center,
# not extent" precedent, the box is the whole county (the register carries no
# jurisdiction column; 3,026 of the 2026-YTD city-bbox permit rows prove the
# county layer covers the City of Spartanburg's urban footprint; the city is
# the urban core at the center). max_lng is -81.69 (raw county max lng is
# -81.7104, so -81.71 would have excluded the county's eastern edge).
SPARTANBURG_METRO_BBOX: Dict[str, float] = {
    "min_lat": 34.57,
    "max_lat": 35.21,
    "min_lng": -82.24,
    "max_lng": -81.69,
}

# Registration-contract center: Downtown Spartanburg (Main Street).
SPARTANBURG_CENTER: Dict[str, float] = {"lat": 34.9497, "lng": -81.9320}

# 6 Spartanburg Division Bounding Boxes (strictly nested inside the metro bbox)
SPARTANBURG_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_CORE":        {"min_lat": 34.920, "max_lat": 34.980, "min_lng": -81.960, "max_lng": -81.900},
    "EAST_CITY":            {"min_lat": 34.920, "max_lat": 34.990, "min_lng": -81.900, "max_lng": -81.840},
    "WEST_CITY":            {"min_lat": 34.920, "max_lat": 35.000, "min_lng": -82.030, "max_lng": -81.960},
    "BLUE_RIDGE_FOOTHILLS": {"min_lat": 34.990, "max_lat": 35.210, "min_lng": -82.240, "max_lng": -81.900},
    "I85_CORRIDOR":         {"min_lat": 34.860, "max_lat": 34.990, "min_lng": -82.150, "max_lng": -81.900},
    "SOUTH_COUNTY":         {"min_lat": 34.570, "max_lat": 34.890, "min_lng": -82.050, "max_lng": -81.690},
}


def is_in_spartanburg_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Spartanburg metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        SPARTANBURG_METRO_BBOX["min_lat"] <= lat <= SPARTANBURG_METRO_BBOX["max_lat"]
        and SPARTANBURG_METRO_BBOX["min_lng"] <= lng <= SPARTANBURG_METRO_BBOX["max_lng"]
    )


def is_in_spartanburg(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_spartanburg_metro`."""
    return is_in_spartanburg_metro(lat, lng)


# ---------------------------------------------------------------------------
# Spartanburg Submarket Registry (10 Submarkets Across 6 Divisions)
# ---------------------------------------------------------------------------

SPARTANBURG_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2 Submarkets)
    # =======================================================================
    "Downtown Spartanburg": SubmarketMeta(
        name="Downtown Spartanburg",
        borough="DOWNTOWN_CORE",
        lat=34.9494,
        lng=-81.9320,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.45,
        sla=55.0,
        description="Main Street commercial core with the city's densest renovation pipeline: upper-floor apartment conversions, facade grants, and the Hub City Mills adaptive-reuse anchors.",
        city_id="spartanburg",
    ),
    "Northside / Rail Yard": SubmarketMeta(
        name="Northside / Rail Yard",
        borough="DOWNTOWN_CORE",
        lat=34.9600,
        lng=-81.9350,
        zoom=14.5,
        pitch=42.0,
        base_lims=0.78,
        capex=3900000.0,
        permit_vel=22.0,
        shift_ratio=1.30,
        sla=44.0,
        description="Warehouse-and-rail district just north of the core where historic cotton-mill and freight stock is converting to lofts, breweries, and make-ready industrial space.",
        city_id="spartanburg",
    ),
    # =======================================================================
    # EAST_CITY (1 Submarket)
    # =======================================================================
    "Eastside / Hillcrest": SubmarketMeta(
        name="Eastside / Hillcrest",
        borough="EAST_CITY",
        lat=34.9470,
        lng=-81.8880,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.74,
        capex=2900000.0,
        permit_vel=18.0,
        shift_ratio=1.26,
        sla=40.0,
        description="Historic brick rowhouse and bungalow belt east of the core converging on Hillcrest Commons, catching first-time-buyer turnover and infill restoration.",
        city_id="spartanburg",
    ),
    # =======================================================================
    # WEST_CITY (1 Submarket)
    # =======================================================================
    "Westgate": SubmarketMeta(
        name="Westgate",
        borough="WEST_CITY",
        lat=34.9550,
        lng=-81.9780,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.72,
        capex=2600000.0,
        permit_vel=16.0,
        shift_ratio=1.22,
        sla=38.0,
        description="Working grid west of the core along the old W.O. Ezell corridor, mixing single-family repair-trade permitting with light industrial and retail refit demand.",
        city_id="spartanburg",
    ),
    # =======================================================================
    # BLUE_RIDGE_FOOTHILLS (2 Submarkets)
    # =======================================================================
    "Inman / Campobello": SubmarketMeta(
        name="Inman / Campobello",
        borough="BLUE_RIDGE_FOOTHILLS",
        lat=35.0460,
        lng=-82.0950,
        zoom=13.5,
        pitch=34.0,
        base_lims=0.70,
        capex=2300000.0,
        permit_vel=14.0,
        shift_ratio=1.20,
        sla=34.0,
        description="Foothills bedroom towns along the SC-9 / SC-11 spine absorbing Greenville-Spartanburg spillover and new single-family subdivisions in the I-26 north corridor.",
        city_id="spartanburg",
    ),
    "Landrum / Chesnee": SubmarketMeta(
        name="Landrum / Chesnee",
        borough="BLUE_RIDGE_FOOTHILLS",
        lat=35.1280,
        lng=-82.0300,
        zoom=13.0,
        pitch=32.0,
        base_lims=0.68,
        capex=2100000.0,
        permit_vel=13.0,
        shift_ratio=1.18,
        sla=32.0,
        description="Northern escarpment hamlets near the Tryon horse-country edge, where estate infill, small-downtown boutiques, and farm-parcel fragmentation drive the permit mix.",
        city_id="spartanburg",
    ),
    # =======================================================================
    # I85_CORRIDOR (2 Submarkets)
    # =======================================================================
    "Greer / Reidville": SubmarketMeta(
        name="Greer / Reidville",
        borough="I85_CORRIDOR",
        lat=34.9130,
        lng=-82.0800,
        zoom=14.0,
        pitch=36.0,
        base_lims=0.78,
        capex=4200000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=46.0,
        description="I-85 inland-port and logistics corridor anchored by BMW-adjacent supplier parks, striking a balance between industrial build-out and fast-growing single-family subdivisions.",
        city_id="spartanburg",
    ),
    "Duncan / Lyman": SubmarketMeta(
        name="Duncan / Lyman",
        borough="I85_CORRIDOR",
        lat=34.9300,
        lng=-82.1350,
        zoom=14.0,
        pitch=36.0,
        base_lims=0.76,
        capex=3900000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=44.0,
        description="Southern I-85 industrial core (Trough Road / Reidville Road reach) with heavy warehouse, cold-chain, and flex permitting around the county's biggest employment nodes.",
        city_id="spartanburg",
    ),
    # =======================================================================
    # SOUTH_COUNTY (2 Submarkets)
    # =======================================================================
    "Woodruff": SubmarketMeta(
        name="Woodruff",
        borough="SOUTH_COUNTY",
        lat=34.7390,
        lng=-82.0320,
        zoom=13.5,
        pitch=34.0,
        base_lims=0.66,
        capex=1900000.0,
        permit_vel=12.0,
        shift_ratio=1.16,
        sla=30.0,
        description="Southern agricultural county seat on the Enoree, anchored by a regional industrial park and steady small-town Main Street refit activity.",
        city_id="spartanburg",
    ),
    "Roebuck": SubmarketMeta(
        name="Roebuck",
        borough="SOUTH_COUNTY",
        lat=34.8780,
        lng=-81.9620,
        zoom=13.5,
        pitch=33.0,
        base_lims=0.69,
        capex=2500000.0,
        permit_vel=15.0,
        shift_ratio=1.24,
        sla=36.0,
        description="South-east county unincorporated belt spreading from the Dorman Centre retail node, mixing subdivision infill, ranch-plus-acreage, and neighborhood-shopping refit.",
        city_id="spartanburg",
    ),
}


# ---------------------------------------------------------------------------
# Spartanburg Divisions Catalog
# ---------------------------------------------------------------------------

SPARTANBURG_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=34.9490,
        center_lng=-81.9320,
        zoom=14.5,
        bbox=SPARTANBURG_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in SPARTANBURG_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="spartanburg",
    ),
    "EAST_CITY": BoroughMeta(
        name="EAST_CITY",
        center_lat=34.9470,
        center_lng=-81.8900,
        zoom=14.0,
        bbox=SPARTANBURG_DIVISION_BBOXES["EAST_CITY"],
        submarkets=[k for k, v in SPARTANBURG_SUBMARKETS.items() if v.borough == "EAST_CITY"],
        city_id="spartanburg",
    ),
    "WEST_CITY": BoroughMeta(
        name="WEST_CITY",
        center_lat=34.9570,
        center_lng=-81.9750,
        zoom=14.0,
        bbox=SPARTANBURG_DIVISION_BBOXES["WEST_CITY"],
        submarkets=[k for k, v in SPARTANBURG_SUBMARKETS.items() if v.borough == "WEST_CITY"],
        city_id="spartanburg",
    ),
    "BLUE_RIDGE_FOOTHILLS": BoroughMeta(
        name="BLUE_RIDGE_FOOTHILLS",
        center_lat=35.0600,
        center_lng=-82.1000,
        zoom=12.5,
        bbox=SPARTANBURG_DIVISION_BBOXES["BLUE_RIDGE_FOOTHILLS"],
        submarkets=[k for k, v in SPARTANBURG_SUBMARKETS.items() if v.borough == "BLUE_RIDGE_FOOTHILLS"],
        city_id="spartanburg",
    ),
    "I85_CORRIDOR": BoroughMeta(
        name="I85_CORRIDOR",
        center_lat=34.9200,
        center_lng=-82.1000,
        zoom=12.5,
        bbox=SPARTANBURG_DIVISION_BBOXES["I85_CORRIDOR"],
        submarkets=[k for k, v in SPARTANBURG_SUBMARKETS.items() if v.borough == "I85_CORRIDOR"],
        city_id="spartanburg",
    ),
    "SOUTH_COUNTY": BoroughMeta(
        name="SOUTH_COUNTY",
        center_lat=34.7800,
        center_lng=-81.9500,
        zoom=12.0,
        bbox=SPARTANBURG_DIVISION_BBOXES["SOUTH_COUNTY"],
        submarkets=[k for k, v in SPARTANBURG_SUBMARKETS.items() if v.borough == "SOUTH_COUNTY"],
        city_id="spartanburg",
    ),
}

SPARTANBURG_DIVISION_BBOXES_ALIAS = SPARTANBURG_DIVISION_BBOXES
SPARTANBURG_SUBMARKETS_ALIAS = SPARTANBURG_SUBMARKETS
SPARTANBURG_DIVISIONS_ALIAS = SPARTANBURG_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed and re-verified live 2026-08-28 against the county's single EnerGov
# FeatureServer layer. Two live corrections over the confirmed probe facts:
# the service root is /server/rest/services (the /arcgis prefix 404s) and the
# host is ANSI-date-literal for the ApplicationDate watermark.
# ---------------------------------------------------------------------------
SPARTANBURG_FEATURESERVER_URL = (
    "https://maps.spartanburgcounty.org/server/rest/services/"
    "EnerGov/EnerGov_Spatial_Collections/FeatureServer/5"
)

SPARTANBURG_PERMITS_ENDPOINT = SPARTANBURG_FEATURESERVER_URL
SPARTANBURG_SLA_ENDPOINT = SPARTANBURG_FEATURESERVER_URL

SPARTANBURG_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": SPARTANBURG_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ApplicationDate",
        "id_keys": ["CaseNumber", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "needs_geocode": False,
            "order_by": "OBJECTID",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "expected_cadence_days": 1,
            "where": "ModuleName='PermitManagement'",
            "field_map": PERMITS_FIELD_MAP,
            "scope": (
                "Spartanburg County EnerGov permit cases (History Points /5, "
                "native point, outSR=4326). Date-typed ApplicationDate watermark "
                "(same-day live 2026-08-28: newest 2026-08-28T16:08:53Z; 41,555 "
                "rows; 30d 1,420; 2026 YTD 9,640). NO address columns — "
                "SpatialType='Address' is a server-side geocode flag and the "
                "point is the native source (needs_geocode False, no ADR-0004). "
                "Host is ANSI-date-literal — must register in "
                "ANSI_DATE_LITERAL_HOSTS. id_keys CaseNumber (unique) -> "
                "OBJECTID. job_type reads WorkClass then CaseType (DM/A2 "
                "signals). Single /5 layer shared with the SLA feed; the "
                "ModuleName module filter is load-bearing."
            ),
        },
    },
    "sla": {
        "endpoint": SPARTANBURG_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ApplicationDate",
        "id_keys": ["CaseNumber", "CaseID", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "needs_geocode": False,
            "order_by": "OBJECTID",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "expected_cadence_days": 30,
            "where": "ModuleName IN ('BusinessLicenseEntity','BusinessLicenseManagement')",
            "field_map": SLA_FIELD_MAP,
            "scope": (
                "Spartanburg County EnerGov business-license + entity cases "
                "(History Points /5, native point). Date-typed ApplicationDate "
                "watermark; union newest 2026-07-08T11:55:00Z, total 187 (Entity "
                "79 + Management 108), recent window 0 — a slow trickle (~2-3/mo), "
                "registered at cadence 30 and flagged for orchestrator review. "
                "NO address columns (native point, needs_geocode False). Business-"
                "license Entity rows carry the business NAME as CaseNumber "
                "(byte-verbatim HTML-escaped, e.g. 'Brat &amp; Curry Co'), so the "
                "id chain falls back to the CaseID GUID then OBJECTID. Shared /5 "
                "layer with the permit feed; the ModuleName IN (...) filter is "
                "load-bearing."
            ),
        },
    },
}


def get_spartanburg_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Spartanburg feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (311 has no
    RequestManagement module and deeds are ROD-portal only).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in SPARTANBURG_FEED_SPECS:
        available = ", ".join(sorted(SPARTANBURG_FEED_SPECS))
        raise KeyError(
            f"'{SPARTANBURG_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = SPARTANBURG_FEED_SPECS[feed_name]
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
    metro_bbox=SPARTANBURG_METRO_BBOX,
    division_bboxes=SPARTANBURG_DIVISION_BBOXES,
    submarkets=SPARTANBURG_SUBMARKETS,
    divisions=SPARTANBURG_DIVISIONS,
    contains=is_in_spartanburg_metro,
)

__all__ = [
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SPARTANBURG_CENTER",
    "SPARTANBURG_CITY_ID",
    "SPARTANBURG_DIVISION_BBOXES",
    "SPARTANBURG_DIVISION_BBOXES_ALIAS",
    "SPARTANBURG_DIVISIONS",
    "SPARTANBURG_DIVISIONS_ALIAS",
    "SPARTANBURG_FEATURESERVER_URL",
    "SPARTANBURG_FEED_SPECS",
    "SPARTANBURG_FIELD_MAP",
    "SPARTANBURG_GEOCODE_CONTEXT",
    "SPARTANBURG_METRO_BBOX",
    "SPARTANBURG_PERMITS_ENDPOINT",
    "SPARTANBURG_SLA_ENDPOINT",
    "SPARTANBURG_SUBMARKETS",
    "SPARTANBURG_SUBMARKETS_ALIAS",
    "SLA_FIELD_MAP",
    "REGISTRATION",
    "get_spartanburg_dataset",
    "is_in_spartanburg",
    "is_in_spartanburg_metro",
]
