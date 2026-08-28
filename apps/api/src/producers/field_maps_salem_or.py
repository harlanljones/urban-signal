"""Per-city field maps for Salem, OR (US-226), imported by the shared parsers.

Salem, OR is a TWO-FEED PARTIAL metro on the City of Salem's ArcGIS Online
org (``kIA6yS9KDGqZL7U3``): Structure_Permits (FeatureServer/0, Tier 1,
~802 rows) and Amanda_MultiFamily_Licenses_Data (FeatureServer/0, Tier 2,
~1,111 rows). Spellings do not match the shared Socrata chains, so the map
lives here as a leaf rather than growing ``src/producers/field_maps.py``
(spine).

Coordinate contract (pinned by tests):

* Both feeds — coordinates come from **native point geometry** requested with
  ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts them to
  ``latitude``/``longitude`` keys, which the parser's generic chain reads.
  The store SR is WKID 2913 (NAD83 Oregon State Plane South, feet).
* The ``X``/``Y`` (Structure_Permits) and ``POINT_X``/``POINT_Y``
  (Amanda licenses) *attributes* are **integer State Plane feet** (values
  ≈ 7.5e6 / 0.5e6) and are deliberately NOT candidates — mapping them would
  emit projected feet as degrees.
* Both layers carry data with 100% native geometry coverage (0 null-geometry
  rows live-probed 2026-08-28), so ``needs_geocode=False``.
* CREATEDDATE/ISSUEDDATE (permits) and INDATE (licenses) are
  ``esriFieldTypeDate`` and arrive as epoch-ms; ``ArcGISClient`` converts
  them to ISO 8601 UTC on flatten.

PII considerations: OWNER on the Amanda licenses layer is the legal entity
(company or individual) and is dropped from the map. The DOB permits producer
dispatches STATUS as provided; the SLA producer dispatches STATUSDESC as
provided.
"""


PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["FOLDERNUMBER"],
    "issuance_date": ["ISSUEDDATE"],
    "filing_date": ["CREATEDDATE"],
    "status": ["STATUS"],
    "job_type": ["SUBDESCRIPTION", "MAPDESCRIPTION"],
    "address_street": ["PROPERTYADDRESS"],
    "borough": ["NEIGHBORHOOD"],
}

SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["FOLDERNUMBER"],
    "dba": ["COMPLEXNAME"],
    "premises_name": ["COMPLEXNAME"],
    "license_type": ["SUBTYPE", "SUBDESC"],
    "status": ["STATUSDESC"],
    "effective_date": ["INDATE"],
    "expiration_date": ["EXPIRYDATE"],
    "address_street": ["FOLDERNAME"],
    "borough": ["NEIGHBORHOOD"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Salem, OR"

DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "OWNER",
    "ISSUEUSER",
    "GlobalID",
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]