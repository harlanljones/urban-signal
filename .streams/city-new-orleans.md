# Stream log — city-new-orleans — 2026-08-23

## Claim

- **Stream id:** `city-new-orleans`
- **Leaf files I will create/edit:**
  - `src/spatial/cities/new_orleans.py`
  - `tests/unit/test_producers_new_orleans.py`
  - `.streams/city-new-orleans.md` (this file)
- **Spine files I expect to need (orchestrator applies after I finish):**
  - registry/config/producer spine entries per docs/agents/spine-manifest.txt
  - proposed field_map JSON recorded in Decisions below

## Intent

Wave C1 of docs/expansion-roadmap.md §4: add New Orleans metro spatial layer
(metro bbox, division bboxes, submarkets, divisions) mirroring seattle.py /
los_angeles.py, plus unit tests mirroring test_producers_la.py with LIVE
Socrata fixtures captured today for the four feeds (permits rcm3-fn58,
311 2jgv-pqrq, licenses hjcd-grvu, NORA deeds hpm5-48nj). Registration tests
are expected red until the orchestrator lands the spine.

## Decisions

- 2026-08-23 — Metro bbox pinned at min_lat 29.82 / max_lat 30.16 /
  min_lng -90.30 / max_lng -89.62; excludes north-shore St. Tammany leak
  (Madisonville ~30.38 lat). Verified against live fixtures.
- 2026-08-23 — Going with 9 divisions (8 required + ST_BERNARD_CHALMETTE).
- 2026-08-23 — Registry watermark_col pins verified against live rows:
  permits "issuedate", 311 "date_created", licenses "businessstartdate",
  deeds "sale_date". Roadmap table's "createddate"/"created_date" for 311 is
  wrong; actual column is `date_created`.
- 2026-08-23 — Proposed field_map JSON for orchestrator (verified against
  untruncated live rows via curl + json.tool):

```json
PERMITS (rcm3-fn58): {"job_id": ["numstring"], "latitude": ["location_1.latitude"], "longitude": ["location_1.longitude"], "cost": ["constrval"], "job_type": ["type"], "issuance_date": ["issuedate"], "filing_date": ["filingdate"], "status": ["currentstatus"], "borough": ["subdivision"]}
311 (2jgv-pqrq): {"incident_id": ["service_request", "rowid"], "created_date": ["date_created"], "closed_date": ["case_close_date"], "descriptor": ["request_reason"], "incident_address": ["final_address"], "borough": ["address_councildis"]}
SLA (hjcd-grvu): {"license_id": ["businesslicensenumber"], "effective_date": ["businessstartdate"], "license_type": ["businesstype"], "dba": ["businessname"], "premises_name": ["ownername"]}
DEEDS (hpm5-48nj): {"doc_id": ["identifier"], "bbl": ["geopin"], "latitude": ["geocoded_column.latitude"], "longitude": ["geocoded_column.longitude"], "doc_type": ["disposition_channel"], "borough": ["council_district"]}
```

## Current step

Done. Spine applied by orchestrator; all gates green.


## Next step

None. Interlock 17/17, city suite + full suite 318/318. Field maps registered exactly as proposed (Norfolk job_type order flipped to work_type-first during interlock review — bare 'Building' classified OT; NB/A2 signal lives in work_type).
