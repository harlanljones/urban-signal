"""Per-city field maps for Tempe, AZ (US-229), imported by the shared parsers.

Tempe is a THREE-FEED PARTIAL metro on the city's ArcGIS Hub
(``data.tempe.gov`` org ``lQySeXwbBg53XWDi``; the datasets live on
``services.arcgis.com`` FeatureServers — the ticket's Socrata hint is the
wrong door): building_permits (FeatureServer/0, Tier 1, daily),
code_complaints (FeatureServer/0 — the 311-family proxy), and
General_Offenses_(Open_Data) (FeatureServer/0 — crime). Spellings do not
match the shared Socrata chains, so the maps live here as a leaf rather than
growing ``src/producers/field_maps.py`` (spine).

Coordinate contracts (pinned by tests):

* PERMITS — coordinates come from **native point geometry** requested with
  ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts them to
  ``latitude``/``longitude`` keys. The ``Latitude``/``Longitude``
  *attributes* are WGS84 degrees (probe values ≈ 33.4 / -111.94) and are
  declared as fallback candidates for the 3.0% geometry-less rows — unlike
  Greenville, Tempe has no state-plane attribute pair on this layer.
* COMPLAINTS_311 — native 4326 geometry is the only coordinate path. The
  ``X_COORD``/``Y_COORD`` attributes are degree-safe duplicates of the
  geometry (probe: X=-111.928923, Y=33.357087) but are deliberately NOT
  candidates (geometry primary, Greenville discipline); rows whose geometry
  carries the (0,0) sentinel (2 live) drop on the producer's 0/0 guard.
* CRIME — **mixed-CRS layer**: geometry store is AZ State Plane Central
  (WKID 2223, intl ft) but every query lifts to ``outSR=4326``. The
  ``Latitude``/``Longitude`` attributes are WGS84 degree fallback
  candidates for geometry-less rows; the ``XCoordinate``/``YCoordinate``
  attributes are the STATE-PLANE pair (probe: 697343 / 875784 feet) and are
  deliberately NOT candidates — mapping them would emit projected feet as
  degrees (the ``state_plane_*`` DatasetSpec keys carry the transform
  contract for the spine instead). ADR-0004: obfuscated addresses
  ("9XX E BROADWAY RD") are not geocodable and ``needs_geocode`` stays
  False; rows with neither geometry nor degree attributes drop.

Date semantics: ``AppliedDate``/``IssuedDate`` are plain ``YYYY-MM-DD``
strings while the ``*Dtm`` twins are esriFieldTypeDate epoch-ms ISO-normalized
by ``_flatten_feature``; ``ExpiresDateDtm`` carries future-date sentinels
(fixture: 2027-08-26) and never feeds an event date. ``PrimaryKey`` on the
crime layer is CHAR-padded — the parser strips incident_id.

PII is dropped at the map: the contractor block and ProjectName (owner/trust
names) are never candidates.
"""


# Canonical permit event field -> building_permits/FeatureServer/0 column
# spellings. Live layer (2026-08-28): OBJECTID is the OID, geometry is the
# primary coordinate source, AppliedDateDtm is the daily watermark.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    # OBJECTID is the OID fallback (Henderson precedent): PermitNum is the
    # id_keys head, but the OID keeps coordinate-less/dedup edge rows
    # addressable if a permit number is ever missing client-side.
    "job_id": ["PermitNum", "OBJECTID"],
    # The *Dtm esri dates lead: _flatten_feature ISO-normalizes them to
    # tz-aware UTC, while the plain string twins ("2026-08-26") parse naive
    # in the permits producer's datetime chain — keep event datetimes
    # tz-consistent, string twins remain the fallback.
    "issuance_date": ["IssuedDateDtm", "IssuedDate"],
    "filing_date": ["AppliedDateDtm", "AppliedDate"],
    "status": ["StatusCurrent"],
    "job_type": ["Type", "PermitClass"],
    "cost": ["EstProjectCost"],
    "address_street": ["OriginalAddress1"],
    "zipcode": ["OriginalZip"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
}


# Canonical 311 event field -> code_complaints/FeatureServer/0 column
# spellings. Live layer (2026-08-28): CaseOpenDate is the watermark (feed
# top watermark 2026-06-12 — quarterly publication suspected). CaseStatusDate
# is the last status-touch date, NOT a closure date — deliberately not a
# closed_date candidate. No neighborhood/zip columns exist, so no borough or
# zipcode candidates are declared (Omaha discipline); Address is a single
# "street, TEMPE, AZ, zip" string used by the ADR-0004 geocode supplement.
COMPLAINTS_311_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["CaseNo", "Id"],
    "created_date": ["CaseOpenDate"],
    "status": ["CaseStatus"],
    "complaint_type": ["ViolationType"],
    "incident_address": ["Address"],
}


# Canonical crime event field -> General_Offenses_(Open_Data)/FeatureServer/0
# column spellings. Live layer (2026-08-28): OccurrenceDatetime is the
# only esriFieldTypeDate column and arrives as epoch-ms; ArcGISClient
# converts it to ISO 8601 UTC on flatten. OffenseCustom is CHAR-padded
# ("[13B] ASSAULT [DV]              "); CharacterArea is the evidenced
# Tempe character-area borough candidate. XCoordinate/YCoordinate are the
# State Plane (WKID 2223) attribute pair — never candidates.
CRIME_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["PrimaryKey", "OBJECTID"],
    "offense_type": ["OffenseCustom"],
    "occurred_date": ["OccurrenceDatetime"],
    "borough": ["CharacterArea"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Tempe, AZ"

# Columns that exist on the live layers and must never become map candidates.
# PERMITS: contractor block + ProjectName (owner/trust names). CRIME: the
# State Plane attribute pair.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "ContractorCompanyName",
    "ContractorLicNum",
    "ContractorPhone",
    "ContractorAddress1",
    "ContractorAddress2",
    "ContractorCity",
    "ContractorState",
    "ContractorZip",
    "ContractorEmail",
    "ProjectName",
)

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "CRIME_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]
