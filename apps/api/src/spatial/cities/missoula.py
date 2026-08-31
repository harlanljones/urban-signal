PERMITS_FIELD_MAP = {
    "job_id": ["RecordID", "OBJECTID"],
    "filing_date": ["ApplicationDate"],
    "status": ["RecordStatus"],
    "job_type": ["B1_PER_TYPE", "B1_PER_SUB_TYPE"],
    "description": ["DescriptionOfWork"],
    "address_street": ["Address", "FullAddress"],
}

FIELD_MAP = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT = "Missoula, MT"

DROPPED_PII_COLUMNS = ()

"""Missoula, MT spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Missoula
and its urban fringe.

Missoula is a ONE-FEED PARTIAL metro like Stockton: PERMITS only
(``AddressesWithPermits_mso`` FeatureServer/0 on the city's official AGOL
org). COMPLAINTS_311, SLA, and DEEDS are unregistered (see rejection evidence
below).

Live-probe evidence that defines this leaf (2026-08-28, US-235; city Hub
``missoulamaps-cityofmissoula.hub.arcgis.com`` → city AGOL org
``services.arcgis.com/HfwHS0BxZBQ1E5DY``):

* PERMITS — ``AddressesWithPermits_mso`` = 122,448 rows, point geometry,
  store SR **WKID 102700 (NAD83 Montana State Plane, meters)** with the host
  honoring ``outSR=4326`` (live fixtures return degrees — server-side
  reprojection). ``ApplicationDate`` (esriFieldTypeDate, epoch-ms → ISO on
  flatten) is the watermark: newest = **2026-08-27** (1787788800000), 0
  nulls, 0 future sentinels, max_record_count = 1000. The layer is the
  city's comprehensive permit-address tracking (all B1_PER_TYPE families:
  Building, Electrical, Utility Excavation, Commercial Construction, Roofing,
  Fence, Right-of-Way, Residential Construction, etc.). Watermark freshness
  ≈1 day (permit ingested within 24 hours of application date) →
  ``expected_cadence_days=1``. No issuance_date column exists (no cost
  column either); the ``DOBPermitsProducer`` populates estimated_cost=0.0
  and issuance_date=None honestly. Every sampled row carries geometry
  (0/3,000 null across 6 offsets) — the geometry lift is the sole locator
  and ``needs_geocode=False``. The layer carries no projected X/Y attribute
  columns, so no ``state_plane_*`` spec keys are declared.

Feed rejections (live evidence, same probe):

* COMPLAINTS_311 — no general citizen-request surface exists on either org.
  The county's ``311_Debris_Overgrowth_WFL1`` (240 rows) is a STALE MIRROR
  of Pittsburgh 311 data (neighborhoods "Brookline", "Swisshelm Park",
  geometry at -80.02°/40.39° — 1,600 mi from Missoula). The city's
  ``Illicit_Discharge`` (310 rows) and ``MS4_Maintenance_Request`` (16 rows)
  are narrow Survey123 stormwater surfaces, not general 311 feeds. Do not
  register.
* SLA — no business-license feed exists on the city or county AGOL org
  (both orgs searched: 0 title matches for "business license", "license").
  Do not register.
* DEEDS — Missoula County publishes no bulk recorded-document or sales feed
  on AGOL. ``TaxAll`` (60,807 parcel polygons) is assessment parcels, not
  sales. The Clerk & Recorder recorded-documents are behind a search portal.
  Partial (permits only) is the honest shape.
"""


from src.spatial.submarkets import BoroughMeta, SubmarketMeta

MISSOULA_CITY_ID: str = "missoula"
MISSOULA_GEOCODE_CONTEXT: str = GEOCODE_CONTEXT

# NAD83 Montana State Plane, meters — native store SR of the probed layer
# (WKID 102700; extent 813k..866k x / 959k..1016k m). Documentation constant
# only: the spec declares no state_plane_* keys because the layer has no
# projected X/Y attribute columns — coordinates ride the outSR=4326 geometry
# lift.
MISSOULA_STATE_PLANE_CRS: str = "EPSG:102700"
MISSOULA_STATE_PLANE_UNITS: str = "m"

