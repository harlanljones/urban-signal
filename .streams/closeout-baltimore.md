# Stream log — closeout-baltimore — 2026-08-23

## Claim

- **Stream id:** `closeout-baltimore` (ticket HJ-25)
- **Leaf files I will create/edit:** `.streams/closeout-baltimore.md`, Baltimore-specific `apps/api/tests/unit/test_producers_baltimore.py` only if a leaf coverage gap is found, and Baltimore closeout evidence/docs under `docs/` only if disjoint.
- **Spine files I will not edit:** registry/config/city exports, producer implementations, dashboard sources, README coverage table, and `apps/product/public/index.html`; report exact required patches to the parent interlock instead.

## Intent

Audit the existing Baltimore implementation against roadmap gates G1–G10 and the parent plan, run reproducible focused/compile checks with the repository `.venv`, record live/staging evidence or blockers, and leave a concise handoff for the parent integrator.

## Decisions

- 2026-08-23 — Shared worktree has unrelated modified files and an earlier Baltimore implementation; preserve all existing edits and do not duplicate ownership.
- 2026-08-23 — Existing `.streams/city-baltimore.md` and `.streams/har-25-baltimore.md` are historical trails; this closeout owns only this evidence trail.
- 2026-08-23 — Codebase graph generation is current and reports no parse-partial/skipped files for the relied-on source; `apps/product/public/index.html` remains intentionally excluded and was inspected directly.
- 2026-08-23 — Focused Baltimore tests: 5 passed. Root-targeted `test_interlock_gate.py`: 20 passed. Edge tests: 2 passed. Compileall and `git diff --check`: passed.
- 2026-08-23 — `pytest -m interlock` from `apps/api` is blocked during collection by `ModuleNotFoundError: scripts` in `tests/unit/test_feed_staleness_probe.py`; root-targeted interlock tests provide the runnable Baltimore gate evidence.
- 2026-08-23 — No staging credentials, database metrics, backfill probe output, or 24-hour soak evidence are present in this worktree; G5–G9 remain open/unevidenced.

## Current step

Checks complete. Baltimore leaf and wiring evidence has been audited; live/staging gates remain explicitly unevidenced.

## Next step

Parent integrator resolves the suite collection blocker and supplies staging/live G5–G9 evidence before final closeout.

## G1–G10 closeout

- **G1 — pass (scoped):** `apps/api/tests/unit/test_interlock_gate.py` passed 20 tests from repo root. The canonical `cd apps/api && pytest -m interlock` command is blocked by the unrelated `scripts` import collection failure noted above.
- **G2 — blocked:** full unit suite was not accepted as green because the same `scripts` collection failure prevents the marker run; no Baltimore-specific failure observed.
- **G3 — pass:** Baltimore geometry/containment and submarket ownership assertions pass in the focused suite.
- **G4 — pass (fixture-in-test):** focused tests include representative permit and 311 rows with IDs, dates, coordinates, and parsed event assertions. Liquor has field-map contract coverage but no captured row parser test.
- **G5 — unevidenced:** no newest-500 live/staging parse-rate probe result.
- **G6 — unevidenced:** no source-count versus ingested-count backfill parity result.
- **G7 — unevidenced:** no staging freshness p95/24-hour soak metrics.
- **G8 — unevidenced:** no DLQ, duplicate, or null-H3 staging counters.
- **G9 — unevidenced:** no PostGIS division-resolution group-by result; unit geometry only establishes declared containment.
- **G10 — pass (wiring present):** README row, API dashboard selector/config, site city entry, and ignored edge static copy all contain Baltimore; edge tests and the interlock dashboard-wiring test pass.

## Parent interlock handoff

No shared-spine patch is requested from this stream: the current Baltimore registration and map wiring are present. Parent should resolve the `scripts` import/layout failure, obtain staging/live G5–G9 evidence, and avoid marking HJ-25 fully closed until those gates are supplied.
