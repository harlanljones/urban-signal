GEOCODE_CONTEXT = "Lynchburg, VA"

PERMITS_FIELD_MAP = {
    "job_id": ["RecordNo", "OBJECTID"],
    "job_type": ["SubType", "Type"],
    "issuance_date": ["StartDate"],
    "address_street": ["Address"],
    "bbl": ["ParcelID"],
    "borough": ["Neighborhood"],
    "cost": ["JobValue"],
    "status": ["Status"],
}

SLA_FIELD_MAP = {
    "license_id": ["LicenseNumber", "Company", "TradeName"],
    "dba": ["TradeName", "Company"],
    "premises_name": ["Company"],
    "license_type": ["BusinessType"],
    "effective_date": ["LicenseIssued"],
    "expiration_date": ["LicenseExpires"],
    "address_street": ["MailAddress1"],
    "zipcode": ["MailZip"],
    "status": ["Status"],
}

DEEDS_FIELD_MAP = {
    "doc_id": ["DocumentNo", "ESRI_OID"],
    "bbl": ["LRSN"],
    "document_amount": ["SaleAmount"],
    "recorded_date": ["SaleDate"],
    "party1_grantor": ["Seller"],
    "party2_grantee": ["Buyer"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

"""Lynchburg Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the independent City of
Lynchburg, VA (settled on the James River fall line between the Blue Ridge
and the Piedmont — an independent city bordered by Amherst, Campbell, and
Bedford counties, none of whose seats this module's box claims).

Feed scope (probed 2026-08-27/28, docs/research/probe-lynchburg_va.md;
re-probed live 2026-08-28 at implementation). All three feeds are non-
spatial tables on ONE city ArcGIS Server — ``mapviewer.lynchburgva.gov``
``OpenData/ODPDynamic/MapServer`` (v10.91, the SDE service behind
data.cityoflynchburg.opendata.arcgis.com) — so the existing
``ArcGISClient`` covers the city with no fifth client:

* PERMITS — ``/37`` "Building Permits - Tabluar" (the city's own layer-name
  typo). TRAKiT export, watermark ``StartDate`` (date-typed). Native-point
  ``/18`` Locations layer shares the ``RecordNo`` key (49,076 of 49,757
  rows) and is the T1 upgrade path; the tabular layer is registered
  address-only (ADR 0004). Status vocabulary spans APPROVED/FINALED/
  EXPIRED/IN REVIEW — registered whole, no server-side status filter.
* SLA — ``/33`` Business Licenses - Tabular. Watermark ``LicenseIssued``
  (date-typed); annual licenses renew mid-year, so the register is a
  trickle by nature (7d=1 at re-probe). Native-point ``/2`` Locations
  layer (``ConcatenatedAddress``, same ``LicenseNumber``) is the T1 path.
* DEEDS — ``/34`` Transfers - Tabular. Watermark ``SaleDate`` (date-typed,
  same-day live: newest row 2026-08-26, 7d=38). NO address column —
  coordinates come from the spec's ``parcel_join`` (``LRSN`` → the ``/41``
  Parcel polygons, centroid source) applied by the deeds ``run_stream``
  enrichment step (DC precedent); ADR 0004 is the lossless fallback.
* COMPLAINTS_311 — absent. The 51-layer service has no citizen-request
  layer; TRAKiT Violation Cases is code enforcement (``ZON26-…``), a
  different family. Do not register.

OID/ordering contract (verified live 2026-08-28): layers ``/37`` and
``/33`` carry an ``OBJECTID`` OID field, but layer ``/34`` publishes NO
``objectIdField`` in its layer JSON and its OID column is ``ESRI_OID`` —
``orderByFields=OBJECTID`` returns ArcGIS error 400. The deeds spec
therefore declares ``order_by="ESRI_OID"`` (the only kwarg the arcgis
adapter forwards) and ``oid_field="ESRI_OID"``. All three watermarks are
true date columns, so ArcGISClient flattens epoch-ms to ISO and no
ADR-0005 text-watermark declaration is needed. Plain ISO string
comparisons (``StartDate >= '2026-08-26T00:00:00+00:00'``) verify working
against this host — no ANSI-date-literal host entry required.

Implementation re-probe (2026-08-28, live, all three watermarks confirmed):
PERMITS newest StartDate 2026-08-26 (COM26-00293 / COM26-00381 /
RES26-00798), total 49,757, 7d 36, Aug 134. SLA newest LicenseIssued
2026-08-21 (031386 Needle Ninja LLC, 924 Main St), total 2,182, 7d 1,
typed-2026 102 — the probe's "2026 YTD 77" was a narrower cohort window,
not the true YTD. DEEDS newest SaleDate 2026-08-26 (DocNo 260000257, a $0
will conveyance split across two LRSNs), total 195,460, 7d 38 — the
circuit-court pull is live at weekly-to-daily cadence. SaleAmount 0 non-
arms-length transfers are kept.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

LYNCHBURG_CITY_ID: str = "lynchburg"
LYNCHBURG_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Independent-city bbox, grounded in the live /41 Parcel-layer extent
# (returnExtentOnly, outSR=4326): lat 37.3326-37.4694, lng -79.2714 -
# -79.0850, padded to the hundredth. The James River (Amherst line) is the
# north edge; Campbell County the south and east; Bedford County (and the
# Forest census area) the west.
LYNCHBURG_METRO_BBOX: Dict[str, float] = {
    "min_lat": 37.33,
    "max_lat": 37.47,
    "min_lng": -79.28,
    "max_lng": -79.08,
}

# Registration-contract center: Downtown Lynchburg (Court Street hill).
LYNCHBURG_CENTER: Dict[str, float] = {"lat": 37.4135, "lng": -79.1422}

# 3 Lynchburg Division Bounding Boxes (strictly nested inside the metro bbox)
LYNCHBURG_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_RIVERFRONT": {"min_lat": 37.400, "max_lat": 37.435, "min_lng": -79.165, "max_lng": -79.125},
    "SOUTH_SIDE":          {"min_lat": 37.375, "max_lat": 37.412, "min_lng": -79.195, "max_lng": -79.155},
    "WEST_END":            {"min_lat": 37.385, "max_lat": 37.445, "min_lng": -79.230, "max_lng": -79.185},
}


def is_in_lynchburg_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Lynchburg metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        LYNCHBURG_METRO_BBOX["min_lat"] <= lat <= LYNCHBURG_METRO_BBOX["max_lat"]
        and LYNCHBURG_METRO_BBOX["min_lng"] <= lng <= LYNCHBURG_METRO_BBOX["max_lng"]
    )


def is_in_lynchburg(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_lynchburg_metro`."""
    return is_in_lynchburg_metro(lat, lng)


# ---------------------------------------------------------------------------
# Lynchburg Submarket Registry (7 Submarkets Across 3 Divisions)
# ---------------------------------------------------------------------------

LYNCHBURG_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_RIVERFRONT (2 Submarkets)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_RIVERFRONT",
        lat=37.4135,
        lng=-79.1422,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.45,
        sla=55.0,
        description="Court Street hill to Main Street commercial core with the city's densest renovation pipeline: upper-floor apartment conversions, facade grants, and institutional anchors.",
        city_id="lynchburg",
    ),
    "Riverfront": SubmarketMeta(
        name="Riverfront",
        borough="DOWNTOWN_RIVERFRONT",
        lat=37.4095,
        lng=-79.1390,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.82,
        capex=4600000.0,
        permit_vel=26.0,
        shift_ratio=1.40,
        sla=50.0,
        description="James River arts-and-amphitheater district below Ninth Street where mill-warehouse stock converts to dining, lofts, and riverwalk-adjacent hospitality.",
        city_id="lynchburg",
    ),
    # =======================================================================
    # SOUTH_SIDE (3 Submarkets)
    # =======================================================================
    "Diamond Hill": SubmarketMeta(
        name="Diamond Hill",
        borough="SOUTH_SIDE",
        lat=37.4055,
        lng=-79.1585,
        zoom=14.5,
        pitch=38.0,
        base_lims=0.72,
        capex=2600000.0,
        permit_vel=18.0,
        shift_ratio=1.26,
        sla=40.0,
        description="Historic brick rowhouse district on the hill southwest of downtown with investor-led restoration and first-time-buyer turnover.",
        city_id="lynchburg",
    ),
    "Tinbridge Hill": SubmarketMeta(
        name="Tinbridge Hill",
        borough="SOUTH_SIDE",
        lat=37.4035,
        lng=-79.1755,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.68,
        capex=2100000.0,
        permit_vel=15.0,
        shift_ratio=1.22,
        sla=36.0,
        description="Working residential grid between Federal Street and the Miller Park edge with steady repair-trade permitting and infill interest.",
        city_id="lynchburg",
    ),
    "Heritage": SubmarketMeta(
        name="Heritage",
        borough="SOUTH_SIDE",
        lat=37.3860,
        lng=-79.1850,
        zoom=14.0,
        pitch=32.0,
        base_lims=0.66,
        capex=1900000.0,
        permit_vel=14.0,
        shift_ratio=1.20,
        sla=34.0,
        description="Wards Road corridor neighborhoods around the Heritage schools and the airport commercial strip, absorbing medical-office and retail refit demand.",
        city_id="lynchburg",
    ),
    # =======================================================================
    # WEST_END (2 Submarkets)
    # =======================================================================
    "Boonsboro": SubmarketMeta(
        name="Boonsboro",
        borough="WEST_END",
        lat=37.4295,
        lng=-79.1985,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.80,
        capex=3900000.0,
        permit_vel=22.0,
        shift_ratio=1.36,
        sla=48.0,
        description="Affluent Boonsboro Road corridor of estate infill, Peaks View-adjacent subdivisions, and the Link Road retail node.",
        city_id="lynchburg",
    ),
    "Wyndhurst": SubmarketMeta(
        name="Wyndhurst",
        borough="WEST_END",
        lat=37.3985,
        lng=-79.2090,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.78,
        capex=3500000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=46.0,
        description="Master-planned new-urbanist district off Lakeside Drive mixing tract build-out, the Wyndhurst Industrial Corridor's flex space, and Liberty University spillover.",
        city_id="lynchburg",
    ),
}


