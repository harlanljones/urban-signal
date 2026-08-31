PERMITS_FIELD_MAP = {
    # PERMIT_NBR is the Accela permit number ("UTL26-0884", "BLD26-2139", …)
    # and the id_keys head; OBJECTID keeps rows addressable if the number is
    # ever missing client-side (Henderson OID-fallback precedent).
    "job_id": ["PERMIT_NBR", "OBJECTID"],
    "filing_date": ["CREATE_DT"],
    "status": ["PERMIT_STATUS"],
    "job_type": ["B1_PER_TYPE", "PERMIT_TYPE"],
    "cost": ["JOB_VALUE"],
    "address_street": ["FULL_ADDRESS", "FULL_ADDR"],
    "zipcode": ["ZIP_CODE"],
    "bbl": ["PARCEL_NBR"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Chandler, AZ"

DROPPED_PII_COLUMNS = (
    "PRI_CNTCT_BUS_NM",
    "PRI_CNTCT_FULL_NM",
    "PRI_CNTCT_PHONE",
    "PRI_CNTCT_EMAIL",
    "PRI_CNTRCT_BUS_NM",
    "PRI_CNTRCT_FULL_NM",
    "PRI_CNTRCT_PHONE",
    "PRI_CNTRCT_EMAIL",
    "OWNER_NM",
    "OWNER_PHONE",
    "OWNER_EMAIL",
)

"""Chandler, AZ spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Chandler
(east Maricopa County, AZ — Southeast Valley).

Chandler is a ONE-FEED PARTIAL metro like Tucson/Greenville: PERMITS only —
``Tolemi/Building_Blocks/MapServer/0`` (``LIS.ACCELA_ALL_PERMITS_V_HARD``),
the city ArcGIS Enterprise 11.5 view of the Accela permitting system, Tier 1,
daily, ~103k rows. COMPLAINTS_311, SLA, DEEDS and CRIME are Tier 3 and stay
unregistered:

* COMPLAINTS_311 — Chandler 311 runs on GOGov; ``GOGov/COC_GOGov`` publishes
  only base-map layers (Address/Parcel/Permit Meter). A full 42-folder sweep
  of the server plus an org-wide search (``orgid:HIBNcuytta1apnkB AND
  ("service request" OR 311)``) return zero service-request datasets.
* SLA — no business-license dataset anywhere on the server or org (Arizona
  cities have no municipal general business license; TPT is
  state-administered) — the phoenix.py "no broader business-tax feed" caveat.
* DEEDS — Maricopa County recorder 403s anonymous scripted access with no
  bulk API ("Deeds have no queryable watermark", phoenix.py:22-23; same
  county as Phoenix).
* CRIME — the city "Crime Map" is raidsonline.com (LexisNexis RAIDS SaaS);
  every other surface is a PIP aggregate dashboard. (ADR-0004 coordinate
  rule moot — nothing to register.)

Live-probe caveats that define this leaf (2026-08-28, US-228):

* The ArcGIS Hub (``chandleraz.opendata.arcgis.com``) is a **private org**
  (search API → 401 "private org id … is not accessible"); the legacy
  ``/arcgis/rest/services`` tree referenced by 2018 web maps is
  decommissioned (IIS 404). The live server is Enterprise 11.5 proxied at
  ``https://gis.chandleraz.gov/portalserver/rest/services`` (the
  ``/appsanonymous`` path serves the identical tree).
* PERMITS native store SR is **NAD83(HARN) StatePlane Arizona Central FIPS
  0202, international feet**; every query goes out with ``outSR=4326`` per
  ``ArcGISClient``, so point geometry arrives as WGS84 latitude/longitude.
  The layer exposes NO X/Y attribute pair — there is nothing to mis-map, so
  no ``state_plane_*`` spec fields are declared (tucson discipline: the
  store SR is documented and never touched). ``SHAPE IS NULL`` count = 0 of
  103,442 rows → ``needs_geocode=False``.
* ``CREATE_DT`` is the ONLY ``esriFieldTypeDate`` column and is the Accela
  record-creation (application) date, **not** issuance: 2,307 pending-status
  permits carry CREATE_DT older than 90d, oldest pending 2006-08-29. It maps
  to ``filing_date`` (Dallas ``CREATEDDATE`` convention); no issuance
  timestamp is published, so ``issuance_date`` stays undeclared and the
  issuance-based permit-velocity chain sees NULL until the city publishes
  one. Newest CREATE_DT verbatim **1787702401000** (2026-08-26T00:00:01Z);
  103,442 rows back to 2001; 3,930 in 2026 YTD; 455 in the last 30d; 0
  future-dated.
* **ANSI-date host**: ``gis.chandleraz.gov`` rejects ISO date-string
  comparisons in ``where`` (400 "Unable to complete operation") and only
  accepts ANSI ``date 'YYYY-MM-DD'`` literals (verified; ``DATEADD`` is
  unsupported). The spine must add the host to ``ANSI_DATE_LITERAL_HOSTS``
  (watermarks.py); the leaf declares no ``where`` guard and needs no literal
  form.
* PII is dropped at the field map (PRI_CNTCT_* / PRI_CNTRCT_* / OWNER_*
  blocks; ``DROPPED_PII_COLUMNS``). ``RETIRED`` (address-retirement flag,
  N/Y) is left unfiltered — 537 Y-rows, newest 2026-04-10.
* ``JOB_VALUE`` is a string ("4000", often null); the shared cost chain
  strips and floats it. ``PERMIT_TYPE`` is null on 49,436 rows, so
  ``job_type`` candidates lead with ``B1_PER_TYPE``.
* Divisions are grounded in the live ``OpenData/LIS_OpenData/MapServer/2``
  Subdivisions layer (2,010 plats) envelopes at outSR=4326: MARLBOROUGH
  ESTATES, SUN GROVES (12 parcels), OCOTILLO (58 plats), FULTON RANCH,
  SPRINGFIELD, COOPER COMMONS, CIRCLE G AT RIGGS HOMESTEAD RANCH. The metro
  bbox is rounded from the live ``GOGov/COC_GOGov/MapServer/11`` city
  boundary envelope: lng[-111.9723,-111.7553] lat[33.2038,33.3613].
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

CHANDLER_CITY_ID: str = "chandler"
CHANDLER_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Chandler, rounded out from the live jurisdiction boundary envelope
# (GOGov/COC_GOGov/MapServer/11): lng[-111.9723,-111.7553]
# lat[33.2038,33.3613]. Permissive enough to hold every live permit fixture
# (downtown -111.841, Sun Groves -111.755, Marlborough Estates 33.349,
# Ocotillo 33.231) while rejecting downtown Phoenix (33.4484, -112.0740) and
# downtown Tucson (32.2226, -110.9723).
CHANDLER_METRO_BBOX: dict[str, float] = {
    "min_lat": 33.20,
    "max_lat": 33.37,
    "min_lng": -111.98,
    "max_lng": -111.75,
}

# 6 Chandler divisions. Hand-authored; borough resolution at ingest comes
# from coordinates via get_division_for_coordinate, so bboxes need only be
# sane, mutually non-overlapping, and contain their own submarket centers.
# Division geography is anchored on live subdivision-plat envelopes (see
# module docstring) and the Chandler Municipal Airport.
CHANDLER_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "WEST_CHANDLER_MARLBOROUGH": {
        "min_lat": 33.325,
        "max_lat": 33.370,
        "min_lng": -111.980,
        "max_lng": -111.855,
    },
    "PRICE_ROAD_CORRIDOR": {
        "min_lat": 33.290,
        "max_lat": 33.325,
        "min_lng": -111.980,
        "max_lng": -111.855,
    },
    "DOWNTOWN_HISTORIC_CORE": {
        "min_lat": 33.290,
        "max_lat": 33.325,
        "min_lng": -111.855,
        "max_lng": -111.825,
    },
    "AIRPORT_EAST_GATEWAY": {
        "min_lat": 33.280,
        "max_lat": 33.370,
        "min_lng": -111.825,
        "max_lng": -111.750,
    },
    "OCOTILLO_SOUTH_LAKES": {
        "min_lat": 33.200,
        "max_lat": 33.280,
        "min_lng": -111.980,
        "max_lng": -111.825,
    },
    "SOUTHEAST_SUN_GROVES": {
        "min_lat": 33.200,
        "max_lat": 33.280,
        "min_lng": -111.825,
        "max_lng": -111.750,
    },
}


def is_in_chandler_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Chandler metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        CHANDLER_METRO_BBOX["min_lat"] <= lat <= CHANDLER_METRO_BBOX["max_lat"]
        and CHANDLER_METRO_BBOX["min_lng"] <= lng <= CHANDLER_METRO_BBOX["max_lng"]
    )


is_in_greater_chandler_metro = is_in_chandler_metro


CHANDLER_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_HISTORIC_CORE (1)
    # =======================================================================
    "Downtown Historic Core": SubmarketMeta(
        name="Downtown Historic Core",
        borough="DOWNTOWN_HISTORIC_CORE",
        lat=33.3060,
        lng=-111.8412,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.85,
        capex=8600000.0,
        permit_vel=40.0,
        shift_ratio=1.54,
        sla=62.0,
        description=(
            "Dr. A.J. Chandler park and the ostrich-farm heritage grid "
            "around San Marcos and Arizona Avenue, with adaptive reuse, "
            "murals-and-patios retail, and steady downtown infill "
            "permitting."
        ),
        city_id="chandler",
    ),
    # =======================================================================
    # PRICE_ROAD_CORRIDOR (2)
    # =======================================================================
    "Andersen Springs & Chandler Blvd": SubmarketMeta(
        name="Andersen Springs & Chandler Blvd",
        borough="PRICE_ROAD_CORRIDOR",
        lat=33.3075,
        lng=-111.8725,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.78,
        capex=5800000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=52.0,
        description=(
            "Office-park and apartment belt along the Chandler Boulevard "
            "frontage with build-to-rent infill, valley-metro commuter "
            "demand, and steady TI/tenant-improvement permitting."
        ),
        city_id="chandler",
    ),
    "Intel Ocotillo Tech Belt": SubmarketMeta(
        name="Intel Ocotillo Tech Belt",
        borough="PRICE_ROAD_CORRIDOR",
        lat=33.3163,
        lng=-111.8560,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.88,
        capex=10800000.0,
        permit_vel=44.0,
        shift_ratio=1.58,
        sla=66.0,
        description=(
            "Price Road Corridor employment core anchored by the Intel "
            "Ocotillo campus and supplier vendors, with the metro's "
            "highest-valuation commercial trades and engineering-led "
            "permit velocity."
        ),
        city_id="chandler",
    ),
    # =======================================================================
    # WEST_CHANDLER_MARLBOROUGH (2)
    # =======================================================================
    "Marlborough Park Estates": SubmarketMeta(
        name="Marlborough Park Estates",
        borough="WEST_CHANDLER_MARLBOROUGH",
        lat=33.3480,
        lng=-111.8918,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=50.0,
        description=(
            "North Chandler residential belt around the MARLBOROUGH "
            "ESTATES plat (recorded 1973) with pool/deck auxiliary "
            "permits, roof-replacement cadence, and Kyrene-school "
            "family churn."
        ),
        city_id="chandler",
    ),
    "West Chandler Kyrene Belt": SubmarketMeta(
        name="West Chandler Kyrene Belt",
        borough="WEST_CHANDLER_MARLBOROUGH",
        lat=33.3400,
        lng=-111.9200,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=26.0,
        shift_ratio=1.36,
        sla=47.0,
        description=(
            "Western edge toward the Kyrene corridor with 1970s-80s "
            "tract stock, renovation-led permitting, and the I-10/"
            "Pecos logistics commute shed."
        ),
        city_id="chandler",
    ),
    # =======================================================================
    # AIRPORT_EAST_GATEWAY (1)
    # =======================================================================
    "Chandler Municipal Airport": SubmarketMeta(
        name="Chandler Municipal Airport",
        borough="AIRPORT_EAST_GATEWAY",
        lat=33.2906,
        lng=-111.7968,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.79,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=54.0,
        description=(
            "Reliever-airport industrial district with hangar and "
            "flight-school tenancy, airpark-adjacent light industrial "
            "trades, and the East Valley logistics gateway."
        ),
        city_id="chandler",
    ),
    # =======================================================================
    # OCOTILLO_SOUTH_LAKES (2)
    # =======================================================================
    "Ocotillo Lakes": SubmarketMeta(
        name="Ocotillo Lakes",
        borough="OCOTILLO_SOUTH_LAKES",
        lat=33.2495,
        lng=-111.8355,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.87,
        capex=9400000.0,
        permit_vel=38.0,
        shift_ratio=1.53,
        sla=63.0,
        description=(
            "Lake-amenity master plan of 58 recorded Ocotillo plats "
            "with golf-front custom stock, waterfront renovation, and "
            "the city's steadiest high-valuation residential trades."
        ),
        city_id="chandler",
    ),
    "Fulton Ranch": SubmarketMeta(
        name="Fulton Ranch",
        borough="OCOTILLO_SOUTH_LAKES",
        lat=33.2402,
        lng=-111.8506,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.86,
        capex=9000000.0,
        permit_vel=36.0,
        shift_ratio=1.51,
        sla=61.0,
        description=(
            "Master-planned village on the Gila River canal system "
            "with estate lots, village-retail pads, and continued "
            "build-out permitting at the metro's southwest edge."
        ),
        city_id="chandler",
    ),
    # =======================================================================
    # SOUTHEAST_SUN_GROVES (2)
    # =======================================================================
    "Sun Groves": SubmarketMeta(
        name="Sun Groves",
        borough="SOUTHEAST_SUN_GROVES",
        lat=33.2120,
        lng=-111.7640,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.83,
        capex=7600000.0,
        permit_vel=34.0,
        shift_ratio=1.48,
        sla=58.0,
        description=(
            "Southeast-corner subdivision family of twelve recorded "
            "parcels with newer-roof stock, Chandler Heights corridor "
            "retail pads, and the metro's fastest family-formation churn."
        ),
        city_id="chandler",
    ),
    "Springfield, Cooper Commons & Circle G": SubmarketMeta(
        name="Springfield, Cooper Commons & Circle G",
        borough="SOUTHEAST_SUN_GROVES",
        lat=33.2118,
        lng=-111.7982,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.81,
        capex=7000000.0,
        permit_vel=31.0,
        shift_ratio=1.45,
        sla=55.0,
        description=(
            "Southeast master-planned belt of the SPRINGFIELD, COOPER "
            "COMMONS and CIRCLE G AT RIGGS HOMESTEAD RANCH plats with "
            "elementary-school build-out, horse-property transition "
            "lots, and pool/ patio auxiliary permitting."
        ),
        city_id="chandler",
    ),
}


CHANDLER_DIVISIONS: dict[str, BoroughMeta] = {
    "WEST_CHANDLER_MARLBOROUGH": BoroughMeta(
        name="WEST_CHANDLER_MARLBOROUGH",
        center_lat=33.347,
        center_lng=-111.900,
        zoom=12.5,
        bbox=CHANDLER_DIVISION_BBOXES["WEST_CHANDLER_MARLBOROUGH"],
        submarkets=[k for k, v in CHANDLER_SUBMARKETS.items() if v.borough == "WEST_CHANDLER_MARLBOROUGH"],
        city_id="chandler",
    ),
    "PRICE_ROAD_CORRIDOR": BoroughMeta(
        name="PRICE_ROAD_CORRIDOR",
        center_lat=33.307,
        center_lng=-111.870,
        zoom=13.0,
        bbox=CHANDLER_DIVISION_BBOXES["PRICE_ROAD_CORRIDOR"],
        submarkets=[k for k, v in CHANDLER_SUBMARKETS.items() if v.borough == "PRICE_ROAD_CORRIDOR"],
        city_id="chandler",
    ),
    "DOWNTOWN_HISTORIC_CORE": BoroughMeta(
        name="DOWNTOWN_HISTORIC_CORE",
        center_lat=33.306,
        center_lng=-111.841,
        zoom=13.5,
        bbox=CHANDLER_DIVISION_BBOXES["DOWNTOWN_HISTORIC_CORE"],
        submarkets=[k for k, v in CHANDLER_SUBMARKETS.items() if v.borough == "DOWNTOWN_HISTORIC_CORE"],
        city_id="chandler",
    ),
    "AIRPORT_EAST_GATEWAY": BoroughMeta(
        name="AIRPORT_EAST_GATEWAY",
        center_lat=33.290,
        center_lng=-111.795,
        zoom=12.5,
        bbox=CHANDLER_DIVISION_BBOXES["AIRPORT_EAST_GATEWAY"],
        submarkets=[k for k, v in CHANDLER_SUBMARKETS.items() if v.borough == "AIRPORT_EAST_GATEWAY"],
        city_id="chandler",
    ),
    "OCOTILLO_SOUTH_LAKES": BoroughMeta(
        name="OCOTILLO_SOUTH_LAKES",
        center_lat=33.245,
        center_lng=-111.845,
        zoom=12.5,
        bbox=CHANDLER_DIVISION_BBOXES["OCOTILLO_SOUTH_LAKES"],
        submarkets=[k for k, v in CHANDLER_SUBMARKETS.items() if v.borough == "OCOTILLO_SOUTH_LAKES"],
        city_id="chandler",
    ),
    "SOUTHEAST_SUN_GROVES": BoroughMeta(
        name="SOUTHEAST_SUN_GROVES",
        center_lat=33.212,
        center_lng=-111.785,
        zoom=12.5,
        bbox=CHANDLER_DIVISION_BBOXES["SOUTHEAST_SUN_GROVES"],
        submarkets=[k for k, v in CHANDLER_SUBMARKETS.items() if v.borough == "SOUTHEAST_SUN_GROVES"],
        city_id="chandler",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register 311, SLA, deeds, crime, the GOGov
# "Permit Meter" layer, or the PIP performance dashboards.
# ---------------------------------------------------------------------------
CHANDLER_PERMITS_ENDPOINT = (
    "https://gis.chandleraz.gov/portalserver/rest/services/"
    "Tolemi/Building_Blocks/MapServer/0"
)

CHANDLER_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": CHANDLER_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "CREATE_DT",
        "id_keys": ["PERMIT_NBR", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "CREATE_DT DESC",
            "scope": (
                "LIS.ACCELA_ALL_PERMITS_V_HARD (103,442 rows; CREATE_DT is "
                "the Accela record-creation/application date, not issuance "
                "- mapped to filing_date; no issuance timestamp exists on "
                "the view; native outSR=4326 point geometry primary, store "
                "SR is StatePlane Arizona Central HARN intl feet with no "
                "X/Y attributes; 0 null-geometry rows so needs_geocode "
                "False; host is ANSI-date - spine must add "
                "gis.chandleraz.gov to ANSI_DATE_LITERAL_HOSTS; PII "
                "contact/contractor/owner blocks dropped at the field map; "
                "RETIRED address flag left unfiltered)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
}


def get_chandler_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Chandler feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in CHANDLER_FEED_SPECS:
        available = ", ".join(sorted(CHANDLER_FEED_SPECS))
        raise KeyError(
            f"'{CHANDLER_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = CHANDLER_FEED_SPECS[feed_name]
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
    metro_bbox=CHANDLER_METRO_BBOX,
    division_bboxes=CHANDLER_DIVISION_BBOXES,
    submarkets=CHANDLER_SUBMARKETS,
    divisions=CHANDLER_DIVISIONS,
    contains=is_in_chandler_metro,
)

__all__ = [
    "CHANDLER_CITY_ID",
    "CHANDLER_DIVISIONS",
    "CHANDLER_DIVISION_BBOXES",
    "CHANDLER_FEED_SPECS",
    "CHANDLER_GEOCODE_CONTEXT",
    "CHANDLER_METRO_BBOX",
    "CHANDLER_PERMITS_ENDPOINT",
    "CHANDLER_SUBMARKETS",
    "REGISTRATION",
    "get_chandler_dataset",
    "is_in_chandler_metro",
    "is_in_greater_chandler_metro",
]
