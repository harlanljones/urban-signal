"""Savannah Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the Savannah / Chatham County
metro (coastal Georgia; the Lowcountry's Georgia anchor on the Savannah River,
settled 1733 and laid out on Oglethorpe's garden-bar square plan that survives
intact in the National Historic Landmark District).

Feed scope (probed 2026-08-28, docs/research/se-probe-savannah.md; re-probed live
2026-08-28 at implementation). Savannah is a PARTIAL metro on ONE ArcGIS Server —
the Chatham County SAGIS host ``pub.sagis.org`` ``Savannah/BuildingPermit_FC``
FeatureServer, so the existing ``ArcGISClient`` covers the city with no fifth
client:

* PERMITS — ``/1`` "BuildingPermit_FC" Residential. Watermark ``IssuedDate_DATE``
  (esriFieldTypeDate, epoch-ms; the client flattens to ISO — no ADR-0005 text
  declaration). The text mirror ``IssuedDate`` (``MM/DD/YYYY``) is retained in the
  field map as a secondary issuance candidate. Native-point layer (WKID 2239 GA
  State Plane E ft) served as WGS84 by ``outSR=4326``; the client lifts the point
  onto ``latitude``/``longitude`` so nearly every row carries native coords and
  ADR-0004 address geocoding is the fallback. id_keys ``["PermitNumber","OBJECTID"]``.
  Status vocabulary spans Issued / In Review / Approved — registered whole, no
  server-side status filter. Null ``IssuedDate_DATE`` on In Review / Approved rows
  surfaces at issuance. Register retained to 2023-01 (not rolling). ``ApplicantName``
  is PII and is deliberately unmapped.
* PERMITS (companion) — ``/0`` Commercial, registered only as
  ``companion_endpoints["commercial_building_permits"]`` (SLA-partner pattern, not
  a new FeedType). Same schema as ``/1``, so the same field map serves it; only
  ``PermitType`` differs ("Building Residential Permit" vs "Building Commercial
  Permit").
* COMPLAINTS_311 / SLA / DEEDS — NOT-VIABLE. (311: Oneview public works
  OneView311 trunk = district polygons; the city's CivicPlus 311 is a master
  address registry; Chatham QAlert is reference layers. SLA: no license register;
  STVR_NewData is a zoning overlay + assessor extract. DEEDS: BOA Parcel is the
  assessor roll (Date_Updated 2026-06-22, no grantor); Parcel Digest is annual
  snapshots.) Do not register any of these.

OID/ordering contract (verified live 2026-08-28): both layers publish an
``OBJECTID`` oid field (``objectIdField``) and ``maxRecordCount`` 2000; date
columns discovered are ``IssuedDate_DATE`` and ``FinalizedDate_DATE``. The permits
spec declares ``order_by="OBJECTID"`` / ``oid_field="OBJECTID"`` /
``max_record_count=2000``.

Host quirk: **``pub.sagis.org`` is an ANSI-date-literal ArcGIS host** — a bare
ISO-string date comparison in ``where`` (``IssuedDate_DATE >= '2026-08-21T00:00:00'``)
returns HTTP 400, while the ANSI literal ``IssuedDate_DATE >= DATE '2026-08-21'``
works (verified live). This is a spine change to ``watermarks.py``
``ANSI_DATE_LITERAL_HOSTS`` and is NOT applied here.

Implementation re-probe (2026-08-28, live, both watermarks confirmed): RES newer
IssuedDate_DATE 2026-08-20 (26-07908-BR / 26-06373-BR / 26-08047-BR), total 1933,
7d 0, 60d 294. COM newest IssuedDate_DATE 2026-08-21 (26-00953-BC), total 666,
7d 1, 60d 61. Native point coordinates observed on every sampled row, including
null-issued In Review rows.
"""

from typing import Dict

from src.producers.field_maps_savannah import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SAVANNAH_CITY_ID: str = "savannah"
SAVANNAH_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Metro bbox, grounded in the live layer extent (returnExtentOnly, outSR=4326):
# lat 31.93395-32.18642, lng -81.36534 - -81.04491, padded to the hundredth —
# essentially the Chatham County footprint. The annexed western edge (New
# Hampstead, -81.3505) and the northern Godley Station annexation (32.1814) sit
# inside it.
SAVANNAH_METRO_BBOX: Dict[str, float] = {
    "min_lat": 31.93,
    "max_lat": 32.19,
    "min_lng": -81.37,
    "max_lng": -81.03,
}

