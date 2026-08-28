"""Per-city field maps for Toledo (US-359), imported by the shared parsers.

Toledo is a PARTIAL ArcGIS metro: the Engage Toledo / Cityworks
service-request extract (`Public/CityWorks_ServiceRequest_2022/MapServer/0`
on `gis.toledo.oh.gov`) is the only live feed. The Cityworks schema shares
nothing with the shared Socrata/NYC 311 chains, so the map lives here as a
leaf rather than growing ``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* 311 — do **not** map ``X_COORD``/``Y_COORD``. Those attributes are
  projected and appear in **mixed CRSes**: Web Mercator meters
  (~-9.3M/+5.1M) on most rows, Ohio State Plane feet (~1.67M/0.74M) on the
  newest 796130 row of the 2026-08-27 re-probe. Prefer ArcGISClient
  ``outSR=4326`` point geometry (flattened to ``latitude``/``longitude``);
  ``LOCATION`` is the ADR-0004 fallback via ``needs_geocode``. One corrupted
  non-geographic point was observed on the re-probe (the newest row returned
  15.04/6.67 outSR=4326) — not flagged by the producer's degree guard, so it
  is cleaned by metro filtering rather than at parse time.

Watermark is ``INIT_DATE`` only — ``CLOSED_DATE`` is nullable on open rows.
PII is dropped at the map: ``INIT_BY`` (submitter identity, e.g.
"SEECLICKFIX,") is never a candidate.
"""

from typing import Dict, List

# Canonical 311 event field -> Cityworks_ServiceRequest_2022 layer-0 spellings.
# Watermark is INIT_DATE (CLOSED_DATE is nullable on open rows).
# No X_COORD/Y_COORD. No INIT_BY PII.
COMPLAINTS_311_FIELD_MAP: Dict[str, List[str]] = {
    "incident_id": ["REQUEST_ID"],
    "complaint_type": ["DESCRIPTION"],
    "created_date": ["INIT_DATE"],
    "closed_date": ["CLOSED_DATE"],
    "status": ["STATUS"],
    "incident_address": ["LOCATION"],
    "zipcode": ["PROBZIP"],
    "borough": ["DISTRICT"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "311": COMPLAINTS_311_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Toledo, OH"

# Columns that exist on the live 311 layer and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "INIT_BY",
)

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
]
