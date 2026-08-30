"""Field maps for the US-397 TX TREC/TDLR license registries.

LEAF module — NOT imported by the shared producers at runtime. In production
each map is merged into the owning city's ``CityRegistration``
``datasets[FeedType.SLA].field_map`` in ``src/spatial/city_registry.py`` (the
spine) when the orchestrator applies the interlock; this file proves the
proposed spellings resolve through the unmodified ``sla_licenses_producer``
and hands the spine a copy-pasteable contract.

Sources, all live-verified 2026-08-30 from this host (row counts + newest
watermarks in .streams/us397-tx-trec-tdlr.md):

- TX TREC Broker & Sales Agent License Holders ``s7ft-44qi`` (data.texas.gov)
  — 324,001-row daily stock feed. ``updated`` (ISO, native) is the watermark.
  Licensees are individuals: ``full_name`` is the premises name, there is no
  business/DBA column. ``county`` is the only geography (no street address),
  so the map declares no address_street/lat/lng — county-level covariates via
  ``geography_crosswalk``, not H3 points.
- TX TREC Applications for Initial License Issuance ``bf5n-799f``
  (data.texas.gov) — flow feed (formation leading indicator). ``updated`` is
  the watermark. ``application_id`` is the id; ``date_application_received`` /
  ``date_application_expires`` are the formation window. County-only geography.
- TX TDLR All Licenses ``7358-krk7`` (data.texas.gov) — 983,494 rows.
  ``license_expiration_date_mmddccyy`` is ``MM/DD/YYYY`` text (the producer's
  ``_parse_datetime`` handles ``%m/%d/%Y``). No native ``updated`` column, so
  the owning spec watermarks Socrata ``:updated_at`` (composed into
  ``$select``). ``business_county`` is the geography; ``owner_name`` is the
  premises name and ``business_name`` the DBA.

license_type NAMESPACING: ``license_type_ns`` does not exist on the sources —
each spec's endpoint carries
``?$select=*, '<ns>:' || license_type as license_type_ns`` so flow features can
distinguish registries sharing the SLA topic (httpx merges the client's
``$limit``/``$offset``/``$order``/``$where`` params with the URL's
``$select``; verified live through ``SocrataClient.paginate``). Zero producer
machinery.

Canonical fields mirror the chains in ``sla_licenses_producer`` /
``field_maps.first_mapped``: license_id, license_type, effective_date,
expiration_date, premises_name, dba, address_street, status, latitude,
longitude, borough. Keyed to the FeedType *value* string ("sla") semantics of
``field_maps.resolve_field_map``.
"""

TX_TREC_BROKER_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_number"],
    "license_type": ["license_type_ns"],
    "effective_date": ["original_license_date"],
    "expiration_date": ["license_expiration_date"],
    "premises_name": ["full_name"],
    "status": ["status"],
    "borough": ["county"],
}

TX_TREC_APP_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["application_id"],
    "license_type": ["license_type_ns"],
    "effective_date": ["date_application_received"],
    "expiration_date": ["date_application_expires"],
    "borough": ["county"],
}

TX_TDLR_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_number"],
    "license_type": ["license_type_ns"],
    "expiration_date": ["license_expiration_date_mmddccyy"],
    "premises_name": ["owner_name"],
    "dba": ["business_name"],
    "borough": ["business_county"],
}

FIELD_MAPS: dict[str, dict[str, list[str]]] = {
    "tx_trec_broker": TX_TREC_BROKER_FIELD_MAP,
    "tx_trec_app": TX_TREC_APP_FIELD_MAP,
    "tx_tdlr": TX_TDLR_FIELD_MAP,
}