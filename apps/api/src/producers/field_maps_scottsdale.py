"""Per-city field maps for Scottsdale, AZ (US-227), imported by the shared parsers.

Scottsdale is a TWO-FEED PARTIAL metro on the city ArcGIS Server 10.6
(``maps.scottsdaleaz.gov``): Building Permits (``OpenData_Tabular/MapServer/12``,
288,121 rows) and Business Licenses (``OpenData_Tabular/MapServer/6``, 19,944
rows) — both standalone tables. Spellings do not match the shared Socrata
chains, so the maps live here as a leaf rather than growing
``src/producers/field_maps.py`` (spine). ``data.scottsdaleaz.gov`` is an
ArcGIS Hub Open Data portal, not Socrata (the US-227 ticket body's
"Socrata" claim is wrong — ``/api/catalog/v1`` 404s).

Coordinate contract (pinned by tests):

* PERMITS — coordinates come from the **native WGS84 attribute columns**
  ``Latitude``/``Longitude`` (verified live: 33.6564984 / -111.90865983 on
  the newest geocoded row). Coverage is partial — 151,704 of 288,121 rows
  (52.6%) carry non-null values, and the newest-window rows are null — so
  declared candidates fall through to the ADR-0004 geocode supplement on
  ``Address``. The table endpoint is registered precisely because the
  mapped twin (``OpenData_Events/MapServer/3``, store SR WKID 2868 Arizona
  Central intl feet) returns ``{'x': 'NaN', 'y': 'NaN'}`` geometry for
  null-shape features, which ``ArcGISClient._flatten_feature`` would lift
  into latitude/longitude keys as the *strings* "NaN" — the table carries
  no geometry at all, so the NaN trap is structurally unreachable.
* SLA — address-only: ``ServAddrComp`` is the premises street address and
  ``ServCityStateZipComp`` is a mixed city-state-zip string, so no zipcode
  candidate is declared (mapping the combined string would emit
  "SCOTTSDALE AZ 85251" as a zip). Geocode context "Scottsdale, AZ"
  completes the address.
* ``ESRI_OID`` (the licenses table's reported OID field) is **unstable** —
  the same row (OBJECTID 19901) returned ESRI_OID 27 in one live query and
  ESRI_OID 1 in another (2026-08-28 probes), i.e. the server enumerates it
  per result set. It is never an id/oid candidate; the attribute
  ``OBJECTID`` column is the stable row key.

PII is dropped at the map: the permit owner/builder/responsible-party
blocks and the license holder's mailing address are never candidates.
"""


# Canonical permit event field -> OpenData_Tabular/MapServer/12 column
# spellings. Live table (2026-08-28): permit_id is the esriFieldTypeOID;
# PermitNumber is the permit number (integer); Latitude/Longitude are the
# WGS84 attribute columns (null on ~47% of rows — geocode fallback).
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["PermitNumber", "permit_id"],
    "issuance_date": ["IssueDate"],
    "status": ["PermitStatus"],
    "job_type": ["PermitType"],
    "cost": ["Valuation"],
    "address_street": ["Address"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
}


# Canonical SLA event field -> OpenData_Tabular/MapServer/6 column
# spellings. Live table (2026-08-28): only LicType values BRS/BRM;
# BusinessStartDate is the only esriFieldTypeDate column and arrives as
# epoch-ms, ISO-normalized by ArcGISClient. Future-dated application
# sentinels (year 5202 garbage row + forward-dated 2026-11/2027-01 rows)
# are excluded at the source by the spec where guard — never by a static
# watermark_exclude list (the set is rolling).
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["AcctNum"],
    "dba": ["Company"],
    "premises_name": ["Company"],
    "license_type": ["LicType"],
    "status": ["AcctStatus"],
    "effective_date": ["BusinessStartDate"],
    "address_street": ["ServAddrComp"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Scottsdale, AZ"

# Columns that exist on the live feeds and must never become map candidates.
# Permit Owner/Builder/ResponsibleParty and the license mailing-address
# block are holder PII (Greenville owner-block discipline); ServCityStateZip
# is a mixed city-state-zip string, not a zip; ESRI_OID is per-query
# unstable; Shape/CityOfScottsdaleMap stay server-side.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "Owner",
    "Builder",
    "ResponsibleParty",
    "MailAddrComp",
    "MailAddrCityStateZipComp",
)

DROPPED_NONADDRESS_COLUMNS: tuple[str, ...] = (
    "ServCityStateZipComp",
    "ESRI_OID",
    "CityOfScottsdaleMap",
    "Shape",
)

__all__ = [
    "DROPPED_NONADDRESS_COLUMNS",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]