# Stream log — probe-miami — 2026-08-27

Phase-0 discovery stream for Linear US-199. Research only.

## Claim

- **Stream id:** `probe-miami`
- **Leaf files I will create/edit:**
  - `.streams/probe-miami.md` (this file)
  - `docs/research/wave-3-probe-miami.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Resolve the Miami-Dade / Fort Lauderdale open data portal (top-10 gap,
unprobed). Probe permits/311/SLA/deeds row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed US-199 and dispatched.
- 2026-08-27 12:31 PT — Host fingerprint: Miami-Dade left Socrata.
  `opendata.miamidade.gov` is ArcGIS Hub (custom domain of
  `gis-mdc.opendata.arcgis.com`, 584 datasets). Fort Lauderdale
  `gis.fortlauderdale.gov` and Broward `geohub-bcgis.opendata.arcgis.com`
  are distinct live portals.
- 2026-08-27 13:05 PT — Row-level complete. Wave-3-ready **yes (partial)**:
  MDC permits T1 (`ISSUDATE` 2026-08-20, points) + LBT SLA T1 snapshot.
  311 T3 (Hub slices stop 2023; City of Miami 311 frozen 2024-08-10).
  Deeds T2 optional snapshot (`DATEOFSALE_UTC` real max 2026-08-03).
  FTL city permits/311/licenses T3 stale. Broward tax T1 snapshot.

## Current step

Done. Research file landed; US-199 commented and marked Done
(assignee unchanged).

## Next step

None for this stream. US-195 synthesizes into the shared Wave 3 roadmap.
Do not register a city in this stream (research only; no spine).
