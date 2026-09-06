# US-374: Build NppesDiffProducer; register NPI registry weekly diffs as medical-office churn

## Summary

This PR completes Linear ticket US-374 by wiring the weekly NPPES (National Plan and Provider Enumeration System) NPI registry incremental diffs into Urban Signal as national medical-office churn events.

### Changes Made
1. **NPPES Diff Producer (`apps/api/src/producers/nppes_diff_producer.py`)**:
   - Leaf diff producer filtering for medical/clinical taxonomy codes (excluding DME supplier `33xx` codes) and geocoding metro-filtered deltas.
   - Added `self.socrata = None` and `run_stream(...)` method to support the scheduler stream polling interface and interlock platform dispatch checks.
2. **National Feed Registry (`apps/api/src/spatial/national_feeds.py`)**:
   - Added `NationalFeed.NPPES_MEDICAL = "nppes_medical"` enum member and `NationalFeedSpec` registration producing `SLALicenseEvent` records to `settings.topic_sla` with `producer_key="nppes"`.
3. **Scheduler Wiring (`apps/api/src/producers/scheduler.py`)**:
   - Registered `nppes` (`NppesDiffProducer`) in `MunicipalIngestionScheduler.producers`.
   - Wired `nppes_medical` job in the national feeds loop for scheduled execution.
4. **Tests & Invariant Gates**:
   - Added unit test `test_nppes_medical_is_registered_and_dispatchable` in `apps/api/tests/unit/test_scheduler_national_feeds.py`.
   - Updated `apps/api/tests/unit/test_gbfs_and_national_feeds.py` to assert the updated national feeds set and exempt `settings.topic_sla` shared topic in national-vs-city cross checks.
   - Added tests in `apps/api/tests/unit/test_nppes_diff_producer.py` covering `socrata` attribute, `run_stream` behavior, and Kafka event emitting.
   - Fixed `VENV_PYTHON` fallback in `scripts/verify_cicd_preflight.py`.
   - Added `.streams/us-374.md`.

## Verification

- `pytest apps/api/tests/unit/test_nppes_diff_producer.py apps/api/tests/unit/test_gbfs_and_national_feeds.py apps/api/tests/unit/test_scheduler_national_feeds.py`: 54/54 passed.
- `pytest -m interlock`: 35/35 passed.
- `python3 scripts/verify_cicd_preflight.py`: All 6 gates passed (interlock, dashboard ↔ product cross-ref, product facts check, product lint, dashboard export, ruff check).

