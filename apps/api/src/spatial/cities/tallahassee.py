GEOCODE_CONTEXT = "Tallahassee, FL"

PERMITS_FIELD_MAP = {
    "job_id": ["PermitNum", "OBJECTID"],
    "job_type": ["PermitTypeMapped", "WorkClassMapped", "WorkClass"],
    "issuance_date": ["IssuedDate"],
    "address_street": ["OriginalAddress1"],
    "bbl": ["PIN"],
    "borough": ["Jurisdiction", "PermitClassMapped"],
    "cost": ["EstProjectCost"],
    "status": ["StatusCurrent", "StatusCurrentMapped"],
}

COMPLAINTS_311_FIELD_MAP = {
    "incident_id": ["SERVNO"],
    "complaint_type": ["PROBDESC", "CATNAME", "DESCRIPT"],
    "created_date": ["CALLDTTM"],
    "closed_date": ["RESDTTM"],
    "incident_address": ["ADDRESS", "LOC"],
    "borough": ["DISTRICT", "COUNTY", "CATNAME"],
    "status": ["RESP", "RESCODE"],
}

DEEDS_FIELD_MAP = {
    "doc_id": ["SALES_SALEKEY", "OBJECTID"],
    "bbl": ["SALES_PARID"],
    "document_amount": ["SALES_PRICE", "SALES_ADJPRICE"],
    "recorded_date": ["SALES_SALEDT", "SALES_RECORDDT"],
    "party1_grantor": ["SALES_OLDOWN", "SALES_OLDOWN2"],
    "party2_grantee": ["SALES_OWN1", "SALES_OWN2"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

"""Tallahassee / Leon County Metro Submarket Registry and Spatial Layer.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the joint City of
Tallahassee / Leon County metro, FL (centered on the state-capitol downtown at
~30.4383, -84.2807; Leon County is the sole county sold-out in this
registration — neither Gadsden to the west, Wakulla to the south, nor
Jefferson to the east is claimed).

Feed scope (probed and re-probed live 2026-08-28,
docs/research/se-probe-tallahassee.md). All three feeds are native-space
point layers on ONE joint City/County ArcGIS Server 10.81 —
``intervector.leoncountyfl.gov``, web-adaptor base
``/intervector/rest/services/MapServices/`` — so the existing ``ArcGISClient``
covers the city with no fifth client:

* PERMITS — ``/MapServer/0`` "Active Building Permits by Type". Watermark
  ``AppliedDate`` (date-typed; newest 2026-08-18, PubDte 2026-08-19T18:00Z).
  Native point, ``outSR=4326``. ``needs_geocode=False``: the ``Latitude``/
  ``Longitude`` attributes are Web Mercator meters (never map); geometry
  supplies WGS84. Cadence 7 (live view; 60d=137, 7d=0 at re-probe). id
  ``PermitNum``.
* COMPLAINTS_311 — ``/MapServer/1`` "All Service Requests" (Infor/PublicWorks
  CRM, open+unresolved plus resolved history). Watermark ``CALLDTTM``
  (date-typed; newest real 2026-08-28T11:03Z, same-day). Native point;
  ``GPSX``/``GPSY`` are FL State Plane North feet (never map). Spec declares
  ``where="CALLDTTM <= CURRENT_TIMESTAMP"`` to exclude the future-dated
  sentinel + scheduled fogging rows (171,552 total -> 171,546 under the
  clause). producer_key "311"; OID field ``ESRI_OID`` (the layer publishes no
  objectIdField and ``orderByFields=OBJECTID`` returns error 400). Cadence 1.
* DEEDS — ``/MapServer/0`` "Sales 2026" (rolling 3-yr set). Watermark
  ``SALES_SALEDT`` (date-typed; newest 2026-08-24). Native parcel-centroid
  point — NO address column and NO ``parcel_join`` needed (the layer already
  serves parcel-centroid geometry). ``needs_geocode=False``; OID field
  ``OBJECTID``. Cadence ~1. id ``SALES_SALEKEY``.
* SLA — absent. No Local Business Tax Receipt dataset anywhere in the org.
  Do not register.

OID/ordering contract (verified live 2026-08-28): no layer publishes an
``objectIdField``. Permits/Deeds carry `OBJECTID` (ordering OK); the 311 layer
carries only ``ESRI_OID`` (``orderByFields=OBJECTID`` returns error 400).
Every spec therefore declares an explicit ``order_by`` and ``oid_field``.
All watermarks are true date columns, so ArcGISClient flattens epoch-ms to ISO
and no ADR-0005 text-watermark declaration is needed.

Host note (spine): ``intervector.leoncountyfl.gov`` is ANSI-date-literal —
a bare ISO string literal 400s (``{"error":{"code":400,...}}``) while the ANSI
``date 'YYYY-MM-DD'`` form works. Added to the spine's
``ANSI_DATE_LITERAL_HOSTS`` set in the stream delta; NOT edited here.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

TALLAHASSEE_CITY_ID: str = "tallahassee"
TALLAHASSEE_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Metro bbox grounded in the live deeds extent (sampled Sales-2026 rows since
# 2026-07-01: lat 30.2997-30.6218, lng -84.6948 - -84.0605), padded to cover
# the Leon County metro. The deep-west / deep-east edges are rural Leon
# (Woodville, Chaires); Tallahassee city sits in the 30.30-30.62 band.
TALLAHASSEE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 30.29,
    "max_lat": 30.63,
    "min_lng": -84.70,
    "max_lng": -84.05,
}

# Registration-contract center: the state-capitol downtown core.
TALLAHASSEE_CENTER: Dict[str, float] = {"lat": 30.4383, "lng": -84.2807}

# 6 Tallahassee Division Bounding Boxes (strictly nested inside the metro bbox).
TALLAHASSEE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_CAPITAL":       {"min_lat": 30.405, "max_lat": 30.450, "min_lng": -84.300, "max_lng": -84.260},
    "MIDTOWN_NORTH":          {"min_lat": 30.455, "max_lat": 30.480, "min_lng": -84.295, "max_lng": -84.270},
    "NORTHEAST_KILLEARN":     {"min_lat": 30.478, "max_lat": 30.545, "min_lng": -84.265, "max_lng": -84.195},
    "NORTHWEST_LAKE_JACKSON": {"min_lat": 30.458, "max_lat": 30.533, "min_lng": -84.390, "max_lng": -84.350},
    "SOUTHSIDE_BOND":         {"min_lat": 30.372, "max_lat": 30.408, "min_lng": -84.288, "max_lng": -84.255},
    "SOUTHEAST_SOUTHWOOD":    {"min_lat": 30.412, "max_lat": 30.440, "min_lng": -84.215, "max_lng": -84.182},
}


def is_in_tallahassee_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Tallahassee metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        TALLAHASSEE_METRO_BBOX["min_lat"] <= lat <= TALLAHASSEE_METRO_BBOX["max_lat"]
        and TALLAHASSEE_METRO_BBOX["min_lng"] <= lng <= TALLAHASSEE_METRO_BBOX["max_lng"]
    )


def is_in_tallahassee(lat: float, lng: float) -> bool:
    """Alias for :func:`is_in_tallahassee_metro`."""
    return is_in_tallahassee_metro(lat, lng)


# ---------------------------------------------------------------------------
# Tallahassee Submarket Registry (10 Submarkets Across 6 Divisions)
# Each submarket's lat/lng is pinned to a real Sales-2026 deed geometry and its
# SALES_PARID is recorded in the description (probe-verified 2026-08-28).
# ---------------------------------------------------------------------------

TALLAHASSEE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CAPITAL (2 Submarkets)
    # =======================================================================
    "Downtown / Capitol": SubmarketMeta(
        name="Downtown / Capitol",
        borough="DOWNTOWN_CAPITAL",
        lat=30.43916,
        lng=-84.28413,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.85,
        capex=5600000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=55.0,
        description="State-capitol core anchoring the city's design, institutional and adaptive-reuse pipeline — pinned to Sales row PARID 2136340006080.",
        city_id="tallahassee",
    ),
    "Myers Park / South Monroe": SubmarketMeta(
        name="Myers Park / South Monroe",
        borough="DOWNTOWN_CAPITAL",
        lat=30.41057,
        lng=-84.27399,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.72,
        capex=2600000.0,
        permit_vel=18.0,
        shift_ratio=1.26,
        sla=40.0,
        description="Historic bungalow grid and the South Monroe commercial corridor with steady fix-and-flip turnover — pinned to Sales row PARID 310775  E0130.",
        city_id="tallahassee",
    ),
    # =======================================================================
    # MIDTOWN_NORTH (2 Submarkets)
    # =======================================================================
    "Midtown": SubmarketMeta(
        name="Midtown",
        borough="MIDTOWN_NORTH",
        lat=30.46439,
        lng=-84.29130,
        zoom=14.5,
        pitch=42.0,
        base_lims=0.80,
        capex=4200000.0,
        permit_vel=24.0,
        shift_ratio=1.34,
        sla=48.0,
        description="Walkable densest retail/craft-hosts district north of downtown anchored by Lake Ella — pinned to Sales row PARID 212360  E0040.",
        city_id="tallahassee",
    ),
    "Lafayette / North Monroe": SubmarketMeta(
        name="Lafayette / North Monroe",
        borough="MIDTOWN_NORTH",
        lat=30.47220,
        lng=-84.27865,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.74,
        capex=3300000.0,
        permit_vel=20.0,
        shift_ratio=1.28,
        sla=42.0,
        description="Residential-commercial seam along the North Monroe / US-27 corridor with office-to-residence conversions — pinned to Sales row PARID 212423  10060.",
        city_id="tallahassee",
    ),
    # =======================================================================
    # NORTHEAST_KILLEARN (2 Submarkets)
    # =======================================================================
    "Killearn Lakes": SubmarketMeta(
        name="Killearn Lakes",
        borough="NORTHEAST_KILLEARN",
        lat=30.53835,
        lng=-84.21013,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.82,
        capex=3900000.0,
        permit_vel=26.0,
        shift_ratio=1.36,
        sla=46.0,
        description="Master-planned northeast set of lakeside subdivisions drawing the metro's higher-value move-up trades — pinned to Sales row PARID 142560 AS0050.",
        city_id="tallahassee",
    ),
    "Betton Hills / Buckhead": SubmarketMeta(
        name="Betton Hills / Buckhead",
        borough="NORTHEAST_KILLEARN",
        lat=30.48527,
        lng=-84.25132,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.78,
        capex=3600000.0,
        permit_vel=22.0,
        shift_ratio=1.30,
        sla=44.0,
        description="Leafy mid-century residential district and the Buckhead commercial node along Thomasville Road — pinned to Sales row PARID 111790  A0180.",
        city_id="tallahassee",
    ),
    # =======================================================================
    # NORTHWEST_LAKE_JACKSON (2 Submarkets)
    # =======================================================================
    "Lake Jackson": SubmarketMeta(
        name="Lake Jackson",
        borough="NORTHWEST_LAKE_JACKSON",
        lat=30.52554,
        lng=-84.38255,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.80,
        capex=3700000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=45.0,
        description="Lake-lined northwest subdivisions on the Bannerman Road corridor with estate infill — pinned to Sales row PARID 253622  B0040.",
        city_id="tallahassee",
    ),
    "West Tallahassee / Jackson Bluff": SubmarketMeta(
        name="West Tallahassee / Jackson Bluff",
        borough="NORTHWEST_LAKE_JACKSON",
        lat=30.46353,
        lng=-84.36692,
        zoom=13.5,
        pitch=32.0,
        base_lims=0.68,
        capex=2100000.0,
        permit_vel=16.0,
        shift_ratio=1.22,
        sla=36.0,
        description="Jackson Bluff Road industrial and working-edge corridor absorbing code-enforcement and repair demand — pinned to Sales row PARID 211941  B0070.",
        city_id="tallahassee",
    ),
    # =======================================================================
    # SOUTHSIDE_BOND (1 Submarket)
    # =======================================================================
    "Southside / Bond": SubmarketMeta(
        name="Southside / Bond",
        borough="SOUTHSIDE_BOND",
        lat=30.38206,
        lng=-84.27208,
        zoom=14.0,
        pitch=35.0,
        base_lims=0.70,
        capex=2200000.0,
        permit_vel=17.0,
        shift_ratio=1.24,
        sla=38.0,
        description="South Monroe and Southside commercial-industrial pocket with investor-led single-family turnover — pinned to Sales row PARID 311930  C0010.",
        city_id="tallahassee",
    ),
    # =======================================================================
    # SOUTHEAST_SOUTHWOOD (1 Submarket)
    # =======================================================================
    "Southwood": SubmarketMeta(
        name="Southwood",
        borough="SOUTHEAST_SOUTHWOOD",
        lat=30.42630,
        lng=-84.19719,
        zoom=14.0,
        pitch=38.0,
        base_lims=0.76,
        capex=3000000.0,
        permit_vel=21.0,
        shift_ratio=1.30,
        sla=41.0,
        description="New-urbanist planned community off Tram Road and the SE growth corridor with steady new-construction and resale velocity — pinned to Sales row PARID 310270  A0270.",
        city_id="tallahassee",
    ),
}


# ---------------------------------------------------------------------------
# Tallahassee Divisions Catalog
# ---------------------------------------------------------------------------

TALLAHASSEE_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CAPITAL": BoroughMeta(
        name="DOWNTOWN_CAPITAL",
        center_lat=30.4275,
        center_lng=-84.2800,
        zoom=14.5,
        bbox=TALLAHASSEE_DIVISION_BBOXES["DOWNTOWN_CAPITAL"],
        submarkets=[k for k, v in TALLAHASSEE_SUBMARKETS.items() if v.borough == "DOWNTOWN_CAPITAL"],
        city_id="tallahassee",
    ),
    "MIDTOWN_NORTH": BoroughMeta(
        name="MIDTOWN_NORTH",
        center_lat=30.4680,
        center_lng=-84.2820,
        zoom=14.0,
        bbox=TALLAHASSEE_DIVISION_BBOXES["MIDTOWN_NORTH"],
        submarkets=[k for k, v in TALLAHASSEE_SUBMARKETS.items() if v.borough == "MIDTOWN_NORTH"],
        city_id="tallahassee",
    ),
    "NORTHEAST_KILLEARN": BoroughMeta(
        name="NORTHEAST_KILLEARN",
        center_lat=30.5100,
        center_lng=-84.2300,
        zoom=13.5,
        bbox=TALLAHASSEE_DIVISION_BBOXES["NORTHEAST_KILLEARN"],
        submarkets=[k for k, v in TALLAHASSEE_SUBMARKETS.items() if v.borough == "NORTHEAST_KILLEARN"],
        city_id="tallahassee",
    ),
    "NORTHWEST_LAKE_JACKSON": BoroughMeta(
        name="NORTHWEST_LAKE_JACKSON",
        center_lat=30.4900,
        center_lng=-84.3700,
        zoom=13.5,
        bbox=TALLAHASSEE_DIVISION_BBOXES["NORTHWEST_LAKE_JACKSON"],
        submarkets=[k for k, v in TALLAHASSEE_SUBMARKETS.items() if v.borough == "NORTHWEST_LAKE_JACKSON"],
        city_id="tallahassee",
    ),
    "SOUTHSIDE_BOND": BoroughMeta(
        name="SOUTHSIDE_BOND",
        center_lat=30.3900,
        center_lng=-84.2700,
        zoom=13.5,
        bbox=TALLAHASSEE_DIVISION_BBOXES["SOUTHSIDE_BOND"],
        submarkets=[k for k, v in TALLAHASSEE_SUBMARKETS.items() if v.borough == "SOUTHSIDE_BOND"],
        city_id="tallahassee",
    ),
    "SOUTHEAST_SOUTHWOOD": BoroughMeta(
        name="SOUTHEAST_SOUTHWOOD",
        center_lat=30.4260,
        center_lng=-84.1980,
        zoom=13.5,
        bbox=TALLAHASSEE_DIVISION_BBOXES["SOUTHEAST_SOUTHWOOD"],
        submarkets=[k for k, v in TALLAHASSEE_SUBMARKETS.items() if v.borough == "SOUTHEAST_SOUTHWOOD"],
        city_id="tallahassee",
    ),
}

TLH_DIVISION_BBOXES = TALLAHASSEE_DIVISION_BBOXES
TLH_SUBMARKETS = TALLAHASSEE_SUBMARKETS
TLH_DIVISIONS = TALLAHASSEE_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed and re-probed live 2026-08-28 against the joint City/County ArcGIS
# Server at intervector.leoncountyfl.gov (web-adaptor base
# /intervector/rest/services/MapServices/). All three watermarks confirmed
# fresh. No layer publishes an objectIdField: permits/deeds order by OBJECTID,
# the 311 layer by ESRI_OID (OBJECTID 400s on that layer). All three are
# native points with needs_geocode=False — geometry (outSR=4326) supplies the
# coordinates; the projected Latitude/Longitude (permits, Web Mercer) and
# GPSX/GPSY (311, FL State Plane North feet) attribute columns are NEVER
# mapped.
# ---------------------------------------------------------------------------
_TLH_BASE = (
    "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices"
)

TALLAHASSEE_PERMITS_ENDPOINT = f"{_TLH_BASE}/TLC_OverlayPermitsActive_D_WM/MapServer/0"
TALLAHASSEE_311_ENDPOINT = f"{_TLH_BASE}/LCPW_InforServiceRequest_D_WM/MapServer/1"
TALLAHASSEE_DEEDS_ENDPOINT = f"{_TLH_BASE}/LCPA_Last3YearsSales_D_WM/MapServer/0"

TALLAHASSEE_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": TALLAHASSEE_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "AppliedDate",
        "id_keys": ["PermitNum", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "needs_geocode": False,
            "order_by": "OBJECTID",
            "oid_field": "OBJECTID",
            "max_record_count": 8000,
            "expected_cadence_days": 7,
            "scope": (
                "Tallahassee active-building-permits overlay (date-typed "
                "AppliedDate watermark, ISO after client flatten; newest "
                "2026-08-18, PubDte 2026-08-19T18:00Z). Native point; the "
                "Latitude/Longitude attributes are Web Mercator meters, so "
                "coordinates come from the geometry (outSR=4326) and "
                "needs_geocode is False. Layer publishes no objectIdField "
                "but carries OBJECTID. Live view — cadence 7; the overlay is "
                "a snapshot of active permits, so a 7d window can be sparse "
                "(60d=137, 7d=0 at the 2026-08-28 re-probe)."
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "311": {
        "endpoint": TALLAHASSEE_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "CALLDTTM",
        "id_keys": ["SERVNO", "ESRI_OID"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "where": "CALLDTTM <= CURRENT_TIMESTAMP",
            "needs_geocode": False,
            "order_by": "ESRI_OID",
            "oid_field": "ESRI_OID",
            "max_record_count": 1000,
            "expected_cadence_days": 1,
            "scope": (
                "Tallahassee / Leon County Infor PublicWorks service-request "
                "layer (date-typed CALLDTTM watermark; newest real "
                "2026-08-28T11:03Z, same-day). Spec where excludes the "
                "future-dated sentinel and scheduled mosquito-fogging rows "
                "(171,552 total -> 171,546 under the clause). Native point; "
                "GPSX/GPSY are FL State Plane North feet — coordinates come "
                "from the geometry and needs_geocode is False. OID column is "
                "ESRI_OID (orderByFields=OBJECTID 400s on this layer). "
                "SERVNO is the integer request id."
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
    "deeds": {
        "endpoint": TALLAHASSEE_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "SALES_SALEDT",
        "id_keys": ["SALES_SALEKEY", "OBJECTID"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            "needs_geocode": False,
            "order_by": "OBJECTID",
            "oid_field": "OBJECTID",
            "max_record_count": 1000,
            "expected_cadence_days": 1,
            "scope": (
                "Leon County rolling 3-year sales set (native parcel-centroid "
                "point; newest SALES_SALEDT 2026-08-24, 60d=912, 7d=11 at the "
                "2026-08-28 re-probe). NO address column and NO parcel_join — "
                "the layer already serves parcel-centroid geometry, so "
                "needs_geocode is False. SALES_SALEKEY is the per-sale id "
                "(SALES_INSTRUNO/SALES_TRANSNO are NULL across the newest "
                "batch). SALES_PARID (space-padded fixed-width) is the bbl, "
                "kept verbatim; doc_type left unmapped so it defaults to "
                "DEED. Layer publishes no objectIdField but carries OBJECTID."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_tallahassee_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Tallahassee feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent (SLA has no
    BTR dataset in the org).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in TALLAHASSEE_FEED_SPECS:
        available = ", ".join(sorted(TALLAHASSEE_FEED_SPECS))
        raise KeyError(
            f"'{TALLAHASSEE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = TALLAHASSEE_FEED_SPECS[feed_name]
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
    metro_bbox=TALLAHASSEE_METRO_BBOX,
    division_bboxes=TALLAHASSEE_DIVISION_BBOXES,
    submarkets=TALLAHASSEE_SUBMARKETS,
    divisions=TALLAHASSEE_DIVISIONS,
    contains=is_in_tallahassee_metro,
)

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "REGISTRATION",
    "TLH_DIVISIONS",
    "TLH_DIVISION_BBOXES",
    "TLH_SUBMARKETS",
    "TALLAHASSEE_311_ENDPOINT",
    "TALLAHASSEE_CENTER",
    "TALLAHASSEE_CITY_ID",
    "TALLAHASSEE_DEEDS_ENDPOINT",
    "TALLAHASSEE_DIVISIONS",
    "TALLAHASSEE_DIVISION_BBOXES",
    "TALLAHASSEE_FEED_SPECS",
    "TALLAHASSEE_GEOCODE_CONTEXT",
    "TALLAHASSEE_METRO_BBOX",
    "TALLAHASSEE_PERMITS_ENDPOINT",
    "TALLAHASSEE_SUBMARKETS",
    "get_tallahassee_dataset",
    "is_in_tallahassee",
    "is_in_tallahassee_metro",
]
