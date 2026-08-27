# Stream log — probe-phoenix — 2026-08-27

Phase-0 discovery stream for Linear US-197. Research only.

## Claim

- **Stream id:** `probe-phoenix`
- **Leaf files I will create/edit:**
  - `.streams/probe-phoenix.md` (this file)
  - `docs/research/wave-3-probe-phoenix.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Resolve phoenixopendata.com platform (Hub API 404'd in 2026-08; likely
CKAN/custom). Probe permits/311/SLA/deeds row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed US-197 and dispatched.
- 2026-08-27 12:30 PT — US-197 confirmed In Progress, assigned harlanljones.
- 2026-08-27 12:45 PT — Platform: CKAN 2.9.11 (158 packages) + ArcGIS Server
  11.3. Hub API 404 on phoenixopendata.com is expected (not a Hub). Live
  permits are GIS REST, missed by the 2026-08-24 CKAN-only skip.
- 2026-08-27 13:10 PT — Row-level: PERMITS Tier 1 (Planning_Permit/1 daily
  `PER_ISSUE_DATE` 2026-08-26 + ShapePHX `_DL` weekly 2026-08-19);
  SLA/STR Tier 1 (`ISSUED_DATE` 2026-08-19); 311 Tier 3; deeds Tier 3.
  Non-`_DL` ShapePHX permits frozen 2022-06-29. City is Wave-3-ready as a
  partial (PERMITS + STR).

## Current step

Done. Research file complete; US-197 commented and marked Done
(assignee unchanged).

## Next step

Orchestrator synthesizes into `docs/expansion-roadmap-wave-3.md`. City
implementation is a later `city-phoenix` stream, not this ticket.
