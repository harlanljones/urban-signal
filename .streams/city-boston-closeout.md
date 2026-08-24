# Stream log — closeout-boston — 2026-08-23

## Claim

- **Ticket:** HJ-23
- **Stream id:** closeout-boston
- **Leaf files I will edit:** `apps/api/tests/unit/test_producers_boston.py`, `.streams/city-boston-closeout.md`
- **Existing Boston trail:** `.streams/city-boston.md` (read-only historical context)
- **Spine files needed:** none for this audit; report any required patch without editing shared files

## Intent

Audit Boston's three CKAN registrations, explicit no-sales exclusion, 311 year-resource rollover, and G1–G10 evidence. Add only Boston leaf tests/documentation/evidence and clearly record live or staging blockers.

## Decisions

- 2026-08-23 — Claimed the Boston closeout leaf after confirming the worktree contains unrelated edits; those edits remain untouched.
- 2026-08-23 — Graph project `home-harlan-dev-urban-signal` is indexed and ready; coverage checked for the Boston test, registry, and CKAN client with no recorded gaps.

## Current step

Focused audit complete. Shared registry, CKAN client, dashboard, and static-copy files were read-only for this stream.

## G1–G10 evidence

- **G1 interlock invariants:** historical Boston trail records `pytest -q -m interlock` as 20 passed. A fresh run was started from `apps/api` but remained running without output during this closeout; no new green result is claimed.
- **G2 full unit suite:** not rerun in this leaf; no Boston-specific failure observed in the focused run.
- **G3 geography:** `pytest -q tests/unit/test_producers_boston.py` passed 4 tests covering metro containment, division containment, and submarket ownership.
- **G4 fixture fidelity:** Boston CKAN resource IDs and field maps are pinned in `test_boston_resources_and_field_maps_are_pinned`; CKAN client fixtures include recorded Boston datastore and non-datastore responses.
- **G5 live parse rate:** blocked here because the live opt-in tests cannot resolve `data.boston.gov` (`[Errno -3] Temporary failure in name resolution`).
- **G6 backfill parity:** staging/database evidence unavailable to this leaf; no claim made.
- **G7 freshness lag:** staging soak/metrics unavailable; local source probe could not complete because the API test context cannot import `scripts.feed_staleness_probe` (`ModuleNotFoundError: No module named 'scripts'`).
- **G8 pipeline hygiene:** staging DLQ/duplicate/null-H3 metrics unavailable; no claim made.
- **G9 division resolution:** no staging/PostGIS group-by evidence available; geometry contract only verifies declared containment.
- **G10 docs + map:** existing interlock/dashboard evidence and `docs/research/non-socrata-platforms.md` cover Boston's map and research cross-link; this stream did not edit shared dashboard/static files.

## Evidence

- `source .venv/bin/activate && pytest -q tests/unit/test_producers_boston.py tests/unit/test_ckan_client.py` from `apps/api`: **19 passed, 2 skipped** (live tests intentionally disabled).
- `URBAN_LIVE_PROBE=1 pytest -q -m live tests/unit/test_ckan_client.py`: **2 failed on DNS resolution**, not an assertion or parser result.
- `git diff --check`: passed for the worktree's current diff.
- Graph project `home-harlan-dev-urban-signal` was ready at generation `2026-08-24T03:20:54Z`; coverage checks for the Boston test, registry, and CKAN client reported no recorded gaps.

## Blockers / parent interlock notes

- No shared-spine patch is required by this audit.
- Live CKAN and staging G5–G9 evidence require network/staging access outside this sandbox. The parent should rerun the live probe and staging freshness/parse/division/quality checks before marking A3 complete.
