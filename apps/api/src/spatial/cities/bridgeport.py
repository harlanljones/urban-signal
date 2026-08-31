"""Bridgeport, CT spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Bridgeport
(Fairfield County, CT).

Bridgeport is a TWO-FEED PARTIAL metro on Connecticut's statewide Socrata portal
(``data.ct.gov``): SLA (State Licenses and Credentials, ``ngch-56tr``) and DEEDS
(Real Estate Sales, ``5mzw-sjtu``). Both are state-level tables filtered to the
city, and both are address-only (no native WGS84 lat/lng read by the shared
producers), so both declare ``needs_geocode=True`` with
``geocode_context="Bridgeport, CT"``. PERMITS / COMPLAINTS_311 are not probed
here — none are registered.

Live-probe caveats that define this leaf (probed 2026-08-30, US-419):

* SLA watermark is ``recordrefreshedon`` (ISO datetime; newest row on the probe
  = 2026-08-30). The feed is the broad statewide eLicensing credentials table
  (2.66M rows statewide; 39,955 for ``city='BRIDGEPORT'``) — rows are
  credentials (gas dealers, repairers, etc.), not hospitality-only. 0 of 39,955
  rows have a null watermark, so no ``IS NOT NULL`` guard is required (unlike
  Buffalo's ``issdttm``). ``credentialid`` is the row identifier.
* DEEDS watermark is ``daterecorded`` (ISO datetime; newest row on the probe =
  2025-09-30, ``listyear`` 2024 — an annual grand-list publication, so the
  watermark lags ~11 months). 0 of 41,036 rows have a null watermark.
  ``serialnumber`` repeats across ``listyear`` (e.g. serialnumber ``10861`` in
  both 2010 and 2001), so ``id_keys = ["serialnumber", "listyear"]``;
  ``(serialnumber, listyear)`` is row-unique.
* Coordinates: native ``geo_coordinates`` is a nested Point (WGS84 ``[lng, lat]``)
  present on 12,574 of 41,036 rows (~30.6%). The shared deeds producer's loc
  fallback does NOT read ``geo_coordinates``, so the feed declares
  ``needs_geocode=True`` and the spine hold should add ``geo_coordinates`` to
  the deeds producer's loc fallback (documented in the field-map module).
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BRIDGEPORT_CITY_ID: str = "bridgeport"

# City of Bridgeport. Permissive enough to hold the Long Island Sound
# waterfront (Black Rock at 41.155 / -73.224, Steel Point/Seaside at -73.175),
# the Beardsley Park / North End line (~41.20), and the East End industrial
# edge at the Stratford line (~-73.16).
BRIDGEPORT_METRO_BBOX: dict[str, float] = {
    "min_lat": 41.135,
    "max_lat": 41.215,
    "min_lng": -73.270,
    "max_lng": -73.150,
}

# 6 Bridgeport divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
BRIDGEPORT_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 41.170,
        "max_lat": 41.190,
        "min_lng": -73.200,
        "max_lng": -73.178,
    },
    "SOUTH_END": {
        "min_lat": 41.150,
        "max_lat": 41.172,
        "min_lng": -73.205,
        "max_lng": -73.180,
    },
    "WEST_SIDE": {
        "min_lat": 41.172,
        "max_lat": 41.192,
        "min_lng": -73.222,
        "max_lng": -73.190,
    },
    "BLACK_ROCK": {
        "min_lat": 41.140,
        "max_lat": 41.165,
        "min_lng": -73.245,
        "max_lng": -73.210,
    },
    "EAST_SIDE": {
        "min_lat": 41.158,
        "max_lat": 41.180,
        "min_lng": -73.200,
        "max_lng": -73.165,
    },
    "NORTH_END": {
        "min_lat": 41.184,
        "max_lat": 41.204,
        "min_lng": -73.205,
        "max_lng": -73.175,
    },
}

def is_in_bridgeport_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Bridgeport city bounds."""
    if lat is None or lng is None:
        return False
    return (
        BRIDGEPORT_METRO_BBOX["min_lat"] <= lat <= BRIDGEPORT_METRO_BBOX["max_lat"]
        and BRIDGEPORT_METRO_BBOX["min_lng"] <= lng <= BRIDGEPORT_METRO_BBOX["max_lng"]
    )

is_in_greater_bridgeport_metro = is_in_bridgeport_metro

