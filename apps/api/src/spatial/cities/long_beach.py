SLA_FIELD_MAP = {
    "license_id": ["LICENSENO"],
    "dba": ["DBANAME"],
    "premises_name": ["DBANAME"],
    "license_type": ["LICCATDESC", "CLASSDESC"],
    "status": ["LICSTATUS"],
    "effective_date": ["ISSDTTM"],
    "expiration_date": ["INACTVDTTM"],
    "address_street": ["SITELOCATION"],
    "zipcode": ["ZIP"],
    "borough": ["COUNCIL_NUMBER"],
}

CRIME_FIELD_MAP = {
    "incident_id": ["DR", "OBJECTID"],
    "offense_type": ["CrimeType", "Category", "Type"],
    "reported_date": ["ReportedDateTimeDate"],
    "borough": ["Division"],
}

FIELD_MAP = {
    "sla": SLA_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT = "Long Beach, CA"

DROPPED_PII_COLUMNS = ("FULLNAME",)

DROPPED_NONADDRESS_COLUMNS = (
    "MILESTONE",
    "MILESTONE_SIMPLE",
    "BID_NAME",
    "BID_NAME_1",
    "BID_NAME_12",
    "TRACT",
    "CDBG",
    "PRINTPRODUCTTYPES",
    "ReportedDateTime",
    "Beat",
    "ReportingDistrict",
    "DaysOld",
    "DayOfWeek",
    "HourOfDay",
)

"""Long Beach, CA spatial registry and geometry.

Provides neighborhood metadata, camera positioning, division catalog, and
geographic bounding boxes for the City of Long Beach (Los Angeles County,
California — independent incorporated city, ~466K population).

Long Beach is a TWO-FEED PARTIAL metro: SLA (``BusinessLicenses_DailyUpdate``
on the city's hosted ArcGIS FeatureServer at ``services6.arcgis.com``
org ``yCArG7wGXGyWLqav``, Tier 1, daily) and CRIME (LBPD ``CrimeData``,
native coordinates — ADR-0004-satisfied). COMPLAINTS_311, PERMITS, and
DEEDS stay unregistered (see probe verdicts below).

Live-probe caveats that define this leaf (all probed live 2026-08-28 UTC):

* The ticket's portal hint is a DEAD DOMAIN — ``datalongbeach.opendatasoft.com``
  returns Huwise "This domain could not be found" (OpenDataSoft rebranded to
  Huwise; the tenant migrated). The official portal is now
  ``data.longbeach.gov`` (same ODS/Huwise platform, custom domain).
* SLA — ``Business_Licenses_Public_View/FeatureServer/0`` (layer name
  ``BusinessLicenses_DailyUpdate``, item 54d45ca9c4554062a02df49ec1ea2b2a):
  178,826 rows; watermark ``MILESTONEDATE`` newest verbatim ``1787817600000``
  = 2026-08-27T08:00:00+00:00 with 1,337 rows since 2026-08-20 (daily
  cadence). ``ISSDTTM`` is FUTURE-DATE SENTINEL-POISONED (max
  ``38886854400000`` = year 3202, min 1800) — mapped only as
  ``effective_date``, never the watermark. ``where="OUTSIDECITY='No'"``
  registers the in-city slice (133,946 of 178,826 rows; the 44,878
  outside-city contractor rows geocode off-map, x ≈ -138 / y ≈ 27).
  ANSI ``date '...'`` where-literals work on this host (Tucson's
  ``CURRENT_TIMESTAMP`` form is not needed — ``MILESTONEDATE`` max is
  already sane). ~0.1% null geometry (2/2000 sampled) resolves through
  the ADR-0004 geocode supplement on ``SITELOCATION`` with context
  "Long Beach, CA"; the junk-geocode tail is downstream metro-scoping's
  concern (H3SpatialIndexer has no bbox gate — Greenville/SNAP precedent).
* CRIME — ``Police_Crime_Mapping/FeatureServer/0`` (layer ``CrimeData``,
  item db3defed7a894a6088b98ec16b4b5dfa): 11,012 rows in a ~6-month
  rolling window (oldest 2026-02-18T08:44:07+00:00); watermark
  ``ReportedDateTimeDate`` newest verbatim ``1787106060000`` =
  2026-08-19T02:21:00+00:00 — a ~9-day publish lag on probe day, ~15
  rows/day batched. Native point geometry is clean WGS84 on every probed
  row, so the ADR-0004 crime gate (coordinates or address) is satisfied
  natively and ``needs_geocode`` stays false. ``Address`` is
  block-anonymized by LBPD and is not an event field.
* 311 — ``service-requests`` on ``data.longbeach.gov`` (OpenDataSoft/
  Huwise) is verified live (346,300 rows; ``createddate`` newest verbatim
  ``2026-08-28T17:50:01+00:00``, intraday-fresh; native ``geolocation``
  geo_point_2d) but is NOT registrable at leaf: the repo has no
  OpenDataSoft client, and the CSV export route is semicolon-delimited
  (CSVClient is comma dialect) and full-file per pull. Spine follow-up:
  an ODS client or a where-parameterized export path, then register.
* PERMITS — no live permit register exists publicly. The RHNA
  ``Bldg_Permits_5th_Cycle_RHNA_2020`` FeatureServer is a compliance
  aggregate and ``Development_Projects_(Public)`` is a 61-row planning
  snapshot (layer ``ProjectInfo_5_2026_Geocoded``) — both skipped
  (no-aggregates rule).
* DEEDS — LA County Recorder publishes no queryable open-data feed:
  ``data.lacounty.gov`` is HTML-reachable but its Socrata API endpoints
  404, and ``lavote.gov`` records services expose no API. Partial
  registration without deeds is accepted by the ticket.
* ``Cannabis_BusinessLicenses`` (six layers, 74-218 rows each) is a
  sub-slice of the general BL feed — skipped.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

LONG_BEACH_CITY_ID: str = "long_beach"
LONG_BEACH_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Long Beach (LA County, CA). Permissive enough to hold the Downtown
# Shoreline waterfront (33.7695, -118.1930), the Belmont Shore / Naples
# canals east edge, Cambodia Town on Anaheim Street, the Bixby Knolls and
# California Heights north corridors, Wrigley west of Long Beach Boulevard,
# and North Long Beach up to the 91 — plus the live fixture extremes
# (33.853, -118.194 on the north edge; 33.765, -118.149 on the east).
LONG_BEACH_METRO_BBOX: dict[str, float] = {
    "min_lat": 33.72,
    "max_lat": 33.885,
    "min_lng": -118.29,
    "max_lng": -118.05,
}

# 8 Long Beach divisions. Hand-authored; borough resolution at ingest comes
# from coordinates via get_division_for_coordinate, so bboxes need only be
# sane and contain their own submarket centers.
LONG_BEACH_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_SHORELINE": {
        "min_lat": 33.755,
        "max_lat": 33.785,
        "min_lng": -118.205,
        "max_lng": -118.185,
    },
    "BELMONT_SHORE": {
        "min_lat": 33.749,
        "max_lat": 33.774,
        "min_lng": -118.168,
        "max_lng": -118.138,
    },
    "NAPLES": {
        "min_lat": 33.749,
        "max_lat": 33.762,
        "min_lng": -118.178,
        "max_lng": -118.161,
    },
    "CAMBODIA_TOWN": {
        "min_lat": 33.775,
        "max_lat": 33.790,
        "min_lng": -118.185,
        "max_lng": -118.168,
    },
    "WRIGLEY": {
        "min_lat": 33.780,
        "max_lat": 33.808,
        "min_lng": -118.215,
        "max_lng": -118.195,
    },
    "BIXBY_KNOLLS": {
        "min_lat": 33.805,
        "max_lat": 33.835,
        "min_lng": -118.210,
        "max_lng": -118.175,
    },
    "CAL_HEIGHTS": {
        "min_lat": 33.805,
        "max_lat": 33.830,
        "min_lng": -118.175,
        "max_lng": -118.145,
    },
    "NORTH_LONG_BEACH": {
        "min_lat": 33.835,
        "max_lat": 33.885,
        "min_lng": -118.230,
        "max_lng": -118.150,
    },
}


def is_in_long_beach_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Long Beach city bounds."""
    if lat is None or lng is None:
        return False
    return (
        LONG_BEACH_METRO_BBOX["min_lat"] <= lat <= LONG_BEACH_METRO_BBOX["max_lat"]
        and LONG_BEACH_METRO_BBOX["min_lng"] <= lng <= LONG_BEACH_METRO_BBOX["max_lng"]
    )


is_in_greater_long_beach_metro = is_in_long_beach_metro


LONG_BEACH_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_SHORELINE (2)
    # =======================================================================
    "Downtown Shoreline": SubmarketMeta(
        name="Downtown Shoreline",
        borough="DOWNTOWN_SHORELINE",
        lat=33.7695,
        lng=-118.1930,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.86,
        capex=7200000.0,
        permit_vel=31.0,
        shift_ratio=1.48,
        sla=54.0,
        description="Waterfront core with Shoreline Village, the Pike outlets, and the convention-center hotel belt — the metro's densest mixed-use licensing corridor.",
        city_id="long_beach",
    ),
    "East Village": SubmarketMeta(
        name="East Village",
        borough="DOWNTOWN_SHORELINE",
        lat=33.7735,
        lng=-118.1885,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.84,
        capex=5900000.0,
        permit_vel=26.0,
        shift_ratio=1.43,
        sla=51.0,
        description="Arts-district edge of downtown with loft conversions, the East Village arts park, and adaptive-reuse storefront licensing along First Street.",
        city_id="long_beach",
    ),
    # =======================================================================
    # BELMONT_SHORE (2)
    # =======================================================================
    "Belmont Shore": SubmarketMeta(
        name="Belmont Shore",
        borough="BELMONT_SHORE",
        lat=33.7590,
        lng=-118.1525,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.89,
        capex=7600000.0,
        permit_vel=27.0,
        shift_ratio=1.50,
        sla=57.0,
        description="Second Street retail spine a block off the bay — the metro's strongest walkable shopfront corridor with steady restaurant and boutique turnover.",
        city_id="long_beach",
    ),
    "Belmont Heights": SubmarketMeta(
        name="Belmont Heights",
        borough="BELMONT_SHORE",
        lat=33.7625,
        lng=-118.1620,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.87,
        capex=6800000.0,
        permit_vel=24.0,
        shift_ratio=1.44,
        sla=53.0,
        description="Craftsman and Spanish-revival blocks between Broadway and 7th with high-valuation renovation permits and Fourth Street's antique row.",
        city_id="long_beach",
    ),
    # =======================================================================
    # NAPLES (1)
    # =======================================================================
    "Naples": SubmarketMeta(
        name="Naples",
        borough="NAPLES",
        lat=33.7560,
        lng=-118.1670,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.91,
        capex=8400000.0,
        permit_vel=18.0,
        shift_ratio=1.38,
        sla=49.0,
        description="Treasure Island and the Naples canals — premium waterfront homes with low velocity but the metro's highest per-permit valuations.",
        city_id="long_beach",
    ),
    # =======================================================================
    # CAMBODIA_TOWN (1)
    # =======================================================================
    "Cambodia Town": SubmarketMeta(
        name="Cambodia Town",
        borough="CAMBODIA_TOWN",
        lat=33.7810,
        lng=-118.1745,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.82,
        capex=4800000.0,
        permit_vel=22.0,
        shift_ratio=1.41,
        sla=46.0,
        description="Anaheim Street corridor between Junipero and Cherry — the officially designated Cambodian business district with small-plate restaurant turnover.",
        city_id="long_beach",
    ),
    # =======================================================================
    # WRIGLEY (1)
    # =======================================================================
    "Wrigley": SubmarketMeta(
        name="Wrigley",
        borough="WRIGLEY",
        lat=33.7920,
        lng=-118.2010,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.80,
        capex=5200000.0,
        permit_vel=23.0,
        shift_ratio=1.42,
        sla=47.0,
        description="Wrigley Village west of Long Beach Boulevard with 1920s bungalow stock, the innovative-starts school campus, and infill permitting along Pacific.",
        city_id="long_beach",
    ),
    # =======================================================================
    # BIXBY_KNOLLS (1)
    # =======================================================================
    "Bixby Knolls": SubmarketMeta(
        name="Bixby Knolls",
        borough="BIXBY_KNOLLS",
        lat=33.8195,
        lng=-118.1900,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=6400000.0,
        permit_vel=25.0,
        shift_ratio=1.45,
        sla=52.0,
        description="Atlantic Avenue corridor with mid-century retail, the Expo-line-adjacent freight villages, and steady commercial rehabilitation permits.",
        city_id="long_beach",
    ),
    # =======================================================================
    # CAL_HEIGHTS (1)
    # =======================================================================
    "California Heights": SubmarketMeta(
        name="California Heights",
        borough="CAL_HEIGHTS",
        lat=33.8155,
        lng=-118.1560,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.85,
        capex=6100000.0,
        permit_vel=24.0,
        shift_ratio=1.43,
        sla=50.0,
        description="Historic-district bungalow belt (California Heights/Cal Heights) with the metro's steadiest single-family renovation and duplex-conversion flow.",
        city_id="long_beach",
    ),
    # =======================================================================
    # NORTH_LONG_BEACH (1)
    # =======================================================================
    "North Long Beach": SubmarketMeta(
        name="North Long Beach",
        borough="NORTH_LONG_BEACH",
        lat=33.8530,
        lng=-118.1935,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.78,
        capex=5500000.0,
        permit_vel=26.0,
        shift_ratio=1.47,
        sla=45.0,
        description="Uptown corridor around Atlantic and Artesia with the Uptown Renaissance plan, ADU-heavy permitting, and the metro's fastest rent-shift slope.",
        city_id="long_beach",
    ),
}


