# Stream log — probe-atlanta — 2026-08-27

Phase-0 discovery stream for Linear US-198. Research only.

## Claim

- **Stream id:** `probe-atlanta`
- **Leaf files I will create/edit:**
  - `.streams/probe-atlanta.md` (this file)
  - `docs/research/wave-3-probe-atlanta.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Resolve opendata.atlantaga.gov (TLS cert failure 2026-08; retry). Probe
permits/311/SLA/deeds row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed US-198 and dispatched.
- 2026-08-27 12:40 PT — TLS still dead (SAN `*.azurewebsites.us`, Azure 404).
  Working platform is ArcGIS Hub `dpcd-coaplangis.opendata.arcgis.com` + DCP
  ArcGIS Server 11.3. City is not Socrata/CKAN.
- 2026-08-27 12:45 PT — All four families Tier 3. Wave-3-ready: no.
  No registration contract. Research file written.

## Current step

Done. Findings on US-198; issue marked completed. Assignee left in place.

## Next step

None for this stream. Orchestrator may record yield in dispatch-log. Do not
edit `docs/expansion-roadmap-wave-3.md` from this stream.
