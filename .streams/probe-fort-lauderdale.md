# Stream log — probe-fort-lauderdale — 2026-08-27

US-199 sub-stream. Finish Fort Lauderdale GIS row-level probe from the
host fingerprint. Do not write `docs/research/wave-3-probe-miami.md`.

## Claim

- **Stream id:** `probe-fort-lauderdale`
- **Leaf files I will create/edit:**
  - `.streams/probe-fort-lauderdale.md` (this file)
  - `docs/research/wave-3-probe-fort-lauderdale.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Find the ArcGIS REST / Hub behind gis.fortlauderdale.gov and probe
permits, 311, SLA, deeds row-level. Tier 1/2/3.

## Decisions

- 2026-08-27 12:31 PT — Fingerprint: gis.fortlauderdale.gov HTML 200
  (City of Fort Lauderdale GIS). No Hub/Socrata/CKAN hit in the host
  sweep. Need the FeatureServer/MapServer base URL from the page or
  common ArcGIS paths.
- 2026-08-27 12:40 PT — REST bases found: `/server/rest/services`
  (10.9.1 FeatureServers) and `/arcgis/rest/services` (10.6.1 app
  MapServers). Hub `fortlauderdale.opendata.arcgis.com` has 80 items.
- 2026-08-27 12:50 PT — Row-level: permits frozen 2026-03-16 (cliff);
  GIS 311 frozen 2022-02-05; SLA frozen 2020/21 (`ISSUEDATE` all-null);
  TaxParcel `SALEDATE1` live 2026-08-14 but Broward-wide PA snapshot
  (19 cities). FTL is not a Wave-3 leaf; Broward-county-only.

## Current step

Done. Research file written. No spine edits. No commit.

## Next step

None for this stream. Parent US-199 / Broward probe owns county sales.

## Yield

- REST: `https://gis.fortlauderdale.gov/server/rest/services`
- Hub: `https://fortlauderdale.opendata.arcgis.com` (80 datasets)
- Permits **Tier 3** (`SUBMITDT` 2026-03-16)
- 311 **Tier 3** (`REQUESTDATE` 2022-02-05)
- SLA **Tier 3** (`ESTABDATE` 2020-07-06)
- Deeds **not an FTL leaf** (`SALEDATE1` 2026-08-14, Broward PA)
- Viable Wave-3 city leaf: **no**
