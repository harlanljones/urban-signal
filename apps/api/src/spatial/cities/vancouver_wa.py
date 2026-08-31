PERMITS_FIELD_MAP = {
    "job_id": ["CSM_CASENO", "sn", "OBJECTID"],
    "issuance_date": ["csm_issued_date"],
    "status": ["CSM_STATUS"],
    "job_type": ["worktype", "cst_description"],
    "address_street": ["PRIM_ADDR"],
    "proposed_units": ["CSM_NO_UNITS"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Vancouver, WA"

"""Vancouver, WA spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Vancouver,
Washington (Clark County, across the Columbia from Portland).

Vancouver is a ONE-FEED PARTIAL metro: PERMITS only, from the
``Permits_and_Code_Enforcement_Data_(public_view)`` FeatureServer/0
("Permit Data") on the city's AGOL org (``CityOfVancouverGISAdmin`` at
``services.arcgis.com/oNvpY90qsPDizwkN``). 311, SLA, and DEEDS stay Tier 3:
311 lives on a token-gated internal server, no public business-license feed
exists (WA L&I/LCB state registries are spine companions), and Clark County
recorder deeds are a web app with no machine-readable feed.

Live-probe caveats that define this leaf (2026-08-28, US-233):

* The ticket's ArcGIS Hub hint points at ``vancouverwa.opendata.arcgis.com``,
  a **decommissioned** legacy Open Data domain ("This site is no longer
  supported"). The real public door is the city's AGOL org found via the
  ArcGIS Online sharing API (``owner=CityOfVancouverGISAdmin``).
* PERMITS is the ``Permits_and_Code_Enforcement_Data`` public view, daily:
  newest ``csm_issued_date`` on the live probe was ``1786781763000`` =
  2026-08-15T08:16:03+00:00; window counts 90d=2,812, since 2026-01-01=8,010,
  total 44,744. Two future-date sentinels (2039-05-19, 2049-10-31, both
  Closed/ELECTRICAL) are excluded by the ``where`` guard
  ``csm_issued_date <= CURRENT_TIMESTAMP`` (Anchorage discipline; the
  scheduler US-111 future guard is the second line of defense).
* ``csm_issued_date`` IS where-clause queryable with ISO strings (NOT an
  ANSI_DATE_LITERAL_HOSTS member) — order with ``orderByFields`` too.
* Coordinates are **native point geometry**: queries with ``outSR=4326``
  return in-city WGS84 point geometry (live extent -122.768/-122.464,
  45.579/45.702), which ``ArcGISClient._flatten_feature`` lifts to
  ``latitude``/``longitude``. The ``Y``/``X`` *attributes* are **WA State
  Plane South feet** (≈1.1e5 / 1.08e6) — never mapped, never emitted as
  degrees; the producer's projected-coordinate guard is a second net.
* ``PRIM_ADDR`` is the address fallback (0 nulls live); rows without
  geometry resolve through the ADR 0004 geocode supplement with context
  "Vancouver, WA". No site-zip or parcel/APN column exists, so ``zipcode``
  and ``bbl`` stay undeclared.
* No neighborhood/district column exists on the layer, so no ``borough``
  field-map candidate is declared (Omaha discipline): division resolution
  comes from coordinates at ingest, and ``source_neighborhood`` passes
  through as None.
* The related ``Development_Projects_Mapped_WFL1`` FeatureServer/3 CMI layer
  (5,779 rows) is NOT registered: it carries a mixed-CRS trap (outSR=4326
  geometry is garbage on ~4,620/5,779 rows while native Latitude/Longitude
  columns are correct) and would collide with the permits job name
  (same FeedType.PERMITS + city_id). It stays Tier-3 evidence for the
  divisions/submarkets catalogued here.
* Felida (ticket suggestion) is unincorporated north of the city and has no
  permit coverage (1 row north of 45.70 in the live layer) — not a division.
"""

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

VANCOUVER_WA_CITY_ID: str = "vancouver_wa"
VANCOUVER_WA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Vancouver, WA. Permissive enough to hold the downtown core
# (~45.628, -122.679 at Esther Short), Uptown Village (~45.632, -122.672),
# Fruit Valley NW (~45.667, -122.721), the Fourth Plain central belt, Cascade
# Park / East Mill Plain (~45.620, -122.512), and Fisher's Landing SE
# (~45.604, -122.490) — plus the live re-probe extent (-122.768/-122.464,
# 45.579/45.702). Felida (north, ~45.72) stays outside.
VANCOUVER_WA_METRO_BBOX: dict[str, float] = {
    "min_lat": 45.56,
    "max_lat": 45.74,
    "min_lng": -122.81,
    "max_lng": -122.41,
}

# 6 Vancouver divisions. Hand-authored from the city's official Neighborhood
# Associations polygon layer (NeighborhoodsCoV) centroids; borough resolution
# at ingest comes from coordinates via get_division_for_coordinate, so bboxes
# need only be sane and contain their own submarket centers.
VANCOUVER_WA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_CORE": {
        "min_lat": 45.620,
        "max_lat": 45.652,
        "min_lng": -122.700,
        "max_lng": -122.640,
    },
    "FRUIT_VALLEY_NORTHWEST": {
        "min_lat": 45.648,
        "max_lat": 45.690,
        "min_lng": -122.745,
        "max_lng": -122.640,
    },
    "CENTRAL_VANCOUVER": {
        "min_lat": 45.615,
        "max_lat": 45.655,
        "min_lng": -122.655,
        "max_lng": -122.585,
    },
    "BURNT_BRIDGE_NORTH": {
        "min_lat": 45.615,
        "max_lat": 45.695,
        "min_lng": -122.610,
        "max_lng": -122.500,
    },
    "CASCADE_EASTSIDE": {
        "min_lat": 45.595,
        "max_lat": 45.650,
        "min_lng": -122.560,
        "max_lng": -122.480,
    },
    "FISHERS_LANDING_SE": {
        "min_lat": 45.585,
        "max_lat": 45.625,
        "min_lng": -122.535,
        "max_lng": -122.470,
    },
}


