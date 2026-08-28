"""Per-city field maps for Chandler, AZ (US-228), imported by the shared parsers.

Chandler is a ONE-FEED PARTIAL metro on the city's ArcGIS Enterprise 11.5
(``gis.chandleraz.gov``, proxied under ``/portalserver``): Building_Blocks
``MapServer/0`` = ``LIS.ACCELA_ALL_PERMITS_V_HARD`` (Tier 1, daily, ~103k
rows). Spellings do not match the shared Socrata chains, so the map lives
here as a leaf rather than growing ``src/producers/field_maps.py`` (spine).

Coordinate contract (pinned by tests):

* PERMITS — coordinates come from **native point geometry** requested with
  ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts them to
  ``latitude``/``longitude`` keys, which the producer's generic chains read.
  No ``latitude``/``longitude`` candidates appear in the map: the layer's
  store SR is NAD83(HARN) StatePlane Arizona Central FIPS 0202 in
  international feet, and the layer exposes no X/Y attribute pair at all —
  nothing except the outSR=4326 geometry lift may feed coordinates, and
  zero of 103,442 live rows carry null geometry (probe 2026-08-28).
* ``CREATE_DT`` is the Accela record-creation (application) date — proven
  live by 2,307 pending-status permits carrying CREATE_DT older than 90d
  (oldest pending back to 2006-08-29) — so it maps to ``filing_date``
  (Dallas ``CREATEDDATE`` convention) and **never** to ``issuance_date``.
  The view publishes no issuance timestamp; issuance is a ``PERMIT_STATUS``
  transition. ``bbl`` carries the Maricopa parcel/APN (``PARCEL_NBR``;
  Las Vegas PRCLID / Savannah PIN precedent).

PII is dropped at the map: the PRI_CNTCT_* (primary contact), PRI_CNTRCT_*
(contractor) and OWNER_* blocks are never candidates.
"""


# Canonical permit event field -> LIS.ACCELA_ALL_PERMITS_V_HARD/MapServer/0
# column spellings. Live layer (2026-08-28): OBJECTID is the OID, geometry is
# the coordinate source, CREATE_DT is the daily watermark (ANSI-date host —
# the spine must add gis.chandleraz.gov to ANSI_DATE_LITERAL_HOSTS).
PERMITS_FIELD_MAP: dict[str, list[str]] = {
    # PERMIT_NBR is the Accela permit number ("UTL26-0884", "BLD26-2139", …)
    # and the id_keys head; OBJECTID keeps rows addressable if the number is
    # ever missing client-side (Henderson OID-fallback precedent).
    "job_id": ["PERMIT_NBR", "OBJECTID"],
    "filing_date": ["CREATE_DT"],
    "status": ["PERMIT_STATUS"],
    "job_type": ["B1_PER_TYPE", "PERMIT_TYPE"],
    "cost": ["JOB_VALUE"],
    "address_street": ["FULL_ADDRESS", "FULL_ADDR"],
    "zipcode": ["ZIP_CODE"],
    "bbl": ["PARCEL_NBR"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "permits": PERMITS_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Chandler, AZ"

# Columns that exist on the live feed and must never become map candidates.
DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "PRI_CNTCT_BUS_NM",
    "PRI_CNTCT_FULL_NM",
    "PRI_CNTCT_PHONE",
    "PRI_CNTCT_EMAIL",
    "PRI_CNTRCT_BUS_NM",
    "PRI_CNTRCT_FULL_NM",
    "PRI_CNTRCT_PHONE",
    "PRI_CNTRCT_EMAIL",
    "OWNER_NM",
    "OWNER_PHONE",
    "OWNER_EMAIL",
)

__all__ = [
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "PERMITS_FIELD_MAP",
]
