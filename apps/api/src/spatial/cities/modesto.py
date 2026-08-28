"""Modesto / Stanislaus County spatial registry and geometry.

Provides neighborhood metadata, division catalog, and geographic bounding
boxes for the City of Modesto, CA and its immediate county-fringe context.

Modesto is a ONE-FEED PARTIAL metro: SLA (``Business Licenses``,
ExternalServices/Map_Layer_Service_External/FeatureServer/7 on the city
ArcGIS Enterprise server ``gis.modestogov.com/hosting``). PERMITS, 311, and
DEEDS are Tier 3 and stay unregistered.

Live-probe evidence that defines this leaf (2026-08-28, US-231):

* The ArcGIS Hub (``modesto.opendata.arcgis.com``) is a **private org** —
  every API surface answers 401 ``private org id ... is not accessible``
  (Greenville precedent). The city's real public GIS surface is the
  ArcGIS Enterprise 12.1 server at ``gis.modestogov.com/hosting/rest``;
  its ``Hosted``, ``InternalServices``, and ``TrakIT`` folders answer 403
  (TrakIT is the city's permit system, so no public permits feed exists —
  the only permit-shaped public layers are an aggregate "Development
  Projects" showcase point layer with no dates or case ids, and KPI
  dashboards).
* SLA — ``FeatureServer/7`` verified live: **4,574 rows**, native point
  geometry lifted by ``outSR=4326`` (probe: x=-121.02749, y=37.65944 for
  OBJECTID 2), **214/4574 null-geometry (95.3% coverage)**. Columns are
  exactly OBJECTID, ACCOUNTNUM, BUSNAME, LOCSTNUM, LOCSTADDR1, LOCSUITE,
  LOCCITY, LOCST, LOCZIP1, LOCZIP2, LOCPHNUM, GlobalID. There is **no
  esriFieldTypeDate column** (incremental is impossible — snapshot-only),
  **no license-class/status/NAICS column** (the shared parser's legacy
  "On-Premises Liquor" default labels every event — registration caveat
  the spine hold must carry), and **no lastEditDate/editingInfo/timeInfo**
  on the layer (the staleness probe would flag ``oldest is None`` forever,
  so the spec is ``alarm_exempt`` with a documented reason — KC SLA
  precedent, US-163). Snapshot registration mirrors KC SLA: full pull per
  cycle, cross-run id-dedup diff as the open/close signal.
* The layer's store SR is **WKID 102643 (NAD83 California Zone 3 state
  plane, US survey feet)** but the attributes carry no X/Y pair, so no
  ``state_plane_*`` spec keys are declared — the outSR=4326 geometry lift
  is the only coordinate path (Tucson precedent). ``needs_geocode`` stays
  False: the mapped address is a street string without a house number
  (no parts-join in the shared SLA chain), which fails the ADR-0004
  confidence gate (MC311 precedent); null-geometry rows drop.
* 311 REJECT — Modesto 311 is "GoModesto" on the PublicStuff vendor
  platform (city embeds ``iframe.publicstuff.com`` client_id=1000044);
  the PublicStuff API is undocumented legacy XML-RPC that rejects every
  anonymous envelope ("Request method not provided" / "Malformed XML").
  No Socrata/ArcGIS 311 surface exists (the AGO org's 68 hosted services
  carry none).
* DEEDS REJECT — Stanislaus County Clerk-Recorder's online service
  (``crweb.stancounty.com``, "Online U.S. Applications") is an interactive
  vendor search portal with no anonymous bulk API; the county parcel
  mirror on the city server (``County_Parcels_Offline_External``,
  168,712 polygons, refreshed with a bulk ``modifydate`` stamp) is a
  cadastre — no sale price, sale date, or document number (Greenville
  parcel-CAMA precedent).
"""

