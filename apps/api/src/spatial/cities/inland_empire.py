PERMITS_FIELD_MAP = {
    # OBJECTID is the OID fallback (Henderson precedent) so coordinate-less
    # rows stay addressable if a CASE_ID is ever missing client-side.
    "job_id": ["CASE_ID", "OBJECTID"],
    "issuance_date": ["APPLIED_DATE"],
    "status": ["CASE_STATUS"],
    "job_type": ["CASE_WORK_CLASS", "CASE_TYPE"],
    # APN is the county parcel number; the bbl slot is the generic
    # parcel-identifier carrier (boise/las_vegas APN precedent).
    "bbl": ["APN"],
    "proposed_units": ["UNIT_COUNT"],
    "proposed_stories": ["FLOOR_COUNT"],
}

CRIME_FIELD_MAP = {
    "incident_id": ["offenseid", "ObjectID"],
    "offense_type": ["nibrsdesc"],
    "occurred_date": ["offendate"],
    # datecreated is the record/report creation timestamp; dateupdated is
    # maintenance noise and deliberately not a candidate.
    "reported_date": ["datecreated"],
    "borough": ["COMMUNITY"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

DROPPED_NOISE_COLUMNS = (
    "SHAPE.STArea()",
    "SHAPE.STLength()",
    "dateupdated",
    "callid",
    "InstanceID",
    "GlobalID",
    "rpdunique",
)

"""Inland Empire (Riverside County anchor) spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the Inland Empire
metro (US-222).

JURISDICTIONAL ANCHOR — read this first. "Inland Empire" spans Riverside and
San Bernardino counties, but the repo norm is a single-jurisdiction anchor
(single-city registrations, not county composites). The verified-feed evidence
picks the anchor unambiguously:

* **Riverside County** (anchor; the miami_dade county exception): Accela
  building-permit ledger PLUS_ACTIVITIES (1,487,546 PERMIT-module rows of
  2,142,939 total, live, ~85 applications/day) plus DEH permit ledgers.
* **City of Riverside**: no permits/311/SLA/deeds feeds on its AGOL org
  (Fu2oOWg1Aw7azh41) — only form surveys, planning views and its crime feed
  (registered below, city-of-Riverside scope, ADR 0004 satisfied).
* **San Bernardino County** (Hub org aA3snZwJfFkVyDuP is public): NO
  transactional feeds at all — only Fire burn-permit views and static
  assessor/TRA/parcel layers. Documented, not registered.

The permits feed is county-wide (its cases span Corona to Coachella), and the
crime feed is City of Riverside only — both scopes are stated here rather
than silently blended. Not a "county composite": every feed is one official
jurisdiction with its scope declared.

Live-probe evidence (all probed 2026-08-28 UTC, this stream):

* PERMITS — ``PLUS_ACTIVITIES`` on the county ArcGIS Server 10.61 at
  ``gis.countyofriverside.us`` (a MapServer layer, layer id 280 of
  ``OpenData/General`` — same ``query`` contract; ``ArcGISClient`` handles
  both). ``where=CASE_MODULE = 'PERMIT'`` filters to building/online-permit
  applications (1,487,546 rows; total 2,142,939). Watermark ``APPLIED_DATE``
  newest verbatim ``1787019074000`` = 2026-08-18T02:11:14+00:00 — the layer
  publishes in batches with a ~10-day lag (window counts since 2026-08-10:
  852 rows; since 2026-08-01: 1,489), hence the 14-day cadence. TRAP: the
  unfiltered layer carries FUTURE-dated rows (a PLAN-module extension case
  with APPLIED_DATE 1798587280000 = 2026-12-29T23:34:40+00:00) — the module
  filter excludes the observed sentinel and the scheduler's US-111
  future-watermark guard covers the rest. APPLIED_DATE IS where-clause
  queryable — but this host REJECTS ISO-string date comparisons (ArcGIS 400
  "Unable to complete operation") and only accepts ANSI ``date 'YYYY-MM-DD'``
  literals, so the spine hold must add ``gis.countyofriverside.us`` to
  ``ANSI_DATE_LITERAL_HOSTS`` (src/producers/watermarks.py). Geometry is
  parcel polygons in CA State Plane Zone VI US-survey feet (wkid 102646);
  queries with ``outSR=4326`` return WGS84 rings, reduced to a centroid by
  ``ArcGISClient._geometry_to_lng_lat`` — the state-plane coordinates never
  enter the record. No address, valuation, or zip column exists: ``cost``
  stays 0.0, no geocode is declared, and a geometry-less row drops honestly
  (nothing to geocode). ``maxRecordCount`` 2000.
* CRIME — City of Riverside ``View_CrimesRPD/FeatureServer/4`` ("Crime (Last
  Year to Date)", services.arcgis.com, org Fu2oOWg1Aw7azh41): 77,234 rows,
  live to the probe day (offendate newest verbatim ``1787882766890`` =
  2026-08-28T02:06:06.890000+00:00). Native WGS84 point geometry (outSR=4326)
  plus ``BLOCK_ADDRESS`` — ADR 0004 satisfied; no geocode declared. NIBRS
  fields (``nibrsdesc``/``nibrscode``) carry offense text; ``COMMUNITY`` is
  the city's community-planning-area name (real borough candidate).
  ``maxRecordCount`` 2000; OID field is camelCase ``ObjectID``.
* Considered and NOT registered: ``Septic_Permits/FeatureServer/0``
  (17,263 rows, SUBMITTED_DATE newest 1787616000000 = 2026-08-25) and
  ``Rivco_Well_Permits/FeatureServer/2`` (32,218 rows, Submitted_Date newest
  1787184000000 = 2026-08-20) — environmental-health permits in the same
  PERMITS family slot as PLUS_ACTIVITIES; ``AllPermits_2015_2019`` (stale,
  ends 2019); county crime views ``10_Min_Crime``/``15_Minute_Crime``
  (untouched since 2021); Treasurer tax-sale inventories (episodic auction
  lists, not a deed stream); the AssessorTables service (published shell:
  zero layers/tables). Rivco/riversideca Hub front-doors are a private org
  (search API 401) — the county's real door is its AGOL org and ArcGIS
  Server; 311, business-license (SLA), and recorded-deed feeds are absent
  everywhere probed. PARTIAL registration: PERMITS + CRIME.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

INLAND_EMPIRE_CITY_ID: str = "inland_empire"

# Riverside County anchor bbox: Corona/El Cerrito west, the San Gorgonio
# Pass / San Bernardino county line north (max_lat 34.03 — low enough to
# exclude the SW San Bernardino County sliver: Ontario 34.06, Fontana 34.09,
# Rancho Cucamonga 34.11), Temecula county line south, Coachella Valley
# through the north Salton Sea shore east. Far-east desert (Blythe/Palo
# Verde) is outside the Inland Empire definition. Riverside downtown
# (33.98, -117.38) is the center, not the extent — Palm Springs, Temecula,
# and Moreno Valley must sit inside.
INLAND_EMPIRE_METRO_BBOX: dict[str, float] = {
    "min_lat": 33.40,
    "max_lat": 34.03,
    "min_lng": -117.67,
    "max_lng": -116.05,
}

# 7 divisions, hand-authored on verified landmarks (city halls, Mission Inn,
# Moreno Valley Mall, Old Town Temecula, El Paseo). Borough resolution at
# ingest comes from coordinates via get_division_for_coordinate, so bboxes
# need only be sane and contain their own submarket centers.
INLAND_EMPIRE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_RIVERSIDE": {
        "min_lat": 33.955,
        "max_lat": 34.005,
        "min_lng": -117.420,
        "max_lng": -117.290,
    },
    "CORONA_NORCO": {
        "min_lat": 33.850,
        "max_lat": 33.960,
        "min_lng": -117.620,
        "max_lng": -117.500,
    },
    "MORENO_VALLEY": {
        "min_lat": 33.880,
        "max_lat": 33.970,
        "min_lng": -117.320,
        "max_lng": -117.200,
    },
    "MENIFEE_PERRIS": {
        "min_lat": 33.660,
        "max_lat": 33.830,
        "min_lng": -117.280,
        "max_lng": -117.120,
    },
    "TEMECULA_MURRIETA": {
        "min_lat": 33.450,
        "max_lat": 33.600,
        "min_lng": -117.250,
        "max_lng": -117.100,
    },
    "HEMET_SAN_JACINTO": {
        "min_lat": 33.700,
        "max_lat": 33.820,
        "min_lng": -117.030,
        "max_lng": -116.900,
    },
    "COACHELLA_VALLEY": {
        "min_lat": 33.600,
        "max_lat": 33.880,
        "min_lng": -116.620,
        "max_lng": -116.100,
    },
}


def is_in_inland_empire_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Inland Empire (Riverside County) bounds."""
    if lat is None or lng is None:
        return False
    return (
        INLAND_EMPIRE_METRO_BBOX["min_lat"] <= lat <= INLAND_EMPIRE_METRO_BBOX["max_lat"]
        and INLAND_EMPIRE_METRO_BBOX["min_lng"] <= lng <= INLAND_EMPIRE_METRO_BBOX["max_lng"]
    )


is_in_greater_inland_empire_metro = is_in_inland_empire_metro


INLAND_EMPIRE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_RIVERSIDE (2)
    # =======================================================================
    "Downtown Riverside": SubmarketMeta(
        name="Downtown Riverside",
        borough="DOWNTOWN_RIVERSIDE",
        lat=33.9803,
        lng=-117.3769,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=34.0,
        shift_ratio=1.49,
        sla=54.0,
        description="Mission Inn historic core with the Fox Performing Arts Center, adaptive-reuse hotels, and the county's densest permit corridor.",
        city_id="inland_empire",
    ),
    "UCR Eastside": SubmarketMeta(
        name="UCR Eastside",
        borough="DOWNTOWN_RIVERSIDE",
        lat=33.9739,
        lng=-117.3265,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.82,
        capex=6900000.0,
        permit_vel=26.0,
        shift_ratio=1.42,
        sla=49.0,
        description="University district east of downtown with student-housing infill, campus-adjacent retail, and steady multifamily permitting.",
        city_id="inland_empire",
    ),
    # =======================================================================
    # CORONA_NORCO (2)
    # =======================================================================
    "Corona": SubmarketMeta(
        name="Corona",
        borough="CORONA_NORCO",
        lat=33.8754,
        lng=-117.5662,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.84,
        capex=8200000.0,
        permit_vel=29.0,
        shift_ratio=1.45,
        sla=51.0,
        description="I-15/91 logistics-and-roofline city at the county's west gate with tract turnover and industrial infill permits.",
        city_id="inland_empire",
    ),
    "Norco": SubmarketMeta(
        name="Norco",
        borough="CORONA_NORCO",
        lat=33.9311,
        lng=-117.5504,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.80,
        capex=6100000.0,
        permit_vel=22.0,
        shift_ratio=1.38,
        sla=47.0,
        description="Horsetown USA half-acre-lot stock with barn-and-arena improvement permits and slow, stable turnover.",
        city_id="inland_empire",
    ),
    # =======================================================================
    # MORENO_VALLEY (1)
    # =======================================================================
    "Moreno Valley Central": SubmarketMeta(
        name="Moreno Valley Central",
        borough="MORENO_VALLEY",
        lat=33.9410,
        lng=-117.2720,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=8600000.0,
        permit_vel=30.0,
        shift_ratio=1.46,
        sla=52.0,
        description="Mall-and-medical core of one of the Inland Empire's fastest-growing cities with warehouse-adjacent housing demand.",
        city_id="inland_empire",
    ),
    # =======================================================================
    # MENIFEE_PERRIS (2)
    # =======================================================================
    "Perris": SubmarketMeta(
        name="Perris",
        borough="MENIFEE_PERRIS",
        lat=33.7860,
        lng=-117.2130,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.78,
        capex=6600000.0,
        permit_vel=25.0,
        shift_ratio=1.41,
        sla=46.0,
        description="Rail-and-warehouse valley south of Riverside with entry-price turnover and large master-planned pipelines.",
        city_id="inland_empire",
    ),
    "Menifee": SubmarketMeta(
        name="Menifee",
        borough="MENIFEE_PERRIS",
        lat=33.7176,
        lng=-117.1707,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.81,
        capex=7900000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=50.0,
        description="Retirement-growth city of tract builders and 55+ communities with the county's steadiest new-build cadence.",
        city_id="inland_empire",
    ),
    # =======================================================================
    # TEMECULA_MURRIETA (2)
    # =======================================================================
    "Old Town Temecula": SubmarketMeta(
        name="Old Town Temecula",
        borough="TEMECULA_MURRIETA",
        lat=33.4903,
        lng=-117.1486,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.89,
        capex=10400000.0,
        permit_vel=33.0,
        shift_ratio=1.52,
        sla=55.0,
        description="Wine-country gateway with hotel/restaurant adaptive reuse and the metro's highest commercial valuations.",
        city_id="inland_empire",
    ),
    "Murrieta": SubmarketMeta(
        name="Murrieta",
        borough="TEMECULA_MURRIETA",
        lat=33.5577,
        lng=-117.2028,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=8800000.0,
        permit_vel=27.0,
        shift_ratio=1.43,
        sla=51.0,
        description="Family-suburb spine along the 15/215 junction with medical-office growth and steady tract-infill permits.",
        city_id="inland_empire",
    ),
    # =======================================================================
    # HEMET_SAN_JACINTO (2)
    # =======================================================================
    "Hemet": SubmarketMeta(
        name="Hemet",
        borough="HEMET_SAN_JACINTO",
        lat=33.7476,
        lng=-116.9718,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5800000.0,
        permit_vel=23.0,
        shift_ratio=1.37,
        sla=45.0,
        description="San Jacinto Valley retirement market with low-basis stock and value-add renovation permits.",
        city_id="inland_empire",
    ),
    "San Jacinto": SubmarketMeta(
        name="San Jacinto",
        borough="HEMET_SAN_JACINTO",
        lat=33.7812,
        lng=-116.9586,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.75,
        capex=5400000.0,
        permit_vel=21.0,
        shift_ratio=1.35,
        sla=44.0,
        description="Valley-edge city with starter-home turnover and small multifamily conversions.",
        city_id="inland_empire",
    ),
    # =======================================================================
    # COACHELLA_VALLEY (3)
    # =======================================================================
    "Palm Springs": SubmarketMeta(
        name="Palm Springs",
        borough="COACHELLA_VALLEY",
        lat=33.8295,
        lng=-116.5454,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.87,
        capex=9600000.0,
        permit_vel=31.0,
        shift_ratio=1.47,
        sla=53.0,
        description="Mid-century resort core with hotel renovation, vacation-rental churn, and premium second-home turnover.",
        city_id="inland_empire",
    ),
    "Palm Desert": SubmarketMeta(
        name="Palm Desert",
        borough="COACHELLA_VALLEY",
        lat=33.7166,
        lng=-116.3762,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=9100000.0,
        permit_vel=28.0,
        shift_ratio=1.45,
        sla=52.0,
        description="El Paseo retail spine and country-club stock with steady high-valuation alteration permits.",
        city_id="inland_empire",
    ),
    "Indio": SubmarketMeta(
        name="Indio",
        borough="COACHELLA_VALLEY",
        lat=33.7206,
        lng=-116.2190,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.82,
        capex=7400000.0,
        permit_vel=27.0,
        shift_ratio=1.42,
        sla=49.0,
        description="East-valley growth city with festival-economy demand and tract-builder pipelines.",
        city_id="inland_empire",
    ),
}


INLAND_EMPIRE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_RIVERSIDE": BoroughMeta(
        name="DOWNTOWN_RIVERSIDE",
        center_lat=33.9803,
        center_lng=-117.3769,
        zoom=14.0,
        bbox=INLAND_EMPIRE_DIVISION_BBOXES["DOWNTOWN_RIVERSIDE"],
        submarkets=[k for k, v in INLAND_EMPIRE_SUBMARKETS.items() if v.borough == "DOWNTOWN_RIVERSIDE"],
        city_id="inland_empire",
    ),
    "CORONA_NORCO": BoroughMeta(
        name="CORONA_NORCO",
        center_lat=33.8754,
        center_lng=-117.5662,
        zoom=13.5,
        bbox=INLAND_EMPIRE_DIVISION_BBOXES["CORONA_NORCO"],
        submarkets=[k for k, v in INLAND_EMPIRE_SUBMARKETS.items() if v.borough == "CORONA_NORCO"],
        city_id="inland_empire",
    ),
    "MORENO_VALLEY": BoroughMeta(
        name="MORENO_VALLEY",
        center_lat=33.9410,
        center_lng=-117.2720,
        zoom=13.5,
        bbox=INLAND_EMPIRE_DIVISION_BBOXES["MORENO_VALLEY"],
        submarkets=[k for k, v in INLAND_EMPIRE_SUBMARKETS.items() if v.borough == "MORENO_VALLEY"],
        city_id="inland_empire",
    ),
    "MENIFEE_PERRIS": BoroughMeta(
        name="MENIFEE_PERRIS",
        center_lat=33.7860,
        center_lng=-117.2130,
        zoom=13.0,
        bbox=INLAND_EMPIRE_DIVISION_BBOXES["MENIFEE_PERRIS"],
        submarkets=[k for k, v in INLAND_EMPIRE_SUBMARKETS.items() if v.borough == "MENIFEE_PERRIS"],
        city_id="inland_empire",
    ),
    "TEMECULA_MURRIETA": BoroughMeta(
        name="TEMECULA_MURRIETA",
        center_lat=33.4903,
        center_lng=-117.1486,
        zoom=13.5,
        bbox=INLAND_EMPIRE_DIVISION_BBOXES["TEMECULA_MURRIETA"],
        submarkets=[k for k, v in INLAND_EMPIRE_SUBMARKETS.items() if v.borough == "TEMECULA_MURRIETA"],
        city_id="inland_empire",
    ),
    "HEMET_SAN_JACINTO": BoroughMeta(
        name="HEMET_SAN_JACINTO",
        center_lat=33.7476,
        center_lng=-116.9718,
        zoom=13.0,
        bbox=INLAND_EMPIRE_DIVISION_BBOXES["HEMET_SAN_JACINTO"],
        submarkets=[k for k, v in INLAND_EMPIRE_SUBMARKETS.items() if v.borough == "HEMET_SAN_JACINTO"],
        city_id="inland_empire",
    ),
    "COACHELLA_VALLEY": BoroughMeta(
        name="COACHELLA_VALLEY",
        center_lat=33.8295,
        center_lng=-116.5454,
        zoom=12.5,
        bbox=INLAND_EMPIRE_DIVISION_BBOXES["COACHELLA_VALLEY"],
        submarkets=[k for k, v in INLAND_EMPIRE_SUBMARKETS.items() if v.borough == "COACHELLA_VALLEY"],
        city_id="inland_empire",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register Septic_Permits, Rivco_Well_Permits,
# AllPermits_2015_2019, the 2021 county crime views, tax-sale inventories,
# the empty AssessorTables shell, or the private Rivco Hub placeholders.
# ---------------------------------------------------------------------------
INLAND_EMPIRE_PERMITS_ENDPOINT = (
    "https://gis.countyofriverside.us/arcgis_mapping/rest/services/"
    "OpenData/General/MapServer/280"
)
INLAND_EMPIRE_CRIME_ENDPOINT = (
    "https://services.arcgis.com/Fu2oOWg1Aw7azh41/arcgis/rest/services/"
    "View_CrimesRPD/FeatureServer/4"
)

INLAND_EMPIRE_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": INLAND_EMPIRE_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "APPLIED_DATE",
        "id_keys": ["CASE_ID", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 14,
            "where": "CASE_MODULE = 'PERMIT'",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "scope": (
                "Riverside County Accela PLUS_ACTIVITIES (MapServer layer 280 "
                "on gis.countyofriverside.us) filtered to CASE_MODULE='PERMIT' "
                "building/online-permit applications. ANSI-date-only host: "
                "ISO-string watermark comparisons return ArcGIS 400 — the "
                "host must join ANSI_DATE_LITERAL_HOSTS. State-plane polygon "
                "source (wkid 102646) reprojected server-side via outSR=4326; "
                "centroid lift client-side. No address/valuation/zip columns: "
                "cost 0.0, no geocode, geometry-less rows drop."
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "crime": {
        "endpoint": INLAND_EMPIRE_CRIME_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "offendate",
        "id_keys": ["offenseid", "ObjectID"],
        "topic_key": "topic_crime",
        "interval_seconds": 300.0,
        "producer_key": "crime",
        "extra": {
            "expected_cadence_days": 7,
            "oid_field": "ObjectID",
            "max_record_count": 2000,
            "scope": (
                "City of Riverside PD 'Crime (Last Year to Date)' "
                "(View_CrimesRPD/FeatureServer/4) — city-of-Riverside scope "
                "inside the county-anchored metro. Native WGS84 point "
                "geometry (outSR=4326) + BLOCK_ADDRESS per ADR 0004; COMMUNITY "
                "is the borough candidate. Rolling last-year-to-date window: "
                "min(date) is not staleness evidence."
            ),
            "field_map": CRIME_FIELD_MAP,
        },
    },
}


def get_inland_empire_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Inland Empire feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in INLAND_EMPIRE_FEED_SPECS:
        available = ", ".join(sorted(INLAND_EMPIRE_FEED_SPECS))
        raise KeyError(
            f"'{INLAND_EMPIRE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = INLAND_EMPIRE_FEED_SPECS[feed_name]
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
    metro_bbox=INLAND_EMPIRE_METRO_BBOX,
    division_bboxes=INLAND_EMPIRE_DIVISION_BBOXES,
    submarkets=INLAND_EMPIRE_SUBMARKETS,
    divisions=INLAND_EMPIRE_DIVISIONS,
    contains=is_in_inland_empire_metro,
)

__all__ = [
    "INLAND_EMPIRE_CITY_ID",
    "INLAND_EMPIRE_CRIME_ENDPOINT",
    "INLAND_EMPIRE_DIVISIONS",
    "INLAND_EMPIRE_DIVISION_BBOXES",
    "INLAND_EMPIRE_FEED_SPECS",
    "INLAND_EMPIRE_METRO_BBOX",
    "INLAND_EMPIRE_PERMITS_ENDPOINT",
    "INLAND_EMPIRE_SUBMARKETS",
    "REGISTRATION",
    "get_inland_empire_dataset",
    "is_in_greater_inland_empire_metro",
    "is_in_inland_empire_metro",
]
