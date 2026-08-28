"""Per-city field maps for the Inland Empire leaf (US-222), imported by the
shared parsers.

The Inland Empire registration is anchored on Riverside County, CA (the
miami_dade county exception — the metro spans Riverside + San Bernardino
counties, but only the county has verified transactional feeds; San
Bernardino County's Hub publishes no permits/311/SLA/deeds). Two feeds:

* PERMITS — Riverside County Accela ``PLUS_ACTIVITIES``
  (``gis.countyofriverside.us`` ``OpenData/General/MapServer/280``). The
  layer holds planning AND permit cases; the spec's ``where`` keeps only
  ``CASE_MODULE = 'PERMIT'`` (building/online-permit applications).
* CRIME — City of Riverside Police ``View_CrimesRPD/FeatureServer/4``
  ("Crime (Last Year to Date)"; city-of-Riverside scope inside the
  county-anchored metro). ADR 0004 satisfied: native WGS84 point geometry
  (outSR=4326) on every probed row plus a BLOCK_ADDRESS fallback.

Coordinate contracts (pinned by tests):

* PERMITS — coordinates come from **parcel polygon geometry** requested with
  ``outSR=4326``; ``ArcGISClient._geometry_to_lng_lat`` reduces the first
  ring to a centroid and lifts it to ``latitude``/``longitude``. The layer's
  native CRS is CA State Plane Zone VI US-survey feet (wkid 102646) — those
  coordinates never enter the record because reprojection happens
  server-side. The layer has NO street-address and NO valuation column, so
  ``address_street`` and ``cost`` stay undeclared (no geocode is declared:
  a geometry-less row has nothing to geocode and drops honestly).
* CRIME — coordinates come from native point geometry (outSR=4326).
  ``BLOCK_ADDRESS`` exists (the ADR 0004 address evidence) but the crime
  producer's address chain reads lowercase spellings only, so the event
  ``address`` passes None; the map declares no ``latitude``/``longitude``
  candidates — geometry is the sole coordinate source.

Watermark parity: ``APPLIED_DATE`` is an *application*, not an issuance,
date, but it is the layer's only ledger-wide event column and the poll
watermark, so it maps to the ``issuance_date`` slot (mapping APPROVED_DATE
there instead would desync the scheduler's event-attr watermark from the
poll filter on the many rows that are still unapproved). ``APPROVED_DATE``
and ``COMPLETED_DATE`` stay unmapped. The ``SUBDIVISION_NAME`` column is
tract metadata, not a neighborhood, and stays undeclared (Omaha
discipline): ``source_neighborhood`` passes through as None on permits.

PII: the layer exposes no owner/applicant columns; nothing to drop.
"""


# Canonical permit event field -> PLUS_ACTIVITIES/MapServer/280 (filtered
# CASE_MODULE='PERMIT') column spellings. Live layer (2026-08-28): OBJECTID
# is the OID, geometry is the coordinate source, APPLIED_DATE is the
# watermark. UNIT_COUNT/FLOOR_COUNT carry 0 on most online applications —
# the producer maps 0 to None honestly.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    # OBJECTID is the OID fallback (Henderson precedent) so coordinate-less
    # rows stay addressable if a CASE_ID is ever missing client-side.
    "job_id": ["CASE_ID", "OBJECTID"],
    "issuance_date": ["APPLIED_DATE"],
    "status": ["CASE_STATUS"],
    "job_type": ["CASE_WORK_CLASS", "CASE_TYPE"],
    # APN is the county parcel number; the bbl slot is the generic
    # parcel-identifier carrier (boise/las_vegas APN precedent).
    "bbl": ["APN"],
    "proposed_units": ["UNIT_COUNT"],
    "proposed_stories": ["FLOOR_COUNT"],
}

# Canonical crime event field -> View_CrimesRPD/FeatureServer/4 column
# spellings. Live layer (2026-08-28): ObjectID (camelCase OID) is the dedup
# tail, offenseid the incident id, nibrsdesc the offense text, COMMUNITY the
# city's community-planning-area name (real neighborhood column — mapped to
# the borough candidate, unlike the permits feed).
CRIME_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["offenseid", "ObjectID"],
    "offense_type": ["nibrsdesc"],
    "occurred_date": ["offendate"],
    # datecreated is the record/report creation timestamp; dateupdated is
    # maintenance noise and deliberately not a candidate.
    "reported_date": ["datecreated"],
    "borough": ["COMMUNITY"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

# Columns that exist on the live layers and must never become map candidates:
# maintenance/derived noise (SHAPE SQL columns ride the flattener as plain
# attributes) and the crime layer's dispatch-call id (LPD-prefixed callid is
# a dispatch key, not an incident id).
DROPPED_NOISE_COLUMNS: tuple[str, ...] = (
    "SHAPE.STArea()",
    "SHAPE.STLength()",
    "dateupdated",
    "callid",
    "InstanceID",
    "GlobalID",
    "rpdunique",
)

__all__ = [
    "CRIME_FIELD_MAP",
    "DROPPED_NOISE_COLUMNS",
    "FIELD_MAP",
    "PERMITS_FIELD_MAP",
]
