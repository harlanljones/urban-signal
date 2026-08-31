CRIME_FIELD_MAP = {
    "incident_id": ["id", "incident_number"],
    "offense_type": ["incident_type"],
    "occurred_date": ["date_time"],
    "reported_date": ["upload"],
    "borough": ["city"],
    "address": ["intersection", "location_address"],
}

FIELD_MAP = {
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT = "Santa Rosa, CA"

DROPPED_PII_COLUMNS = (
    "agency_code",
    "agency",
)

"""Santa Rosa, CA / Sonoma County spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Santa Rosa
and its county-fringe context (Sonoma County).

Santa Rosa is a ONE-FEED PARTIAL metro: CRIME (Sonoma County Sheriff's
Office Incident Data, Socrata ``3rsj-iche`` on ``data.sonomacounty.ca.gov``,
Tier 1, daily, native Socrata point geometry). Permits, 311, SLA, and deeds
all stay Tier 3 and unregistered.

Live-probe caveats that define this leaf (original probe 2026-08-28,
US-247):

* The city's live data is **PowerBI-only** behind ``Insights.SRCity.org``
  (Building Permits, Community Service Requests, Police Calls for Service,
  Engineering Permits, Water Utility Permits — all PowerBI dashboards, no
  public raw API). The city's AGOL org (santarosa.maps.arcgis.com) holds
  only stale snapshots: Building Permits FeatureServer last updated 2018
  (max IssuedDate 2018-06, max LastUpdated 2018-06); Santa Rosa Police Calls
  for Service CurrentYear tabular view last updated 2020-01; CallsForService
  FeatureServer empty template; Crimes FeatureServer empty template. Parcels
  Sold (814 rows) and RC Building Permits (2,674 rows) are fire-recovery
  specific (2017 Tubbs Fire zone).
* The **Sonoma County Sheriff's Office Incident Data** (3rsj-iche) is the
  only verifiable live feed: 329,685 rows total, 104,564 tagged city=SANTA
  ROSA, max date_time 2026-08-27T12:37:13 (fresh daily), 100% id unique,
  0 null locations. Native Socrata ``location`` point container (``latitude``
  / ``longitude`` dict keys). This is a county sheriff feed covering
  unincorporated areas; the metro bbox filters to the Santa Rosa area.
* County planning permits (m689-iiuu) are unincorporated-only and
  address-only (needs_geocode) with stalled watermark (max started
  2025-05-30, no advancing rows). Construction permits (88ms-k5e7) are
  APN-only — no geometry and no address. Defaulted Tax Data (bp8v-uax7) is
  property/tax, address-only, no geometry. County Recorder unreachable
  (000). None qualify as live feeds.
* PERMITS, COMPLAINTS_311, SLA, and DEEDS all stay Tier 3.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

SANTA_ROSA_CITY_ID: str = "santa_rosa"
SANTA_ROSA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Santa Rosa (Sonoma County, CA). Permissive enough to hold
# Downtown (38.4405, -122.7144), Roseland (38.4310, -122.7360), Bennett
# Valley (38.4040, -122.6570), Rincon Valley (38.4569, -122.6483), North
# Santa Rosa (38.4600, -122.7000), Northwest/Larkfield (38.5100, -122.7500),
# Southwest Santa Rosa (38.4200, -122.7200), and the broader metro area
# including Rohnert Park (south) and Windsor (north).
SANTA_ROSA_METRO_BBOX: dict[str, float] = {
    "min_lat": 38.30,
    "max_lat": 38.58,
    "min_lng": -122.95,
    "max_lng": -122.45,
}

# 6 Santa Rosa divisions. Hand-authored; borough resolution at ingest
# comes from coordinates via get_division_for_coordinate, so bboxes need
# only be sane and contain their own submarket centers.
SANTA_ROSA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 38.432,
        "max_lat": 38.446,
        "min_lng": -122.726,
        "max_lng": -122.706,
    },
    "NORTHWEST": {
        "min_lat": 38.470,
        "max_lat": 38.530,
        "min_lng": -122.770,
        "max_lng": -122.720,
    },
    "NORTH_EAST": {
        "min_lat": 38.445,
        "max_lat": 38.470,
        "min_lng": -122.712,
        "max_lng": -122.680,
    },
    "ROSELAND": {
        "min_lat": 38.410,
        "max_lat": 38.435,
        "min_lng": -122.745,
        "max_lng": -122.710,
    },
    "SOUTHEAST": {
        "min_lat": 38.390,
        "max_lat": 38.420,
        "min_lng": -122.690,
        "max_lng": -122.640,
    },
    "EAST": {
        "min_lat": 38.440,
        "max_lat": 38.470,
        "min_lng": -122.660,
        "max_lng": -122.610,
    },
}


def is_in_santa_rosa_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Santa Rosa metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        SANTA_ROSA_METRO_BBOX["min_lat"] <= lat <= SANTA_ROSA_METRO_BBOX["max_lat"]
        and SANTA_ROSA_METRO_BBOX["min_lng"] <= lng <= SANTA_ROSA_METRO_BBOX["max_lng"]
    )


is_in_greater_santa_rosa_metro = is_in_santa_rosa_metro


SANTA_ROSA_SUBMARKETS: dict[str, SubmarketMeta] = {
    # ===================================================================
    # DOWNTOWN (3)
    # ===================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN",
        lat=38.4405,
        lng=-122.7144,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=52.0,
        description="Old Courthouse Square core with the historic Empire building, Railroad Square adaptive reuse, and the downtown mixed-use permitting corridor.",
        city_id="santa_rosa",
    ),
    "Railroad Square": SubmarketMeta(
        name="Railroad Square",
        borough="DOWNTOWN",
        lat=38.4380,
        lng=-122.7220,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.83,
        capex=5800000.0,
        permit_vel=26.0,
        shift_ratio=1.42,
        sla=50.0,
        description="Historic transit-adjacent district with artisan studios, brewery taprooms, and converted warehouse retail.",
        city_id="santa_rosa",
    ),
    "West End": SubmarketMeta(
        name="West End",
        borough="DOWNTOWN",
        lat=38.4360,
        lng=-122.7180,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.82,
        capex=5400000.0,
        permit_vel=24.0,
        shift_ratio=1.40,
        sla=49.0,
        description="West Ninth Street corridor with bungalow infill, small-scale commercial rehab, and West End studio conversions.",
        city_id="santa_rosa",
    ),
    # ===================================================================
    # NORTHWEST (2)
    # ===================================================================
    "Northwest Santa Rosa": SubmarketMeta(
        name="Northwest Santa Rosa",
        borough="NORTHWEST",
        lat=38.4800,
        lng=-122.7400,
        zoom=13.5,
        pitch=48.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.38,
        sla=48.0,
        description="Mendocino Avenue north corridor with post-war residential, Mark West business park, and Airport Boulevard industrial infill.",
        city_id="santa_rosa",
    ),
    "Larkfield-Wikiup": SubmarketMeta(
        name="Larkfield-Wikiup",
        borough="NORTHWEST",
        lat=38.5100,
        lng=-122.7500,
        zoom=13.0,
        pitch=46.0,
        base_lims=0.78,
        capex=4800000.0,
        permit_vel=20.0,
        shift_ratio=1.36,
        sla=46.0,
        description="Unincorporated north Sonoma County suburban fringe with ranch-style homes, auto-oriented retail, and steady renovation permits.",
        city_id="santa_rosa",
    ),
    # ===================================================================
    # NORTH_EAST (1)
    # ===================================================================
    "North Santa Rosa": SubmarketMeta(
        name="North Santa Rosa",
        borough="NORTH_EAST",
        lat=38.4600,
        lng=-122.7000,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.81,
        capex=5400000.0,
        permit_vel=24.0,
        shift_ratio=1.40,
        sla=49.0,
        description="Cleveland Avenue and Mendocino Avenue north of downtown with mid-century housing stock, strip retail, and steady alteration permits.",
        city_id="santa_rosa",
    ),
    # ===================================================================
    # ROSELAND (2)
    # ===================================================================
    "Roseland": SubmarketMeta(
        name="Roseland",
        borough="ROSELAND",
        lat=38.4310,
        lng=-122.7360,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.76,
        capex=4600000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=45.0,
        description="Sebastopol Road corridor with immigrant-owned small businesses, Hispanic cultural district, and the Roseland Village mixed-use node.",
        city_id="santa_rosa",
    ),
    "Southwest Santa Rosa": SubmarketMeta(
        name="Southwest Santa Rosa",
        borough="ROSELAND",
        lat=38.4200,
        lng=-122.7200,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.77,
        capex=4400000.0,
        permit_vel=22.0,
        shift_ratio=1.36,
        sla=44.0,
        description="West College Avenue corridor with suburban residential, St. Joseph Health campus, and Yulupa Avenue retail pads.",
        city_id="santa_rosa",
    ),
    # ===================================================================
    # SOUTHEAST (2)
    # ===================================================================
    "Bennett Valley": SubmarketMeta(
        name="Bennett Valley",
        borough="SOUTHEAST",
        lat=38.4040,
        lng=-122.6570,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=6000000.0,
        permit_vel=26.0,
        shift_ratio=1.42,
        sla=51.0,
        description="Bennett Valley Road corridor with golf-course residential, Annadel State Park edge, and the Bennett Valley Village center.",
        city_id="santa_rosa",
    ),
    "Southeast Santa Rosa": SubmarketMeta(
        name="Southeast Santa Rosa",
        borough="SOUTHEAST",
        lat=38.4100,
        lng=-122.6800,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.38,
        sla=48.0,
        description="South Avenue corridor with mid-century residential, Oliver's Market area, and Yulupa Boulevard retail.",
        city_id="santa_rosa",
    ),
    # ===================================================================
    # EAST (2)
    # ===================================================================
    "Rincon Valley": SubmarketMeta(
        name="Rincon Valley",
        borough="EAST",
        lat=38.4569,
        lng=-122.6483,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=5800000.0,
        permit_vel=26.0,
        shift_ratio=1.42,
        sla=50.0,
        description="Mission Boulevard east corridor with suburban subdivisions, Rincon Valley Library anchor, and steady new-build permit volume.",
        city_id="santa_rosa",
    ),
    "Fountaingrove": SubmarketMeta(
        name="Fountaingrove",
        borough="EAST",
        lat=38.4600,
        lng=-122.6300,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.86,
        capex=7400000.0,
        permit_vel=30.0,
        shift_ratio=1.48,
        sla=54.0,
        description="East hills master-planned community with custom homes, winery estate lots, and the Fountaingrove golf course residential belt.",
        city_id="santa_rosa",
    ),
}


SANTA_ROSA_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=38.4405,
        center_lng=-122.7144,
        zoom=14.0,
        bbox=SANTA_ROSA_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in SANTA_ROSA_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="santa_rosa",
    ),
    "NORTHWEST": BoroughMeta(
        name="NORTHWEST",
        center_lat=38.4900,
        center_lng=-122.7450,
        zoom=13.0,
        bbox=SANTA_ROSA_DIVISION_BBOXES["NORTHWEST"],
        submarkets=[k for k, v in SANTA_ROSA_SUBMARKETS.items() if v.borough == "NORTHWEST"],
        city_id="santa_rosa",
    ),
    "NORTH_EAST": BoroughMeta(
        name="NORTH_EAST",
        center_lat=38.4560,
        center_lng=-122.6960,
        zoom=13.5,
        bbox=SANTA_ROSA_DIVISION_BBOXES["NORTH_EAST"],
        submarkets=[k for k, v in SANTA_ROSA_SUBMARKETS.items() if v.borough == "NORTH_EAST"],
        city_id="santa_rosa",
    ),
    "ROSELAND": BoroughMeta(
        name="ROSELAND",
        center_lat=38.4250,
        center_lng=-122.7300,
        zoom=13.5,
        bbox=SANTA_ROSA_DIVISION_BBOXES["ROSELAND"],
        submarkets=[k for k, v in SANTA_ROSA_SUBMARKETS.items() if v.borough == "ROSELAND"],
        city_id="santa_rosa",
    ),
    "SOUTHEAST": BoroughMeta(
        name="SOUTHEAST",
        center_lat=38.4050,
        center_lng=-122.6650,
        zoom=13.5,
        bbox=SANTA_ROSA_DIVISION_BBOXES["SOUTHEAST"],
        submarkets=[k for k, v in SANTA_ROSA_SUBMARKETS.items() if v.borough == "SOUTHEAST"],
        city_id="santa_rosa",
    ),
    "EAST": BoroughMeta(
        name="EAST",
        center_lat=38.4580,
        center_lng=-122.6400,
        zoom=13.0,
        bbox=SANTA_ROSA_DIVISION_BBOXES["EAST"],
        submarkets=[k for k, v in SANTA_ROSA_SUBMARKETS.items() if v.borough == "EAST"],
        city_id="santa_rosa",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Register CRIME ONLY — do not register permits, 311,
# SLA, or deeds (all Tier 3 — see caveats above).
# ---------------------------------------------------------------------------
SANTA_ROSA_CRIME_ENDPOINT = "https://data.sonomacounty.ca.gov/resource/3rsj-iche.json"

SANTA_ROSA_FEED_SPECS: dict[str, dict[str, object]] = {
    "crime": {
        "endpoint": SANTA_ROSA_CRIME_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "date_time",
        "id_keys": ["id", "incident_number"],
        "topic_key": "topic_crime",
        "interval_seconds": 300.0,
        "producer_key": "crime",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "order_by": "date_time DESC",
            "scope": (
                "Sonoma County Sheriff's Office Incident Data (Socrata "
                "3rsj-iche) — county sheriff incidents covering unincorporated "
                "Sonoma County including Santa Rosa mailing addresses; native "
                "Socrata point geometry (latitude/longitude dict key); "
                "daily upload (upload column 2026-08-28 on probe); "
                "329,685 rows total, 104,564 city=SANTA ROSA; "
                "100% id unique, 0 null locations; "
                "watermark date_time advances daily"
            ),
            "field_map": CRIME_FIELD_MAP,
        },
    },
}


def get_santa_rosa_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Santa Rosa feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in SANTA_ROSA_FEED_SPECS:
        available = ", ".join(sorted(SANTA_ROSA_FEED_SPECS))
        raise KeyError(
            f"'{SANTA_ROSA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = SANTA_ROSA_FEED_SPECS[feed_name]
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
    metro_bbox=SANTA_ROSA_METRO_BBOX,
    division_bboxes=SANTA_ROSA_DIVISION_BBOXES,
    submarkets=SANTA_ROSA_SUBMARKETS,
    divisions=SANTA_ROSA_DIVISIONS,
    contains=is_in_santa_rosa_metro,
)

__all__ = [
    "REGISTRATION",
    "SANTA_ROSA_CITY_ID",
    "SANTA_ROSA_CRIME_ENDPOINT",
    "SANTA_ROSA_DIVISIONS",
    "SANTA_ROSA_DIVISION_BBOXES",
    "SANTA_ROSA_FEED_SPECS",
    "SANTA_ROSA_GEOCODE_CONTEXT",
    "SANTA_ROSA_METRO_BBOX",
    "SANTA_ROSA_SUBMARKETS",
    "get_santa_rosa_dataset",
    "is_in_greater_santa_rosa_metro",
    "is_in_santa_rosa_metro",
]