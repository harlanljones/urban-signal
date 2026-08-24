# Stream log — boston-runtime-evidence — 2026-08-23

## Claim

- **Stream id:** `boston-runtime-evidence`
- **Leaf files I will create/edit:** `.streams/boston-runtime-evidence.md`
- **Spine files I expect to need:** none

## Intent

Run available read-only Boston CKAN probes and focused tests using `.venv`, then record G5–G9 staging readiness evidence or exact network/secrets blockers. No registry or dashboard code changes are in scope.

## Decisions

- 2026-08-23 — Claimed runtime-evidence audit as a documentation-only leaf; existing Boston implementation and closeout trails are historical context.
- 2026-08-23 — Graph project `home-harlan-dev-urban-signal` is ready at generation `2026-08-24T03:34:40Z`; coverage checks for the CKAN client, Boston tests, and staleness probe report no recorded gaps (best-effort caveat).
- 2026-08-23 — No registry/dashboard files were opened for editing; no deterministic test was needed because existing contracts cover the requested runtime seam.

## Current step

Read-only checks complete. Focused tests pass; live and staleness probes are blocked by the sandbox's external DNS/network availability.

## G5–G9 evidence

- **G5 live parse rate:** blocked. `URBAN_LIVE_PROBE=1 pytest -q -m live tests/unit/test_ckan_client.py` ran both live tests, and both failed before parsing with `httpx.ConnectError: [Errno -3] Temporary failure in name resolution` for `data.boston.gov`.
- **G6 backfill parity:** not evidenced. No staging database/receiver credentials or reachable staging environment are present; no source-vs-ingested count claim is made.
- **G7 freshness lag:** blocked. `timeout 15s env PYTHONPATH=. python scripts/feed_staleness_probe.py --city boston --dry-run` exited `124` without output, consistent with the unavailable external source; no p95/24-hour soak claim is made.
- **G8 pipeline hygiene:** not evidenced. No staging DLQ, duplicate, or null-H3 counters are available locally; no claim is made.
- **G9 division resolution:** not evidenced at runtime. Existing focused geometry contracts verify declared containment/ownership only; no staging/PostGIS group-by result or ≥90% runtime rate is available.

## Checks

- `source .venv/bin/activate && pytest -q tests/unit/test_producers_boston.py tests/unit/test_ckan_client.py` from `apps/api`: **19 passed, 2 skipped** (live tests disabled by default).
- `source .venv/bin/activate && pytest -q tests/unit/test_producers_boston.py tests/unit/test_ckan_client.py tests/unit/test_feed_staleness_probe.py`: collection blocked by existing import-layout issue, `ModuleNotFoundError: No module named 'scripts'` from `test_feed_staleness_probe.py`; rerunning from repo root with `PYTHONPATH=.` was not attempted as a code change and does not alter the staging blocker.
- `git diff --check`: passed.
- Existing unrelated worktree change `.streams/e2e-spatial-worker-hang.md` was preserved.

## Blockers / handoff

- Live CKAN evidence requires network/DNS access to `data.boston.gov`.
- G6–G9 require staging endpoint/database access, credentials/secrets, and runtime counters/soak output. None are available in this workspace.
- Parent can close staging readiness only after rerunning the live CKAN probe and supplying staging G5–G9 artifacts; this stream does not claim live evidence from historical fixture data.

## Next step

No further in-scope work remains unless network or staging credentials become available.
