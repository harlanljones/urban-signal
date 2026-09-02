"""DatasetSpec-shaped plain dicts for the US-420 California state license registries.

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold.

ABC is a snap-only weekly CSV zip (``DailyExport-CSV.zip``) published by the
California ABC. The file carries a single preamble line ("Updated Wednesday
...") that CSVClient detects and strips automatically. The full 7.4 MB payload
is downloaded each cycle and filtered client-side by ``prem_county``.

CSLB is a statewide contractor master file from cslb.ca.gov — the endpoint
has not been verified live from this network (404 as of 2026-09-02), so the
specs carry ``verified=False`` and are not scheduled (NREL precedent).
"""

from src.config import settings
from src.producers.field_maps_ca_licenses import (
    CA_ABC_FIELD_MAP,
    CA_CSLB_FIELD_MAP,
)

# ── ABC ──────────────────────────────────────────────────────────────────────

ABC_ENDPOINT = "https://www.abc.ca.gov/wp-content/uploads/DailyExport-CSV.zip"
ABC_ZIP_MEMBER = "ABC-DailyDataExport.csv"


def abc_spec(counties: list[str]) -> dict:
    """ABC liquor license spec for one metro's county-slice."""
    where = " OR ".join(f"(prem_county = '{c}')" for c in counties)
    return {
        "endpoint": ABC_ENDPOINT,
        "platform": "csv",
        "watermark_col": "",
        "id_keys": ["file_number", "license_type"],
        "topic": settings.topic_sla,
        "interval_seconds": 86400.0,
        "producer_key": "sla",
        "expected_cadence_days": 7,
        "ingestion_mode": "snapshot",
        "where": where,
        "needs_geocode": True,
        "geocode_context": "CA",
        "order_by": "file_number ASC",
        "field_map": CA_ABC_FIELD_MAP,
        "zip_member": ABC_ZIP_MEMBER,
    }


# ── CSLB (unverified endpoint — client built to documented contract) ─────────

# The research probe (2026-08-30) recorded cslb.ca.gov as the host. The
# ``DataDownload.aspx`` page returned 404 on 2026-09-02; the client is built
# to the documented contract and exercised against fixtures. Do not schedule
# until a live endpoint is verified (NREL AFDC precedent).
CSLB_ENDPOINT = "https://www.cslb.ca.gov/Public_Registry/DataDownload.aspx"


def cslb_spec(counties: list[str]) -> dict:
    """CSLB contractor license spec for one metro's county-slice."""
    where = " OR ".join(f"(county = '{c}')" for c in counties)
    return {
        "endpoint": CSLB_ENDPOINT,
        "platform": "csv",
        "watermark_col": "",
        "id_keys": ["license_number"],
        "topic": settings.topic_sla,
        "interval_seconds": 86400.0,
        "producer_key": "sla",
        "expected_cadence_days": 90,
        "ingestion_mode": "snapshot",
        "where": where,
        "needs_geocode": True,
        "geocode_context": "CA",
        "order_by": "license_number ASC",
        "field_map": CA_CSLB_FIELD_MAP,
    }