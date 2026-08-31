COMPLAINTS_311_FIELD_MAP = {
    "incident_id": ["FID", "GlobalID"],
    "complaint_type": ["Title"],
    "created_date": ["CreatedOn"],
    "status": ["StatusText"],
}

SLA_FIELD_MAP = {
    "license_id": ["UID", "GlobalID"],
    "dba": ["Name"],
    "premises_name": ["Name"],
    "address_street": ["MatchAddr"],
    "status": ["Active"],
}

DEEDS_FIELD_MAP = {
    "doc_id": ["CITYDEED", "OBJECTID_1"],
    "recorded_date": ["DATE_"],
    "doc_type": ["ACQDIS"],
}

FIELD_MAP = {
    "311": COMPLAINTS_311_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Eugene, OR"

"""Eugene, OR spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Eugene
(western Oregon, Lane County).

Eugene is a THREE-FEED PARTIAL metro:

* DEEDS — ``CityLandDeeds`` (FeatureServer/0 on
  ``services3.arcgis.com/F7NiRLGNbA2hh7gE``, Tier 1). City-owned property
  records (acquisitions/dispositions) with polygon geometry, DATE_ watermark
  live to 2026-06-30. Lane County's own deed/sales records are web-portal-only
  (LMD-PRO / citizenserviceportal) — not reachable as a bulk feed.
* COMPLAINTS_311 — ``2020_2021CampingWorkOrders`` (FeatureServer/0 on the
  same server, Tier 1). Code-enforcement/encampment service requests from the
  city's PDD (Planning & Development) camping work-order archive (last
  updated 2021). Companion: ``HistoricalCampingWorkOrders`` (25,171 rows).
* SLA — ``Food_Service_Establishments_Updated_VIEW_CBE`` (FeatureServer/0,
  Tier 1). Food service establishment business licenses maintained by the
  city's Code & Business Enforcement division. Snapshot with no date column
  (hasStaticData: True, empty watermark_col, snapshot mode).

Permits are NOT registered: the city's PDD ebuild permit system
(pdd.eugene-or.gov/ebuild) is an Accela-style web portal with no public bulk
API. CIP project layers (Current_Projects, InfrastructureProjects) are
capital projects, not permit records. Lane County permit data is not publicly
bulk-accessible.

Live-probe caveats (original probe 2026-08-28, stream west-eugene):

* The ticket's candidate domain ``eugene.opendata.arcgis.com`` is dead (404,
  no domain record). The real hosts are ``mapping.eugene-or.gov`` (ArcGIS Hub)
  and ``services3.arcgis.com/F7NiRLGNbA2hh7gE`` (ArcGIS Server).
* Oregon State Plane North (WKID 2914) is the store SR for most layers;
  ``ArcGISClient`` requests ``outSR=4326`` for server-side WGS84 reprojection.
  Verified working on all three feeds.
* Food_Service_Establishments stores SR 102100 (Web Mercator); same outSR=4326
  lift works. DisplayX/DisplayY attributes are native decimal-degree lat/lng
  but geometry lift is the sole coordinate source (Bend discipline).
* CityLandDeeds is polygon geometry → centroid via ``ArcGISClient._geometry_to_lng_lat``.
  CampingWorkOrders is point geometry.
* No future-date sentinels found on CityLandDeeds DATE_ (max 2026-06-30).
  No ANSI-date-only hosts — all ArcGIS FeatureServers with esriFieldTypeDate.
* No mixed-CRS traps beyond the standard state-plane lift.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

EUGENE_CITY_ID: str = "eugene"
EUGENE_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Eugene, OR metro bbox (Lane County, Willamette Valley).
# Covers the full Eugene urban area including Springfield and Glenwood to
# the east, Santa Clara to the north, and the Bethel area to the west.
EUGENE_METRO_BBOX: dict[str, float] = {
    "min_lat": 43.96,
    "max_lat": 44.14,
    "min_lng": -123.30,
    "max_lng": -122.96,
}

# 8 Eugene divisions. Hand-authored from official neighborhood association
# boundaries and known submarket areas. Borough resolution at ingest comes
# from coordinates via get_division_for_coordinate.
EUGENE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 44.044,
        "max_lat": 44.058,
        "min_lng": -123.100,
        "max_lng": -123.080,
    },
    "WHITAKER": {
        "min_lat": 44.054,
        "max_lat": 44.070,
        "min_lng": -123.108,
        "max_lng": -123.090,
    },
    "FRIENDLY": {
        "min_lat": 44.020,
        "max_lat": 44.045,
        "min_lng": -123.120,
        "max_lng": -123.070,
    },
    "SOUTH_EUGENE": {
        "min_lat": 43.990,
        "max_lat": 44.025,
        "min_lng": -123.120,
        "max_lng": -123.055,
    },
    "CAL_YOUNG": {
        "min_lat": 44.060,
        "max_lat": 44.085,
        "min_lng": -123.070,
        "max_lng": -123.035,
    },
    "SANTA_CLARA": {
        "min_lat": 44.090,
        "max_lat": 44.135,
        "min_lng": -123.130,
        "max_lng": -123.050,
    },
    "BETHEL": {
        "min_lat": 44.050,
        "max_lat": 44.090,
        "min_lng": -123.180,
        "max_lng": -123.120,
    },
    "CHURCHILL": {
        "min_lat": 44.010,
        "max_lat": 44.050,
        "min_lng": -123.200,
        "max_lng": -123.130,
    },
}


def is_in_eugene_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Eugene metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        EUGENE_METRO_BBOX["min_lat"] <= lat <= EUGENE_METRO_BBOX["max_lat"]
        and EUGENE_METRO_BBOX["min_lng"] <= lng <= EUGENE_METRO_BBOX["max_lng"]
    )


is_in_greater_eugene_metro = is_in_eugene_metro


EUGENE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN",
        lat=44.0510,
        lng=-123.0920,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=28.0,
        shift_ratio=1.45,
        sla=50.0,
        description="Eugene's downtown core with the 5th Street Market District, Hult Center, and the Broadway retail corridor — the metro's primary office and entertainment hub.",
        city_id="eugene",
    ),
    "Jefferson Westside": SubmarketMeta(
        name="Jefferson Westside",
        borough="DOWNTOWN",
        lat=44.0530,
        lng=-123.0980,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.84,
        capex=5800000.0,
        permit_vel=25.0,
        shift_ratio=1.43,
        sla=48.0,
        description="West-side downtown residential neighborhood with historic craftsman bungalows, infill apartments, and proximity to the riverfront.",
        city_id="eugene",
    ),
    # =======================================================================
    # WHITAKER (2)
    # =======================================================================
    "Whiteaker": SubmarketMeta(
        name="Whiteaker",
        borough="WHITAKER",
        lat=44.0600,
        lng=-123.0980,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.86,
        capex=5900000.0,
        permit_vel=27.0,
        shift_ratio=1.48,
        sla=55.0,
        description="Eugene's historic working-class neighborhood turned arts district with Blair Boulevard restaurant row, breweries, and live-work artist compounds.",
        city_id="eugene",
    ),
    "Trainsong": SubmarketMeta(
        name="Trainsong",
        borough="WHITAKER",
        lat=44.0640,
        lng=-123.1020,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=4800000.0,
        permit_vel=20.0,
        shift_ratio=1.38,
        sla=42.0,
        description="Rail-adjacent industrial-edge neighborhood transitioning with new infill and light-industrial redevelopment.",
        city_id="eugene",
    ),
    # =======================================================================
    # FRIENDLY (2)
    # =======================================================================
    "Friendly": SubmarketMeta(
        name="Friendly",
        borough="FRIENDLY",
        lat=44.0320,
        lng=-123.0980,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.85,
        capex=5500000.0,
        permit_vel=24.0,
        shift_ratio=1.44,
        sla=50.0,
        description="South-central residential neighborhood around Friendly Street with mature tree canopy, mid-century homes, and steady renovation permits.",
        city_id="eugene",
    ),
    "South University": SubmarketMeta(
        name="South University",
        borough="FRIENDLY",
        lat=44.0350,
        lng=-123.0780,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.83,
        capex=5200000.0,
        permit_vel=23.0,
        shift_ratio=1.42,
        sla=46.0,
        description="University of Oregon adjacent student and faculty housing with high turnover, rental conversions, and steady remodel permits.",
        city_id="eugene",
    ),
    # =======================================================================
    # SOUTH_EUGENE (2)
    # =======================================================================
    "South Eugene": SubmarketMeta(
        name="South Eugene",
        borough="SOUTH_EUGENE",
        lat=44.0100,
        lng=-123.0900,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.87,
        capex=6800000.0,
        permit_vel=26.0,
        shift_ratio=1.46,
        sla=52.0,
        description="Upper south hills with premium residential stock, Spencer Butte views, and the highest-valued single-family homes in the metro.",
        city_id="eugene",
    ),
    "Fairmount": SubmarketMeta(
        name="Fairmount",
        borough="SOUTH_EUGENE",
        lat=44.0200,
        lng=-123.0650,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.84,
        capex=6100000.0,
        permit_vel=22.0,
        shift_ratio=1.41,
        sla=48.0,
        description="Southeast Eugene foothills neighborhood with University of Oregon family housing, multi-family conversions, and steady renovation permits.",
        city_id="eugene",
    ),
    # =======================================================================
    # CAL_YOUNG (2)
    # =======================================================================
    "Cal Young": SubmarketMeta(
        name="Cal Young",
        borough="CAL_YOUNG",
        lat=44.0700,
        lng=-123.0520,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=6400000.0,
        permit_vel=25.0,
        shift_ratio=1.44,
        sla=50.0,
        description="Northeast Eugene's primary commercial corridor with Coburg Road retail, Olympic Village, and the area's densest suburban multifamily stock.",
        city_id="eugene",
    ),
    "Harlow": SubmarketMeta(
        name="Harlow",
        borough="CAL_YOUNG",
        lat=44.0770,
        lng=-123.0600,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.82,
        capex=5300000.0,
        permit_vel=21.0,
        shift_ratio=1.39,
        sla=44.0,
        description="Mid-century suburban neighborhood of ranch homes, duplex infill, and aging-housing-stock renovation permits.",
        city_id="eugene",
    ),
    # =======================================================================
    # SANTA_CLARA (1)
    # =======================================================================
    "Santa Clara": SubmarketMeta(
        name="Santa Clara",
        borough="SANTA_CLARA",
        lat=44.1100,
        lng=-123.0900,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=5600000.0,
        permit_vel=22.0,
        shift_ratio=1.40,
        sla=46.0,
        description="Northern Eugene suburban corridor with River Road commercial strip, new single-family subdivisions, and farm-adjacent residential",
        city_id="eugene",
    ),
    # =======================================================================
    # BETHEL (2)
    # =======================================================================
    "Bethel": SubmarketMeta(
        name="Bethel",
        borough="BETHEL",
        lat=44.0700,
        lng=-123.1550,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=5100000.0,
        permit_vel=23.0,
        shift_ratio=1.41,
        sla=45.0,
        description="West Eugene's largest suburban neighborhood with Royal Avenue retail, new infrastructure, and the metro's most affordable single-family stock.",
        city_id="eugene",
    ),
    "West Eugene": SubmarketMeta(
        name="West Eugene",
        borough="BETHEL",
        lat=44.0700,
        lng=-123.1700,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.80,
        capex=4900000.0,
        permit_vel=20.0,
        shift_ratio=1.37,
        sla=42.0,
        description="Western industrial and residential edge with the West Eugene Enterprise Zone, light-industrial parks, and workforce housing stock.",
        city_id="eugene",
    ),
    # =======================================================================
    # CHURCHILL (2)
    # =======================================================================
    "Churchill": SubmarketMeta(
        name="Churchill",
        borough="CHURCHILL",
        lat=44.0300,
        lng=-123.1650,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=5300000.0,
        permit_vel=22.0,
        shift_ratio=1.42,
        sla=47.0,
        description="Southwest Eugene residential area around Churchill High School with mid-century ranch homes, rolling hills, and steady renovation permits.",
        city_id="eugene",
    ),
    "Amazon": SubmarketMeta(
        name="Amazon",
        borough="CHURCHILL",
        lat=44.0350,
        lng=-123.1500,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=5400000.0,
        permit_vel=23.0,
        shift_ratio=1.42,
        sla=47.0,
        description="Amazon Creek corridor residential area with creek-side parks, mixed zoning, and the Amazon Marketplace commercial node.",
        city_id="eugene",
    ),
}


EUGENE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=44.0510,
        center_lng=-123.0920,
        zoom=14.0,
        bbox=EUGENE_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in EUGENE_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="eugene",
    ),
    "WHITAKER": BoroughMeta(
        name="WHITAKER",
        center_lat=44.0600,
        center_lng=-123.0980,
        zoom=14.0,
        bbox=EUGENE_DIVISION_BBOXES["WHITAKER"],
        submarkets=[k for k, v in EUGENE_SUBMARKETS.items() if v.borough == "WHITAKER"],
        city_id="eugene",
    ),
    "FRIENDLY": BoroughMeta(
        name="FRIENDLY",
        center_lat=44.0320,
        center_lng=-123.0980,
        zoom=14.0,
        bbox=EUGENE_DIVISION_BBOXES["FRIENDLY"],
        submarkets=[k for k, v in EUGENE_SUBMARKETS.items() if v.borough == "FRIENDLY"],
        city_id="eugene",
    ),
    "SOUTH_EUGENE": BoroughMeta(
        name="SOUTH_EUGENE",
        center_lat=44.0100,
        center_lng=-123.0900,
        zoom=13.5,
        bbox=EUGENE_DIVISION_BBOXES["SOUTH_EUGENE"],
        submarkets=[k for k, v in EUGENE_SUBMARKETS.items() if v.borough == "SOUTH_EUGENE"],
        city_id="eugene",
    ),
    "CAL_YOUNG": BoroughMeta(
        name="CAL_YOUNG",
        center_lat=44.0700,
        center_lng=-123.0520,
        zoom=13.5,
        bbox=EUGENE_DIVISION_BBOXES["CAL_YOUNG"],
        submarkets=[k for k, v in EUGENE_SUBMARKETS.items() if v.borough == "CAL_YOUNG"],
        city_id="eugene",
    ),
    "SANTA_CLARA": BoroughMeta(
        name="SANTA_CLARA",
        center_lat=44.1100,
        center_lng=-123.0900,
        zoom=13.0,
        bbox=EUGENE_DIVISION_BBOXES["SANTA_CLARA"],
        submarkets=[k for k, v in EUGENE_SUBMARKETS.items() if v.borough == "SANTA_CLARA"],
        city_id="eugene",
    ),
    "BETHEL": BoroughMeta(
        name="BETHEL",
        center_lat=44.0700,
        center_lng=-123.1550,
        zoom=13.5,
        bbox=EUGENE_DIVISION_BBOXES["BETHEL"],
        submarkets=[k for k, v in EUGENE_SUBMARKETS.items() if v.borough == "BETHEL"],
        city_id="eugene",
    ),
    "CHURCHILL": BoroughMeta(
        name="CHURCHILL",
        center_lat=44.0300,
        center_lng=-123.1650,
        zoom=13.5,
        bbox=EUGENE_DIVISION_BBOXES["CHURCHILL"],
        submarkets=[k for k, v in EUGENE_SUBMARKETS.items() if v.borough == "CHURCHILL"],
        city_id="eugene",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Lane County deeds not reachable as a bulk feed (web
# portal only). Permits unregistered (ebuild Accela portal, no API).
# ---------------------------------------------------------------------------
EUGENE_CAMPING_311_ENDPOINT = (
    "https://services3.arcgis.com/F7NiRLGNbA2hh7gE/arcgis/rest/services/"
    "2020_2021CampingWorkOrders/FeatureServer/0"
)

EUGENE_FOOD_SERVICE_SLA_ENDPOINT = (
    "https://services3.arcgis.com/F7NiRLGNbA2hh7gE/arcgis/rest/services/"
    "Food_Service_Establishments_Updated_VIEW_CBE/FeatureServer/0"
)

EUGENE_CITYLAND_DEEDS_ENDPOINT = (
    "https://services3.arcgis.com/F7NiRLGNbA2hh7gE/arcgis/rest/services/"
    "CityLandDeeds/FeatureServer/0"
)

EUGENE_FEED_SPECS: dict[str, dict[str, object]] = {
    "311": {
        "endpoint": EUGENE_CAMPING_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "CreatedOn",
        "id_keys": ["FID", "GlobalID"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "FID",
            "max_record_count": 2000,
            "order_by": "CreatedOn DESC",
            "scope": (
                "2020_2021CampingWorkOrders (FeatureServer/0 on the city's "
                "ArcGIS Server — 10,287 rows, camping/encampment code-"
                "enforcement work orders, the city's PDD service-request "
                "archive. Point geometry native via outSR=4326. CreatedOn "
                "watermark newest 2021-03-12. Companion HistoricalCampingWorkOrders "
                "(25,171 rows). Lane County web-portal-only 311; no live "
                "public 311 feed on the city server. Code enforcement "
                "ServiceCod = PDD10, PFI10, SFS30, SWM30, PFI11"
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": EUGENE_FOOD_SERVICE_SLA_ENDPOINT,
        "platform": "arcgis",
        # No esriFieldTypeDate column exists on the layer — snapshot only.
        "watermark_col": "",
        "id_keys": ["UID", "ObjectId", "GlobalID"],
        "topic_key": "topic_sla",
        "interval_seconds": 1800.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 90,
            "needs_geocode": False,
            "ingestion_mode": "snapshot",
            "oid_field": "ObjectId",
            "max_record_count": 2000,
            "alarm_exempt": True,
            "alarm_exempt_reason": (
                "Food service establishment license snapshot with no date "
                "fields and no source edit metadata (hasStaticData: True, no "
                "editingInfo) — freshness is unverifiable at the source; the "
                "cross-run id-dedup diff is the open/close signal (Modesto "
                "SLA precedent, US-163)"
            ),
            "scope": (
                "Food_Service_Establishments_Updated_VIEW_CBE (FeatureServer/0 "
                "on the city's ArcGIS Server — 752 rows, food service "
                "establishment business licenses. Store SR 102100 Web Mercator; "
                "outSR=4326 geometry lift produces WGS84. DisplayX/DisplayY "
                "attributes are native decimal-degree lat/lng but geometry lift "
                "is the sole coordinate source. Name, Licensee, Active. No date "
                "column — snapshot mode, Modesto SLA precedent. City code "
                "enforcement (CBE) business license registry; companion state "
                "registries: Oregon OLCC (liquor) and CCB (contractors)."
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "deeds": {
        "endpoint": EUGENE_CITYLAND_DEEDS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "DATE_",
        "id_keys": ["CITYDEED", "OBJECTID_1"],
        "topic_key": "topic_deeds",
        "interval_seconds": 600.0,
        "producer_key": "deeds",
        "extra": {
            "expected_cadence_days": 3,
            "needs_geocode": False,
            "oid_field": "OBJECTID_1",
            "max_record_count": 2000,
            "order_by": "DATE_ DESC",
            "scope": (
                "CityLandDeeds (FeatureServer/0 on the city's ArcGIS Server — "
                "2,873 rows, city-owned property deed records (acquisitions/"
                "dispositions). Polygon geometry → centroid via outSR=4326. "
                "DATE_ watermark live to 2026-06-30. Native Oregon State Plane "
                "North WKID 2914; server-side outSR=4326 reprojection. "
                "Companion deed layers: EasementDeeds (7,340 rows, DATE_ to "
                "2026-06-30), ROWDeeds (4,380 rows, DATE_ to 2026-01-04). "
                "Lane County's property records are web-portal-only (LMD-PRO / "
                "citizenserviceportal) — not bulk-accessible. City-generated "
                "deed layers are the verifiable partial record per the city-"
                "registration rule (partial without deeds is fine)."
            ),
            "field_map": DEEDS_FIELD_MAP,
        },
    },
}


def get_eugene_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Eugene feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in EUGENE_FEED_SPECS:
        available = ", ".join(sorted(EUGENE_FEED_SPECS))
        raise KeyError(
            f"'{EUGENE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = EUGENE_FEED_SPECS[feed_name]
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
    metro_bbox=EUGENE_METRO_BBOX,
    division_bboxes=EUGENE_DIVISION_BBOXES,
    submarkets=EUGENE_SUBMARKETS,
    divisions=EUGENE_DIVISIONS,
    contains=is_in_eugene_metro,
)

__all__ = [
    "EUGENE_CAMPING_311_ENDPOINT",
    "EUGENE_CITYLAND_DEEDS_ENDPOINT",
    "EUGENE_CITY_ID",
    "EUGENE_DIVISIONS",
    "EUGENE_DIVISION_BBOXES",
    "EUGENE_FEED_SPECS",
    "EUGENE_FOOD_SERVICE_SLA_ENDPOINT",
    "EUGENE_GEOCODE_CONTEXT",
    "EUGENE_METRO_BBOX",
    "EUGENE_SUBMARKETS",
    "REGISTRATION",
    "get_eugene_dataset",
    "is_in_eugene_metro",
    "is_in_greater_eugene_metro",
]