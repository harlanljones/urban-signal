# Stream log — closeout-montgomery — 2026-08-23

## Claim

- **Stream id:** `closeout-montgomery` (HJ-26)
- **Leaf files I will create/edit:** `apps/api/tests/unit/test_producers_montgomery.py`, Montgomery-specific docs/evidence under `docs/`, `.streams/city-montgomery-co-codex.md`
- **Spine files I expect to need:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, `apps/api/src/serving/dashboard.py`, `apps/edge/public/index.html`, `README.md`

## Intent

Finish Montgomery County's two verified Socrata feeds (permit families and ABS liquor licenses), explicitly exclude MC311 because it has no coordinates, and verify G1–G10 including dashboard/static-copy wiring and scorecard evidence.

## Decisions

- 2026-08-23 — Existing Montgomery implementation is present in the shared worktree; inspect and preserve it before making only leaf-scoped corrections.
- 2026-08-23 — Graph project `home-harlan-dev-urban-signal` is indexed and ready with no parse-partial or skipped files; `apps/edge/public/index.html` is intentionally excluded by gitignore, so static wiring requires direct filesystem checks.
- 2026-08-23 — The prior `city-montgomery-co` stream log records the shared implementation; this closeout adds verification only and does not edit source or shared spine/static files.
- 2026-08-23 — The current executable registry has 17 cities but 55 feed jobs, not the roadmap's 57–58 target. This is a parent/integration reconciliation item, not a Montgomery leaf change.

## Current step

2026-08-23 — HJ-26 closeout audit complete. Worktree is shared and unrelated parent/other-stream edits were preserved; ownership remained limited to this log and Montgomery evidence. G1–G10, MC311 exclusion, dashboard/static wiring, and the 17-city/~57-feed target are recorded below.

## Next step

Parent to reconcile the 17-city/55-feed executable count against the ~57 target and close live/staging evidence; no shared spine/static edit is requested.

## Audit evidence — HJ-26 closeout

- 2026-08-23 — Focused command: `source .venv/bin/activate && cd apps/api && pytest -q tests/unit/test_producers_montgomery.py tests/unit/test_interlock_gate.py tests/unit/test_export_snapshot.py && pytest -q -m interlock`; result: **30 passed**, then **20 passed**. Only existing Starlette/httpx and unknown-`live` mark warnings appeared.
- 2026-08-23 — G1 interlock: green; G2 full unit suite: not rerun in this leaf closeout (parent owns the full-suite gate); G3 geography: Montgomery metro/division containment and submarket membership assertions pass; G4 fixture fidelity: permit and ABS nested-location fixture rows assert IDs and coordinates.
- 2026-08-23 — G5 live parse, G6 backfill parity, G7 freshness, G8 pipeline hygiene, and G9 division resolution: **no live/staging runtime evidence available in this worktree**, so these remain unverified rather than claimed.
- 2026-08-23 — G10 dashboard/map: focused interlock passed; direct checks found Montgomery in `apps/api/src/serving/dashboard.py` and synced `apps/edge/public/index.html`, plus README/research references and both non-empty dashboard screenshots.
- 2026-08-23 — MC311 exclusion: `FeedType.COMPLAINTS_311` is absent from Montgomery's datasets and the registry comment identifies Socrata `xtyh-brr2` as zip/city/district-only with no coordinates; the leaf test explicitly asserts the omission.
- 2026-08-23 — Direct registry count: `len(REGISTRY) == 17`; `sum(len(city.datasets) for city in REGISTRY.values()) == 55`; Montgomery contributes exactly `permits` + `sla`. Parent should reconcile the missing two feed jobs against other city streams before closing A1.
- 2026-08-23 — Graph evidence: project `home-harlan-dev-urban-signal`, generation `2026-08-24T03:21:14Z`, ready with no parse-partial/skipped files. Coverage is `no_recorded_issue` for indexed code/docs; static edge HTML is excluded by design and was read directly.

## Parent interlock patch request

No shared spine/static patch is requested for Montgomery. Parent/integration must reconcile the program-level 17-city/~57-feed count (current executable count is 17/55) and provide live/staging evidence for G5–G9 or record those environmental blockers in the final scorecard.
