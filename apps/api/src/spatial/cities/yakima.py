GEOCODE_CONTEXT = "Yakima, WA"

PERMITS_FIELD_MAP = {
    # OBJECTID is the OID fallback (Henderson/Greenville precedent): live rows
    # always carry PermitID (it is the id_keys head), but the OID keeps
    # coordinate-less/dedup edge rows addressable if a permit number is ever
    # missing client-side.
    "job_id": ["PermitID", "OBJECTID"],
    "issuance_date": ["IssuedOnDate"],
    "filing_date": ["SubmittedOnDate"],
    "status": ["PermitStatus"],
    "job_type": ["PermitType"],
    "address_street": ["SiteStreet"],
    "zipcode": ["SiteZipCode"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

DROPPED_PII_COLUMNS = (
    # YakBack requestor/assignee block (311 follow-up guard). The permit
    # layer itself publishes no owner/contractor columns.
    "name",
    "email",
    "phone",
    "GlobalID",
    "closedBy",
    "assignedTo",
    "updatedBy",
)

"""Yakima, WA spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Yakima
(south-central Washington, Yakima County).

Yakima is a ONE-FEED PARTIAL metro: PERMITS (``BuildingPermits`` FeatureServer
on the city's own ArcGIS open data platform at ``gis.yakimawa.gov``, Tier 1).
COMPLAINTS_311 (the city's YakBack service-request system, ``YakBack/
PublicRequest/MapServer/0``) is **live at the data layer but spine-blocked**:
its ``status`` column is an integer (1=open/2=closed) and the shared
``Complaints311Producer`` maps it straight into the typed
``Complaint311Event.status: Optional[str]`` — pydantic v2 rejects the int and
every row drops (verified live 2026-08-28). Registering it before a spine
str-coercion would silently stream zero events, so it stays Tier 3. DEEDS
(Yakima County assessor sales layers on ``services3.arcgis.com`` org
``9Qz94N8Zml9hnG84``) are STALE STATIC EXTRACTS, not live feeds:
``Res_Sales_History`` stops at SALE_DATE 2024-12-20 and ``Sales_History`` at
DOCUMENT_D 2016 — not registered (Greenville SLA-snapshot precedent). YFD
Calls for Service (fire/EMS dispatch, daily) and the YPD ``Crimes_public``
layer (family-gated crime) are documented candidates, not registered feeds.

Live-probe evidence (original probe 2026-08-28, ``opendata.yakimawa.gov``
ArcGIS Hub + ``gis.yakimawa.gov`` REST):

* The ticket's "city ArcGIS Hub" hint is correct but the Hub is only the
  door: the real feed endpoints live on the org's own ArcGIS Server REST
  services under ``gis.yakimawa.gov`` (the Hub embeds them in its web maps).
* PERMITS is ``gis.yakimawa.gov/arcgis/rest/services/Planning/BuildingPermits/
  FeatureServer/0`` — native ``esriGeometryPoint`` geometry; queries with
  ``outSR=4326`` return WGS84 point geometry on every live row (probe sample
  x=-120.6023…/-120.5264, y=46.5805…/46.5958), which
  ``ArcGISClient._flatten_feature`` lifts to ``latitude``/``longitude``.
  Row count 2,228; watermark ``IssuedOnDate`` newest 1787270400000 =
  2026-08-21T00:00:00+00:00; windows 7d=2 / 30d=87 / 60d=163 (client-side
  where, which the host DOES accept with ISO date literals — not an
  ANSI_DATE_LITERAL_HOSTS candidate). The layer holds a ~2022-10 -> now
  window (oldest SubmittedOnDate 2022-10-27), so ``min(date)`` is not
  staleness evidence. ``IssuedOnDate``/``SubmittedOnDate`` are esri dates and
  ISO-normalize in the ArcGIS client. No valuation/cost column exists.
  ``maxRecordCount`` 2000; OID is ``OBJECTID``.
* The YakBack 311 layer carries point geometry + a composed ``address``
  ("1068-1098 S 48th Ave, Yakima, Washington, 98908"); its integer ``status``
  is the registration blocker (see above).
* No Socrata domain exists (``data.yakimawa.gov`` does not resolve). City
  business licenses are a SmartGov document portal, not open data — no SLA
  feed.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

YAKIMA_CITY_ID: str = "yakima"
YAKIMA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Yakima (south-central WA). Permissive enough to hold the Downtown
# core (46.6021, -120.5059), the Summitview/40th Ave West Valley corridor,
# Terrace Heights across the Yakima River, the East Valley corridor, the
# South 16th / South Yakima belt, and the North Yakima / Nob Hill belt — plus
# the live permit-fixture sample down to 46.58, -120.60.
YAKIMA_METRO_BBOX: dict[str, float] = {
    "min_lat": 46.545,
    "max_lat": 46.635,
    "min_lng": -120.660,
    "max_lng": -120.370,
}

# 6 Yakima divisions. Hand-authored; borough resolution at ingest comes from
# coordinates via get_division_for_coordinate, so bboxes need only be sane
# and contain their own submarket centers.
YAKIMA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 46.595,
        "max_lat": 46.609,
        "min_lng": -120.514,
        "max_lng": -120.498,
    },
    "NORTH_YAKIMA": {
        "min_lat": 46.605,
        "max_lat": 46.630,
        "min_lng": -120.528,
        "max_lng": -120.495,
    },
    "WEST_VALLEY": {
        "min_lat": 46.575,
        "max_lat": 46.600,
        "min_lng": -120.655,
        "max_lng": -120.520,
    },
    "SOUTH_16TH": {
        "min_lat": 46.552,
        "max_lat": 46.576,
        "min_lng": -120.512,
        "max_lng": -120.483,
    },
    "TERRACE_HEIGHTS": {
        "min_lat": 46.596,
        "max_lat": 46.620,
        "min_lng": -120.462,
        "max_lng": -120.433,
    },
    "EAST_VALLEY": {
        "min_lat": 46.550,
        "max_lat": 46.592,
        "min_lng": -120.432,
        "max_lng": -120.378,
    },
}


def is_in_yakima_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Yakima city/urbanized bounds."""
    if lat is None or lng is None:
        return False
    return (
        YAKIMA_METRO_BBOX["min_lat"] <= lat <= YAKIMA_METRO_BBOX["max_lat"]
        and YAKIMA_METRO_BBOX["min_lng"] <= lng <= YAKIMA_METRO_BBOX["max_lng"]
    )


is_in_greater_yakima_metro = is_in_yakima_metro


YAKIMA_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (1)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN",
        lat=46.6021,
        lng=-120.5059,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.84,
        capex=5800000.0,
        permit_vel=18.0,
        shift_ratio=1.38,
        sla=52.0,
        description="Yakima Avenue / Front Street downtown core with the Capitol Theatre, civic buildings, and the riverfront Millennium Plaza — the metro's densest mixed-use permitting corridor.",
        city_id="yakima",
    ),
    # =======================================================================
    # NORTH_YAKIMA (2)
    # =======================================================================
    "Nob Hill": SubmarketMeta(
        name="Nob Hill",
        borough="NORTH_YAKIMA",
        lat=46.6085,
        lng=-120.5190,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.83,
        capex=5200000.0,
        permit_vel=14.0,
        shift_ratio=1.34,
        sla=48.0,
        description="Nob Hill Boulevard corridor of mid-century housing, retail nodes, and steady infill between downtown and the north hill residential belt.",
        city_id="yakima",
    ),
    "North Yakima": SubmarketMeta(
        name="North Yakima",
        borough="NORTH_YAKIMA",
        lat=46.6180,
        lng=-120.5070,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.82,
        capex=4900000.0,
        permit_vel=12.0,
        shift_ratio=1.30,
        sla=45.0,
        description="N 1st–20th / Washington Ave northside stock with single-family turnover, duplex conversions, and quiet corridor infill.",
        city_id="yakima",
    ),
    # =======================================================================
    # WEST_VALLEY (2)
    # =======================================================================
    "Summitview": SubmarketMeta(
        name="Summitview",
        borough="WEST_VALLEY",
        lat=46.5900,
        lng=-120.5600,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.85,
        capex=6100000.0,
        permit_vel=16.0,
        shift_ratio=1.40,
        sla=50.0,
        description="Summitview Avenue west corridor — the city's primary retail-commercial spine with grocery anchors, office parks, and steady mixed-use permitting.",
        city_id="yakima",
    ),
    "West Valley": SubmarketMeta(
        name="West Valley",
        borough="WEST_VALLEY",
        lat=46.5840,
        lng=-120.6300,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.86,
        capex=6800000.0,
        permit_vel=15.0,
        shift_ratio=1.42,
        sla=49.0,
        description="40th Ave / Wide Hollow Rd edge of the West Valley school-district corridor with newer subdivisions, townhome infill, and the metro's largest new-build SFR valuations.",
        city_id="yakima",
    ),
    # =======================================================================
    # SOUTH_16TH (2)
    # =======================================================================
    "South 16th": SubmarketMeta(
        name="South 16th",
        borough="SOUTH_16TH",
        lat=46.5620,
        lng=-120.4980,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.81,
        capex=4600000.0,
        permit_vel=10.0,
        shift_ratio=1.28,
        sla=42.0,
        description="S 16th Ave industrial-adjacent belt with older single-family stock, light-industrial conversions, and affordable-housing permitting.",
        city_id="yakima",
    ),
    "South Yakima": SubmarketMeta(
        name="South Yakima",
        borough="SOUTH_16TH",
        lat=46.5720,
        lng=-120.4920,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=5000000.0,
        permit_vel=11.0,
        shift_ratio=1.29,
        sla=44.0,
        description="S 1st / S Front St south-central neighborhood with bungalow infill, corner-store retail, and steady small-scale alteration permits.",
        city_id="yakima",
    ),
    # =======================================================================
    # TERRACE_HEIGHTS (1)
    # =======================================================================
    "Terrace Heights": SubmarketMeta(
        name="Terrace Heights",
        borough="TERRACE_HEIGHTS",
        lat=46.6060,
        lng=-120.4470,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=5400000.0,
        permit_vel=13.0,
        shift_ratio=1.33,
        sla=47.0,
        description="East-bank residential district across the Yakima River (Terrace Heights Dr / Keys Rd) with starter homes, ag-edge lots, and new single-family builds.",
        city_id="yakima",
    ),
    # =======================================================================
    # EAST_VALLEY (1)
    # =======================================================================
    "East Valley": SubmarketMeta(
        name="East Valley",
        borough="EAST_VALLEY",
        lat=46.5750,
        lng=-120.4200,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.80,
        capex=4700000.0,
        permit_vel=9.0,
        shift_ratio=1.26,
        sla=40.0,
        description="East Valley corridor toward Moxee — farm-town edge with rural residential splits, ag support structures, and low-density infill permitting.",
        city_id="yakima",
    ),
}