# ---------------------------------------------------------------------------
# Lynchburg Divisions Catalog
# ---------------------------------------------------------------------------

LYNCHBURG_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_RIVERFRONT": BoroughMeta(
        name="DOWNTOWN_RIVERFRONT",
        center_lat=37.4120,
        center_lng=-79.1420,
        zoom=14.5,
        bbox=LYNCHBURG_DIVISION_BBOXES["DOWNTOWN_RIVERFRONT"],
        submarkets=[k for k, v in LYNCHBURG_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIVERFRONT"],
        city_id="lynchburg",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=37.3980,
        center_lng=-79.1730,
        zoom=13.5,
        bbox=LYNCHBURG_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in LYNCHBURG_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="lynchburg",
    ),
    "WEST_END": BoroughMeta(
        name="WEST_END",
        center_lat=37.4140,
        center_lng=-79.2040,
        zoom=13.5,
        bbox=LYNCHBURG_DIVISION_BBOXES["WEST_END"],
        submarkets=[k for k, v in LYNCHBURG_SUBMARKETS.items() if v.borough == "WEST_END"],
        city_id="lynchburg",
    ),
}

LYN_DIVISION_BBOXES = LYNCHBURG_DIVISION_BBOXES
LYN_SUBMARKETS = LYNCHBURG_SUBMARKETS
LYN_DIVISIONS = LYNCHBURG_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27/28 and re-probed live 2026-08-28 against the city's
# single ODPDynamic MapServer. All three watermarks confirmed fresh. Two
# live corrections over the probe: layer /34 publishes no objectIdField
# (its OID column is ESRI_OID; OBJECTID ordering 400s) and the SLA
# typed-2026 count is 102, not the probe's "2026 YTD 77".
# ---------------------------------------------------------------------------
_LYNCHBURG_ODP_BASE = (
    "https://mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer"
)

