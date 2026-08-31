SLA_FIELD_MAP = {
    "license_id": ["FileNumber", "OBJECTID"],
    "dba": ["PremiseName"],
    "premises_name": ["OwnerName"],
    "license_type": ["LicenseType", "LicenseCode"],
    "status": ["Status"],
    "effective_date": ["OriginalIssueDate"],
    "expiration_date": ["ExpirationDate"],
    "address_street": ["PremiseAddress", "PremiseAddress2"],
}

FIELD_MAP = {
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT = "Stockton, CA"

DROPPED_MAIL_COLUMNS = (
    "MailAddress",
    "MailAddress2",
    "MailCity",
    "MailState",
    "MailZipcode",
    "PremiseZipcode",
    "PremiseCensusTract",
    "Shape",
)

"""Stockton, CA spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Stockton
(San Joaquin County, CA).

Stockton is a ONE-FEED PARTIAL metro like Tucson: SLA only — the city's
liquor-license layer (``OpenCounter/OpenCounterMap/MapServer/7``, Tier 2,
1,363 rows) on the city's own ArcGIS Server. PERMITS, COMPLAINTS_311, and
DEEDS are Tier 3 and stay unregistered: the Accela, CityWorks, Comcate,
Forerunner, BuildingBlocks, Peregrine, and SpatialWave service folders on
``gisportal.stocktonca.gov`` all answer ``{"error":{"code":499,"message":
"Token Required"}}`` (permits / work orders / 311 systems of record are
token-secured), San Joaquin County's GIS (sjmap.org, v10.05) exposes only
Locators/PublicWorks with an empty GoRequest folder, and no county
recorder/deed bulk surface exists.

Live-probe caveats that define this leaf (probed 2026-08-28, US-230):

* The ticket's claimed source ``stocktonca.opendata.arcgis.com`` is a dead
  Hub-v2 shell (every ``/api/*`` route 404s), and ``data.stocktonca.gov``
  is a misconfigured Socrata domain serving the NATIONAL catalog (Dallas
  Police Active Calls et al.; zero own datasets). Neither is evidence of a
  feed. The real official surface is the city ArcGIS Server
  ``gisportal.stocktonca.gov/arcgis2`` (v11.3, valid TLS).
* SLA row count is **1,363 live** (ACTIVE 1,241 / PEND 84 / SUREND 35 /
  R64B 2 / REVPEN 1). ``OriginalIssueDate`` is the watermark
  (esriFieldTypeDate, epoch-ms → ISO on flatten); newest = **2026-07-14**
  (1783987200000), oldest 1953. No future-dated sentinels — no ``where``
  guard is needed. 61 rows carry 2026 issue dates; ExpirationDate rides
  the ABC license-year edge (all newest rows expire 2027-06-30).
* ``LicenseType`` is the raw CA-ABC type code as a string ("20" off-sale
  beer/wine 265 rows, "21" off-sale general 260, "41" on-sale beer/wine
  240, "47" on-sale general 214, "2" winegrower 73, ...). Finer
  classification is analytics-side.
* **Mixed-CRS trap (Aurora/Tucson discipline)**: the layer's store SR is
  **WKID 102643 / latest 2227 — NAD83 California Zone 3, US survey feet**
  — but unlike Aurora there are NO X/Y attribute columns on the layer.
  Coordinates come ONLY from the ``outSR=4326`` geometry lift that
  ``ArcGISClient`` flattens onto ``latitude``/``longitude``; the map
  declares no latitude/longitude candidates. ``state_plane_crs``/
  ``state_plane_units`` are declared spec-side for spine tooling, with no
  x/y columns (nothing to transform — every row carries native geometry:
  ``Shape IS NULL`` count = 0/1,363).
* **Mailing-zip trap**: ``PremiseZipcode`` carries MAILING zip values, not
  premise zips (e.g. the newest row sits at 950 W 11th St, Stockton with
  PremiseZipcode "95376" and MailCity "TRACY"). It stays unmapped and is
  never used for geography; the zips ride ``Mail*`` columns which are
  dropped as mailing-block fields.
* ``PremiseName`` (trade name) is often a single space; ``OwnerName`` (the
  license holder) is consistently populated — dba keeps the source bytes
  byte-verbatim (" "), premises_name maps to the owner.
* County-wide premises ride the layer (Lodi/Manteca/Tracy license files
  appear); metro bbox containment gates ingestion to the Stockton urban
  area while the live extent spans 37.8536–38.1169 N, 121.5303–121.1465 W.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

STOCKTON_CITY_ID: str = "stockton"
STOCKTON_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Store SR of the liquor layer (WKID 102643 / latestWkid 2227): NAD83
# California Zone 3, US survey feet. No attribute coordinate columns exist
# on the layer — this declaration documents the store CRS for spine
# tooling; the only coordinate path is the outSR=4326 geometry lift.
STOCKTON_STATE_PLANE_CRS: str = "EPSG:2227"
STOCKTON_STATE_PLANE_UNITS: str = "ftUS"

# City of Stockton urban area plus its immediate San Joaquin fringe
# (Lathrop/French Camp edge, west port belt, north Lower Sacramento Rd
# corridor). Permissive enough to hold downtown (37.9577, -121.2900), the
# Miracle Mile (37.9666, -121.3190), Spanos Park (37.9330, -121.3130),
# Weston Ranch (37.9250, -121.2820), the north winery corridor
# (38.0775, -121.3104), and the deep-west industrial belt — while
# rejecting Tracy (37.74), Manteca (37.80), Lodi (38.13), and
# Sacramento (38.58).
STOCKTON_METRO_BBOX: dict[str, float] = {
    "min_lat": 37.85,
    "max_lat": 38.10,
    "min_lng": -121.44,
    "max_lng": -121.16,
}

# 7 Stockton divisions. Hand-authored; borough resolution at ingest comes
# from coordinates via get_division_for_coordinate, so bboxes need only be
# sane, mutually non-overlapping, and contain their own submarket centers.
STOCKTON_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_WATERFRONT": {
        "min_lat": 37.944,
        "max_lat": 37.970,
        "min_lng": -121.310,
        "max_lng": -121.278,
    },
    "MIDTOWN_MIRACLE_MILE": {
        "min_lat": 37.956,
        "max_lat": 37.990,
        "min_lng": -121.335,
        "max_lng": -121.310,
    },
    "NORTH_LINCOLN_VILLAGE": {
        "min_lat": 37.962,
        "max_lat": 38.005,
        "min_lng": -121.278,
        "max_lng": -121.205,
    },
    "WEST_BROOKSIDE": {
        "min_lat": 37.950,
        "max_lat": 37.970,
        "min_lng": -121.368,
        "max_lng": -121.335,
    },
    "SOUTHWEST_SPANOS": {
        "min_lat": 37.900,
        "max_lat": 37.950,
        "min_lng": -121.368,
        "max_lng": -121.305,
    },
    "SOUTH_CENTRAL": {
        "min_lat": 37.895,
        "max_lat": 37.944,
        "min_lng": -121.305,
        "max_lng": -121.285,
    },
    "SOUTHEAST_WESTON": {
        "min_lat": 37.895,
        "max_lat": 37.955,
        "min_lng": -121.285,
        "max_lng": -121.205,
    },
}


def is_in_stockton_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Stockton metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        STOCKTON_METRO_BBOX["min_lat"] <= lat <= STOCKTON_METRO_BBOX["max_lat"]
        and STOCKTON_METRO_BBOX["min_lng"] <= lng <= STOCKTON_METRO_BBOX["max_lng"]
    )


is_in_greater_stockton_metro = is_in_stockton_metro


STOCKTON_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_WATERFRONT (2)
    # =======================================================================
    "Downtown Core": SubmarketMeta(
        name="Downtown Core",
        borough="DOWNTOWN_WATERFRONT",
        lat=37.9577,
        lng=-121.2900,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.84,
        capex=7800000.0,
        permit_vel=30.0,
        shift_ratio=1.48,
        sla=58.0,
        description=(
            "Civic-center and Hunter Square core with the arena-waterfront "
            "entertainment district, historic Mariclare and Medico-Dental "
            "building reuse, and adaptive-reuse permitting."
        ),
        city_id="stockton",
    ),
    "Banner Island & Waterfront": SubmarketMeta(
        name="Banner Island & Waterfront",
        borough="DOWNTOWN_WATERFRONT",
        lat=37.9535,
        lng=-121.3010,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.80,
        capex=6400000.0,
        permit_vel=24.0,
        shift_ratio=1.42,
        sla=52.0,
        description=(
            "Banner Island ballpark district and the Weber Point "
            "waterfront promenade with stadium-adjacent hospitality "
            "licensing and event-economy turnover."
        ),
        city_id="stockton",
    ),
    # =======================================================================
    # MIDTOWN_MIRACLE_MILE (2)
    # =======================================================================
    "Miracle Mile": SubmarketMeta(
        name="Miracle Mile",
        borough="MIDTOWN_MIRACLE_MILE",
        lat=37.9666,
        lng=-121.3190,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=7200000.0,
        permit_vel=28.0,
        shift_ratio=1.50,
        sla=62.0,
        description=(
            "Pacific Avenue's Miracle Mile with independent restaurants "
            "and taprooms, the Fox/Bob Hope theatre block, and the "
            "metro's densest on-sale license strip."
        ),
        city_id="stockton",
    ),
    "University of the Pacific": SubmarketMeta(
        name="University of the Pacific",
        borough="MIDTOWN_MIRACLE_MILE",
        lat=37.9802,
        lng=-121.3122,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=25.0,
        shift_ratio=1.46,
        sla=55.0,
        description=(
            "UOP campus and Lincoln Center shopping belt with "
            "student-housing turnover, medical-office demand, and "
            "steady neighborhood-retail licensing."
        ),
        city_id="stockton",
    ),
    # =======================================================================
    # NORTH_LINCOLN_VILLAGE (2)
    # =======================================================================
    "Lincoln Village & Park Nine": SubmarketMeta(
        name="Lincoln Village & Park Nine",
        borough="NORTH_LINCOLN_VILLAGE",
        lat=37.9740,
        lng=-121.2755,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=4800000.0,
        permit_vel=22.0,
        shift_ratio=1.36,
        sla=44.0,
        description=(
            "Post-war Lincoln Village tracts east of the El Dorado "
            "corridor with renovation-led permitting and "
            "neighborhood-market license churn."
        ),
        city_id="stockton",
    ),
    "Eastland Plaza": SubmarketMeta(
        name="Eastland Plaza",
        borough="NORTH_LINCOLN_VILLAGE",
        lat=37.9650,
        lng=-121.2740,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=4400000.0,
        permit_vel=20.0,
        shift_ratio=1.34,
        sla=42.0,
        description=(
            "Eastland Plaza and East Harding Way retail node with "
            "family-market grocers, strip-lot refurbishment, and "
            "off-sale license turnover."
        ),
        city_id="stockton",
    ),
    # =======================================================================
    # WEST_BROOKSIDE (2)
    # =======================================================================
    "Brookside": SubmarketMeta(
        name="Brookside",
        borough="WEST_BROOKSIDE",
        lat=37.9505,
        lng=-121.3420,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.88,
        capex=8400000.0,
        permit_vel=26.0,
        shift_ratio=1.52,
        sla=60.0,
        description=(
            "Brookside planned community west of I-5 with "
            "office-park retrofit, Trinity Parkway retail pads, and "
            "high-valuation residential permitting."
        ),
        city_id="stockton",
    ),
    "West Lane & Country Club": SubmarketMeta(
        name="West Lane & Country Club",
        borough="WEST_BROOKSIDE",
        lat=37.9620,
        lng=-121.3430,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5200000.0,
        permit_vel=22.0,
        shift_ratio=1.38,
        sla=48.0,
        description=(
            "Country Club Boulevard commercial spine with the golf-course "
            "anchor, westside strip retail, and steady"
            " service-business licensing."
        ),
        city_id="stockton",
    ),
    # =======================================================================
    # SOUTHWEST_SPANOS (2)
    # =======================================================================
    "Quail Lakes & Heritage": SubmarketMeta(
        name="Quail Lakes & Heritage",
        borough="SOUTHWEST_SPANOS",
        lat=37.9455,
        lng=-121.3290,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.84,
        capex=7000000.0,
        permit_vel=24.0,
        shift_ratio=1.47,
        sla=56.0,
        description=(
            "Quail Lakes shopping district and the Heritage planned "
            "community with pool/roof permitting and "
            "family-restaurant licensing."
        ),
        city_id="stockton",
    ),
    "Spanos Park": SubmarketMeta(
        name="Spanos Park",
        borough="SOUTHWEST_SPANOS",
        lat=37.9330,
        lng=-121.3130,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.86,
        capex=7600000.0,
        permit_vel=23.0,
        shift_ratio=1.49,
        sla=54.0,
        description=(
            "Spanos Park residential-golf community along West Eight "
            "Mile Road with new-build tract permitting and "
            "clubhouse-adjacent hospitality."
        ),
        city_id="stockton",
    ),
    # =======================================================================
    # SOUTH_CENTRAL (2)
    # =======================================================================
    "South Stockton & Fairgrounds": SubmarketMeta(
        name="South Stockton & Fairgrounds",
        borough="SOUTH_CENTRAL",
        lat=37.9370,
        lng=-121.2890,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.72,
        capex=4600000.0,
        permit_vel=21.0,
        shift_ratio=1.40,
        sla=46.0,
        description=(
            "San Joaquin County Fairgrounds district and the California "
            "Street corridor with community-reinvestment permits and "
            "neighborhood-market licensing."
        ),
        city_id="stockton",
    ),
    "El Dorado & South Central": SubmarketMeta(
        name="El Dorado & South Central",
        borough="SOUTH_CENTRAL",
        lat=37.9180,
        lng=-121.2965,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.70,
        capex=4200000.0,
        permit_vel=19.0,
        shift_ratio=1.36,
        sla=40.0,
        description=(
            "South El Dorado Street spine with taquerias and markets, "
            "Wilson Elementary-area infill, and steady "
            "small-operator license turnover."
        ),
        city_id="stockton",
    ),
    # =======================================================================
    # SOUTHEAST_WESTON (2)
    # =======================================================================
    "Weston Ranch": SubmarketMeta(
        name="Weston Ranch",
        borough="SOUTHEAST_WESTON",
        lat=37.9250,
        lng=-121.2820,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=23.0,
        shift_ratio=1.44,
        sla=43.0,
        description=(
            "Master-planned Weston Ranch along Manthey Road with "
            "builder-driven new-construction permitting and "
            "neighborhood retail pads."
        ),
        city_id="stockton",
    ),
    "Airport & Arch Road Industrial": SubmarketMeta(
        name="Airport & Arch Road Industrial",
        borough="SOUTHEAST_WESTON",
        lat=37.9020,
        lng=-121.2580,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.68,
        capex=5000000.0,
        permit_vel=20.0,
        shift_ratio=1.32,
        sla=38.0,
        description=(
            "Stockton Metropolitan Airport and Arch Airport industrial "
            "belt with logistics-warehouse permits and "
            "cannabis-license adjacency to the southeast."
        ),
        city_id="stockton",
    ),
}


STOCKTON_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_WATERFRONT": BoroughMeta(
        name="DOWNTOWN_WATERFRONT",
        center_lat=37.957,
        center_lng=-121.294,
        zoom=14.0,
        bbox=STOCKTON_DIVISION_BBOXES["DOWNTOWN_WATERFRONT"],
        submarkets=[k for k, v in STOCKTON_SUBMARKETS.items() if v.borough == "DOWNTOWN_WATERFRONT"],
        city_id="stockton",
    ),
    "MIDTOWN_MIRACLE_MILE": BoroughMeta(
        name="MIDTOWN_MIRACLE_MILE",
        center_lat=37.973,
        center_lng=-121.322,
        zoom=14.0,
        bbox=STOCKTON_DIVISION_BBOXES["MIDTOWN_MIRACLE_MILE"],
        submarkets=[k for k, v in STOCKTON_SUBMARKETS.items() if v.borough == "MIDTOWN_MIRACLE_MILE"],
        city_id="stockton",
    ),
    "NORTH_LINCOLN_VILLAGE": BoroughMeta(
        name="NORTH_LINCOLN_VILLAGE",
        center_lat=37.983,
        center_lng=-121.240,
        zoom=13.0,
        bbox=STOCKTON_DIVISION_BBOXES["NORTH_LINCOLN_VILLAGE"],
        submarkets=[k for k, v in STOCKTON_SUBMARKETS.items() if v.borough == "NORTH_LINCOLN_VILLAGE"],
        city_id="stockton",
    ),
    "WEST_BROOKSIDE": BoroughMeta(
        name="WEST_BROOKSIDE",
        center_lat=37.960,
        center_lng=-121.351,
        zoom=13.5,
        bbox=STOCKTON_DIVISION_BBOXES["WEST_BROOKSIDE"],
        submarkets=[k for k, v in STOCKTON_SUBMARKETS.items() if v.borough == "WEST_BROOKSIDE"],
        city_id="stockton",
    ),
    "SOUTHWEST_SPANOS": BoroughMeta(
        name="SOUTHWEST_SPANOS",
        center_lat=37.925,
        center_lng=-121.336,
        zoom=13.0,
        bbox=STOCKTON_DIVISION_BBOXES["SOUTHWEST_SPANOS"],
        submarkets=[k for k, v in STOCKTON_SUBMARKETS.items() if v.borough == "SOUTHWEST_SPANOS"],
        city_id="stockton",
    ),
    "SOUTH_CENTRAL": BoroughMeta(
        name="SOUTH_CENTRAL",
        center_lat=37.920,
        center_lng=-121.300,
        zoom=13.5,
        bbox=STOCKTON_DIVISION_BBOXES["SOUTH_CENTRAL"],
        submarkets=[k for k, v in STOCKTON_SUBMARKETS.items() if v.borough == "SOUTH_CENTRAL"],
        city_id="stockton",
    ),
    "SOUTHEAST_WESTON": BoroughMeta(
        name="SOUTHEAST_WESTON",
        center_lat=37.925,
        center_lng=-121.250,
        zoom=13.0,
        bbox=STOCKTON_DIVISION_BBOXES["SOUTHEAST_WESTON"],
        submarkets=[k for k, v in STOCKTON_SUBMARKETS.items() if v.borough == "SOUTHEAST_WESTON"],
        city_id="stockton",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28 (US-230). Do NOT register permits, 311, or deeds: the
# Accela/CityWorks/Comcate/Forerunner folders answer 499 Token Required and
# San Joaquin County publishes no recorder/deed bulk surface. The OpenCounter
# basemap layers (parcels/zoning/districts) are reference-only, not feeds.
# ---------------------------------------------------------------------------
STOCKTON_SLA_ENDPOINT = (
    "https://gisportal.stocktonca.gov/arcgis2/rest/services/"
    "OpenCounter/OpenCounterMap/MapServer/7"
)

# No future-dated sentinels at probe (newest OriginalIssueDate 2026-07-14
# against a 2026-08-28 probe date) — no where guard, unlike Tucson.
STOCKTON_SLA_ALARM_EXEMPT_REASON = (
    "current-license snapshot republished by the city GIS team: the "
    "watermark is the ABC original issue date, not the republication "
    "timestamp, and premise issuance runs ~1/week (61 rows dated 2026); "
    "an alarm on issue-date freshness would false-positive on the "
    "publication lag"
)

STOCKTON_FEED_SPECS: dict[str, dict[str, object]] = {
    "sla": {
        "endpoint": STOCKTON_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "OriginalIssueDate",
        "id_keys": ["FileNumber", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "alarm_exempt": True,
            "alarm_exempt_reason": STOCKTON_SLA_ALARM_EXEMPT_REASON,
            "ingestion_mode": "snapshot",
            "needs_geocode": True,
            "geocode_context": STOCKTON_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "OriginalIssueDate DESC",
            "state_plane_crs": STOCKTON_STATE_PLANE_CRS,
            "state_plane_units": STOCKTON_STATE_PLANE_UNITS,
            "scope": (
                "liquor licenses (ABC premises; 1,363 rows; store SR WKID "
                "2227 CA-Zone-3 ftUS with NO X/Y attribute columns - coords "
                "only via outSR=4326 geometry lift, 0 null geometries at "
                "probe; PremiseZipcode carries MAILING zips and is never "
                "geographic; county-wide premises gated by metro bbox; "
                "permits/311 token-secured 499, deeds unregistered)"
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_stockton_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Stockton feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in STOCKTON_FEED_SPECS:
        available = ", ".join(sorted(STOCKTON_FEED_SPECS))
        raise KeyError(
            f"'{STOCKTON_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = STOCKTON_FEED_SPECS[feed_name]
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
    metro_bbox=STOCKTON_METRO_BBOX,
    division_bboxes=STOCKTON_DIVISION_BBOXES,
    submarkets=STOCKTON_SUBMARKETS,
    divisions=STOCKTON_DIVISIONS,
    contains=is_in_stockton_metro,
)

__all__ = [
    "DROPPED_MAIL_COLUMNS",
    "GEOCODE_CONTEXT",
    "REGISTRATION",
    "SLA_FIELD_MAP",
    "STOCKTON_CITY_ID",
    "STOCKTON_DIVISIONS",
    "STOCKTON_DIVISION_BBOXES",
    "STOCKTON_FEED_SPECS",
    "STOCKTON_GEOCODE_CONTEXT",
    "STOCKTON_METRO_BBOX",
    "STOCKTON_SLA_ALARM_EXEMPT_REASON",
    "STOCKTON_SLA_ENDPOINT",
    "STOCKTON_STATE_PLANE_CRS",
    "STOCKTON_STATE_PLANE_UNITS",
    "STOCKTON_SUBMARKETS",
    "get_stockton_dataset",
    "is_in_greater_stockton_metro",
    "is_in_stockton_metro",
]
