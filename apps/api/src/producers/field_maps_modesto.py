"""Per-city field maps for Modesto, CA (US-231), imported by the shared parsers.

Modesto is a ONE-FEED PARTIAL metro on the city's ArcGIS Enterprise server
(``gis.modestogov.com/hosting``, ArcGIS 12.1): Business Licenses
(``ExternalServices/Map_Layer_Service_External/FeatureServer/7`` — live
2026-08-28, 4,574 rows). Spellings do not match the shared Socrata chains,
so the map lives here as a leaf rather than growing
``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* SLA — native point geometry is the primary locator: every query requests
  ``outSR=4326`` and ``ArcGISClient._flatten_feature`` lifts it to
  ``latitude``/``longitude`` keys, which the parser's generic chain reads.
  No ``latitude``/``longitude`` candidates appear in the map — the layer's
  store SR is WKID 102643 (NAD83 California Zone 3 state plane, US survey
  feet), so nothing except the outSR=4326 geometry lift may feed
  coordinates. The attributes carry no X/Y pair at all, so unlike Aurora
  no ``state_plane_*`` spec keys are declared (Tucson precedent).
* Null-geometry rows exist live (214 of 4,574 ≈ 4.7% on the 2026-08-28
  pull). ``needs_geocode`` stays False: the mapped address is a street
  string without a house number (see below), which fails the ADR-0004
  confidence gate (MC311 precedent) — null-geometry rows drop instead of
  geocoding.

Live-source schema quirks (byte-verbatim fixtures in tests):

* There is **no license-class column** (no type/status/NAICS anywhere on
  the layer), so ``license_type`` is deliberately NOT a map candidate.
  The shared parser's legacy default ("On-Premises Liquor") lands on every
  Modesto event — the registration caveat the spine hold must carry.
* There is **no date column**, so the feed registers as a snapshot with
  an empty watermark and alarm-exempt staleness (KC SLA precedent).
* The address is split into ``LOCSTNUM`` (house number) + ``LOCSTADDR1``
  (street) with no composed column; the shared SLA chain has no parts
  join, so ``address_street`` maps to ``LOCSTADDR1`` alone and
  ``LOCSTNUM``/``LOCSUITE`` stay unmapped.
* ``ACCNUM``-style zero padding: ``ACCOUNTNUM`` is a 7-char zero-padded
  string ("0000563") and is kept verbatim as the license id (SD
  account_key precedent); the parser stringifies it as-is.
* ``BUSNAME`` is the only name field on the layer — it maps to dba AND
  premises_name because Modesto publishes no separate trade name
  (Tucson precedent).

PII/unused columns are dropped at the map: LOCPHNUM (business phone) is
never a candidate.
"""


# Canonical SLA event field -> Business Licenses FeatureServer/7 column
# spellings. Live layer (2026-08-28): OBJECTID is the OID, geometry is the
# coordinate source, no esriFieldTypeDate column exists.
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["ACCOUNTNUM"],
    "dba": ["BUSNAME"],
    "premises_name": ["BUSNAME"],
    "address_street": ["LOCSTADDR1"],
    "zipcode": ["LOCZIP1"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Modesto, CA"

# Columns that exist on the live layer and must never become map candidates:
# LOCPHNUM is the business phone (unused), LOCCITY is the data-entry variant
# field ("MODESTO" / "MODESTO BRM ZIP" / "MODESTO DR" / ""), LOCST is a
# constant "CA", and LOCSTNUM/LOCSUITE/LOCZIP2 are address parts the shared
# SLA chain cannot join (see module docstring).
DROPPED_NONADDRESS_COLUMNS: tuple[str, ...] = (
    "LOCSTNUM",
    "LOCSUITE",
    "LOCCITY",
    "LOCST",
    "LOCZIP2",
    "LOCPHNUM",
    "GlobalID",
)

__all__ = [
    "DROPPED_NONADDRESS_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "SLA_FIELD_MAP",
]
