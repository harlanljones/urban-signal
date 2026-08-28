"""Per-city field maps for Greenville, SC (US-340), imported by the shared parsers.

Greenville is a ONE-FEED PARTIAL metro on the city's ArcGIS Server 10.81
(``citygis.greenvillesc.gov``): BuildingPermits_PriorTwoYears (MapServer/0,
Tier 1, daily). Spellings do not match the shared Socrata chains, so the map
lives here as a leaf rather than growing ``src/producers/field_maps.py``
(spine). The Hub placeholders are a private org (401) and no Socrata exists.

Coordinate contract (pinned by tests):

* PERMITS — coordinates come from **native point geometry** requested with
  ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts them to
  ``latitude``/``longitude`` keys, which the producer's generic chains read.
  The ``X_COORD``/``Y_COORD`` *attributes* are **State Plane feet** (values
  ≈ 1.58e6 / 1.08e6 on the live 2026-08-28 re-probe) and are deliberately
  NOT candidates — mapping them would emit projected feet as degrees.
* ``APPLICDATE`` is a numeric ``YYYYMMDD`` double (not an esri date) and
  stays unparsed client-side; ``NewIssueDate`` (esriFieldTypeDate) is the
  issuance watermark and ISO-normalizes in the ArcGIS client.
* No site-zip column exists (``OWNER_ZIP`` is the owner's mailing zip) and
  no parcel/APN column exists, so ``zipcode`` and ``bbl`` stay undeclared.

PII is dropped at the map: OwnerName/OwnerAddress and Contractor blocks are
never candidates.
"""


# Canonical permit event field -> BuildingPermits_PriorTwoYears/MapServer/0
# column spellings. Live layer (2026-08-28): OBJECTID is the OID, geometry is
# the coordinate source, NewIssueDate is the daily watermark.
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    "job_id": ["PERMIT_NUM"],
    "issuance_date": ["NewIssueDate"],
    "filing_date": ["APPLICDATE"],
    "status": ["BP_STATUS", "Status"],
    "job_type": ["PERMIT_TYPE"],
    "cost": ["PERMIT_VALUATION"],
    "address_street": ["STREETADDRESS"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Greenville, SC"

# Columns that exist on the live feed and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "OWNER_NAME",
    "OWNER_ADDR",
    "OWNER_ADDR2",
    "OWNER_ZIP",
    "CONTRACTOR_NAME",
    "CONT_ADDR",
    "CONT_ADDR2",
    "CONT_ZIP",
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]
