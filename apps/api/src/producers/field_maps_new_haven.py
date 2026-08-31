"""Per-city field maps for New Haven, CT (US-419), imported by the shared parsers.

New Haven is a TWO-FEED metro on Connecticut's statewide Socrata portal
(``data.ct.gov``): State Licenses and Credentials (``ngch-56tr``, Tier 1 SLA)
and Real Estate Conveyance Tax / property sales (``5mzw-sjtu``, Tier 1 DEEDS).
These are the SAME statewide feeds Hartford already carries (see
``field_maps`` for Hartford's inline map in ``city_registry.py``), filtered to
New Haven. Neither carries a native latitude/longitude column the shared
parsers read:

* SLA — address-only. ``recordrefreshedon`` is a daily refresh stamp (0 nulls,
  max 2026-08-30 at probe); no native coordinates. The Hartford inline map is
  STALE (it references ``license_number``/``credential_number`` which do not
  exist on the live feed) — the CORRECT spellings are pinned here.
* DEEDS — address + a nested ``geo_coordinates`` Socrata Point (``{type:
  "Point", coordinates: [lng, lat]}``, present on 32.5% of rows at probe), but
  the shared ``deeds_acris_producer`` nested-loc fallback reads
  ``the_geom``/``point``/``location``/``georeference``/``shape``/
  ``mappable_latitude_and_longitude`` — NOT ``geo_coordinates``. So even the
  rows carrying native coords fall through to the address geocode hook
  (``needs_geocode=True``). The orchestrator SHOULD add ``geo_coordinates``
  to that fallback list in the spine hold so native coords win first.

Column spellings do not match the shared Socrata chains (``credentialid``/
``effectivedate``/``recordrefreshedon``; ``serialnumber``/``daterecorded``/
``saleamount``), so both maps live here as a leaf rather than growing
``src/producers/field_maps.py`` (spine).
"""

SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["credentialid", "fullcredentialcode"],
    "license_type": ["credential", "credentialtype"],
    "effective_date": ["effectivedate", "issuedate"],
    "expiration_date": ["expirationdate"],
    "address_street": ["address"],
    "zipcode": ["zip"],
    "borough": ["city"],
    "premises_name": ["businessname", "name"],
    "dba": ["businessname", "name"],
    "status": ["status"],
}

DEEDS_FIELD_MAP: dict[str, list[str]] = {
    "doc_id": ["serialnumber"],
    "recorded_date": ["daterecorded"],
    "document_amount": ["saleamount"],
    "address_street": ["address"],
    "borough": ["town"],
    "doc_type": ["propertytype"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SLA_FIELD_MAP,
    "deeds": DEEDS_FIELD_MAP,
}

# Columns that exist on the live feeds but must never become map candidates.
SLA_NEVER_CANDIDATE_COLUMNS: tuple[str, ...] = (
    # "active" is a 0/1 flag, not the status string; "statusreason" is the
    # human expiry reason (not a status code); "type" is the holder kind
    # (INDIVIDUAL/BUSINESS/CORPORATION); "credentialnumber" is the numeric
    # sub-part already carried by "credentialid"/"fullcredentialcode".
    "active",
    "statusreason",
    "type",
    "credentialnumber",
)

DEEDS_NEVER_CANDIDATE_COLUMNS: tuple[str, ...] = (
    # "listyear" is the assessment-year half of the composite id_keys, NOT a
    # doc_id candidate (serialnumber alone is not row-unique); "assessedvalue"
    # is the assessed value (not the sale amount); "salesratio" is the ratio,
    # not a price; "residentialtype" is a sub-classification; "geo_coordinates"
    # is a native Point the shared producer does not yet read (see module
    # docstring); "remarks" is free text.
    "listyear",
    "assessedvalue",
    "salesratio",
    "residentialtype",
    "geo_coordinates",
    "remarks",
)

__all__ = [
    "DEEDS_FIELD_MAP",
    "DEEDS_NEVER_CANDIDATE_COLUMNS",
    "FIELD_MAP",
    "SLA_FIELD_MAP",
    "SLA_NEVER_CANDIDATE_COLUMNS",
]
