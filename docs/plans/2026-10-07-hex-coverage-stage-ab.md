# Implementation plan — Hex coverage Stages A+B

Source spec: `~/Downloads/2026-10-07-hex-coverage-design.md` (2026-10-07, proposed).
Recon facts: `.streams/recon-coverage-spec.md` (HEAD a676eb4, branch main).
Scope: Stage A (client coverage states, national availability gating, generation-safe request caching, truthful legends) + Stage B plumbing (generation-pinned publication, verified cached national context consumed by daily snapshots). Explicitly out of scope: Stage C density pilot, Stage D regional context, full-metro fine-grid expansion, MVT/R2 transport migration.

## Ground truth (from recon)

- Manifest is built by `apps/api/src/export/snapshot_builder.py:781-811`, published to Workers KV key `manifest` (single `SNAPSHOT` binding, `apps/dashboard/wrangler.jsonc`); served verbatim with ETag/304 at `apps/dashboard/src/index.ts:1559-1572`. No R2 binding exists. No `snapshot_id`, no `coverage` fields anywhere.
- `GET /api/v1/national` + `/{res}?parents=` exist in the worker (index.ts:1637-1668, snapshot.ts:208-262, max 64 parents, res 4/5/6) and are tested; production 404s only because `.github/workflows/batch-push.yml:119-122` never passes `--national-dir`, so `national/*` keys are never published. `national_builder.py` has checksums, per-res reports, aggregate manifest, and a fail-closed `current.json` pointer — all local-only, uploaded by no workflow.
- Client national path (`dashboard.py:1932-1991`) has none of the metro loader's guards: no concurrency cap (one `Promise.all` over all batches of 24), no generation guard, no retry, no negative caching, no manifest-derived availability gating (gated only on its own cache Map).
- Manifest fetch is one-shot on load (`dashboard.py:2503-2528`, wired at 2574). No 5-min refresh, no version check, no snapshot_id. Client has no timeouts/AbortController anywhere.
- Metro path (dashboard.py:2975-3104) is the reference: debounce, manifest tile_index whitelist, concurrency-2 pool, generation guard `tileLoadGeneration`, in-flight dedupe, success-only negative marking.
- CLI flags today: `--out --cities --skip-legacy-cells --national-dir --require-national --context-dir --dense-metro`. `--metrics-out` does NOT exist (spec §6 names it; adding it is in scope, spec text otherwise).
- All spec seams are leaves (spine-manifest.txt covers only registry/producer files). Interlock tests `TestNationalWiring`/`TestDashboardWiring` assert on dashboard.py/index.ts/snapshot.ts content and byte-synced `apps/dashboard/public/index.html` — regenerate via `scripts/export_dashboard.py` after any dashboard.py edit.
- No R2/artifact store configured. Spec §6: "A durable artifact store must be configured before annual reuse" — Stage B here therefore implements release-qualified KV keys + `snapshot/current` pointer + `snapshot_id` query param (KV-compatible), and defers the R2/dedicated-bucket move to a separate infra change, exactly as the spec's "initial client improvement" carve-out allows.

## Design decisions

1. **snapshot_id format**: `r-YYYYMMDD-<sha256-8 of manifest content>` — bounded, path-safe, opaque; validated by API adapters (`^[A-Za-z0-9._-]{1,64}$`, reject anything else).
2. **Release-qualified KV keys**: writer emits `releases/{snapshot_id}/{logical_key}` for every key it already publishes (data is content-duplicated, not moved — legacy keys keep being written during migration so old readers never break). New reader routes: `GET /api/v1/manifest` resolves `snapshot/current` (KV key holding `{current, previous}`) and returns the release-qualified manifest + `snapshot_id` metadata header; all snapshot data routes accept optional `?snapshot_id=`; pinned clients read `releases/{id}/...`.
3. **Availability gating client-side**: manifest gains `coverage.national.status` (`unavailable|available|stale`) and `coverage.schema_version: 1`. Client schedules zero national requests unless `available|stale`. When the manifest block is absent (legacy), treat as `unavailable` — this single change stops the observed 24-26 empty chunk requests.
4. **No new datasets**: national stays unpublished until Stage B's artifact store workflow is wired; Stage A ships honest `unavailable` states + legends against today's production.

