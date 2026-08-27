"""Albuquerque / Bernalillo County spatial registry and geometry.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the City of Albuquerque
and inner Bernalillo County.

Albuquerque is a ONE-FEED PARTIAL metro like Boise / Austin / LA: PERMITS
only, from the daily UTF-8 CSV dump at data.cabq.gov. The dump is
address-only and therefore declares ``needs_geocode`` (ADR 0004). 311 / SLA
/ DEEDS are absent (CRM not queryable, business-registration dump frozen,
no deed transaction stream).

Live-probe caveats that define this leaf (2026-08-27, US-205):

* Platform is a static CSV, not CKAN. ``CSVClient`` covers the file.
* ``IssueDate`` is text ``YYYYMMDD``. Four future sentinels share
  ``20261224`` and must be excluded from the high watermark.
* Status mix is Complete / Expired / Issued; drop Expired (majority of
  the dump) at registration. CSVClient has no ``IN`` predicate, so the
  spine ``where`` is ``Status NOT IN ('Expired')``.
* AGIS ``City_Building_Permits`` FeatureServer is frozen (max DateIssued
  2025-01-16) and must not be registered.
"""

from typing import Any, Dict, List

from src.producers.field_maps_albuquerque import (
    ALBUQUERQUE_FIELD_MAPS,
    ALBUQUERQUE_GEOCODE_CONTEXT,
    ALBUQUERQUE_PERMITS_FIELD_MAP,
    FIELD_MAP,
    GEOCODE_CONTEXT,
)
from src.spatial.submarkets import BoroughMeta, SubmarketMeta

ALBUQUERQUE_CITY_ID: str = "albuquerque"

# City of Albuquerque / inner Bernalillo. Permits are municipal (not
# county-wide); the bbox only has to keep live CABQ samples inside.
# Downtown ~35.0844, -106.6504; west volcanoes ~-106.82; east foothills
# ~-106.49; Alameda north ~35.21; Mesa del Sol south ~34.96.
ALBUQUERQUE_METRO_BBOX: Dict[str, float] = {
    "min_lat": 34.94,
    "max_lat": 35.22,
    "min_lng": -106.85,
    "max_lng": -106.47,
}

# 6 division bounding boxes. Approximate hand-authored geographies;
# borough resolution at ingest comes from coordinates via
# get_division_for_coordinate, so bboxes need only be sane and contain
# their own submarket centers.
ALBUQUERQUE_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "DOWNTOWN_CORE": {
        "min_lat": 35.06,
        "max_lat": 35.12,
        "min_lng": -106.70,
        "max_lng": -106.62,
    },
    "NOB_HILL_UNM": {
        "min_lat": 35.06,
        "max_lat": 35.11,
        "min_lng": -106.63,
        "max_lng": -106.54,
    },
    "NORTHEAST_HEIGHTS": {
        "min_lat": 35.09,
        "max_lat": 35.18,
        "min_lng": -106.60,
        "max_lng": -106.48,
    },
    "NORTH_VALLEY": {
        "min_lat": 35.12,
        "max_lat": 35.22,
        "min_lng": -106.70,
        "max_lng": -106.58,
    },
    "WEST_MESA": {
        "min_lat": 35.08,
        "max_lat": 35.20,
        "min_lng": -106.85,
        "max_lng": -106.68,
    },
    "SOUTH_VALLEY": {
        "min_lat": 34.94,
        "max_lat": 35.07,
        "min_lng": -106.75,
        "max_lng": -106.55,
    },
}


def is_in_albuquerque_metro(lat: float, lng: float) -> bool:
    """Check if a coordinate lies within the Albuquerque / Bernalillo bounds."""
    if lat is None or lng is None:
        return False
    return (
        ALBUQUERQUE_METRO_BBOX["min_lat"] <= lat <= ALBUQUERQUE_METRO_BBOX["max_lat"]
        and ALBUQUERQUE_METRO_BBOX["min_lng"] <= lng <= ALBUQUERQUE_METRO_BBOX["max_lng"]
    )


is_in_greater_albuquerque_metro = is_in_albuquerque_metro


