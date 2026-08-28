# Stream log — west-coeur_dalene — 2026-08-28

## Claim

- **Stream id:** west-coeur_dalene
- **Leaf files I will create/edit:** NONE (REJECTED)
- **Spine files I expect to need:** NONE

## Intent

Live-probe cdaid.org (City of Coeur d'Alene) for 1-4 verifiable official
open-data feeds (permits / 311 / business licenses / deeds via Kootenai
County). REJECT — no verifiable live feed exists.

## Decisions

- <2026-08-28> Claimed US-244 as LEAF stream. Spine files: NONE.
- <2026-08-28> PHASE A probe complete. REJECT with evidence below.

## Probe evidence

### 1. City ArcGIS Enterprise (gis.cdaid.org)
ArcGIS Enterprise 2023.2, Server 11.2. NOT an ArcGIS Hub — the ticket's
"ArcGIS Hub" hint is the wrong door. Public services at
`/server/rest/services/`. Portal at `/portal/sharing/rest/`.

**Candidate: Restricted/Permits_Licensing_Applications/MapServer/1
("Mapped Permits")** — 21,762 records, esriGeometryPoint, Idaho State
Plane West FIPS 1103 Feet (WKID 102670 / EPSG:2243). Columns: permitNum,
permit_type, project_description, project_type, site_address,
site_directional, site_street, site_designation, site_suite, status,
project_valuation, totalfees, createdDate, closedDate, issuedDate,
permitlink. **STALE MIRROR**: max createdDate/issuedDate =
1731456000000 = 2024-11-13. Query `where createdDate >= date
'2025-01-01'` returns 0 rows. The layer is a stale replica of the live
building.cdaid.org permit system, which stopped syncing ~21 months ago.
REJECT.

**Candidate: Restricted/Permits_Licensing_Applications/MapServer/0
("Today's Inspections")** — max InspectionDate = 1644969600000 =
2022-02-16 (~4.5 years stale). REJECT.

**Candidate: Restricted/Permits_Licensing_Applications/MapServer/3
("Short Term Rentals")** — 433 records, business license data (LicenseNum,
IssuedOn, ExpiresOn, BusinessNa, ComAddress). Max IssuedOn = 1762300800000
= 2025-11-04 (~10 months stale). REJECT.

**Candidate: Restricted/Permits_Licensing_Applications/MapServer/2
("Child Care")** — static directory, no date column. REJECT.

**Candidate: Restricted/Permits_Licensing_Applications/MapServer/6
("ADUs")** — static snapshot (C_O_ISSUED string dates 2007-2024). REJECT.

**Share/Planning/MapServer** — zoning/land-use polygons, Short Term
Rentals points. Reference data, not a transactional feed. REJECT.

**Share/Admin_Boundaries/MapServer** — City Limits, flood zones, urban
renewal districts. Reference data. REJECT.

**Other public services** (Share/Garbage, Share/Recreation, Share/Art,
Share/CemeteryBoundaries, CityUtilities/*, Edit/Street_Dept,
Edit/EditBurials, Imagery/*) — infrastructure/reference/imagery, not
transactional open-data feeds. All REJECT.

### 2. Kootenai County (kcgov.us)
County GIS server at gis.kcgov.us returns "Could not access any server
machines" — appears offline (ransomware attack noted on homepage).
County Recorder's office page returns 404. Growth Dashboard is a KPI
dashboard (aggregates/PDFs, not raw data). No accessible ArcGIS REST
services, no deed/parcel open-data feed. REJECT.

### 3. 311 / Service Requests
No open-data feed. "Report" web forms (Code Violation, Streetlight,
Stormwater, Snow Removal, Street Maintenance, Sewer Backup) are
form-to-email, not machine-readable feeds. REJECT.

## Outcome

**REJECT — No verifiable official live feed exists for Coeur d'Alene, ID.**

- PERMITS: City ArcGIS "Mapped Permits" is a stale mirror (last updated
  Nov 2024). building.cdaid.org is a live web app but no REST API.
- SLA: STR license layer last updated Nov 2025.
- 311: Web forms only, no open data feed.
- DEEDS: Kootenai County GIS offline (ransomware aftermath). Recorder
  page unreachable.

## Spine delta (recommended Linear comment)

```
US-244 REJECT — Coeur d'Alene, ID

No verifiable official live feed exists. Received:
- City ArcGIS "Mapped Permits" layer (stale mirror, last updated
  2024-11-13, confirmed via `where createdDate >= date '2025-01-01'`
  returning 0 rows)
- City ArcGIS STR license layer (stale, last updated 2025-11-04)
- Kootenai County GIS offline (ransomware aftermath, server error)
- No 311, no deeds, no Socrata, no Hub

The city's ArcGIS Enterprise at gis.cdaid.org hosts infrastructure
MapServers (water, sewer, storm, fiber, imagery, admin boundaries,
planning) plus a stale permit/license snapshot. No transactional
feed is fit for registration.

No CityId.COEUR_DALENE member, no registry entry, no config endpoints.
Recommend closing as wontfix.
```

## Current step

REJECT complete. No files to create.

## Next step

(No next step — stream is complete.)