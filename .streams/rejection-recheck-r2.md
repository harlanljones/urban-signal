# Stream log — rejection-recheck-r2 — 2026-08-24

## Outcome (2026-08-24)

Completed. scripts/rejection_recheck.py + quarterly workflow
(.github/workflows/rejection-recheck.yml, cron first day of every 3rd month)
+ test_rejection_recheck.py.

Manifest: 10 documented rejections across wave-2-city-candidates.md,
socrata-sweep.md, mc311 evaluation, US-75/US-94 notes — four probe kinds:
socrata_dataset (count+newest), socrata_schema (column-drift watch),
socrata_catalog (family-keyword discovery search), arcgis_layer
(reachability). Statuses: ALIVE_SINCE_REJECTION / STILL_REJECTED /
SUPERSEDED / INACCESSIBLE; reports diffs, never pages (exit 0).

**Acceptance case proven:** kc_311 (rejected 2026-08-23 as "effectively
dead", dataset d4px-6rwg) resolves SUPERSEDED→registered via live probe;
818k+ rows confirmed. nashville_311 watch immediately earned its keep by
surfacing that data.nashville.gov left the Socrata discovery universe
(platform migration) — INACCESSIBLE with manual-re-probe note, consistent
with the US-75 flag that its Current-Year view carries 2026 rows.

Live run: 1 SUPERSEDED, 7 STILL_REJECTED, 2 INACCESSIBLE (nashville +
miami-dade domains gone from discovery). Report persisted to
docs/research/rejection-recheck-report.json (--write-report).

Fixes during build: ISO-date parsing in freshness comparison (silent no-op
found by tests), strict postdates-the-verdict semantics (7-day margin would
have missed KC's own one-day flip), param-aware stub client in tests.

Gates: interlock 20 passed; full suite 683 passed / 3 skipped / 0 failed;
ruff clean.