BRIDGEPORT_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (1)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN",
        lat=41.1792,
        lng=-73.1894,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.36,
        sla=50.0,
        description="Civic and transit core around Main and State Streets with the Hartford Line station, Housatonic Community College, and adaptive-reuse of the McLevy and Arcade blocks.",
        city_id="bridgeport",
    ),
    # =======================================================================
    # SOUTH_END (1)
    # =======================================================================
    "South End": SubmarketMeta(
        name="South End",
        borough="SOUTH_END",
        lat=41.1620,
        lng=-73.1940,
        zoom=13.5,
        pitch=45.0,
        base_lims=0.72,
        capex=4300000.0,
        permit_vel=24.0,
        shift_ratio=1.30,
        sla=47.0,
        description="Harbor-side residential wedge below downtown with the Seaside Park frontage and long-standing multifamily stock facing light redevelopment.",
        city_id="bridgeport",
    ),
    # =======================================================================
    # WEST_SIDE (2)
    # =======================================================================
    "West Side": SubmarketMeta(
        name="West Side",
        borough="WEST_SIDE",
        lat=41.1800,
        lng=-73.2100,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=4500000.0,
        permit_vel=25.0,
        shift_ratio=1.32,
        sla=48.0,
        description="West Side industrial-residential corridor along the Fairfield line with dense rowhouse stock and the University of Bridgeport campus edge.",
        city_id="bridgeport",
    ),
    "The Hollow": SubmarketMeta(
        name="The Hollow",
        borough="WEST_SIDE",
        lat=41.1820,
        lng=-73.1990,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.70,
        capex=3900000.0,
        permit_vel=23.0,
        shift_ratio=1.28,
        sla=45.0,
        description="Working-class enclave north of I-95 around Coleman and Maplewood Streets with stabilization-level values and small-business corridor reinvestment.",
        city_id="bridgeport",
    ),
    # =======================================================================
    # BLACK_ROCK (1)
    # =======================================================================
    "Black Rock": SubmarketMeta(
        name="Black Rock",
        borough="BLACK_ROCK",
        lat=41.1550,
        lng=-73.2240,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.80,
        capex=5600000.0,
        permit_vel=26.0,
        shift_ratio=1.40,
        sla=52.0,
        description="Historic 19th-century harbor village at the Fairfield line with the St. Mary's-by-the-Sea shore, Black Rock Harbor, and boutique marina-adjacent redevelopment.",
        city_id="bridgeport",
    ),
    # =======================================================================
    # EAST_SIDE (2)
    # =======================================================================
    "East Side": SubmarketMeta(
        name="East Side",
        borough="EAST_SIDE",
        lat=41.1680,
        lng=-73.1900,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.73,
        capex=4400000.0,
        permit_vel=25.0,
        shift_ratio=1.31,
        sla=46.0,
        description="East Main Street corridor with legacy housing stock, the city's densest immigrant commercial streets, and early corridor-street redevelopment groundwork.",
        city_id="bridgeport",
    ),
    "East End": SubmarketMeta(
        name="East End",
        borough="EAST_SIDE",
        lat=41.1700,
        lng=-73.1750,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.71,
        capex=4200000.0,
        permit_vel=22.0,
        shift_ratio=1.29,
        sla=44.0,
        description="Waterfront industrial and residential edge toward the Stratford line, including Steel Point and the Sound-side parcels primed for mixed-use redevelopment.",
        city_id="bridgeport",
    ),
    # =======================================================================
    # NORTH_END (1)
    # =======================================================================
    "North End": SubmarketMeta(
        name="North End",
        borough="NORTH_END",
        lat=41.1940,
        lng=-73.1900,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.76,
        capex=4700000.0,
        permit_vel=24.0,
        shift_ratio=1.33,
        sla=49.0,
        description="North Avenue corridor reaching Beardsley Park and the Trumbull line, with modest suburban-style residential streets and institutional demand.",
        city_id="bridgeport",
    ),
}

BRIDGEPORT_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=41.1792,
        center_lng=-73.1894,
        zoom=13.5,
        bbox=BRIDGEPORT_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in BRIDGEPORT_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="bridgeport",
    ),
    "SOUTH_END": BoroughMeta(
        name="SOUTH_END",
        center_lat=41.1620,
        center_lng=-73.1940,
        zoom=13.5,
        bbox=BRIDGEPORT_DIVISION_BBOXES["SOUTH_END"],
        submarkets=[k for k, v in BRIDGEPORT_SUBMARKETS.items() if v.borough == "SOUTH_END"],
        city_id="bridgeport",
    ),
    "WEST_SIDE": BoroughMeta(
        name="WEST_SIDE",
        center_lat=41.1810,
        center_lng=-73.2045,
        zoom=13.5,
        bbox=BRIDGEPORT_DIVISION_BBOXES["WEST_SIDE"],
        submarkets=[k for k, v in BRIDGEPORT_SUBMARKETS.items() if v.borough == "WEST_SIDE"],
        city_id="bridgeport",
    ),
    "BLACK_ROCK": BoroughMeta(
        name="BLACK_ROCK",
        center_lat=41.1550,
        center_lng=-73.2240,
        zoom=13.5,
        bbox=BRIDGEPORT_DIVISION_BBOXES["BLACK_ROCK"],
        submarkets=[k for k, v in BRIDGEPORT_SUBMARKETS.items() if v.borough == "BLACK_ROCK"],
        city_id="bridgeport",
    ),
    "EAST_SIDE": BoroughMeta(
        name="EAST_SIDE",
        center_lat=41.1690,
        center_lng=-73.1825,
        zoom=13.5,
        bbox=BRIDGEPORT_DIVISION_BBOXES["EAST_SIDE"],
        submarkets=[k for k, v in BRIDGEPORT_SUBMARKETS.items() if v.borough == "EAST_SIDE"],
        city_id="bridgeport",
    ),
    "NORTH_END": BoroughMeta(
        name="NORTH_END",
        center_lat=41.1940,
        center_lng=-73.1900,
        zoom=13.5,
        bbox=BRIDGEPORT_DIVISION_BBOXES["NORTH_END"],
        submarkets=[k for k, v in BRIDGEPORT_SUBMARKETS.items() if v.borough == "NORTH_END"],
        city_id="bridgeport",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed live 2026-08-30. Register SLA + DEEDS ONLY — do not register permits
# or 311 (not probed) or any sibling view.
# ---------------------------------------------------------------------------
BRIDGEPORT_SLA_ENDPOINT = "https://data.ct.gov/resource/ngch-56tr.json"
BRIDGEPORT_DEEDS_ENDPOINT = "https://data.ct.gov/resource/5mzw-sjtu.json"

SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["credentialid", "fullcredentialcode"],
    "license_type": ["credential", "credentialtype"],
    "effective_date": ["effectivedate", "issuedate"],
    "expiration_date": ["expirationdate"],
    "address_street": ["address"],
    "zipcode": ["zip"],
    "borough": ["city"],
    "premises_name": ["businessname", "name"],
    "dba": ["businessname", "name"],
    "status": ["status"],
}

