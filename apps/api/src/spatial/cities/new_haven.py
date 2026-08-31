"""New Haven, CT spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of New Haven
(New Haven County, CT).

New Haven is a TWO-FEED metro on Connecticut's statewide Socrata portal
(``data.ct.gov``), reusing the SAME statewide feeds Hartford already carries:

* SLA — State Licenses and Credentials (``ngch-56tr``), Tier 1. A broad
  statewide credentials feed (2.66M rows statewide); ``city='NEW HAVEN'`` is
  a large slice (47,001 rows incl. individual credentials). Watermark
  ``recordrefreshedon`` (ISO datetime, 0 nulls at probe, daily refresh;
  newest 2026-08-30). Consistent with the Hartford precedent — but Hartford's
  inline SLA field_map is STALE (references ``license_number``/
  ``credential_number`` that do not exist live); the CORRECT columns are
  pinned in ``field_maps_new_haven.py``.
* DEEDS — Real Estate Conveyance Tax / property sales (``5mzw-sjtu``), Tier 1.
  Watermark ``daterecorded`` (ISO datetime, 0 nulls at probe). ``serialnumber``
  is NOT row-unique within ``town='New Haven'`` (25,907 distinct vs 25,909
  rows) — it resets across the 22 assessment years, so id_keys are the
  composite ``["serialnumber", "listyear"]``. ``geo_coordinates`` (a Socrata
  Point) is present on 32.5% of rows but is NOT read by the shared deeds
  producer's nested-loc fallback — see the geo note in the FEED_SPECS scope.

Live-probe caveats that define this leaf (probed 2026-08-30, US-419):

* SLA is address-only (no native lat/lng columns) — ``needs_geocode=True``,
  ``geocode_context="New Haven, CT"``. ``recordrefreshedon`` has zero nulls,
  so unlike Buffalo there is NO ``IS NOT NULL`` guard on the watermark.
* DEEDS is also address-only from the producer's view: the native
  ``geo_coordinates`` Point is dropped because the shared
  ``deeds_acris_producer`` nested-loc fallback does not read
  ``geo_coordinates`` (it reads ``the_geom``/``point``/``location``/
  ``georeference``/``shape``/``mappable_latitude_and_longitude``). Declare
  ``needs_geocode=True``; the orchestrator SHOULD add ``geo_coordinates`` to
  that fallback list in the spine hold so native coords are used first.
* DEEDS ``doc_type`` is ``propertytype`` — the property classification
  ("Residential"/"Condo"/"Single Family"), NOT a deed instrument type; there
  is no deed-type column on this feed.
* SLA ``type`` (INDIVIDUAL/BUSINESS/CORPORATION), ``active`` (0/1),
  ``statusreason``, and ``credentialnumber`` ride the wire but are never
  field-map candidates; ``businessname`` exists only on BUSINESS/CORPORATION
  rows so ``premises_name``/``dba`` read ``["businessname", "name"]``.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

NEW_HAVEN_CITY_ID: str = "new_haven"

# City of New Haven. Permissive enough to hold the downtown core around the
# Green (41.3083, -72.9279), the Yale campus spine, Wooster Square on the
# Mill River, East Rock under the bluff, Westville on the Whalley ridge,
# Fair Haven on the Quinnipiac, Dixwell/Newhallville north, and The Hill /
# Long Wharf on the harbor edge.
NEW_HAVEN_METRO_BBOX: dict[str, float] = {
    "min_lat": 41.27,
    "max_lat": 41.35,
    "min_lng": -72.99,
    "max_lng": -72.86,
}

# 6 New Haven divisions. Hand-authored; borough resolution at ingest comes
# from coordinates via get_division_for_coordinate, so bboxes need only be
# sane and contain their own submarket centers.
NEW_HAVEN_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 41.290,
        "max_lat": 41.320,
        "min_lng": -72.940,
        "max_lng": -72.900,
    },
    "EAST_ROCK": {
        "min_lat": 41.315,
        "max_lat": 41.337,
        "min_lng": -72.925,
        "max_lng": -72.890,
    },
    "WESTVILLE": {
        "min_lat": 41.315,
        "max_lat": 41.340,
        "min_lng": -72.990,
        "max_lng": -72.955,
    },
    "FAIR_HAVEN": {
        "min_lat": 41.305,
        "max_lat": 41.335,
        "min_lng": -72.905,
        "max_lng": -72.870,
    },
    "DIXWELL": {
        "min_lat": 41.310,
        "max_lat": 41.340,
        "min_lng": -72.940,
        "max_lng": -72.910,
    },
    "THE_HILL": {
        "min_lat": 41.280,
        "max_lat": 41.300,
        "min_lng": -72.965,
        "max_lng": -72.925,
    },
}

def is_in_new_haven_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the New Haven city bounds."""
    if lat is None or lng is None:
        return False
    return (
        NEW_HAVEN_METRO_BBOX["min_lat"] <= lat <= NEW_HAVEN_METRO_BBOX["max_lat"]
        and NEW_HAVEN_METRO_BBOX["min_lng"] <= lng <= NEW_HAVEN_METRO_BBOX["max_lng"]
    )