## Tasks

### Task 1 — Manifest coverage block + snapshot_id (API, leaf)
TDD. Extend `build_snapshot`:
- Add `snapshot_id` (per decision 1) to the manifest root; add `coverage` block: `coverage.schema_version=1`, `coverage.national.status` (derived: `available` when national block published + nonempty chunks verified, else `unavailable`), `coverage.national.index_key` when available, `coverage.national.resolutions` mirror of the national block, `coverage.metro.mode` (`sparse_registry`, constant for now), `coverage.study_areas` omitted initially.
- Add `--metrics-out <file>` flag writing a small JSON build report (build time, source time when national present, counts) — spec §6 names this; keep it additive.
- New unit tests in `apps/api/tests/unit/test_export_snapshot.py`: snapshot_id format/stability/determinism, coverage block presence, status derivation both ways, require-national interaction.
- Keep all existing manifest fields byte-identical in shape (additive only). Verify: api unit tests green.

### Task 2 — Release-qualified writer + snapshot/current pointer (API, leaf)
TDD. In `snapshot_builder.py`:
- Write every artifact additionally under `releases/{snapshot_id}/{logical_key}`; write `snapshot/current` KV key `{current: <id>, previous: <prev-id or null>, promoted_at}`. Fail-closed: pointer written only after all release-qualified artifacts verified present + hash-checked (reuse existing integrity checks; smoke query = national index + one known-nonempty chunk when national declared).
- Previous generation retention: read existing `snapshot/current` before overwrite; roll current→previous. Never delete old artifacts in this task.
- Optional `--previous-manifest <path|url>` not needed initially — read previous pointer from the KV bulk being replaced if present, else null previous.
- Tests: release keys present for all logical keys, pointer format, rollback simulation (rebuild → pointer advances; re-run with older manifest → still coherent), oversize/integrity rejection keeps prior pointer.

### Task 3 — Reader: snapshot_id query param + release-qualified serving (worker TS, leaf)
TDD in `apps/dashboard/tests/`:
- `snapshot/current` resolution in worker (`fetchSnapshotPointer`, KV, cached 60s like manifest); `GET /api/v1/manifest` returns release-qualified manifest when pointer exists, legacy `manifest` key otherwise (explicit legacy path).
- All snapshot data routes (`/api/v1/*` reading `grid/`, `gridtiles/`, `cells/`, `national/`, `catalysts/`) accept `?snapshot_id=` → read `releases/{id}/{key}`; reject invalid id (400); 503 + bounded retry hint when release key temporarily unavailable; NEVER fall back to another generation.
- Payload/manifest version mismatch: if manifest declares coverage.schema_version the worker doesn't implement, fail the read (500-style integrity failure), don't serve mismatched data.
- Legacy clients untouched: routes keep paths, defaults resolve current pointer per request.
- Verify: dashboard `bun test tests`, `bun run typecheck`.

### Task 4 — Client coverage states machine (dashboard inline JS, leaf)
TDD-equivalent (static-source assertions + new worker tests; browser verification is the acceptance step). In `dashboard.py` inline JS + `index.ts`/`snapshot.ts` TS types:
- Per-layer state machine: `loading|ready|empty|unavailable|stale|failed` (+ `hidden_by_filter` for displayed metric), inspectable in desktop and mobile UI.
- Behavior 1: resolve manifest before layer reads; zero national chunk requests when no declared availability; show "National context not published."
- Behavior 4: dedupe in-flight by snapshot_id+resolution+parent; negatively cache successful empty chunks per generation.
- Behavior 5: retries at 500/1500/4000 ms (≤3), then accessible Retry action; honor Retry-After.
- Behavior 6: generation guard for national path (mirror `tileLoadGeneration`); below/above-floor cancels queued work.
- Behavior 7: manifest refresh on explicit refresh or 5-min visible-tab interval; snapshot_id change invalidates generation-local caches, restarts reads, keeps supported outgoing geometry until replacement ready.
- Behavior 8: index/payload version mismatch fails the read.
- Metro concurrency/cancellation untouched.

