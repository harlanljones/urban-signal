# Stream log — city-columbus — 2026-08-24

## Claim

- **Stream id:** `city-columbus` (Linear HJ-118, claimed via --assignee self)
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/columbus.py`,
  `apps/api/tests/unit/test_producers_columbus.py`
- **Spine files I expect to need (orchestrator-held):** `config.py`,
  `city_registry.py`, `cities/__init__.py`, `serving/dashboard.py`,
  synced `apps/dashboard/public/index.html`

## Intent

Columbus OH permits (arcgis Building_Permits/0, ISSUED_DT). Scope: gates G1–G11 incl. G10 dashboard wiring. Leaf stream verifies
the endpoint live, authors geometry + contract tests, and returns a spec
recommendation; orchestrator lands the spine hold and resolves the ticket.

## Current step

Leaf stream dispatched.

## Next step

Orchestrator spine hold after leaf report.

## Outcome (2026-08-24)

Completed. PERMITS registered: arcgis Building_Permits/0, watermark ISSUED_DT,
id_keys=["B1_ALT_ID"] (OBJECTID excluded from the job-id chain per ticket),
cadence 7, oid_field OBJECTID, max_record_count 2000, 7-entry field_map
(job_id/issuance_date/cost/address_street/zipcode/status/job_type — each
load-bearing vs producer chains). Spine landed: config endpoint Field,
CityId.COLUMBUS + aliases columbus/columbus_oh, job_suffix cmoh, registry
entry, __init__ exports+__all__, dashboard selector/CITY_CONFIGS/
cityCoordinates/autodetect, index.html resynced.

Live leaf evidence: newest ISSUED_DT age 2.78d at probe → honest cadence 7;
parse rate 300/300 through real producer+client; 63% zero-cost permits
(G3_VALUE_TTL=0 quirk confirmed as events with cost 0.0, never parse
failures); all coords inside COLUMBUS_METRO_BBOX; volume grew to 7,176 since
Jul 1 (survey said ~6,782 — consistent growth).

Gates: interlock 20 passed; full suite 615 passed / 0 failed; ruff clean on
new files; spine debt identical to HEAD (36 = 36).