LYNCHBURG_PERMITS_ENDPOINT = f"{_LYNCHBURG_ODP_BASE}/37"
LYNCHBURG_SLA_ENDPOINT = f"{_LYNCHBURG_ODP_BASE}/33"
LYNCHBURG_DEEDS_ENDPOINT = f"{_LYNCHBURG_ODP_BASE}/34"
# T1 parcel-join path for the address-less Transfers table (Path A).
LYNCHBURG_PARCEL_LAYER_ENDPOINT = f"{_LYNCHBURG_ODP_BASE}/41"

LYNCHBURG_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": LYNCHBURG_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "StartDate",
        "id_keys": ["RecordNo", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "needs_geocode": True,
            "geocode_context": LYNCHBURG_GEOCODE_CONTEXT,
            "order_by": "OBJECTID",
            "oid_field": "OBJECTID",
            "max_record_count": 50000,
            "expected_cadence_days": 1,
            "non_spatial": True,
            "scope": (
                "Lynchburg TRAKiT building-permit table (date-typed "
                "StartDate watermark, ISO after client flatten). "
                "Address-only on the tabular layer (ADR-0004); the "
                "/18 Locations point layer keyed by RecordNo is the "
                "T1 upgrade path. Registered whole — no server-side "
                "status filter (APPROVED/FINALED/EXPIRED/IN REVIEW)."
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": LYNCHBURG_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "LicenseIssued",
        "id_keys": ["LicenseNumber", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "needs_geocode": True,
            "geocode_context": LYNCHBURG_GEOCODE_CONTEXT,
            "order_by": "OBJECTID",
            "oid_field": "OBJECTID",
            "max_record_count": 50000,
            "expected_cadence_days": 365,
            "non_spatial": True,
            "scope": (
                "Lynchburg business-license table (annual licenses "
                "renewing mid-year — trickle cadence is the register's "
                "nature, not staleness; LicenseExpires runs a year+ "
                "ahead). Date-typed LicenseIssued watermark; "
                "LicenseNumber is a zero-padded string kept verbatim. "
                "Mail-address block is the only tabular address; the "
                "/2 Locations point layer is the T1 upgrade path."
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "deeds": {
        "endpoint": LYNCHBURG_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SaleDate",
        "id_keys": ["LRSN", "DocumentNo"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            "needs_geocode": True,
            "geocode_context": LYNCHBURG_GEOCODE_CONTEXT,
            # Layer /34 publishes NO objectIdField — its OID column is
            # ESRI_OID and orderByFields=OBJECTID returns error 400.
            "order_by": "ESRI_OID",
            "oid_field": "ESRI_OID",
            "max_record_count": 50000,
            "expected_cadence_days": 1,
            "non_spatial": True,
            "parcel_join": {
                "parcel_layer": LYNCHBURG_PARCEL_LAYER_ENDPOINT,
                "join_key": "LRSN",
                "geometry_source": "centroid",
            },
            "scope": (
                "Lynchburg circuit-court property-transfer table "
                "(195k rows, same-day live at the 2026-08-28 "
                "re-probe: newest SaleDate 2026-08-26, 7d=38). NO "
                "address column: coordinates arrive via the LRSN -> "
                "/41 Parcel polygon centroid join (parcel_join, DC "
                "precedent) with ADR-0004 as the lossless fallback. "
                "Layer publishes no objectIdField — ESRI_OID ordering "
                "is mandatory. SaleAmount 0 non-arms-length transfers "
                "(wills, family conveyances) are kept; DocumentNo "
                "repeats across LRSN splits of one instrument."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_lynchburg_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Lynchburg feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent (311 has no municipal CRM extract in the ODPDynamic service).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in LYNCHBURG_FEED_SPECS:
        available = ", ".join(sorted(LYNCHBURG_FEED_SPECS))
        raise KeyError(
            f"'{LYNCHBURG_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = LYNCHBURG_FEED_SPECS[feed_name]
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
    metro_bbox=LYNCHBURG_METRO_BBOX,
    division_bboxes=LYNCHBURG_DIVISION_BBOXES,
    submarkets=LYNCHBURG_SUBMARKETS,
    divisions=LYNCHBURG_DIVISIONS,
    contains=is_in_lynchburg_metro,
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "LYN_DIVISIONS",
    "LYN_DIVISION_BBOXES",
    "LYN_SUBMARKETS",
    "LYNCHBURG_CENTER",
    "LYNCHBURG_CITY_ID",
    "LYNCHBURG_DEEDS_ENDPOINT",
    "LYNCHBURG_DIVISIONS",
    "LYNCHBURG_DIVISION_BBOXES",
    "LYNCHBURG_FEED_SPECS",
    "LYNCHBURG_GEOCODE_CONTEXT",
    "LYNCHBURG_METRO_BBOX",
    "LYNCHBURG_PARCEL_LAYER_ENDPOINT",
    "LYNCHBURG_PERMITS_ENDPOINT",
    "LYNCHBURG_SLA_ENDPOINT",
    "LYNCHBURG_SUBMARKETS",
    "PERMITS_FIELD_MAP",
    "REGISTRATION",
    "SLA_FIELD_MAP",
    "get_lynchburg_dataset",
    "is_in_lynchburg",
    "is_in_lynchburg_metro",
]
