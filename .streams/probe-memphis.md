# Stream log — probe-memphis — 2026-08-27

Phase-0 discovery stream for Linear US-201. Research only.

## Claim

- **Stream id:** `probe-memphis`
- **Leaf files I will create/edit:**
  - `.streams/probe-memphis.md` (this file)
  - `docs/research/wave-3-probe-memphis.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Resolve the Memphis TN data portal (unprobed). Probe permits/311/SLA/deeds
row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed US-201 and dispatched.
- 2026-08-27 12:30 PT — Portal resolved: `data.memphistn.gov` is **ArcGIS
  Hub** (not Socrata; leftover Socrata chrome). MEMEGIS org
  `saWmpKJIUAjyyNVc`. Retracts 2026-08-25 "portal not found".
- 2026-08-27 12:35 PT — Permits Tier 1: `DPD_Building_Permits`
  FeatureServer/0, `Issued_Date` newest 2026-07-31, 27,100 rows, native
  lat/lng. Monthly batch (0 August rows; 583 July). 311 Tier 1:
  `311.memphistn.gov` `311_Request_Map_PROD`/0, `REPORTED_DATE` newest
  2026-08-27 19:31 UTC, 395,216 rows, `outSR=4326` WGS84.
- 2026-08-27 12:40 PT — SLA Tier 3 (Accela Develop 901 + County Clerk UI,
  no FeatureServer). Deeds Tier 3 (QualifiedSales empty; Parcel
  SALES/RSALES 500; CERT_TAX_PARCELS is CAMA). **REGISTER partial.**
  Research file written. Findings comment on US-201; ticket marked
  completed. Roadmap file not edited (orchestrator hold).

## Current step

Done.

## Next step

None for this stream. Orchestrator may record the REGISTER-partial row
on `docs/expansion-roadmap-wave-3.md` in a later serial hold.
