"""DatasetSpec-shaped plain dicts for the FL Statewide Cadastral (US-398).

LEAF data — NOT registered anywhere. Field names mirror the ``DatasetSpec``
dataclass in ``src/spatial/city_registry.py`` exactly (``DatasetSpec(**spec)``
constructs from these dicts) so the spine can copy them mechanically during
the interlock hold; the per-city placement is documented in
``.streams/us398-fl-cadastral.md`` ("Spine delta").

The FL Statewide Cadastral (FDOR) is an annual assessment-derived polygon layer
over 67 counties. It is NOT a permit event stream — it is a construction-
activity context covariate. ``NCONST_VAL`` (new-construction value) and
``DEL_VAL`` (demolition value) are the dollar-value signals; ``EFF_YR_BLT``
within 1–3 years of the assessment year is the defensible building-completion
signal. County code (``CO_NO``) maps to metro via the FIPS crosswalk in
``src.spatial.geography_crosswalk`` (``city_for_county_fips``).

Metros this supplies: Ocala, Orlando, Lakeland, Melbourne/Palm Bay, Port St.
Lucie, Gainesville, Cape Coral, Tallahassee/Leon.

The spec is a per-county slice function (``fl_cadastral_spec(cono)``), following
the TABC/childcare pattern so the spine can register each metro with its own
``where`` clause. The full state layer is 2M+ polygons; per-county slices keep
each snapshot proportional to the metro's parcels.
"""

from src.config import settings
from src.producers.field_maps_fl_cadastral import FL_CADASTRAL_FIELD_MAP

FL_CADASTRAL_ENDPOINT = (
    "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/"
    "Florida_Statewide_Cadastral/FeatureServer/0"
)


def fl_cadastral_spec(cono: int) -> dict:
    """FL Statewide Cadastral slice for one county (CO_NO = FDOR county code).

    ``cono`` is the 2-digit FL DOR county code (01–67).  The spine resolves
    county → FIPS via ``FL_COUNTY_CODE_TO_FIPS`` in the field map module, then
    → metro via ``geography_crosswalk.city_for_county_fips``.
    """
    return {
        "endpoint": FL_CADASTRAL_ENDPOINT,
        "platform": "arcgis",
        "watermark_col": "",
        "id_keys": ["OBJECTID", "PARCEL_ID"],
        "topic": settings.topic_permits,
        "interval_seconds": 86400.0,
        "producer_key": "permits",
        "expected_cadence_days": 365,
        "ingestion_mode": "snapshot",
        "where": f"ASMNT_YR = 2025 AND CO_NO = {cono}",
        "oid_field": "OBJECTID",
        "max_record_count": 2000,
        "needs_geocode": False,
        "field_map": FL_CADASTRAL_FIELD_MAP,
    }