# Stream log — west-anaheim — 2026-08-28

## Claim

- **Stream id:** west-anaheim
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/anaheim.py
  - apps/api/src/producers/field_maps_anaheim.py
  - apps/api/tests/unit/test_producers_anaheim.py
- **Spine files I expect to need:** NONE

## Intent

Live-probe anaheim.net (ArcGIS) open-data feeds for Anaheim, CA; verify 1-4
official feeds (permits / 311 / SLA licenses / deeds; crime only with coords
per ADR-0004); then build leaf registration files (city module + field maps +
spine-stable unit tests) for verified feeds only. REJECT with evidence if no
verifiable official feed exists. No spine edits, no commits, no Linear updates.

## Decisions

- 2026-08-28 12:45 — Hub is live: `anaheim.opendata.arcgis.com` (official city domain) lists
  datasets on the city AGOL org `services3.arcgis.com/hPs600I3X0RTaaaq` + city ArcGIS Server
  `gis.anaheim.net/map/rest/services` (v11.5; OpenData2 = reference geography only, no
  transactional layers).
- 2026-08-28 12:50 — PERMITS VERIFIED: `Accela_Building_Permits/FeatureServer/0`, 191,477
  rows, point geometry, store SR WKID 2230 (CA zone 6 ftUS) **correctly declared** — host
  honors outSR=4326 (live fixtures returned degrees). Watermark `permitissued` (esri Date,
  epoch-ms): 14,113 nulls; newest non-future 2026-08-06 (BLD2026-00346); **1 future sentinel**
  BLD2026-01741 @ 2026-09-13T00:00:00Z → spec `where permitissued <= CURRENT_TIMESTAMP`.
  Publishing lag ~3wk (steady ~400-570/mo through Aug 6) → expected_cadence_days=21 (NYC
  deeds style). jobvaluation is a string incl. negatives ("-15536" ADU conversion).
- 2026-08-28 13:05 — SLA VERIFIED (Active snapshot only): `ActiveBusinessLicenses/FeatureServer/0`,
  15,263 rows = exactly the casestatus='Active' subset of the full-history layer. 2,000-row scan:
  818 real-degree geometries / 0 feet / 1,182 null → geometry lift safe, needs_geocode=True for
  null-geometry rows. Watermark `applicationdate` (esriFieldType**DateOnly** → "2026-06-02"
  strings; ANSI-date host check NOT needed — ISO string where clauses verified live): 0 nulls,
  0 future sentinels, newest 2026-06-02 (~87d publishing lag) → expected_cadence_days=90.
- 2026-08-28 13:05 — FULL-HISTORY SLA REJECTED (mixed-CRS trap, live evidence):
  `Business_Licenses/FeatureServer/0` (82,636 rows) declares SR **wkid 4326 but stores WKID 2230
  state-plane feet** and IGNORES outSR (x=6107939.8, y=2262155.6 returned with outSR=4326 —
  values match the permits layer's 2230 extent). Sample 200 @ offset 40000: 148 feet / 52 null /
  0 degrees. `ArcGISClient._flatten_feature` lifts geometry x/y unconditionally and
  `sla_licenses_producer` has NO projected-coordinate guard (permits producer does) → feet would
  emit as latitude/longitude on the wire. Not registered; not listed as companion.
- 2026-08-28 13:10 — 311 NOT REGISTERED: only complaint-family feed on the Hub is Code
  Enforcement Cases (171,255 rows, native 4326 points, fresh watermark 2026-08-27) — code
  enforcement is a different family (Lynchburg TRAKiT discipline; Spartanburg rejects its
  CodeManagement the same way). No citizen-request/311 surface exists (Hub q=311/request/complaint:
  0 matches).
- 2026-08-28 13:12 — CRIME NOT REGISTERED: `Crime_Mapping_` is a 7-day rolling TABLE (2026-08-11
  → 2026-08-18), geometryType None, intersection-only `Location` ("MAGNOLIA AV // CRIS AV"),
  270 rows. Rolling views are not registered (Aurora L156/L157 precedent); ADR-0004 address path
  would geocode intersections lossily.
- 2026-08-28 13:15 — DEEDS NOT REACHABLE: Orange County AGOL/Hub searches (deed/sales/recorded
  document; org-owner variants) return 0 datasets; OC Clerk-Recorder is a search portal only.
  Partial (permits + sla) is acceptable per ticket.
- 2026-08-28 13:20 — Final shape: TWO-FEED metro (permits + sla) like Aurora. Division set
  (evidence-based): DOWNTOWN_ANAHEIM, RESORT_DISTRICT, PLATINUM_TRIANGLE, WEST_ANAHEIM,
  ANAHEIM_CANYON, ANAHEIM_HILLS with 10 submarkets.

## Current step

Phase B — writing the three leaf files (anaheim.py, field_maps_anaheim.py,
test_producers_anaheim.py).

## Next step

Run verify suite from apps/api; record outcomes; write Spine delta + Outcome.
