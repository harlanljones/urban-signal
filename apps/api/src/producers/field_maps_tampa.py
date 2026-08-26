"""Per-city field-mapping support for Tampa (leaf module).

Tampa's City of Tampa ArcGIS feeds use an Accela-style schema whose columns do
not match the shared parser chains (which are Socrata/NYC-anchored). Rather
than grow the shared fallback chains, Tampa declares its spellings here as data, following the Wave-B mechanism (see
``src/producers/field_maps.py``). The map is imported by
``src/spatial/cities/tampa.py`` and embedded into the PERMITS DatasetSpec's
``extra["field_map"]``; the shared ``resolve_field_map`` accessor picks it up
automatically once the spine registers the city.

The canonical city id is imported from the city module so the two leaf files
cannot drift apart.
"""

from typing import Dict, List

# NOTE: the canonical city id is imported lazily inside ``city_id()`` to avoid a
# circular import — ``tampa.py`` imports ``FIELD_MAP`` from this module at load
# time, so this module must not import ``tampa`` at module load.

# Column spellings for Tampa's full permits and partial alcohol layers.
# ``first_mapped`` semantics: falsy values fall through to the next candidate,
# matching the shared chains. These are provisional against the Accela schema
# described in docs/research/wave-2-city-candidates.md (B1_PER_ID* family);
# confirm exact field names at spine time against a live layer describe call.
FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["RECORD_ID"],
    "issuance_date": ["LASTUPDATE"],
    "status": ["PROJECTSTATUS"],
    "job_type": ["RECORDTYPE", "PROJECTDESCRIPTION", "OCCUPANCYTYPE"],
    "cost": ["NEWCONSTRUCTIONSF"],
    "address_street": ["ADDRESS"],
    "zipcode": ["ZIP"],
    "borough": ["NEIGHBORHOOD", "COUNCIL"],
    "proposed_units": ["NBROFUNITS"],
}

SLA_FIELD_MAP: Dict[str, List[str]] = {
    "license_id": ["ORD_PERMIT", "APP_NUM"],
    "license_type": ["ABSALETYPE", "AB_CLASS_PREFIX", "AB_CLASS_SUFFIX"],
    "premises_name": ["BUS_NAME"],
    "dba": ["BUS_NAME"],
    "effective_date": ["HISTORY_ACT_DT"],
    "expiration_date": ["MTH24_END_DT"],
    "status": ["HISTORY_ACTION"],
    "address_street": ["PERMIT_ADDR", "BUS_OWNER_MAIL_ADD"],
    "zipcode": ["PERMIT_ZIP"],
}


def city_id() -> str:
    """Return the canonical Tampa city id this field map belongs to."""
    from src.spatial.cities.tampa import TAMPA_CITY_ID

    return TAMPA_CITY_ID
