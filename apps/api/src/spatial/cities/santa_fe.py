"""Santa Fe, NM spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Santa Fe
(northern New Mexico, Santa Fe County).

Santa Fe is a ONE-FEED PARTIAL metro: COMPLAINTS_311 (``CRM_Report_A_Problem_New_Public``
on the city's ArcGIS Online hosted FeatureServer at
``services7.arcgis.com/p0Gk2nDbPs7KEqSZ``, Tier 1).

Live-probe 2026-08-28 (``.streams/west-santa_fe.md``):

* The city's ArcGIS Hub (``data-thecitydifferent.opendata.arcgis.com``, org
  ``p0Gk2nDbPs7KEqSZ``, "City of Santa Fe") is the ONLY verified data source.
  No Socrata exists; ``santafenm.maps.arcgis.com`` and ``data.santafenm.gov``
  are dead. The ticket's ArcGIS Hub hint is correct (the org is real and
  public), but the subdomain is ``data-thecitydifferent`` not ``santafenm``.
* COMPLAINTS_311 — 2,765 rows, point geometry, native WGS84 (outSR=4326
  returns -105.99x/35.64x), live watermark ``CreationDate`` (esriFieldTypeDate).
  Newest watermark on probe: ``1787949766476`` = 2026-08-28T20:42:46Z (today).
  Date range: 2026-04-10T14:01:42Z → 2026-08-28T20:42:46Z. 0 null geometries.
  Fields: objectid, globalid, problemtype, problem2, status, resolved_on
  (STRING, not a date field), CreationDate, field_notes. problemtype domain
  (15 coded values): abandonedvehicle, arroyoriver, transit, encampments,
  graffiti, dumping, parking, parks, property, roads, streetlights, trash,
  utilities, weeds, other. status values: Submitted(34), Received(673),
  cs_only_resolved(2040), In progress(15), null(3). maxRecordCount 1000,
  no declared supportsOrderBy (orderByFields works — verified).
* SLA, DEEDS, and PERMITS are Tier 3: the city's ``ShortTermRentals2024_1``
  (1,239 rows) is an annual STR-license snapshot with no watermark column
  (Greenville BusinessLicenses precedent); no building-permit or SLA feature
  layer exists in the org; Santa Fe County org (``OrtlXpzQGtgBGqsz``, 88 items)
  has no deeds/sales/assessor feeds.
"""


from src.producers.field_maps_santa_fe import (
    COMPLAINTS_311_FIELD_MAP,
    GEOCODE_CONTEXT,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SANTA_FE_CITY_ID: str = "santa_fe"
SANTA_FE_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Santa Fe (northern NM). Permissive enough to hold the Downtown Plaza
# core (35.6869, -105.9372), the Railyard district, South Capitol, Cerro Gordo,
# the Southside corridor, and the Museum Hill/Eastside areas — plus the live
# probe sample coordinates down to 35.642, -106.013.
SANTA_FE_METRO_BBOX: dict[str, float] = {
    "min_lat": 35.60,
    "max_lat": 35.75,
    "min_lng": -106.05,
    "max_lng": -105.85,
}

# 6 Santa Fe divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need only
# be sane and contain their own submarket centers.
SANTA_FE_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_PLAZA": {
        "min_lat": 35.678,
        "max_lat": 35.695,
        "min_lng": -105.948,
        "max_lng": -105.925,
    },
    "SOUTH_CAPITOL": {
        "min_lat": 35.660,
        "max_lat": 35.680,
        "min_lng": -105.965,
        "max_lng": -105.935,
    },
    "RAILYARD": {
        "min_lat": 35.670,
        "max_lat": 35.690,
        "min_lng": -105.960,
        "max_lng": -105.940,
    },
    "EASTSIDE": {
        "min_lat": 35.675,
        "max_lat": 35.698,
        "min_lng": -105.935,
        "max_lng": -105.910,
    },
    "CERRO_GORDO": {
        "min_lat": 35.686,
        "max_lat": 35.720,
        "min_lng": -105.920,
        "max_lng": -105.885,
    },
    "SOUTHSIDE": {
        "min_lat": 35.620,
        "max_lat": 35.665,
        "min_lng": -106.030,
        "max_lng": -105.960,
    },
}


