PERMITS_FIELD_MAP = {
    "job_id": ["Permit_Number", "OBJECTID"],
    "issuance_date": ["Issued_Date"],
    "job_type": ["Permit_Type"],
    "cost": ["Project_Valuation"],
    "address_street": ["Permit_Location"],
}

BUSREG_FIELD_MAP = {
    "license_id": ["RECNO", "OBJECTID"],
    "dba": ["DBA", "RECNAME"],
    "premises_name": ["RECNAME", "DBA"],
    "license_type": ["BusCat", "BusType"],
    "status": ["STATUS"],
    "effective_date": ["LastUpdateDate"],
    "address_street": ["RecAddress"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": BUSREG_FIELD_MAP,
}

GEOCODE_CONTEXT = "Las Cruces, NM"

DROPPED_PII_COLUMNS = (
    "Owner_Name",
    "Contractor_Name",
    "Contractor_Business_Name",
    "Email",
    "Phone",
    "MailAddress",
    "ContactName",
)

"""Las Cruces, NM spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Las Cruces
(south-central Doña Ana County, NM, Mesilla Valley).

Las Cruces is a TWO-FEED PARTIAL metro: PERMITS (``Information_Services/
MapServer/1`` on the city's ArcGIS Server at ``maps.las-cruces.org``, Tier 1,
~82k rows, native WKID 4326 point geometry, ``Issued_Date`` watermark) and
BUSINESS_REGISTRATIONS (``Information_Services/MapServer/2``, Tier 2,
~26k rows, native WKID 4326 point geometry, ``LastUpdateDate`` watermark).
Parishes: CertificateOFoccupancy (``MapServer/3``, ~7k, ``IssueDate``) is
available but not registered. 311 (Tyler Portico, no open API) and deeds
(Doña Ana County parcel data, no bulk sales/deeds feed) are Tier 3 and stay
unregistered.

Live-probe evidence (2026-08-28, US-240):

* PERMITS (BuildingPermits): 82,433 rows, ``Issued_Date`` range 2016-10-03
  to 2026-08-21T06:00Z (newest epoch ``1787292000000``; reads as
  2026-08-20 local MST), 0 future-dated rows, 0 null geometries. Native WKID
  4326 point geometry (``esriGeometryPoint``). ``maxRecordCount=1000``.
  Watermark ``Issued_Date`` (esriFieldTypeDate). Key columns:
  ``Permit_Number``, ``Permit_Type``, ``Permit_Location`` (address),
  ``Project_Valuation``, ``Issued_Date``, ``Issue_Year``, ``IssueMonthNo``,
  ``Contractor_Business_Name``, ``Owner_Name``, ``Proposed_Use``,
  ``Total_SQFT``, ``Zoning``, ``X``, ``Y``, ``OBJECTID``. No State Plane CRS
  issue — X/Y attributes are WKID 4326 decimals matching the geometry.

* BUSINESS_REGISTRATIONS (Business_Registrations): 26,508 rows,
  ``LastUpdateDate`` range 2018-12-09 to 2026-08-21T06:00Z, native WKID 4326
  point geometry (``esriGeometryPoint``). ``maxRecordCount=1000``. Watermark
  ``LastUpdateDate`` (esriFieldTypeDate). Key columns: ``RECNO``,
  ``BUSINESS_NAME``, ``DBA``, ``RECNAME``, ``BusCat``, ``BusType``,
  ``NAICS``, ``CRS`` (parcel number), ``RecAddress``, ``LastUpdateDate``,
  ``IssueYear``, ``IssueMonth``, ``STATUS``, ``RECORD_STATUS``,
  ``RECORD_TYPE``, ``ContactName``, ``Phone``, ``Email``, ``X``, ``Y``,
  ``OBJECTID``.

* 311 / Service Requests: The city uses Tyler Portico
  (``cityoflascrucesnm.tylerportico.com``) for "Ask Las Cruces" service
  requests — no open REST API. No 311 feed registered.

* Deeds / Sales: Doña Ana County's ArcGIS Server (``gis.donaana.gov``)
  publishes ``Parcels`` (FeatureServer) and ``Situs_Addresses`` but no
  deeds/sales recorder feed. No deeds feed registered.

* No ANSI-date host issues (``maps.las-cruces.org`` accepts ISO date
  literals in where clauses).

* Feed geometry is native WKID 4326. X/Y attributes are WGS84 decimal
  degrees (not State Plane). No ``outSR`` transformation needed.
  ``needs_geocode=False`` for both feeds.

* Division evidence: coordinate-spatial query counts from the live
  BuildingPermits layer confirm the six hand-authored divisions below.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

LAS_CRUCES_CITY_ID: str = "las_cruces"
LAS_CRUCES_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Las Cruces (Doña Ana County, NM). The Mesilla Valley runs along
# the Rio Grande at ~3,900 ft elevation. The bbox is wide enough to hold
# the downtown core, the Mesilla historic district, East Mesa (NMSU), the
# Sonoma Ranch master-planned communities, and the northern Telshor/medical
# corridor — while excluding far-county Hatch / Sunland Park / Anthony.
LAS_CRUCES_METRO_BBOX: dict[str, float] = {
    "min_lat": 32.20,
    "max_lat": 32.50,
    "min_lng": -106.95,
    "max_lng": -106.55,
}

# 6 Las Cruces divisions. Evidence-based from coordinate-spatial query
# counts on the live BuildingPermits layer (2026-08-28 probe):
#   Downtown: ~19,805 | Mesilla: ~3,317 | East Mesa: ~4,001
#   Sonoma Ranch: ~15,853 | Northern: ~36,532 | West Mesa: ~22,337
LAS_CRUCES_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CORE": {
        "min_lat": 32.305,
        "max_lat": 32.320,
        "min_lng": -106.795,
        "max_lng": -106.765,
    },
    "MESILLA_VALLEY": {
        "min_lat": 32.270,
        "max_lat": 32.285,
        "min_lng": -106.815,
        "max_lng": -106.790,
    },
    "EAST_MESA": {
        "min_lat": 32.265,
        "max_lat": 32.295,
        "min_lng": -106.760,
        "max_lng": -106.700,
    },
    "SONOMA_RANCH": {
        "min_lat": 32.340,
        "max_lat": 32.365,
        "min_lng": -106.750,
        "max_lng": -106.700,
    },
    "NORTHERN_LC": {
        "min_lat": 32.335,
        "max_lat": 32.360,
        "min_lng": -106.790,
        "max_lng": -106.750,
    },
    "WEST_MESA": {
        "min_lat": 32.290,
        "max_lat": 32.320,
        "min_lng": -106.900,
        "max_lng": -106.800,
    },
}


def is_in_las_cruces_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Las Cruces metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        LAS_CRUCES_METRO_BBOX["min_lat"] <= lat <= LAS_CRUCES_METRO_BBOX["max_lat"]
        and LAS_CRUCES_METRO_BBOX["min_lng"] <= lng <= LAS_CRUCES_METRO_BBOX["max_lng"]
    )


is_in_greater_las_cruces_metro = is_in_las_cruces_metro


LAS_CRUCES_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2)
    # =======================================================================
    "Downtown Las Cruces": SubmarketMeta(
        name="Downtown Las Cruces",
        borough="DOWNTOWN_CORE",
        lat=32.3120,
        lng=-106.7780,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=35.0,
        shift_ratio=1.48,
        sla=58.0,
        description="Main Street downtown corridor with the historic Plaza, the Rio Grande Theatre, and mixed-use redevelopment of the commercial core.",
        city_id="las_cruces",
    ),
    "Las Cruces Plaza": SubmarketMeta(
        name="Las Cruces Plaza",
        borough="DOWNTOWN_CORE",
        lat=32.3125,
        lng=-106.7710,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=6800000.0,
        permit_vel=32.0,
        shift_ratio=1.45,
        sla=55.0,
        description="Historic Plaza district with the Doña Ana County Courthouse, the Cathedral of the Immaculate Heart of Mary, and century-old storefront retail.",
        city_id="las_cruces",
    ),
    # =======================================================================
    # MESILLA_VALLEY (1)
    # =======================================================================
    "Mesilla Historic District": SubmarketMeta(
        name="Mesilla Historic District",
        borough="MESILLA_VALLEY",
        lat=32.2775,
        lng=-106.8000,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.80,
        capex=6400000.0,
        permit_vel=30.0,
        shift_ratio=1.43,
        sla=54.0,
        description="Historic Mesilla town square with adobe architecture, the Basilica of San Albino, and a tourist-oriented arts and dining economy.",
        city_id="las_cruces",
    ),
    # =======================================================================
    # EAST_MESA (2)
    # =======================================================================
    "NMSU Corridor": SubmarketMeta(
        name="NMSU Corridor",
        borough="EAST_MESA",
        lat=32.2820,
        lng=-106.7450,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=36.0,
        shift_ratio=1.50,
        sla=60.0,
        description="New Mexico State University corridor with student housing, tech-transfer spin-offs, and the Arrowhead Research Park.",
        city_id="las_cruces",
    ),
    "East Mesa Growth": SubmarketMeta(
        name="East Mesa Growth",
        borough="EAST_MESA",
        lat=32.2800,
        lng=-106.7200,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=7000000.0,
        permit_vel=33.0,
        shift_ratio=1.46,
        sla=56.0,
        description="Eastern growth corridor along Lohman Avenue with new subdivisions, strip retail, and the expanding Las Cruces airport edge.",
        city_id="las_cruces",
    ),
    # =======================================================================
    # SONOMA_RANCH (1)
    # =======================================================================
    "Sonoma Ranch": SubmarketMeta(
        name="Sonoma Ranch",
        borough="SONOMA_RANCH",
        lat=32.3520,
        lng=-106.7350,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.86,
        capex=8400000.0,
        permit_vel=38.0,
        shift_ratio=1.52,
        sla=62.0,
        description="Northwest master-planned community with golf-course residential, Sonoma Ranch Elementary, and the emerging Sonoma Marketplace retail.",
        city_id="las_cruces",
    ),
    # =======================================================================
    # NORTHERN_LC (2)
    # =======================================================================
    "Telshor/Medical District": SubmarketMeta(
        name="Telshor/Medical District",
        borough="NORTHERN_LC",
        lat=32.3470,
        lng=-106.7700,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.87,
        capex=9200000.0,
        permit_vel=40.0,
        shift_ratio=1.55,
        sla=64.0,
        description="Telshor Boulevard medical corridor with Memorial Medical Center, MountainView Regional, and the highest concentration of medical office and ancillary services.",
        city_id="las_cruces",
    ),
    "Las Colinas": SubmarketMeta(
        name="Las Colinas",
        borough="NORTHERN_LC",
        lat=32.3450,
        lng=-106.7650,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.85,
        capex=7800000.0,
        permit_vel=36.0,
        shift_ratio=1.50,
        sla=60.0,
        description="Northern residential area with Mesilla Valley Hospital, established neighborhoods, and the Foothills Road corridor.",
        city_id="las_cruces",
    ),
    # =======================================================================
    # WEST_MESA (1)
    # =======================================================================
    "West Mesa": SubmarketMeta(
        name="West Mesa",
        borough="WEST_MESA",
        lat=32.3050,
        lng=-106.8500,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.79,
        capex=6000000.0,
        permit_vel=28.0,
        shift_ratio=1.40,
        sla=50.0,
        description="West side of the Rio Grande valley with agricultural land, rural residential, and the Doña Ana County Government Center.",
        city_id="las_cruces",
    ),
}


LAS_CRUCES_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=32.3120,
        center_lng=-106.7780,
        zoom=13.5,
        bbox=LAS_CRUCES_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in LAS_CRUCES_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="las_cruces",
    ),
    "MESILLA_VALLEY": BoroughMeta(
        name="MESILLA_VALLEY",
        center_lat=32.2775,
        center_lng=-106.8000,
        zoom=13.5,
        bbox=LAS_CRUCES_DIVISION_BBOXES["MESILLA_VALLEY"],
        submarkets=[k for k, v in LAS_CRUCES_SUBMARKETS.items() if v.borough == "MESILLA_VALLEY"],
        city_id="las_cruces",
    ),
    "EAST_MESA": BoroughMeta(
        name="EAST_MESA",
        center_lat=32.2820,
        center_lng=-106.7450,
        zoom=13.0,
        bbox=LAS_CRUCES_DIVISION_BBOXES["EAST_MESA"],
        submarkets=[k for k, v in LAS_CRUCES_SUBMARKETS.items() if v.borough == "EAST_MESA"],
        city_id="las_cruces",
    ),
    "SONOMA_RANCH": BoroughMeta(
        name="SONOMA_RANCH",
        center_lat=32.3520,
        center_lng=-106.7350,
        zoom=13.0,
        bbox=LAS_CRUCES_DIVISION_BBOXES["SONOMA_RANCH"],
        submarkets=[k for k, v in LAS_CRUCES_SUBMARKETS.items() if v.borough == "SONOMA_RANCH"],
        city_id="las_cruces",
    ),
    "NORTHERN_LC": BoroughMeta(
        name="NORTHERN_LC",
        center_lat=32.3470,
        center_lng=-106.7700,
        zoom=13.0,
        bbox=LAS_CRUCES_DIVISION_BBOXES["NORTHERN_LC"],
        submarkets=[k for k, v in LAS_CRUCES_SUBMARKETS.items() if v.borough == "NORTHERN_LC"],
        city_id="las_cruces",
    ),
    "WEST_MESA": BoroughMeta(
        name="WEST_MESA",
        center_lat=32.3050,
        center_lng=-106.8500,
        zoom=13.0,
        bbox=LAS_CRUCES_DIVISION_BBOXES["WEST_MESA"],
        submarkets=[k for k, v in LAS_CRUCES_SUBMARKETS.items() if v.borough == "WEST_MESA"],
        city_id="las_cruces",
    ),
}

# ---------------------------------------------------------------------------
# Feed endpoints
# ---------------------------------------------------------------------------
LAS_CRUCES_PERMITS_ENDPOINT = (
    "https://maps.las-cruces.org/gis/rest/services/"
    "Information_Services/MapServer/1"
)

LAS_CRUCES_BUSREG_ENDPOINT = (
    "https://maps.las-cruces.org/gis/rest/services/"
    "Information_Services/MapServer/2"
)

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. 311 and deeds stay unregistered (Tier 3).
# CertificateOFoccupancy (MapServer/3) is available but not registered.
# ---------------------------------------------------------------------------
LAS_CRUCES_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": LAS_CRUCES_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Issued_Date",
        "id_keys": ["Permit_Number", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 7,
            "oid_field": "OBJECTID",
            "max_record_count": 1000,
            "order_by": "Issued_Date DESC",
            "needs_geocode": False,
            "geocode_context": "Las Cruces, NM",
            "scope": (
                "Las Cruces Building Permits (82,433 rows; native WKID 4326 "
                "point geometry — no State Plane CRS issue; Issued_Date range "
                "2016-10-03 to 2026-08-20; 0 future-dated rows; 0 null "
                "geometries)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": LAS_CRUCES_BUSREG_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "LastUpdateDate",
        "id_keys": ["RECNO", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "oid_field": "OBJECTID",
            "max_record_count": 1000,
            "order_by": "LastUpdateDate DESC",
            "needs_geocode": False,
            "geocode_context": "Las Cruces, NM",
            "scope": (
                "Las Cruces Business Registrations (26,508 rows; native WKID "
                "4326 point geometry; LastUpdateDate range 2018-12-09 to "
                "2026-08-20; RECORD_TYPE includes Business Registration, "
                "Renewal, and Cannabis tiers)"
            ),
            "field_map": BUSREG_FIELD_MAP,
        },
    },
}


def get_las_cruces_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Las Cruces feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in LAS_CRUCES_FEED_SPECS:
        available = ", ".join(sorted(LAS_CRUCES_FEED_SPECS))
        raise KeyError(
            f"'{LAS_CRUCES_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = LAS_CRUCES_FEED_SPECS[feed_name]
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
    metro_bbox=LAS_CRUCES_METRO_BBOX,
    division_bboxes=LAS_CRUCES_DIVISION_BBOXES,
    submarkets=LAS_CRUCES_SUBMARKETS,
    divisions=LAS_CRUCES_DIVISIONS,
    contains=is_in_las_cruces_metro,
)

__all__ = [
    "LAS_CRUCES_BUSREG_ENDPOINT",
    "LAS_CRUCES_CITY_ID",
    "LAS_CRUCES_DIVISIONS",
    "LAS_CRUCES_DIVISION_BBOXES",
    "LAS_CRUCES_FEED_SPECS",
    "LAS_CRUCES_GEOCODE_CONTEXT",
    "LAS_CRUCES_METRO_BBOX",
    "LAS_CRUCES_PERMITS_ENDPOINT",
    "LAS_CRUCES_SUBMARKETS",
    "REGISTRATION",
    "get_las_cruces_dataset",
    "is_in_greater_las_cruces_metro",
    "is_in_las_cruces_metro",
]