### Task 5 — Truthful legends + coverage UI (dashboard inline JS, leaf)
- Compact coverage/source strip beside the legend (kind, source, reference year, snapshot time) — only when context visible; separate context legend naming the actual indicator.
- "Context only — no LIMS output at this scale" label when selected metric has no layer at coarse view; explicit context indicator choice; neutral coverage explanation over basemap when context unavailable.
- Inspector/compare cards disclose kind, source year, snapshot time, support resolution, units, transformation; unsupported selections show coordinates + availability reason + nearest supported location, never a synthesized score. Coarse context stays context on zoom-in; compare never ranks jobs percentile vs forecast return.
- Mobile: coverage kind + source year in persistent compact legend + top of inspector sheet; use existing Sources & coverage expansion.
- Not hover- or color-only.

### Task 6 — Wire `--require-national` + verified national consumption path (API + workflow, leaf)
Stage B enablement, WITHOUT enabling daily national publish yet (artifact store prerequisite unresolved):
- batch-push.yml gains explicit optional env-gated inputs (`--national-dir` from a verified artifact source, `--require-national`) — wired but default-off; documented as flip-ready.
- National artifact reuse: workflow accepts a verified national artifact (checksum-addressed) and validates per spec §6 before invoking snapshot_builder (vintage policy, hashes, nonempty sample chunks, aggregate totals). Local script `scripts/validate_national_artifact.py` implementing those checks, unit-tested.
- `--metrics-out` plumbed into the workflow job summary.
- No raw LODES download in the daily path.

### Task 7 — Regression fixtures + browser acceptance script
- Six-metro viewport pan/zoom scripted browser verification (Playwright or equivalent) exercising: unavailable-national states, no chunk requests, legends, inspector disclosure, mobile 390×844.
- Update interlock-adjacent tests: `TestNationalWiring` extended for coverage block + pointer + snapshot_id param; `test_export_snapshot.py` for writer/reader; worker tests for Task 3 routes.
- Full `python3 scripts/verify_cicd_preflight.py` green (mandatory).

## Dependency order

1 → 2 → 3 → 4 → 5 → 6 → 7. Tasks 4 and 5 both touch dashboard.py inline JS — serialize them (no parallel implementers on that file). Tasks 1, 2 touch snapshot_builder.py — serialize. Parallelism is therefore limited: tasks run sequentially except Task 6 (workflow + new script) can run alongside Task 4 after Task 3 lands. Keep it simple: run the chain sequentially; the SDD review loop is the quality mechanism.

## Per-task verification

Every implementer: TDD, run targeted suites, then `pytest -q -m interlock` from apps/api when dashboard.py/index.ts/snapshot.ts touched, plus `python3 scripts/export_dashboard.py` after dashboard.py edits (byte-sync), plus `bun run build && typecheck && lint` at dashboard-touching milestones. Controller runs full preflight before final commit.

## Open decisions (do not silently default)

- Snapshot_id composition (decision 1 above) — review in Task 1 spec review.
- Worker `503` vs `404` for temporarily-unavailable release keys — spec §7 says 503 + bounded retry; confirm against KV behavior in Task 3.
- Task 6 artifact source: which store carries the verified national artifact until the dedicated R2 bucket exists (approved long-retention GH artifact can serve the pilot per spec §6) — decide with Harlan at Task 6, not before.