# City of Missoula plus urban fringe. Permissive enough to hold all 20
# official neighborhoods (Northside, University District, Heart of Missoula,
# Rose Park, Southgate Triangle, Miller Creek, Grant Creek, Lower/Upper
# Rattlesnake, etc.) while rejecting downtown Helena (46.59, -112.03),
# Bozeman (45.68, -111.04), and Spokane (47.66, -117.43).
MISSOULA_METRO_BBOX: dict[str, float] = {
    "min_lat": 46.78,
    "max_lat": 46.94,
    "min_lng": -114.13,
    "max_lng": -113.92,
}

# 7 Missoula divisions, evidence-based from the official
# Neighborhoods_mso layer (20 polygons, live-probed 2026-08-28). Hand-authored
# bboxes that nest inside the metro bbox and contain their submarket centers.
MISSOULA_DIVISION_BBOXES: dict[str, dict[str, float]] = {
    "DOWNTOWN": {
        "min_lat": 46.866,
        "max_lat": 46.878,
        "min_lng": -114.002,
        "max_lng": -113.988,
    },
    "UNIVERSITY": {
        "min_lat": 46.850,
        "max_lat": 46.866,
        "min_lng": -114.020,
        "max_lng": -113.980,
    },
    "SOUTHSIDE": {
        "min_lat": 46.822,
        "max_lat": 46.850,
        "min_lng": -114.050,
        "max_lng": -114.000,
    },
    "WEST_MIDTOWN": {
        "min_lat": 46.846,
        "max_lat": 46.885,
        "min_lng": -114.060,
        "max_lng": -114.002,
    },
    "NORTHSIDE": {
        "min_lat": 46.878,
        "max_lat": 46.930,
        "min_lng": -114.100,
        "max_lng": -113.990,
    },
    "RATTLESNAKE": {
        "min_lat": 46.878,
        "max_lat": 46.930,
        "min_lng": -114.002,
        "max_lng": -113.920,
    },
    "SOUTHEAST": {
        "min_lat": 46.780,
        "max_lat": 46.846,
        "min_lng": -114.100,
        "max_lng": -113.950,
    },
}


