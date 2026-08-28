"""Per-city field maps for Tucson, AZ (US-328), imported by the shared parsers.

Tucson is a ONE-FEED PARTIAL metro on the city ArcGIS Server: BUSLIC
(``PublicMaps/OpenData_EconomicDevelopment/MapServer/3``, Tier 2, ~93k
rows). Spellings do not match the shared Socrata chains, so the map lives
here as a leaf rather than growing ``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* SLA — native point geometry is the primary locator: every query requests
  ``outSR=4326`` and ``ArcGISClient._flatten_feature`` lifts it to
  ``latitude``/``longitude`` keys, which the parser's generic chain reads.
  No ``latitude``/``longitude`` candidates appear in the map — the layer's
  store SR is WKID 2868 (NAD83 Arizona East intl feet), so nothing except
  the outSR=4326 geometry lift may feed coordinates.
* Null-geometry rows exist live (e.g. OBJECTID 16 on the 2026-08-28
  re-probe: newest row, geometry null). They carry no latitude/longitude
  keys and fall to the ADR-0004 geocode supplement on ``FULLADDRESS`` —
  a clean single-field street string, not a parts-join.

Live-source text quirks (byte-verbatim fixtures in tests): several columns
are CHAR-padded by the source database — ``ACC_NUM`` (``"T3092419    "``),
``LIC_STATUS`` (``"Active              "``), ``STREETNUM``/``STREETDIR``/
``ZIP_CODE``. The SLA parser strips ``license_id`` itself; other fields keep
source padding. ``FULLADDRESS`` is not padded.

``ACC_NAME`` is the license-holder/account name and is the only name field
on the layer (OWN_TYPE=Individual rows are persons) — it maps to dba AND
premises_name because Tucson publishes no separate trade name.
"""


# Canonical SLA event field -> BUSLIC MapServer/3 column spellings.
# Live layer (2026-08-28): DT_START is the only esriFieldTypeDate column and
# arrives as epoch-ms; ArcGISClient converts it to ISO 8601 UTC on flatten.
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["ACC_NUM"],
    "dba": ["ACC_NAME"],
    "premises_name": ["ACC_NAME"],
    "license_type": ["LIC_TYPE", "NAIC_DESC"],
    "status": ["LIC_STATUS"],
    "effective_date": ["DT_START"],
    "address_street": ["FULLADDRESS"],
    "zipcode": ["ZIP_CODE"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Tucson, AZ"

# Columns that exist on the live layer and must never become map candidates.
# X/Y-shaped names are absent entirely; Shape/geometry stay server-side.
DROPPED_NONADDRESS_COLUMNS: tuple[str, ...] = (
    "STREETNUM",
    "STREETDIR",
    "STREETNAM",
    "STREETSUF",
    "APT",
    "ADDRESS",
    "Shape",
    "GlobalID",
)

__all__ = [
    "DROPPED_NONADDRESS_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "SLA_FIELD_MAP",
]