def is_in_santa_fe_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Santa Fe city bounds."""
    if lat is None or lng is None:
        return False
    return (
        SANTA_FE_METRO_BBOX["min_lat"] <= lat <= SANTA_FE_METRO_BBOX["max_lat"]
        and SANTA_FE_METRO_BBOX["min_lng"] <= lng <= SANTA_FE_METRO_BBOX["max_lng"]
    )


is_in_greater_santa_fe_metro = is_in_santa_fe_metro


SANTA_FE_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_PLAZA (2)
    # =======================================================================
    "Downtown Plaza": SubmarketMeta(
        name="Downtown Plaza",
        borough="DOWNTOWN_PLAZA",
        lat=35.6869,
        lng=-105.9372,
        zoom=15.0,
        pitch=55.0,
        base_lims=0.85,
        capex=5800000.0,
        permit_vel=27.0,
        shift_ratio=1.44,
        sla=50.0,
        description="Historic Santa Fe Plaza core with Palace of the Governors, San Miguel Chapel, and the central mixed-use retail/hospitality corridor.",
        city_id="santa_fe",
    ),
    "Baca Street": SubmarketMeta(
        name="Baca Street",
        borough="DOWNTOWN_PLAZA",
        lat=35.6895,
        lng=-105.9305,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.83,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.38,
        sla=46.0,
        description="Baca Street corridor east of the Plaza with Victorian-era cottages, infill townhomes, and steady renovation permit activity.",
        city_id="santa_fe",
    ),
    # =======================================================================
    # SOUTH_CAPITOL (2)
    # =======================================================================
    "South Capitol": SubmarketMeta(
        name="South Capitol",
        borough="SOUTH_CAPITOL",
        lat=35.6700,
        lng=-105.9500,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.84,
        capex=5400000.0,
        permit_vel=24.0,
        shift_ratio=1.41,
        sla=48.0,
        description="South Capitol neighborhood with the New Mexico State Capitol, government offices, and the emerging Siler Road creative-zone mixed-use corridor.",
        city_id="santa_fe",
    ),
    "Siler Road": SubmarketMeta(
        name="Siler Road",
        borough="SOUTH_CAPITOL",
        lat=35.6650,
        lng=-105.9520,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.82,
        capex=5000000.0,
        permit_vel=21.0,
        shift_ratio=1.36,
        sla=45.0,
        description="Siler Road industrial-artist corridor with warehouse conversions, maker spaces, and light-industrial redevelopment.",
        city_id="santa_fe",
    ),
    # =======================================================================
    # RAILYARD (1)
    # =======================================================================
    "Railyard": SubmarketMeta(
        name="Railyard",
        borough="RAILYARD",
        lat=35.6770,
        lng=-105.9500,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.86,
        capex=6100000.0,
        permit_vel=26.0,
        shift_ratio=1.45,
        sla=52.0,
        description="Santa Fe Railyard district with the Farmers Market, railyard parks, gallery spaces, and the Guadalupe Street retail corridor.",
        city_id="santa_fe",
    ),
    # =======================================================================
    # EASTSIDE (2)
    # =======================================================================
    "Eastside": SubmarketMeta(
        name="Eastside",
        borough="EASTSIDE",
        lat=35.6850,
        lng=-105.9250,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.87,
        capex=6000000.0,
        permit_vel=25.0,
        shift_ratio=1.43,
        sla=51.0,
        description="Eastside including Canyon Road gallery district, Museum Hill, and the historic Acequia Madre neighborhood with high-value adobe renovation permits.",
        city_id="santa_fe",
    ),
    "Casa Solana": SubmarketMeta(
        name="Casa Solana",
        borough="EASTSIDE",
        lat=35.6800,
        lng=-105.9300,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.81,
        capex=4800000.0,
        permit_vel=20.0,
        shift_ratio=1.35,
        sla=44.0,
        description="Casa Solana mid-century residential neighborhood with ranch-style homes, lot splits, and steady alteration permits.",
        city_id="santa_fe",
    ),
    # =======================================================================
    # CERRO_GORDO (2)
    # =======================================================================
    "Cerro Gordo": SubmarketMeta(
        name="Cerro Gordo",
        borough="CERRO_GORDO",
        lat=35.7000,
        lng=-105.9000,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.80,
        capex=5500000.0,
        permit_vel=19.0,
        shift_ratio=1.34,
        sla=43.0,
        description="Cerro Gordo foothills east of downtown with view-lot estate builds, hillside adobe construction, and National Forest adjacency.",
        city_id="santa_fe",
    ),
    "Agua Fria": SubmarketMeta(
        name="Agua Fria",
        borough="CERRO_GORDO",
        lat=35.7080,
        lng=-105.9050,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.79,
        capex=4600000.0,
        permit_vel=18.0,
        shift_ratio=1.32,
        sla=42.0,
        description="Agua Fria Village historic settlement west of the Plaza with agricultural-lot conversions, traditional adobe rehab, and new single-family infill.",
        city_id="santa_fe",
    ),
    # =======================================================================
    # SOUTHSIDE (1)
    # =======================================================================
    "Southside": SubmarketMeta(
        name="Southside",
        borough="SOUTHSIDE",
        lat=35.6400,
        lng=-105.9850,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.78,
        capex=6200000.0,
        permit_vel=23.0,
        shift_ratio=1.40,
        sla=47.0,
        description="Southside corridor along Airport Road and Cerrillos Road with master-planned subdivisions, big-box retail, and the metro's highest new-build permit volume.",
        city_id="santa_fe",
    ),
}


SANTA_FE_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_PLAZA": BoroughMeta(
        name="DOWNTOWN_PLAZA",
        center_lat=35.6869,
        center_lng=-105.9372,
        zoom=14.0,
        bbox=SANTA_FE_DIVISION_BBOXES["DOWNTOWN_PLAZA"],
        submarkets=[k for k, v in SANTA_FE_SUBMARKETS.items() if v.borough == "DOWNTOWN_PLAZA"],
        city_id="santa_fe",
    ),
    "SOUTH_CAPITOL": BoroughMeta(
        name="SOUTH_CAPITOL",
        center_lat=35.6700,
        center_lng=-105.9500,
        zoom=14.0,
        bbox=SANTA_FE_DIVISION_BBOXES["SOUTH_CAPITOL"],
        submarkets=[k for k, v in SANTA_FE_SUBMARKETS.items() if v.borough == "SOUTH_CAPITOL"],
        city_id="santa_fe",
    ),
    "RAILYARD": BoroughMeta(
        name="RAILYARD",
        center_lat=35.6770,
        center_lng=-105.9500,
        zoom=14.0,
        bbox=SANTA_FE_DIVISION_BBOXES["RAILYARD"],
        submarkets=[k for k, v in SANTA_FE_SUBMARKETS.items() if v.borough == "RAILYARD"],
        city_id="santa_fe",
    ),
    "EASTSIDE": BoroughMeta(
        name="EASTSIDE",
        center_lat=35.6850,
        center_lng=-105.9250,
        zoom=13.5,
        bbox=SANTA_FE_DIVISION_BBOXES["EASTSIDE"],
        submarkets=[k for k, v in SANTA_FE_SUBMARKETS.items() if v.borough == "EASTSIDE"],
        city_id="santa_fe",
    ),
    "CERRO_GORDO": BoroughMeta(
        name="CERRO_GORDO",
        center_lat=35.7000,
        center_lng=-105.9000,
        zoom=13.0,
        bbox=SANTA_FE_DIVISION_BBOXES["CERRO_GORDO"],
        submarkets=[k for k, v in SANTA_FE_SUBMARKETS.items() if v.borough == "CERRO_GORDO"],
        city_id="santa_fe",
    ),
    "SOUTHSIDE": BoroughMeta(
        name="SOUTHSIDE",
        center_lat=35.6400,
        center_lng=-105.9850,
        zoom=13.0,
        bbox=SANTA_FE_DIVISION_BBOXES["SOUTHSIDE"],
        submarkets=[k for k, v in SANTA_FE_SUBMARKETS.items() if v.borough == "SOUTHSIDE"],
        city_id="santa_fe",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. COMPLAINTS_311 only (CRM_Report_A_Problem_New_Public).
# No SLA, permits, or deeds feed exists in the city or county org.
# ---------------------------------------------------------------------------
SANTA_FE_311_ENDPOINT = (
    "https://services7.arcgis.com/p0Gk2nDbPs7KEqSZ/arcgis/rest/services/"
    "CRM_Report_A_Problem_New_Public/FeatureServer/0"
)

SANTA_FE_FEED_SPECS: dict[str, dict[str, object]] = {
    "311": {
        "endpoint": SANTA_FE_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "CreationDate",
        "id_keys": ["globalid"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "geocode_context": SANTA_FE_GEOCODE_CONTEXT,
            "oid_field": "objectid",
            "max_record_count": 1000,
            "order_by": "CreationDate DESC",
            "scope": (
                "CRM_Report_A_Problem_New_Public live service requests "
                "(FeatureServer/0 hosted on AGO services7; native 4326 point "
                "geometry, 0 null geometries; CreationDate esriFieldTypeDate "
                "watermark, newest 2026-08-28T20:42Z on probe; "
                "problemtype coded domain 15 values; status STRING coded "
                "domain 5 values; resolved_on is STRING not a date field; "
                "no address column — geometry is the sole coordinate source, "
                "needs_geocode=False; maxRecordCount 1000, orderByFields "
                "supported)"
            ),
            "field_map": COMPLAINTS_311_FIELD_MAP,
        },
    },
}


def get_santa_fe_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Santa Fe feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in SANTA_FE_FEED_SPECS:
        available = ", ".join(sorted(SANTA_FE_FEED_SPECS))
        raise KeyError(
            f"'{SANTA_FE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = SANTA_FE_FEED_SPECS[feed_name]
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
    metro_bbox=SANTA_FE_METRO_BBOX,
    division_bboxes=SANTA_FE_DIVISION_BBOXES,
    submarkets=SANTA_FE_SUBMARKETS,
    divisions=SANTA_FE_DIVISIONS,
    contains=is_in_santa_fe_metro,
)

__all__ = [
    "REGISTRATION",
    "SANTA_FE_311_ENDPOINT",
    "SANTA_FE_CITY_ID",
    "SANTA_FE_DIVISIONS",
    "SANTA_FE_DIVISION_BBOXES",
    "SANTA_FE_FEED_SPECS",
    "SANTA_FE_GEOCODE_CONTEXT",
    "SANTA_FE_METRO_BBOX",
    "SANTA_FE_SUBMARKETS",
    "get_santa_fe_dataset",
    "is_in_greater_santa_fe_metro",
    "is_in_santa_fe_metro",
]