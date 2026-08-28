"""Per-city field maps for Bozeman, MT (US-236), imported by the shared parsers.

Bozeman is a TWO-FEED metro on the City of Bozeman's ArcGIS stack
(``gisweb.bozeman.net`` + hosted ``services3.arcgis.com`` under AGO org
``f4hk1qcfxRJ0L2BU``):

* PERMITS — ``BP_Comm_Dev_Report_Data_view/FeatureServer/0`` (Tier 1,
  24,338 rows). The public view behind the Building Permit Data Dashboard; it
  carries no owner/contractor PII (a cleaned view of the Internal
  ``Building_Permits/MapServer``). Daily issuance watermark.
* CRIME — ``BPD_CFS_Public_30_Days/FeatureServer/0`` (Tier 1, 5,202 rows,
  rolling 30-day calls-for-service window; ADR 0004 satisfied — native point
  geometry on every captured row).

Coordinate contract (pinned by tests):

* PERMITS — coordinates come from **native point geometry** requested with
  ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts it to
  ``latitude``/``longitude`` keys, which the producer's generic chain reads.
  The ``LATITUDE``/``LONGITUDE`` *attributes* are **Montana State Plane
  (NAD83 26912) feet**, not degrees (live values ≈ 5.06e6 / 4.9e5), and are
  deliberately NOT candidates — mapping them would emit feet as degrees. The
  producer's projected-coordinate guard is a second net behind that.
* CRIME — native point geometry, already WGS84 (the hosted layer's store SR
  is 102100/3857); outSR=4326 is honored on query.
* No site-zip column exists on either layer, so ``zipcode`` stays undeclared
  (``LOCATION_ID`` is a parcel key, not a zip). No neighborhood/district
  column exists either (Omaha discipline): ``borough`` stays undeclared and
  division resolution comes from coordinates at ingest.

PII is dropped at the map: the Internal Building_Permits MapServer carries
owner/contractor columns (CONTRACTOR_NAME/EMAIL/PHONE, OWNER_*), but the
registered view does not — the view columns are pinned here.
"""


# Canonical permit event field -> BP_Comm_Dev_Report_Data_view/FeatureServer/0
# column spellings. Live view (2026-08-28): OBJECTID is the OID,
# PERMIT_NUMBER the id head, PERMIT_ISSUE_DATE the daily watermark.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["PERMIT_NUMBER", "APPLICATION_NUMBER", "OBJECTID"],
    "issuance_date": ["PERMIT_ISSUE_DATE"],
    "filing_date": ["APPLICATION_DATE"],
    "status": ["PERMIT_STATUS", "APPLICATION_STATUS"],
    "job_type": ["PERMIT_TYPE", "APPLICATION_TYPE"],
    "cost": ["VALUATION"],
    "address_street": ["LOCATION"],
    "proposed_units": ["New_Dwelling_Units"],
}

# Canonical crime event field -> BPD_CFS_Public_30_Days/FeatureServer/0 column
# spellings. Live layer (2026-08-28): INCIDENT_NUMBER is the id head, DATE the
# daily watermark, ALL_CALL_TYPES the type text ("NOISE - NOISE" etc.).
CRIME_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["INCIDENT_NUMBER", "CASE_NUMBER", "OBJECTID"],
    "offense_type": ["ALL_CALL_TYPES", "PRIMARY_CODE", "PRIMARY_DESCRIPTION"],
    "occurred_date": ["DATE"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Bozeman, MT"

# Columns that exist on the live feeds and must never become map candidates.
# LATITUDE/LONGITUDE are Montana State Plane (NAD83 26912) feet, not degrees;
# TIME is the day-of-incident time string (DATE carries the day); RESPONDING_AGENCIES
# is operational staffing, not geography.
DROPPED_NONADDRESS_COLUMNS: tuple[str, ...] = (
    "LATITUDE",
    "LONGITUDE",
    "TIME",
    "RESPONDING_AGENCIES",
    "GlobalID",
    "Shape",
)

__all__ = [
    "CRIME_FIELD_MAP",
    "DROPPED_NONADDRESS_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]
