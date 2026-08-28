"""Per-city field-mapping support for Wilmington, NC (New Hanover County) permits.

Verified public source:
- ArcGIS FeatureServer: https://gis.nhcgov.com/server/rest/services/Thematic/BuildingPermits/FeatureServer/0
- Geometry: esriGeometryPoint (native NC State Plane; client requests outSR=4326)
- MaxRecordCount: 10000
- Watermark/date field: ISSUE_DATE (esriFieldTypeDate; epoch-ms)

This module exports a FIELD_MAP consumed by the shared permits producer via the
registry DatasetSpec.extra.field_map entry, aligning New Hanover County column
spellings to Urban Signal's canonical event fields.
"""

from typing import Dict, List

# Canonical event field -> candidate row keys for Wilmington NC.
# Values follow the same "falsy falls through" semantics as shared chains.
FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "permits": {
        # Human-friendly id; OBJECTID is the ArcGIS OID fallback.
        "job_id": ["PERMIT_NUMBER", "PMPERMITID", "OBJECTID", "id"],
        # Issuance date drives the incremental watermark.
        "issuance_date": ["ISSUE_DATE"],
        # Total declared valuation is the closest permit value; fees as fallback.
        "cost": ["VALUATION", "TOTAL_FEE_AMOUNT"],
        # Work/permit classification.
        "job_type": ["PERMIT_TYPE", "WORK_CLASS"],
        # Status string.
        "status": ["PERMIT_STATUS"],
        # Address components exist (NUMBER/STREET/TYPE/DIR), but geometry is
        # native point, so address mapping is optional. Keep light for now.
        # Borough/area descriptors are not present as named neighborhoods.
    },
}

__all__ = ["FIELD_MAP"]

