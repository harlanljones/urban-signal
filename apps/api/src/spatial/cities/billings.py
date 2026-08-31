PERMITS_FIELD_MAP = {
    "job_id": ["Building_Permit_Num", "OBJECTID"],
    "issuance_date": ["Issue_Date"],
    "filing_date": ["Date_Entered"],
    "status": ["Permit_Status"],
    "job_type": ["Permit_Type"],
    "address_street": ["Property_Address"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

BILLINGS_311_FIELD_MAP = {
    "incident_id": ["reqid", "OBJECTID"],
    "created_date": ["created_date"],
    "closed_date": ["resolutiondt"],
    "status": ["status"],
    "complaint_type": ["reqtype"],
    "incident_address": ["locdesc"],
}

GEOCODE_CONTEXT = "Billings, MT"

DROPPED_PII_COLUMNS = (
    "Owner",
    "Owner_Address",
    "Owner_City",
    "Owner_State",
    "Owner_Zip",
    "Contractor",
    "Contractor_Num",
    "Entered_By",
    "pocfirstname",
    "poclastname",
    "created_user",
)

"""Billings, MT spatial registry and geometry (US-234).

Provides neighborhood metadata, investment metrics, division catalog, and
geographic bounding boxes for the City of Billings (south-central Montana,
Yellowstone County).

Billings is a TWO-FEED PARTIAL metro (registration evidence, live-probed
2026-08-28):

* PERMITS — ``BuildingPermits_CodeViolations_EXT`` (MapServer/0 on the city's
  ArcGIS Server at ``billingsgis.com``, Tier 1, daily). 81,016 rows. The
  ticket's ArcGIS Hub hint (``billings.opendata.arcgis.com``) is a dead
  domain-record; the real public door is the city's ArcGIS Server behind the
  ``billingsmt.gov`` "Permits and Code Violations" map. Native WGS84 geometry
  (outSR=4326) AND native Latitude/Longitude attribute columns — both native
  degrees; the leaf relies on the geometry lift only. ``Issue_Date`` is NOT
  where-clause queryable (ArcGIS 400) — order with ``orderByFields`` and
  filter client-side. Duplicate ``Building_Permit_Num`` rows exist (a
  contractor-to-permit join), so ``OBJECTID`` is the true unique key.
  Newest watermark 2026-08-11 (``1786437732857``). PII (Owner/Contractor
  blocks, Entered_By) dropped at the map.
* COMPLAINTS_311 — ``Requests_public`` (FeatureServer/0 on the city's ArcGIS
  Online org ``rCC3yWJa2mjYtKDP``, Tier 1, daily). 245 rows. Native WGS84
  point geometry (no lat/lng attribute columns — geometry lift only). Newest
  watermark ``created_date`` 2026-08-27 (``1787808604235`` — probe-day fresh).
  PII (pocfirstname/poclastname/created_user) dropped at the map.

Not registered:

* CRIME — ``bpd_offenses`` (8,362 rows, native geometry + CaseAddress) and
  ``tfoffenses_rolling_6months_online`` (1,481 rows, native geometry) both
  carry coordinates and would satisfy ADR-0004, but both are stale (newest
  2024-08-01 and 2023-12-31 respectively) — left unregistered.
* SLA — no business-license feed exists in the org (search: license → 0).
* DEEDS — Yellowstone County recorder reachability failed from the probe
  environment (``co.yellowstone.mt.us`` timeout, no official AGOL org found);
  partial without deeds is correct.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

BILLINGS_CITY_ID: str = "billings"
BILLINGS_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# City of Billings (south-central MT). Permissive enough to hold the downtown
# core (45.7835, -108.5045), the Billings Heights plateau north of the
# Yellowstone River, the West End (King Ave / Grand Ave corridor), the South
# Side below I-90, Midtown along Grand Ave, and the Lockwood community to the
# east — plus the live-probe fixtures down to 45.754, -108.530.
BILLINGS_METRO_BBOX: dict[str, float] = {
    "min_lat": 45.72,
    "max_lat": 45.87,
    "min_lng": -108.65,
    "max_lng": -108.38,
}

# 6 Billings divisions. Hand-authored; borough resolution at ingest comes from
# coordinates via get_division_for_coordinate, so bboxes need only be sane and
# contain their own submarket centers.
BILLINGS_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 45.775,
        "max_lat": 45.794,
        "min_lng": -108.520,
        "max_lng": -108.492,
    },
    "MIDTOWN": {
        "min_lat": 45.776,
        "max_lat": 45.802,
        "min_lng": -108.562,
        "max_lng": -108.520,
    },
    "WEST_END": {
        "min_lat": 45.766,
        "max_lat": 45.796,
        "min_lng": -108.625,
        "max_lng": -108.562,
    },
    "SOUTH_SIDE": {
        "min_lat": 45.742,
        "max_lat": 45.776,
        "min_lng": -108.555,
        "max_lng": -108.505,
    },
    "BILLINGS_HEIGHTS": {
        "min_lat": 45.802,
        "max_lat": 45.845,
        "min_lng": -108.545,
        "max_lng": -108.440,
    },
    "LOCKWOOD": {
        "min_lat": 45.790,
        "max_lat": 45.818,
        "min_lng": -108.440,
        "max_lng": -108.390,
    },
}


def is_in_billings_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Billings metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        BILLINGS_METRO_BBOX["min_lat"] <= lat <= BILLINGS_METRO_BBOX["max_lat"]
        and BILLINGS_METRO_BBOX["min_lng"] <= lng <= BILLINGS_METRO_BBOX["max_lng"]
    )


is_in_greater_billings_metro = is_in_billings_metro


BILLINGS_SUBMARKETS: dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN (1)
    # =======================================================================
    "Downtown": SubmarketMeta(
        name="Downtown",
        borough="DOWNTOWN",
        lat=45.7835,
        lng=-108.5045,
        zoom=14.5,
        pitch=52.0,
        base_lims=0.87,
        capex=6800000.0,
        permit_vel=27.0,
        shift_ratio=1.42,
        sla=51.0,
        description="Montana Avenue / 27th Street CBD core with the courthouse square, historic Skypoint, and the densest commercial permitting corridor in south-central Montana.",
        city_id="billings",
    ),
    # =======================================================================
    # MIDTOWN (2)
    # =======================================================================
    "Midtown": SubmarketMeta(
        name="Midtown",
        borough="MIDTOWN",
        lat=45.7875,
        lng=-108.5460,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=6200000.0,
        permit_vel=25.0,
        shift_ratio=1.39,
        sla=49.0,
        description="Grand Avenue corridor between downtown and the West End with mid-century retail strips, motel conversions, and steady small-bay remodel permits.",
        city_id="billings",
    ),
    "MetraPark District": SubmarketMeta(
        name="MetraPark District",
        borough="MIDTOWN",
        lat=45.7915,
        lng=-108.5230,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.84,
        capex=7500000.0,
        permit_vel=23.0,
        shift_ratio=1.44,
        sla=47.0,
        description="First Interstate Arena at MetraPark and the airport-adjacent event campus with parking-lot infill, hospitality upgrades, and big-box reuse permits.",
        city_id="billings",
    ),
    # =======================================================================
    # WEST_END (2)
    # =======================================================================
    "West End": SubmarketMeta(
        name="West End",
        borough="WEST_END",
        lat=45.7795,
        lng=-108.5900,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.89,
        capex=8400000.0,
        permit_vel=31.0,
        shift_ratio=1.51,
        sla=55.0,
        description="King Avenue / Grand Avenue growth belt with medical-office expansion (Billings Clinic West), auto-oriented retail redevelopment, and the metro's largest new-construction valuations.",
        city_id="billings",
    ),
    "Rimrock": SubmarketMeta(
        name="Rimrock",
        borough="WEST_END",
        lat=45.7723,
        lng=-108.6020,
        zoom=13.5,
        pitch=46.0,
        base_lims=0.86,
        capex=7200000.0,
        permit_vel=26.0,
        shift_ratio=1.46,
        sla=50.0,
        description="Rimrock Mall and West Park Promenade trade area with enclosed-mall redevelopment, grocery-anchored pads, and the last infill parcels along King Ave.",
        city_id="billings",
    ),
    # =======================================================================
    # SOUTH_SIDE (2)
    # =======================================================================
    "South Side": SubmarketMeta(
        name="South Side",
        borough="SOUTH_SIDE",
        lat=45.7650,
        lng=-108.5350,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.83,
        capex=5400000.0,
        permit_vel=21.0,
        shift_ratio=1.37,
        sla=46.0,
        description="Historic South Side below I-90 with the South Park greenbelt, brick bungalow stock, and affordable single-family infill along the Midland rail corridor.",
        city_id="billings",
    ),
    "Southgate": SubmarketMeta(
        name="Southgate",
        borough="SOUTH_SIDE",
        lat=45.7530,
        lng=-108.5220,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.82,
        capex=5900000.0,
        permit_vel=22.0,
        shift_ratio=1.40,
        sla=45.0,
        description="Southgate Drive corridor at the city's south edge with newer subdivisions, the Southgate Mall trade area, and incremental multifamily infill.",
        city_id="billings",
    ),
    # =======================================================================
    # BILLINGS_HEIGHTS (2)
    # =======================================================================
    "Billings Heights": SubmarketMeta(
        name="Billings Heights",
        borough="BILLINGS_HEIGHTS",
        lat=45.8150,
        lng=-108.4820,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.84,
        capex=6100000.0,
        permit_vel=24.0,
        shift_ratio=1.41,
        sla=48.0,
        description="Main Street north-of-the-river residential plateau with ranch inventory, box-retail nodes, and steady single-family and duplex permitting.",
        city_id="billings",
    ),
    "Airport District": SubmarketMeta(
        name="Airport District",
        borough="BILLINGS_HEIGHTS",
        lat=45.8077,
        lng=-108.5427,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.81,
        capex=8200000.0,
        permit_vel=25.0,
        shift_ratio=1.43,
        sla=44.0,
        description="Billings Logan International Airport and the surrounding aviation/logistics employment zone with hangar construction, freight expansion, and hotel permitting.",
        city_id="billings",
    ),
    # =======================================================================
    # LOCKWOOD (1)
    # =======================================================================
    "Lockwood": SubmarketMeta(
        name="Lockwood",
        borough="LOCKWOOD",
        lat=45.8020,
        lng=-108.4140,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.80,
        capex=5800000.0,
        permit_vel=20.0,
        shift_ratio=1.36,
        sla=42.0,
        description="Unincorporated Lockwood community east of the city line with I-90-adjacent trade parcels, light-industrial expansion, and affordable-acreage home building.",
        city_id="billings",
    ),
}


BILLINGS_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=45.7835,
        center_lng=-108.5045,
        zoom=14.0,
        bbox=BILLINGS_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in BILLINGS_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="billings",
    ),
    "MIDTOWN": BoroughMeta(
        name="MIDTOWN",
        center_lat=45.7875,
        center_lng=-108.5460,
        zoom=14.0,
        bbox=BILLINGS_DIVISION_BBOXES["MIDTOWN"],
        submarkets=[k for k, v in BILLINGS_SUBMARKETS.items() if v.borough == "MIDTOWN"],
        city_id="billings",
    ),
    "WEST_END": BoroughMeta(
        name="WEST_END",
        center_lat=45.7770,
        center_lng=-108.6000,
        zoom=13.5,
        bbox=BILLINGS_DIVISION_BBOXES["WEST_END"],
        submarkets=[k for k, v in BILLINGS_SUBMARKETS.items() if v.borough == "WEST_END"],
        city_id="billings",
    ),
    "SOUTH_SIDE": BoroughMeta(
        name="SOUTH_SIDE",
        center_lat=45.7620,
        center_lng=-108.5310,
        zoom=13.5,
        bbox=BILLINGS_DIVISION_BBOXES["SOUTH_SIDE"],
        submarkets=[k for k, v in BILLINGS_SUBMARKETS.items() if v.borough == "SOUTH_SIDE"],
        city_id="billings",
    ),
    "BILLINGS_HEIGHTS": BoroughMeta(
        name="BILLINGS_HEIGHTS",
        center_lat=45.8150,
        center_lng=-108.4820,
        zoom=13.0,
        bbox=BILLINGS_DIVISION_BBOXES["BILLINGS_HEIGHTS"],
        submarkets=[k for k, v in BILLINGS_SUBMARKETS.items() if v.borough == "BILLINGS_HEIGHTS"],
        city_id="billings",
    ),
    "LOCKWOOD": BoroughMeta(
        name="LOCKWOOD",
        center_lat=45.8020,
        center_lng=-108.4140,
        zoom=13.0,
        bbox=BILLINGS_DIVISION_BBOXES["LOCKWOOD"],
        submarkets=[k for k, v in BILLINGS_SUBMARKETS.items() if v.borough == "LOCKWOOD"],
        city_id="billings",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28. Do not register crime (stale), SLA (none found), or deeds
# (Yellowstone County recorder unreachable).
# ---------------------------------------------------------------------------
BILLINGS_PERMITS_ENDPOINT = (
    "https://billingsgis.com/arcgis_public/rest/services/"
    "ArcOnline_Public/BuildingPermits_CodeViolations_EXT/MapServer/0"
)

BILLINGS_311_ENDPOINT = (
    "https://services6.arcgis.com/rCC3yWJa2mjYtKDP/arcgis/rest/services/"
    "Requests_public_00e63199176f44b788fd43684476713d/FeatureServer/0"
)

BILLINGS_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": BILLINGS_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "Issue_Date",
        "id_keys": ["Building_Permit_Num", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "geocode_context": BILLINGS_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "Issue_Date DESC",
            "scope": (
                "BuildingPermits_CodeViolations_EXT issued/completed permits "
                "(MapServer on billingsgis.com — same query contract, not a "
                "FeatureServer; 81,016 rows; native outSR=4326 point geometry, "
                "Latitude/Longitude attribute columns are also native degrees "
                "but the geometry lift is the coordinate source; Issue_Date is "
                "not where-clause queryable (ArcGIS 400) — orderByFields only, "
                "filter at analytics; duplicate Building_Permit_Num rows exist "
                "via the contractor-to-permit join, OBJECTID is the unique key)"
            ),
            "field_map": PERMITS_FIELD_MAP,
        },
    },
    "311": {
        "endpoint": BILLINGS_311_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "created_date",
        "id_keys": ["reqid", "OBJECTID"],
        "topic_key": "topic_311",
        "interval_seconds": 300.0,
        "producer_key": "311",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "geocode_context": BILLINGS_GEOCODE_CONTEXT,
            "oid_field": "OBJECTID",
            "max_record_count": 2000,
            "order_by": "created_date DESC",
            "scope": (
                "Requests_public city service requests (FeatureServer on the "
                "City of Billings ArcGIS Online org rCC3yWJa2mjYtKDP; 245 rows; "
                "native WGS84 point geometry — no lat/lng attribute columns; "
                "created_date is the daily watermark; pocfirstname/"
                "poclastname/created_user PII dropped at the map)"
            ),
            "field_map": BILLINGS_311_FIELD_MAP,
        },
    },
}


def get_billings_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a registered Billings feed, or raises ``KeyError``
    naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in BILLINGS_FEED_SPECS:
        available = ", ".join(sorted(BILLINGS_FEED_SPECS))
        raise KeyError(
            f"'{BILLINGS_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = BILLINGS_FEED_SPECS[feed_name]
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
    metro_bbox=BILLINGS_METRO_BBOX,
    division_bboxes=BILLINGS_DIVISION_BBOXES,
    submarkets=BILLINGS_SUBMARKETS,
    divisions=BILLINGS_DIVISIONS,
    contains=is_in_billings_metro,
)

__all__ = [
    "BILLINGS_311_ENDPOINT",
    "BILLINGS_CITY_ID",
    "BILLINGS_DIVISIONS",
    "BILLINGS_DIVISION_BBOXES",
    "BILLINGS_FEED_SPECS",
    "BILLINGS_GEOCODE_CONTEXT",
    "BILLINGS_METRO_BBOX",
    "BILLINGS_PERMITS_ENDPOINT",
    "BILLINGS_SUBMARKETS",
    "REGISTRATION",
    "get_billings_dataset",
    "is_in_billings_metro",
    "is_in_greater_billings_metro",
]