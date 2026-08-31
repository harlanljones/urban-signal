PERMITS_FIELD_MAP = {
    # OBJECTID is the OID fallback (Henderson precedent): PermitNum is the
    # id_keys head, but the OID keeps coordinate-less/dedup edge rows
    # addressable if a permit number is ever missing client-side.
    "job_id": ["PermitNum", "OBJECTID"],
    # The *Dtm esri dates lead: _flatten_feature ISO-normalizes them to
    # tz-aware UTC, while the plain string twins ("2026-08-26") parse naive
    # in the permits producer's datetime chain — keep event datetimes
    # tz-consistent, string twins remain the fallback.
    "issuance_date": ["IssuedDateDtm", "IssuedDate"],
    "filing_date": ["AppliedDateDtm", "AppliedDate"],
    "status": ["StatusCurrent"],
    "job_type": ["Type", "PermitClass"],
    "cost": ["EstProjectCost"],
    "address_street": ["OriginalAddress1"],
    "zipcode": ["OriginalZip"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
}

COMPLAINTS_311_FIELD_MAP = {
    "incident_id": ["CaseNo", "Id"],
    "created_date": ["CaseOpenDate"],
    "status": ["CaseStatus"],
    "complaint_type": ["ViolationType"],
    "incident_address": ["Address"],
}

CRIME_FIELD_MAP = {
    "incident_id": ["PrimaryKey", "OBJECTID"],
    "offense_type": ["OffenseCustom"],
    "occurred_date": ["OccurrenceDatetime"],
    "borough": ["CharacterArea"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT = "Tempe, AZ"

DROPPED_PII_COLUMNS = (
    "ContractorCompanyName",
    "ContractorLicNum",
    "ContractorPhone",
    "ContractorAddress1",
    "ContractorAddress2",
    "ContractorCity",
    "ContractorState",
    "ContractorZip",
    "ContractorEmail",
    "ProjectName",
)

"""Tempe, AZ spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Tempe
(Maricopa County, Arizona).

Tempe is a THREE-FEED PARTIAL metro on the city's ArcGIS Hub
(``data.tempe.gov``, org ``lQySeXwbBg53XWDi``): PERMITS
(``building_permits/FeatureServer/0``, Tier 1, daily), COMPLAINTS_311
(``code_complaints/FeatureServer/0`` — the city publishes code-compliance
cases, not a raw 311 request log), and CRIME (``General_Offenses_(Open_Data)/
FeatureServer/0``). SLA and DEEDS are Tier 3 and stay unregistered.

Live-probe caveats that define this leaf (2026-08-28, stream ``west-tempe``,
US-229):

* The ticket's Socrata hint is the wrong door — ``data.tempe.gov/api/odata/v4``
  and ``/api/catalog/v1`` both 404; the portal is an **ArcGIS Hub Site** whose
  datasets live on ``services.arcgis.com`` FeatureServers. Hub search
  (``/api/search/v1/collections/dataset/items``) resolves the services.
* PERMITS — 20,226 rows live; native WGS84 point geometry (``outSR=4326``) is
  primary; the attribute ``Latitude``/``Longitude`` columns (3.0% null,
  615/20,226) are WGS84 degree fallback candidates. ``AppliedDate``/
  ``IssuedDate`` are plain ``YYYY-MM-DD`` strings while ``*Dtm`` twins are
  esriFieldTypeDate epoch-ms; the watermark is ``AppliedDateDtm`` and IS
  where-clause queryable with ArcGIS ``timestamp`` syntax (unlike
  Greenville's). ``needs_geocode=True`` with context "Tempe, AZ" on
  ``OriginalAddress1`` (a clean single-field street string). Future-date
  sentinels exist on ``ExpiresDateDtm`` (fixture: 2027-08-26) — they flatten
  to ISO but never feed the event date fields.
* COMPLAINTS_311 (code_complaints) — 2,743 rows; native WGS84 geometry; the
  ``X_COORD``/``Y_COORD`` attributes are degree-safe duplicates of the
  geometry and are deliberately NOT candidates (geometry primary, Greenville
  discipline). Freshness caveat: newest ``CaseOpenDate`` on the probe day was
  ``1781247600000`` = 2026-06-12T07:00:00+00:00 (~11 weeks stale — quarterly
  publication suspected); ``CaseStatusDate`` tops out the same day. Two rows
  carry (0,0) zero-coordinate sentinels — the producers' 0/0 guard drops
  them. ``needs_geocode=True`` on ``Address`` (single string with city/zip).
* CRIME (general_offenses) — 380,724 rows; watermark ``OccurrenceDatetime``
  same-day fresh (probe: 2026-08-27T23:31:00+00:00). **Mixed-CRS trap**: the
  native geometry store is **AZ State Plane Central (WKID 2223, intl feet)**
  (probe sample geometry x=697343 y=875784) while the ``Latitude``/
  ``Longitude`` attributes hold WGS84 degrees. Every query goes out with
  ``outSR=4326`` per ``ArcGISClient``, so geometry arrives as WGS84; the
  ``state_plane_*`` spec keys document the store SR for a Boston-style
  fallback transform and ``XCoordinate``/``YCoordinate`` (state-plane attrs)
  must never become map candidates. ``ObfuscatedAddress`` ("9XX E BROADWAY
  RD") is deliberately not geocodable — ``needs_geocode=False``; rows with
  neither geometry nor degree attributes drop. ADR-0004 satisfied by
  coordinates (+ obfuscated address text). ``PrimaryKey`` is CHAR-padded
  ("TE202686933         ") — the parser strips incident_id. ``CharacterArea``
  carries real Tempe character areas (evidenced distribution: Rio
  Salado/DT/ASU/NW 98,085; Alameda 63,212; Mills/Emerald 54,442; Apache
  52,176; Kiwanis/The Lakes 37,409; Diablo/Double Butte 32,632;
  Papago/North Tempe 26,227; Corona/South Tempe 13,699) and maps as the
  borough candidate.
* Verified but NOT registered (no FeedType slot / volume discipline):
  ``ArrestsOpenDataDenormalized/FeatureServer/0`` (42,777 rows, SR 2223,
  watermark ``arrest_dt`` 2026-08-27T22:38:00+00:00 — arrests would need
  either its own FeedType or to displace general_offenses) and
  ``Calls_For_Service/FeatureServer/0`` (640,463 rows of police CAD,
  watermark 2026-08-28T08:01:48+00:00 — overlaps general_offenses at 14x
  row volume; layers 1/2 are 608k/721k historical variants).
* REJECT evidence: no SLA/business-license feed exists in the Tempe catalog
  (only Business *Survey* datasets; the candidate "3.09 ABOR Certificates
  and Licenses (detail)" FeatureServer resolves but has **zero layers**).
  Maricopa County deeds are not machine-verifiable:
  ``recorder.maricopa.gov/recdocdata/`` returns HTTP 403 to programmatic
  requests (session-gated document-search app), ``gis.maricopa.gov`` RED
  folder carries only Assessor/Boundary/DOT MapServers, and the Assessor's
  parcel data is file-download only. Tempe has no raw 311 request feed (only
  KPI summaries). Partial registration without deeds is accepted per the
  metro-expansion brief.

Metro bbox: city-controlled dataset extents plus the north Papago edge —
permissive enough to hold Downtown Mill Avenue, the ASU campus edge, Hayden
Ferry, Escalante, the Diablo Stadium west edge, and South Tempe while
rejecting downtown Phoenix (-112.07), Mesa downtown (-111.8287), Scottsdale
(33.49+), Chandler (33.31-), and Gilbert. Guadalupe (33.366, -111.956) is
scooped in (small town wedged between Tempe and Phoenix; division resolution
stays coordinate-based).
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

TEMPE_CITY_ID: str = "tempe"
TEMPE_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# NAD83(HARN) Arizona Central state plane, international feet — the native
# store SR (WKID 2223) of the general_offenses geometry and its
# XCoordinate/YCoordinate attribute pair. Not used by permits or
# code_complaints (both native WGS84).
TEMPE_STATE_PLANE_CRS: str = "EPSG:2223"
TEMPE_STATE_PLANE_UNITS: str = "ft"

# City of Tempe plus the Papago north edge. Rejects downtown Phoenix
# (-112.0740), Mesa downtown (-111.8287), Scottsdale (33.4942), Chandler
# (33.3062), and Gilbert (-111.7890); scoops in Guadalupe (33.366, -111.956).
TEMPE_METRO_BBOX: dict[str, float] = {
    "min_lat": 33.31,
    "max_lat": 33.47,
    "min_lng": -111.99,
    "max_lng": -111.83,
}

# 9 Tempe divisions. Hand-authored from the evidenced CharacterArea
# distribution on the general_offenses layer (plus Downtown/Hayden Ferry and
# the ASU campus edge split out of the 98k-row combined character area);
# borough resolution at ingest comes from coordinates via
# get_division_for_coordinate, so bboxes need only be sane, non-overlapping,
# and contain their own submarket centers.
TEMPE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_RIO_SALADO": {
        "min_lat": 33.417,
        "max_lat": 33.446,
        "min_lng": -111.955,
        "max_lng": -111.930,
    },
    "ASU_CAMPUS_EDGE": {
        "min_lat": 33.417,
        "max_lat": 33.446,
        "min_lng": -111.930,
        "max_lng": -111.915,
    },
    "ESCALANTE_HISTORIC": {
        "min_lat": 33.417,
        "max_lat": 33.446,
        "min_lng": -111.915,
        "max_lng": -111.890,
    },
    "PAPAGO_NORTH_TEMPE": {
        "min_lat": 33.446,
        "max_lat": 33.465,
        "min_lng": -111.985,
        "max_lng": -111.895,
    },
    "DIABLO_DOUBLE_BUTTE": {
        "min_lat": 33.393,
        "max_lat": 33.446,
        "min_lng": -111.985,
        "max_lng": -111.955,
    },
    "ALAMEDA": {
        "min_lat": 33.393,
        "max_lat": 33.417,
        "min_lng": -111.955,
        "max_lng": -111.930,
    },
    "MILLS_APACHE": {
        "min_lat": 33.393,
        "max_lat": 33.417,
        "min_lng": -111.930,
        "max_lng": -111.888,
    },
    "KIWANIS_THE_LAKES": {
        "min_lat": 33.355,
        "max_lat": 33.393,
        "min_lng": -111.985,
        "max_lng": -111.855,
    },
    "CORONA_SOUTH_TEMPE": {
        "min_lat": 33.310,
        "max_lat": 33.355,
        "min_lng": -111.985,
        "max_lng": -111.830,
    },
}


def is_in_tempe_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Tempe city bounds."""
    if lat is None or lng is None:
        return False
    return (
        TEMPE_METRO_BBOX["min_lat"] <= lat <= TEMPE_METRO_BBOX["max_lat"]
        and TEMPE_METRO_BBOX["min_lng"] <= lng <= TEMPE_METRO_BBOX["max_lng"]
    )


is_in_greater_tempe_metro = is_in_tempe_metro


TEMPE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_RIO_SALADO (2)
    # =======================================================================
    "Downtown Mill Avenue": SubmarketMeta(
        name="Downtown Mill Avenue",
        borough="DOWNTOWN_RIO_SALADO",
        lat=33.4267,
        lng=-111.9398,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.88,
        capex=8200000.0,
        permit_vel=34.0,
        shift_ratio=1.52,
        sla=60.0,
        description=(
            "Mill Avenue entertainment spine with adaptive-reuse lofts, "
            "patio-retail turnover, and the metro's densest evening shift "
            "traffic."
        ),
        city_id="tempe",
    ),
    "Hayden Ferry Lakeside": SubmarketMeta(
        name="Hayden Ferry Lakeside",
        borough="DOWNTOWN_RIO_SALADO",
        lat=33.4313,
        lng=-111.9437,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.90,
        capex=10500000.0,
        permit_vel=40.0,
        shift_ratio=1.58,
        sla=65.0,
        description=(
            "Tempe Town Lake south-shore office/residential district with "
            "class-A build-outs and the city's highest permit valuations."
        ),
        city_id="tempe",
    ),
    # =======================================================================
    # ASU_CAMPUS_EDGE (1)
    # =======================================================================
    "ASU Campus & University Drive": SubmarketMeta(
        name="ASU Campus & University Drive",
        borough="ASU_CAMPUS_EDGE",
        lat=33.4245,
        lng=-111.9285,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=9600000.0,
        permit_vel=38.0,
        shift_ratio=1.55,
        sla=62.0,
        description=(
            "Campus-edge student-housing belt with continual renovation "
            "permitting, annual tenant turnover, and university-anchored "
            "retail."
        ),
        city_id="tempe",
    ),
    # =======================================================================
    # ESCALANTE_HISTORIC (1)
    # =======================================================================
    "Escalante Historic District": SubmarketMeta(
        name="Escalante Historic District",
        borough="ESCALANTE_HISTORIC",
        lat=33.4300,
        lng=-111.9080,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=5800000.0,
        permit_vel=24.0,
        shift_ratio=1.40,
        sla=50.0,
        description=(
            "Historic bungalow district with steady renovation, "
            "garage-conversion filings, and infill near the Mesa border."
        ),
        city_id="tempe",
    ),
    # =======================================================================
    # PAPAGO_NORTH_TEMPE (1)
    # =======================================================================
    "Papago Park & North Tempe": SubmarketMeta(
        name="Papago Park & North Tempe",
        borough="PAPAGO_NORTH_TEMPE",
        lat=33.4520,
        lng=-111.9350,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.84,
        capex=7200000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=54.0,
        description=(
            "North-edge recreation and research belt with hotel/office "
            "repositioning and riverfront-adjacent multifamily filings."
        ),
        city_id="tempe",
    ),
    # =======================================================================
    # DIABLO_DOUBLE_BUTTE (1)
    # =======================================================================
    "Diablo Stadium Corridor": SubmarketMeta(
        name="Diablo Stadium Corridor",
        borough="DIABLO_DOUBLE_BUTTE",
        lat=33.4010,
        lng=-111.9595,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.80,
        capex=5600000.0,
        permit_vel=23.0,
        shift_ratio=1.38,
        sla=48.0,
        description=(
            "West Tempe stadium district with seasonal hospitality churn "
            "and spring-training-driven short-term demand."
        ),
        city_id="tempe",
    ),
    # =======================================================================
    # ALAMEDA (1)
    # =======================================================================
    "Alameda Park & Hudson Manor": SubmarketMeta(
        name="Alameda Park & Hudson Manor",
        borough="ALAMEDA",
        lat=33.4075,
        lng=-111.9370,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=4900000.0,
        permit_vel=22.0,
        shift_ratio=1.36,
        sla=47.0,
        description=(
            "Mid-century central neighborhoods with starter-home turnover, "
            "SES-panel permits, and rental-to-own conversions."
        ),
        city_id="tempe",
    ),
    # =======================================================================
    # MILLS_APACHE (2)
    # =======================================================================
    "Apache Boulevard Light Rail": SubmarketMeta(
        name="Apache Boulevard Light Rail",
        borough="MILLS_APACHE",
        lat=33.4147,
        lng=-111.9130,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=6800000.0,
        permit_vel=30.0,
        shift_ratio=1.46,
        sla=54.0,
        description=(
            "Light-rail spine with transit-oriented multifamily, "
            "international-food retail, and corridor infill permitting."
        ),
        city_id="tempe",
    ),
    "Mills Avenue & Emerald Park": SubmarketMeta(
        name="Mills Avenue & Emerald Park",
        borough="MILLS_APACHE",
        lat=33.4040,
        lng=-111.9220,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.81,
        capex=6100000.0,
        permit_vel=26.0,
        shift_ratio=1.42,
        sla=51.0,
        description=(
            "Mills/Emerald character area with duplex conversions and "
            "small-plex new builds feeding steady rental supply."
        ),
        city_id="tempe",
    ),
    # =======================================================================
    # KIWANIS_THE_LAKES (3)
    # =======================================================================
    "Kiwanis Park": SubmarketMeta(
        name="Kiwanis Park",
        borough="KIWANIS_THE_LAKES",
        lat=33.3820,
        lng=-111.8747,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.80,
        capex=5400000.0,
        permit_vel=24.0,
        shift_ratio=1.40,
        sla=50.0,
        description=(
            "Park-anchored east Tempe with townhome infill and "
            "roof/HVAC replacement cadence on 1970s-80s stock."
        ),
        city_id="tempe",
    ),
    "The Lakes": SubmarketMeta(
        name="The Lakes",
        borough="KIWANIS_THE_LAKES",
        lat=33.3720,
        lng=-111.9445,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.79,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.38,
        sla=49.0,
        description=(
            "Lakeside community near Baseline with stable owner-occupancy "
            "and water-adjacent amenity premiums."
        ),
        city_id="tempe",
    ),
    "Corona del Sol": SubmarketMeta(
        name="Corona del Sol",
        borough="KIWANIS_THE_LAKES",
        lat=33.3745,
        lng=-111.9050,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.82,
        capex=5700000.0,
        permit_vel=23.0,
        shift_ratio=1.41,
        sla=51.0,
        description=(
            "School-district-driven family market with pool permits and "
            "kitchen/bath remodel velocity."
        ),
        city_id="tempe",
    ),
    # =======================================================================
    # CORONA_SOUTH_TEMPE (1)
    # =======================================================================
    "South Tempe Rural Corridor": SubmarketMeta(
        name="South Tempe Rural Corridor",
        borough="CORONA_SOUTH_TEMPE",
        lat=33.3400,
        lng=-111.9200,
        zoom=13.5,
        pitch=40.0,
        base_lims=0.76,
        capex=4600000.0,
        permit_vel=21.0,
        shift_ratio=1.34,
        sla=47.0,
        description=(
            "South-edge pockets along the Chandler boundary with "
            "no-hoA infill lots and low-rise commercial pads."
        ),
        city_id="tempe",
    ),
}


TEMPE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_RIO_SALADO": BoroughMeta(
        name="DOWNTOWN_RIO_SALADO",
        center_lat=33.4270,
        center_lng=-111.9400,
        zoom=14.0,
        bbox=TEMPE_DIVISION_BBOXES["DOWNTOWN_RIO_SALADO"],
        submarkets=[k for k, v in TEMPE_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIO_SALADO"],
        city_id="tempe",
    ),
    "ASU_CAMPUS_EDGE": BoroughMeta(
        name="ASU_CAMPUS_EDGE",
        center_lat=33.4245,
        center_lng=-111.9225,
        zoom=14.0,
        bbox=TEMPE_DIVISION_BBOXES["ASU_CAMPUS_EDGE"],
        submarkets=[k for k, v in TEMPE_SUBMARKETS.items() if v.borough == "ASU_CAMPUS_EDGE"],
        city_id="tempe",
    ),
    "ESCALANTE_HISTORIC": BoroughMeta(
        name="ESCALANTE_HISTORIC",
        center_lat=33.4300,
        center_lng=-111.9025,
        zoom=14.0,
        bbox=TEMPE_DIVISION_BBOXES["ESCALANTE_HISTORIC"],
        submarkets=[k for k, v in TEMPE_SUBMARKETS.items() if v.borough == "ESCALANTE_HISTORIC"],
        city_id="tempe",
    ),
    "PAPAGO_NORTH_TEMPE": BoroughMeta(
        name="PAPAGO_NORTH_TEMPE",
        center_lat=33.4550,
        center_lng=-111.9400,
        zoom=13.5,
        bbox=TEMPE_DIVISION_BBOXES["PAPAGO_NORTH_TEMPE"],
        submarkets=[k for k, v in TEMPE_SUBMARKETS.items() if v.borough == "PAPAGO_NORTH_TEMPE"],
        city_id="tempe",
    ),
    "DIABLO_DOUBLE_BUTTE": BoroughMeta(
        name="DIABLO_DOUBLE_BUTTE",
        center_lat=33.4100,
        center_lng=-111.9700,
        zoom=13.5,
        bbox=TEMPE_DIVISION_BBOXES["DIABLO_DOUBLE_BUTTE"],
        submarkets=[k for k, v in TEMPE_SUBMARKETS.items() if v.borough == "DIABLO_DOUBLE_BUTTE"],
        city_id="tempe",
    ),
    "ALAMEDA": BoroughMeta(
        name="ALAMEDA",
        center_lat=33.4050,
        center_lng=-111.9425,
        zoom=14.0,
        bbox=TEMPE_DIVISION_BBOXES["ALAMEDA"],
        submarkets=[k for k, v in TEMPE_SUBMARKETS.items() if v.borough == "ALAMEDA"],
        city_id="tempe",
    ),
    "MILLS_APACHE": BoroughMeta(
        name="MILLS_APACHE",
        center_lat=33.4050,
        center_lng=-111.9100,
        zoom=13.5,
        bbox=TEMPE_DIVISION_BBOXES["MILLS_APACHE"],
        submarkets=[k for k, v in TEMPE_SUBMARKETS.items() if v.borough == "MILLS_APACHE"],
        city_id="tempe",
    ),
    "KIWANIS_THE_LAKES": BoroughMeta(
        name="KIWANIS_THE_LAKES",
        center_lat=33.3750,
        center_lng=-111.9200,
        zoom=13.5,
        bbox=TEMPE_DIVISION_BBOXES["KIWANIS_THE_LAKES"],
        submarkets=[k for k, v in TEMPE_SUBMARKETS.items() if v.borough == "KIWANIS_THE_LAKES"],
        city_id="tempe",
    ),
    "CORONA_SOUTH_TEMPE": BoroughMeta(
        name="CORONA_SOUTH_TEMPE",
        center_lat=33.3325,
        center_lng=-111.9075,
        zoom=13.0,
        bbox=TEMPE_DIVISION_BBOXES["CORONA_SOUTH_TEMPE"],
        submarkets=[k for k, v in TEMPE_SUBMARKETS.items() if v.borough == "CORONA_SOUTH_TEMPE"],
        city_id="tempe",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Register permits, code complaints (311), and
# general_offenses (crime). Do NOT register: arrests / calls-for-service
# (verified live but no FeedType slot / volume discipline — see docstring),
# the ABOR license stub (zero layers), the business surveys, or anything
# Maricopa-County-deeds-shaped (403 session-gated).
# ---------------------------------------------------------------------------
TEMPE_PERMITS_ENDPOINT = (
    "https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/"
    "building_permits/FeatureServer/0"
)
TEMPE_COMPLAINTS_311_ENDPOINT = (
    "https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/"
    "code_complaints/FeatureServer/0"
)
TEMPE_CRIME_ENDPOINT = (
    "https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/"
    "General_Offenses_(Open_Data)/FeatureServer/0"
)

TEMPE_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": TEMPE_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "AppliedDateDtm",
        "id_keys": ["PermitNum", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": TEMPE_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "AppliedDateDtm DESC",
            "scope": (
                "building_permits FeatureServer/0 (ArcGIS Hub org "
                "lQySeXwbBg53XWDi — NOT Socrata). 20,226 rows; native 4326 "
                "point geometry primary, WGS84 Latitude/Longitude attrs "
                "(3.0% null) as fallback; AppliedDateDtm watermark IS "
                "where-queryable (timestamp syntax); AppliedDate/IssuedDate "
                "string twins are plain YYYY-MM-DD; ExpiresDateDtm carries "
                "future-date sentinels (never an event date); contractor "
                "block + ProjectName never mapped"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "311": {
        "endpoint": TEMPE_COMPLAINTS_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "CaseOpenDate",
        "id_keys": ["CaseNo", "Id"],
        "topic_key": "topic_311",
        "interval_seconds": 180.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 30,
            "needs_geocode": True,
            "geocode_context": TEMPE_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "CaseOpenDate DESC",
            "scope": (
                "code_complaints FeatureServer/0 — code-compliance cases as "
                "the 311-family proxy (no raw 311 request log exists; only "
                "KPI summaries). 2,743 rows; native 4326 geometry; X_COORD/"
                "Y_COORD degree duplicates deliberately unmapped; 2 zero-"
                "coordinate sentinel rows (producer 0/0 guard drops). "
                "STALENESS CAVEAT: newest CaseOpenDate 1781247600000 = "
                "2026-06-12T07:00:00+00:00 on the 2026-08-28 probe (~11 "
                "weeks; quarterly publication suspected) — staleness alarm "
                "expected until the city resumes publication"
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
    "crime": {
        "endpoint": TEMPE_CRIME_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "OccurrenceDatetime",
        "id_keys": ["PrimaryKey", "OBJECTID"],
        "topic_key": "topic_crime",
        "interval_seconds": 1800.0,
        "producer_key": "crime",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "OccurrenceDatetime DESC",
            "state_plane_crs": TEMPE_STATE_PLANE_CRS,
            "state_plane_units": TEMPE_STATE_PLANE_UNITS,
            "state_plane_x_col": "XCoordinate",
            "state_plane_y_col": "YCoordinate",
            "scope": (
                "General_Offenses_(Open_Data) FeatureServer/0 — NIBRS-style "
                "offense rows with obfuscated addresses (ADR-0004 satisfied "
                "by coordinates). 380,724 rows, same-day fresh watermark. "
                "MIXED-CRS: geometry store is AZ State Plane Central WKID "
                "2223 (intl ft) but outSR=4326 lift delivers WGS84; "
                "Latitude/Longitude attrs are WGS84 degree fallbacks; "
                "XCoordinate/YCoordinate state-plane attrs never map. "
                "PrimaryKey is CHAR-padded (parser strips). ArrestsOpenData"
                "Denormalized (42,777 rows) verified live but unregistered —"
                " no FeedType slot"
            ),
            "field_map": CRIME_FIELD_MAP,
        },
    },
}


def get_tempe_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Tempe feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in TEMPE_FEED_SPECS:
        available = ", ".join(sorted(TEMPE_FEED_SPECS))
        raise KeyError(
            f"'{TEMPE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = TEMPE_FEED_SPECS[feed_name]
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
    metro_bbox=TEMPE_METRO_BBOX,
    division_bboxes=TEMPE_DIVISION_BBOXES,
    submarkets=TEMPE_SUBMARKETS,
    divisions=TEMPE_DIVISIONS,
    contains=is_in_tempe_metro,
)

__all__ = [
    "REGISTRATION",
    "TEMPE_CITY_ID",
    "TEMPE_COMPLAINTS_311_ENDPOINT",
    "TEMPE_CRIME_ENDPOINT",
    "TEMPE_DIVISIONS",
    "TEMPE_DIVISION_BBOXES",
    "TEMPE_FEED_SPECS",
    "TEMPE_GEOCODE_CONTEXT",
    "TEMPE_METRO_BBOX",
    "TEMPE_PERMITS_ENDPOINT",
    "TEMPE_STATE_PLANE_CRS",
    "TEMPE_STATE_PLANE_UNITS",
    "TEMPE_SUBMARKETS",
    "get_tempe_dataset",
    "is_in_greater_tempe_metro",
    "is_in_tempe_metro",
]