def compose_permit_address(row: Dict[str, Any]) -> str:
    """Join CABQ site parts into one geocode query.

    Probe form: ``{SiteNumber} {SiteStreet} {SiteStreetType}
    {SiteStreetDirectional}, Albuquerque, NM {SiteZip}``. Accepts original
    or CSVClient-normalized keys.
    """

    def _first(*keys: str) -> str:
        for key in keys:
            val = row.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
        return ""

    street = " ".join(
        part
        for part in (
            _first("sitenumber", "SiteNumber"),
            _first("sitestreet", "SiteStreet"),
            _first("sitestreettype", "SiteStreetType"),
            _first("sitestreetdirectional", "SiteStreetDirectional"),
        )
        if part
    )
    zipcode = _first("sitezip", "SiteZip")
    if street and zipcode:
        return f"{street}, Albuquerque, NM {zipcode}"
    if street:
        return f"{street}, Albuquerque, NM"
    if zipcode:
        return f"Albuquerque, NM {zipcode}"
    return ""


ALBUQUERQUE_SUBMARKETS: Dict[str, SubmarketMeta] = {
    # =======================================================================
    # DOWNTOWN_CORE (3)
    # =======================================================================
    "Downtown Albuquerque": SubmarketMeta(
        name="Downtown Albuquerque",
        borough="DOWNTOWN_CORE",
        lat=35.0844,
        lng=-106.6504,
        zoom=14.5,
        pitch=55.0,
        base_lims=0.88,
        capex=9200000.0,
        permit_vel=44.0,
        shift_ratio=1.52,
        sla=64.0,
        description="Civic and rail-runner core around Central and 2nd with office-to-residential conversions and the densest issued-permit volume.",
        city_id="albuquerque",
    ),
    "Old Town": SubmarketMeta(
        name="Old Town",
        borough="DOWNTOWN_CORE",
        lat=35.0964,
        lng=-106.6698,
        zoom=15.0,
        pitch=50.0,
        base_lims=0.84,
        capex=6800000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=56.0,
        description="Plaza-centered historic adobe stock with renovation-heavy permitting and preservation overlays west of downtown.",
        city_id="albuquerque",
    ),
    "Barelas": SubmarketMeta(
        name="Barelas",
        borough="DOWNTOWN_CORE",
        lat=35.0735,
        lng=-106.6565,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.78,
        capex=5400000.0,
        permit_vel=31.0,
        shift_ratio=1.42,
        sla=52.0,
        description="South-of-downtown rail and warehouse district with adaptive reuse along 4th Street and the Barelas-South Valley seam.",
        city_id="albuquerque",
    ),
    # =======================================================================
    # NOB_HILL_UNM (3)
    # =======================================================================
    "Nob Hill": SubmarketMeta(
        name="Nob Hill",
        borough="NOB_HILL_UNM",
        lat=35.0808,
        lng=-106.6056,
        zoom=14.5,
        pitch=50.0,
        base_lims=0.86,
        capex=7600000.0,
        permit_vel=38.0,
        shift_ratio=1.48,
        sla=60.0,
        description="Route 66 commercial spine east of downtown with storefront renovation, ADU pressure, and the metro's densest street-retail permits.",
        city_id="albuquerque",
    ),
    "UNM / University": SubmarketMeta(
        name="UNM / University",
        borough="NOB_HILL_UNM",
        lat=35.0843,
        lng=-106.6198,
        zoom=14.5,
        pitch=48.0,
        base_lims=0.83,
        capex=8100000.0,
        permit_vel=41.0,
        shift_ratio=1.50,
        sla=62.0,
        description="Campus-adjacent rental and medical-office stock with student-housing infill and hospital-corridor permitting.",
        city_id="albuquerque",
    ),
    "International District": SubmarketMeta(
        name="International District",
        borough="NOB_HILL_UNM",
        lat=35.0710,
        lng=-106.5610,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.70,
        capex=3900000.0,
        permit_vel=24.0,
        shift_ratio=1.28,
        sla=44.0,
        description="Central-east corridor along Zuni and Central with small-lot commercial rehab and high 311-to-permit imbalance.",
        city_id="albuquerque",
    ),
    # =======================================================================
    # NORTHEAST_HEIGHTS (3)
    # =======================================================================
    "Uptown": SubmarketMeta(
        name="Uptown",
        borough="NORTHEAST_HEIGHTS",
        lat=35.1040,
        lng=-106.5710,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.85,
        capex=8800000.0,
        permit_vel=40.0,
        shift_ratio=1.46,
        sla=61.0,
        description="Louisiana and I-40 office-retail node with mixed-use tower conversions and the Heights' densest commercial permit pipeline.",
        city_id="albuquerque",
    ),
    "Far Northeast Heights": SubmarketMeta(
        name="Far Northeast Heights",
        borough="NORTHEAST_HEIGHTS",
        lat=35.1450,
        lng=-106.5250,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.80,
        capex=6200000.0,
        permit_vel=33.0,
        shift_ratio=1.40,
        sla=55.0,
        description="Post-war tract grid toward the Sandias with teardown/rebuild and ADU permitting on large lots.",
        city_id="albuquerque",
    ),
    "Foothills": SubmarketMeta(
        name="Foothills",
        borough="NORTHEAST_HEIGHTS",
        lat=35.0960,
        lng=-106.4980,
        zoom=13.0,
        pitch=44.0,
        base_lims=0.87,
        capex=9400000.0,
        permit_vel=26.0,
        shift_ratio=1.36,
        sla=50.0,
        description="High-value east-edge estate stock under Open Space constraints, dominated by renovation rather than new construction.",
        city_id="albuquerque",
    ),
    # =======================================================================
    # NORTH_VALLEY (3)
    # =======================================================================
    "North Valley": SubmarketMeta(
        name="North Valley",
        borough="NORTH_VALLEY",
        lat=35.1610,
        lng=-106.6420,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.82,
        capex=7100000.0,
        permit_vel=32.0,
        shift_ratio=1.41,
        sla=54.0,
        description="Acequia-irrigated lots along 4th Street with estate infill, horse-property splits, and Los Ranchos-adjacent permitting.",
        city_id="albuquerque",
    ),
    "Journal Center": SubmarketMeta(
        name="Journal Center",
        borough="NORTH_VALLEY",
        lat=35.1480,
        lng=-106.5890,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.79,
        capex=6500000.0,
        permit_vel=36.0,
        shift_ratio=1.44,
        sla=57.0,
        description="I-25 north employment campus with office, industrial, and limited residential conversion permits.",
        city_id="albuquerque",
    ),
    "Alameda": SubmarketMeta(
        name="Alameda",
        borough="NORTH_VALLEY",
        lat=35.1920,
        lng=-106.6460,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.76,
        capex=4800000.0,
        permit_vel=22.0,
        shift_ratio=1.30,
        sla=46.0,
        description="Northern city-limit villages along the Rio Grande with sparse permitting and agricultural-lot pressure.",
        city_id="albuquerque",
    ),
    # =======================================================================
    # WEST_MESA (3)
    # =======================================================================
    "West Central / Atrisco": SubmarketMeta(
        name="West Central / Atrisco",
        borough="WEST_MESA",
        lat=35.0950,
        lng=-106.7220,
        zoom=13.5,
        pitch=44.0,
        base_lims=0.74,
        capex=5100000.0,
        permit_vel=29.0,
        shift_ratio=1.35,
        sla=48.0,
        description="Central Avenue west of the river with corridor commercial rehab and Atrisco-grant residential infill.",
        city_id="albuquerque",
    ),
    "Taylor Ranch / Petroglyph": SubmarketMeta(
        name="Taylor Ranch / Petroglyph",
        borough="WEST_MESA",
        lat=35.1580,
        lng=-106.7320,
        zoom=13.5,
        pitch=42.0,
        base_lims=0.81,
        capex=6700000.0,
        permit_vel=37.0,
        shift_ratio=1.45,
        sla=58.0,
        description="Northwest mesa master-planned tracts against Petroglyph National Monument with high single-family permit velocity.",
        city_id="albuquerque",
    ),
    "Volcano Cliffs": SubmarketMeta(
        name="Volcano Cliffs",
        borough="WEST_MESA",
        lat=35.1680,
        lng=-106.7620,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.77,
        capex=5800000.0,
        permit_vel=34.0,
        shift_ratio=1.43,
        sla=53.0,
        description="Far-west escarpment growth edge with new-construction permitting on volcanic-mesa lots.",
        city_id="albuquerque",
    ),
    # =======================================================================
    # SOUTH_VALLEY (3)
    # =======================================================================
    "South Valley": SubmarketMeta(
        name="South Valley",
        borough="SOUTH_VALLEY",
        lat=35.0220,
        lng=-106.6820,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.72,
        capex=4300000.0,
        permit_vel=25.0,
        shift_ratio=1.32,
        sla=46.0,
        description="Unincorporated-adjacent south valley with agricultural-lot splits, owner-builder permits, and Isleta-road commercial.",
        city_id="albuquerque",
    ),
    "Sunport / Airport": SubmarketMeta(
        name="Sunport / Airport",
        borough="SOUTH_VALLEY",
        lat=35.0410,
        lng=-106.6090,
        zoom=13.0,
        pitch=42.0,
        base_lims=0.75,
        capex=7200000.0,
        permit_vel=30.0,
        shift_ratio=1.38,
        sla=51.0,
        description="Airport and Yale industrial belt with warehouse, hotel, and limited residential permitting south of Gibson.",
        city_id="albuquerque",
    ),
    "Mesa del Sol": SubmarketMeta(
        name="Mesa del Sol",
        borough="SOUTH_VALLEY",
        lat=34.9950,
        lng=-106.6220,
        zoom=13.0,
        pitch=40.0,
        base_lims=0.80,
        capex=8600000.0,
        permit_vel=39.0,
        shift_ratio=1.47,
        sla=59.0,
        description="Master-planned south mesa with the city's largest greenfield residential and employment-center pipeline.",
        city_id="albuquerque",
    ),
}


