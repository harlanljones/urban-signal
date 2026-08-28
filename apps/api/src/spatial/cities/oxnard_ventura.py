"""Oxnard–Ventura, CA spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the Oxnard–Ventura metro
(Ventura County, California).

**ANCHOR: City of San Buenaventura (City of Ventura).** Per the repo's
single-jurisdiction norm (``miami_dade`` is the composite exception) this
registration anchors on the strongest of the twin cities. Ventura verified
THREE live feeds on the 2026-08-28 probe (SLA + 311-family + crime); Oxnard
verified one (its 311 Requests layer) and is documented as a future
companion metro — NOT composited here, and the metro bbox deliberately
excludes the Oxnard plain so no future Oxnard rows can resolve into
Ventura divisions.

Ventura is a THREE-FEED metro on its own ArcGIS Hub
(``open-data-cityofventura.hub.arcgis.com``) backed by AGO org
``dBVj4EXO3IdRPOqb``:

* SLA — ``OpenData_PSI_BusinessLicenses/FeatureServer/0`` (PSI, the city's
  licensing vendor). Current-license registry grain.
* COMPLAINTS_311 — ``Graffiti_Responses_Read_Only/FeatureServer/0``. The
  published service-request surface of Ask Ventura (graffiti response
  requests); the full 311 case stream is not bulk-open.
* CRIME — ``OpenData_Police_Crimes/FeatureServer/0``. ADR 0004 satisfied:
  native point geometry AND a generalized block address per row.

Live-probe evidence that defines this leaf (2026-08-28, US-232; the ticket's
ArcGIS Hub hints were dead URLs):

* ``oxnard.opendata.arcgis.com`` and ``ventura.opendata.arcgis.com`` both
  return ``Domain record(s) not found :: 404``; ``venturacity.us`` has no
  DNS. The real doors are the AGO orgs: Ventura ``dBVj4EXO3IdRPOqb`` (205
  feature services; DCAT lists 37 public datasets) and Oxnard
  ``oxnard.maps.arcgis.com`` (orgid ``PWexKTkN39Lf339y``).
* SLA — 12,590 rows, native point geometry, maxRecordCount 16,000, watermark
  ``DATEISSUE`` newest **1787814000000 = 2026-08-27T07:00:00+00:00** (renewals
  flow continuously: 622 rows issued in Aug 2026); 193 DATEISSUE-null rows;
  0 null geometries in the newest 500. ISO/ANSI date where-literals filter
  fine (epoch-ms literals 400). Ingestion mirrors the Aurora/KC current-
  license registry: snapshot mode, watermark ``DATEISSUE`` still recorded,
  cross-run dedup on ``ACCTNO``.
* 311 — 22,085 rows, native point geometry, maxRecordCount 10,000, watermark
  ``ReportedOn`` newest **1787943600000 = 2026-08-28T19:00:00+00:00** (hours
  before the probe). No address column, so ``needs_geocode`` stays False and
  the (rare) null-geometry row drops; 0 null geometries in the newest 500.
* CRIME — 85,974 rows, native point geometry, maxRecordCount 2000, watermark
  ``Incident_Date_Start`` newest **1787783460000 =
  2026-08-26T22:31:00+00:00** with the layer's edit stamp ``created_date`` at
  2026-08-28T16:26:54+00:00 — the police data team syncs daily and incidents
  lag ~2 days. 0 null geometries and 0 future-dated rows in the newest 500.
  ADR 0004 note: ``GeneralizedAddress`` is block-level ("1600 Block WALTER
  ST") and is deliberately NOT declared for geocoding — coordinates are the
  locator; null-geometry rows drop.
* Mixed-CRS trap: the SLA attribute pair ``BADDRX``/``BADDRY`` is a local
  vendor grid (in-city ≈ 22589–24716 / 19570–20086; out-of-city rows carry
  0.0) — neither WGS84 degrees nor any California State Plane zone, so the
  aurora-style ``state_plane_*`` spec keys are NOT declared (nothing on the
  three layers is state-plane) and the columns are pinned unmapped in
  ``field_maps_oxnard_ventura``. All coordinates come from the
  ``outSR=4326`` geometry lift.
* Divisions are evidenced, not invented: the city publishes its 19 official
  Planning Communities (``OpenData_Plan_PlanningCommunities``, edited by
  ``SiteAdmin_CityOfVentura`` 2026-04); the 7 divisions below group those
  communities, and each submarket center was placed from the community
  polygon centroids computed on the probe. The source's own ``EconDevAreas``
  label ("MIDTOWN") on live license rows corroborates the grouping.
* Ventura County recorded deeds: the County Clerk-Recorder host is
  reachable (recorder.countyofventura.org, HTTP 200) but exposes only a
  vendor search portal, no bulk feed — DEEDS stay unregistered (partial
  registration is fine per the ticket contract).
* Oxnard future-companion evidence (documented, not built): hosted
  ``services3.arcgis.com/PWexKTkN39Lf339y/.../Requests/FeatureServer/0``
  ("311 Requests"), 235,026 rows, native point geometry, watermark
  ``DateCreated`` newest 1787834885000 = 2026-08-27T12:48:05+00:00. Oxnard's
  ``HTE_Layers_Businesses`` license layers are a stale 2021 snapshot (199+31
  rows, item last modified 2023-04) and its AGO org holds no permits layer —
  the companion registration would be 311-only.
"""

