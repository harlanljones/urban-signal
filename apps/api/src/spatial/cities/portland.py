"""Portland, Oregon spatial registry and geometry for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics, division
catalog, and geographic bounding boxes for the City of Portland, OR and the
greater metro (Vancouver, WA edge included loosely in the permissive metro bbox).

Portland registers as a **TWO-FEED partial city** like Los Angeles / Austin:

* PERMITS — Portland Maps / `data.portlandoregon.gov` building permits (Socrata).
* SLA — Oregon Liquor Control Commission (OLCC) liquor licenses.

DEEDS and COMPLAINTS_311 are deliberately **absent** from this leaf: no open
recorded-deeds endpoint is published for Multnomah County at the precision this
pipeline needs, and Portland 311 is a separate ticket. Like LA's absent DEEDS,
`get_dataset(PORTLAND, FeedType.DEEDS)` / `FeedType.COMPLAINTS_311` raise a
readable error once the spine lands the registry entry.

NOTE ON DISCOVERY (2026-08-26): the sandbox has no live network access, so the
exact Socrata 4x4 resource IDs for Portland permits and OLCC licenses are
**UNVERIFIED**. They are exposed as endpoint constants below and MUST be
confirmed by the spine owner before the REGISTRY entry is written. The field-map
shape, watermark columns, and geometry in this file are correct regardless of
the exact resource ID; only the endpoint strings are placeholders.
"""

from typing import Dict

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

# Greater Portland metro bounding box. Portland proper sits ~45.40–45.60 N,
# -122.75 to -122.55 W; the metro bbox is permissive and also admits the
# inner-east side and North Portland / St. Johns corridor.
PORTLAND_METRO_BBOX: Dict[str, float] = {
    "min_lat": 45.35,
    "max_lat": 45.65,
    "min_lng": -122.85,
    "max_lng": -122.45,
}

# 5 Portland division bounding boxes, hand-authored. Borough resolution at ingest
# comes from coordinates via get_division_for_coordinate (district strings in
# both feeds are free-text neighborhoods, not division names), so bboxes need
# only be sane and disjoint enough to resolve unambiguously near their centers.
PORTLAND_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_PEARL": {
        "min_lat": 45.50, "max_lat": 45.54,
        "min_lng": -122.70, "max_lng": -122.66,
    },
    "EASTSIDE_INNER": {
        "min_lat": 45.50, "max_lat": 45.55,
        "min_lng": -122.66, "max_lng": -122.58,
    },
    "NORTH_PORTLAND": {
        "min_lat": 45.55, "max_lat": 45.62,
        "min_lng": -122.75, "max_lng": -122.62,
    },
    "SOUTHWEST_PORTLAND": {
        "min_lat": 45.40, "max_lat": 45.50,
        "min_lng": -122.75, "max_lng": -122.68,
    },
    "SOUTHEAST_PORTLAND": {
        "min_lat": 45.40, "max_lat": 45.50,
        "min_lng": -122.68, "max_lng": -122.55,
    },
}