def is_in_missoula_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Missoula metro bounds."""
    if lat is None or lng is None:
        return False
    return (
        MISSOULA_METRO_BBOX["min_lat"] <= lat <= MISSOULA_METRO_BBOX["max_lat"]
        and MISSOULA_METRO_BBOX["min_lng"] <= lng <= MISSOULA_METRO_BBOX["max_lng"]
    )


is_in_greater_missoula_metro = is_in_missoula_metro


MISSOULA_SUBMARKETS: dict[str, SubmarketMeta] = {
    # ===================================================================
    # DOWNTOWN (2)
    # ===================================================================
    "Heart of Missoula": SubmarketMeta(
        name="Heart of Missoula",
        borough="DOWNTOWN",
        lat=46.8721,
        lng=-113.9940,
        zoom=15.0,
        pitch=48.0,
        base_lims=0.82,
        capex=7200000.0,
        permit_vel=38.0,
        shift_ratio=1.44,
        sla=54.0,
        description="Central downtown core with Higgins Avenue retail, the Wilma, and the Missoula Farmers Market adjacency.",
        city_id="missoula",
    ),
    "Riverfront": SubmarketMeta(
        name="Riverfront",
        borough="DOWNTOWN",
        lat=46.8710,
        lng=-113.9965,
        zoom=15.0,
        pitch=45.0,
        base_lims=0.78,
        capex=5800000.0,
        permit_vel=32.0,
        shift_ratio=1.38,
        sla=50.0,
        description="Clark Fork riverfront corridor with Caras Park, the Brennan's Wave surf amenity, and mixed-use redevelopment.",
        city_id="missoula",
    ),
    # ===================================================================
    # UNIVERSITY (3)
    # ===================================================================
    "University District": SubmarketMeta(
        name="University District",
        borough="UNIVERSITY",
        lat=46.8595,
        lng=-113.9842,
        zoom=15.0,
        pitch=48.0,
        base_lims=0.80,
        capex=6400000.0,
        permit_vel=34.0,
        shift_ratio=1.40,
        sla=52.0,
        description="University of Montana campus-adjacent historic district with student housing turnover and academic-adjacent licensing.",
        city_id="missoula",
    ),
    "Franklin to the Fort": SubmarketMeta(
        name="Franklin to the Fort",
        borough="UNIVERSITY",
        lat=46.8570,
        lng=-114.0030,
        zoom=14.5,
        pitch=44.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=28.0,
        shift_ratio=1.34,
        sla=46.0,
        description="Transitional corridor between UM and the South Hills with single-family infill and small-scale commercial.",
        city_id="missoula",
    ),
    "Lewis & Clark": SubmarketMeta(
        name="Lewis & Clark",
        borough="UNIVERSITY",
        lat=46.8650,
        lng=-114.0180,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.76,
        capex=5200000.0,
        permit_vel=30.0,
        shift_ratio=1.36,
        sla=48.0,
        description="Southwest residential neighborhood of mid-century ranch homes with steady renovation permitting.",
        city_id="missoula",
    ),
    # ===================================================================
    # SOUTHSIDE (3)
    # ===================================================================
    "Southgate Triangle": SubmarketMeta(
        name="Southgate Triangle",
        borough="SOUTHSIDE",
        lat=46.8380,
        lng=-114.0200,
        zoom=14.5,
        pitch=46.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=32.0,
        shift_ratio=1.38,
        sla=50.0,
        description="Southgate Mall retail node and surrounding garden-apartment stock with commercial renovation and tenant-improvement permits.",
        city_id="missoula",
    ),
    "South 39th Street": SubmarketMeta(
        name="South 39th Street",
        borough="SOUTHSIDE",
        lat=46.8305,
        lng=-114.0150,
        zoom=14.5,
        pitch=44.0,
        base_lims=0.74,
        capex=4600000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=46.0,
        description="South-central residential corridor of post-war single-family homes with modest renovation cyclics.",
        city_id="missoula",
    ),
    "Two Rivers": SubmarketMeta(
        name="Two Rivers",
        borough="SOUTHSIDE",
        lat=46.8280,
        lng=-114.0400,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.72,
        capex=4200000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=44.0,
        description="Clark Fork / Bitterroot confluence neighborhood with large-lot single-family and rural-urban fringe permitting.",
        city_id="missoula",
    ),
    # ===================================================================
    # WEST_MIDTOWN (4)
    # ===================================================================
    "Westside": SubmarketMeta(
        name="Westside",
        borough="WEST_MIDTOWN",
        lat=46.8730,
        lng=-114.0260,
        zoom=14.5,
        pitch=46.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=30.0,
        shift_ratio=1.36,
        sla=50.0,
        description="West Missoula corridor with Reserve Street commercial spine and working-class single-family stock.",
        city_id="missoula",
    ),
    "Rose Park": SubmarketMeta(
        name="Rose Park",
        borough="WEST_MIDTOWN",
        lat=46.8780,
        lng=-114.0070,
        zoom=14.5,
        pitch=46.0,
        base_lims=0.80,
        capex=6000000.0,
        permit_vel=34.0,
        shift_ratio=1.40,
        sla=52.0,
        description="Rose Park neighborhood with early-20th-century bungalows, mature tree canopy, and steady kitchen/bathroom renovation permits.",
        city_id="missoula",
    ),
    "River Road": SubmarketMeta(
        name="River Road",
        borough="WEST_MIDTOWN",
        lat=46.8520,
        lng=-114.0550,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.72,
        capex=4400000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=44.0,
        description="West-side river corridor of newer subdivisions and large-lot residential with new-build permitting volume.",
        city_id="missoula",
    ),
    "Moose Can Gully": SubmarketMeta(
        name="Moose Can Gully",
        borough="WEST_MIDTOWN",
        lat=46.8460,
        lng=-114.0520,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.70,
        capex=4000000.0,
        permit_vel=22.0,
        shift_ratio=1.30,
        sla=42.0,
        description="Southwest gully neighborhood of exurban subdivisions with well-septic permitting and rural character.",
        city_id="missoula",
    ),
    # ===================================================================
    # NORTHSIDE (3)
    # ===================================================================
    "Northside": SubmarketMeta(
        name="Northside",
        borough="NORTHSIDE",
        lat=46.8840,
        lng=-113.9960,
        zoom=14.5,
        pitch=46.0,
        base_lims=0.78,
        capex=5600000.0,
        permit_vel=32.0,
        shift_ratio=1.38,
        sla=50.0,
        description="North Missoula industrial-residential mix with the rail yard, Northside neighborhood, and warehouse-to-residential conversions.",
        city_id="missoula",
    ),
    "Grant Creek": SubmarketMeta(
        name="Grant Creek",
        borough="NORTHSIDE",
        lat=46.9100,
        lng=-114.0650,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.76,
        capex=5400000.0,
        permit_vel=28.0,
        shift_ratio=1.36,
        sla=48.0,
        description="Northern valley corridor with master-planned subdivisions, golf course adjacency, and hotel/commercial development.",
        city_id="missoula",
    ),
    "Marshall Canyon": SubmarketMeta(
        name="Marshall Canyon",
        borough="NORTHSIDE",
        lat=46.8870,
        lng=-114.0300,
        zoom=14.0,
        pitch=42.0,
        base_lims=0.74,
        capex=4800000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=46.0,
        description="Marshall Mountain foothills neighborhood with newer single-family construction and wildland-urban interface permitting.",
        city_id="missoula",
    ),
    # ===================================================================
    # RATTLESNAKE (3)
    # ===================================================================
    "Lower Rattlesnake": SubmarketMeta(
        name="Lower Rattlesnake",
        borough="RATTLESNAKE",
        lat=46.8870,
        lng=-113.9700,
        zoom=14.5,
        pitch=46.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=34.0,
        shift_ratio=1.40,
        sla=52.0,
        description="Established Rattlesnake Valley floor neighborhood with leafy streets, mid-century homes, and steady renovation permits.",
        city_id="missoula",
    ),
    "Upper Rattlesnake": SubmarketMeta(
        name="Upper Rattlesnake",
        borough="RATTLESNAKE",
        lat=46.9160,
        lng=-113.9550,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.78,
        capex=5800000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=50.0,
        description="Upper Rattlesnake Creek corridor with large estate lots, high-value remodels, and hillside building permits.",
        city_id="missoula",
    ),
    "Captain John Mullan": SubmarketMeta(
        name="Captain John Mullan",
        borough="RATTLESNAKE",
        lat=46.8940,
        lng=-113.9380,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.82,
        capex=6800000.0,
        permit_vel=36.0,
        shift_ratio=1.42,
        sla=54.0,
        description="East Mullan Road corridor with big-box retail, office parks, and the metro's largest commercial permit pipeline.",
        city_id="missoula",
    ),
    # ===================================================================
    # SOUTHEAST (2)
    # ===================================================================
    "Miller Creek": SubmarketMeta(
        name="Miller Creek",
        borough="SOUTHEAST",
        lat=46.8010,
        lng=-114.0550,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.72,
        capex=4600000.0,
        permit_vel=24.0,
        shift_ratio=1.32,
        sla=44.0,
        description="Southern exurban corridor along Miller Creek Road with new subdivisions, well/septic permits, and rural-residential growth.",
        city_id="missoula",
    ),
    "Farviews / Pattee Canyon": SubmarketMeta(
        name="Farviews / Pattee Canyon",
        borough="SOUTHEAST",
        lat=46.8360,
        lng=-113.9820,
        zoom=14.0,
        pitch=44.0,
        base_lims=0.74,
        capex=5000000.0,
        permit_vel=26.0,
        shift_ratio=1.34,
        sla=46.0,
        description="Southeast hillside neighborhood with Pattee Canyon recreation access, custom home construction, and forest-interface permits.",
        city_id="missoula",
    ),
}


MISSOULA_DIVISIONS: dict[str, BoroughMeta] = {
    "DOWNTOWN": BoroughMeta(
        name="DOWNTOWN",
        center_lat=46.8715,
        center_lng=-113.9955,
        zoom=14.5,
        bbox=MISSOULA_DIVISION_BBOXES["DOWNTOWN"],
        submarkets=[k for k, v in MISSOULA_SUBMARKETS.items() if v.borough == "DOWNTOWN"],
        city_id="missoula",
    ),
    "UNIVERSITY": BoroughMeta(
        name="UNIVERSITY",
        center_lat=46.8600,
        center_lng=-114.0000,
        zoom=14.0,
        bbox=MISSOULA_DIVISION_BBOXES["UNIVERSITY"],
        submarkets=[k for k, v in MISSOULA_SUBMARKETS.items() if v.borough == "UNIVERSITY"],
        city_id="missoula",
    ),
    "SOUTHSIDE": BoroughMeta(
        name="SOUTHSIDE",
        center_lat=46.8360,
        center_lng=-114.0250,
        zoom=13.5,
        bbox=MISSOULA_DIVISION_BBOXES["SOUTHSIDE"],
        submarkets=[k for k, v in MISSOULA_SUBMARKETS.items() if v.borough == "SOUTHSIDE"],
        city_id="missoula",
    ),
    "WEST_MIDTOWN": BoroughMeta(
        name="WEST_MIDTOWN",
        center_lat=46.8620,
        center_lng=-114.0350,
        zoom=13.0,
        bbox=MISSOULA_DIVISION_BBOXES["WEST_MIDTOWN"],
        submarkets=[k for k, v in MISSOULA_SUBMARKETS.items() if v.borough == "WEST_MIDTOWN"],
        city_id="missoula",
    ),
    "NORTHSIDE": BoroughMeta(
        name="NORTHSIDE",
        center_lat=46.8930,
        center_lng=-114.0300,
        zoom=13.0,
        bbox=MISSOULA_DIVISION_BBOXES["NORTHSIDE"],
        submarkets=[k for k, v in MISSOULA_SUBMARKETS.items() if v.borough == "NORTHSIDE"],
        city_id="missoula",
    ),
    "RATTLESNAKE": BoroughMeta(
        name="RATTLESNAKE",
        center_lat=46.8990,
        center_lng=-113.9620,
        zoom=13.0,
        bbox=MISSOULA_DIVISION_BBOXES["RATTLESNAKE"],
        submarkets=[k for k, v in MISSOULA_SUBMARKETS.items() if v.borough == "RATTLESNAKE"],
        city_id="missoula",
    ),
    "SOUTHEAST": BoroughMeta(
        name="SOUTHEAST",
        center_lat=46.8180,
        center_lng=-114.0180,
        zoom=13.0,
        bbox=MISSOULA_DIVISION_BBOXES["SOUTHEAST"],
        submarkets=[k for k, v in MISSOULA_SUBMARKETS.items() if v.borough == "SOUTHEAST"],
        city_id="missoula",
    ),
}

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-28 (US-235). Do not register 311 (none; county mirror is
# stale Pittsburgh), SLA (none), or deeds (no bulk feed).
# ---------------------------------------------------------------------------
MISSOULA_PERMITS_ENDPOINT = (
    "https://services.arcgis.com/HfwHS0BxZBQ1E5DY/arcgis/rest/services/"
    "AddressesWithPermits_mso/FeatureServer/0"
)

MISSOULA_FEED_SPECS: dict[str, dict[str, object]] = {
    "permits": {
        "endpoint": MISSOULA_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ApplicationDate",
        "id_keys": ["RecordID", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "needs_geocode": False,
            "oid_field": "OBJECTID",
            "max_record_count": 1000,
            "order_by": "ApplicationDate DESC",
            "field_map": PERMITS_FIELD_MAP,
        },
    },
}


def get_missoula_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for a (pending-spine) Missoula feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is
    absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in MISSOULA_FEED_SPECS:
        available = ", ".join(sorted(MISSOULA_FEED_SPECS))
        raise KeyError(
            f"'{MISSOULA_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = MISSOULA_FEED_SPECS[feed_name]
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
    metro_bbox=MISSOULA_METRO_BBOX,
    division_bboxes=MISSOULA_DIVISION_BBOXES,
    submarkets=MISSOULA_SUBMARKETS,
    divisions=MISSOULA_DIVISIONS,
    contains=is_in_missoula_metro,
)

__all__ = [
    "MISSOULA_CITY_ID",
    "MISSOULA_DIVISIONS",
    "MISSOULA_DIVISION_BBOXES",
    "MISSOULA_FEED_SPECS",
    "MISSOULA_GEOCODE_CONTEXT",
    "MISSOULA_METRO_BBOX",
    "MISSOULA_PERMITS_ENDPOINT",
    "MISSOULA_STATE_PLANE_CRS",
    "MISSOULA_STATE_PLANE_UNITS",
    "MISSOULA_SUBMARKETS",
    "REGISTRATION",
    "get_missoula_dataset",
    "is_in_missoula_metro",
]