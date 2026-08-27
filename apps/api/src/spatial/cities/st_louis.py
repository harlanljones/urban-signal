"""St. Louis Metro Submarket Registry and Spatial Layer for Urban Signal.

Provides neighborhood metadata, camera positioning, investment metrics,
division catalog, and geographic bounding boxes for the **independent City of
St. Louis, MO** (not St. Louis County).

St. Louis is a THREE-FEED PARTIAL metro like Austin/LA/San Diego: COMPLAINTS_311
(CSB yearly CSV inside ``csb.zip``), PERMITS (ColdFusion 30-day building-permit
CSV), and SLA (Excise Commissioner liquor snapshot). DEEDS are absent — the
assessor parcel-sales watermark lags six months (SaleDate max 2026-02-11).

Live-probe caveats that define this leaf (2026-08-27, US-200):

* 311 native ``SRX``/``SRY`` are **EPSG:3857 Web Mercator meters**, not WGS84
  degrees (Boston-SLA lesson). ``mercator_xy_to_wgs84`` lives in this city
  module because ``geo_utils.py`` is spine. Wiring the helper into
  ``complaints_311_producer.py`` is a later spine hold; until then the shared
  parser must not ingest raw SRX/SRY as lat/lng. ``PROBADDRESS`` is the ADR-0004
  fallback (35 rows, 0.04%, lack XY).
* 311 is a D3 zip of year files (``2008.csv``…``2026.csv`` inside one
  ``csb.zip``). ``CSVClient`` accepts ``zip_member='2026.csv'``; the scheduler
  does not yet forward that kwarg (spine).
* PERMITS ``ISSUEDATE`` is month-name text (``August, 07 2026 00:00:00``),
  rolling 30-day window, ~20-day publish lag, address-only
  (``needs_geocode=True``, ``expected_cadence_days=21``). No permit number —
  composite id is address+issuedate+applicationdescription. Do not register
  frozen ArcGIS Building_Permits (newest 2025-03-05) or trades APIs.
* SLA is liquor-only (Baltimore precedent): snapshot, ``STATUS_CODE='ACTIVE'``,
  drop expiration sentinels year 1969/3027. Not general business licenses.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, Mapping

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

ST_LOUIS_CITY_ID: str = "st_louis"
ST_LOUIS_ALIASES: tuple[str, ...] = (
    "st_louis",
    "stl",
    "saint_louis",
    "st-louis",
    "st louis",
)
ST_LOUIS_GEOCODE_CONTEXT: str = "St. Louis, MO"
ST_LOUIS_JOB_SUFFIX: str = "stl"

# Spherical mercator radius used by EPSG:3857 (not WGS84 ellipsoidal).
_WGS84_SPHERE_R = 6378137.0
_EXCISE_SENTINEL_YEARS = frozenset({1969, 3027})

# Independent City of St. Louis only. West edge is Skinker / the city-county
# line (Clayton at ~-90.338 stays out). East edge is the Mississippi
# (East St. Louis, IL at ~-90.151 stays out).
ST_LOUIS_METRO_BBOX: Dict[str, float] = {
    "min_lat": 38.53,
    "max_lat": 38.775,
    "min_lng": -90.322,
    "max_lng": -90.166,
}

ST_LOUIS_DIVISION_BBOXES: Dict[str, Dict[str, float]] = {
    "STL_CORE": {
        "min_lat": 38.57,
        "max_lat": 38.68,
        "min_lng": -90.30,
        "max_lng": -90.18,
    },
}


def is_in_st_louis_metro(lat: float, lng: float) -> bool:
    """Return whether a coordinate lies inside the City of St. Louis extent."""
    if lat is None or lng is None:
        return False
    return (
        ST_LOUIS_METRO_BBOX["min_lat"] <= lat <= ST_LOUIS_METRO_BBOX["max_lat"]
        and ST_LOUIS_METRO_BBOX["min_lng"] <= lng <= ST_LOUIS_METRO_BBOX["max_lng"]
    )


is_in_greater_st_louis_metro = is_in_st_louis_metro


def is_wgs84_degrees(lat: Any, lng: Any) -> bool:
    """True when ``lat``/``lng`` could be geographic degrees (not projected XY)."""
    try:
        return abs(float(lat)) <= 90.0 and abs(float(lng)) <= 180.0
    except (TypeError, ValueError):
        return False


def mercator_xy_to_wgs84(x: Any, y: Any) -> tuple[float, float]:
    """Convert EPSG:3857 Web Mercator meters to WGS84 ``(lat, lng)`` degrees.

    CSB ``SRX``/``SRY`` are spherical mercator, not geographic degrees. Do not
    pass those columns to H3 as lat/lng (Boston-SLA lesson). Wiring this helper
    into ``complaints_311_producer.py`` is a later spine hold — the shared
    parser currently has no ``src_crs`` path.
    """
    easting = float(x)
    northing = float(y)
    lng = (easting / _WGS84_SPHERE_R) * (180.0 / math.pi)
    lat = (
        2.0 * math.atan(math.exp(northing / _WGS84_SPHERE_R)) - math.pi / 2.0
    ) * (180.0 / math.pi)
    return lat, lng


def attach_wgs84_from_srxy(row: Mapping[str, Any]) -> dict[str, Any]:
    """Leaf-local stand-in for the spine 311 producer CRS transform.

    Copies the row and writes WGS84 ``latitude``/``longitude`` from ``srx``/
    ``sry`` so the shared parser can ingest the row in unit tests. Production
    wiring belongs in ``complaints_311_producer.py``.
    """
    out = dict(row)
    lat, lng = mercator_xy_to_wgs84(row["srx"], row["sry"])
    out["latitude"] = lat
    out["longitude"] = lng
    return out


def is_excise_expiration_sentinel(value: Any) -> bool:
    """True for Excise Commissioner expiration sentinels (year 1969 or 3027)."""
    if value in (None, ""):
        return False
    text = str(value).strip()
    year: int | None = None
    try:
        year = int(text[:4])
    except ValueError:
        parsed = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if parsed is not None:
            year = parsed.year
    return year in _EXCISE_SENTINEL_YEARS


def is_active_excise_license(row: Mapping[str, Any]) -> bool:
    """Snapshot filter: ACTIVE and not an expiration-year sentinel."""
    status = str(row.get("status_code") or row.get("STATUS_CODE") or "").strip()
    if status.upper() != "ACTIVE":
        return False
    expiration = row.get("date_expiration") or row.get("DATE_EXPIRATION")
    return not is_excise_expiration_sentinel(expiration)


def permit_composite_id(row: Mapping[str, Any]) -> str:
    """Composite permit id — the 30-day CF export has no permit number.

    Scheduler ``_extract_record_id`` currently takes the first non-empty
    ``id_keys`` value, so address-only collisions are a documented registration
    risk. Spine may concatenate these three columns.
    """
    parts = [
        str(row.get("address") or row.get("ADDRESS") or "").strip(),
        str(row.get("issuedate") or row.get("ISSUEDATE") or "").strip(),
        str(row.get("applicationdescription") or row.get("APPLICATIONDESCRIPTION") or "").strip(),
    ]
    return "|".join(parts)


# ---------------------------------------------------------------------------
# Submarkets (City of St. Louis only — not Clayton, University City, etc.)
# ---------------------------------------------------------------------------

ST_LOUIS_SUBMARKETS: Dict[str, SubmarketMeta] = {
    "Downtown & Gateway Arch": SubmarketMeta(
        name="Downtown & Gateway Arch",
        borough="STL_CORE",
        lat=38.6270,
        lng=-90.1994,
        zoom=14.2,
        pitch=52.0,
        base_lims=0.88,
        capex=9800000.0,
        permit_vel=44.0,
        shift_ratio=1.52,
        sla=64.0,
        description="Civic core and riverfront around the Gateway Arch with office conversion, stadium-adjacent hospitality, and the densest CSB 311 volume in the city.",
        city_id="st_louis",
    ),
    "Central West End": SubmarketMeta(
        name="Central West End",
        borough="STL_CORE",
        lat=38.6447,
        lng=-90.2614,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.90,
        capex=11200000.0,
        permit_vel=48.0,
        shift_ratio=1.58,
        sla=68.0,
        description="Medical-and-university district around BJC / WashU with high-value residential rehab and mixed-use infill along Euclid.",
        city_id="st_louis",
    ),
    "The Hill": SubmarketMeta(
        name="The Hill",
        borough="STL_CORE",
        lat=38.6162,
        lng=-90.2778,
        zoom=14.0,
        pitch=46.0,
        base_lims=0.82,
        capex=5400000.0,
        permit_vel=28.0,
        shift_ratio=1.38,
        sla=54.0,
        description="Italian enclave west of Kingshighway with renovation-led permitting, restaurant density, and stable single-family stock.",
        city_id="st_louis",
    ),
    "Soulard & Benton Park": SubmarketMeta(
        name="Soulard & Benton Park",
        borough="STL_CORE",
        lat=38.6045,
        lng=-90.2085,
        zoom=14.0,
        pitch=48.0,
        base_lims=0.84,
        capex=6200000.0,
        permit_vel=32.0,
        shift_ratio=1.44,
        sla=58.0,
        description="Historic market neighborhood and brewery corridor south of downtown with rehab-heavy permitting and hospitality churn.",
        city_id="st_louis",
    ),
    "Tower Grove & Shaw": SubmarketMeta(
        name="Tower Grove & Shaw",
        borough="STL_CORE",
        lat=38.5880,
        lng=-90.2560,
        zoom=13.6,
        pitch=44.0,
        base_lims=0.83,
        capex=5800000.0,
        permit_vel=30.0,
        shift_ratio=1.42,
        sla=56.0,
        description="South-city garden-district grid around Tower Grove Park with steady single-family rehab and small-commercial renewal.",
        city_id="st_louis",
    ),
    "Old North St. Louis": SubmarketMeta(
        name="Old North St. Louis",
        borough="STL_CORE",
        lat=38.6550,
        lng=-90.1950,
        zoom=13.8,
        pitch=44.0,
        base_lims=0.74,
        capex=4100000.0,
        permit_vel=22.0,
        shift_ratio=1.30,
        sla=46.0,
        description="Near-north historic district with sparse but targeted rehab, high 311 volume relative to permit activity, and riverfront-adjacent vacant-stock pressure.",
        city_id="st_louis",
    ),
}


ST_LOUIS_DIVISIONS: Dict[str, BoroughMeta] = {
    "STL_CORE": BoroughMeta(
        name="St. Louis Core",
        center_lat=38.6270,
        center_lng=-90.1994,
        zoom=11.8,
        bbox=ST_LOUIS_DIVISION_BBOXES["STL_CORE"],
        submarkets=list(ST_LOUIS_SUBMARKETS),
        city_id="st_louis",
    ),
}


# ---------------------------------------------------------------------------
# Per-feed field maps (US-200 / ADR 0004). CSVClient lowercases headers;
# maps include the normalized names. Do NOT map SRX/SRY onto latitude/
# longitude — they are EPSG:3857 meters, not degrees.
# ---------------------------------------------------------------------------
ST_LOUIS_311_FIELD_MAP: Dict[str, list[str]] = {
    "incident_id": ["requestid", "REQUESTID"],
    "complaint_type": ["problemcode", "PROBLEMCODE", "description", "DESCRIPTION"],
    "created_date": ["datetimeinit", "DATETIMEINIT"],
    "closed_date": ["datetimeclosed", "DATETIMECLOSED"],
    "status": ["status", "STATUS"],
    "incident_address": ["probaddress", "PROBADDRESS"],
    "zipcode": ["zip", "ZIP", "zipcode"],
    "descriptor": ["description", "DESCRIPTION", "comment", "COMMENT"],
    "borough": ["neighborhood", "NEIGHBORHOOD", "ward", "WARD"],
}

ST_LOUIS_PERMITS_FIELD_MAP: Dict[str, list[str]] = {
    "job_id": ["address", "ADDRESS"],
    "issuance_date": ["issuedate", "ISSUEDATE"],
    "filing_date": ["applicationdate", "APPLICATIONDATE"],
    "job_type": ["projecttype", "PROJECTTYPE", "structuretype", "STRUCTURETYPE"],
    "cost": ["estprojectcost", "ESTPROJECTCOST"],
    "status": ["projecttype", "PROJECTTYPE"],
    "address_street": ["address", "ADDRESS"],
    "descriptor": ["applicationdescription", "APPLICATIONDESCRIPTION"],
}

ST_LOUIS_SLA_FIELD_MAP: Dict[str, list[str]] = {
    "license_id": ["case_number", "CASE_NUMBER", "id", "ID"],
    "license_type": ["permit_type", "PERMIT_TYPE", "license_type", "LICENSE_TYPE"],
    "expiration_date": ["date_expiration", "DATE_EXPIRATION"],
    "status": ["status_code", "STATUS_CODE"],
    "address_street": ["location", "LOCATION"],
    "dba": ["dba", "DBA", "business_name", "BUSINESS_NAME"],
    "premises_name": ["business_name", "BUSINESS_NAME", "dba", "DBA"],
}


ST_LOUIS_FIELD_MAPS: Dict[str, Dict[str, list[str]]] = {
    "311": ST_LOUIS_311_FIELD_MAP,
    "permits": ST_LOUIS_PERMITS_FIELD_MAP,
    "sla": ST_LOUIS_SLA_FIELD_MAP,
}


# ---------------------------------------------------------------------------
# Feed specs (leaf-local dicts). Spine copies these into REGISTRY.
# Endpoint strings are the live URLs; config.py will wrap them as
# settings.csv_st_louis_{311,permits,sla}_endpoint in the spine hold.
# zip_member / src_crs are not yet DatasetSpec fields — they stay in extra.
# ---------------------------------------------------------------------------
STL_311_ENDPOINT = "https://www.stlouis-mo.gov/data/upload/data-files/csb.zip"
STL_PERMITS_ENDPOINT = (
    "https://www.stlouis-mo.gov/customcf/endpoints/building-permits/"
    "building-permits-30-days-export.cfm?permitType=all&dataType=csv"
)
STL_SLA_ENDPOINT = (
    "https://www.stlouis-mo.gov/data/upload/data-files/excise-data/"
    "excise-permits-licenses.csv"
)

STL_311_SPEC: Dict[str, object] = {
    "endpoint": STL_311_ENDPOINT,  # spine: settings.csv_st_louis_311_endpoint
    "platform": "csv",
    "watermark_col": "datetimeinit",
    "id_keys": ["requestid"],
    "topic": "settings.topic_311",
    "interval_seconds": 1800.0,
    "producer_key": "311",
    "extra": {
        "expected_cadence_days": 1,
        "endpoint_by_year": {"2026": "2026.csv", "2027": "2027.csv"},
        "zip_member": True,
        "src_crs": "EPSG:3857",
        "geocode_context": ST_LOUIS_GEOCODE_CONTEXT,
        "field_map": ST_LOUIS_311_FIELD_MAP,
        "scope": "City of St. Louis CSB service requests (yearly CSV inside csb.zip)",
    },
}

STL_PERMITS_SPEC: Dict[str, object] = {
    "endpoint": STL_PERMITS_ENDPOINT,  # spine: settings.csv_st_louis_permits_endpoint
    "platform": "csv",
    "watermark_col": "issuedate",
    "id_keys": ["address", "issuedate", "applicationdescription"],
    "topic": "settings.topic_permits",
    "interval_seconds": 1800.0,
    "producer_key": "permits",
    "extra": {
        "expected_cadence_days": 21,
        "rolling_window_days": 30,
        "needs_geocode": True,
        "watermark_format": "%B, %d %Y %H:%M:%S",
        "geocode_context": ST_LOUIS_GEOCODE_CONTEXT,
        "field_map": ST_LOUIS_PERMITS_FIELD_MAP,
        "scope": "City of St. Louis building permits, 30-day rolling CF export (address-only)",
    },
}

STL_SLA_SPEC: Dict[str, object] = {
    "endpoint": STL_SLA_ENDPOINT,  # spine: settings.csv_st_louis_sla_endpoint
    "platform": "csv",
    "watermark_col": "date_expiration",
    "id_keys": ["case_number", "id"],
    "topic": "settings.topic_sla",
    "interval_seconds": 1800.0,
    "producer_key": "sla",
    "extra": {
        "expected_cadence_days": 1,
        "ingestion_mode": "snapshot",
        "needs_geocode": True,
        "where": "status_code = 'ACTIVE'",
        "watermark_exclude": ["1969-12-31", "3027-07-02"],
        "geocode_context": ST_LOUIS_GEOCODE_CONTEXT,
        "field_map": ST_LOUIS_SLA_FIELD_MAP,
        "scope": "City of St. Louis excise (liquor) licenses — snapshot, not general business licenses",
    },
}

ST_LOUIS_FEED_SPECS: Dict[str, Dict[str, object]] = {
    "311": STL_311_SPEC,
    "permits": STL_PERMITS_SPEC,
    "sla": STL_SLA_SPEC,
}

# Keys the typed DatasetSpec does not yet carry. Spine may promote zip_member
# and src_crs; until then they stay on the leaf dict extra.
_DATASET_SPEC_LEAF_ONLY = frozenset({"scope", "zip_member", "src_crs"})


def get_st_louis_dataset(feed: object) -> object:
    """Leaf-local mirror of ``city_registry.get_dataset``.

    Returns a ``DatasetSpec`` for a registered St. Louis feed, or raises
    ``KeyError`` naming the city and available feeds when the feed is absent
    (DEEDS is deliberately unregistered).
    """
    from src.config import settings
    from src.spatial.city_registry import DatasetSpec

    feed_name = getattr(feed, "value", str(feed))
    if feed_name not in ST_LOUIS_FEED_SPECS:
        available = ", ".join(sorted(ST_LOUIS_FEED_SPECS))
        raise KeyError(
            f"'{ST_LOUIS_CITY_ID}' has no '{feed_name}' feed; available: {available}"
        )
    payload = ST_LOUIS_FEED_SPECS[feed_name]
    extra_kwargs = {
        k: v for k, v in payload.get("extra", {}).items() if k not in _DATASET_SPEC_LEAF_ONLY
    }
    topic = payload["topic"]
    if isinstance(topic, str) and topic.startswith("settings."):
        topic = getattr(settings, topic.removeprefix("settings."))
    return DatasetSpec(
        endpoint=payload["endpoint"],
        platform=payload["platform"],
        watermark_col=payload["watermark_col"],
        id_keys=payload["id_keys"],
        topic=topic,
        interval_seconds=payload["interval_seconds"],
        producer_key=payload["producer_key"],
        **extra_kwargs,
    )


GREATER_ST_LOUIS_METRO_BBOX = ST_LOUIS_METRO_BBOX
STL_DIVISION_BBOXES = ST_LOUIS_DIVISION_BBOXES
STL_SUBMARKETS = ST_LOUIS_SUBMARKETS
STL_DIVISIONS = ST_LOUIS_DIVISIONS


from src.spatial.registration import SpatialRegistration

REGISTRATION = SpatialRegistration(
    metro_bbox=ST_LOUIS_METRO_BBOX,
    division_bboxes=ST_LOUIS_DIVISION_BBOXES,
    submarkets=ST_LOUIS_SUBMARKETS,
    divisions=ST_LOUIS_DIVISIONS,
    contains=is_in_st_louis_metro,
)
