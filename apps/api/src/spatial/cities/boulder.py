PERMITS_FIELD_MAP = {
    "job_id": ["PermitNum", "PermitID", "ObjectId"],
    "issuance_date": ["IssuedDate"],
    "filing_date": ["AppliedDate"],
    "status": ["StatusCurrent"],
    "job_type": ["PermitType", "PermitWorkType"],
    "cost": ["EstProjectCost"],
    "address_street": ["OriginalAddress"],
    "zipcode": ["OriginalZip"],
    "borough": ["OriginalCity"],
}

SLA_FIELD_MAP = {
    "license_id": ["LICENSENUMBER"],
    "dba": ["COMPLEXNAME", "PROFESSIONALLICENSEHOLDERNAME"],
    "premises_name": ["COMPLEXNAME"],
    "license_type": ["RENTALTYPE"],
    "status": ["LICENSESTATUS"],
    "effective_date": ["APPLIEDDATE"],
    "expiration_date": ["EXPIRATIONDATE"],
    "address_street": ["MAINADDRESS"],
    "borough": ["SUBCOMMUNITY"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT = "Boulder, CO"

"""Boulder, CO spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Boulder, CO
and its county-fringe context (Boulder County).

Boulder is a TWO-FEED partial metro (live-probed 2026-08-28, US-245):

* PERMITS — ``Construction_Permits`` FeatureServer/0 on the city's AGOL org
  (services.arcgis.com/ePKBjXrBZ2vEEgWd). A **Table** (non-spatial): no
  geometry is returned. 335,946 rows; all dates are ANSI string ``YYYY-MM-DD``;
  watermark ``IssuedDate``, newest 2026-08-27. Address-only
  (``OriginalAddress`` + ``OriginalCity``/``OriginalState``/``OriginalZip``),
  so ``needs_geocode=True`` with context "Boulder, CO".
* SLA — ``RentalHousingLicenses`` MapServer/0 on the city ArcGIS Server
  (gis.bouldercolorado.gov/ags_svr1/plan/...). 11,720 rows; parcel **polygon**
  geometry at native WKID 2876 (NAD83 Colorado North state-plane feet), lifted
  to WGS84 centroids via ``outSR=4326``. ``APPLIEDDATE`` is the clean
  watermark (newest 2026-08-23); ``ISSUEDDATE`` carries future-dated
  license-period effective dates (e.g. 2027-04-20) and is NOT the watermark.
  ``SUBCOMMUNITY`` supplies neighborhood granularity (South Boulder, Southeast
  Boulder, Palo Park, …).

Rejected feeds (evidence in stream log west-boulder.md):

* 311 — Inquire Boulder CS Portal Requests by Topic (62,265 rows) is an
  aggregate by Department/Topic with no addresses and no geometry; the
  InquireBoulderIncidentAddress/RequesterAddress services are address
  locators with no data.
* DEEDS — no fresh verifiable bulk feed. Boulder County "Recent Sales" AGOL
  service (194,681 rows, polygon geometry) maxes at SaleDate 2025-03-28, the
  item was last modified 2024-09-03, and date-range where clauses return 400;
  the county's PropSearch_SALES table (752,488 rows, non-spatial) has
  future-date sentinels on SaleDate (top rows 2057/2027), null dates, and the
  same non-queryable date-range limitation.
* SLA — Active_Business_Licenses (13,656 rows) is stale (newest
  License_Effective_Date 2019-09-09) and carries only City/State/Zip with no
  street address; Licensed_Contractors (3,077 rows) is a current snapshot
  with no usable watermark (only future-dated ExpirationDate).
* CRIME — Boulder_PD_Calls_For_Service (365,854 rows, point geometry) is
  verified live but out of scope for this leaf (ticket prefers
  permits/311/SLA/deeds).
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BOULDER_CITY_ID: str = "boulder"
BOULDER_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# Native store SR of the RentalHousingLicenses layer — NAD83 Colorado North
# state plane, US survey feet (WKID 2876). Every query requests outSR=4326 so
# geometry arrives as WGS84; the state-plane declaration documents the native
# CRS for any fallback path.
BOULDER_STATE_PLANE_CRS: str = "EPSG:2876"
BOULDER_STATE_PLANE_UNITS: str = "ftUS"

# City of Boulder plus the immediate county fringe (Gunbarrel to the NE).
# Permissive enough to hold the Downtown core (-105.274), the Flatirons-facing
# west edge (-105.31), the Table Mesa/South Boulder belt (39.97), North Boulder
# (40.03), and Gunbarrel (40.06) while rejecting Superior (39.95, -105.16),
# Louisville (-105.13), Lafayette (-105.09), and Denver (-104.99).
BOULDER_METRO_BBOX: dict[str, float] = {
    "min_lat": 39.94,
    "max_lat": 40.09,
    "min_lng": -105.33,
    "max_lng": -105.14,
}

# 7 Boulder divisions. Hand-authored; borough resolution at ingest comes from
# coordinates via get_division_for_coordinate, so bboxes need only be sane,
# mutually non-overlapping, and contain their own submarket centers.
BOULDER_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN_WEST": {
        "min_lat": 39.990,
        "max_lat": 40.035,
        "min_lng": -105.320,
        "max_lng": -105.260,
    },
    "UNIVERSITY_HILL": {
        "min_lat": 39.980,
        "max_lat": 40.015,
        "min_lng": -105.285,
        "max_lng": -105.255,
    },
    "CENTRAL_EAST": {
        "min_lat": 40.000,
        "max_lat": 40.035,
        "min_lng": -105.255,
        "max_lng": -105.220,
    },
    "NORTH_BOULDER": {
        "min_lat": 40.035,
        "max_lat": 40.070,
        "min_lng": -105.320,
        "max_lng": -105.245,
    },
    "SOUTH_BOULDER": {
        "min_lat": 39.940,
        "max_lat": 40.000,
        "min_lng": -105.320,
        "max_lng": -105.245,
    },
    "SOUTHEAST_BOULDER": {
        "min_lat": 39.940,
        "max_lat": 40.000,
        "min_lng": -105.245,
        "max_lng": -105.140,
    },
    "GUNBARREL": {
        "min_lat": 40.035,
        "max_lat": 40.090,
        "min_lng": -105.245,
        "max_lng": -105.140,
    },
}


def is_in_boulder_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Boulder / county-fringe bounds."""
    if lat is None or lng is None:
        return False
    return (
        BOULDER_METRO_BBOX["min_lat"] <= lat <= BOULDER_METRO_BBOX["max_lat"]
        and BOULDER_METRO_BBOX["min_lng"] <= lng <= BOULDER_METRO_BBOX["max_lng"]
    )


is_in_greater_boulder_metro = is_in_boulder_metro


BOULDER_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_WEST (2)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN_WEST",
        lat=40.0193,
        lng=-105.2738,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.88,
        capex=6800000.0,
        permit_vel=32.0,
        shift_ratio=1.48,
        sla=56.0,
        description=(
            "Pearl Street Mall core with the Civic Area, Boulder Theater, "
            "and the city's densest mixed-use adaptive-reuse permitting."
        ),
        city_id="boulder",
    ),
    "Mapleton Hill": SubmarketMeta(
        name="Mapleton Hill",
        borough="DOWNTOWN_WEST",
        lat=40.0240,
        lng=-105.2820,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.86,
        capex=5900000.0,
        permit_vel=24.0,
        shift_ratio=1.42,
        sla=52.0,
        description=(
            "West-side historic district of Victorians and Craftsman stock "
            "with renovation-led and restoration permitting."
        ),
        city_id="boulder",
    ),
    # =======================================================================
    # UNIVERSITY_HILL (1)
    # =======================================================================
    "University Hill": SubmarketMeta(
        name="University Hill",
        borough="UNIVERSITY_HILL",
        lat=40.0076,
        lng=-105.2708,
        zoom=14.0,
        pitch=52.0,
        base_lims=0.87,
        capex=6200000.0,
        permit_vel=27.0,
        shift_ratio=1.45,
        sla=54.0,
        description=(
            "The Hill commercial strip and CU Boulder-adjacent student "
            "housing with rental-license churn and storefront turnover."
        ),
        city_id="boulder",
    ),
    # =======================================================================
    # CENTRAL_EAST (2)
    # =======================================================================
    "Whittier": SubmarketMeta(
        name="Whittier",
        borough="DOWNTOWN_WEST",
        lat=40.0270,
        lng=-105.2700,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.84,
        capex=5600000.0,
        permit_vel=26.0,
        shift_ratio=1.43,
        sla=51.0,
        description=(
            "Central Boulder neighborhood with bungalow infill, ADU "
            "additions, and steady renovation permitting."
        ),
        city_id="boulder",
    ),
    "Boulder Junction": SubmarketMeta(
        name="Boulder Junction",
        borough="CENTRAL_EAST",
        lat=40.0320,
        lng=-105.2320,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.85,
        capex=7200000.0,
        permit_vel=31.0,
        shift_ratio=1.46,
        sla=53.0,
        description=(
            "East Boulder transit village around the RTD station with "
            "new-build mixed-use, office, and multifamily permitting."
        ),
        city_id="boulder",
    ),
    # =======================================================================
    # NORTH_BOULDER (2)
    # =======================================================================
    "North Boulder": SubmarketMeta(
        name="North Boulder",
        borough="NORTH_BOULDER",
        lat=40.0470,
        lng=-105.2800,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.85,
        capex=6400000.0,
        permit_vel=29.0,
        shift_ratio=1.45,
        sla=52.0,
        description=(
            "North Boulder (NoBo) growth corridor along Broadway with "
            "master-planned housing, mixed-use pads, and utility work."
        ),
        city_id="boulder",
    ),
    "Holiday": SubmarketMeta(
        name="Holiday",
        borough="NORTH_BOULDER",
        lat=40.0620,
        lng=-105.2800,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.83,
        capex=5800000.0,
        permit_vel=26.0,
        shift_ratio=1.42,
        sla=50.0,
        description=(
            "Holiday neighborhood at the north city edge with ranch stock, "
            "additions, and the North Boulder Rec Center belt."
        ),
        city_id="boulder",
    ),
    # =======================================================================
    # SOUTH_BOULDER (2)
    # =======================================================================
    "Table Mesa": SubmarketMeta(
        name="Table Mesa",
        borough="SOUTH_BOULDER",
        lat=39.9780,
        lng=-105.2500,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.86,
        capex=6000000.0,
        permit_vel=27.0,
        shift_ratio=1.44,
        sla=53.0,
        description=(
            "Post-war South Boulder residential belt with mid-century "
            "renovations, solar retrofits, and remodel permits."
        ),
        city_id="boulder",
    ),
    "Martin Acres": SubmarketMeta(
        name="Martin Acres",
        borough="SOUTHEAST_BOULDER",
        lat=39.9820,
        lng=-105.2350,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.85,
        capex=5900000.0,
        permit_vel=26.0,
        shift_ratio=1.43,
        sla=52.0,
        description=(
            "Martin Acres tract housing with renovation-led permitting and "
            "steady rental-license coverage."
        ),
        city_id="boulder",
    ),
    # =======================================================================
    # SOUTHEAST_BOULDER (1)
    # =======================================================================
    "Southeast Boulder": SubmarketMeta(
        name="Southeast Boulder",
        borough="SOUTHEAST_BOULDER",
        lat=39.9990,
        lng=-105.2350,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.84,
        capex=6100000.0,
        permit_vel=28.0,
        shift_ratio=1.44,
        sla=52.0,
        description=(
            "Southeast Boulder residential and light-commercial belt with "
            "in-fill housing and Flatirons Business Park-adjacent permitting."
        ),
        city_id="boulder",
    ),
    # =======================================================================
    # GUNBARREL (1)
    # =======================================================================
    "Gunbarrel": SubmarketMeta(
        name="Gunbarrel",
        borough="GUNBARREL",
        lat=40.0620,
        lng=-105.1950,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.82,
        capex=6600000.0,
        permit_vel=25.0,
        shift_ratio=1.41,
        sla=49.0,
        description=(
            "Gunbarrel master-planned area at the NE city fringe with "
            "office parks, townhome infill, and residential build-out."
        ),
        city_id="boulder",
    ),
}


