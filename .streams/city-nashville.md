# Stream log — city-nashville — 2026-08-24

## Claim

- **Stream id:** `city-nashville` (Linear HJ-119, claimed via --assignee self)
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/nashville.py`,
  `apps/api/tests/unit/test_producers_nashville.py`
- **Spine files I expect to need (orchestrator-held):** `config.py`,
  `city_registry.py`, `cities/__init__.py`, `serving/dashboard.py`,
  synced `apps/dashboard/public/index.html`

## Intent

Nashville TN permits (arcgis Building_Permits_Issued_2/0, Date_Issued; optional STR feed). Scope: gates G1–G11 incl. G10 dashboard wiring. Leaf stream verifies
the endpoint live, authors geometry + contract tests, and returns a spec
recommendation; orchestrator lands the spine hold and resolves the ticket.

## Current step

Leaf stream dispatched.

## Next step

Orchestrator spine hold after leaf report.

## Outcome (2026-08-24)

Completed — two feeds registered: PERMITS (Building_Permits_Issued_2/0,
watermark Date_Issued, id_keys Permit__+ObjectId, oid_field "ObjectId"
mixed-case!, max_record_count 1000, cadence 7, field_map incl. mandatory
latitude=["Lat"]/longitude=["Lon"] — mixed-case attrs ride NO fallback chain)
and SLA (Residential_STR_Permits_view/0, cadence 14, full license-class map;
STR included on leaf evidence: usable watermark + coords + 200/200 parse).

Spine landed: two config Fields, CityId.NASHVILLE + aliases
nashville/nashville_tn, job_suffix bna, registry entry, __init__,
dashboard wiring, index.html resync. One leaf test updated post-registration:
the empty-map documentation test now patches resolve_field_map explicitly
(previously relied on the feed being unregistered).

FLAG for re-adjudication (recorded, out of scope): hubNashville 311's
Current_Year view now carries 2026 rows (newest 2026-08-24) despite the
ticket's 2025-stuck claim — a follow-up ticket can verify + register it.

Live leaf evidence: permits 200/200 and STR 200/200 parse through real
pipeline; volumes match survey exactly (1,270 since Jul 1); all coords inside
bboxes; two-date model validated by a 2022 application issuing in 2026.

Gates: interlock 20 passed; suite 615 passed / 0 failed; ruff clean.
