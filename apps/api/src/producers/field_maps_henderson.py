"""Per-city field maps for Henderson, NV (US-325), imported by the shared parsers.

Henderson is a TWO-FEED PARTIAL metro on ArcGIS AGOL: DSC_Permits
(FeatureServer/0, Tier 1) and Active Business Licenses (CSV item, Tier 2,
address-only). Spellings do not match the shared Socrata chains, so the maps
live here as a leaf rather than growing ``src/producers/field_maps.py``
(spine). The MJBL county-wide license CSV (companion) shares the Active map
after its ``Jurisdiction='HENDERSON'`` filter.

Coordinate contract (pinned by tests):

* PERMITS — native ``GISX``/``GISY`` attribute columns verified live
  (2026-08-28) to be **WGS84 geographic degrees** (lng ≈ -115.09…-114.91,
  lat ≈ 35.93…36.09), NOT State Plane feet and NOT Web Mercator meters —
  no transform is applied. ``GISX`` is longitude, ``GISY`` is latitude.
  Null on ~11.8% of rows; those fall back to the composed parcel-address
  string (ADR 0004 geocode supplement via ``compose_permit_address``).
* SLA — no coordinates at all: ``Business Location`` + City/State/Zip is
  the only locator, so rows declare ``needs_geocode=True`` with context
  "Henderson, NV" (ADR 0004) and resolve at parse time.

PII is dropped at the map: OwnerName/OwnerAddress, ProfessionalName/
ProfessionalStateLicNbr/ProfessionalAddress/ProfessionalPhone, and Business
Phone are never candidates.
"""


# Canonical permit event field -> DSC_Permits/FeatureServer/0 column spellings.
# Live layer (2026-08-28): ObjectId is the OID. GISY=latitude, GISX=longitude
# (WGS84 degrees — pinned live; see module docstring).
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["PermitNumber", "ObjectId"],
    "issuance_date": ["IssueDate"],
    "filing_date": ["ApplyDate"],
    "status": ["PermitStatus"],
    "job_type": ["PermitType", "WorkClass", "Category"],
    "cost": ["ValuationTotal"],
    "address_street": [
        "ParcelAddressNumber",
        "ParcelAddressPreDirection",
        "ParcelAddressStreet",
        "ParcelAddressStreetType",
    ],
    "bbl": ["ParcelNumber"],
    "zipcode": ["ParcelAddressZip"],
    "latitude": ["GISY"],
    "longitude": ["GISX"],
}

# Canonical SLA event field -> Active Business Licenses CSV header spellings.
# Address-only feed: no latitude/longitude candidates by design.
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["License Number"],
    "dba": ["DBA", "Entity Name"],
    "premises_name": ["Entity Name"],
    "license_type": ["License Type", "License Sub-Type"],
    "effective_date": ["Original Issue Date"],
    "expiration_date": ["Expiration Date"],
    "address_street": ["Business Location"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
    "sla": SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Henderson, NV"

# Columns that exist on the live feeds and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "OwnerName",
    "OwnerAddress",
    "ProfessionalName",
    "ProfessionalStateLicNbr",
    "ProfessionalAddress",
    "ProfessionalPhone",
    "Business Phone",
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
    "SLA_FIELD_MAP",
]