# Registration-contract center: Downtown Savannah (Johnson Square / Broughton).
SAVANNAH_CENTER: Dict[str, float] = {"lat": 32.0767, "lng": -81.0943}

# 5 Savannah Division Bounding Boxes (strictly nested inside the metro bbox).
# Division coordinates are grounded in the annexation geometry: the metro's
# northern and western reach come from Godley Station / New Hampstead.
SAVANNAH_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "HISTORIC_CORE":   {"min_lat": 32.045, "max_lat": 32.095, "min_lng": -81.105, "max_lng": -81.045},
    "MIDTOWN":         {"min_lat": 32.030, "max_lat": 32.070, "min_lng": -81.135, "max_lng": -81.060},
    "WEST_SIDE":       {"min_lat": 32.035, "max_lat": 32.095, "min_lng": -81.150, "max_lng": -81.115},
    "SOUTH_SIDE":      {"min_lat": 31.965, "max_lat": 32.060, "min_lng": -81.175, "max_lng": -81.100},
    "WEST_CHATHAM":    {"min_lat": 32.020, "max_lat": 32.190, "min_lng": -81.360, "max_lng": -81.200},
}


def is_in_savannah_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Savannah metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        SAVANNAH_METRO_BBOX["min_lat"] <= lat <= SAVANNAH_METRO_BBOX["max_lat"]
        and SAVANNAH_METRO_BBOX["min_lng"] <= lng <= SAVANNAH_METRO_BBOX["max_lng"]
    )