from src.producers.field_maps_oxnard_ventura import (
    COMPLAINTS_311_FIELD_MAP,
    CRIME_FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

OXNARD_VENTURA_CITY_ID: str = "oxnard_ventura"
OXNARD_VENTURA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of San Buenaventura plus immediate context (Ventura River mouth and
# estuary, the SOAR edge toward Saticoy). Permissive enough to hold the
# Downtown core (34.2795, -119.2970), Pierpont Bay (34.2600, -119.2700),
# Ventura Harbor (34.2445, -119.2590), the Wells corridor (34.2900,
# -119.1680), and Saticoy (34.2780, -119.1540) while rejecting Oxnard
# downtown (34.1970, -119.1770) and Santa Barbara (34.4208, -119.6982).
OXNARD_VENTURA_METRO_BBOX: dict[str, float] = {
    "min_lat": 34.2300,
    "max_lat": 34.3560,
    "min_lng": -119.3450,
    "max_lng": -119.1280,
}

# 7 divisions grouping the city's 19 official Planning Communities
# (OpenData_Plan_PlanningCommunities). Hand-authored bboxes; borough
# resolution at ingest comes from coordinates via get_division_for_coordinate,
# so bboxes need only be sane, mutually non-overlapping, and contain their own
# submarket centers. The Hillsides community (an empty hillside arc wrapping
# the north city) belongs to no division — it carries no license/request/crime
# activity.
OXNARD_VENTURA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    # Downtown planning community (Main St / California St / Mission).
    "DOWNTOWN_VENTURA": {
        "min_lat": 34.2720,
        "max_lat": 34.2830,
        "min_lng": -119.3235,
        "max_lng": -119.2790,
    },
    # Westside + North Avenue + Taylor Ranch communities (Ventura Avenue
    # corridor and the northern slopes).
    "WESTSIDE_TAYLOR_RANCH": {
        "min_lat": 34.2835,
        "max_lat": 34.3510,
        "min_lng": -119.3400,
        "max_lng": -119.2760,
    },
    # Midtown planning community incl. the Sanjon shore strip.
    "MIDTOWN_SANJON": {
        "min_lat": 34.2625,
        "max_lat": 34.2830,
        "min_lng": -119.2785,
        "max_lng": -119.2450,
    },
    # Pierpont community (north beach) + Ventura Harbor & Keys.
    "PIERPONT_HARBOR": {
        "min_lat": 34.2350,
        "max_lat": 34.2620,
        "min_lng": -119.2755,
        "max_lng": -119.2520,
    },
    # Olivas community east of the harbor (Olivas Links, Santa Clara River
    # north bank).
    "OLIVAS_RIVERBANK": {
        "min_lat": 34.2350,
        "max_lat": 34.2520,
        "min_lng": -119.2515,
        "max_lng": -119.2115,
    },
    # College + Thille + Arundell communities (College corridor and east
    # midtown flats).
    "COLLEGE_CORRIDOR": {
        "min_lat": 34.2525,
        "max_lat": 34.2990,
        "min_lng": -119.2445,
        "max_lng": -119.2095,
    },
    # Poinsettia + Juanamaria + Serra + Wells + Saticoy + North Bank
    # communities (the east end and the Saticoy edge).
    "EAST_END_SATICOY": {
        "min_lat": 34.2435,
        "max_lat": 34.3050,
        "min_lng": -119.2060,
        "max_lng": -119.1385,
    },
}


def is_in_oxnard_ventura_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Ventura-anchored metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        OXNARD_VENTURA_METRO_BBOX["min_lat"] <= lat <= OXNARD_VENTURA_METRO_BBOX["max_lat"]
        and OXNARD_VENTURA_METRO_BBOX["min_lng"] <= lng <= OXNARD_VENTURA_METRO_BBOX["max_lng"]
    )


