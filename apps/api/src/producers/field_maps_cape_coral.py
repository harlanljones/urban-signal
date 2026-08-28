"""Per-city field-mapping for Cape Coral–Fort Myers (leaf module).

Cape Coral's public permits are published as an ArcGIS MapServer table with
address fields (no geometry columns). The shared producers resolve this map
to normalize record spellings without growing global parser chains.
"""

from typing import Dict, List

# Column spellings observed on:
# https://capeims.capecoral.gov/arcgis/rest/services/OpenData/OpenData/MapServer/1?f=json
FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["Permit_Number"],
    "issuance_date": ["issuedate", "applydate", "lastchangedon"],
    "status": ["permit_status"],
    "job_type": ["Permit_Type", "Work_Class", "permit_desc"],
    "cost": ["permitvalue"],
    "address_street": ["Addr1"],
    "zipcode": ["Zip"],
    "borough": ["City"],
}


def city_id() -> str:
    """Return the canonical Cape Coral city id this field map belongs to."""
    from src.spatial.cities.cape_coral import CAPE_CORAL_CITY_ID

    return CAPE_CORAL_CITY_ID

