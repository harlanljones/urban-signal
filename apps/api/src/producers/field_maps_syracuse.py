"""Per-city field maps for Syracuse, NY (US-352), imported by the shared parsers.

Syracuse is a ONE-FEED PARTIAL metro on the city's ArcGIS Hub (data.syrgov.net,
AGOL org services6.arcgis.com/bdPqSfflsdgFRVVM): the Syracuse Rental Registry
(FeatureServer/0, Tier 1). Permits are frozen (2025-08-16 max), 311 and deeds
are absent — nothing else is registered.

Coordinate contract (pinned by tests):

* SLA — native WGS84 ``Latitude``/``Longitude`` attribute columns verified
  live (2026-08-27) at 500/500 completeness on the newest window. NOT the
  lowercase keys the generic fallback chains read, so the map is what makes
  the native coordinates reach the parser. ``needs_geocode`` stays False —
  no ADR 0004 dependency.

PII is dropped at the map: ``RR_contact_name`` and ``pc_owner`` never become
candidates (the probe's explicit drop-at-ingest list).
"""


# Canonical SLA event field -> Syracuse_Rental_Registry/FeatureServer/0
# column spellings. Fresh applications carry ``completion_type_name = null``
# and fall to ``NeedsRR``; granted cards read e.g. "Rental Registry Card
# Issued" / "Family Based Exemption Granted". ``RR_contact_name`` /
# ``pc_owner`` are deliberately absent (PII).
SYRACUSE_SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["SBL"],
    "license_type": ["completion_type_name", "NeedsRR"],
    "effective_date": ["RR_app_received"],
    "expiration_date": ["valid_until"],
    "status": ["RRisValid"],
    "address_street": ["PropertyAddress"],
    "latitude": ["Latitude"],
    "longitude": ["Longitude"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SYRACUSE_SLA_FIELD_MAP,
}

# Columns that exist on the live layer and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "RR_contact_name",
    "pc_owner",
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "SYRACUSE_SLA_FIELD_MAP",
]
