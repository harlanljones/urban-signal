"""Per-city field maps for Missoula, MT (US-235 leaf), imported by the shared
parsers.

Missoula is a ONE-FEED PARTIAL metro on the city's official ArcGIS org
(``services.arcgis.com/HfwHS0BxZBQ1E5DY``, behind the ``missoulamaps-
cityofmissoula.hub.arcgis.com`` Hub): PERMITS — ``AddressesWithPermits_mso``
FeatureServer/0 (122,448 rows). Column spellings do not match the shared
Socrata chains, so the map lives here as a leaf rather than growing
``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* PERMITS — native point geometry requested with ``outSR=4326``; the layer's
  store SR is **WKID 102700 (NAD83 Montana State Plane, meters)** and the
  host honors the outSR request (live fixtures come back as degrees). No
  ``latitude``/``longitude`` candidates appear in the map; the layer has no
  projected X/Y *attribute* columns to mis-map. Null-geometry rate is 0 in a
  3,000-row live scan, so ``needs_geocode`` stays spec-side False and the
  geometry lift is the sole locator.

Date contract (pinned by tests):

* ``ApplicationDate`` (the watermark) and ``RecordStatusDate`` are
  ``esriFieldTypeDate`` — epoch-ms, converted to ISO 8601 UTC on flatten.
  Newest ApplicationDate on the live probe is 1787788800000 =
  ``2026-08-27T00:00:00+00:00``, with 0 nulls and 0 future sentinels.
* The layer has NO issuance-date column and NO cost/valuation column —
  ``issuance_date`` and ``cost`` are simply absent from the map, and the
  producer honestly emits ``issuance_date=None`` / ``estimated_cost=0.0``.
  ``RecordStatusDate`` is the status-change timestamp, NOT an issuance date,
  and is deliberately unmapped.
* ``B1_PER_TYPE`` (e.g. "Electrical", "Utility Excavation") doubles as the
  job-type signal; ``B1_PER_SUB_TYPE`` (e.g. "Water Service",
  "Sanitary Sewer Service") rides as the fallback candidate.

PII is none at the map: the layer carries no owner/contractor person-name
columns (unlike Anaheim's Accela surface) — ``Address``/``FullAddress`` are
street addresses only, and ``DescriptionOfWork`` is free-form work text.
"""


# Canonical permit event field -> AddressesWithPermits_mso/FeatureServer/0
# column spellings. Live layer (2026-08-28): RecordID is the stable permit id
# (e.g. "2026-MSS-SWR-00946"); OBJECTID is a rebuild-dependent row id (newest
# live row carries OBJECTID 1) and keeps dedup edge rows addressable.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["RecordID", "OBJECTID"],
    "filing_date": ["ApplicationDate"],
    "status": ["RecordStatus"],
    "job_type": ["B1_PER_TYPE", "B1_PER_SUB_TYPE"],
    "description": ["DescriptionOfWork"],
    "address_street": ["Address", "FullAddress"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Missoula, MT"

# No PII columns exist on the live layer (no owner/contractor/phone fields),
# so the dropped-column tuple is empty by design.
DROPPED_PII_COLUMNS: tuple[str, ...] = ()

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]