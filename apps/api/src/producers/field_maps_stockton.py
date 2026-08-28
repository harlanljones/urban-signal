"""Per-city field maps for Stockton, CA (US-230).

Stockton is a ONE-FEED PARTIAL metro on the city's own ArcGIS Server
(``gisportal.stocktonca.gov/arcgis2``): SLA — the liquor-license layer
(``OpenCounter/OpenCounterMap/MapServer/7``, Tier 2, 1,363 rows). Spellings
do not match the shared Socrata chains, so the map lives here as a leaf
rather than growing ``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* SLA — native point geometry is the primary locator: every query requests
  ``outSR=4326`` and ``ArcGISClient._flatten_feature`` lifts it to
  ``latitude``/``longitude`` keys, which the parser's generic chain reads.
  No ``latitude``/``longitude`` candidates appear in the map — the layer's
  store SR is WKID 102643 / latest 2227 (NAD83 California Zone 3, US survey
  feet), and unlike Aurora the layer carries NO X/Y attribute columns, so
  nothing except the outSR=4326 geometry lift can feed coordinates. Every
  live row carries geometry (``Shape IS NULL`` count = 0/1,363 at probe);
  ``needs_geocode`` is declared spec-side as the ADR-0004 supplement for
  any future null-geometry rows on ``PremiseAddress``.
* ``PremiseZipcode`` is the mailing-zip trap: it holds the license
  holder's MAILING zip (the newest row at 950 W 11th St, Stockton carries
  "95376" / MailCity "TRACY"), never the premise zip. It stays unmapped —
  the SLA event has no zip field, and the ``Mail*`` block below is dropped
  wholesale so no mailing field can become a map candidate.
* ``PremiseName`` (trade name) is often a single space; ``OwnerName`` (the
  ABC license holder) is consistently populated. dba keeps the source
  bytes byte-verbatim; premises_name maps to the owner.
* ``LicenseType`` is the raw CA-ABC type code as a string ("20", "47", ...)
  — analytics-side classification.
"""


# Canonical SLA event field -> liquor MapServer/7 column spellings.
# Live layer (2026-08-28): OriginalIssueDate and ExpirationDate are the
# only esriFieldTypeDate columns and arrive as epoch-ms; ArcGISClient
# converts them to ISO 8601 UTC on flatten.
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["FileNumber", "OBJECTID"],
    "dba": ["PremiseName"],
    "premises_name": ["OwnerName"],
    "license_type": ["LicenseType", "LicenseCode"],
    "status": ["Status"],
    "effective_date": ["OriginalIssueDate"],
    "expiration_date": ["ExpirationDate"],
    "address_street": ["PremiseAddress", "PremiseAddress2"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Stockton, CA"

# Columns that exist on the live layer and must never become map
# candidates. The Mail* block is the license holder's mailing address
# (person/place PII with no premise meaning), PremiseZipcode carries
# mailing zips, and PremiseCensusTract is a tract label.
DROPPED_MAIL_COLUMNS: tuple = (
    "MailAddress",
    "MailAddress2",
    "MailCity",
    "MailState",
    "MailZipcode",
    "PremiseZipcode",
    "PremiseCensusTract",
    "Shape",
)

__all__ = [
    "DROPPED_MAIL_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "SLA_FIELD_MAP",
]