LONG_BEACH_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_SHORELINE": BoroughMeta(
        name="DOWNTOWN_SHORELINE",
        center_lat=33.7695,
        center_lng=-118.1930,
        zoom=14.0,
        bbox=LONG_BEACH_DIVISION_BBOXES["DOWNTOWN_SHORELINE"],
        submarkets=[k for k, v in LONG_BEACH_SUBMARKETS.items() if v.borough == "DOWNTOWN_SHORELINE"],
        city_id="long_beach",
    ),
    "BELMONT_SHORE": BoroughMeta(
        name="BELMONT_SHORE",
        center_lat=33.7590,
        center_lng=-118.1525,
        zoom=14.0,
        bbox=LONG_BEACH_DIVISION_BBOXES["BELMONT_SHORE"],
        submarkets=[k for k, v in LONG_BEACH_SUBMARKETS.items() if v.borough == "BELMONT_SHORE"],
        city_id="long_beach",
    ),
    "NAPLES": BoroughMeta(
        name="NAPLES",
        center_lat=33.7560,
        center_lng=-118.1670,
        zoom=15.0,
        bbox=LONG_BEACH_DIVISION_BBOXES["NAPLES"],
        submarkets=[k for k, v in LONG_BEACH_SUBMARKETS.items() if v.borough == "NAPLES"],
        city_id="long_beach",
    ),
    "CAMBODIA_TOWN": BoroughMeta(
        name="CAMBODIA_TOWN",
        center_lat=33.7810,
        center_lng=-118.1745,
        zoom=14.0,
        bbox=LONG_BEACH_DIVISION_BBOXES["CAMBODIA_TOWN"],
        submarkets=[k for k, v in LONG_BEACH_SUBMARKETS.items() if v.borough == "CAMBODIA_TOWN"],
        city_id="long_beach",
    ),
    "WRIGLEY": BoroughMeta(
        name="WRIGLEY",
        center_lat=33.7920,
        center_lng=-118.2010,
        zoom=14.0,
        bbox=LONG_BEACH_DIVISION_BBOXES["WRIGLEY"],
        submarkets=[k for k, v in LONG_BEACH_SUBMARKETS.items() if v.borough == "WRIGLEY"],
        city_id="long_beach",
    ),
    "BIXBY_KNOLLS": BoroughMeta(
        name="BIXBY_KNOLLS",
        center_lat=33.8195,
        center_lng=-118.1900,
        zoom=14.0,
        bbox=LONG_BEACH_DIVISION_BBOXES["BIXBY_KNOLLS"],
        submarkets=[k for k, v in LONG_BEACH_SUBMARKETS.items() if v.borough == "BIXBY_KNOLLS"],
        city_id="long_beach",
    ),
    "CAL_HEIGHTS": BoroughMeta(
        name="CAL_HEIGHTS",
        center_lat=33.8155,
        center_lng=-118.1560,
        zoom=14.0,
        bbox=LONG_BEACH_DIVISION_BBOXES["CAL_HEIGHTS"],
        submarkets=[k for k, v in LONG_BEACH_SUBMARKETS.items() if v.borough == "CAL_HEIGHTS"],
        city_id="long_beach",
    ),
    "NORTH_LONG_BEACH": BoroughMeta(
        name="NORTH_LONG_BEACH",
        center_lat=33.8530,
        center_lng=-118.1935,
        zoom=13.5,
        bbox=LONG_BEACH_DIVISION_BBOXES["NORTH_LONG_BEACH"],
        submarkets=[k for k, v in LONG_BEACH_SUBMARKETS.items() if v.borough == "NORTH_LONG_BEACH"],
        city_id="long_beach",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed live 2026-08-28. Register ONLY the two verified feeds: SLA
# (Business_Licenses_Public_View/0) and CRIME (Police_Crime_Mapping/0).
# Do not register 311 (no ODS client in repo — data.longbeach.gov
# service-requests is verified but blocked), the RHNA permits aggregate,
# the Development_Projects planning snapshot, or the cannabis BL sub-slice.
# ---------------------------------------------------------------------------
LONG_BEACH_SLA_ENDPOINT = (
    "https://services6.arcgis.com/yCArG7wGXGyWLqav/arcgis/rest/services/"
    "Business_Licenses_Public_View/FeatureServer/0"
)
LONG_BEACH_CRIME_ENDPOINT = (
    "https://services6.arcgis.com/yCArG7wGXGyWLqav/arcgis/rest/services/"
    "Police_Crime_Mapping/FeatureServer/0"
)

LONG_BEACH_FEED_SPECS: dict[str, dict[str, object]] = {
    "sla": {
        "endpoint": LONG_BEACH_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "MILESTONEDATE",
        "id_keys": ["LICENSENO", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 3,
            "needs_geocode": True,
            "geocode_context": LONG_BEACH_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "MILESTONEDATE DESC",
            "where": "OUTSIDECITY='No'",
            "scope": (
                "BusinessLicenses_DailyUpdate in-city slice (FeatureServer/0 "
                "on services6.arcgis.com org yCArG7wGXGyWLqav — City of Long "
                "Beach; 178,826 rows total, 133,946 with OUTSIDECITY='No'). "
                "Watermark MILESTONEDATE is daily-fresh (newest verbatim "
                "1787817600000 = 2026-08-27T08:00:00+00:00; 1,337 rows "
                "2026-08-20..probe). ISSDTTM is future-date sentinel-poisoned "
                "(max year 3202) — effective_date only, never the watermark. "
                "Native outSR=4326 point geometry primary; ~0.1% null "
                "geometry falls to the ADR-0004 geocode on SITELOCATION; "
                "junk off-map geocodes (x≈-138/y≈27 outside-city tail) are "
                "downstream metro-scoping's concern. ANSI date literals "
                "work in where."
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
    "crime": {
        "endpoint": LONG_BEACH_CRIME_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ReportedDateTimeDate",
        "id_keys": ["DR", "OBJECTID"],
        "topic_key": "topic_crime",
        "interval_seconds": 1800.0,
        "producer_key": "crime",
        "extra": {
            "expected_cadence_days": 14,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "ReportedDateTimeDate DESC",
            "scope": (
                "LBPD CrimeData (FeatureServer/0, item "
                "db3defed7a894a6088b98ec16b4b5dfa): 11,012 rows in a "
                "~6-month rolling window (oldest 2026-02-18T08:44:07+00:00) "
                "— min(date) is window scoping, not staleness. Watermark "
                "ReportedDateTimeDate newest verbatim 1787106060000 = "
                "2026-08-19T02:21:00+00:00 on the 2026-08-28 probe (~9d "
                "publish lag, ~15 rows/day batched) hence the 14-day "
                "cadence. Native WGS84 point geometry satisfies the "
                "ADR-0004 crime gate — needs_geocode stays false; "
                "Address is block-anonymized by LBPD and is not mapped."
            ),
            "field_map": CRIME_FIELD_MAP,
        },
    },
}


def get_long_beach_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Long Beach feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in LONG_BEACH_FEED_SPECS:
        available = ", ".join(sorted(LONG_BEACH_FEED_SPECS))
        raise KeyError(
            f"'{LONG_BEACH_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = LONG_BEACH_FEED_SPECS[feed_name]
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
    metro_bbox=LONG_BEACH_METRO_BBOX,
    division_bboxes=LONG_BEACH_DIVISION_BBOXES,
    submarkets=LONG_BEACH_SUBMARKETS,
    divisions=LONG_BEACH_DIVISIONS,
    contains=is_in_long_beach_metro,
)

__all__ = [
    "LONG_BEACH_CITY_ID",
    "LONG_BEACH_CRIME_ENDPOINT",
    "LONG_BEACH_DIVISIONS",
    "LONG_BEACH_DIVISION_BBOXES",
    "LONG_BEACH_FEED_SPECS",
    "LONG_BEACH_GEOCODE_CONTEXT",
    "LONG_BEACH_METRO_BBOX",
    "LONG_BEACH_SLA_ENDPOINT",
    "LONG_BEACH_SUBMARKETS",
    "REGISTRATION",
    "get_long_beach_dataset",
    "is_in_greater_long_beach_metro",
    "is_in_long_beach_metro",
]
