"""Per-city field maps for Glendale, AZ (US-250), imported by the shared parsers.

Glendale is a TWO-FEED PARTIAL metro on the official City of Glendale ArcGIS
Server 11.4 (``gismaps.glendaleaz.com/gisserver``, owner ``GisAdmin_COG``):

* COMPLAINTS_311 — ``OpenData/GLENDALEONE_EXTERNAL_REQUESTS_PTS``
  (MapServer/0, ~107,646 rows). The GlendaleOne citizen-service-request
  layer: water/trash/police/street requests with request numbers, status,
  open/close dates, and native WGS84 point geometry.
* SLA — ``OpenData/Business_Licenses`` (MapServer/1 table "Glendale
  Business Licenses", ~9,856 rows). Current GBL/bingo/massage/peddler etc.
  license registry with IssuedOn/ExpiresOn effective dates.

The permitting system (``SmartGov`` folder) and ``Building_Safety`` are
token-protected (ArcGIS error 499) — no anonymous permit feed exists, so
``permits`` stays unregistered. Deeds are Maricopa County-held (see
``docs/research/probe-maricopa-sales-affidavits.md``) — out of leaf scope.

Coordinate contract (pinned by tests):

* COMPLAINTS_311 — coordinates come from **native point geometry** (the
  layer's store SR is WGS84/4326; ``ArcGISClient._flatten_feature`` lifts
  it to full-precision ``latitude``/``longitude`` keys, which the parser's
  generic chain reads). The ``Latitude``/``Longitude`` *attributes* are
  truncated 3-decimal placeholders (~110 m) and are deliberately NOT
  candidates — no latitude/longitude map entries are declared, so the
  geometry lift is the only coordinate path. ``FULL_ADDRESS`` is
  anonymized to block level ("6700 BLOCK W DENTON LN"); 311 rows keep
  ``needs_geocode`` false because every row carries geometry.
* SLA — the layer is a **standalone table with no geometry**; ``IssuedOn``
  and ``ExpiresOn`` are ``esriFieldTypeDateOnly`` and arrive as ``YYYY-MM-DD``
  strings (the ArcGIS client only ISO-normalizes ``esriFieldTypeDate``).
  Rows geocode through the ADR-0004 supplement on the clean single-field
  ``AddressLine1`` (spec declares ``needs_geocode``). No latitude/longitude
  candidates appear in the map.

Id/date notes:

* 311 ``Request_Number`` is the natural id (integer); ``OBJECTID`` is the
  dedup fallback. ``Request_Date`` is the watermark; ``Close_Date`` feeds
  closed_date. ``Council_District`` (BARREL/CACTUS/CHOLLA/OCOTILLO/
  SAHUARO/YUCCA) rides ``borough`` so source_neighborhood is populated.
* SLA has no standalone license-number column — the license number is
  embedded as a suffix in ``LicenseType`` (e.g. "GBL - GLENDALE BUSINESS
  LICENSE-9898") but is absent on some rows ("BINGO LICENSE"), so
  ``license_id`` maps to ``OBJECTID`` (unique within a snapshot; the feed
  is snapshot mode). ``BusinessName`` maps to dba AND premises_name because
  Glendale publishes no separate trade name.
"""


# Canonical 311 event field -> GLENDALEONE_EXTERNAL_REQUESTS_PTS/MapServer/0
# column spellings. Live layer (2026-08-28): native WGS84 geometry, esri date
# watermark Request_Date (max 2026-08-05), anonymized block FULL_ADDRESS.
COMPLAINTS_311_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["Request_Number", "OBJECTID"],
    "complaint_type": ["Request_Type", "Request_Type_Group"],
    "created_date": ["Request_Date"],
    "closed_date": ["Close_Date"],
    "status": ["Status"],
    "borough": ["Council_District"],
    "incident_address": ["FULL_ADDRESS"],
}

# Canonical SLA event field -> Business_Licenses/MapServer/1 column
# spellings. Live table (2026-08-28): IssuedOn/ExpiresOn are DateOnly
# "YYYY-MM-DD" strings; no geometry (address-only, needs_geocode).
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["OBJECTID"],
    "license_type": ["BusinessType", "LicenseType"],
    "premises_name": ["BusinessName"],
    "dba": ["BusinessName"],
    "effective_date": ["IssuedOn"],
    "expiration_date": ["ExpiresOn"],
    "status": ["LicenseStatus"],
    "borough": ["District"],
    "address_street": ["AddressLine1"],
    "zipcode": ["ZipCode"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "311": COMPLAINTS_311_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Glendale, AZ"

# Columns that exist on the live layers and must never become map candidates.
# 311 Latitude/Longitude are truncated placeholders — geometry is the
# coordinate path; the SLA table is non-spatial so City/State/ParcelLegalDesc
# carry no coordinate or address-part value worth mapping.
DROPPED_NONADDRESS_COLUMNS: tuple[str, ...] = (
    "Latitude",
    "Longitude",
    "ANON_BLOCK",
    "Cross_Streets",
    "Responsible_Department_Name",
    "DateLoaded",
    "City",
    "State",
    "ParcelLegalDesc",
    "Shape",
    "GlobalID",
)

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "DROPPED_NONADDRESS_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "SLA_FIELD_MAP",
]
