"""Field maps for the US-372 state liquor/contractor license registries.

LEAF module — NOT imported by the shared producers at runtime. In production
each map is merged into the owning city's ``CityRegistration``
``datasets[FeedType.SLA].field_map`` in ``src/spatial/city_registry.py`` (the
spine) when the orchestrator applies the interlock; this file proves the
proposed spellings resolve through the unmodified ``sla_licenses_producer``
and hands the spine a copy-pasteable contract.

Sources, all live-verified 2026-08-28 from this host (row counts + newest
watermarks in .streams/us372-state-licenses.md):

- TX TABC active ``7hf9-qc9f`` + pending original applications ``mxm5-tdpj``
  (data.texas.gov) — street-address strings only, so the owning specs declare
  ``needs_geocode``. Classify on ``primary_status``: ``license_status``
  compounds the renewal state onto it ("Active - Renewal Pending"), so
  ``primary_status`` leads the status candidates.
- WA L&I contractor licenses ``m8qx-ubtq`` (data.wa.gov) — ``address1`` is the
  MAILING address, not the jobsite (the dataset ships no jobsite columns), so
  geocoded points carry accepted noise.
- WA LCB local authority letters ``vgcw-qfjm`` (data.wa.gov) — geocoded point
  in ``location``; ``applicationdate`` is CCYYMMDD text (``_parse_datetime``
  handles ``%Y%m%d``).
- OR CCB active licenses ``g77e-6bhs`` + OLCC applications received
  ``qad4-bnxp`` (data.oregon.gov) — CCB has no status column (active-only
  registry) and MM/DD/YYYY text dates.
- CO liquor licenses ``ier5-5ms2`` + recently approved ``htyp-tqzh``
  (data.colorado.gov) — geocoded points in ``location``; ``htyp-tqzh``
  ``issue_date`` carries ~98 far-future junk rows (years 2048–2262) that flow
  through the event verbatim — the watermark layer's future guard ignores
  them (verified: 1,408 of 1,506 rows carry real 2026 dates).
- MO new liquor licenses ``dymb-xy5c`` (data.mo.gov) — the address is split
  across ``street_number``/``street``; the owning spec's ``$select`` composes
  ``street_address_ns`` (see state_license_specs.py), with the bare ``street``
  fallback kept here.

license_type NAMESPACING: ``license_type_ns`` does not exist on the sources —
each spec's endpoint carries
``?$select=*, '<ns>:' || <type_col> as license_type_ns`` so flow features can
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

TABC_ACTIVE_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_id"],
    "license_type": ["license_type_ns"],
    "effective_date": ["current_issued_date"],
    "expiration_date": ["expiration_date"],
    "premises_name": ["owner"],
    "dba": ["trade_name"],
    "address_street": ["address"],
    "status": ["primary_status", "license_status"],
    "borough": ["city"],
}

TABC_PENDING_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["applicationid"],
    "license_type": ["license_type_ns"],
    "effective_date": ["submission_date"],
    "premises_name": ["owner"],
    "dba": ["trade_name"],
    "address_street": ["address"],
    "status": ["applicationstatus"],
    "borough": ["city"],
}

WA_LI_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["contractorlicensenumber"],
    "license_type": ["license_type_ns"],
    "effective_date": ["licenseeffectivedate"],
    "expiration_date": ["licenseexpirationdate"],
    "premises_name": ["businessname"],
    "address_street": ["address1"],
    "status": ["contractorlicensestatus"],
    "borough": ["city"],
}

WA_LCB_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license"],
    "license_type": ["license_type_ns"],
    "effective_date": ["applicationdate"],
    "premises_name": ["licenseename"],
    "dba": ["tradename"],
    "address_street": ["streetaddress"],
    "latitude": ["location.latitude"],
    "longitude": ["location.longitude"],
    "borough": ["city"],
}

OR_CCB_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_number"],
    "license_type": ["license_type_ns"],
    "effective_date": ["orig_regis_date"],
    "expiration_date": ["lic_exp_date"],
    "premises_name": ["full_name"],
    "address_street": ["address"],
    "borough": ["city"],
}

OR_OLCC_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["trade_name"],
    "license_type": ["license_type_ns"],
    "effective_date": ["date_received"],
    "premises_name": ["trade_name"],
    "address_street": ["address"],
    "status": ["application_status"],
}

CO_LIQUOR_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_number"],
    "license_type": ["license_type_ns"],
    "expiration_date": ["expiration"],
    "premises_name": ["licensee_name"],
    "dba": ["doing_business_as"],
    "address_street": ["street_address"],
    "latitude": ["location.latitude"],
    "longitude": ["location.longitude"],
    "borough": ["city"],
}

CO_APPROVED_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_number"],
    "license_type": ["license_type_ns"],
    "effective_date": ["issue_date"],
    "premises_name": ["licensee_name"],
    "dba": ["doing_business_as"],
    "address_street": ["street_address"],
    "latitude": ["location.latitude"],
    "longitude": ["location.longitude"],
    "borough": ["city"],
}

MO_NEW_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["license_number"],
    "license_type": ["license_type_ns"],
    "effective_date": ["original_date"],
    "premises_name": ["licensee"],
    "dba": ["dbaname"],
    "address_street": ["street_address_ns", "street"],
    "status": ["current_status"],
    "borough": ["city"],
}

FIELD_MAPS: dict[str, dict[str, list[str]]] = {
    "tabc_active": TABC_ACTIVE_FIELD_MAP,
    "tabc_pending": TABC_PENDING_FIELD_MAP,
    "wa_li": WA_LI_FIELD_MAP,
    "wa_lcb": WA_LCB_FIELD_MAP,
    "or_ccb": OR_CCB_FIELD_MAP,
    "or_olcc": OR_OLCC_FIELD_MAP,
    "co_liquor": CO_LIQUOR_FIELD_MAP,
    "co_approved": CO_APPROVED_FIELD_MAP,
    "mo_new": MO_NEW_FIELD_MAP,
}
