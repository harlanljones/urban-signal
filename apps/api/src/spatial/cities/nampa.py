"""Nampa, ID spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Nampa
(southwest Idaho, Canyon County).

Nampa is a ONE-FEED PARTIAL metro: ROW road closures (``ROW_Road_Closure``
on the city's utility ArcGIS server, mapped as ``permits`` through the
field-map path — right-of-way road closure permits with polyline geometry,
CreationDate watermark, street/type/subtype/status/identifier columns).
PERMITS (building) are hosted on Tyler EnerGov (``nampaid-energovpub.tylerhost.net``
— SaaS, no public REST API). COMPLAINTS_311, SLA, and DEEDS are absent or
unreachable: 311 / code compliance is a CivicPlus web form only, SLA has no
AGOL layer, and Canyon County Parcels (``CityInformation_Public/MapServer/36``)
carries null Instrument/address fields — not a deeds feed.

Live-probe caveats that define this leaf (probed 2026-08-28):

* The ticket's "ArcGIS Hub" hint resolves to ``gisdata-nampa.hub.arcgis.com``
  — a skeleton Hub with no dataset API; the real data lives on the city's
  AGOL utility servers at ``utility.arcgis.com/usrsvcs/servers/...``.
* ROW_Road_Closure is **polyline** geometry (``esriGeometryPolyline``) and
  ArcGISClient's ``_geometry_to_lng_lat`` reduces it to the mean of all
  path points (WGS84, via ``outSR=4326``). The ``starttime``/``endtime``
  columns are the planned closure window; ``CreationDate`` is the system
  watermark (newest 1787857841000 = 2026-08-27). The ``identifier`` column
  carries the permit ID (``ROW-08302-2026``) and ``OBJECTID`` is the OID
  fallback.
* **Idaho State Plane West** (wkid 102670 / latest 2243, feet) is the native
  CRS of every layer. The ``outSR=4326`` geometry lift is the sole coordinate
  source — attribute columns are in State Plane feet and are never mapped
  as latitude/longitude (the field map omits them).
* No ANSI-date or ISO-date restrictions: the ArcGIS Server accepts standard
  epoch-ms in ``where`` clauses; no special host entry needed.
* The layer is **small and active** (76 rows, maintained by the GIS team).
  ``expected_cadence_days=7`` with ``alarm_exempt=True`` to avoid false
  positives on the slow issuance pace of road closures.
"""

from src.producers.field_maps_nampa import (
    GEOCODE_CONTEXT,
    STREET_CUT_FIELD_MAP,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

NAMPA_CITY_ID: str = "nampa"
NAMPA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Nampa proper (Canyon County, SW Idaho). The city limit polygon
# (live-probed from NampaOpenData/MapServer/6) spans 43.5173–43.6559 lat,
# -116.6442–-116.4736 lng. The metro bbox adds a small buffer.
NAMPA_METRO_BBOX: dict[str, float] = {
    "min_lat": 43.50,
    "max_lat": 43.67,
    "min_lng": -116.66,
    "max_lng": -116.46,
}

# 6 Nampa divisions, evidenced by the city's own GIS district layers (live
# probed 2026-08-28 from CityInformation_Public MapServer extents, converted
# from Idaho State Plane West 2243 to WGS84). Hand-authored; borough
# resolution at ingest comes from coordinates via
# get_division_for_coordinate, so bboxes need only be sane and contain their
# own submarket centers.
NAMPA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 43.570,
        "max_lat": 43.590,
        "min_lng": -116.578,
        "max_lng": -116.550,
    },
    "UNIVERSITY": {
        "min_lat": 43.552,
        "max_lat": 43.572,
        "min_lng": -116.576,
        "max_lng": -116.550,
    },
    "WEST_NAMPA": {
        "min_lat": 43.580,
        "max_lat": 43.610,
        "min_lng": -116.640,
        "max_lng": -116.585,
    },
    "SOUTH_NAMPA": {
        "min_lat": 43.540,
        "max_lat": 43.570,
        "min_lng": -116.590,
        "max_lng": -116.540,
    },
    "NORTH_NAMPA": {
        "min_lat": 43.600,
        "max_lat": 43.645,
        "min_lng": -116.610,
        "max_lng": -116.550,
    },
    "EAST_NAMPA": {
        "min_lat": 43.550,
        "max_lat": 43.600,
        "min_lng": -116.550,
        "max_lng": -116.490,
    },
}


