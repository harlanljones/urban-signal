# Stream log — validate-airnow-aqs — 2026-08-30

## Claim

- **Stream id:** `validate-airnow-aqs`
- **Leaf files I will create/edit:** `docs/research/airnow-aqs-validation.md` (required), `.streams/validate-airnow-aqs.md`, plus optional leaf module `apps/api/src/spatial/airnow_signal.py` and `apps/api/tests/unit/test_airnow_signal.py`
- **Spine files I expect to need:** none

## Intent

Evaluate EPA AirNow real-time observations and the validated AQS archive as environmental-stress features for short-lived, location-sensitive market disruption. Produce a validation doc that probes both sources' live API surfaces (AQS with the documented test key, AirNow via the publicly accessible `reportingarea.dat` product), characterizes monitor density across 3 registered metros (Los Angeles — dense, New Orleans — moderate, Tyler — sparse), and assesses the feasibility of mapping monitor/reporting-area observations to the repo's H3 7–9 hierarchy as `ContextObservationEvent` covariates. The doc alone is the deliverable; no feed is registered, no `FeedType` is added.

## Decisions

- 2026-08-30 — AQS API is live and queryable with the documented test key (`test@aqs.api` / `test`). Met data endpoints (metaData/isAvailable, list/states, monitors/byBox, sampleData/byBox, dailyData/byBox) all return real data. Rate limit: 10 req/min, 1M rows/req, pause 5s between requests.
- 2026-08-30 — AirNow API endpoints are key-gated (HTTP 401 without key). No non-production key is available in this environment. **However**, the AirNow `reportingarea.dat` file product at `https://files.airnowtech.org/airnow/today/reportingarea.dat` is **publicly accessible without authentication** (HTTP 200, 1.99 MB, 6,841 rows, 892 distinct reporting areas, 16 pollutants, updated twice per hour at :55 and :25). This is the key finding: AirNow's real-time observations can be ingested anonymously as a file product.
- 2026-08-30 — AQS 2026 data is not yet available (test query for 2026-08 returned "No data matched your selection"). Latest accessible data is ~2023 (consistent with the documented 6+ month validation lag). The test key has a limited quota.
- 2026-08-30 — Monitor density confirmed: Los Angeles (13 PM2.5+O3 monitors), New Orleans (6), Tyler (1). AQS monitors return precise lat/lng in WGS84/NAD83, suitable for H3 assignment.
- 2026-08-30 — The `reportingarea.dat` file contains per-pollutant AQI values and categories at reporting-area point coordinates, with both observed (O) and forecast (F) rows. This is a near-real-time context signal that could map to `ContextObservationEvent` with `period_type="hour"`.
- 2026-08-30 — AirNow and AQS are both best suited as **context/anchor** signals (never LIMS terms), fitting the `ContextObservationEvent` shape. Neither is a per-event feed like permits/311/SLA/deeds. AQS would be a trailing anchor (6+ month lag); AirNow would be a near-real-time context layer.

## Current step

Validation doc written; leaf module `apps/api/src/spatial/airnow_signal.py` + unit test added and passing.

## Next step

None — leaf stream complete. Verify no spine files touched, then report.