def is_in_savannah(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_savannah_metro`."""
    return is_in_savannah_metro(lat, lng)


# ---------------------------------------------------------------------------
# Savannah Submarket Registry (10 Submarkets Across 5 Divisions)
# ---------------------------------------------------------------------------

SAVANNAH_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # HISTORIC_CORE (2 Submarkets)
    # =======================================================================
    "Landmark Historic District": SubmarketMeta(
        name="Landmark Historic District",
        borough="HISTORIC_CORE",
        lat=32.0810,
        lng=-81.0918,
        zoom=14.5,
        pitch=45.0,
        base_lims=0.88,
        capex=6800000.0,
        permit_vel=34.0,
        shift_ratio=1.44,
        sla=52.0,
        description="Oglethorpe's garden-bar National Historic Landmark grid from Johnson Square to Broughton: host/conversion capex, adaptive-reuse hospitality, and the tourist retail core.",
        city_id="savannah",
    ),
    "Victorian District": SubmarketMeta(
        name="Victorian District",
        borough="HISTORIC_CORE",
        lat=32.0607,
        lng=-81.0631,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.78,
        capex=4200000.0,
        permit_vel=28.0,
        shift_ratio=1.32,
        sla=44.0,
        description="Post-victorian residential grid radiating east from Bull Street: remodeling, short-term-rental conversion, and the Forsyth Park neighborhood built-out.",
        city_id="savannah",
    ),
    # =======================================================================
    # MIDTOWN (2 Submarkets)
    # =======================================================================
    "Ardsley Park": SubmarketMeta(
        name="Ardsley Park",
        borough="MIDTOWN",
        lat=32.0550,
        lng=-81.0780,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.80,
        capex=3900000.0,
        permit_vel=24.0,
        shift_ratio=1.28,
        sla=48.0,
        description="Early-1900s master-planned historic district of stately brick residences and the Victory Drive / Habersham retail node.",
        city_id="savannah",
    ),
    "Parkside": SubmarketMeta(
        name="Parkside",
        borough="MIDTOWN",
        lat=32.0599,
        lng=-81.1075,
        zoom=13.5,
        pitch=32.0,
        base_lims=0.72,
        capex=2600000.0,
        permit_vel=20.0,
        shift_ratio=1.24,
        sla=38.0,
        description="Midtown residential corridor around Daffin Park and the 36th Street commercial strip with steady repair-trade permitting and infill interest.",
        city_id="savannah",
    ),
    # =======================================================================
    # WEST_SIDE (2 Submarkets)
    # =======================================================================
    "Woodville": SubmarketMeta(
        name="Woodville",
        borough="WEST_SIDE",
        lat=32.0889,
        lng=-81.1418,
        zoom=13.5,
        pitch=32.0,
        base_lims=0.68,
        capex=2300000.0,
        permit_vel=16.0,
        shift_ratio=1.22,
        sla=34.0,
        description="Working residential and industrial-adjacent neighborhoods northwest of downtown near the campus and railyard edge.",
        city_id="savannah",
    ),
    "Liberty City": SubmarketMeta(
        name="Liberty City",
        borough="WEST_SIDE",
        lat=32.0481,
        lng=-81.1279,
        zoom=13.5,
        pitch=30.0,
        base_lims=0.64,
        capex=1900000.0,
        permit_vel=14.0,
        shift_ratio=1.18,
        sla=30.0,
        description="West-side mixed residential block facing the new-construction pipeline along the Walmont redevelopment frontage.",
        city_id="savannah",
    ),
    # =======================================================================
    # SOUTH_SIDE (2 Submarkets)
    # =======================================================================
    "Oglethorpe Mall": SubmarketMeta(
        name="Oglethorpe Mall",
        borough="SOUTH_SIDE",
        lat=32.0058,
        lng=-81.1174,
        zoom=13.5,
        pitch=30.0,
        base_lims=0.70,
        capex=3100000.0,
        permit_vel=22.0,
        shift_ratio=1.26,
        sla=36.0,
        description="Abercorn Expressway retail-and-multifamily corridor anchored by the Oglethorpe Mall area, absorbing strip-refit and buildout demand.",
        city_id="savannah",
    ),
    "Chatham Parkway": SubmarketMeta(
        name="Chatham Parkway",
        borough="SOUTH_SIDE",
        lat=32.0512,
        lng=-81.1655,
        zoom=13.0,
        pitch=32.0,
        base_lims=0.66,
        capex=5200000.0,
        permit_vel=26.0,
        shift_ratio=1.30,
        sla=40.0,
        description="High-capex commercial park at the pooler interchange gateway: hotel, medical-office, and industrial-box erections.",
        city_id="savannah",
    ),
    # =======================================================================
    # WEST_CHATHAM (2 Submarkets)
    # =======================================================================
    "Godley Station": SubmarketMeta(
        name="Godley Station",
        borough="WEST_CHATHAM",
        lat=32.1814,
        lng=-81.2590,
        zoom=13.0,
        pitch=30.0,
        base_lims=0.74,
        capex=4100000.0,
        permit_vel=30.0,
        shift_ratio=1.36,
        sla=42.0,
        description="Master-planned West Chatham annexation on the I-95 / SR-21 corridor with the metro's heaviest new single-family submarket velocity — its permit coordinates set the metro's north edge.",
        city_id="savannah",
    ),
    "New Hampstead": SubmarketMeta(
        name="New Hampstead",
        borough="WEST_CHATHAM",
        lat=32.1300,
        lng=-81.3505,
        zoom=12.5,
        pitch=28.0,
        base_lims=0.68,
        capex=3300000.0,
        permit_vel=24.0,
        shift_ratio=1.28,
        sla=36.0,
        description="Far-west annexed and planned-residential district (pooler-adjacent) whose permit coordinates pin the metro box's western edge.",
        city_id="savannah",
    ),
}


# ---------------------------------------------------------------------------
# Savannah Divisions Catalog
# ---------------------------------------------------------------------------

SAVANNAH_DIVISIONS: Dict[str, BoroughMeta] = {
    "HISTORIC_CORE": BoroughMeta(
        name="HISTORIC_CORE",
        center_lat=32.0777,
        center_lng=-81.0800,
        zoom=14.0,
        bbox=SAVANNAH_DIVISION_BBOXES["HISTORIC_CORE"],
        submarkets=[k for k, v in SAVANNAH_SUBMARKETS.items() if v.borough == "HISTORIC_CORE"],
        city_id="savannah",
    ),
    "MIDTOWN": BoroughMeta(
        name="MIDTOWN",
        center_lat=32.0500,
        center_lng=-81.1000,
        zoom=13.5,
        bbox=SAVANNAH_DIVISION_BBOXES["MIDTOWN"],
        submarkets=[k for k, v in SAVANNAH_SUBMARKETS.items() if v.borough == "MIDTOWN"],
        city_id="savannah",
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=32.0650,
        center_lng=-81.1320,
        zoom=13.5,
        bbox=SAVANNAH_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in SAVANNAH_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id="savannah",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=32.0200,
        center_lng=-81.1300,
        zoom=12.5,
        bbox=SAVANNAH_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in SAVANNAH_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="savannah",
    ),
    "WEST_CHATHAM": BoroughMeta(
        name="WEST_CHATHAM",
        center_lat=32.1050,
        center_lng=-81.2800,
        zoom=12.0,
        bbox=SAVANNAH_DIVISION_BBOXES["WEST_CHATHAM"],
        submarkets=[k for k, v in SAVANNAH_SUBMARKETS.items() if v.borough == "WEST_CHATHAM"],
        city_id="savannah",
    ),
}

SAV_DIVISION_BBOXES = SAVANNAH_DIVISION_BBOXES
SAV_SUBMARKETS = SAVANNAH_SUBMARKETS
SAV_DIVISIONS = SAVANNAH_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed and re-probed live 2026-08-28 on the city's single SAGIS FeatureServer.
# Only PERMITS is registered (partial): /1 Residential is the dataset; /0
# Commercial is the companion endpoint (same schema, not a separate FeedType).
# ---------------------------------------------------------------------------
_SAVANNAH_SAGIS_BASE = (
    "https://pub.sagis.org/arcgis/rest/services/Savannah/BuildingPermit_FC/FeatureServer"
)

SAVANNAH_PERMITS_ENDPOINT = f"{_SAVANNAH_SAGIS_BASE}/1"
SAVANNAH_COMMERCIAL_ENDPOINT = f"{_SAVANNAH_SAGIS_BASE}/0"

SAVANNAH_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": SAVANNAH_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "IssuedDate_DATE",
        "id_keys": ["PermitNumber", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "needs_geocode": True,
            "geocode_context": SAVANNAH_GEOCODE_CONTEXT,
            "order_by": "OBJECTID",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "expected_cadence_days": 7,
            "scope": (
                "Savannah / Chatham County building-permit layer (date-typed "
                "IssuedDate_DATE watermark, ISO after client flatten; text "
                "mirror IssuedDate MM/DD/YYYY is a secondary issuance "
                "candidate). Native-point (WKID 2239 GA State Plane E ft, "
                "served WGS84 by outSR=4326) so most rows carry client-injected "
                "latitude/longitude; ADR-0004 address geocode is the fallback "
                "for the residual coordinate-less rows. Registered whole — no "
                "server-side status filter (Issued / In Review / Approved); "
                "null IssuedDate_DATE surfaces at issuance. Register retained "
                "to 2023-01 (not rolling). ApplicantName is PII — unmapped. "
                "Commercial layer /0 is the companion endpoint "
                "commercial_building_permits (same schema). Host pub.sagis.org "
                "is ANSI-date-literal: where='IssuedDate_DATE >= DATE ...'."
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
}


def get_savannah_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Savannah feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (311 / SLA /
    deeds are all NOT-viable for Savannah — no municipal CRM extract, no
    license register, no grantor-bearing assessor sales source).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in SAVANNAH_FEED_SPECS:
        available = ", ".join(sorted(SAVANNAH_FEED_SPECS))
        raise KeyError(
            f"'{SAVANNAH_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = SAVANNAH_FEED_SPECS[feed_name]
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
    metro_bbox=SAVANNAH_METRO_BBOX,
    division_bboxes=SAVANNAH_DIVISION_BBOXES,
    submarkets=SAVANNAH_SUBMARKETS,
    divisions=SAVANNAH_DIVISIONS,
    contains=is_in_savannah_metro,
)

__all__ = [
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "REGISTRATION",
    "SAV_DIVISIONS",
    "SAV_DIVISION_BBOXES",
    "SAV_SUBMARKETS",
    "SAVANNAH_CENTER",
    "SAVANNAH_CITY_ID",
    "SAVANNAH_COMMERCIAL_ENDPOINT",
    "SAVANNAH_DIVISIONS",
    "SAVANNAH_DIVISION_BBOXES",
    "SAVANNAH_FEED_SPECS",
    "SAVANNAH_GEOCODE_CONTEXT",
    "SAVANNAH_METRO_BBOX",
    "SAVANNAH_PERMITS_ENDPOINT",
    "SAVANNAH_SUBMARKETS",
    "get_savannah_dataset",
    "is_in_savannah",
    "is_in_savannah_metro",
]
