"""DatasetSpec-shaped plain dicts for the US-421 Colorado DORA license registries.

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold; mirrors the ``tx_trec_specs.py`` precedent (US-397).

Both registries ride ``FeedType.SLA`` (household-formation / professional-
services proxy) through the shared ``sla_licenses_producer`` classify->
geocode->H3 path:

- CO DORA Professional & Occupational Licenses ``7s5z-vewr`` (data.colorado.gov)
  — statewide, ~129k rows. Watermark on native ``licensefirstissuedate`` (ISO
  timestamp text, server-sortable). City slice (``city = '<name>'`` — the
  live schema has no county column). ``co_occ:`` namespace.
- CO DORA Licensed Real Estate Professionals ``4zse-6bnw`` (data.colorado.gov)
  — the current live dataset for the real-estate registry (the ticket's cited
  id ``m4y3-x47v`` 404s / is retired). ``licensefirstissuedate`` here is
  ``MM/DD/YYYY`` text with no server-side chronological ordering, so this
  spec runs ``ingestion_mode="snapshot"`` (OR CCB precedent, US-372): a full
  city-slice pull per cycle whose cross-run id-dedup diff is the churn
  signal. ``co_re:`` namespace.

Both are city-name-only sources (no lat/lng, no street address):
``needs_geocode=True`` with ``geocode_context="CO"``, matching the TX TABC
precedent — the ADR 0004 geocoder recovers coordinates from city/state/zip
at parse time.

``licensee_name_ns`` composes ``coalesce(entityname, trim(firstname || ' '
|| lastname))`` because neither dataset carries one column usable for both
individual and business licensees (see ``field_maps_co_dora.py``).
``license_type_ns`` composes the standard ``'<ns>:' || licensetype``
namespace so flow features can distinguish registries sharing the SLA topic.
"""

from src.config import settings
from src.producers.field_maps_co_dora import (
    CO_DORA_OCCUPATIONAL_FIELD_MAP,
    CO_DORA_REALESTATE_FIELD_MAP,
)

_NAME_SELECT = (
    "coalesce(entityname, trim(firstname || ' ' || lastname)) as licensee_name_ns"
)

CO_DORA_OCCUPATIONAL_ENDPOINT = (
    "https://data.colorado.gov/resource/7s5z-vewr.json"
    f"?$select=*, {_NAME_SELECT}, 'co_occ:' || licensetype as license_type_ns"
)
CO_DORA_REALESTATE_ENDPOINT = (
    "https://data.colorado.gov/resource/4zse-6bnw.json"
    f"?$select=*, {_NAME_SELECT}, 'co_re:' || licensetype as license_type_ns"
)


def co_dora_occupational_spec(city: str) -> dict:
    """CO DORA professional & occupational licenses for one city slice."""
    return {
        "endpoint": CO_DORA_OCCUPATIONAL_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "licensefirstissuedate",
        "id_keys": ["licensenumber"],
        "topic": settings.topic_sla,
        "interval_seconds": 3600.0,
        "producer_key": "sla",
        "expected_cadence_days": 7,
        "ingestion_mode": "incremental",
        "where": f"city = '{city}'",
        "needs_geocode": True,
        "geocode_context": "CO",
        "order_by": "licensefirstissuedate DESC",
        "field_map": CO_DORA_OCCUPATIONAL_FIELD_MAP,
    }


def co_dora_realestate_spec(city: str) -> dict:
    """CO DORA licensed real estate professionals for one city slice.

    ``licensefirstissuedate`` is ``MM/DD/YYYY`` text with no server-side
    chronological ordering (Socrata 400s on ``to_fixed_timestamp``/``substr``
    conversions for this domain, same as the OR CCB precedent), so this spec
    is snapshot-mode: a full city-slice pull per cycle.
    """
    return {
        "endpoint": CO_DORA_REALESTATE_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "",
        "id_keys": ["licensenumber"],
        "topic": settings.topic_sla,
        "interval_seconds": 21600.0,
        "producer_key": "sla",
        "expected_cadence_days": 7,
        "ingestion_mode": "snapshot",
        "where": f"city = '{city}'",
        "needs_geocode": True,
        "geocode_context": "CO",
        "field_map": CO_DORA_REALESTATE_FIELD_MAP,
    }