is_in_greater_oxnard_ventura_metro = is_in_oxnard_ventura_metro


OXNARD_VENTURA_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_VENTURA (1)
    # =======================================================================
    "Downtown Ventura & Mission": SubmarketMeta(
        name="Downtown Ventura & Mission",
        borough="DOWNTOWN_VENTURA",
        lat=34.2795,
        lng=-119.2970,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.86,
        capex=6600000.0,
        permit_vel=27.0,
        shift_ratio=1.45,
        sla=54.0,
        description=(
            "Main Street and California Street core around the Mission with "
            "adaptive-reuse storefronts, hotel conversions, and the city's "
            "densest business-license churn."
        ),
        city_id="oxnard_ventura",
    ),
    # =======================================================================
    # WESTSIDE_TAYLOR_RANCH (3)
    # =======================================================================
    "Westside & Ventura Avenue": SubmarketMeta(
        name="Westside & Ventura Avenue",
        borough="WESTSIDE_TAYLOR_RANCH",
        lat=34.2990,
        lng=-119.2930,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.76,
        capex=4900000.0,
        permit_vel=22.0,
        shift_ratio=1.36,
        sla=47.0,
        description=(
            "Historic Ventura Avenue oil-town corridor with small-business "
            "licensing, garage-conversion permitting, and art-city "
            "warehouse reuse."
        ),
        city_id="oxnard_ventura",
    ),
    "Taylor Ranch & Two Trees": SubmarketMeta(
        name="Taylor Ranch & Two Trees",
        borough="WESTSIDE_TAYLOR_RANCH",
        lat=34.3000,
        lng=-119.3100,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.83,
        capex=6100000.0,
        permit_vel=19.0,
        shift_ratio=1.32,
        sla=44.0,
        description=(
            "Hillside subdivision below the Two Trees landmark with "
            "view-lot remodels, pool/deck auxiliary permits, and quiet "
            "commercial churn."
        ),
        city_id="oxnard_ventura",
    ),
    "North Avenue": SubmarketMeta(
        name="North Avenue",
        borough="WESTSIDE_TAYLOR_RANCH",
        lat=34.3250,
        lng=-119.2920,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.74,
        capex=4200000.0,
        permit_vel=17.0,
        shift_ratio=1.28,
        sla=42.0,
        description=(
            "North Avenue valley edge with tract-home turnover and "
            "school-adjacent renovation permits."
        ),
        city_id="oxnard_ventura",
    ),
    # =======================================================================
    # MIDTOWN_SANJON (2)
    # =======================================================================
    "Midtown Ventura": SubmarketMeta(
        name="Midtown Ventura",
        borough="MIDTOWN_SANJON",
        lat=34.2750,
        lng=-119.2740,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.82,
        capex=5700000.0,
        permit_vel=24.0,
        shift_ratio=1.40,
        sla=51.0,
        description=(
            "Midtown Main and Telegraph commercial strip with the city's "
            "own EconDevAreas tag, medical-office leasing, and steady "
            "alteration permitting."
        ),
        city_id="oxnard_ventura",
    ),
    "Sanjon & Surfers Point": SubmarketMeta(
        name="Sanjon & Surfers Point",
        borough="MIDTOWN_SANJON",
        lat=34.2808,
        lng=-119.2680,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=5300000.0,
        permit_vel=21.0,
        shift_ratio=1.38,
        sla=49.0,
        description=(
            "Beach-side midtown strip by Surfers Point with short-stay "
            "turnover, coastal-inn licensing, and boardwalk retail."
        ),
        city_id="oxnard_ventura",
    ),
    # =======================================================================
    # PIERPONT_HARBOR (2)
    # =======================================================================
    "Pierpont Bay": SubmarketMeta(
        name="Pierpont Bay",
        borough="PIERPONT_HARBOR",
        lat=34.2600,
        lng=-119.2700,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.85,
        capex=6900000.0,
        permit_vel=20.0,
        shift_ratio=1.42,
        sla=52.0,
        description=(
            "Oceanfront tract between the dunes and Harbor Boulevard with "
            "beach-house remodels and high-valuation coastal permits."
        ),
        city_id="oxnard_ventura",
    ),
    "Ventura Harbor & Keys": SubmarketMeta(
        name="Ventura Harbor & Keys",
        borough="PIERPONT_HARBOR",
        lat=34.2445,
        lng=-119.2590,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.87,
        capex=7400000.0,
        permit_vel=23.0,
        shift_ratio=1.47,
        sla=58.0,
        description=(
            "Harbor village, marina, and the canal-front Keys with "
            "tourism-led licensing, charter operations, and village "
            "retail churn."
        ),
        city_id="oxnard_ventura",
    ),
    # =======================================================================
    # OLIVAS_RIVERBANK (1)
    # =======================================================================
    "Olivas & River North Bank": SubmarketMeta(
        name="Olivas & River North Bank",
        borough="OLIVAS_RIVERBANK",
        lat=34.2450,
        lng=-119.2350,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.75,
        capex=4600000.0,
        permit_vel=18.0,
        shift_ratio=1.30,
        sla=45.0,
        description=(
            "Olivas Links and the Santa Clara River north bank with "
            "golf/resort adjacency, equestrian parcels, and light "
            "commercial turnover."
        ),
        city_id="oxnard_ventura",
    ),
    # =======================================================================
    # COLLEGE_CORRIDOR (2)
    # =======================================================================
    "College Area": SubmarketMeta(
        name="College Area",
        borough="COLLEGE_CORRIDOR",
        lat=34.2790,
        lng=-119.2320,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.81,
        capex=5500000.0,
        permit_vel=23.0,
        shift_ratio=1.39,
        sla=50.0,
        description=(
            "College corridor around Pacific View Mall with medical and "
            "office leasing, apartment turnover, and retail-pad "
            "repositioning."
        ),
        city_id="oxnard_ventura",
    ),
    "Telegraph & Thille": SubmarketMeta(
        name="Telegraph & Thille",
        borough="COLLEGE_CORRIDOR",
        lat=34.2620,
        lng=-119.2230,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.78,
        capex=5000000.0,
        permit_vel=20.0,
        shift_ratio=1.34,
        sla=48.0,
        description=(
            "Telegraph Road east flats with auto-row licensing, "
            "duplex conversions, and infill townhome filings."
        ),
        city_id="oxnard_ventura",
    ),
    # =======================================================================
    # EAST_END_SATICOY (3)
    # =======================================================================
    "Wells Corridor": SubmarketMeta(
        name="Wells Corridor",
        borough="EAST_END_SATICOY",
        lat=34.2900,
        lng=-119.1680,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.79,
        capex=5200000.0,
        permit_vel=21.0,
        shift_ratio=1.36,
        sla=49.0,
        description=(
            "Wells Road commercial spine with neighborhood retail, "
            "clinic licensing, and steady residential renovation."
        ),
        city_id="oxnard_ventura",
    ),
    "Serra & Juanamaria": SubmarketMeta(
        name="Serra & Juanamaria",
        borough="EAST_END_SATICOY",
        lat=34.2720,
        lng=-119.1880,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.77,
        capex=4700000.0,
        permit_vel=18.0,
        shift_ratio=1.31,
        sla=46.0,
        description=(
            "Post-war east-end tracts around Serra School with "
            "starter-home turnover and garage-conversion permits."
        ),
        city_id="oxnard_ventura",
    ),
    "Saticoy": SubmarketMeta(
        name="Saticoy",
        borough="EAST_END_SATICOY",
        lat=34.2780,
        lng=-119.1540,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.72,
        capex=3900000.0,
        permit_vel=15.0,
        shift_ratio=1.26,
        sla=41.0,
        description=(
            "Historic Saticoy village at the SOAR edge with "
            "ag-service businesses, warehouse reuse, and slow-license "
            "churn."
        ),
        city_id="oxnard_ventura",
    ),
}


