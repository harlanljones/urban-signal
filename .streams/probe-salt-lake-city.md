# Stream log — probe-salt-lake-city — 2026-08-27

Phase-0 discovery stream for Linear US-202. Research only.

## Claim

- **Stream id:** `probe-salt-lake-city`
- **Leaf files I will create/edit:**
  - `.streams/probe-salt-lake-city.md` (this file)
  - `docs/research/wave-3-probe-salt-lake-city.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Resolve the Salt Lake City UT opendata portal (unprobed). Probe
permits/311/SLA/deeds row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed US-202 and dispatched.
- 2026-08-27 12:40 PT — Platform = ArcGIS Server (`maps.slc.gov`) + Hub
  (`slcgov.opendata.arcgis.com`). State Socrata `opendata.utah.gov`
  decommissioned. CivicData Accela CKAN last updated 2014 / datastore 404.
- 2026-08-27 12:40 PT — All four families **Tier 3**. Permits: Accela
  Active Building Permits live endpoint but watermark `OpenedDate`
  2025-04-03 (active-only, stale). 311: Cartegraph Request 56k rows,
  `EntryDate` froze 2026-06-20 (closest miss). SLA: none. Deeds: LIR
  snapshot / recorder paywall. **Not Wave-3-ready.**
- 2026-08-27 12:40 PT — Did not edit `docs/expansion-roadmap-wave-3.md`
  (orchestrator-owned). Findings on US-202 + research file.

## Current step

Done. Research file written; US-202 commented and marked Done (assignee kept).

## Next step

None for this stream. Orchestrator may fold the tier table into the Wave 3
roadmap. Re-probe Cartegraph if a later wave needs a Mountain West swap.