BOULDER_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN_WEST": BoroughMeta(
        name="DOWNTOWN_WEST",
        center_lat=40.019,
        center_lng=-105.283,
        zoom=13.5,
        bbox=BOULDER_DIVISION_BBOXES["DOWNTOWN_WEST"],
        submarkets=[k for k, v in BOULDER_SUBMARKETS.items() if v.borough == "DOWNTOWN_WEST"],
        city_id="boulder",
    ),
    "UNIVERSITY_HILL": BoroughMeta(
        name="UNIVERSITY_HILL",
        center_lat=40.0076,
        center_lng=-105.2708,
        zoom=13.5,
        bbox=BOULDER_DIVISION_BBOXES["UNIVERSITY_HILL"],
        submarkets=[k for k, v in BOULDER_SUBMARKETS.items() if v.borough == "UNIVERSITY_HILL"],
        city_id="boulder",
    ),
    "CENTRAL_EAST": BoroughMeta(
        name="CENTRAL_EAST",
        center_lat=40.020,
        center_lng=-105.250,
        zoom=13.0,
        bbox=BOULDER_DIVISION_BBOXES["CENTRAL_EAST"],
        submarkets=[k for k, v in BOULDER_SUBMARKETS.items() if v.borough == "CENTRAL_EAST"],
        city_id="boulder",
    ),
    "NORTH_BOULDER": BoroughMeta(
        name="NORTH_BOULDER",
        center_lat=40.047,
        center_lng=-105.280,
        zoom=13.0,
        bbox=BOULDER_DIVISION_BBOXES["NORTH_BOULDER"],
        submarkets=[k for k, v in BOULDER_SUBMARKETS.items() if v.borough == "NORTH_BOULDER"],
        city_id="boulder",
    ),
    "SOUTH_BOULDER": BoroughMeta(
        name="SOUTH_BOULDER",
        center_lat=39.980,
        center_lng=-105.255,
        zoom=13.0,
        bbox=BOULDER_DIVISION_BBOXES["SOUTH_BOULDER"],
        submarkets=[k for k, v in BOULDER_SUBMARKETS.items() if v.borough == "SOUTH_BOULDER"],
        city_id="boulder",
    ),
    "SOUTHEAST_BOULDER": BoroughMeta(
        name="SOUTHEAST_BOULDER",
        center_lat=39.975,
        center_lng=-105.200,
        zoom=12.5,
        bbox=BOULDER_DIVISION_BBOXES["SOUTHEAST_BOULDER"],
        submarkets=[k for k, v in BOULDER_SUBMARKETS.items() if v.borough == "SOUTHEAST_BOULDER"],
        city_id="boulder",
    ),
    "GUNBARREL": BoroughMeta(
        name="GUNBARREL",
        center_lat=40.062,
        center_lng=-105.195,
        zoom=12.5,
        bbox=BOULDER_DIVISION_BBOXES["GUNBARREL"],
        submarkets=[k for k, v in BOULDER_SUBMARKETS.items() if v.borough == "GUNBARREL"],
        city_id="boulder",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register 311 (aggregate, no addresses), deeds
# (no fresh bulk feed), Active_Business_Licenses (stale 2019), or
# Licensed_Contractors (snapshot, no watermark).
# ---------------------------------------------------------------------------
BOULDER_PERMITS_ENDPOINT = (
    "https://services.arcgis.com/ePKBjXrBZ2vEEgWd/arcgis/rest/services/"
    "Construction_Permits/FeatureServer/0"
)
BOULDER_SLA_ENDPOINT = (
    "https://gis.bouldercolorado.gov/ags_svr1/rest/services/"
    "plan/RentalHousingLicenses/MapServer/0"
)

BOULDER_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": BOULDER_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "IssuedDate",
        "id_keys": ["PermitNum", "PermitID", "ObjectId"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": True,
            "geocode_context": BOULDER_GEOCODE_CONTEXT,
            "oid_field": "ObjectId",
            "max_record_count": 1000,
            "order_by": "IssuedDate DESC",
            "watermark_type": "text",
            "watermark_format": "%Y-%m-%d",
            "scope": (
                "City of Boulder Construction_Permits (AGOL FeatureServer/0, "
                "Table = non-spatial): all dates are ANSI string YYYY-MM-DD "
                "and no geometry is returned — coordinates come from the "
                "ADR-0004 geocode supplement on OriginalAddress + OriginalCity/"
                "OriginalState/OriginalZip; watermark IssuedDate newest "
                "2026-08-27; PermitType covers the full building/utility/"
                "trade permit set; OriginalCity has typos (BOUDER/BUOLDER) "
                "and out-of-city values (LONGMONT/GREELEY) — bbox filters"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "sla": {
        "endpoint": BOULDER_SLA_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "APPLIEDDATE",
        "id_keys": ["LICENSENUMBER", "OBJECTID"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "extra": {
            "expected_cadence_days": 7,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "APPLIEDDATE DESC",
            "state_plane_crs": BOULDER_STATE_PLANE_CRS,
            "state_plane_units": BOULDER_STATE_PLANE_UNITS,
            "scope": (
                "City of Boulder RentalHousingLicenses (ArcGIS Server "
                "MapServer/0, native WKID 2876 CO North state-plane feet; "
                "outSR=4326 polygon centroid lift is the coordinate path). "
                "Watermark APPLIEDDATE (newest 2026-08-23); ISSUEDDATE is "
                "NOT the watermark — it carries future-dated license-period "
                "effective dates (e.g. 2027-04-20). SUBCOMMUNITY supplies "
                "source_neighborhood. EXPIRATIONDATE/LASTRENEWALDATE may be "
                "null for pending applications."
            ),
            "field_map": SLA_FIELD_MAP,
        },
    },
}


def get_boulder_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Boulder feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in BOULDER_FEED_SPECS:
        available = ", ".join(sorted(BOULDER_FEED_SPECS))
        raise KeyError(
            f"'{BOULDER_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = BOULDER_FEED_SPECS[feed_name]
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
    metro_bbox=BOULDER_METRO_BBOX,
    division_bboxes=BOULDER_DIVISION_BBOXES,
    submarkets=BOULDER_SUBMARKETS,
    divisions=BOULDER_DIVISIONS,
    contains=is_in_boulder_metro,
)

__all__ = [
    "BOULDER_CITY_ID",
    "BOULDER_DIVISIONS",
    "BOULDER_DIVISION_BBOXES",
    "BOULDER_FEED_SPECS",
    "BOULDER_GEOCODE_CONTEXT",
    "BOULDER_METRO_BBOX",
    "BOULDER_PERMITS_ENDPOINT",
    "BOULDER_SLA_ENDPOINT",
    "BOULDER_STATE_PLANE_CRS",
    "BOULDER_STATE_PLANE_UNITS",
    "BOULDER_SUBMARKETS",
    "REGISTRATION",
    "get_boulder_dataset",
    "is_in_boulder_metro",
    "is_in_greater_boulder_metro",
]