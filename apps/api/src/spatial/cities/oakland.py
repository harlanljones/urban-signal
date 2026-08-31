OAKLAND_311_FIELD_MAP = {
    "incident_id": ["requestid"],
    "latitude": ["sry"],
    "longitude": ["srx"],
    "created_date": ["datetimeinit"],
    "closed_date": ["datetimeclosed"],
    "complaint_type": ["reqcategory"],
    "borough": ["councildistrict"],
    "incident_address": ["probaddress"],
    "zipcode": ["zipcode"],
}

OAKLAND_CRIME_FIELD_MAP = {
    "incident_id": ["casenumber"],
    "offense_type": ["crimetype"],
    "occurred_date": ["datetime"],
    "borough": ["policebeat"],
    "address": ["address"],
}

FIELD_MAP = {
    "311": OAKLAND_311_FIELD_MAP,
    "crime": OAKLAND_CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT = "Oakland, CA"

DROPPED_NONADDRESS_COLUMNS = (
    "reqaddress",
    "beat",
    "status",
    "source",
    "referredto",
    ":@computed_region_w23w_jfhw",
)

"""Oakland, CA spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Oakland
(Alameda County, West-region Bay Area metro).

Oakland is a TWO-FEED PARTIAL metro on the official Socrata domain
``data.oaklandca.gov``: COMPLAINTS_311 (``quth-gb8e``, OAK 311 Call
Center service requests, 1,185,559 rows) and CRIME (``ppgh-7dqv``, OPD
CrimeWatch Data, 1,281,231 rows — coordinates AND address, so it clears
the ADR-0004 gate). PERMITS, SLA, and DEEDS are Tier 3 and stay
unregistered: no permits dataset exists on the domain (313 datasets
enumerated 2026-08-28; zero permit hits) and the Accela citizen portal is
interactive-only (acacontrib.oaklandca.gov / aca.oaklandca.gov, HTTP 000);
no business-license/tax registry is published (SLA absent); Alameda County
LANDATA (landata.acgov.org) is unreachable with no anonymous bulk API
(deeds absent — partial registration per ticket).

Live-probe evidence that defines this leaf (probed 2026-08-28 UTC, US-223):

* 311 row count **1,185,559 live**, every ``requestid`` unique (count
  distinct == count). ``datetimeinit`` newest verbatim
  **2026-08-28T04:59:31.000** (same-day); dataset rowsUpdatedAt
  2026-08-28T13:05:30Z. Cadence: 17,715 rows since 2026-07-01
  (≈8.5k/month) → ``expected_cadence_days=1``. No future-dated rows.
* CRIME newest ``datetime`` verbatim **2026-08-25T22:57:00.000**;
  rowsUpdatedAt 2026-08-27T12:51:07Z (≈daily publication lag). Archive
  spans 1950-01-04 → 2026-08-25 (OPD historical backfill is in-band, not
  staleness). ``casenumber`` is not unique — case 26-036393 carries three
  descriptions live — so ``id_keys`` is [casenumber, description] and the
  event incident_id is the casenumber.
* **srx/sry name trap (311)**: the columns echo St. Louis's projected x/y
  names but carry **WGS84 degrees** on this dataset (srx = longitude,
  sry = latitude; verified across 2023-2026 rows from Phone and
  SeeClickFix sources). Mapped directly; the producer's projected-
  coordinate guard is the second net against any projected-era rows.
* **reqaddress poison (311)**: the Socrata location container carries
  mid-Pacific placeholders on SeeClickFix rows (live: latitude
  "30.009927…", longitude "-141.219150…") — never a candidate; the key is
  ``reqaddress`` so the parser's ``location`` point-container fallback
  never sees it either.
* **Null geometry**: 311 null srx/sry 23,897 (2%) and crime null location
  58,587 (4.6%) fall to the ADR-0004 geocode supplement (311 on
  ``probaddress``, crime on ``address`` text; context "Oakland, CA").
  Both feeds declare ``needs_geocode``.
* The sibling rolling 90-day crime view (``ym6k-rx7a``, 7,990 rows) is
  NOT registered: its point container is ``location_1`` (the parser's
  GeoJSON fallback reads ``location`` only) and the full archive serves
  both history and 1-day freshness.
* Metro bbox is the rectangle holding city flatlands and hills: it
  admits the enclaves Piedmont and, at the edges, Alameda / Emeryville
  / a San-Leandro fringe — permissive-bbox doctrine; division resolution
  and analytics scoping are downstream. Reject test coordinates are
  chosen genuinely outside (San Francisco, San Jose).
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

OAKLAND_CITY_ID: str = "oakland"
OAKLAND_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Oakland flatlands + hills. Holds Downtown (37.8040, -122.2712),
# the Lake Merritt bowl, the Temescal/Rockridge north corridor, Fruitvale,
# deep-East Eastmont/Elmhurst (37.7180, -122.1650), the OAK airport
# (37.7126, -122.2212), and the live fixture extremes (37.7303–37.8357,
# -122.2920–-122.1752) — while excluding San Francisco (-122.42) and
# San Jose.
OAKLAND_METRO_BBOX: dict[str, float] = {
    "min_lat": 37.696,
    "max_lat": 37.885,
    "min_lng": -122.360,
    "max_lng": -122.114,
}

# 7 Oakland divisions. Hand-authored, mutually disjoint; borough resolution
# at ingest comes from coordinates via get_division_for_coordinate, so
# bboxes need only be sane and contain their own submarket centers.
OAKLAND_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "WEST_OAKLAND": {
        "min_lat": 37.795,
        "max_lat": 37.812,
        "min_lng": -122.335,
        "max_lng": -122.282,
    },
    "DOWNTOWN_CORE": {
        "min_lat": 37.794,
        "max_lat": 37.812,
        "min_lng": -122.282,
        "max_lng": -122.264,
    },
    "LAKE_MERRITT_GRAND_LAKE": {
        "min_lat": 37.792,
        "max_lat": 37.815,
        "min_lng": -122.264,
        "max_lng": -122.240,
    },
    "NORTH_OAKLAND": {
        "min_lat": 37.815,
        "max_lat": 37.860,
        "min_lng": -122.310,
        "max_lng": -122.249,
    },
    "HILLS_MONTCLAIR": {
        "min_lat": 37.815,
        "max_lat": 37.878,
        "min_lng": -122.249,
        "max_lng": -122.185,
    },
    "EAST_OAKLAND_FRUITVALE": {
        "min_lat": 37.740,
        "max_lat": 37.792,
        "min_lng": -122.245,
        "max_lng": -122.150,
    },
    "EASTMONT_DEEP_EAST": {
        "min_lat": 37.696,
        "max_lat": 37.740,
        "min_lng": -122.220,
        "max_lng": -122.140,
    },
}


def is_in_oakland_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Oakland metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        OAKLAND_METRO_BBOX["min_lat"] <= lat <= OAKLAND_METRO_BBOX["max_lat"]
        and OAKLAND_METRO_BBOX["min_lng"] <= lng <= OAKLAND_METRO_BBOX["max_lng"]
    )


is_in_greater_oakland_metro = is_in_oakland_metro


OAKLAND_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # WEST_OAKLAND (1)
    # =======================================================================
    "West Oakland": SubmarketMeta(
        name="West Oakland",
        borough="WEST_OAKLAND",
        lat=37.8060,
        lng=-122.2950,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.82,
        capex=7400000.0,
        permit_vel=34.0,
        shift_ratio=1.53,
        sla=58.0,
        description="Mandela Parkway corridor with Victorian rowhouse stock, the Seventh Street cultural heritage blocks, and infill reinvestment beside the Port and West Oakland BART.",
        city_id="oakland",
    ),
    # =======================================================================
    # DOWNTOWN_CORE (2)
    # =======================================================================
    "Downtown Oakland": SubmarketMeta(
        name="Downtown Oakland",
        borough="DOWNTOWN_CORE",
        lat=37.8040,
        lng=-122.2712,
        zoom=14.5,
        pitch=54.0,
        base_lims=0.87,
        capex=11800000.0,
        permit_vel=42.0,
        shift_ratio=1.58,
        sla=68.0,
        description="Frank Ogawa Plaza and the CBD core with the 19th Street BART office market, new residential towers, and the Chinatown-adjacent retail spine.",
        city_id="oakland",
    ),
    "Uptown": SubmarketMeta(
        name="Uptown",
        borough="DOWNTOWN_CORE",
        lat=37.8090,
        lng=-122.2670,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.89,
        capex=10400000.0,
        permit_vel=39.0,
        shift_ratio=1.56,
        sla=66.0,
        description="Telegraph Avenue entertainment district with the Fox and Paramount theatres, the Uptown Station office conversion, and Oakland's densest bar-and-restaurant turnover.",
        city_id="oakland",
    ),
    # =======================================================================
    # LAKE_MERRITT_GRAND_LAKE (2)
    # =======================================================================
    "Lake Merritt": SubmarketMeta(
        name="Lake Merritt",
        borough="LAKE_MERRITT_GRAND_LAKE",
        lat=37.7970,
        lng=-122.2560,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.88,
        capex=9600000.0,
        permit_vel=35.0,
        shift_ratio=1.52,
        sla=63.0,
        description="Lakeside apartment belt with the Cleveland Heights edge, Adams Point multifamily stock, and the Lakeshore retail corridor ringing the nation's first wildlife refuge.",
        city_id="oakland",
    ),
    "Grand Lake": SubmarketMeta(
        name="Grand Lake",
        borough="LAKE_MERRITT_GRAND_LAKE",
        lat=37.8075,
        lng=-122.2490,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=8200000.0,
        permit_vel=32.0,
        shift_ratio=1.49,
        sla=60.0,
        description="Grand Avenue retailer strip below the Grand Lake Theatre with walkable cafe-frontage blocks, Craftsman renovation demand, and Lakeview terrace housing.",
        city_id="oakland",
    ),
    # =======================================================================
    # NORTH_OAKLAND (2)
    # =======================================================================
    "Temescal": SubmarketMeta(
        name="Temescal",
        borough="NORTH_OAKLAND",
        lat=37.8285,
        lng=-122.2680,
        zoom=14.0,
        pitch=50.0,
        base_lims=0.87,
        capex=8900000.0,
        permit_vel=37.0,
        shift_ratio=1.54,
        sla=64.0,
        description="Telegraph/51st merchant district with restaurant-row foot traffic, former-industrial live-work conversions, and the MacArthur BART transit-adjacent infill.",
        city_id="oakland",
    ),
    "Rockridge": SubmarketMeta(
        name="Rockridge",
        borough="NORTH_OAKLAND",
        lat=37.8410,
        lng=-122.2530,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.91,
        capex=13500000.0,
        permit_vel=31.0,
        shift_ratio=1.50,
        sla=72.0,
        description="College Avenue premium retail spine with bungalow-stock renovation, College Prep/BART walkability, and the metro's top single-family valuation band.",
        city_id="oakland",
    ),
    # =======================================================================
    # HILLS_MONTCLAIR (2)
    # =======================================================================
    "Montclair": SubmarketMeta(
        name="Montclair",
        borough="HILLS_MONTCLAIR",
        lat=37.8410,
        lng=-122.2160,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.90,
        capex=11200000.0,
        permit_vel=28.0,
        shift_ratio=1.47,
        sla=70.0,
        description="Mountain Boulevard village core with hillside view lots, mid-century estate turnover, and the Montclair village retail block.",
        city_id="oakland",
    ),
    "Skyline Hills": SubmarketMeta(
        name="Skyline Hills",
        borough="HILLS_MONTCLAIR",
        lat=37.8420,
        lng=-122.1950,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.84,
        capex=7800000.0,
        permit_vel=24.0,
        shift_ratio=1.44,
        sla=56.0,
        description="Skyline Boulevard crest neighborhoods with canyon-view properties, Joaquin Miller/Chabot park adjacency, and low-density custom-build permitting.",
        city_id="oakland",
    ),
    # =======================================================================
    # EAST_OAKLAND_FRUITVALE (2)
    # =======================================================================
    "Fruitvale": SubmarketMeta(
        name="Fruitvale",
        borough="EAST_OAKLAND_FRUITVALE",
        lat=37.7750,
        lng=-122.2150,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.81,
        capex=6800000.0,
        permit_vel=33.0,
        shift_ratio=1.55,
        sla=55.0,
        description="International Boulevard Latino commercial spine with the Fruitvale BART transit village, mixed-use Paseo redevelopment, and dense multifamily turnover.",
        city_id="oakland",
    ),
    "San Antonio": SubmarketMeta(
        name="San Antonio",
        borough="EAST_OAKLAND_FRUITVALE",
        lat=37.7905,
        lng=-122.2345,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=31.0,
        shift_ratio=1.52,
        sla=53.0,
        description="East Lake and San Antonio flatlands with the Park Street bridge-frontage blocks, oldest Victorian stock in the metro, and strong small-multifamily conversion demand.",
        city_id="oakland",
    ),
    # =======================================================================
    # EASTMONT_DEEP_EAST (2)
    # =======================================================================
    "Eastmont": SubmarketMeta(
        name="Eastmont",
        borough="EASTMONT_DEEP_EAST",
        lat=37.7320,
        lng=-122.1900,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=29.0,
        shift_ratio=1.56,
        sla=50.0,
        description="Eastmont Town Center district with the 73rd/98th Avenue corridors, large-lot single-family stock, and community-benefit redevelopment along Foothill.",
        city_id="oakland",
    ),
    "Elmhurst": SubmarketMeta(
        name="Elmhurst",
        borough="EASTMONT_DEEP_EAST",
        lat=37.7180,
        lng=-122.1650,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.77,
        capex=5400000.0,
        permit_vel=27.0,
        shift_ratio=1.54,
        sla=49.0,
        description="Southernmost flatlands along the San Leandro border with post-war starter stock, the Hegenberger logistics corridor, and airport-adjacent industrial conversion.",
        city_id="oakland",
    ),
}


OAKLAND_DIVISIONS: dict[str, BoroughMeta] = {
    "WEST_OAKLAND": BoroughMeta(
        name="WEST_OAKLAND",
        center_lat=37.8045,
        center_lng=-122.3030,
        zoom=13.5,
        bbox=OAKLAND_DIVISION_BBOXES["WEST_OAKLAND"],
        submarkets=[k for k, v in OAKLAND_SUBMARKETS.items() if v.borough == "WEST_OAKLAND"],
        city_id="oakland",
    ),
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=37.8060,
        center_lng=-122.2690,
        zoom=13.5,
        bbox=OAKLAND_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in OAKLAND_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="oakland",
    ),
    "LAKE_MERRITT_GRAND_LAKE": BoroughMeta(
        name="LAKE_MERRITT_GRAND_LAKE",
        center_lat=37.8020,
        center_lng=-122.2520,
        zoom=13.5,
        bbox=OAKLAND_DIVISION_BBOXES["LAKE_MERRITT_GRAND_LAKE"],
        submarkets=[k for k, v in OAKLAND_SUBMARKETS.items() if v.borough == "LAKE_MERRITT_GRAND_LAKE"],
        city_id="oakland",
    ),
    "NORTH_OAKLAND": BoroughMeta(
        name="NORTH_OAKLAND",
        center_lat=37.8350,
        center_lng=-122.2790,
        zoom=13.5,
        bbox=OAKLAND_DIVISION_BBOXES["NORTH_OAKLAND"],
        submarkets=[k for k, v in OAKLAND_SUBMARKETS.items() if v.borough == "NORTH_OAKLAND"],
        city_id="oakland",
    ),
    "HILLS_MONTCLAIR": BoroughMeta(
        name="HILLS_MONTCLAIR",
        center_lat=37.8410,
        center_lng=-122.2150,
        zoom=13.0,
        bbox=OAKLAND_DIVISION_BBOXES["HILLS_MONTCLAIR"],
        submarkets=[k for k, v in OAKLAND_SUBMARKETS.items() if v.borough == "HILLS_MONTCLAIR"],
        city_id="oakland",
    ),
    "EAST_OAKLAND_FRUITVALE": BoroughMeta(
        name="EAST_OAKLAND_FRUITVALE",
        center_lat=37.7660,
        center_lng=-122.2220,
        zoom=13.0,
        bbox=OAKLAND_DIVISION_BBOXES["EAST_OAKLAND_FRUITVALE"],
        submarkets=[k for k, v in OAKLAND_SUBMARKETS.items() if v.borough == "EAST_OAKLAND_FRUITVALE"],
        city_id="oakland",
    ),
    "EASTMONT_DEEP_EAST": BoroughMeta(
        name="EASTMONT_DEEP_EAST",
        center_lat=37.7250,
        center_lng=-122.1850,
        zoom=13.0,
        bbox=OAKLAND_DIVISION_BBOXES["EASTMONT_DEEP_EAST"],
        submarkets=[k for k, v in OAKLAND_SUBMARKETS.items() if v.borough == "EASTMONT_DEEP_EAST"],
        city_id="oakland",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed live 2026-08-28 UTC (US-223). Do not register the rolling 90-day
# crime view (ym6k-rx7a, location_1 container), the equity-indicator
# aggregates, or any permits/SLA/deeds feed — none exist (see docstring).
# ---------------------------------------------------------------------------
OAKLAND_311_ENDPOINT = "https://data.oaklandca.gov/resource/quth-gb8e.json"
OAKLAND_CRIME_ENDPOINT = "https://data.oaklandca.gov/resource/ppgh-7dqv.json"

OAKLAND_FEED_SPECS: dict[str, dict[str, object]] = {
    "311": {
        "endpoint": OAKLAND_311_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "datetimeinit",
        "id_keys": ["requestid"],
        "topic_key": "topic_311",
        "interval_seconds": 180.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "watermark_exclude": [],
            "ingestion_mode": "incremental",
            "needs_geocode": True,
            "geocode_context": OAKLAND_GEOCODE_CONTEXT,
            "scope": (
                "OAK 311 Call Center service requests (1,185,559 rows; "
                "requestid unique). srx/sry carry WGS84 degrees despite "
                "x/y names (srx=lng, sry=lat — verified 2023-2026 rows); "
                "reqaddress location container is poisoned on SeeClickFix "
                "rows (lat 30.0099 / lng -141.219) and is never mapped; "
                "2% null-coordinate rows geocode on probaddress (ADR-0004); "
                "no future-dated rows; 0 permits/SLA datasets exist on the "
                "domain — partial registration"
            ),
            "field_map": OAKLAND_311_FIELD_MAP,
        },
    },
    "crime": {
        "endpoint": OAKLAND_CRIME_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "datetime",
        "id_keys": ["casenumber", "description"],
        "topic_key": "topic_crime",
        "interval_seconds": 1800.0,
        "producer_key": "crime",
        "extra": {
            "expected_cadence_days": 1,
            "watermark_exclude": [],
            "ingestion_mode": "incremental",
            "needs_geocode": True,
            "geocode_context": OAKLAND_GEOCODE_CONTEXT,
            "scope": (
                "OPD CrimeWatch Data (1,281,231 rows; archive spans "
                "1950-01-04 to 2026-08-25 — historical backfill is in-band, "
                "not staleness). location is a Socrata GeoJSON point "
                "container read natively by the crime parser fallback; "
                "4.6% null-location rows geocode on address (ADR-0004: "
                "coordinates AND address present — gate cleared); "
                "casenumber repeats across multi-offense cases so id_keys "
                "pairs it with description; rolling 90-day sibling "
                "(ym6k-rx7a, location_1) NOT registered"
            ),
            "field_map": OAKLAND_CRIME_FIELD_MAP,
        },
    },
}


def get_oakland_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Oakland feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in OAKLAND_FEED_SPECS:
        available = ", ".join(sorted(OAKLAND_FEED_SPECS))
        raise KeyError(
            f"'{OAKLAND_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = OAKLAND_FEED_SPECS[feed_name]
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
    metro_bbox=OAKLAND_METRO_BBOX,
    division_bboxes=OAKLAND_DIVISION_BBOXES,
    submarkets=OAKLAND_SUBMARKETS,
    divisions=OAKLAND_DIVISIONS,
    contains=is_in_oakland_metro,
)

__all__ = [
    "OAKLAND_311_ENDPOINT",
    "OAKLAND_CITY_ID",
    "OAKLAND_CRIME_ENDPOINT",
    "OAKLAND_DIVISIONS",
    "OAKLAND_DIVISION_BBOXES",
    "OAKLAND_FEED_SPECS",
    "OAKLAND_GEOCODE_CONTEXT",
    "OAKLAND_METRO_BBOX",
    "OAKLAND_SUBMARKETS",
    "REGISTRATION",
    "get_oakland_dataset",
    "is_in_greater_oakland_metro",
    "is_in_oakland_metro",
]