def is_in_portland_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Greater Portland Metropolitan bounds."""
    if lat is None or lng is None:
        return False
    return (
        PORTLAND_METRO_BBOX["min_lat"] <= lat <= PORTLAND_METRO_BBOX["max_lat"]
        and PORTLAND_METRO_BBOX["min_lng"] <= lng <= PORTLAND_METRO_BBOX["max_lng"]
    )


# Alias kept for symmetry with the other city modules' verbose spellings.
is_in_greater_portland_metro = is_in_portland_metro


PORTLAND_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_PEARL (3 Submarkets)
    # =======================================================================
    "Pearl District": SubmarketMeta(
        name="Pearl District",
        borough="DOWNTOWN_PEARL",
        lat=45.5280, lng=-122.6835,
        zoom=14.5, pitch=55.0, base_lims=0.91, capex=11000000.0,
        permit_vel=52.0, shift_ratio=1.62, sla=71.0,
        description="Former industrial district north of downtown converted to high-density residential and ground-floor retail and galleries.",
        city_id="portland",
    ),
    "Downtown & West End": SubmarketMeta(
        name="Downtown & West End",
        borough="DOWNTOWN_PEARL",
        lat=45.5200, lng=-122.6770,
        zoom=14.5, pitch=52.0, base_lims=0.89, capex=9800000.0,
        permit_vel=46.0, shift_ratio=1.57, sla=68.0,
        description="Central business core with office-to-residential conversions and hospitality along the transit mall.",
        city_id="portland",
    ),
    "Goose Hollow & Providence Park": SubmarketMeta(
        name="Goose Hollow & Providence Park",
        borough="DOWNTOWN_PEARL",
        lat=45.5160, lng=-122.6920,
        zoom=14.0, pitch=48.0, base_lims=0.84, capex=7200000.0,
        permit_vel=38.0, shift_ratio=1.49, sla=63.0,
        description="Stadium-adjacent residential hillside with mixed-use infill near the western downtown edge.",
        city_id="portland",
    ),
    # =======================================================================
    # EASTSIDE_INNER (3 Submarkets)
    # =======================================================================
    "Buckman & SE Hawthorne": SubmarketMeta(
        name="Buckman & SE Hawthorne",
        borough="EASTSIDE_INNER",
        lat=45.5120, lng=-122.6350,
        zoom=14.0, pitch=46.0, base_lims=0.86, capex=8600000.0,
        permit_vel=44.0, shift_ratio=1.54, sla=64.0,
        description="Dense inner-east neighborhood with retail corridors, ADU construction, and renovation-led permitting.",
        city_id="portland",
    ),
    "Kerns & Burnside East": SubmarketMeta(
        name="Kerns & Burnside East",
        borough="EASTSIDE_INNER",
        lat=45.5230, lng=-122.6400,
        zoom=14.0, pitch=46.0, base_lims=0.83, capex=6400000.0,
        permit_vel=40.0, shift_ratio=1.51, sla=61.0,
        description="Transit-adjacent east-burnside corridor with mid-rise multifamily replacing single-story commercial.",
        city_id="portland",
    ),
    "Laurelhurst & NE Broadway": SubmarketMeta(
        name="Laurelhurst & NE Broadway",
        borough="EASTSIDE_INNER",
        lat=45.5300, lng=-122.6200,
        zoom=13.5, pitch=44.0, base_lims=0.82, capex=6100000.0,
        permit_vel=33.0, shift_ratio=1.46, sla=58.0,
        description="Streetcar-era bungalow district meeting the NE retail spine, with renovation-heavy permits.",
        city_id="portland",
    ),
    # =======================================================================
    # NORTH_PORTLAND (3 Submarkets)
    # =======================================================================
    "Eliot & N Williams": SubmarketMeta(
        name="Eliot & N Williams",
        borough="NORTH_PORTLAND",
        lat=45.5600, lng=-122.6680,
        zoom=13.5, pitch=44.0, base_lims=0.80, capex=6800000.0,
        permit_vel=48.0, shift_ratio=1.55, sla=60.0,
        description="Rapidly densifying north corridor with infill multifamily along the N Williams bike/transit spine.",
        city_id="portland",
    ),
    "Boise & N Mississippi": SubmarketMeta(
        name="Boise & N Mississippi",
        borough="NORTH_PORTLAND",
        lat=45.5720, lng=-122.6750,
        zoom=13.5, pitch=42.0, base_lims=0.78, capex=5600000.0,
        permit_vel=36.0, shift_ratio=1.47, sla=56.0,
        description="Historic Albina bungalow stock under gentle upzoning pressure near the Mississippi arts district.",
        city_id="portland",
    ),
    "St Johns": SubmarketMeta(
        name="St Johns",
        borough="NORTH_PORTLAND",
        lat=45.5850, lng=-122.7480,
        zoom=13.0, pitch=40.0, base_lims=0.70, capex=3900000.0,
        permit_vel=22.0, shift_ratio=1.32, sla=47.0,
        description="Formerly independent north Portland town with small-lot infill and a village-scale commercial core.",
        city_id="portland",
    ),
    # =======================================================================
    # SOUTHWEST_PORTLAND (3 Submarkets)
    # =======================================================================
    "South Waterfront & OHSU": SubmarketMeta(
        name="South Waterfront & OHSU",
        borough="SOUTHWEST_PORTLAND",
        lat=45.4980, lng=-122.6900,
        zoom=14.0, pitch=50.0, base_lims=0.88, capex=10500000.0,
        permit_vel=50.0, shift_ratio=1.6, sla=66.0,
        description="OHSU-anchored high-rise academic medical district with continued tower construction on the Willamette's west bank.",
        city_id="portland",
    ),
    "Hillsdale & SW Macadam": SubmarketMeta(
        name="Hillsdale & SW Macadam",
        borough="SOUTHWEST_PORTLAND",
        lat=45.4700, lng=-122.6950,
        zoom=13.0, pitch=40.0, base_lims=0.76, capex=4900000.0,
        permit_vel=26.0, shift_ratio=1.38, sla=50.0,
        description="Southwest hills neighborhood with teardown/rebuild pressure and strict slope ordinances.",
        city_id="portland",
    ),
    "Multnomah Village": SubmarketMeta(
        name="Multnomah Village",
        borough="SOUTHWEST_PORTLAND",
        lat=45.4550, lng=-122.7200,
        zoom=13.0, pitch=38.0, base_lims=0.72, capex=4200000.0,
        permit_vel=23.0, shift_ratio=1.34, sla=48.0,
        description="Inner-southwest village node with indie retail and renovation-led permits.",
        city_id="portland",
    ),
    # =======================================================================
    # SOUTHEAST_PORTLAND (2 Submarkets)
    # =======================================================================
    "Mount Tabor & SE Belmont": SubmarketMeta(
        name="Mount Tabor & SE Belmont",
        borough="SOUTHEAST_PORTLAND",
        lat=45.4950, lng=-122.6250,
        zoom=13.5, pitch=42.0, base_lims=0.81, capex=6500000.0,
        permit_vel=38.0, shift_ratio=1.47, sla=59.0,
        description="Hill-adjacent east-side neighborhood with ADU construction and corridor multifamily.",
        city_id="portland",
    ),
    "Woodstock & SE Foster": SubmarketMeta(
        name="Woodstock & SE Foster",
        borough="SOUTHEAST_PORTLAND",
        lat=45.4750, lng=-122.5900,
        zoom=13.0, pitch=38.0, base_lims=0.66, capex=3300000.0,
        permit_vel=27.0, shift_ratio=1.3, sla=44.0,
        description="Outer-southeast arterial with affordability-pressure infill and small-lot development.",
        city_id="portland",
    ),
}


PORTLAND_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_PEARL": BoroughMeta(
        name="DOWNTOWN_PEARL",
        center_lat=45.521, center_lng=-122.684,
        zoom=13.5, bbox=PORTLAND_DIVISION_BBOXES["DOWNTOWN_PEARL"],
        submarkets=[k for k, v in PORTLAND_SUBMARKETS.items() if v.borough == "DOWNTOWN_PEARL"],
        city_id="portland",
    ),
    "EASTSIDE_INNER": BoroughMeta(
        name="EASTSIDE_INNER",
        center_lat=45.522, center_lng=-122.631,
        zoom=13.0, bbox=PORTLAND_DIVISION_BBOXES["EASTSIDE_INNER"],
        submarkets=[k for k, v in PORTLAND_SUBMARKETS.items() if v.borough == "EASTSIDE_INNER"],
        city_id="portland",
    ),
    "NORTH_PORTLAND": BoroughMeta(
        name="NORTH_PORTLAND",
        center_lat=45.572, center_lng=-122.700,
        zoom=12.5, bbox=PORTLAND_DIVISION_BBOXES["NORTH_PORTLAND"],
        submarkets=[k for k, v in PORTLAND_SUBMARKETS.items() if v.borough == "NORTH_PORTLAND"],
        city_id="portland",
    ),
    "SOUTHWEST_PORTLAND": BoroughMeta(
        name="SOUTHWEST_PORTLAND",
        center_lat=45.474, center_lng=-122.702,
        zoom=12.5, bbox=PORTLAND_DIVISION_BBOXES["SOUTHWEST_PORTLAND"],
        submarkets=[k for k, v in PORTLAND_SUBMARKETS.items() if v.borough == "SOUTHWEST_PORTLAND"],
        city_id="portland",
    ),
    "SOUTHEAST_PORTLAND": BoroughMeta(
        name="SOUTHEAST_PORTLAND",
        center_lat=45.490, center_lng=-122.605,
        zoom=12.5, bbox=PORTLAND_DIVISION_BBOXES["SOUTHEAST_PORTLAND"],
        submarkets=[k for k, v in PORTLAND_SUBMARKETS.items() if v.borough == "SOUTHEAST_PORTLAND"],
        city_id="portland",
    ),
}

# Verbose aliases mirroring the other city modules' */*_META pairs.
GREATER_PORTLAND_METRO_BBOX = PORTLAND_METRO_BBOX
PDX_DIVISION_BBOXES = PORTLAND_DIVISION_BBOXES
PDX_SUBMARKETS = PORTLAND_SUBMARKETS
PDX_DIVISIONS = PORTLAND_DIVISIONS


# =======================================================================
# Feed specifications (spine-foldable)
#
# These are the PERMITS + SLA dataset specs for Portland, expressed as plain
# data so the spine can fold them into REGISTRY via get_dataset() without this
# leaf importing the registry (no circular import). Keys mirror DatasetSpec
# fields. Endpoint constants are UNVERIFIED placeholders — see module docstring.
# =======================================================================

PORTLAND_PERMITS_ENDPOINT: str = (
    "https://www.portlandmaps.com/od/rest/services/"
    "COP_OpenData_PlanningDevelopment/MapServer/89"
)
PORTLAND_SLA_ENDPOINT: str = (
    "https://data.oregon.gov/resource/qad4-bnxp.json"
)

PORTLAND_PERMITS_FIELD_MAP: Dict[str, list] = {
    "job_id": ["FOLDERNUMB", "OBJECTID", "permit_number"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
    "issuance_date": ["ISSUEDATE", "issue_date"],
    "filing_date": ["INDATE", "application_date"],
    "cost": ["VALUATION", "estimated_cost", "total_cost"],
    "status": ["STATUS", "status"],
    "zipcode": ["zip_code"],
    "job_type": ["NEWCLASS", "NEWTYPE", "WORKDESC", "permit_type", "permit_subtype"],
    "address_street": ["PROP_ADDRE", "address"],
    "borough": ["NBRHOOD", "PDXBND", "district", "neighborhood"],
    "proposed_units": ["NEW_UNITS", "proposed_units"],
    "proposed_stories": ["proposed_stories", "number_of_stories"],
}

PORTLAND_SLA_FIELD_MAP: Dict[str, list] = {
    "license_id": ["license_number", "trade_name", "address"],
    "license_type": ["license_type", "application_type"],
    "dba": ["dba", "trade_name", "doing_business_as"],
    "premises_name": ["business_name", "licensee_name", "trade_name"],
    "effective_date": ["date_received", "issue_date", "effective_date"],
    "expiration_date": ["expiration_date"],
    "status": ["application_status", "license_status", "status"],
    "address_street": ["address", "premise_address"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
    "borough": ["district", "police_district"],
}

# Spine-foldable spec data. `field_map` references the maps above.
PORTLAND_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": PORTLAND_PERMITS_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "ISSUEDATE",
        "id_keys": ["FOLDERNUMB", "OBJECTID"],
        "topic_key": "topic_permits",
        "interval_seconds": 300.0,
        "producer_key": "permits",
        "field_map": PORTLAND_PERMITS_FIELD_MAP,
        "expected_cadence_days": 7,
        "extra": {"oid_field": "OBJECTID", "max_record_count": 2000, "order_by": "ISSUEDATE DESC", "scope": "Portland residential building permits"},
    },
    "sla": {
        "endpoint": PORTLAND_SLA_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "date_received",
        "id_keys": ["trade_name", "address"],
        "topic_key": "topic_sla",
        "interval_seconds": 600.0,
        "producer_key": "sla",
        "field_map": PORTLAND_SLA_FIELD_MAP,
        "expected_cadence_days": 7,
        "extra": {"needs_geocode": True, "scope": "Oregon OLCC liquor applications received (address-only Portland rows)"},
    },
}
