"""Per-city field maps for Salem, OR (US-226; SLA updated US-426).

Salem, OR is a TWO-FEED PARTIAL metro: Structure_Permits (FeatureServer/0,
Tier 1, ~802 rows) on the City of Salem's AGOL org
(``services.arcgis.com/kIA6yS9KDGqZL7U3``) and — since US-426 — the OR
Secretary of State Active Businesses registry (``tckn-sxa6``,
``data.oregon.gov``) as the metropolitan SLA slot (US-426 super-feed; see
docs/research/pnw-rockies-plains-expansion-probe-2026-08-30.md). Spellings
do not match the shared Socrata chains, so the map lives here as a leaf
rather than growing ``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* PERMITS — coordinates come from **native point geometry** requested with
  ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts them to
  ``latitude``/``longitude`` keys, which the parser's generic chain reads.
  The store SR is WKID 2913 (NAD83 Oregon State Plane South, feet).
* SLA — the OR Active Businesses Socrata registry is **address-only**
  (``address``/``city``/``state``/``zip``), so rows geocode via the
  ADR-0004 supplement with context "Salem, OR" (``needs_geocode=True``).
  ``registry_date`` is the ISO-8601 watermark.
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
    "license_id": ["registry_number"],
    "dba": ["business_name"],
    "premises_name": ["business_name"],
    "license_type": ["entity_type"],
    "effective_date": ["registry_date"],
    "address_street": ["address"],
    "city": ["city"],
    "zipcode": ["zip"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Salem, OR"

DROPPED_PII_COLUMNS: tuple[str, ...] = ()

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]