def is_in_nampa_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Nampa city bounds."""
    if lat is None or lng is None:
        return False
    return (
        NAMPA_METRO_BBOX["min_lat"] <= lat <= NAMPA_METRO_BBOX["max_lat"]
        and NAMPA_METRO_BBOX["min_lng"] <= lng <= NAMPA_METRO_BBOX["max_lng"]
    )


is_in_greater_nampa_metro = is_in_nampa_metro


NAMPA_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (2)
    # =======================================================================
    "Downtown Nampa": SubmarketMeta(
        name="Downtown Nampa",
        borough="DOWNTOWN",
        lat=43.580,
        lng=-116.564,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.85,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.35,
        sla=48.0,
        description="Downtown Nampa core along 1st/3rd Streets with the Civic Center, the Nampa Public Library, and the downtown business district retail spine.",
        city_id="nampa",
    ),
    "Old Nampa": SubmarketMeta(
        name="Old Nampa",
        borough="DOWNTOWN",
        lat=43.577,
        lng=-116.569,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.83,
        capex=4800000.0,
        permit_vel=20.0,
        shift_ratio=1.33,
        sla=46.0,
        description="Historic residential neighborhood south of downtown with pre-war bungalow stock, the Old Nampa Neighborhood Association, and steady renovation permits.",
        city_id="nampa",
    ),
    # =======================================================================
    # UNIVERSITY (1)
    # =======================================================================
    "College of Western Idaho": SubmarketMeta(
        name="College of Western Idaho",
        borough="UNIVERSITY",
        lat=43.562,
        lng=-116.564,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=5800000.0,
        permit_vel=24.0,
        shift_ratio=1.37,
        sla=50.0,
        description="University District around the College of Western Idaho Nampa Campus with student-housing turnover, academic infrastructure, and the Nampa Workforce Center.",
        city_id="nampa",
    ),
    # =======================================================================
    # WEST_NAMPA (2)
    # =======================================================================
    "West Nampa": SubmarketMeta(
        name="West Nampa",
        borough="WEST_NAMPA",
        lat=43.595,
        lng=-116.615,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=4600000.0,
        permit_vel=18.0,
        shift_ratio=1.31,
        sla=44.0,
        description="Flamingo Avenue and Midland Boulevard corridor with master-planned subdivisions, the West Nampa growth belt, and the Middleton Road edge.",
        city_id="nampa",
    ),
    "Middleton Road Edge": SubmarketMeta(
        name="Middleton Road Edge",
        borough="WEST_NAMPA",
        lat=43.605,
        lng=-116.635,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.81,
        capex=4400000.0,
        permit_vel=17.0,
        shift_ratio=1.30,
        sla=43.0,
        description="Western approach corridor along Middleton Road with new subdivision build-out and the transition to agricultural land.",
        city_id="nampa",
    ),
    # =======================================================================
    # SOUTH_NAMPA (1)
    # =======================================================================
    "South Nampa": SubmarketMeta(
        name="South Nampa",
        borough="SOUTH_NAMPA",
        lat=43.555,
        lng=-116.565,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=4500000.0,
        permit_vel=19.0,
        shift_ratio=1.32,
        sla=45.0,
        description="South Nampa corridor along 14th Avenue South and Franklin Boulevard with light industrial, utility infrastructure, and water line replacement projects.",
        city_id="nampa",
    ),
    # =======================================================================
    # NORTH_NAMPA (1)
    # =======================================================================
    "North Nampa": SubmarketMeta(
        name="North Nampa",
        borough="NORTH_NAMPA",
        lat=43.622,
        lng=-116.580,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.83,
        capex=5000000.0,
        permit_vel=21.0,
        shift_ratio=1.34,
        sla=47.0,
        description="North Nampa corridor north of Interstate 84 with the Urban Renewal District, Northside Boulevard, and the Garrity Boulevard industrial-commercial spine.",
        city_id="nampa",
    ),
    # =======================================================================
    # EAST_NAMPA (1)
    # =======================================================================
    "East Nampa": SubmarketMeta(
        name="East Nampa",
        borough="EAST_NAMPA",
        lat=43.575,
        lng=-116.520,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.84,
        capex=5100000.0,
        permit_vel=20.0,
        shift_ratio=1.34,
        sla=46.0,
        description="East Nampa Opportunity Zone corridor along the East Nampa commercial strip with the Nampa Municipal Airport edge and large-lot commercial development.",
        city_id="nampa",
    ),
}


NAMPA_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=43.580,
        center_lng=-116.564,
        zoom=14.0,
        bbox=NAMPA_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in NAMPA_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="nampa",
    ),
    "UNIVERSITY": BoroughMeta(
        name="UNIVERSITY",
        center_lat=43.562,
        center_lng=-116.564,
        zoom=14.0,
        bbox=NAMPA_DIVISION_BBOXES["UNIVERSITY"],
        submarkets=[k for k, v in NAMPA_SUBMARKETS.items() if v.borough == "UNIVERSITY"],
        city_id="nampa",
    ),
    "WEST_NAMPA": BoroughMeta(
        name="WEST_NAMPA",
        center_lat=43.595,
        center_lng=-116.615,
        zoom=13.0,
        bbox=NAMPA_DIVISION_BBOXES["WEST_NAMPA"],
        submarkets=[k for k, v in NAMPA_SUBMARKETS.items() if v.borough == "WEST_NAMPA"],
        city_id="nampa",
    ),
    "SOUTH_NAMPA": BoroughMeta(
        name="SOUTH_NAMPA",
        center_lat=43.555,
        center_lng=-116.565,
        zoom=13.0,
        bbox=NAMPA_DIVISION_BBOXES["SOUTH_NAMPA"],
        submarkets=[k for k, v in NAMPA_SUBMARKETS.items() if v.borough == "SOUTH_NAMPA"],
        city_id="nampa",
    ),
    "NORTH_NAMPA": BoroughMeta(
        name="NORTH_NAMPA",
        center_lat=43.622,
        center_lng=-116.580,
        zoom=13.0,
        bbox=NAMPA_DIVISION_BBOXES["NORTH_NAMPA"],
        submarkets=[k for k, v in NAMPA_SUBMARKETS.items() if v.borough == "NORTH_NAMPA"],
        city_id="nampa",
    ),
    "EAST_NAMPA": BoroughMeta(
        name="EAST_NAMPA",
        center_lat=43.575,
        center_lng=-116.520,
        zoom=13.0,
        bbox=NAMPA_DIVISION_BBOXES["EAST_NAMPA"],
        submarkets=[k for k, v in NAMPA_SUBMARKETS.items() if v.borough == "EAST_NAMPA"],
        city_id="nampa",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Only ROW_Road_Closure registered as a `permits` feed
# (road closure permits through the DOBPermitsProducer field-map path).
# Final Plats (Active) and Preliminary Plats (Active) are available but
# have no street address column for geocode supplement — unregistered.
# The street_cut producer is not field-map aware, so the feed is registered
# as `permits` with a field map matching the ROW_Road_Closure columns.
# ---------------------------------------------------------------------------
NAMPA_STREET_CUT_ENDPOINT = (
    "https://utility.arcgis.com/usrsvcs/servers/"
    "7751a4c516434f1d947c67cd78a4d968/rest/services/"
    "Public/PublicRoadClosures/FeatureServer/3"
)

NAMPA_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": NAMPA_STREET_CUT_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "CreationDate",
        "id_keys": ["identifier", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 600.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 7,
            "alarm_exempt": True,
            "alarm_exempt_reason": (
                "slow cadence: ROW road closure permits layer is small (76 "
                "rows) and maintained by the GIS team; new closures are "
                "infrequent and alarm would false-positive on the slow pace"
            ),
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "CreationDate DESC",
            "scope": (
                "ROW_Road_Closure road closure permits (76 rows, polyline "
                "geometry with outSR=4326 centroid lift; Idaho State Plane "
                "West 2243 native; CreationDate watermark epoch-ms; "
                "street/type_/subtype_/description/Status/identifier columns; "
                "permits hosted on Tyler EnerGov are SaaS-only with no REST "
                "API — NOT registered; Final/Preliminary Plats available but "
                "no address column for geocode supplement)"
            ),
            "field_map": STREET_CUT_FIELD_MAP,
        },
    },
}


def get_nampa_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Nampa feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in NAMPA_FEED_SPECS:
        available = ", ".join(sorted(NAMPA_FEED_SPECS))
        raise KeyError(
            f"'{NAMPA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = NAMPA_FEED_SPECS[feed_name]
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
    metro_bbox=NAMPA_METRO_BBOX,
    division_bboxes=NAMPA_DIVISION_BBOXES,
    submarkets=NAMPA_SUBMARKETS,
    divisions=NAMPA_DIVISIONS,
    contains=is_in_nampa_metro,
)

__all__ = [
    "NAMPA_CITY_ID",
    "NAMPA_DIVISIONS",
    "NAMPA_DIVISION_BBOXES",
    "NAMPA_FEED_SPECS",
    "NAMPA_GEOCODE_CONTEXT",
    "NAMPA_METRO_BBOX",
    "NAMPA_STREET_CUT_ENDPOINT",
    "NAMPA_SUBMARKETS",
    "REGISTRATION",
    "get_nampa_dataset",
    "is_in_greater_nampa_metro",
    "is_in_nampa_metro",
]