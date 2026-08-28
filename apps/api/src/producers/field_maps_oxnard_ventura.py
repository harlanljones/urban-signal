"""Per-city field maps for Oxnard–Ventura, CA (US-232), imported by the shared
parsers.

Oxnard–Ventura is a THREE-FEED metro anchored on the **City of San
Buenaventura (City of Ventura)** — the strongest of the twin cities (three
verified live feeds vs Oxnard's one; see cities/oxnard_ventura.py). The
anchor's open-data catalog is the city's own ArcGIS Hub backed by AGO org
``dBVj4EXO3IdRPOqb``:

* SLA — ``OpenData_PSI_BusinessLicenses`` (FeatureServer/0, Tier 1, 12,590
  rows). PSI is the city's licensing vendor; the layer is a current-license
  registry with annual renewals posted continuously.
* COMPLAINTS_311 — ``Graffiti_Responses_Read_Only`` (FeatureServer/0, Tier 1,
  22,085 rows). Graffiti response requests are the published service-request
  surface of Ask Ventura; the full 311 case stream is not bulk-open.
* CRIME — ``OpenData_Police_Crimes`` (FeatureServer/0, Tier 1, 85,974 rows;
  ADR 0004 satisfied: native point geometry AND a generalized block address).

Coordinate contract (pinned by tests):

* All three layers serve **native point geometry** requested with
  ``outSR=4326``; ``ArcGISClient._flatten_feature`` lifts it to
  ``latitude``/``longitude``, which the producers' generic chains read. No
  ``latitude``/``longitude`` candidates appear in any map.
* The SLA layer carries ``BADDRX``/``BADDRY`` attribute doubles that are a
  **local vendor grid, not coordinates**: in-city rows read ≈ 22589–24716 /
  19570–20086 and out-of-city rows carry 0.0. They are neither WGS84 degrees
  nor a declared California State Plane zone (values are orders of magnitude
  below EPSG:2225 ftUS), so no ``state_plane_*`` spec keys are declared and
  the columns are pinned unmapped — the SLA parser has no out-of-range
  guard, so mapping them would emit grid units as degrees.

PII is dropped at the map: SLA ``BUSPHONE``/``BUSNOTE`` (phone, state
license number), and the 311 layer's ``Username``/``Creator``/``Editor``
(staff accounts) and ``Monikers`` (gang-tagging evidence text) are never
candidates.
"""

# ---------------------------------------------------------------------------
# SLA — OpenData_PSI_BusinessLicenses/FeatureServer/0. Live layer
# (2026-08-28): DATESTART/DATEISSUE/DATEEXPIRE are the esriFieldTypeDate
# columns and arrive as epoch-ms; ArcGISClient converts them to ISO 8601 UTC
# on flatten. ``DBA`` is blank for some accounts, so ``COMPNAME`` rides as
# the dba fallback; COMPNAME is also the only premises/legal-name column.
# ---------------------------------------------------------------------------
SLA_FIELD_MAP: dict[str, list[str]] = {
    "license_id": ["ACCTNO"],
    "dba": ["DBA", "COMPNAME"],
    "premises_name": ["COMPNAME"],
    "license_type": ["BUSTYPE", "NAICS_DESC", "NAICS_CODE"],
    "status": ["STATUSDESC"],
    "effective_date": ["DATESTART"],
    "expiration_date": ["DATEEXPIRE"],
    "address_street": ["ADDRESS"],
}

# ---------------------------------------------------------------------------
# COMPLAINTS_311 — Graffiti_Responses_Read_Only/FeatureServer/0. The layer is
# graffiti-only by design, so no ``complaint_type`` candidate is declared
# (the producer's chain lands on "Unknown" honestly — there is no request
# type column to pretend otherwise). No ``borough``/neighborhood column
# exists either (Omaha discipline): source_neighborhood passes through None
# and division resolution comes from coordinates at ingest. There is no
# address column, so null-geometry rows drop (needs_geocode stays False —
# a geocoder has nothing to geocode).
# ---------------------------------------------------------------------------
COMPLAINTS_311_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["globalid", "objectid"],
    "created_date": ["ReportedOn"],
    "closed_date": ["DateEnded"],
}

# ---------------------------------------------------------------------------
# CRIME — OpenData_Police_Crimes/FeatureServer/0. ``Community_Council`` is
# the police department's own sub-city label ("College Community Council")
# and is the declared borough candidate (source_neighborhood).
# ``GeneralizedAddress`` is a block-level string ("1600 Block WALTER ST")
# that mainstream geocoders cannot reliably resolve, so it is NOT declared:
# with needs_geocode False, null-geometry rows drop (0 null geometries in
# the live newest-500 probe 2026-08-28).
# ---------------------------------------------------------------------------
CRIME_FIELD_MAP: dict[str, list[str]] = {
    "incident_id": ["EventOffenseKey", "Report_Number"],
    "offense_type": ["Offense_Type", "Offense_Category"],
    "occurred_date": ["Incident_Date_Start"],
    "borough": ["Community_Council"],
}

FIELD_MAP: dict[str, dict[str, list[str]]] = {
    "sla": SLA_FIELD_MAP,
    "311": COMPLAINTS_311_FIELD_MAP,
    "crime": CRIME_FIELD_MAP,
}

GEOCODE_CONTEXT: str = "Ventura, CA"

# Columns that exist on the live layers and must never become map candidates.
# BADDRX/BADDRY are the local vendor grid (see module docstring); BADDPARCEL
# is the parcel key as a float; BUSNOTE embeds the state license number.
DROPPED_NONADDRESS_COLUMNS: tuple[str, ...] = (
    "BADDRX",
    "BADDRY",
    "BADDPARCEL",
    "BUSPHONE",
    "BUSNOTE",
    "CONTRACTNO",
    "GlobalID",
)

DROPPED_PII_COLUMNS: tuple[str, ...] = (
    "Username",
    "Creator",
    "Editor",
    "ReportedBy",
    "Monikers",
    "PhotoNote",
)

__all__ = [
    "COMPLAINTS_311_FIELD_MAP",
    "CRIME_FIELD_MAP",
    "DROPPED_NONADDRESS_COLUMNS",
    "DROPPED_PII_COLUMNS",
    "FIELD_MAP",
    "GEOCODE_CONTEXT",
    "SLA_FIELD_MAP",
]
