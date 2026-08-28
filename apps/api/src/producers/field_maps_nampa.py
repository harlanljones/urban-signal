"""Per-city field maps for Nampa, ID (US-243), imported by the shared parsers.

Nampa is a ONE-FEED PARTIAL metro: ROW road closure permits
(``PublicRoadClosures/FeatureServer/3`` ``ROW_Road_Closure``, Tier 1
quality but small — 76 rows, polyline geometry). Building permits live on
Tyler EnerGov SaaS (``nampaid-energovpub.tylerhost.net``, no public REST
API), 311/SLA/deeds are absent — never registered. Spellings do not match
the shared chains, so the map lives here as a leaf rather than growing
``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* Coordinates come from **native polyline geometry** requested with
  ``outSR=4326``; ``ArcGISClient._flatten_feature`` reduces the path points
  to a single representative (mean) ``latitude``/``longitude`` pair. The
  producer's generic chains read those keys. No ``latitude``/``longitude``
  candidates appear in the map — the layer's native CRS is Idaho State
  Plane West (wkid 102670 / latest 2243, feet) and nothing except the
  outSR=4326 geometry lift may feed coordinates.
* ``CreationDate`` is the esriFieldTypeDate watermark and ISO-normalizes in
  the ArcGIS client; ``starttime``/``endtime`` are the planned closure
  window (also esri dates) but are not mapped (no canonical permit
  field for them).
* ``identifier`` carries the permit ID (``ROW-08302-2026``) and is the
  ``id_keys`` head; ``OBJECTID`` is the OID fallback.
* No site-zip column exists, no parcel/APN column, and no
  neighborhood/district column — ``zipcode``, ``bbl``, and ``borough`` stay
  undeclared (Omaha discipline).
* ``street`` is the street-name fallback address; geometry is always
  present on live rows so ``needs_geocode=False`` (ADR 0004).

PII is handled by never mapping contact fields: ``pocname``/``pocemail``/
``pocphone`` (right-of-way permit contact) and ``permitcontractor`` are
never candidates.
"""


# Canonical permit event field -> ROW_Road_Closure/FeatureServer/3 column
# spellings. Live layer (2026-08-28): OBJECTID is the OID, geometry is the
# coordinate source, CreationDate is the system watermark, identifier is the
# permit ID. type_ is the closure kind ("Road Closure") and maps through the
# producer's job-type classifier to OT honestly.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["identifier", "OBJECTID"],
    "issuance_date": ["CreationDate"],
    "status": ["Status"],
    "job_type": ["type_", "subtype_"],
    "address_street": ["street"],
}

STREET_CUT_FIELD_MAP: dict[str, list[str]] = PERMITS_FIELD_MAP

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Nampa, ID"

# Columns that exist on the live feed and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "pocname",
    "pocemail",
    "pocphone",
    "permitcontractor",
    "Creator",
    "Editor",
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "STREET_CUT_FIELD_MAP",
]