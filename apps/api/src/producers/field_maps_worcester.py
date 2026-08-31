"""Per-city field maps for Worcester, MA (US-419), imported by the shared parsers.

Worcester is a TWO-FEED PARTIAL metro on the city's ArcGIS Hub
(``opendata.worcesterma.gov``, AGOL org
``services1.arcgis.com/j8dqo2DJE7mVUBU1``): Building Permits and Food
Establishment Licenses. Both layers are **non-spatial Tables** — address-only,
so every row resolves coordinates through the ADR-0004 geocode hook
(``needs_geocode=True``, context ``Worcester, MA``) and there are NO native
latitude/longitude columns. Both date columns are TEXT ``M/D/YYYY`` with no
zero-padding ("8/9/2026"), so they sort lexically (ADR-0005) and are parsed by
the shared ``_parse_datetime`` via ``%m/%d/%Y``.

Column spellings do not match the shared Socrata/ArcGIS chains, so the maps
live here as a leaf rather than growing ``src/producers/field_maps.py``
(spine).

PERMITS — ``Building_Permits/FeatureServer/0``: NO cost column and NO
lat/lng; ``Occupancy_Type`` is deliberately left unmapped (no canonical slot
in the permit event worth binding it to). ``Record_Type`` is constant
``"Building Permit"``, so the ``job_type`` slot canonicalizes through it to
``JobType.OT`` before ``Permit_For`` is ever consulted.

SLA — ``Food_Establishment_Licenses/FeatureServer/0``: there is NO
business-name column on this layer, so ``dba``/``premises_name`` stay unmapped
(both resolve to ``None`` on the wire event). ``Type`` is the license-type
grain. (A richer sibling exists — ``Business_Certificates_1963_to_Present``
carries ``Business_Name`` — but the ticket pins this leaf to
``Food_Establishment_Licenses``; see the city module docstring.)
"""


# Canonical permit event field -> Building_Permits/FeatureServer/0 column
# spellings. Address-only: no latitude/longitude candidates, no cost column.
WORCESTER_PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["Record__", "ObjectId"],
    "issuance_date": ["Permit_License_Issued_Date"],
    "filing_date": ["Date_Submitted"],
    "job_type": ["Record_Type", "Permit_For"],
    "status": ["Record_Status"],
    "address_street": ["Address"],
    "bbl": ["MBL"],
}

# Canonical SLA event field -> Food_Establishment_Licenses/FeatureServer/0
# column spellings. No business-name column: dba/premises_name stay unmapped.
WORCESTER_SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["Record__", "ObjectId"],
    "license_type": ["Type"],
    "effective_date": ["Issued_Date"],
    "expiration_date": ["Expiration_Date"],
    "address_street": ["Address"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": WORCESTER_PERMITS_FIELD_MAP,
    "sla": WORCESTER_SLA_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Worcester, MA"

# Columns that exist on the live layers but must never become map candidates.
# No PII columns were found on either layer; this list pins the ADR-0004
# discipline (no cost on permits, no business name on SLA).
NEVER_CANDIDATE_COLUMNS: tuple[str, ...] = (
    "Occupancy_Type",
    "Contractor_Name",
    "Total_of_Fees",
)

__all__ = [
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "NEVER_CANDIDATE_COLUMNS",
    "WORCESTER_PERMITS_FIELD_MAP",
    "WORCESTER_SLA_FIELD_MAP",
]
