"""DatasetSpec-shaped plain dicts for the US-397 TX TREC/TDLR license registries.

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold; the per-city placement is documented in
``.streams/us397-tx-trec-tdlr.md`` ("Spine delta").

All three registries ride ``FeedType.SLA`` (household-formation proxy) through
the shared ``sla_licenses_producer`` classify->geocode->H3 path:

- TX TREC Broker & Sales Agent License Holders ``s7ft-44qi`` (data.texas.gov)
  — daily stock feed (324,001 rows). Watermark on native ``updated`` ISO
  timestamp. County slice (``county = '<name>'``). ``trec_broker:`` namespace.
- TX TREC Applications for Initial License Issuance ``bf5n-799f``
  (data.texas.gov) — flow feed (formation leading indicator). Watermark on
  native ``updated``. County slice. ``trec_app:`` namespace.
- TX TDLR All Licenses ``7358-krk7`` (data.texas.gov) — 983,494 rows. No
  native ``updated`` column; watermark on Socrata ``:updated_at`` composed into
  ``$select`` (the childcare TX pattern, US-377). ``license_expiration_date_mmddccyy``
  is ``MM/DD/YYYY`` text handled by the producer's ``_parse_datetime``
  (``%m/%d/%Y``). ``tdlr:`` namespace.

All three are county-name-only sources: ``needs_geocode=False``, no lat/lng
in field maps. The county name flows through ``borough`` (``county`` or
``business_county``) and resolves via ``geography_crosswalk`` to county-level
covariates, NOT H3 point events. Null-coordinate events follow the DC Basic
Business Licenses precedent (US-134).

license_type NAMESPACING rides the endpoint string: SoQL
``$select=*, '<ns>:' || <type_col> as license_type_ns`` — httpx merges the
client's pagination params with the URL's ``$select`` (verified live through
``SocrataClient.paginate``), so no producer machinery is needed. For TDLR the
``$select`` also composes ``:updated_at`` (the watermark column).
"""

from src.config import settings
from src.producers.field_maps_tx_trec import (
    TX_TDLR_FIELD_MAP,
    TX_TREC_APP_FIELD_MAP,
    TX_TREC_BROKER_FIELD_MAP,
)

TX_TREC_BROKER_ENDPOINT = (
    "https://data.texas.gov/resource/s7ft-44qi.json"
    "?$select=*, 'trec_broker:' || license_type as license_type_ns"
)
TX_TREC_APP_ENDPOINT = (
    "https://data.texas.gov/resource/bf5n-799f.json"
    "?$select=*, 'trec_app:' || license_type as license_type_ns"
)
TX_TDLR_ENDPOINT = (
    "https://data.texas.gov/resource/7358-krk7.json"
    "?$select=*, 'tdlr:' || license_type as license_type_ns, :updated_at"
)


def tx_trec_broker_spec(county: str) -> dict:
    """TX TREC broker & sales agent license holders for one county slice."""
    return {
        "endpoint": TX_TREC_BROKER_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "updated",
        "id_keys": ["license_number"],
        "topic": settings.topic_sla,
        "interval_seconds": 3600.0,
        "producer_key": "sla",
        "expected_cadence_days": 1,
        "ingestion_mode": "incremental",
        "where": f"county = '{county}'",
        "needs_geocode": False,
        "order_by": "updated DESC",
        "field_map": TX_TREC_BROKER_FIELD_MAP,
    }


def tx_trec_app_spec(county: str) -> dict:
    """TX TREC applications for initial license issuance, one county slice (leading indicator)."""
    return {
        "endpoint": TX_TREC_APP_ENDPOINT,
        "platform": "socrata",
        "watermark_col": "updated",
        "id_keys": ["application_id"],
        "topic": settings.topic_sla,
        "interval_seconds": 3600.0,
        "producer_key": "sla",
        "expected_cadence_days": 1,
        "ingestion_mode": "incremental",
        "where": f"county = '{county}'",
        "needs_geocode": False,
        "order_by": "updated DESC",
        "field_map": TX_TREC_APP_FIELD_MAP,
    }


def tx_tdlr_spec(county: str) -> dict:
    """TX TDLR all licenses for one county slice (business_county, uppercase).

    ``license_expiration_date_mmddccyy`` is ``MM/DD/YYYY`` text; the producer's
    ``_parse_datetime`` handles it via ``%m/%d/%Y``. Watermark rides Socrata
    ``:updated_at`` (composed into ``$select``) because the dataset has no
    native ``updated`` column.
    """
    return {
        "endpoint": TX_TDLR_ENDPOINT,
        "platform": "socrata",
        "watermark_col": ":updated_at",
        "id_keys": ["license_number"],
        "topic": settings.topic_sla,
        "interval_seconds": 86400.0,
        "producer_key": "sla",
        "expected_cadence_days": 1,
        "ingestion_mode": "incremental",
        "where": f"business_county = '{county}'",
        "needs_geocode": False,
        "order_by": ":updated_at DESC",
        "field_map": TX_TDLR_FIELD_MAP,
    }