from src.producers.field_maps_modesto import (
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MODESTO_CITY_ID: str = "modesto"
MODESTO_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Modesto plus the immediate fringe. Permissive enough to hold the
# Kiernan Avenue growth corridor (37.686), Village One (37.664), the Airport
# Neighborhood (37.617), and Rosemount/Scenic (-120.947) while rejecting
# Ceres (37.5947), Turlock (37.4947), Salida (37.7058), and Stockton
# (37.9577).
MODESTO_METRO_BBOX: dict[str, float] = {
    "min_lat": 37.60,
    "max_lat": 37.70,
    "min_lng": -121.05,
    "max_lng": -120.93,
}

# 8 Modesto divisions. Hand-authored; borough resolution at ingest comes
# from coordinates via get_division_for_coordinate, so bboxes need only be
# sane, mutually non-overlapping, and contain their own submarket centers.
MODESTO_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CORE": {
        "min_lat": 37.630,
        "max_lat": 37.648,
        "min_lng": -121.005,
        "max_lng": -120.985,
    },
    "GRACEADA_MCHENRY": {
        "min_lat": 37.648,
        "max_lat": 37.656,
        "min_lng": -121.000,
        "max_lng": -120.982,
    },
    "COLLEGE_AREA_MJC": {
        "min_lat": 37.640,
        "max_lat": 37.656,
        "min_lng": -120.982,
        "max_lng": -120.968,
    },
    "LA_LOMA_EAST": {
        "min_lat": 37.628,
        "max_lat": 37.640,
        "min_lng": -120.978,
        "max_lng": -120.962,
    },
    "VILLAGE_ONE_NORTHEAST": {
        "min_lat": 37.656,
        "max_lat": 37.676,
        "min_lng": -120.990,
        "max_lng": -120.966,
    },
    "KIERNAN_CORRIDOR_NORTH": {
        "min_lat": 37.676,
        "max_lat": 37.700,
        "min_lng": -120.980,
        "max_lng": -120.940,
    },
    "SOUTHWEST_AIRPORT": {
        "min_lat": 37.600,
        "max_lat": 37.630,
        "min_lng": -121.040,
        "max_lng": -121.000,
    },
    "SOUTHEAST_SCENIC": {
        "min_lat": 37.630,
        "max_lat": 37.650,
        "min_lng": -120.960,
        "max_lng": -120.938,
    },
}


