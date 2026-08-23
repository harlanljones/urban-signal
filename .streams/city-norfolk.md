# Stream log — city-norfolk — 2026-08-23

## Claim

- **Stream id:** `city-norfolk`
- **Leaf files I will create/edit:** `src/spatial/cities/norfolk.py`, `tests/unit/test_producers_norfolk.py`, `.streams/city-norfolk.md`
- **Spine files I expect to need:** producers/registry/config (orchestrator applies after finish; registration tests red until then — expected)

## Intent

Wave C1: register Norfolk, VA (partial city) with two Socrata feeds on data.norfolk.gov — PERMITS `fahm-yuh4` and DEEDS/Sales `qva7-tzrf`. Deliver seattle-shaped spatial layer (metro bbox, 5 divisions, 12–16 submarkets) plus la-mirrored producer tests with LIVE-captured fixtures. 311 (`nbyu-xjez`) and licenses (`dpi6-sct5`) DEFERRED pending address-geocoding.

## Decisions

- 2026-08-23 (start) — Scope correction trusted over docs/research/socrata-sweep.md §Norfolk: TWO feeds only; 311 (`nbyu-xjez`, address-string location) + licenses (`dpi6-sct5`, no geometry) DEFERRED pending address geocoding. Deferral noted in module docstring.
- 2026-08-23 — Live fixtures captured (curl → json.tool, untruncated):
  - PERMITS `fahm-yuh4` newest row B26-01819: has latitude/longitude DIRECT strings, type="Building", work_type="Alteration/Repair - ...", status, application_date, issue_date (2026-12-24 — future-dated scheduled filing quirk confirmed), total_fee "1378.98", project_cost "310000.0". Columns project_cost/application_date/type/work_type all EXIST on the live row — proposed map below verified against reality.
  - DEEDS `qva7-tzrf` newest row doc 260016116: transfer_date 2026-08-19, consideration "400000", grantor/grantee present, gpin/parcel_id/lrsn present, NO coordinates.
- 2026-08-23 — Verified field_map for orchestrator spine edit:
  ```python
  PERMITS: {"cost": ["project_cost"], "filing_date": ["application_date"], "job_type": ["type", "work_type"]}
  DEEDS:   {"doc_id": ["document_number"], "bbl": ["gpin", "parcel_id"]}
  ```
- 2026-08-23 — Metro bbox set to min_lat 36.83 (not 36.85): South Norfolk division (Berkley/Campostella south of the Elizabeth River, real lat ~36.83–36.88) must nest inside the metro bbox per interlock invariant; sample permit row at 36.8512 still comfortably contained; Portsmouth (-76.36) still excluded. max_lng -76.17 excludes Virginia Beach line.
- 2026-08-23 — job_type reality check: with no field_map entry the permit chain falls through to its literal default `"A1"` (not OT as briefed); xfail test asserts A2 post-map since work_type "Alteration/Repair..." classifies A2 once mapped.
- 2026-08-23 — is_in_norfolk_metro guards None inputs (mirrors los_angeles.py; seattle.py lacks the guard).
- 2026-08-23 — Deeds FY rotation caveat recorded in module docstring: sales publish as annual fiscal-year datasets FY23...FY27; register current-year file, rotate ID each July 1 (runbook pointer).

## Results

- `src/spatial/cities/norfolk.py`: 5 divisions, **13 submarkets** (Downtown Waterfront 3, Ghent/Westburg 3, Ocean View 3, Military Circle 2, South Norfolk/Berkley 2), every submarket claimed exactly once; aliases {"norfolk", "norfolk_va"} proposed for spine ALIASES.
- Parser tests PASSING today (live-fixture): permit parses / job_id / lat-lng / cost>0 via total_fee / issuance_date; deed parses / doc_id=document_number / parties+consideration / transfer_date / null-lat-lng-null-h3. Spatial-invariant tests all pass.
- XFAIL until spine: permit filing_date (application_date), permit job_type NB/A2, permit division resolution, deed bbl (gpin).
- RED-by-design (10): registration/aliases/watermarks/partial-feeds — need CityId.NORFOLK in REGISTRY.

## Current step

Done. Spine applied by orchestrator; all gates green.


## Next step

None. Interlock 17/17, city suite + full suite 318/318. Field maps registered exactly as proposed (Norfolk job_type order flipped to work_type-first during interlock review — bare 'Building' classified OT; NB/A2 signal lives in work_type).