YAKIMA_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=46.6021,
        center_lng=-120.5059,
        zoom=14.0,
        bbox=YAKIMA_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in YAKIMA_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="yakima",
    ),
    "NORTH_YAKIMA": BoroughMeta(
        name="NORTH_YAKIMA",
        center_lat=46.6180,
        center_lng=-120.5070,
        zoom=13.5,
        bbox=YAKIMA_DIVISION_BBOXES["NORTH_YAKIMA"],
        submarkets=[k for k, v in YAKIMA_SUBMARKETS.items() if v.borough == "NORTH_YAKIMA"],
        city_id="yakima",
    ),
    "WEST_VALLEY": BoroughMeta(
        name="WEST_VALLEY",
        center_lat=46.5900,
        center_lng=-120.5700,
        zoom=13.0,
        bbox=YAKIMA_DIVISION_BBOXES["WEST_VALLEY"],
        submarkets=[k for k, v in YAKIMA_SUBMARKETS.items() if v.borough == "WEST_VALLEY"],
        city_id="yakima",
    ),
    "SOUTH_16TH": BoroughMeta(
        name="SOUTH_16TH",
        center_lat=46.5640,
        center_lng=-120.4980,
        zoom=13.5,
        bbox=YAKIMA_DIVISION_BBOXES["SOUTH_16TH"],
        submarkets=[k for k, v in YAKIMA_SUBMARKETS.items() if v.borough == "SOUTH_16TH"],
        city_id="yakima",
    ),
    "TERRACE_HEIGHTS": BoroughMeta(
        name="TERRACE_HEIGHTS",
        center_lat=46.6060,
        center_lng=-120.4470,
        zoom=13.5,
        bbox=YAKIMA_DIVISION_BBOXES["TERRACE_HEIGHTS"],
        submarkets=[k for k, v in YAKIMA_SUBMARKETS.items() if v.borough == "TERRACE_HEIGHTS"],
        city_id="yakima",
    ),
    "EAST_VALLEY": BoroughMeta(
        name="EAST_VALLEY",
        center_lat=46.5720,
        center_lng=-120.4150,
        zoom=13.0,
        bbox=YAKIMA_DIVISION_BBOXES["EAST_VALLEY"],
        submarkets=[k for k, v in YAKIMA_SUBMARKETS.items() if v.borough == "EAST_VALLEY"],
        city_id="yakima",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register the YakBack 311 feed (integer status
# column drops every row in Complaints311Producer until the spine str-coerces
# it), the county sales layers (stale static extracts), YFD calls, or crime.
# ---------------------------------------------------------------------------
YAKIMA_PERMITS_ENDPOINT = (
    "https://gis.yakimawa.gov/arcgis/rest/services/Planning/"
    "BuildingPermits/FeatureServer/0"
)

YAKIMA_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": YAKIMA_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "IssuedOnDate",
        "id_keys": ["PermitID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 14,
            "needs_geocode": True,
            "geocode_context": YAKIMA_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "IssuedOnDate DESC",
            "scope": (
                "Planning/BuildingPermits/FeatureServer/0 on gis.yakimawa.gov "
                "(city ArcGIS open data; native esriGeometryPoint, outSR=4326 "
                "WGS84 on every row; ~2,228 rows in a ~2022-10 -> now window "
                "so min(date) is not staleness; IssuedOnDate watermark newest "
                "2026-08-21T00:00:00+00:00, where-clause queryable with ISO "
                "date literals — NOT an ANSI_DATE_LITERAL_HOSTS candidate; "
                "no valuation/cost column — cost unmapped, producer defaults "
                "0.0; SiteCity/SiteState fixed YAKIMA/WA unmapped; no "
                "borough/parcel columns — division resolution is "
                "coordinate-based, source_neighborhood passes None)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
}


def get_yakima_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Yakima feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in YAKIMA_FEED_SPECS:
        available = ", ".join(sorted(YAKIMA_FEED_SPECS))
        raise KeyError(
            f"'{YAKIMA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = YAKIMA_FEED_SPECS[feed_name]
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
    metro_bbox=YAKIMA_METRO_BBOX,
    division_bboxes=YAKIMA_DIVISION_BBOXES,
    submarkets=YAKIMA_SUBMARKETS,
    divisions=YAKIMA_DIVISIONS,
    contains=is_in_yakima_metro,
)

__all__ = [
    "REGISTRATION",
    "YAKIMA_CITY_ID",
    "YAKIMA_DIVISIONS",
    "YAKIMA_DIVISION_BBOXES",
    "YAKIMA_FEED_SPECS",
    "YAKIMA_GEOCODE_CONTEXT",
    "YAKIMA_METRO_BBOX",
    "YAKIMA_PERMITS_ENDPOINT",
    "YAKIMA_SUBMARKETS",
    "get_yakima_dataset",
    "is_in_greater_yakima_metro",
    "is_in_yakima_metro",
]
