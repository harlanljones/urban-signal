"""Per-city field maps for Medford, OR (US-238), imported by the shared parsers.

Medford is a THREE-FEED PARTIAL metro on the city's own ArcGIS Server 12.1
(``maps.medfordmaps.org``), fed by the TRAKiT Community Development database:

* **PERMITS** — ``TRAKiTExport/TRAKiTPermits_service/FeatureServer/1``
  ("Permits from 2020 to Present", ~59k rows, daily). Native **point**
  geometry is the coordinate source (store SR WKID 2270 = OR State Plane
  North feet; every query requests ``outSR=4326`` and
  ``ArcGISClient._flatten_feature`` lifts it to ``latitude``/``longitude``).
  ``ISSUED`` (esri date) is the watermark. No ``X``/``Y`` *attribute*
  columns exist, so nothing projected can leak into coordinates.
* **SLA** — ``MLI2/MLI_TRAKiT_Service/FeatureServer/14`` (License2_Main,
  ~29.6k rows; 6,594 ACTIVE). A **Table** with no geometry: coordinates come
  only from the ADR-0004 geocode supplement on ``SITE_ADDR`` (context
  "Medford, OR"). ``ISSUED`` is the watermark.
* **COMPLAINTS_311** — ``MLI2/MLI_TRAKiT_Service/FeatureServer/12``
  (Case_Main code-enforcement cases, ~83.7k rows). Also a **Table**; geocode
  supplement on ``SITE_ADDR``. ``STARTED`` is the watermark. ``LASTACTION``
  carries future-dated sentinels (2026-09-01/02 on the 2026-08-28 probe) so
  it is deliberately NOT a candidate.

Host caveat (pinned by tests): ``maps.medfordmaps.org`` is an **ANSI-date
host** — ISO date-string or epoch-ms ``where`` comparisons return ArcGIS 400
"Unable to complete operation" while ANSI ``timestamp 'YYYY-MM-DD'`` and
``CURRENT_TIMESTAMP`` work. The spine must add the host to
``ANSI_DATE_LITERAL_HOSTS`` (watermarks.py) for incremental watermark
queries.

PII is dropped at the map: owner/applicant/contractor names, staff-*BY
columns, and the SLA mailing/contact block (EMAIL/PHONE/FAX/mailing address)
are never candidates.
"""


# Canonical permit event field -> TRAKiTPermits FeatureServer/1 spellings.
# Live layer (2026-08-28): PERMIT_NO is the id head (OBJECTID OID fallback);
# SITE_ADDR is the street string, SITE_ZIP the site zip, SITE_APN the parcel.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["PERMIT_NO", "OBJECTID"],
    "issuance_date": ["ISSUED"],
    "filing_date": ["APPLIED"],
    "status": ["STATUS"],
    "job_type": ["PermitType"],
    "cost": ["JOBVALUE"],
    "address_street": ["SITE_ADDR"],
    "zipcode": ["SITE_ZIP"],
    "bbl": ["SITE_APN"],
    "borough": ["SITE_CITY"],
}

# Canonical SLA event field -> License2_Main/FeatureServer/14 spellings.
# COMPANY is the only business-name field on the layer, so it maps to both
# dba and premises_name (Tucson precedent). SITE_ADDR feeds the geocoder.
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["LICENSE_NO"],
    "dba": ["COMPANY"],
    "premises_name": ["COMPANY"],
    "license_type": ["LICENSE_TYPE"],
    "status": ["STATUS"],
    "effective_date": ["ISSUED"],
    "expiration_date": ["EXPIRED"],
    "address_street": ["SITE_ADDR"],
    "zipcode": ["SITE_ZIP"],
    "borough": ["SITE_CITY"],
    "bbl": ["SITE_APN"],
}

# Canonical 311 event field -> Case_Main/FeatureServer/12 spellings.
# STARTED is the created watermark; CLOSED the close date. SITE_ADDR feeds
# the geocoder. LASTACTION is future-dated on some rows -> never a candidate.
CASE_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["CASE_NO"],
    "complaint_type": ["CaseType"],
    "status": ["STATUS"],
    "created_date": ["STARTED"],
    "closed_date": ["CLOSED"],
    "incident_address": ["SITE_ADDR"],
    "zipcode": ["SITE_ZIP"],
    "borough": ["SITE_CITY"],
    "bbl": ["SITE_APN"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "311": CASE_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Medford, OR"

# Columns that exist on the live feeds and must never become map candidates.
# Mailing/contact fields (SLA) and complainant/owner blocks (cases) are PII.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    # Permits (FeatureServer/1)
    "Taxlots_FEEOWNER",
    "OWNER_NAME",
    "APPLICANT_NAME",
    "CONTRACTOR_NAME",
    "APPLIED_BY",
    "APPROVED_BY",
    "ISSUED_BY",
    "FINALED_BY",
    "EXPIRED_BY",
    "OTHER_BY1",
    "NOTES",
    # License2_Main (FeatureServer/14)
    "EMAIL",
    "EMERGENCY",
    "FAX",
    "PHONE",
    "PHONE_EXT",
    "LIAB_CARRIER",
    "LIAB_NO",
    "LIAB_ISS",
    "LIAB_EXP",
    "WRKR_COMP",
    "W_COMP_NO",
    "W_COMP_ISS",
    "W_COMP_EXP",
    "TAX_ID",
    "MAIL_ADDRESS1",
    "MAIL_ADDRESS2",
    "MAIL_CITY",
    "MAIL_STATE",
    "MAIL_ZIP",
    # Case_Main (FeatureServer/12)
    "COMPLAINANT_NAME",
    "RESIDENT_NAME",
    "RECEIVED_BY",
    "STARTED_BY",
    "CLOSED_BY",
    "LASTACTION_BY",
    "FOLLOWUP_BY",
    "ASSIGNED_TO",
    "REFERRED_TO",
)

__all__ = [
    "CASE_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]