ALBUQUERQUE_DIVISIONS: Dict[str, BoroughMeta] = {
    "DOWNTOWN_CORE": BoroughMeta(
        name="DOWNTOWN_CORE",
        center_lat=35.084,
        center_lng=-106.650,
        zoom=13.5,
        bbox=ALBUQUERQUE_DIVISION_BBOXES["DOWNTOWN_CORE"],
        submarkets=[k for k, v in ALBUQUERQUE_SUBMARKETS.items() if v.borough == "DOWNTOWN_CORE"],
        city_id="albuquerque",
    ),
    "NOB_HILL_UNM": BoroughMeta(
        name="NOB_HILL_UNM",
        center_lat=35.081,
        center_lng=-106.605,
        zoom=13.0,
        bbox=ALBUQUERQUE_DIVISION_BBOXES["NOB_HILL_UNM"],
        submarkets=[k for k, v in ALBUQUERQUE_SUBMARKETS.items() if v.borough == "NOB_HILL_UNM"],
        city_id="albuquerque",
    ),
    "NORTHEAST_HEIGHTS": BoroughMeta(
        name="NORTHEAST_HEIGHTS",
        center_lat=35.125,
        center_lng=-106.545,
        zoom=12.5,
        bbox=ALBUQUERQUE_DIVISION_BBOXES["NORTHEAST_HEIGHTS"],
        submarkets=[k for k, v in ALBUQUERQUE_SUBMARKETS.items() if v.borough == "NORTHEAST_HEIGHTS"],
        city_id="albuquerque",
    ),
    "NORTH_VALLEY": BoroughMeta(
        name="NORTH_VALLEY",
        center_lat=35.165,
        center_lng=-106.640,
        zoom=12.5,
        bbox=ALBUQUERQUE_DIVISION_BBOXES["NORTH_VALLEY"],
        submarkets=[k for k, v in ALBUQUERQUE_SUBMARKETS.items() if v.borough == "NORTH_VALLEY"],
        city_id="albuquerque",
    ),
    "WEST_MESA": BoroughMeta(
        name="WEST_MESA",
        center_lat=35.140,
        center_lng=-106.745,
        zoom=12.5,
        bbox=ALBUQUERQUE_DIVISION_BBOXES["WEST_MESA"],
        submarkets=[k for k, v in ALBUQUERQUE_SUBMARKETS.items() if v.borough == "WEST_MESA"],
        city_id="albuquerque",
    ),
    "SOUTH_VALLEY": BoroughMeta(
        name="SOUTH_VALLEY",
        center_lat=35.020,
        center_lng=-106.640,
        zoom=12.0,
        bbox=ALBUQUERQUE_DIVISION_BBOXES["SOUTH_VALLEY"],
        submarkets=[k for k, v in ALBUQUERQUE_SUBMARKETS.items() if v.borough == "SOUTH_VALLEY"],
        city_id="albuquerque",
    ),
}

