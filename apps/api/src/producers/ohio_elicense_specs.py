"""DatasetSpec-shaped plain dicts for the US-425 Ohio eLicense registry.

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold.

The research probe (2026-08-30) recorded DataOhio's "State of Ohio Licensure -
Individual" CSV as a Tier 2 Batch ETL candidate. The endpoint was NOT
verifiable from this host on 2026-09-02 (``data.ohio.gov`` returned 404 on all
paths), so the spec is documented as unverified (NREL AFDC precedent) and is
NOT registered or scheduled until a live endpoint is confirmed. See ``field_maps_ohio_elicense.py`` for the probe-recorded column
mapping and ``docs/research/midwest-rust-belt-expansion-probe-2026-08-30.md``
for the full probe analysis.

Filter partition: municipality (Akron, Canton, Youngstown, Cleveland, Dayton,
Toledo, Columbus, Cincinnati).
"""

from src.producers.field_maps_ohio_elicense import OHIO_ELICENSE_FIELD_MAP


def ohio_elicense_spec(city: str) -> dict:
    """Ohio eLicense SLA spec for one city slice."""
    return {
        "endpoint": "https://data.ohio.gov/resource/state-of-ohio-licensure-individual.csv",
        "platform": "csv",
        "watermark_col": "original_issue_date",
        "id_keys": ["license_number"],
        "topic": "raw.municipal.sla",
        "interval_seconds": 86400.0,
        "producer_key": "sla",
        "expected_cadence_days": 7,
        "ingestion_mode": "incremental",
        "where": f"city = '{city.upper()}'",
        "needs_geocode": True,
        "order_by": "original_issue_date DESC",
        "field_map": OHIO_ELICENSE_FIELD_MAP,
    }