OXNARD_VENTURA_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_VENTURA": BoroughMeta(
        name="DOWNTOWN_VENTURA",
        center_lat=34.2795,
        center_lng=-119.2970,
        zoom=14.0,
        bbox=OXNARD_VENTURA_DIVISION_BBOXES["DOWNTOWN_VENTURA"],
        submarkets=[k for k, v in OXNARD_VENTURA_SUBMARKETS.items() if v.borough == "DOWNTOWN_VENTURA"],
        city_id="oxnard_ventura",
    ),
    "WESTSIDE_TAYLOR_RANCH": BoroughMeta(
        name="WESTSIDE_TAYLOR_RANCH",
        center_lat=34.2990,
        center_lng=-119.2930,
        zoom=13.0,
        bbox=OXNARD_VENTURA_DIVISION_BBOXES["WESTSIDE_TAYLOR_RANCH"],
        submarkets=[k for k, v in OXNARD_VENTURA_SUBMARKETS.items() if v.borough == "WESTSIDE_TAYLOR_RANCH"],
        city_id="oxnard_ventura",
    ),
    "MIDTOWN_SANJON": BoroughMeta(
        name="MIDTOWN_SANJON",
        center_lat=34.2750,
        center_lng=-119.2740,
        zoom=13.5,
        bbox=OXNARD_VENTURA_DIVISION_BBOXES["MIDTOWN_SANJON"],
        submarkets=[k for k, v in OXNARD_VENTURA_SUBMARKETS.items() if v.borough == "MIDTOWN_SANJON"],
        city_id="oxnard_ventura",
    ),
    "PIERPONT_HARBOR": BoroughMeta(
        name="PIERPONT_HARBOR",
        center_lat=34.2600,
        center_lng=-119.2700,
        zoom=13.5,
        bbox=OXNARD_VENTURA_DIVISION_BBOXES["PIERPONT_HARBOR"],
        submarkets=[k for k, v in OXNARD_VENTURA_SUBMARKETS.items() if v.borough == "PIERPONT_HARBOR"],
        city_id="oxnard_ventura",
    ),
    "OLIVAS_RIVERBANK": BoroughMeta(
        name="OLIVAS_RIVERBANK",
        center_lat=34.2450,
        center_lng=-119.2350,
        zoom=13.0,
        bbox=OXNARD_VENTURA_DIVISION_BBOXES["OLIVAS_RIVERBANK"],
        submarkets=[k for k, v in OXNARD_VENTURA_SUBMARKETS.items() if v.borough == "OLIVAS_RIVERBANK"],
        city_id="oxnard_ventura",
    ),
    "COLLEGE_CORRIDOR": BoroughMeta(
        name="COLLEGE_CORRIDOR",
        center_lat=34.2790,
        center_lng=-119.2320,
        zoom=13.0,
        bbox=OXNARD_VENTURA_DIVISION_BBOXES["COLLEGE_CORRIDOR"],
        submarkets=[k for k, v in OXNARD_VENTURA_SUBMARKETS.items() if v.borough == "COLLEGE_CORRIDOR"],
        city_id="oxnard_ventura",
    ),
    "EAST_END_SATICOY": BoroughMeta(
        name="EAST_END_SATICOY",
        center_lat=34.2900,
        center_lng=-119.1680,
        zoom=12.5,
        bbox=OXNARD_VENTURA_DIVISION_BBOXES["EAST_END_SATICOY"],
        submarkets=[k for k, v in OXNARD_VENTURA_SUBMARKETS.items() if v.borough == "EAST_END_SATICOY"],
        city_id="oxnard_ventura",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register: Development_Projects_Public (238-row
# dashboard tracker), EGOV_CSS (reference address/street/parcels), county
# recorder deeds (vendor search portal, no bulk feed), Oxnard's stale
# HTE_Layers_Businesses (2021 snapshot), or the dead ticket Hub URLs.
# ---------------------------------------------------------------------------
OXNARD_VENTURA_SLA_ENDPOINT = (
    "https://services.arcgis.com/dBVj4EXO3IdRPOqb/arcgis/rest/services/"
    "OpenData_PSI_BusinessLicenses/FeatureServer/0"
)
OXNARD_VENTURA_311_ENDPOINT = (
    "https://services.arcgis.com/dBVj4EXO3IdRPOqb/arcgis/rest/services/"
    "Graffiti_Responses_Read_Only/FeatureServer/0"
)
OXNARD_VENTURA_CRIME_ENDPOINT = (
    "https://services.arcgis.com/dBVj4EXO3IdRPOqb/arcgis/rest/services/"
    "OpenData_Police_Crimes/FeatureServer/0"
)

OXNARD_VENTURA_FEED_SPECS: dict[str, dict[str, object]] = {
    "sla": {
        "endpoint": OXNARD_VENTURA_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "DATEISSUE",
        "id_keys": ["ACCTNO", "GlobalID", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 300.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": OXNARD_VENTURA_GEOCODE_CONTEXT,
            "ingestion_mode": "snapshot",
            "oid_field": "OBJECTID",
            "max_record_count": 16000,
            "order_by": "DATEISSUE DESC",
            "scope": (
                "OpenData_PSI_BusinessLicenses current-license registry "
                "(PSI vendor; FeatureServer/0, 12,590 rows < "
                "maxRecordCount 16000 — one-page snapshot; renewals "
                "bump DATEISSUE in place, dedup on ACCTNO; watermark "
                "newest 2026-08-27T07:00:00+00:00; ISO/ANSI where-"
                "literals filter, epoch-ms literals 400; geometry "
                "outSR=4326 primary, BADDRX/BADDRY local grid never "
                "mapped; 193 DATEISSUE-null rows)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "311": {
        "endpoint": OXNARD_VENTURA_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ReportedOn",
        "id_keys": ["globalid", "objectid"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "objectid",
            "max_record_count": 10000,
            "order_by": "ReportedOn DESC",
            "scope": (
                "Graffiti_Responses_Read_Only — the published "
                "service-request surface of Ask Ventura (graffiti "
                "subset; full 311 case stream not bulk-open); 22,085 "
                "rows; watermark newest 2026-08-28T19:00:00+00:00; "
                "native point geometry, no address column so "
                "needs_geocode stays False and null-geometry rows "
                "drop; no complaint_type column — rows classify "
                "honestly as Unknown"
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
    "crime": {
        "endpoint": OXNARD_VENTURA_CRIME_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Incident_Date_Start",
        "id_keys": ["EventOffenseKey", "Report_Number", "ObjectID"],
        "topic_key": "topic_crime",
        "interval_seconds": 1800.0,
        "producer_key": "crime",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "ObjectID",
            "max_record_count": 2000,
            "order_by": "Incident_Date_Start DESC",
            "scope": (
                "OpenData_Police_Crimes (85,974 rows; ADR 0004 "
                "satisfied — native point geometry AND generalized "
                "block address); watermark newest "
                "2026-08-26T22:31:00+00:00 with daily edit-stamp sync; "
                "GeneralizedAddress is block-level and NOT geocode-"
                "declared — coordinates are the locator; 0 null "
                "geometry and 0 future dates in newest 500"
            ),
            "field_map": CRIME_FIELD_MAP,
        },
    },
}


def get_oxnard_ventura_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Oxnard–Ventura feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in OXNARD_VENTURA_FEED_SPECS:
        available = ", ".join(sorted(OXNARD_VENTURA_FEED_SPECS))
        raise KeyError(
            f"'{OXNARD_VENTURA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = OXNARD_VENTURA_FEED_SPECS[feed_name]
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
    metro_bbox=OXNARD_VENTURA_METRO_BBOX,
    division_bboxes=OXNARD_VENTURA_DIVISION_BBOXES,
    submarkets=OXNARD_VENTURA_SUBMARKETS,
    divisions=OXNARD_VENTURA_DIVISIONS,
    contains=is_in_oxnard_ventura_metro,
)

__all__ = [
    "OXNARD_VENTURA_311_ENDPOINT",
    "OXNARD_VENTURA_CITY_ID",
    "OXNARD_VENTURA_CRIME_ENDPOINT",
    "OXNARD_VENTURA_DIVISIONS",
    "OXNARD_VENTURA_DIVISION_BBOXES",
    "OXNARD_VENTURA_FEED_SPECS",
    "OXNARD_VENTURA_GEOCODE_CONTEXT",
    "OXNARD_VENTURA_METRO_BBOX",
    "OXNARD_VENTURA_SLA_ENDPOINT",
    "OXNARD_VENTURA_SUBMARKETS",
    "REGISTRATION",
    "get_oxnard_ventura_dataset",
    "is_in_greater_oxnard_ventura_metro",
    "is_in_oxnard_ventura_metro",
]
