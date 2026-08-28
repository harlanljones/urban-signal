"""Per-city field maps for Omaha (US-358), imported by the shared parsers.

Omaha is a ONE-FEED PARTIAL ArcGIS metro: the city's Mayor's Hotline (Omaha
311) published as an anonymous Cityworks extract on the DCGIS ArcGIS Server
(``Cityworks/Mayors_Hotline_Dashboard_Interactive/MapServer/0``). Permits
are Accela UI-only, liquor licenses are an unwatermarkable registry, and
there is no deeds stream — all Tier 3 and unregistered (probe
``docs/research/probe-omaha.md``, stamp 2026-08-28).

Coordinate contract (pinned by tests):

* 311 — native point geometry. ArcGISClient lifts ``outSR=4326`` geometry
  to ``latitude``/``longitude`` keys. Do **not** map ``SRX``/``SRY`` —
  those are State Plane feet (NAD83 Nebraska South), not degrees.
* ``PROBADDRESS`` ("15308 Wycliffe Dr, Omaha, NE, 68154") is the ADR-0004
  geocode supplement for geometry-less rows. It already carries city/state,
  so the ``_STATE_RE`` guard appends no ``Omaha, NE`` context.

Watermark contract: ``DATETIMEINIT`` is ``esriFieldTypeDateOnly`` (day
precision). ``DATETIMECLOSED`` is nullable on open rows and is never a
created-date candidate. ``DATETIMEINITFULL`` is the epoch-ms twin used for
precise row timing.

PII is dropped at the map: ``INITIATEDBY`` and ``CLOSEDBY`` (Memphis
contact-field precedent) plus ``SUBMITTO`` / ``Submit_To_byOrg`` (internal
staff-assignee names, never map candidates).
"""

from typing import Dict, List

# Canonical 311 event field -> Mayors_Hotline_Dashboard_Interactive layer-0
# spellings. OBJECTID and REQUESTID carry identical values on live rows;
# OBJECTID is the layer OID and the primary id candidate. No zipcode column
# exists on the layer (the ZIP rides inside PROBADDRESS); no neighborhood
# column exists either, so no borough candidate is declared.
COMPLAINTS_311_FIELD_MAP: Dict[str, List[str]] = {
    "incident_id": ["OBJECTID", "REQUESTID"],
    "complaint_type": ["PROBLEMCODE", "REQCATEGORY"],
    "created_date": ["DATETIMEINIT"],
    "closed_date": ["DATETIMECLOSED"],
    "status": ["STATUS"],
    "incident_address": ["PROBADDRESS"],
    "descriptor": ["DESCRIPTION", "DETAILS", "PROBLEMCODE"],
}

FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "311": COMPLAINTS_311_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Omaha, NE"

# Columns that exist on the live 311 layer and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "INITIATEDBY",
    "SUBMITTO",
    "CLOSEDBY",
)

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
]
