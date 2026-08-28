"""Per-city field maps for Las Cruces, NM (US-240), imported by the shared parsers.

Las Cruces is a TWO-FEED PARTIAL metro on the city's ArcGIS Server
(``maps.las-cruces.org/gis/rest/services/Information_Services/MapServer``):
BuildingPermits (L1, Tier 1, ~82k rows) and Business_Registrations (L2,
Tier 2, ~26k rows). Spellings do not match the shared Socrata chains, so
the maps live here as leaves rather than growing
``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* PERMITS and SLA — native point geometry is the primary locator: every
  query requests ``outSR=4326`` and ``ArcGISClient._flatten_feature`` lifts
  it to ``latitude``/``longitude`` keys, which the parser's generic chain
  reads. The X/Y attributes on the layer are WGS84 decimal degrees (same
  CRS as the geometry) — no State Plane issue. ``needs_geocode=False`` for
  both feeds.

* No ANSI-date host issues: ``maps.las-cruces.org`` accepts ISO date
  literals in where clauses.

* PII columns (Owner_Name, Contractor_Name, Contractor_Business_Name,
  Email, Phone, MailAddress, ContactName) are dropped at the map — never
  candidates.
"""


# Canonical permit event field -> BuildingPermits MapServer/1 column spellings.
# Live layer (2026-08-28): Issued_Date is the watermark (esriFieldTypeDate);
# Permit_Number is the primary id; OBJECTID is the OID fallback.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["Permit_Number", "OBJECTID"],
    "issuance_date": ["Issued_Date"],
    "job_type": ["Permit_Type"],
    "cost": ["Project_Valuation"],
    "address_street": ["Permit_Location"],
}

# Canonical SLA event field -> Business_Registrations MapServer/2 columns.
# Live layer: LastUpdateDate is the watermark (esriFieldTypeDate);
# RECNO is the primary id; DBA holds the trade name (BUSINESS_NAME is
# null for most records); RECNAME holds the premises/legal name.
BUSREG_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["RECNO", "OBJECTID"],
    "dba": ["DBA", "RECNAME"],
    "premises_name": ["RECNAME", "DBA"],
    "license_type": ["BusCat", "BusType"],
    "status": ["STATUS"],
    "effective_date": ["LastUpdateDate"],
    "address_street": ["RecAddress"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": BUSREG_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Las Cruces, NM"

# Columns that exist on the live feeds and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "Owner_Name",
    "Contractor_Name",
    "Contractor_Business_Name",
    "Email",
    "Phone",
    "MailAddress",
    "ContactName",
)

__all__ = [
    "BUSREG_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]