DEEDS_FIELD_MAP: dict[str, list[str]] = {
    "doc_id": ["serialnumber"],
    "recorded_date": ["daterecorded"],
    "document_amount": ["saleamount"],
    "address_street": ["address"],
    "borough": ["town"],
    "doc_type": ["propertytype"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

NATIVE_GEO_COORDINATES: str = "geo_coordinates"

BRIDGEPORT_FEED_SPECS: dict[str, dict[str, object]] = {
    "sla": {
        "endpoint": BRIDGEPORT_SLA_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "recordrefreshedon",
        "id_keys": ["credentialid"],
        "topic_key": "topic_sla",
        "interval_seconds": 3600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "needs_geocode": True,
            "geocode_context": "Bridgeport, CT",
            "where": "city = 'BRIDGEPORT'",
            "order_by": "recordrefreshedon DESC",
            "scope": (
                "Connecticut State Licenses and Credentials (statewide "
                "eLicensing Socrata feed filtered to city = 'BRIDGEPORT'; "
                "39,955 rows; broad credential types incl. gas dealers and "
                "repairers; recordrefreshedon ISO watermark, 0 null rows so no "
                "IS NOT NULL guard; address-only so needs_geocode=True)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "deeds": {
        "endpoint": BRIDGEPORT_DEEDS_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "daterecorded",
        "id_keys": ["serialnumber", "listyear"],
        "topic_key": "topic_deeds",
        "interval_seconds": 3600.0,
        "producer_key": "deeds",
        "extra": {
            "expected_cadence_days": 30,
            "needs_geocode": True,
            "geocode_context": "Bridgeport, CT",
            "where": "town = 'Bridgeport'",
            "order_by": "daterecorded DESC",
            "scope": (
                "Connecticut Real Estate Sales (statewide Socrata feed filtered "
                "to town = 'Bridgeport'; 41,036 rows; daterecorded ISO watermark, "
                "0 null rows; serialnumber repeats across listyear so the id is "
                "the (serialnumber, listyear) pair; native geo_coordinates Point "
                "present on ~30.6% of rows but NOT read by the shared deeds "
                "producer's loc fallback, so needs_geocode=True and the spine "
                "hold should add geo_coordinates to that fallback)"
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}

def get_bridgeport_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Bridgeport feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in BRIDGEPORT_FEED_SPECS:
        available = ", ".join(sorted(BRIDGEPORT_FEED_SPECS))
        raise KeyError(
            f"'{BRIDGEPORT_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = BRIDGEPORT_FEED_SPECS[feed_name]
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
    metro_bbox=BRIDGEPORT_METRO_BBOX,
    division_bboxes=BRIDGEPORT_DIVISION_BBOXES,
    submarkets=BRIDGEPORT_SUBMARKETS,
    divisions=BRIDGEPORT_DIVISIONS,
    contains=is_in_bridgeport_metro,
)

__all__ = [
    "BRIDGEPORT_CITY_ID",
    "BRIDGEPORT_DEEDS_ENDPOINT",
    "BRIDGEPORT_DIVISIONS",
    "BRIDGEPORT_DIVISION_BBOXES",
    "BRIDGEPORT_FEED_SPECS",
    "BRIDGEPORT_METRO_BBOX",
    "BRIDGEPORT_SLA_ENDPOINT",
    "BRIDGEPORT_SUBMARKETS",
    "REGISTRATION",
    "get_bridgeport_dataset",
    "is_in_bridgeport_metro",
    "is_in_greater_bridgeport_metro",
]

