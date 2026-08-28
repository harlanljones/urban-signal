"""Per-city field maps for Santa Rosa, CA (US-247), imported by the shared parsers.

Santa Rosa is a ONE-FEED PARTIAL metro: the Sonoma County Sheriff's Office
Incident Data (Socrata ``3rsj-iche`` on ``data.sonomacounty.ca.gov``, Tier 1,
daily). The city's live data is PowerBI-only behind ``Insights.SRCity.org``;
the city's AGOL org (santarosa.maps.arcgis.com) holds only stale snapshots
(Building Permits last updated 2018, Calls for Service last 2020). County
planning permits (m689-iiuu) are unincorporated-only and address-only with
no advancing watermark (max started 2025-05-30). Permits, 311, SLA, and deeds
all stay Tier 3 — only crime is registered.

Coordinate contract (pinned by tests):

* CRIME — coordinates come from the Socrata ``location`` point container
  (``{latitude, longitude, human_address}`` dict). The
  ``CrimeIncidentsProducer.parse_socrata_row`` parser reads this via its
  generic point-container fallback at line 185 (``loc.get("latitude")`` /
  ``loc.get("longitude")``). Do NOT map ``latitude``/``longitude`` in the
  field map — the point container is the authoritative source.

PII is dropped at the map: ``agency_code`` and ``agency`` are internal
identifiers, never candidates. No owner/contact columns exist on the layer.
"""


CRIME_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["id", "incident_number"],
    "offense_type": ["incident_type"],
    "occurred_date": ["date_time"],
    "reported_date": ["upload"],
    "borough": ["city"],
    "address": ["intersection", "location_address"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Santa Rosa, CA"

DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "agency_code",
    "agency",
)

__all__ = [
    "CRIME_FIELD_MAP",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
]