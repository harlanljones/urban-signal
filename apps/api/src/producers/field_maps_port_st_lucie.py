"""Per-city field-mapping support for Port St. Lucie (leaf module).

Port St. Lucie's public Building Permits layer (ArcGIS FeatureServer) uses
city-specific column names that do not match the shared NYC/Socrata-anchored
parser chains. Declare the per-city spellings here (Wave-B pattern; see
``src/producers/field_maps.py``). The map is imported by
``src/spatial/cities/port_st_lucie.py`` and embedded into the PERMITS
DatasetSpec so the shared ``resolve_field_map`` accessor can pick it up once
the spine registers the city.
"""

from typing import Dict, List

# Column spellings for Port St. Lucie's Building Permits layer:
# https://services1.arcgis.com/YdUP5V6WwzeG8T8r/arcgis/rest/services/Permits/FeatureServer/0
FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["PermitID"],
    "issuance_date": ["DateIssued", "AppliedDate"],
    "status": ["Status"],
    "job_type": ["PermitType", "ApplicationType", "BuildingType"],
    "address_street": ["ADDRESSWITHUNIT"],
    # Coordinates come from geometry; the layer also carries State-Plane GEOX/GEOY
    # which we deliberately ignore here.
}


def city_id() -> str:
    """Return the canonical city id this field map belongs to."""
    from src.spatial.cities.port_st_lucie import PSL_CITY_ID

    return PSL_CITY_ID

