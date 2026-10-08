# Stream log — enable-expanded-coverage — 2026-10-07

## Claim

- **Stream id:** `enable-expanded-coverage`
- **Directive:** enable the expanded metro coverage in production and finish the
  coverage Stage A/B reader the plan deferred. User chose: national artifact =
  GitHub Actions long-retention artifact (pilot); dense metro = enable globally now.
- **Leaf files I will create/edit:**
  - `.github/workflows/national-publish.yml` (new — monthly LODES build + artifact)
  - `.github/workflows/batch-push.yml` (dense flag + national download/validate/require)
  - `scripts/validate_national_artifact.py` (new) + `apps/api/tests/unit/test_validate_national_artifact.py` (new)
  - `apps/dashboard/src/index.ts`, `apps/dashboard/src/snapshot.ts` (snapshot_id resolution + release-qualified reads)
  - `apps/dashboard/tests/index.test.ts`, `apps/dashboard/tests/snapshot.test.ts`
  - `apps/api/src/serving/dashboard.py` (client coverage states + legends) + byte-synced `apps/dashboard/public/index.html`
  - `apps/api/tests/unit/*` (interlock/static-source assertions)
  - `.streams/enable-expanded-coverage.md`, `.streams/dispatch-log.md`
- **Spine files I expect to need:** none (all seams are leaves).
- **Open decisions:** none outstanding — artifact store = GH artifact; dense = on.

## Intent

1. (a) Turn on the coverage the specs shipped but never enabled:
   - `--dense-metro` on the daily snapshot (US-408's bounded k_ring=3 + 1.5 km).
   - National LODES context: a monthly build uploads a checksum-addressed artifact;
     the daily snapshot downloads, validates, and runs `--national-dir --require-national`.
2. (c) Finish hex-coverage Stage A/B:
   - Worker reader: `snapshot/current` resolution, `?snapshot_id=` release-pinned reads,
     400 on invalid id, no cross-generation fallback, version-mismatch failure.
   - Client: per-layer coverage state machine, availability gating (no wasted national
     chunk requests), generation guard, retries, and truthful coverage legends.

## Acceptance gates

- `python3 scripts/verify_cicd_preflight.py` green (interlock, dashboard↔product
  cross-ref, facts drift, product lint/build, dashboard export byte-sync, ruff).
- `pytest -m interlock` green from `apps/api`.
- Worker `bun test` + `tsc --noEmit` + wrangler dry-run build green.
- National validation script has unit tests (vintage, sha, nonempty sample, totals, fail-closed).
- Prod smoke after the next scheduled publish: manifest has `snapshot_id` + `coverage`
  block + `national` block; `/api/v1/national` 200; res-9 counts ~4.5× k_ring=1 for nyc.

## Status

- [x] Task A1 — dense flag + workflow (batch-push `--dense-metro`)
- [x] Task A2 — national build workflow + artifact (`national-publish.yml`)
- [x] Task A3 — validate_national_artifact.py + 11 tests + batch-push wiring (fetch/validate/require)
- [x] Task C1 — worker snapshot_id / release-qualified reader + tests
- [x] Task C2 — client coverage states + legends + tests + byte-sync
- [x] Task V — full preflight + evidence

## Task A evidence (2026-10-07)

- `batch-push.yml`: builder now runs `--dense-metro --national-dir build --require-national`;
  new steps fetch + validate the `national-artifact` before the build; summary reports its age.
- `national-publish.yml` (new): monthly (1st, 04:00 UTC) + on-demand + on-merge build of
  LODES res 4/5/6, validated then uploaded as `national-artifact` (90-day retention).
- `scripts/validate_national_artifact.py` (new): independent consumer-side gate (manifest,
  pointer, per-resolution reports, per-chunk sha, aggregate sha, completeness, vintage).
- `apps/api/tests/unit/test_validate_national_artifact.py` (new): 11 tests, all pass;
  ruff clean; `test_workflow_routing.py` 7 tests pass.

## Task C evidence (2026-10-07)

- C1 (worker, `apps/dashboard/src/{index,snapshot}.ts`): `fetchSnapshotPointer`, pointer-resolved
  `getManifest` (`releases/{current}/manifest` with legacy fallback), shared
  `readSnapshotValue` (valid id → release key, missing → 503 + retry-after, never cross-generation;
  invalid → 400), schema-version guard (500), `x-snapshot-id` on `/api/v1/manifest`; wired through
  submarkets/grid/catalysts/gridtiles/national/catalysts-all/predict. 20 new tests.
- C2 (client, `apps/api/src/serving/dashboard.py` + byte-synced `public/index.html`):
  coverage-state machine, availability gating (zero national fetches when unpublished), snapshot
  pinning, generation guard + in-flight dedupe + success-only negative cache, retry/backoff with
  `retry-after` + Retry toast, 5-minute visible-tab manifest refresh, truthful legend + inspector
  disclosure. New `apps/dashboard/tests/coverage-states.test.js` (8 tests).
- Deferred (Task 5 depth, recorded): context-only coarse-scale selector, "nearest supported
  location" inspector fallback, mobile-specific legend persistence, browser acceptance script (Task 7).

## Verification (2026-10-07)

- `verify_cicd_preflight.py` (venv python + venv on PATH): interlock, cross-ref, facts:check,
  product lint, dashboard export, ruff — **all green**.
- Worker: `bun test tests` 144 pass; `tsc --noEmit` clean; wrangler `--dry-run` build clean.
- Node: `grid-zoom.test.js` + `coverage-states.test.js` 22 pass.
- Python: interlock 25 pass; `test_validate_national_artifact.py` + `test_workflow_routing.py`
  + `test_export_snapshot.py` 72 pass.
- Root `bun run build && typecheck && lint` green; `get_dashboard_html() == public/index.html` exact.

## Not done / next

- **Bulk guard raised** 512 MiB → 1 GiB (`snapshot_builder.py`) so the requested dense +
  release-twin config builds. Measured extrapolation from the 2026-10-07 prod snapshot
  (64 MiB logical / 69 MiB bulk, 13,154 keys) is ~566 MiB with both on; the KV bulk API
  caps each *request* at 10k pairs / 100 MB and wrangler segments the file.
- **Release-key retention fixed.** `scripts/prune_snapshot_releases.py` (new) keeps only
  `{current, previous}` generations and bulk-deletes the rest; wired into `batch-push.yml`
  after the KV push (namespace id via `vars.SNAPSHOT_NAMESPACE_ID` fallback). 10 unit tests
  (paginated list, batched delete, dry-run, fail-safe on a missing pointer). Bounds the
  namespace at ~2 generations instead of unbounded growth.
- No commit and no deployment (repo policy: human/CI commits; prod publish is the scheduled job).
- After the next scheduled publish, smoke-check prod: manifest gains `snapshot_id` + `coverage`
  + `national` blocks; `/api/v1/national` 200; nyc res-9 `grid_features` ~4.5× (1846 vs 442);
  the prune step reports `PRUNE_OK` and the `releases/` key count stays at two generations.

## Task P evidence (release retention, 2026-10-07)

- `scripts/prune_snapshot_releases.py`: reads the `snapshot/current` pointer from the built
  `dist/kv-bulk.json`, lists `releases/` keys (cursor-paginated), deletes generations outside
  `{current, previous}` via `POST …/bulk/delete` (≤10k per request), fails safe when the pointer
  is unreadable. `apps/api/tests/unit/test_prune_snapshot_releases.py`: 10 tests, ruff clean.
- `batch-push.yml`: "Prune stale snapshot generations" step after the KV push; prune test added
  to the CI pytest line.