def is_in_modesto_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Modesto / county-fringe bounds."""
    if lat is None or lng is None:
        return False
    return (
        MODESTO_METRO_BBOX["min_lat"] <= lat <= MODESTO_METRO_BBOX["max_lat"]
        and MODESTO_METRO_BBOX["min_lng"] <= lng <= MODESTO_METRO_BBOX["max_lng"]
    )


is_in_greater_modesto_metro = is_in_modesto_metro


MODESTO_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2)
    # =======================================================================
    "Downtown Modesto": SubmarketMeta(
        name="Downtown Modesto",
        borough="DOWNTOWN_CORE",
        lat=37.6394,
        lng=-120.9969,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=54.0,
        description=(
            "Tenth Street Plaza core with the Gallo Center for the Arts, "
            "facade-rehab permitting, adaptive reuse of the historic "
            "commercial grid, and the city's densest business-license "
            "churn."
        ),
        city_id="modesto",
    ),
    "Virginia Corridor South": SubmarketMeta(
        name="Virginia Corridor South",
        borough="DOWNTOWN_CORE",
        lat=37.6445,
        lng=-120.9930,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.72,
        capex=4600000.0,
        permit_vel=27.0,
        shift_ratio=1.36,
        sla=49.0,
        description=(
            "Mid-century belt along the Virginia Corridor greenway with "
            "renovation-led permitting and small-office conversions."
        ),
        city_id="modesto",
    ),
    # =======================================================================
    # GRACEADA_MCHENRY (1)
    # =======================================================================
    "Graceada Park Historic District": SubmarketMeta(
        name="Graceada Park Historic District",
        borough="GRACEADA_MCHENRY",
        lat=37.6494,
        lng=-120.9904,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.46,
        sla=55.0,
        description=(
            "Graceada Park, the McHenry Mansion and Museum district, and "
            "the city's finest century-old housing stock with "
            "restoration-grade permit cadence."
        ),
        city_id="modesto",
    ),
    # =======================================================================
    # COLLEGE_AREA_MJC (2)
    # =======================================================================
    "Modesto Junior College East": SubmarketMeta(
        name="Modesto Junior College East",
        borough="COLLEGE_AREA_MJC",
        lat=37.6495,
        lng=-120.9777,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.74,
        capex=5000000.0,
        permit_vel=29.0,
        shift_ratio=1.40,
        sla=52.0,
        description=(
            "MJC east-campus rental belt with steady tenant turnover, "
            "duplex conversions, and college-service licensing."
        ),
        city_id="modesto",
    ),
    "College & El Vista": SubmarketMeta(
        name="College & El Vista",
        borough="COLLEGE_AREA_MJC",
        lat=37.6440,
        lng=-120.9730,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.70,
        capex=4400000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=47.0,
        description=(
            "El Vista Avenue corridor of post-war tracts with "
            "basement-finish and roof-permit cadence."
        ),
        city_id="modesto",
    ),
    # =======================================================================
    # LA_LOMA_EAST (1)
    # =======================================================================
    "La Loma": SubmarketMeta(
        name="La Loma",
        borough="LA_LOMA_EAST",
        lat=37.6360,
        lng=-120.9730,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.72,
        capex=4800000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=50.0,
        description=(
            "East-side grid around La Loma Park with owner-occupied "
            "vintage housing and incremental renovation permitting."
        ),
        city_id="modesto",
    ),
    # =======================================================================
    # VILLAGE_ONE_NORTHEAST (2)
    # =======================================================================
    "Village One": SubmarketMeta(
        name="Village One",
        borough="VILLAGE_ONE_NORTHEAST",
        lat=37.6640,
        lng=-120.9760,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=54.0,
        description=(
            "One of Modesto's largest planned-unit developments — "
            "curvilinear 1970s-80s housing with steady remodel volume "
            "and neighborhood-retail licensing."
        ),
        city_id="modesto",
    ),
    "Sherwood Forest & Sylvan": SubmarketMeta(
        name="Sherwood Forest & Sylvan",
        borough="VILLAGE_ONE_NORTHEAST",
        lat=37.6700,
        lng=-120.9880,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=52.0,
        description=(
            "Sylvan Avenue retail spine beside Sherwood Forest Park with "
            "pool/deck auxiliary permits and small-business churn."
        ),
        city_id="modesto",
    ),
    # =======================================================================
    # KIERNAN_CORRIDOR_NORTH (2)
    # =======================================================================
    "Kiernan Business Corridor": SubmarketMeta(
        name="Kiernan Business Corridor",
        borough="KIERNAN_CORRIDOR_NORTH",
        lat=37.6860,
        lng=-120.9540,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.84,
        capex=7600000.0,
        permit_vel=38.0,
        shift_ratio=1.50,
        sla=58.0,
        description=(
            "Kiernan Avenue northeast growth corridor with new-build "
            "retail and medical pads, UC Merced-adjacent logistics, and "
            "the metro's fastest permit velocity."
        ),
        city_id="modesto",
    ),
    "Pelandale Corridor": SubmarketMeta(
        name="Pelandale Corridor",
        borough="KIERNAN_CORRIDOR_NORTH",
        lat=37.6790,
        lng=-120.9640,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.80,
        capex=6800000.0,
        permit_vel=34.0,
        shift_ratio=1.46,
        sla=56.0,
        description=(
            "Pelandale Avenue big-box and dining row with pad-site "
            "filings and highway-99-adjacent service licensing."
        ),
        city_id="modesto",
    ),
    # =======================================================================
    # SOUTHWEST_AIRPORT (2)
    # =======================================================================
    "Airport Neighborhood": SubmarketMeta(
        name="Airport Neighborhood",
        borough="SOUTHWEST_AIRPORT",
        lat=37.6170,
        lng=-121.0080,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.68,
        capex=4200000.0,
        permit_vel=26.0,
        shift_ratio=1.32,
        sla=46.0,
        description=(
            "Housing south of the Modesto City-County Airport with "
            "industrial-adjacent infill and steady alteration permitting."
        ),
        city_id="modesto",
    ),
    "West Modesto & Beard Industrial Edge": SubmarketMeta(
        name="West Modesto & Beard Industrial Edge",
        borough="SOUTHWEST_AIRPORT",
        lat=37.6260,
        lng=-121.0120,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.66,
        capex=4400000.0,
        permit_vel=27.0,
        shift_ratio=1.30,
        sla=48.0,
        description=(
            "Highway 99 frontage against the Beard Industrial District "
            "with warehouse conversions and trade licensing volume."
        ),
        city_id="modesto",
    ),
    # =======================================================================
    # SOUTHEAST_SCENIC (1)
    # =======================================================================
    "Rosemount & Scenic": SubmarketMeta(
        name="Rosemount & Scenic",
        borough="SOUTHEAST_SCENIC",
        lat=37.6390,
        lng=-120.9470,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.40,
        sla=51.0,
        description=(
            "Scenic Drive heights above the Oakdale Road retail spine "
            "with ranch-scale lots and remodel-led permitting."
        ),
        city_id="modesto",
    ),
}


MODESTO_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=37.640,
        center_lng=-120.996,
        zoom=14.0,
        bbox=MODESTO_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in MODESTO_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="modesto",
    ),
    "GRACEADA_MCHENRY": BoroughMeta(
        name="GRACEADA_MCHENRY",
        center_lat=37.652,
        center_lng=-120.991,
        zoom=14.0,
        bbox=MODESTO_DIVISION_BBOXES["GRACEADA_MCHENRY"],
        submarkets=[k for k, v in MODESTO_SUBMARKETS.items() if v.borough == "GRACEADA_MCHENRY"],
        city_id="modesto",
    ),
    "COLLEGE_AREA_MJC": BoroughMeta(
        name="COLLEGE_AREA_MJC",
        center_lat=37.647,
        center_lng=-120.975,
        zoom=13.5,
        bbox=MODESTO_DIVISION_BBOXES["COLLEGE_AREA_MJC"],
        submarkets=[k for k, v in MODESTO_SUBMARKETS.items() if v.borough == "COLLEGE_AREA_MJC"],
        city_id="modesto",
    ),
    "LA_LOMA_EAST": BoroughMeta(
        name="LA_LOMA_EAST",
        center_lat=37.634,
        center_lng=-120.970,
        zoom=13.5,
        bbox=MODESTO_DIVISION_BBOXES["LA_LOMA_EAST"],
        submarkets=[k for k, v in MODESTO_SUBMARKETS.items() if v.borough == "LA_LOMA_EAST"],
        city_id="modesto",
    ),
    "VILLAGE_ONE_NORTHEAST": BoroughMeta(
        name="VILLAGE_ONE_NORTHEAST",
        center_lat=37.666,
        center_lng=-120.978,
        zoom=13.0,
        bbox=MODESTO_DIVISION_BBOXES["VILLAGE_ONE_NORTHEAST"],
        submarkets=[k for k, v in MODESTO_SUBMARKETS.items() if v.borough == "VILLAGE_ONE_NORTHEAST"],
        city_id="modesto",
    ),
    "KIERNAN_CORRIDOR_NORTH": BoroughMeta(
        name="KIERNAN_CORRIDOR_NORTH",
        center_lat=37.683,
        center_lng=-120.958,
        zoom=12.5,
        bbox=MODESTO_DIVISION_BBOXES["KIERNAN_CORRIDOR_NORTH"],
        submarkets=[k for k, v in MODESTO_SUBMARKETS.items() if v.borough == "KIERNAN_CORRIDOR_NORTH"],
        city_id="modesto",
    ),
    "SOUTHWEST_AIRPORT": BoroughMeta(
        name="SOUTHWEST_AIRPORT",
        center_lat=37.622,
        center_lng=-121.010,
        zoom=13.0,
        bbox=MODESTO_DIVISION_BBOXES["SOUTHWEST_AIRPORT"],
        submarkets=[k for k, v in MODESTO_SUBMARKETS.items() if v.borough == "SOUTHWEST_AIRPORT"],
        city_id="modesto",
    ),
    "SOUTHEAST_SCENIC": BoroughMeta(
        name="SOUTHEAST_SCENIC",
        center_lat=37.640,
        center_lng=-120.949,
        zoom=13.5,
        bbox=MODESTO_DIVISION_BBOXES["SOUTHEAST_SCENIC"],
        submarkets=[k for k, v in MODESTO_SUBMARKETS.items() if v.borough == "SOUTHEAST_SCENIC"],
        city_id="modesto",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register 311 (PublicStuff vendor platform with no
# anonymous API), deeds (county recorder is an interactive search portal;
# the city parcel mirror is a cadastre), or the TrakIT/Hosted/Internal
# folders (403).
# ---------------------------------------------------------------------------
MODESTO_SLA_ENDPOINT = (
    "https://gis.modestogov.com/hosting/rest/services/"
    "ExternalServices/Map_Layer_Service_External/FeatureServer/7"
)

MODESTO_FEED_SPECS: dict[str, dict[str, object]] = {
    "sla": {
        "endpoint": MODESTO_SLA_ENDPOINT,
        "platform": "arcgis",
        # No esriFieldTypeDate column exists on the layer — snapshot only.
        "watermark_col": "",
        "id_keys": ["ACCOUNTNUM", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 1800.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 90,
            "needs_geocode": False,
            "ingestion_mode": "snapshot",
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "alarm_exempt": True,
            "alarm_exempt_reason": (
                "current-license snapshot with no date fields and no "
                "source edit metadata (no lastEditDate/editingInfo) — "
                "freshness is unverifiable at the source; the cross-run "
                "id-dedup diff is the open/close signal (KC SLA "
                "precedent, US-163)"
            ),
            "scope": (
                "Business Licenses (FeatureServer/7 on the city ArcGIS "
                "Enterprise 12.1 server — current-license snapshot of "
                "4,574 rows, 214/4574 null geometry ≈ 4.7%, native "
                "outSR=4326 point geometry primary; store SR WKID 102643 "
                "state plane but attributes carry no X/Y pair so no "
                "state_plane_* keys; no license-class column so events "
                "carry the shared parser's legacy license_type default — "
                "spine hold must carry that caveat)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_modesto_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Modesto feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in MODESTO_FEED_SPECS:
        available = ", ".join(sorted(MODESTO_FEED_SPECS))
        raise KeyError(
            f"'{MODESTO_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = MODESTO_FEED_SPECS[feed_name]
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
    metro_bbox=MODESTO_METRO_BBOX,
    division_bboxes=MODESTO_DIVISION_BBOXES,
    submarkets=MODESTO_SUBMARKETS,
    divisions=MODESTO_DIVISIONS,
    contains=is_in_modesto_metro,
)

__all__ = [
    "MODESTO_CITY_ID",
    "MODESTO_DIVISIONS",
    "MODESTO_DIVISION_BBOXES",
    "MODESTO_FEED_SPECS",
    "MODESTO_GEOCODE_CONTEXT",
    "MODESTO_METRO_BBOX",
    "MODESTO_SLA_ENDPOINT",
    "MODESTO_SUBMARKETS",
    "REGISTRATION",
    "get_modesto_dataset",
    "is_in_greater_modesto_metro",
    "is_in_modesto_metro",
]