is_in_greater_new_haven_metro = is_in_new_haven_metro

NEW_HAVEN_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN",
        lat=41.3083,
        lng=-72.9279,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=34.0,
        shift_ratio=1.48,
        sla=56.0,
        description="Civic and commercial core around the historic New Haven Green with the Chapel Street retail spine, arts venues, and office-to-residential conversion.",
        city_id="new_haven",
    ),
    "Wooster Square": SubmarketMeta(
        name="Wooster Square",
        borough="DOWNTOWN",
        lat=41.2970,
        lng=-72.9120,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=54.0,
        description="Historic Italianate rowhouse district around Wooster Square Park with the frank-pepe pizza anchor, Union Station adjacency, and steady residential rehab.",
        city_id="new_haven",
    ),
    # =======================================================================
    # EAST_ROCK (1)
    # =======================================================================
    "East Rock": SubmarketMeta(
        name="East Rock",
        borough="EAST_ROCK",
        lat=41.3270,
        lng=-72.9050,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.87,
        capex=7100000.0,
        permit_vel=26.0,
        shift_ratio=1.47,
        sla=57.0,
        description="Green-bluff neighborhood of late-19th-century houses on the State Street ridge with the Orange Street corridor and strong owner-occupancy.",
        city_id="new_haven",
    ),
    # =======================================================================
    # WESTVILLE (1)
    # =======================================================================
    "Westville": SubmarketMeta(
        name="Westville",
        borough="WESTVILLE",
        lat=41.3300,
        lng=-72.9770,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=6400000.0,
        permit_vel=22.0,
        shift_ratio=1.42,
        sla=53.0,
        description="West Rock edge village along Whalley Avenue with the Arts Council hub, tree-lined side streets, and the metro's most stable single-family stock.",
        city_id="new_haven",
    ),
    # =======================================================================
    # FAIR_HAVEN (1)
    # =======================================================================
    "Fair Haven": SubmarketMeta(
        name="Fair Haven",
        borough="FAIR_HAVEN",
        lat=41.3210,
        lng=-72.8940,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.74,
        capex=4700000.0,
        permit_vel=27.0,
        shift_ratio=1.46,
        sla=47.0,
        description="Quinnipiac River waterfront neighborhood with the Grand Avenue commercial row, immigrant-led storefront vitality, and stabilization-level reinvestment.",
        city_id="new_haven",
    ),
    # =======================================================================
    # DIXWELL (2)
    # =======================================================================
    "Dixwell": SubmarketMeta(
        name="Dixwell",
        borough="DIXWELL",
        lat=41.3220,
        lng=-72.9340,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.75,
        capex=5000000.0,
        permit_vel=25.0,
        shift_ratio=1.43,
        sla=49.0,
        description="Historic African American neighborhood on the Dixwell Avenue spine with Winchester Avenue corridor infill and mixed-income redevelopment.",
        city_id="new_haven",
    ),
    "Newhallville": SubmarketMeta(
        name="Newhallville",
        borough="DIXWELL",
        lat=41.3310,
        lng=-72.9230,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.72,
        capex=4300000.0,
        permit_vel=24.0,
        shift_ratio=1.40,
        sla=45.0,
        description="North-of-Downtown neighborhood of multi-family and worker housing along Winchester and Shelton Avenues with transit-adjacent redevelopment groundwork.",
        city_id="new_haven",
    ),
    # =======================================================================
    # THE_HILL (1)
    # =======================================================================
    "The Hill": SubmarketMeta(
        name="The Hill",
        borough="THE_HILL",
        lat=41.2900,
        lng=-72.9460,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.71,
        capex=4500000.0,
        permit_vel=23.0,
        shift_ratio=1.38,
        sla=44.0,
        description="Southwest neighborhood around Columbus Avenue with the Trowbridge Square district, Long Wharf adjacency, and early-stage corridor reinvestment.",
        city_id="new_haven",
    ),
}

