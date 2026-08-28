"""Per-city field maps for Yakima, WA (US-239), imported by the shared parsers.

Yakima is a ONE-FEED PARTIAL metro on the city's ArcGIS open data platform
(``gis.yakimawa.gov``; org ``drBwGNA3YMS2QPJd`` / urlKey ``yakima``, the public
door being the ArcGIS Hub at ``opendata.yakimawa.gov``):

* PERMITS — ``Planning/BuildingPermits/FeatureServer/0`` (native point
  geometry, ~2,228 rows, watermark ``IssuedOnDate``, newest live-probe value
  2026-08-21T00:00:00+00:00; layer holds a ~2022-10 -> now window, so
  ``min(date)`` is not staleness evidence).

YakBack Requests (the city's service-request/311 system, ``YakBack/
PublicRequest/MapServer/0``) is LIVE and verifiable at the data layer
(~16,833 rows, watermark ``dateOpened`` 2026-08-28T21:12:14+00:00, native
point geometry), but its ``status`` column is an **integer** (1 = open,
2 = closed) — ``Complaints311Producer`` unconditionally reads
``row.get("status")`` into the typed ``Complaint311Event.status: Optional[str]``,
and pydantic v2 rejects the int (verified live 2026-08-28: every YakBack row
drops with "Input should be a valid string"). Until the spine str-coerces the
311 status (or the layer publishes a string status), the 311 feed must NOT be
registered — doing so would silently stream zero rows. The count/geometry/
watermark evidence is recorded in the leaf docstring for that follow-up.

Coordinate contract (pinned by tests):

* PERMITS — coordinates come from **native WGS84 point geometry** requested
  with ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts them to
  ``latitude``/``longitude`` keys, which the producer's generic chains read.
  There are NO State Plane ``X_COORD``/``Y_COORD`` feet columns on this layer
  (unlike Greenville), so ``latitude``/``longitude`` stay undeclared and the
  projected-coordinate guard in the producer is a second net.
* ``SubmittedOnDate`` (filing) and ``IssuedOnDate`` (issuance watermark) are
  esriFieldTypeDate — the client flattens epoch-ms to ISO.
* No valuation/cost column exists on the layer, so ``cost`` stays unmapped
  (the producer defaults to 0.0). No borough/neighborhood/parcel column
  exists, so division resolution comes from coordinates at ingest and
  ``source_neighborhood`` passes through as None (Omaha discipline).
* ``SiteZipCode`` maps to ``zipcode``; ``SiteCity``/``SiteState`` are fixed
  literals (YAKIMA/WA) and stay unmapped.

PII: the permit layer publishes no owner/contractor columns; the YakBack
layer publishes ``name``/``email``/``phone``/``GlobalID`` — those are listed
as never-candidates so a future 311 map cannot leak them.
"""

GEOCODE_CONTEXT: str = "Yakima, WA"

# Canonical permit event field -> Planning/BuildingPermits/FeatureServer/0
# column spellings. Live layer (2026-08-28): OBJECTID is the OID, geometry is
# the coordinate source, IssuedOnDate is the daily issuance watermark.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    # OBJECTID is the OID fallback (Henderson/Greenville precedent): live rows
    # always carry PermitID (it is the id_keys head), but the OID keeps
    # coordinate-less/dedup edge rows addressable if a permit number is ever
    # missing client-side.
    "job_id": ["PermitID", "OBJECTID"],
    "issuance_date": ["IssuedOnDate"],
    "filing_date": ["SubmittedOnDate"],
    "status": ["PermitStatus"],
    "job_type": ["PermitType"],
    "address_street": ["SiteStreet"],
    "zipcode": ["SiteZipCode"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
}

# Columns that exist on the live feeds and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    # YakBack requestor/assignee block (311 follow-up guard). The permit
    # layer itself publishes no owner/contractor columns.
    "name",
    "email",
    "phone",
    "GlobalID",
    "closedBy",
    "assignedTo",
    "updatedBy",
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]
