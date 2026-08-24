# Stream log — city-boston — 2026-08-24

## Claim

- **Stream id:** city-boston
- **Leaf files I will create/edit:** `src/spatial/cities/boston.py`, `tests/unit/test_producers_boston.py`
- **Spine files I expect to need:** `src/config.py`, `src/spatial/city_registry.py`, `src/spatial/cities/__init__.py`, `src/serving/dashboard.py`, `apps/product/public/index.html`, `README.md`

## Intent

Register Boston's three CKAN feeds (approved-building permits, current-year 311,
and Licensing Board SLA) with the existing CKAN client, including the 311
year-resource rollover contract, narrow SLA scope, and explicit no-sales
exclusion. Close with interlock and focused contract evidence.

## Decisions

- 2026-08-24 — Claimed HAR-23 after HAR-18 was confirmed completed and no open blocker remained.

## Current step

Boston leaf geometry and CKAN contract tests are green; registry and dashboard spine are wired, the research cross-link is now applied, and the static dashboard copy has been exported.

## Evidence

- Verified CKAN resources: approved permits `6ddcd912-32a0-43df-9908-63574f8c7e77`, current 311 `1a0b420d-99f1-4887-9851-990b2a5a6e17`, licensing board `04dc653b-1789-4374-9669-b07df7233344`.
- `pytest -q tests/unit/test_producers_boston.py`: 3 passed.
- `pytest -q -m interlock`: 20 passed.
- `scripts/export_dashboard.py` regenerated `apps/product/public/index.html`.
- Read-only feed probe reached all three live CKAN resources: permits newest watermark 2026-08-22, 311 newest watermark 2026-08-22, licensing newest watermark 2026-07-25 (narrow monthly feed).
- Added an explicit rollover dry-run test: 2025-12-31 selects the 2025 resource and 2027-01-02 falls back to the latest known 2026 resource.

## Next step

Post updated implementation evidence to HAR-23 and leave the issue In Progress pending staging ingestion validation.