GREATER_ALBUQUERQUE_METRO_BBOX = ALBUQUERQUE_METRO_BBOX
ABQ_DIVISION_BBOXES = ALBUQUERQUE_DIVISION_BBOXES
ABQ_SUBMARKETS = ALBUQUERQUE_SUBMARKETS
ABQ_DIVISIONS = ALBUQUERQUE_DIVISIONS

# ---------------------------------------------------------------------------
# Feed specs (leaf-local; the spine copies these into REGISTRY).
# Probed 2026-08-27 against data.cabq.gov. PERMITS only.
# ---------------------------------------------------------------------------
ALBUQUERQUE_PERMITS_ENDPOINT = (
    "https://data.cabq.gov/business/buildingpermits/BuildingPermitsCABQ-en-us.csv"
)

# CSVClient has no IN predicate (unknown clauses are a silent no-op). Drop
# the Expired majority with NOT IN; Issued+Complete (and a small remainder)
# pass. Do not ship ``Status IN ('Issued','Complete')`` until csv_client
# grows IN — St. Louis owns that file this wave.
ALBUQUERQUE_PERMITS_WHERE = "Status NOT IN ('Expired')"

ALBUQUERQUE_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "permits": {
        "endpoint": ALBUQUERQUE_PERMITS_ENDPOINT,
        "platform": "csv",
        "watermark_col": "IssueDate",
        "id_keys": ["ApplicationPermitNumber"],
        "topic_key": "topic_permits",
        "interval_seconds": 1800.0,
        "producer_key": "permits",
        "extra": {
            "expected_cadence_days": 1,
            "watermark_type": "text",
            "watermark_format": "%Y%m%d",
            "watermark_exclude": ["20261224"],
            "where": ALBUQUERQUE_PERMITS_WHERE,
            "needs_geocode": True,
            "geocode_context": ALBUQUERQUE_GEOCODE_CONTEXT,
            "field_map": ALBUQUERQUE_PERMITS_FIELD_MAP,
        },
    },
}


