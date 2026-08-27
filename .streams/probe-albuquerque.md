# Stream log — probe-albuquerque — 2026-08-27

Phase-0 discovery stream for Linear US-205. Research only.

## Claim

- **Stream id:** `probe-albuquerque`
- **Leaf files I will create/edit:**
  - `.streams/probe-albuquerque.md` (this file)
  - `docs/research/wave-3-probe-albuquerque.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Resolve the Albuquerque NM CKAN portal (unprobed). Probe
permits/311/SLA/deeds row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed US-205 and dispatched.
- 2026-08-27 12:45 PT — **Not CKAN.** `data.cabq.gov/api/3/action/*` 404;
  CivicData package_search albuquerque/cabq count=0. Actual platform:
  Apache CSV dumps (`data.cabq.gov`) + ArcGIS Server (`coageo.cabq.gov`).
- 2026-08-27 12:45 PT — Permits **Tier 2** live CSV
  `BuildingPermitsCABQ-en-us.csv`, watermark `IssueDate` **2026-08-26**
  (YYYYMMDD; exclude `20261224`). Address-only → ADR 0004. AGIS
  `City_Building_Permits` frozen at `DateIssued` 2025-01-16 — do not
  register. 311 CRM token/timeout; graffiti 2020; SLA dump frozen
  2025-01-24; deeds none. **Wave-3-ready: yes, partial (PERMITS only).**
- 2026-08-27 12:45 PT — Did not edit `docs/expansion-roadmap-wave-3.md`
  (orchestrator-owned). Findings on US-205 + research file.

## Current step

Done. Research file written; US-205 comment + completed (assignee kept).

## Next step

None for this stream. Orchestrator may fold the tier table into the Wave 3
roadmap. Implementation = leaf `cities/albuquerque.py` + CSV permits spec.
