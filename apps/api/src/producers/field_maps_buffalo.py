"""Per-city field maps for Buffalo, NY (US-349), imported by the shared parsers.

Buffalo is a ONE-FEED PARTIAL metro on Socrata (``data.buffalony.gov``):
Restaurant Licenses (``4pp3-qkuj``, Tier 1). The spellings do not match the
shared Socrata chains (``licenseno``/``issdttm``/``descript``/``businessname``),
so the map lives here as a leaf rather than growing
``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* SLA — native ``latitude``/``longitude`` columns are **WGS84 geographic
  degrees** and match the ``location`` Point geometry on every probed row.
  They are the ONLY coordinate candidates: the ``gpsx``/``gpsy`` columns are
  **mixed CRS in one live dataset** (re-probe 2026-08-27 found WGS84 degree
  values on some rows — e.g. ``-78.87831433`` — and NY State Plane feet on
  others — e.g. ``1063508.89``). ``gpsx``/``gpsy`` must never become map
  candidates.
* ``neighborhood`` (source-maintained: "Elmwood Bryant", "Genesee-Moselle",
  "North Park", …) is mapped to the ``borough`` canonical slot so it passes
  through as the row's source neighborhood.
"""

SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["licenseno", "uniqkey"],
    "dba": ["businessname"],
    "premises_name": ["businessname"],
    "license_type": ["descript", "code"],
    "effective_date": ["issdttm"],
    "expiration_date": ["expdttm"],
    "status": ["licstatus"],
    "address_street": ["address"],
    "borough": ["neighborhood"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SLA_FIELD_MAP,
}

# Columns that exist on the live feed but must never become map candidates:
# gpsx/gpsy carry mixed CRS (WGS84 on some rows, State Plane feet on others);
# licensedttm/statusdttm are not the issuance stream (issdttm is); expdttm is
# an expiration, pinned via the expiration_date slot above.
NEVER_CANDIDATE_COLUMNS: tuple[str, ...] = (
    "gpsx",
    "gpsy",
    "licensedttm",
    "statusdttm",
)

__all__ = [
    "FIELD_MAP",
    "NEVER_CANDIDATE_COLUMNS",
    "SLA_FIELD_MAP",
]
