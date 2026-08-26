"""Per-city field-mapping support for Tampa (leaf module).

Tampa's City of Tampa "Single Family Permits" feed is an Accela-schema ArcGIS
layer whose columns do not match the shared parser chains (which are Socrata/
NYC-anchored). Rather than grow the shared fallback chains, Tampa declares its
spellings here as data, following the Wave-B mechanism (see
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

# Column spellings for Tampa's Accela-schema Single Family Permits layer.
# ``first_mapped`` semantics: falsy values fall through to the next candidate,
# matching the shared chains. These are provisional against the Accela schema
# described in docs/research/wave-2-city-candidates.md (B1_PER_ID* family);
# confirm exact field names at spine time against a live layer describe call.
FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["B1_PER_ID", "B1_ALT_ID"],
    "issuance_date": ["OPENED_DATE"],
    "status": ["APPLICATION_STATUS"],
    "job_type": ["B1_WORK_FLOW", "B1_PER_TYPE"],
    "cost": ["B1_EST_PROJ_COST", "TOTAL_PROJECT_COST"],
    "address_street": ["B1_SITE_ADDRESS", "SITE_ADDRESS"],
    "zipcode": ["ZIP_CODE", "B1_SITE_ZIP"],
    "borough": ["COUNCIL_DISTRICT", "MUNICIPALITY"],
}


def city_id() -> str:
    """Return the canonical Tampa city id this field map belongs to."""
    from src.spatial.cities.tampa import TAMPA_CITY_ID

    return TAMPA_CITY_ID
