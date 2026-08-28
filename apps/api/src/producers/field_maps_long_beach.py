"""Per-city field maps for Long Beach, CA (US-224), imported by the shared parsers.

Long Beach is a TWO-FEED PARTIAL metro on the city's hosted ArcGIS org
(``services6.arcgis.com``/``yCArG7wGXGyWLqav``, owner ``arcgis_clb``): the
BusinessLicenses_DailyUpdate layer (SLA, Tier 1, daily) and the LBPD
CrimeData layer (crime with native coordinates, ADR-0004-satisfied). The
ticket's ``datalongbeach.opendatasoft.com`` portal is dead — the official
OpenDataSoft/Huwise portal moved to ``data.longbeach.gov`` and its
service-requests dataset (346,300 rows, intraday-fresh) is verified but NOT
registrable at leaf: the repo has no OpenDataSoft client and its CSV export
is semicolon-delimited full-file (spine follow-up).

Coordinate contract (pinned by tests):

* SLA — coordinates come ONLY from the ``outSR=4326`` point-geometry lift
  (``ArcGISClient._flatten_feature`` → ``latitude``/``longitude``). The
  layer publishes no coordinate attribute columns, so nothing else can
  feed degrees. A small tail of rows carries junk off-map geocodes
  (x ≈ -138, y ≈ 27 — the source geocoder's outside-city failures) and
  ~0.1% null geometry; junk-coord rows are downstream metro-scoping's
  concern (Greenville/SNAP precedent), null-geometry rows fall to the
  ADR-0004 geocode supplement on ``SITELOCATION``.
* CRIME — same native-geometry lift, clean WGS84 on every probed row.
  ``Address`` is block-anonymized by LBPD and stays unmapped: coordinates
  are the locator, so the event address passes through the producer's
  hard-coded block chains as None.

Date/watermark contract:

* SLA — ``MILESTONEDATE`` is the watermark (esriFieldTypeDate, epoch-ms →
  ISO in the client; newest live ``1787817600000`` = 2026-08-27T08:00:00+00:00,
  ~167 milestones/day). ``ISSDTTM`` is FUTURE-DATE SENTINEL-POISONED
  (max ``38886854400000`` = year 3202, min 1800) — deliberately NOT the
  watermark; it still maps ``effective_date`` (Tucson DT_START precedent)
  with the sentinel caveat documented in the city module.
* CRIME — ``ReportedDateTimeDate`` (esriFieldTypeDate) is the watermark;
  ``ReportedDateTime`` is a plain "MM/DD/YYYY hh:mm AM/PM" string kept as a
  display passthrough and never parsed.

PII is dropped at the map: ``FULLNAME`` is the license-holder name (SOLE
rows are persons) and is never a candidate.
"""


# Canonical SLA event field -> Business_Licenses_Public_View/FeatureServer/0
# column spellings. Live layer (2026-08-28): OBJECTID is the OID, geometry is
# the coordinate source, MILESTONEDATE is the daily watermark.
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["LICENSENO"],
    "dba": ["DBANAME"],
    "premises_name": ["DBANAME"],
    "license_type": ["LICCATDESC", "CLASSDESC"],
    "status": ["LICSTATUS"],
    "effective_date": ["ISSDTTM"],
    "expiration_date": ["INACTVDTTM"],
    "address_street": ["SITELOCATION"],
    "zipcode": ["ZIP"],
    "borough": ["COUNCIL_NUMBER"],
}

# Canonical crime event field -> Police_Crime_Mapping/FeatureServer/0 column
# spellings. Native geometry is the locator; no latitude/longitude candidates
# exist as attributes, and none may be added.
CRIME_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["DR", "OBJECTID"],
    "offense_type": ["CrimeType", "Category", "Type"],
    "reported_date": ["ReportedDateTimeDate"],
    "borough": ["Division"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SLA_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Long Beach, CA"

# Columns that exist on the live layers and must never become map candidates.
# FULLNAME is the license holder (persons on SOLE/TRUST rows); the BID trio
# and TRACT/CDBG are analytics joins, not event fields; ReportedDateTime is
# superseded by the esri-typed ReportedDateTimeDate.
DROPPED_PII_COLUMNS: tuple[str, ...] = ("FULLNAME",)

DROPPED_NONADDRESS_COLUMNS: tuple[str, ...] = (
    "MILESTONE",
    "MILESTONE_SIMPLE",
    "BID_NAME",
    "BID_NAME_1",
    "BID_NAME_12",
    "TRACT",
    "CDBG",
    "PRINTPRODUCTTYPES",
    "ReportedDateTime",
    "Beat",
    "ReportingDistrict",
    "DaysOld",
    "DayOfWeek",
    "HourOfDay",
)

__all__ = [
    "CRIME_FIELD_MAP",
    "DROPPED_NONADDRESS_COLUMNS",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "SLA_FIELD_MAP",
]
