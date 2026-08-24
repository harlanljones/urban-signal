# Stream log — city-kansas-city — 2026-08-24

## Claim

- **Stream id:** `city-kansas-city` (Linear HJ-120, claimed via --assignee self)
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/kansas-city.py`,
  `apps/api/tests/unit/test_producers_kansas-city.py`
- **Spine files I expect to need (orchestrator-held):** `config.py`,
  `city_registry.py`, `cities/__init__.py`, `serving/dashboard.py`,
  synced `apps/dashboard/public/index.html`

## Intent

Kansas City MO 311 (socrata d4px-6rwg, open_date_time; corrects prior rejection). Scope: gates G1–G11 incl. G10 dashboard wiring. Leaf stream verifies
the endpoint live, authors geometry + contract tests, and returns a spec
recommendation; orchestrator lands the spine hold and resolves the ticket.

## Current step

Leaf stream dispatched.

## Next step

Orchestrator spine hold after leaf report.

## Outcome (2026-08-24)

Completed — corrects the 2026-08-23 rejection. COMPLAINTS_311 registered:
socrata d4px-6rwg, watermark open_date_time, id_keys ["reported_issue"],
cadence 7 (measured intraday publishing: 14/14 consecutive days, newest row
same-day at probe), 4-entry field_map (reported_issue/issue_type/
open_date_time/current_status — zero chain coverage for any of them).
Exclusions pinned in tests: PERMITS (dead annual archives) and SLA pnm4-68wg
(no date column) both raise KeyError.

Spine landed: config endpoint Field, CityId.KANSAS_CITY + aliases
kcmo/kansas_city/kc_mo, job_suffix kcmo, registry entry, __init__, dashboard
wiring, index.html resynced.

Live leaf evidence: parse rate 25/25 newest rows through real producer;
818,728 rows total; newest open_date_time 2026-08-24T11:07 (age ~0d);
coordinates inside KANSAS_CITY_CORE bbox. Note: legacy bad geocodes exist in
whole-history aggregates (min lat 26.2) — bbox scoped to urban core.

Gates: interlock 20 passed; suite 615 passed / 0 failed; ruff clean.