NEW_HAVEN_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=41.3050,
        center_lng=-72.9200,
        zoom=14.0,
        bbox=NEW_HAVEN_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in NEW_HAVEN_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="new_haven",
    ),
    "EAST_ROCK": BoroughMeta(
        name="EAST_ROCK",
        center_lat=41.3270,
        center_lng=-72.9050,
        zoom=14.0,
        bbox=NEW_HAVEN_DIVISION_BBOXES["EAST_ROCK"],
        submarkets=[k for k, v in NEW_HAVEN_SUBMARKETS.items() if v.borough == "EAST_ROCK"],
        city_id="new_haven",
    ),
    "WESTVILLE": BoroughMeta(
        name="WESTVILLE",
        center_lat=41.3300,
        center_lng=-72.9770,
        zoom=13.5,
        bbox=NEW_HAVEN_DIVISION_BBOXES["WESTVILLE"],
        submarkets=[k for k, v in NEW_HAVEN_SUBMARKETS.items() if v.borough == "WESTVILLE"],
        city_id="new_haven",
    ),
    "FAIR_HAVEN": BoroughMeta(
        name="FAIR_HAVEN",
        center_lat=41.3210,
        center_lng=-72.8940,
        zoom=14.0,
        bbox=NEW_HAVEN_DIVISION_BBOXES["FAIR_HAVEN"],
        submarkets=[k for k, v in NEW_HAVEN_SUBMARKETS.items() if v.borough == "FAIR_HAVEN"],
        city_id="new_haven",
    ),
    "DIXWELL": BoroughMeta(
        name="DIXWELL",
        center_lat=41.3260,
        center_lng=-72.9290,
        zoom=14.0,
        bbox=NEW_HAVEN_DIVISION_BBOXES["DIXWELL"],
        submarkets=[k for k, v in NEW_HAVEN_SUBMARKETS.items() if v.borough == "DIXWELL"],
        city_id="new_haven",
    ),
    "THE_HILL": BoroughMeta(
        name="THE_HILL",
        center_lat=41.2900,
        center_lng=-72.9460,
        zoom=14.0,
        bbox=NEW_HAVEN_DIVISION_BBOXES["THE_HILL"],
        submarkets=[k for k, v in NEW_HAVEN_SUBMARKETS.items() if v.borough == "THE_HILL"],
        city_id="new_haven",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-30 (US-419). Register SLA + DEEDS only — both are the
# statewide CT Socrata feeds Hartford already carries, filtered to New Haven.
# ---------------------------------------------------------------------------
NEW_HAVEN_SLA_ENDPOINT = "https://data.ct.gov/resource/ngch-56tr.json"
NEW_HAVEN_DEEDS_ENDPOINT = "https://data.ct.gov/resource/5mzw-sjtu.json"

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

SLA_NEVER_CANDIDATE_COLUMNS: tuple[str, ...] = (
    # "active" is a 0/1 flag, not the status string; "statusreason" is the
    # human expiry reason (not a status code); "type" is the holder kind
    # (INDIVIDUAL/BUSINESS/CORPORATION); "credentialnumber" is the numeric
    # sub-part already carried by "credentialid"/"fullcredentialcode".
    "active",
    "statusreason",
    "type",
    "credentialnumber",
)

DEEDS_NEVER_CANDIDATE_COLUMNS: tuple[str, ...] = (
    # "listyear" is the assessment-year half of the composite id_keys, NOT a
    # doc_id candidate (serialnumber alone is not row-unique); "assessedvalue"
    # is the assessed value (not the sale amount); "salesratio" is the ratio,
    # not a price; "residentialtype" is a sub-classification; "geo_coordinates"
    # is a native Point the shared producer does not yet read (see module
    # docstring); "remarks" is free text.
    "listyear",
    "assessedvalue",
    "salesratio",
    "residentialtype",
    "geo_coordinates",
    "remarks",
)

NEW_HAVEN_FEED_SPECS: dict[str, dict[str, object]] = {
    "sla": {
        "endpoint": NEW_HAVEN_SLA_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "recordrefreshedon",
        "id_keys": ["credentialid"],
        "topic_key": "topic_sla",
        "interval_seconds": 3600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "needs_geocode": True,
            "geocode_context": "New Haven, CT",
            "where": "city = 'NEW HAVEN'",
            "order_by": "recordrefreshedon DESC",
            "scope": (
                "CT State Licenses and Credentials statewide feed filtered to "
                "city='NEW HAVEN' (47,001 rows incl. individual credentials; "
                "broad credentials stream, Hartford precedent). Address-only — "
                "no native lat/lng, needs_geocode=True. Watermark "
                "recordrefreshedon is a daily refresh stamp with 0 nulls (no "
                "IS NOT NULL guard); credentialid is row-unique; type/active/"
                "statusreason/credentialnumber are never field-map candidates; "
                "businessname exists only on BUSINESS/CORPORATION rows so "
                "premises_name/dba read [businessname, name]."
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "deeds": {
        "endpoint": NEW_HAVEN_DEEDS_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "daterecorded",
        "id_keys": ["serialnumber", "listyear"],
        "topic_key": "topic_deeds",
        "interval_seconds": 3600.0,
        "producer_key": "deeds",
        "extra": {
            "expected_cadence_days": 30,
            "needs_geocode": True,
            "geocode_context": "New Haven, CT",
            "where": "town = 'New Haven'",
            "order_by": "daterecorded DESC",
            "scope": (
                "CT Real Estate Conveyance Tax statewide feed filtered to "
                "town='New Haven' (25,909 rows). serialnumber is NOT row-unique "
                "(resets across 22 assessment years; 2 collisions) so id_keys "
                "are [serialnumber, listyear]. doc_type=propertytype is a "
                "property classification, not a deed instrument type (no "
                "deed-type column). GEO NOTE: native geo_coordinates Point is "
                "present on 32.5% of rows but is NOT read by the shared deeds "
                "producer's nested-loc fallback (the_geom/point/location/"
                "georeference/shape) — needs_geocode=True falls back to the "
                "address; the spine SHOULD add geo_coordinates to that "
                "fallback list so native coords win first."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}

def get_new_haven_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered New Haven feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in NEW_HAVEN_FEED_SPECS:
        available = ", ".join(sorted(NEW_HAVEN_FEED_SPECS))
        raise KeyError(
            f"'{NEW_HAVEN_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = NEW_HAVEN_FEED_SPECS[feed_name]
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
    metro_bbox=NEW_HAVEN_METRO_BBOX,
    division_bboxes=NEW_HAVEN_DIVISION_BBOXES,
    submarkets=NEW_HAVEN_SUBMARKETS,
    divisions=NEW_HAVEN_DIVISIONS,
    contains=is_in_new_haven_metro,
)

__all__ = [
    "NEW_HAVEN_CITY_ID",
    "NEW_HAVEN_DEEDS_ENDPOINT",
    "NEW_HAVEN_DIVISIONS",
    "NEW_HAVEN_DIVISION_BBOXES",
    "NEW_HAVEN_FEED_SPECS",
    "NEW_HAVEN_METRO_BBOX",
    "NEW_HAVEN_SLA_ENDPOINT",
    "NEW_HAVEN_SUBMARKETS",
    "REGISTRATION",
    "get_new_haven_dataset",
    "is_in_greater_new_haven_metro",
    "is_in_new_haven_metro",
]

