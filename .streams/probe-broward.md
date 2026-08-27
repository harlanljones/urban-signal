# Stream log — probe-broward — 2026-08-27

US-199 sub-stream. Finish Broward County row-level probe from the host
fingerprint. Do not write `docs/research/wave-3-probe-miami.md`.

## Claim

- **Stream id:** `probe-broward`
- **Leaf files I will create/edit:**
  - `.streams/probe-broward.md` (this file)
  - `docs/research/wave-3-probe-broward.md` (NEW)
- **Spine files I expect to need:** none

## Intent

Search Broward County GeoHub for permits, 311, SLA, deeds. Row-level
newest-watermark probe. Tier 1/2/3.

## Decisions

- 2026-08-27 12:31 PT — Fingerprint: geohub-bcgis.opendata.arcgis.com Hub
  HTML + search API live. www.broward.org/OpenData 404.
  opendata.broward.org and data.broward.org DNS fail. gis.broward.org
  connection refused. Do not retry dead hosts except as a one-line
  confirmation.
- 2026-08-27 12:48 PT — Hub dataset collection is 123 items, almost all
  ACS/flood/boundaries. `data.json` 500; DCAT-US truncated. Family
  keyword search: permits/311 = 0 on the Open Data collection.
- 2026-08-27 12:52 PT — SLA hit: `TaxDatabase2021/0` + email overlay,
  111,263 points, `Business_Start_Date` newest 2026-09-07, lastEdit
  2026-08-24. Native geometry. Fort Lauderdale ~20k rows. **Tier 1.**
- 2026-08-27 12:55 PT — Org search (not Hub catalog) found
  `HCEDPossePermitsRef/4`: live `ISSUEDATE` 2026-08-26 but ROW/utility
  (Telephone/Electric/Driveway), not building permits. Accela ePermits
  is a UI only. **PERMITS Tier 3.** 311 is a jurisdiction lookup +
  Power BI, no ticket table. **311 Tier 3.**
- 2026-08-27 13:00 PT — Deeds: BCPA `PARCEL_POLY_BCPA_TAXROLL`
  `SALE_DATE_1` newest 2024-09-27 (0 in 2025/2026). FDOR 2025 centroids
  Broward is `CO_NO=16` (765,030), not 11. Annual NAL, not a stream.
  `Real_Property_TEST` frozen 2023-03. **DEEDS Tier 3.**
- 2026-08-27 13:05 PT — Prior worker claimed the research file; parent
  re-dispatched because the file was missing from the expected handoff.
- 2026-08-27 13:12 PT — Re-dispatch: independently re-probed Hub + org
  search + REST folder walk (`bcgishub` needs a browser User-Agent; bare
  curl 403). Confirmed `server/311`, `posse/BCS`, `posse/CodeEnforcement`
  empty. SLA/POSSE/BCPA watermarks match. FTL `TaxParcel` still live
  Broward-shaped (`SALEDATE1` 2026-08-14) but not a county GeoHub feed.
  Wrote `docs/research/wave-3-probe-broward.md`. Fort Lauderdale
  supplement: **yes** (county SLA). Wave-3-ready: **yes, partial** (SLA
  only). No spine edits. No registration. No git commit.

## Current step

Done.

## Next step

None. Orchestrator may fold this leaf into the US-199 Miami write-up
and the Wave 3 roadmap under a later spine hold.
