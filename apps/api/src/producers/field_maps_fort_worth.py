"""Per-city field-mapping support for Fort Worth's municipal row parsers.

Fort Worth publishes through the City of Fort Worth ArcGIS server as the
"CFW Development Permits Points" FeatureServer. The live layer returns point
geometry in WGS84 (the shared ArcGIS client requests ``outSR=4326`` and
normalizes the returned point into ``latitude``/``longitude``). The address
fields remain the ADR-0004 fallback when a row has no usable geometry.

This module is the per-city analog of :mod:`src.producers.field_maps`; it
exports one `FIELD_MAP` consumed by the shared permits producer via the
registry's `extra["field_map"]` entry. Kept as a dedicated leaf file so the
spine `field_maps.py` dispatch stays untouched.
"""

from typing import Dict, List

# Fort Worth development-permit field spellings. Geometry is supplied by
# ArcGISClient after its WGS84 request; the aliases below retain compatibility
# with the point layer's attribute columns.
FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["Unique_ID", "Permit_No", "OBJECTID"],
    "latitude": ["SHAPE__Y", "Y"],
    "longitude": ["SHAPE__X", "X"],
    "cost": ["JobValue"],
    "job_type": ["Permit_Type", "Permit_SubType", "Permit_Category", "B1_WORK_DESC"],
    "issuance_date": ["File_Date", "Status_Date"],
    "filing_date": ["File_Date"],
    "status": ["Current_Status"],
    "address_street": ["Addr_No", "Street_Name"],
    "zipcode": ["Zip_Code"],
    "bbl": ["B1_LOT", "B1_BLOCK", "B1_TRACT"],
}
