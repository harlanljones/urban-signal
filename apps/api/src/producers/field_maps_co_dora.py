"""Field maps for the US-421 Colorado DORA state license super-feeds.

LEAF module — NOT imported by the shared producers at runtime. In production
each map is merged into the owning city's ``CityRegistration``
``datasets[FeedType.SLA].field_map`` in ``src/spatial/city_registry.py`` (the
spine) when the orchestrator applies the interlock; this file proves the
proposed spellings resolve through the unmodified ``sla_licenses_producer``
and hands the spine a copy-pasteable contract. Mirrors the TX TREC/TDLR
precedent (``field_maps_tx_trec.py`` / ``tx_trec_specs.py``, US-397).

Sources, live-verified 2026-09-03 from this host against ``data.colorado.gov``:

- CO DORA Professional & Occupational Licenses ``7s5z-vewr`` — statewide
  register of ~129k rows covering architects, engineers, accountants, health
  professions, and trades. Fields are ``lastname``/``firstname``/``entityname``
  (individuals carry no ``entityname``; businesses carry no first/last name),
  ``city``/``state``/``mailzipcode`` (no county column, no address, no
  lat/lng — city-only geography), ``licensetype`` (short code, e.g. ``COS``,
  ``APN``), ``licensenumber``, ``licensefirstissuedate`` (ISO timestamp text,
  sortable — the watermark), ``licenselastreneweddate``,
  ``licenseexpirationdate``, ``licensestatusdescription``. The doc's claimed
  ``Entity Name``/``County`` fields do not both exist as claimed: ``county``
  is absent from this dataset (verified against the live schema via
  ``api/views/7s5z-vewr.json``), so the ``where`` clause and ``borough`` field
  ride ``city`` instead, matching the CO_LIQUOR/CO_APPROVED precedent in
  ``state_license_specs.py``.
- CO DORA Licensed Real Estate Professionals ``4zse-6bnw`` — the ticket's
  cited id ``m4y3-x47v`` 404s on data.colorado.gov (retired/renamed); this is
  the live current dataset ("Licensed Real Estate Professionals in
  Colorado") with the equivalent schema: ``licensefirstissuedate`` here is
  ``MM/DD/YYYY`` text (not sortable server-side), so the owning spec runs in
  snapshot mode (OR CCB precedent) rather than incremental.

Both datasets lack lat/lng and street-address columns — city/state/zip only
— so the owning specs declare ``needs_geocode=True`` with ``geocode_context``
(the ADR 0004 geocode path), matching the TX TABC precedent.

``licensee_name_ns`` NAMESPACING (composed, not namespaced by license_type):
neither dataset has one column carrying a usable premises name for both
individuals and entities, so each spec's endpoint composes
``coalesce(entityname, trim(firstname || ' ' || lastname)) as
licensee_name_ns`` (verified live) alongside the standard
``'<ns>:' || licensetype as license_type_ns`` namespacing trick from the TX
TREC/TABC precedent. httpx merges the client's pagination params with the
URL's ``$select`` (verified live through ``SocrataClient.paginate``), so no
producer machinery is needed.

Canonical fields mirror the chains in ``sla_licenses_producer`` /
``field_maps.first_mapped``: license_id, license_type, effective_date,
expiration_date, premises_name, status, borough, zipcode. Keyed to the
FeedType *value* string ("sla") semantics of ``field_maps.resolve_field_map``.
"""

CO_DORA_OCCUPATIONAL_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["licensenumber"],
    "license_type": ["license_type_ns"],
    "effective_date": ["licensefirstissuedate"],
    "expiration_date": ["licenseexpirationdate"],
    "premises_name": ["licensee_name_ns"],
    "status": ["licensestatusdescription"],
    "borough": ["city"],
    "zipcode": ["mailzipcode"],
}

CO_DORA_REALESTATE_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["licensenumber"],
    "license_type": ["license_type_ns"],
    "effective_date": ["licensefirstissuedate"],
    "expiration_date": ["licenseexpirationdate"],
    "premises_name": ["licensee_name_ns"],
    "status": ["licensestatus"],
    "borough": ["city"],
    "zipcode": ["zipcode"],
}

FIELD_MAPS: dict[str, dict[str, list[str]]] = {
    "co_dora_occupational": CO_DORA_OCCUPATIONAL_FIELD_MAP,
    "co_dora_realestate": CO_DORA_REALESTATE_FIELD_MAP,
}
