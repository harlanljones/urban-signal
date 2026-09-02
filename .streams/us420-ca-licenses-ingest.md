# Stream log — us420-ca-licenses-ingest — 2026-09-02

## Claim

- **Stream id:** us420-ca-licenses-ingest
- **Ticket:** US-420 (Linear) — Ingest California ABC liquor licensing and CSLB
  contractor feeds + CalEnviroScreen H3 layers.
- **Worktree:** `../ft/US-420-ca-licenses-ingest` (branch `ft/US-420-ca-licenses-ingest`)
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/field_maps_ca_licenses.py` (create)
  - `apps/api/src/producers/ca_license_specs.py` (create)
  - `apps/api/src/producers/calenviroscreen_client.py` (create)
  - `apps/api/src/producers/data/calenviroscreen_tract_centroids.json` (create)
  - `apps/api/tests/unit/test_ca_license_specs.py` (create)
  - `apps/api/tests/unit/test_calenviroscreen_client.py` (create)
  - `apps/api/src/producers/csv_client.py` (preamble skip + OR support)
- **Spine files I expect to need (additive/minimal):**
  - `apps/api/src/config.py` (new ABC endpoint field)
  - `apps/api/src/spatial/cities/data/{oakland,inland_empire,santa_rosa}.yaml`
    (SLA dataset blocks)

## Intent

Add California state-level supplements: ABC liquor license weekly export as SLA
coverage for the CA metros lacking an SLA feed, a CSLB contractor spec (endpoint
unverified — not scheduled), and a CalEnviroScreen 5.0 → H3 res-8 covariate
crosswalk client.

## Research (live-verified 2026-09-02)

- ABC licensing-reports page lists two exports; `DailyExport-CSV.zip` →
  `ABC-DailyDataExport.csv` (129,024 rows). First line is a one-field preamble
  ("Updated Wednesday ..."), then a 27-column quoted header. Dates are
  `DD-MON-YYYY`. Premise address only → `needs_geocode`.
- CA ABC counties for the gap metros: oakland=ALAMEDA (5,088 rows),
  inland_empire=RIVERSIDE (5,916) + SAN BERNARDINO (4,630),
  santa_rosa=SONOMA (4,972).
- CSLB `DataDownload.aspx` → 404. NREL-style unverified spec only.
- CalEnviroScreen 5.0 CSV live on data.ca.gov (9,106 rows, 70 cols, tract GEOID
  + scores, no coordinates). Tract centroids derived from the 5.0 shapefile
  (CA Teale Albers EPSG:3310 → EPSG:4326 via pyproj) and bundled.

## Decisions

- 2026-09-02 — Register ABC as a **snapshot** SLA feed (full weekly zip
  re-pulled, id-dedup diff is the churn signal — KC SLA precedent). Only the
  three metros with NO existing SLA feed get it (ADR 0007: one endpoint per
  FeedType per CityId; SNAP metros keep SNAP).
- 2026-09-02 — CSVClient gets a generic single-field preamble auto-skip so the
  ABC metadata line never becomes the DictReader header. Safe for every
  existing CSV feed (all have multi-column headers).
- 2026-09-02 — `_row_matches` gains top-level `OR` (inland_empire two-county
  slice); single-branch behavior unchanged.
- 2026-09-02 — CalEnviroScreen is a covariate client only (mirrors US-401
  environmental stress): no new event schema, no scheduler/registry wiring.

## Current step

DONE — implemented and verified.

## Next step

PR_DESCRIPTION.md written; ticket moved to In Review (orchestrator commits).