def get_albuquerque_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns the spec for the registered Albuquerque feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is absent.
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in ALBUQUERQUE_FEED_SPECS:
        available = ", ".join(sorted(ALBUQUERQUE_FEED_SPECS)) or "none"
        raise KeyError(
            f"'{ALBUQUERQUE_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = ALBUQUERQUE_FEED_SPECS[feed_name]
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
    metro_bbox=ALBUQUERQUE_METRO_BBOX,
    division_bboxes=ALBUQUERQUE_DIVISION_BBOXES,
    submarkets=ALBUQUERQUE_SUBMARKETS,
    divisions=ALBUQUERQUE_DIVISIONS,
    contains=is_in_albuquerque_metro,
)

__all__ = [
    "ABQ_DIVISION_BBOXES",
    "ABQ_DIVISIONS",
    "ABQ_SUBMARKETS",
    "ALBUQUERQUE_CITY_ID",
    "ALBUQUERQUE_DIVISION_BBOXES",
    "ALBUQUERQUE_DIVISIONS",
    "ALBUQUERQUE_FEED_SPECS",
    "ALBUQUERQUE_FIELD_MAPS",
    "ALBUQUERQUE_GEOCODE_CONTEXT",
    "ALBUQUERQUE_METRO_BBOX",
    "ALBUQUERQUE_PERMITS_ENDPOINT",
    "ALBUQUERQUE_PERMITS_FIELD_MAP",
    "ALBUQUERQUE_PERMITS_WHERE",
    "ALBUQUERQUE_SUBMARKETS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "GREATER_ALBUQUERQUE_METRO_BBOX",
    "REGISTRATION",
    "compose_permit_address",
    "get_albuquerque_dataset",
    "is_in_albuquerque_metro",
    "is_in_greater_albuquerque_metro",
]
