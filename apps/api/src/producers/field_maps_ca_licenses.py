"""Field maps for the US-420 California state license registries.

LEAF module — NOT imported by the shared producers at runtime. In production
each map is merged into the owning city's ``CityRegistration``
``datasets[FeedType.SLA].field_map`` in ``src/spatial/city_registry.py`` (the
spine) when the orchestrator applies the interlock; this file proves the
proposed spellings resolve through the unmodified ``sla_licenses_producer``
and hands the spine a copy-pasteable contract.

Sources, all live-verified 2026-09-02 from this host:

- CA ABC DailyExport-CSV (abc.ca.gov) — premise address only, so the owning
  specs declare ``needs_geocode``. Classify on ``type_status``.
- CA CSLB contractor master file (cslb.ca.gov) — business address only,
  ``needs_geocode``.

license_type NAMESPACING: ``license_type_ns`` is composed from the raw
``License Type`` or ``classification`` column at the spec level, so the field
map targets the pre-composed value.
"""

CA_ABC_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["file_number"],
    "license_type": ["license_type"],
    "effective_date": ["type_orig_iss_date"],
    "expiration_date": ["expir_date"],
    "premises_name": ["primary_name"],
    "dba": ["dba_name"],
    "address_street": ["prem_addr_1", "prem_addr_2"],
    "status": ["type_status"],
    "borough": ["prem_city"],
    "zipcode": ["prem_zip"],
}

CA_CSLB_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_number"],
    "license_type": ["classification"],
    "effective_date": ["issue_date"],
    "expiration_date": ["expiration_date"],
    "premises_name": ["business_name"],
    "dba": ["business_name"],
    "address_street": ["address"],
    "status": ["status"],
    "borough": ["city"],
    "zipcode": ["zip"],
}

FIELD_MAPS: dict[str, dict[str, list[str]]] = {
    "ca_abc": CA_ABC_FIELD_MAP,
    "ca_cslb": CA_CSLB_FIELD_MAP,
}