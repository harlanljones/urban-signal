"""Per-city field map for Laredo, TX (US-263), imported by the shared parsers.

Laredo is a ONE-FEED Tier-2 metro on CKAN 2.9.11 OpenGov
(``data.openlaredo.com``, resource ``61972510-7b8c-488a-9e88-b73b0112f496``):

* PERMITS — ``city-of-laredo-building-applications-permits-inspections`` →
  ``PERMITS ISSUED.xlsx`` / ``bpod1e.csv`` (91,198 rows back to 2022, CKAN
  datastore_active true, watermark ``PERMIT ISS. DATE`` timestamp newest
  2026-07-02T00:00:00, monthly bulk replace). Columns are Naviline
  spellings with trailing spaces on some keys; geometry is absent and
  the locator is the split address ``STREET NBR`` + ``STREET``.

Coordinate contract (pinned by tests):

* PERMITS — **no native geometry**. Coordinates come from the ADR-0004
  geocode path only (``needs_geocode=true``, ``geocode_context="Laredo, TX"``).
  The address candidate is the pair ``STREET NBR``/``STREET`` concatenated as
  ``f"{STREET NBR.strip()} {STREET.strip()}, Laredo, TX"`` (e.g. "801 PALOMA
  CT, Laredo, TX"). No ``latitude``/``longitude`` attribute candidates are
  declared — the geocoder is the sole coordinate source, matching the
  Boulder Table precedent for non-spatial sources.
* ``PERMIT ISS. DATE`` is the issuance timestamp and maps to both
  ``issuance_date`` and ``filing_date`` (Naviline issues on create for most
  permit types; no separate application-received column is exposed).
* ``VALUATION`` / ``TOTAL FEE`` carry cost; ``PERMIT TYPE DESC`` /
  ``APP TYPE DESC`` / ``Permit Group Type`` carry work type.

Staleness note — the live probe (2026-08-30) found newest 2026-07-02,
58 days behind with 0 in the trailing 30 days (86 in July, 1,650 in
60 days, 9,481 in 2026 YTD). The feed remains registrable as a monthly
batch under the 60-day tolerance, but the staleness flag is pinned here
and in ``docs/research/probe-laredo.md``.

PII is dropped at the map: ``CONTRACTOR NAME`` is a free-text contractor
or owner name and must never become a map candidate (Chandler
``DROPPED_PII_COLUMNS`` precedent).
"""

from src.spatial.cities.laredo import LAREDO_METRO_BBOX  # noqa: F401  (city context anchor)

# Canonical permit event field -> CKAN datastore column spellings.
# Live datastore (2026-08-30): column ids are the CKAN field names verbatim
# (e.g. "PERMIT ISS. DATE" contains a dot + spaces). The spine
# ``first_mapped`` treats "." as a nested-container separator, so dotted
# keys fail at the spine today — see stream log spine delta. The leaf
# therefore declares **sanitized** keys (dots removed, spaces → "_") and
# ships a normalizer (``normalize_laredo_row``) that the producer must
# call before ``first_mapped``. This matches the SocrataClient alias
# precedent and keeps the leaf runnable without a spine patch.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    # APP NBR (numeric) + APP YR composite key; _id is the CKAN row OID fallback.
    "job_id": ["APP_NBR", "APP_YR", "_id"],
    # Watermark column is timestamp; maps to both issuance and filing.
    "issuance_date": ["PERMIT_ISS_DATE"],
    "filing_date": ["PERMIT_ISS_DATE"],
    "status": ["PERMIT_STATUS_DESC", "PERMIT_STATUS", "APP_STAT_DESC", "APP_STATUS"],
    "job_type": ["APP_TYPE_DESC", "PERMIT_TYPE_DESC", "Permit_Group_Type", "Permit_Group_Tab"],
    "cost": ["VALUATION", "TOTAL_FEE", "PERMIT_FEE"],
    "valuation": ["VALUATION"],
    "total_fee": ["TOTAL_FEE"],
    # Split address — first_mapped picks the first truthy; the producer
    # concatenates STREET NBR + STREET when both present.
    "address_street": ["STREET", "STREET_NBR"],
    "street_number": ["STREET_NBR"],
    "street_name": ["STREET"],
    "description": ["APP_DESC", "Permit_Group_Type"],
    "permit_type": ["PERMIT_TYPE", "APP_TYPE"],
    "permit_sequence": ["PERMIT_SEQUENCE"],
    "borough": ["Permit_Group_Tab"],
}


def normalize_laredo_row(row: dict) -> dict:
    """Normalize a raw CKAN datastore row so its keys match PERMITS_FIELD_MAP.

    CKAN field ids contain dots and spaces (e.g. "PERMIT ISS. DATE"). The
    spine ``first_mapped`` treats dots as nesting, so the leaf normalizes
    by replacing dots/spaces with "_" and upper-casing to the map's
    sanitized keys. Both the original and normalized keys are kept so
    existing callers that pass raw rows keep working after the spine patch.
    """
    out: dict = dict(row)
    for k, v in list(row.items()):
        sanitized = k.replace(".", "").replace(" ", "_").replace("-", "_")
        # Collapse double underscores from dot+space removal.
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        sanitized = sanitized.strip("_")
        # Keep original key plus sanitized alias.
        if sanitized != k:
            out[sanitized] = v
            # Also keep upper variant for case-insensitive match
            out[sanitized.upper()] = v
    return out

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Laredo, TX"

# Columns that exist on the live feed and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "CONTRACTOR NAME",
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "normalize_laredo_row",
]
