"""Per-city field maps for the Las Vegas / Clark County registration.

Clark County (the metro's governing open-data publisher) spells its permit and
parcel-sales columns differently from the shared parser chains. Rather than
grow the shared `or row.get(...)` fallback chains, this leaf module declares
Las Vegas' spellings as data, mirroring the Wave-B mechanism used by NOLA,
Seattle, Norfolk, and other registrations.

The map is keyed by feed (`"permits"` / `"deeds"`) so `las_vegas.py` can embed
each sub-map into the matching `DatasetSpec.extra["field_map"]`. The shared
`first_mapped` helper consumes these lists directly.

Both Las Vegas feeds are address-only on the wire (the permit and parcel
services are ArcGIS tables without geometry). Their address entries exist
precisely so ADR-0004 geocoding fires at enrichment.
"""

from typing import Dict, List

# Canonical field name -> ordered candidate keys (dotted = nested container).
FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    # ------------------------------------------------------------------
    # PERMITS — Clark County Building Permits (ArcGIS table)
    # ------------------------------------------------------------------
    "permits": {
        "job_id": ["APNO", "APBLDGKEY", "ObjectId"],
        "cost": [
            "DECLVLTN",
            "CALCVLTN",
        ],
        "job_type": ["WORKTYPE", "APTYPE"],
        "issuance_date": ["ISSDTTM"],
        "status": ["BLDGAPPLSTATUS"],
        "address_street": ["APL_ADDRESS", "ADDR1"],
        "zipcode": ["ZIP"],
        "borough": ["CITY", "SUBDIV"],
        "bbl": ["PRCLID"],
    },
    # ------------------------------------------------------------------
    # DEEDS — Clark County real-property parcel sales / recorded deeds
    # (ArcGIS table, address-only -> ADR-0004 geocoded at enrichment)
    # ------------------------------------------------------------------
    "deeds": {
        "doc_id": ["DOCNO", "ObjectId"],
        "bbl": ["PARCEL", "APN"],
        "document_amount": ["SALEPRICE"],
        "recorded_date": ["SALEDATE", "DOCDATE"],
        "borough": ["COMNAME", "WARD"],
        "address_street": ["ADDRESS1", "ADDRESS2"],
        "zipcode": ["ZIP", "ZIPCODE"],
    },
}
