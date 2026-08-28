"""Per-city field maps for Eugene, OR (US-225), imported by the shared parsers.

Eugene is a THREE-FEED PARTIAL metro on the City of Eugene ArcGIS Server at
``services3.arcgis.com/F7NiRLGNbA2hh7gE``:

* COMPLAINTS_311 — ``2020_2021CampingWorkOrders/FeatureServer/0`` (10,287
  rows): camping/encampment code-enforcement work orders from the PDD service
  request archive (companion ``HistoricalCampingWorkOrders`` 25,171 rows).
* SLA — ``Food_Service_Establishments_Updated_VIEW_CBE/FeatureServer/0``
  (752 rows): food service establishment business licenses (Code & Business
  Enforcement registry). Snapshot with no date column.
* DEEDS — ``CityLandDeeds/FeatureServer/0`` (2,873 rows): city-owned property
  deed records (acquisitions/dispositions). Companion deed layers:
  EasementDeeds (7,340), ROWDeeds (4,380).

Coordinate contract (pinned by tests):

* All three feeds rely on the **outSR=4326 geometry lift** — no
  ``latitude``/``longitude`` attribute candidates are declared. Deeds and 311
  store SR WKID 2914 (NAD83 Oregon State Plane North, ft); Food_Service
  stores SR 102100 (Web Mercator); ArcGISClient requests outSR=4326 so every
  layer returns WGS84 degrees. ``CityLandDeeds`` polygon rings are reduced to
  a centroid by ``ArcGISClient._geometry_to_lng_lat`` (Bend/King County
  precedent).
* Food_Service ``DisplayX``/``DisplayY`` attributes are native decimal-degree
  lat/lng but are NOT map candidates — the geometry lift is the sole
  coordinate source (Bend discipline), so no projected-coordinate accident.
* No date field exists on Food_Service (``watermark_col`` empty, snapshot
  mode, Modesto SLA precedent). 311 uses ``CreatedOn``; deeds use ``DATE_``.
* No PII to drop at the map: work-order free-text ``WorkDescri`` stays an
  unmapped description column (not an address candidate), and neither feed
  exposes owner/contact blocks that the shared chains would touch.
"""


COMPLAINTS_311_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["FID", "GlobalID"],
    "complaint_type": ["Title"],
    "created_date": ["CreatedOn"],
    "status": ["StatusText"],
}

SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["UID", "GlobalID"],
    "dba": ["Name"],
    "premises_name": ["Name"],
    "address_street": ["MatchAddr"],
    "status": ["Active"],
}

DEEDS_FIELD_MAP: dict[str, list[str]] = {
    "doc_id": ["CITYDEED", "OBJECTID_1"],
    "recorded_date": ["DATE_"],
    "doc_type": ["ACQDIS"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "311": COMPLAINTS_311_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Eugene, OR"

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "DEEDS_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "SLA_FIELD_MAP",
]