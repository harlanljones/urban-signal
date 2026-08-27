# Stream log — probe-oklahoma-city — 2026-08-27

Phase-0 discovery stream for Linear US-204. Research only.

## Claim

- **Stream id:** `probe-oklahoma-city`
- **Leaf files I will create/edit:**
  - `.streams/probe-oklahoma-city.md` (this file)
  - `docs/research/wave-3-probe-oklahoma-city.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Resolve the Oklahoma City OK opendata portal (unprobed). Probe
permits/311/SLA/deeds row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed US-204 and dispatched.
- 2026-08-27 ~12:40 PT — Portal resolved: ArcGIS Hub `open-okc.hub.arcgis.com`
  (DCAT 81 items). Legacy `data.okc.gov` still Incapsula-blocked to curl;
  browser session + Hub FeatureServers are the programmatic path. Not
  Socrata/CKAN. All four families Tier 3. Wave-3-ready: no.

## Current step

Research file written; US-204 findings comment + completed.

## Next step

None for this stream. Do not edit `docs/expansion-roadmap-wave-3.md`
(orchestrator). Do not commit.

## Findings (gist)

| Family | Tier | Watermark | Geocode |
|---|---|---|---|
| Permits | 3 | none (Work Zones occupancy `OBJECTID` newest 2026-08-27, not issuance) | n/a |
| 311 | 3 | none (CitySourced Action Center, no bulk) | n/a |
| SLA | 3 | none (Hotel Motel Tax snapshot, 375 rows, no date) | n/a |
| Deeds | 3 | Land Documents real `Date` max 2026-07-21 easement / 2026-06-02 type D; 0 in 30d; no price | n/a |

Artifact: `docs/research/wave-3-probe-oklahoma-city.md`
