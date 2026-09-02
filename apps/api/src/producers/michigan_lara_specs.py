"""DatasetSpec-shaped plain dicts for the US-425 Michigan LARA/MLCC registries.

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold.

The research probe (2026-08-30) recorded LARA License Lists & Reports (CSV)
and MLCC Active Liquor License Queries as Tier 2 Batch ETL candidates. The
endpoint was NOT verifiable from this host on 2026-09-02
(``michigan.gov/lara`` returned 403/302; ``mlcc.michigan.gov`` failed DNS),
so the spec is documented as unverified (NREL AFDC precedent) and is NOT
registered or scheduled until a live endpoint is confirmed. See ``field_maps_michigan_lara.py`` for the probe-recorded column mapping and
``docs/research/midwest-rust-belt-expansion-probe-2026-08-30.md`` for the full
probe analysis.

Filter partition: city (Lansing, East Lansing, Flint, Ann Arbor, Grand Rapids,
Detroit).
"""

from src.producers.field_maps_michigan_lara import MICHIGAN_LARA_FIELD_MAP


def michigan_lara_spec(city: str) -> dict:
    """Michigan LARA SLA spec for one city slice."""
    return {
        "endpoint": "https://www.michigan.gov/lara/-/media/Project/Websites/lara/DOES/BOIS/BOIS-License-List/CSL-Licensee-List.csv",
        "platform": "csv",
        "watermark_col": "issue_date",
        "id_keys": ["license_number"],
        "topic": "raw.municipal.sla",
        "interval_seconds": 86400.0,
        "producer_key": "sla",
        "expected_cadence_days": 7,
        "ingestion_mode": "incremental",
        "where": f"city = '{city}'",
        "needs_geocode": True,
        "order_by": "issue_date DESC",
        "field_map": MICHIGAN_LARA_FIELD_MAP,
    }