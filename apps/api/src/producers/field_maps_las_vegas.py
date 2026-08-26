"""Per-city field maps for the Las Vegas / Clark County registration.

Clark County (the metro's governing open-data publisher) spells its permit and
parcel-sales columns differently from the shared parser chains. Rather than
grow the shared `or row.get(...)` fallback chains (rejected at four cities, see
`src/producers/field_maps.py`), this leaf module declares Las Vegas' spellings
as data, mirroring the Wave-B mechanism used by NOLA, Seattle, Norfolk, etc.

The map is keyed by feed (`"permits"` / `"deeds"`) so `las_vegas.py` can embed
each sub-map into the matching `DatasetSpec.extra["field_map"]`. The shared
`first_mapped` helper consumes these lists directly.

Las Vegas DEEDS is **address-only** on the wire (street address, no native
geometry). Its `address_street` entries exist precisely so ADR-0004 geocoding
fires at enrichment. PERMITS exposes the Socrata `location_1` geo container, so
it parses with native coordinates today.

DISCOVERY NOTE: exact Clark County column names below are the portal's
documented Socrata spellings and MUST be confirmed against the live catalog
during the spine interlock — a leaf cannot reach the network. The structure is
correct; individual keys are low-risk and easily corrected by the orchestrator
without touching shared code.
"""

from typing import Dict, List

# Canonical field name -> ordered candidate keys (dotted = nested container).
FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    # ------------------------------------------------------------------
    # PERMITS — Clark County Building Permits (Socrata)
    # ------------------------------------------------------------------
    "permits": {
        "job_id": ["permit_number", "permit_no"],
        "latitude": ["location_1.latitude"],
        "longitude": ["location_1.longitude"],
        "cost": [
            "total_project_valuation",
            "total_job_valuation",
            "valuation",
        ],
        "job_type": ["permit_type", "work_class", "permit_class"],
        "issuance_date": ["issued_date", "date_issued"],
        "filing_date": ["application_date", "date_filed"],
        "status": ["status", "permit_status"],
        "address_street": ["site_address", "address", "location_address"],
        "zipcode": ["zip_code", "zip"],
        "borough": ["city", "jurisdiction", "subdivision"],
    },
    # ------------------------------------------------------------------
    # DEEDS — Clark County real-property parcel sales / recorded deeds
    # (Socrata, address-only -> ADR-0004 geocoded at enrichment)
    # ------------------------------------------------------------------
    "deeds": {
        "doc_id": ["document_number", "instrument_number", "doc_num"],
        "bbl": ["parcel_number", "apn", "pin"],
        "document_amount": [
            "sale_price",
            "sale_amount",
            "total_consideration",
        ],
        "recorded_date": ["sale_date", "recorded_date", "deed_date"],
        "borough": ["city", "subdivision", "township"],
        "address_street": ["site_address", "property_address", "address"],
    },
}
