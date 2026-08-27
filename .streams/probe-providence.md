# Stream log — probe-providence — 2026-08-27

Phase-0 discovery stream for Linear US-206. Research only.

## Claim

- **Stream id:** `probe-providence`
- **Leaf files I will create/edit:**
  - `.streams/probe-providence.md` (this file)
  - `docs/research/wave-3-probe-providence.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Re-probe Providence RI Socrata (catalog answered in 2026-08 but feeds were
2020–2025 stale). Confirm whether anything is now live. Probe
permits/311/SLA/deeds row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed US-206 and dispatched.
- 2026-08-27 12:45 PT — Domain resolved: `data.providenceri.gov` (297
  datasets). Other hostname guesses 404 on the discovery API.
- 2026-08-27 12:50 PT — Row-level: all four families Tier 3. Permits
  `ufmm-rbej` newest `issueddate` 2020-01-23 (0 since 2021). SLA ABL
  `ui7z-kv69` collapsed to 1 row (2011). No 311 table; no deeds
  transaction table. Police case log is live (2026-08-27) but is not
  311. PVD311 / ViewPoint / Kofile are citizen portals, not feeds.
- 2026-08-27 12:55 PT — **REJECT.** Research file written. Findings
  comment on US-206; ticket marked completed. Roadmap file not edited
  (orchestrator hold).

## Current step

Done.

## Next step

None for this stream. Orchestrator may record the REJECT row on
`docs/expansion-roadmap-wave-3.md` in a later serial hold.
