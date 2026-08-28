"""Per-city field maps for Santa Fe, NM (US-241), imported by the shared parsers.

Santa Fe is a ONE-FEED PARTIAL metro on the City of Santa Fe ArcGIS Online
hosted FeatureServer at ``services7.arcgis.com/p0Gk2nDbPs7KEqSZ``:
COMPLAINTS_311 (``CRM_Report_A_Problem_New_Public/FeatureServer/0``, Tier 1,
daily).

Coordinate contract (pinned by tests):

* COMPLAINTS_311 — coordinates come from **native point geometry** requested
  with ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts them to
  ``latitude``/``longitude`` keys, which the producer's generic chains read.
  The layer's spatial reference is WGS84 (wkid 4326) — all 2,765 live rows
  carry geometry (0 null geometries on probe). No ``latitude``/``longitude``
  attribute candidates are declared.
* ``CreationDate`` (esriFieldTypeDate) is the daily watermark and
  ISO-normalizes in the ArcGIS client.
* ``resolved_on`` is an ``esriFieldTypeString`` column (always null on live
  probe) — NOT mapped as ``closed_date``; the producer's chain lands on None
  honestly.
* No site-zip, address, or neighborhood column exists on the feed, so
  ``zipcode``, ``incident_address``, and ``borough`` stay undeclared (Omaha
  discipline): division resolution comes from coordinates at ingest, and
  ``source_neighborhood`` passes through as None.

PII is dropped at the map: the layer's field list is minimal (objectid,
globalid, problemtype, problem2, status, resolved_on, CreationDate,
field_notes) — none of the columns are PII candidates, so no drop list is
declared.
"""


COMPLAINTS_311_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["globalid", "objectid"],
    "complaint_type": ["problemtype"],
    "created_date": ["CreationDate"],
    "status": ["status"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "311": COMPLAINTS_311_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Santa Fe, NM"

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
]