def is_in_vancouver_wa_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Vancouver WA city bounds."""
    if lat is None or lng is None:
        return False
    return (
        VANCOUVER_WA_METRO_BBOX["min_lat"] <= lat <= VANCOUVER_WA_METRO_BBOX["max_lat"]
        and VANCOUVER_WA_METRO_BBOX["min_lng"] <= lng <= VANCOUVER_WA_METRO_BBOX["max_lng"]
    )


is_in_greater_vancouver_wa_metro = is_in_vancouver_wa_metro


VANCOUVER_WA_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (2)
    # =======================================================================
    "Downtown / Esther Short": SubmarketMeta(
        name="Downtown / Esther Short",
        borough="DOWNTOWN_CORE",
        lat=45.6282,
        lng=-122.6785,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.87,
        capex=6800000.0,
        permit_vel=30.0,
        shift_ratio=1.45,
        sla=53.0,
        description="Esther Short Park and the Columbia River waterfront core with the convention center, the Waterfront Vancouver redevelopment, and the downtown Main Street retail spine.",
        city_id="vancouver_wa",
    ),
    "Uptown Village": SubmarketMeta(
        name="Uptown Village",
        borough="DOWNTOWN_CORE",
        lat=45.6325,
        lng=-122.6715,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.85,
        capex=6100000.0,
        permit_vel=27.0,
        shift_ratio=1.43,
        sla=51.0,
        description="Main Street's historic north stretch above Esther Short with walkable shopfronts, taverns, and mixed-use infill between downtown and the Hough neighborhood.",
        city_id="vancouver_wa",
    ),
    # =======================================================================
    # FRUIT_VALLEY_NORTHWEST (3)
    # =======================================================================
    "Fruit Valley": SubmarketMeta(
        name="Fruit Valley",
        borough="FRUIT_VALLEY_NORTHWEST",
        lat=45.6667,
        lng=-122.7211,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.83,
        capex=5400000.0,
        permit_vel=22.0,
        shift_ratio=1.40,
        sla=49.0,
        description="Northwest industrial-flavored corridor along NW Fruit Valley Road with rail-adjacent warehouses, tract housing, and the western gateway to the Burnt Bridge Creek trail.",
        city_id="vancouver_wa",
    ),
    "Northwest Vancouver": SubmarketMeta(
        name="Northwest Vancouver",
        borough="FRUIT_VALLEY_NORTHWEST",
        lat=45.6665,
        lng=-122.6790,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=5200000.0,
        permit_vel=21.0,
        shift_ratio=1.39,
        sla=48.0,
        description="Established postwar single-family quadrant between NW 78th Street and the Fruit Valley road, steady remodel and addition permitting.",
        city_id="vancouver_wa",
    ),
    "West Minnehaha": SubmarketMeta(
        name="West Minnehaha",
        borough="FRUIT_VALLEY_NORTHWEST",
        lat=45.6589,
        lng=-122.6512,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.84,
        capex=5600000.0,
        permit_vel=24.0,
        shift_ratio=1.42,
        sla=50.0,
        description="Minnehaha Street west-of-I-5 corridor with mid-century bungalows, small multifamily, and light commercial nodes along the state highway.",
        city_id="vancouver_wa",
    ),
    # =======================================================================
    # CENTRAL_VANCOUVER (2)
    # =======================================================================
    "Fourth Plain / Bagley Downs": SubmarketMeta(
        name="Fourth Plain / Bagley Downs",
        borough="CENTRAL_VANCOUVER",
        lat=45.6454,
        lng=-122.6210,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=6300000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=52.0,
        description="Fourth Plain Boulevard's diverse retail corridor and Bagley Downs residential grid — the metro's densest row of small-business permits and multicultural storefronts.",
        city_id="vancouver_wa",
    ),
    "Maplewood": SubmarketMeta(
        name="Maplewood",
        borough="CENTRAL_VANCOUVER",
        lat=45.6341,
        lng=-122.6337,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.84,
        capex=5700000.0,
        permit_vel=25.0,
        shift_ratio=1.41,
        sla=50.0,
        description="Central post-war neighborhood between Fourth Plain and Mill Plain with bungalow turnover, duplex conversions, and the NE Andresen mixed-use strip.",
        city_id="vancouver_wa",
    ),
    # =======================================================================
    # BURNT_BRIDGE_NORTH (2)
    # =======================================================================
    "Walnut Grove": SubmarketMeta(
        name="Walnut Grove",
        borough="BURNT_BRIDGE_NORTH",
        lat=45.6644,
        lng=-122.5917,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=5800000.0,
        permit_vel=23.0,
        shift_ratio=1.39,
        sla=48.0,
        description="Northern residential belt along NE 63rd Street between I-5 and NE 112th with ranch homes, green-lot infill, and new-build subdivisions.",
        city_id="vancouver_wa",
    ),
    "Burnt Bridge Creek / Image": SubmarketMeta(
        name="Burnt Bridge Creek / Image",
        borough="BURNT_BRIDGE_NORTH",
        lat=45.6560,
        lng=-122.5206,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.83,
        capex=6500000.0,
        permit_vel=26.0,
        shift_ratio=1.43,
        sla=51.0,
        description="Burnt Bridge Creek greenbelt neighborhoods and the Image corridor with creek-adjacent redevelopment, trail access, and steady infill permitting.",
        city_id="vancouver_wa",
    ),
    # =======================================================================
    # CASCADE_EASTSIDE (2)
    # =======================================================================
    "Cascade Park / First Place": SubmarketMeta(
        name="Cascade Park / First Place",
        borough="CASCADE_EASTSIDE",
        lat=45.6323,
        lng=-122.5205,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.88,
        capex=7400000.0,
        permit_vel=31.0,
        shift_ratio=1.50,
        sla=55.0,
        description="Cascade Park retail core and First Place's master-planned subdivisions — the metro's highest-volume new-home permitting belt east of I-205.",
        city_id="vancouver_wa",
    ),
    "East Mill Plain": SubmarketMeta(
        name="East Mill Plain",
        borough="CASCADE_EASTSIDE",
        lat=45.6205,
        lng=-122.5117,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.85,
        capex=7000000.0,
        permit_vel=29.0,
        shift_ratio=1.47,
        sla=53.0,
        description="East Mill Plain Boulevard corridor with big-box retail, garden apartments, and the SE 164th Avenue growth node at the city's east edge.",
        city_id="vancouver_wa",
    ),
    # =======================================================================
    # FISHERS_LANDING_SE (2)
    # =======================================================================
    "Fisher's Landing": SubmarketMeta(
        name="Fisher's Landing",
        borough="FISHERS_LANDING_SE",
        lat=45.6041,
        lng=-122.4900,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.86,
        capex=6900000.0,
        permit_vel=28.0,
        shift_ratio=1.46,
        sla=52.0,
        description="SE 164th/Fisher's Landing East office-retail node with newer multifamily, medical campus employment, and Columbia River-adjacent high-value permits.",
        city_id="vancouver_wa",
    ),
    "Columbia River / Northfield": SubmarketMeta(
        name="Columbia River / Northfield",
        borough="FISHERS_LANDING_SE",
        lat=45.5888,
        lng=-122.5004,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=6200000.0,
        permit_vel=24.0,
        shift_ratio=1.41,
        sla=49.0,
        description="Riverfront southern edge along SE Columbia River Way with townhome infill, marina-adjacent development, and view-lot turnover.",
        city_id="vancouver_wa",
    ),
}


VANCOUVER_WA_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=45.6282,
        center_lng=-122.6785,
        zoom=14.0,
        bbox=VANCOUVER_WA_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in VANCOUVER_WA_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="vancouver_wa",
    ),
    "FRUIT_VALLEY_NORTHWEST": BoroughMeta(
        name="FRUIT_VALLEY_NORTHWEST",
        center_lat=45.6667,
        center_lng=-122.7211,
        zoom=13.0,
        bbox=VANCOUVER_WA_DIVISION_BBOXES["FRUIT_VALLEY_NORTHWEST"],
        submarkets=[k for k, v in VANCOUVER_WA_SUBMARKETS.items() if v.borough == "FRUIT_VALLEY_NORTHWEST"],
        city_id="vancouver_wa",
    ),
    "CENTRAL_VANCOUVER": BoroughMeta(
        name="CENTRAL_VANCOUVER",
        center_lat=45.6454,
        center_lng=-122.6210,
        zoom=13.5,
        bbox=VANCOUVER_WA_DIVISION_BBOXES["CENTRAL_VANCOUVER"],
        submarkets=[k for k, v in VANCOUVER_WA_SUBMARKETS.items() if v.borough == "CENTRAL_VANCOUVER"],
        city_id="vancouver_wa",
    ),
    "BURNT_BRIDGE_NORTH": BoroughMeta(
        name="BURNT_BRIDGE_NORTH",
        center_lat=45.6560,
        center_lng=-122.5917,
        zoom=13.0,
        bbox=VANCOUVER_WA_DIVISION_BBOXES["BURNT_BRIDGE_NORTH"],
        submarkets=[k for k, v in VANCOUVER_WA_SUBMARKETS.items() if v.borough == "BURNT_BRIDGE_NORTH"],
        city_id="vancouver_wa",
    ),
    "CASCADE_EASTSIDE": BoroughMeta(
        name="CASCADE_EASTSIDE",
        center_lat=45.6205,
        center_lng=-122.5117,
        zoom=13.0,
        bbox=VANCOUVER_WA_DIVISION_BBOXES["CASCADE_EASTSIDE"],
        submarkets=[k for k, v in VANCOUVER_WA_SUBMARKETS.items() if v.borough == "CASCADE_EASTSIDE"],
        city_id="vancouver_wa",
    ),
    "FISHERS_LANDING_SE": BoroughMeta(
        name="FISHERS_LANDING_SE",
        center_lat=45.6041,
        center_lng=-122.4900,
        zoom=13.0,
        bbox=VANCOUVER_WA_DIVISION_BBOXES["FISHERS_LANDING_SE"],
        submarkets=[k for k, v in VANCOUVER_WA_SUBMARKETS.items() if v.borough == "FISHERS_LANDING_SE"],
        city_id="vancouver_wa",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed live 2026-08-28 against the city's AGOL org (CityOfVancouverGISAdmin,
# services.arcgis.com/oNvpY90qsPDizwkN). Do not register 311 (token-gated
# internal server), SLA (no public feed), or deeds (Clark Co. web app).
# ---------------------------------------------------------------------------
VANCOUVER_WA_PERMITS_ENDPOINT = (
    "https://services.arcgis.com/oNvpY90qsPDizwkN/arcgis/rest/services/"
    "Permits_and_Code_Enforcement_Data_(public_view)/FeatureServer/0"
)

# Future-dated csm_issued_date rows are sentinels (2 live, max 2049-10-31,
# both Closed/ELECTRICAL): exclude them at the source so neither the high
# watermark nor staleness math sees them. Verified live on the host; the host
# also accepts ISO string comparisons (NOT an ANSI_DATE_LITERAL_HOSTS member).
VANCOUVER_WA_PERMITS_WHERE = "csm_issued_date <= CURRENT_TIMESTAMP"

VANCOUVER_WA_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": VANCOUVER_WA_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "csm_issued_date",
        "id_keys": ["CSM_CASENO", "sn", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": VANCOUVER_WA_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "csm_issued_date DESC",
            "where": VANCOUVER_WA_PERMITS_WHERE,
            "scope": (
                "Permits_and_Code_Enforcement_Data public view (FeatureServer/0 "
                "'Permit Data') on the City of Vancouver WA AGOL org — daily, "
                "44,744 rows live (90d=2,812; since 2026-01-01=8,010; newest "
                "2026-08-15T08:16:03Z). Native outSR=4326 point geometry "
                "primary (Y/X attributes are WA State Plane South feet, never "
                "mapped); csm_issued_date where-queryable with ISO strings "
                "(not ANSI-only); two future sentinels (2039-05-19, "
                "2049-10-31, both Closed/ELECTRICAL) excluded by the "
                "csm_issued_date<=CURRENT_TIMESTAMP where guard + scheduler "
                "US-111 future guard; PRIM_ADDR address fallback (0 nulls) "
                "via ADR-0004 geocode context 'Vancouver, WA'; CSM_STATUS "
                "Open/Closed; worktype + cst_description classify; no "
                "site-zip/parcel/neighborhood columns, so zipcode/bbl/"
                "borough stay undeclared."
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
}


def get_vancouver_wa_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Vancouver WA feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in VANCOUVER_WA_FEED_SPECS:
        available = ", ".join(sorted(VANCOUVER_WA_FEED_SPECS))
        raise KeyError(
            f"'{VANCOUVER_WA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = VANCOUVER_WA_FEED_SPECS[feed_name]
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
    metro_bbox=VANCOUVER_WA_METRO_BBOX,
    division_bboxes=VANCOUVER_WA_DIVISION_BBOXES,
    submarkets=VANCOUVER_WA_SUBMARKETS,
    divisions=VANCOUVER_WA_DIVISIONS,
    contains=is_in_vancouver_wa_metro,
)

__all__ = [
    "REGISTRATION",
    "VANCOUVER_WA_CITY_ID",
    "VANCOUVER_WA_DIVISIONS",
    "VANCOUVER_WA_DIVISION_BBOXES",
    "VANCOUVER_WA_FEED_SPECS",
    "VANCOUVER_WA_GEOCODE_CONTEXT",
    "VANCOUVER_WA_METRO_BBOX",
    "VANCOUVER_WA_PERMITS_ENDPOINT",
    "VANCOUVER_WA_PERMITS_WHERE",
    "VANCOUVER_WA_SUBMARKETS",
    "get_vancouver_wa_dataset",
    "is_in_greater_vancouver_wa_metro",
    "is_in_vancouver_wa_metro",
]