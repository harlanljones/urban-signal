# Stream log — probe-st-louis — 2026-08-27

Phase-0 discovery stream for Linear US-200. Research only.

## Claim

- **Stream id:** `probe-st-louis`
- **Leaf files I will create/edit:**
  - `.streams/probe-st-louis.md` (this file)
  - `docs/research/wave-3-probe-st-louis.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Resolve the St. Louis MO open data portal. Probe permits/311/SLA/deeds
row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed US-200 and dispatched.
- 2026-08-27 12:45 PT — Platform is **custom** (ColdFusion DCAT at
  `www.stlouis-mo.gov/data.json` + maps8 ArcGIS REST + `stlcitypermits.com`
  JSON + CSV/zip dumps). Prior Hub host `stlouis-moa-gis.opendata.arcgis.com`
  is a private org (401) — that is why the 2026-08-25 sweep registered none.
- 2026-08-27 12:45 PT — **311 Tier 1.** `csb.zip` / `2026.csv`, watermark
  `DATETIMEINIT` = 2026-08-27 05:54:02, native Web Mercator `SRX`/`SRY`
  (99.96%) + `PROBADDRESS`.
- 2026-08-27 12:45 PT — **PERMITS Tier 2.** CF 30-day CSV/JSON, `ISSUEDATE` =
  2026-08-07, address-only (140/140). 20-day publish lag. ArcGIS
  `Building_Permits` FS frozen at 2025-03-05; 2025 MapServer year-slice has
  no 2026 successor.
- 2026-08-27 12:45 PT — **SLA Tier 2 narrow liquor.** Daily excise CSV
  snapshot, address `LOCATION`, no issue watermark. General business
  licenses are Oct-2025 ArcGIS snapshots.
- 2026-08-27 12:45 PT — **DEEDS Tier 3.** `prclsale.mdb` `SaleDate` max
  2026-02-11 (6-month lag) despite same-day zip mtime. Do not register.
- 2026-08-27 12:45 PT — **Wave-3-ready: yes**, partial metro (`st_louis`):
  311 + permits (+ optional liquor SLA). Research at
  `docs/research/wave-3-probe-st-louis.md`. Did not edit the shared Wave 3
  roadmap.

## Current step

Phase-0 complete. Research file written; findings commented on US-200;
ticket marked completed. Assignee left in place.

## Next step

None for this stream. A later `city-st-louis` leaf would implement the
registration contract (CSVClient zip-member for 311, geocoder for permits,
snapshot liquor SLA). Re-probe ≤72 h before that build.
