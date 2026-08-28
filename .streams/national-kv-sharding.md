# Stream log — national-kv-sharding — 2026-08-28

## Claim

- **Stream id:** `national-kv-sharding`
- **Linear ticket:** US-385 (KV sharding + CI gates for national scale), child of
  US-381. Runs in parallel with US-383/US-384 (no data dependency).
- **Leaf files I will create/edit:**
  - `apps/api/src/export/snapshot_builder.py` (per-cell KV shards, size budgets,
    thread-pooled cells inference)
  - `apps/api/tests/unit/test_cells_sharding.py` (new)
  - `apps/dashboard/src/snapshot.ts` (per-cell lookup + legacy fallback)
  - `apps/dashboard/tests/index.test.ts` (KV-mock per-cell branch, additive)
  - `apps/dashboard/tests/snapshot.test.ts` (new lookup tests)
  - `.streams/national-kv-sharding.md` (this file)
- **Spine files I expect to need:** none.

## Intent

Remove the single-global-`cells/index` scaling wall (25 MiB KV cap, full-object
parse per predict request) and bound artifact sizes so nationwide publishes fail
loudly instead of silently corrupting. `cells/index` becomes per-cell keys
(`cells/{h3}`) + `cells/index_meta`; worker prefers per-cell and falls back to
legacy during the compat window.

## Decisions

- 2026-08-28 — **Per-cell keys, not res-5 shards.** `POST /api/v1/predict` is a
  point lookup; per-cell keys give 1 KV read + no JSON mega-parse, need no h3-js
  dependency in the worker (res-5 sharding would require cellToParent
  client-side), and scale to any national cell count. `cells/index_meta` carries
  {sharded, total, generated_at} for observability.
- 2026-08-28 — **Gate test keeps its embedded stub build (measured 1.24s).** The
  ticket's "15-min CI wall" applies to real engine builds in the snapshot-push
  job, not the gate (stub engine, no ONNX). Splitting it out would weaken a live
  invariant for no measured gain. Decision recorded on the ticket.
- 2026-08-28 — **Manifest slimming deferred** (tri-surface: dashboard.py inline JS
  + index.ts + builder in one hold). Commented on the ticket for a focused stream.
- 2026-08-28 — Size budgets enforced in the builder (per-KV-value ≤ 20 MiB vs the
  25 MiB KV cap; manifest ≤ 10 MiB; kv-bulk ≤ 512 MiB) so oversized publishes fail
  the build before `wrangler kv bulk put`.

## Current step

Builder per-cell sharding + budgets + thread-pooled cells inference.

## Next step

Worker lookup path + bun tests; Python tests; interlock + full-suite re-run;
comment + resolve ticket.

## Done — 2026-08-28

- **Builder** (`apps/api/src/export/snapshot_builder.py`):
  - Cells loop rewritten two-phase: collect feature dicts, then
    `ThreadPoolExecutor.map` (CELL_INFERENCE_WORKERS consumers) over the
    inference engine, registering per-cell `cells/{h3}` + `cells/index_meta` and
    optionally the legacy `cells/index` (default on; `--skip-legacy-cells` off).
  - `build_snapshot(..., include_legacy_cells=True)`: when False, legacy
    `cells/index` is omitted (per-cell shards + meta only).
  - Manifest now carries `cells_sharded: true` and `cells` = shard count;
    registers `cells/index_meta` key.
  - Size budgets enforced in `register()` (per-value `< MAX_KV_VALUE_BYTES`) and
    in `build_snapshot` after writing bulk (`> MAX_BULK_BYTES`) and manifest
    (`> MAX_MANIFEST_BYTES`) — each raises ValueError with a descriptive message.
  - CLI: added `--skip-legacy-cells`. ruff + format clean.
- **Python tests** (`apps/api/tests/unit/test_export_snapshot.py` — the sharding
  tests live with the existing snapshot tests rather than a new file): manifest
  shape asserts per-cell keys + `cells_sharded`; `test_per_cell_shards_match_legacy_cells`
  cross-checks every shard against legacy `cells.json` and verifies meta;
  `test_skip_legacy_cells_omits_single_key`; subset export key-set updated.
- **Worker** (`apps/dashboard/src/snapshot.ts`): `lookupPrediction` reads
  `cells/{h3}` first, falls back to legacy `cells/index` when the shard is absent;
  missing both → same error as before. No `cells/index` presence difference in
  error string is asserted anywhere.
- **Worker tests**: KV mock in `index.test.ts` gained a per-cell branch for a
  cell not in legacy; `snapshot.test.ts` gained shard-precedence, legacy-fallback,
  and strip-shap-on-fallback tests. 66 pass, `tsc --noEmit` clean, wrangler
  `--dry-run` build clean.
- **Verification**: `pytest -m interlock` green (gate + snapshot + dashboard
  wiring); full suite **1596 passed** in my scope (wave-4 omaha/henderson/
  virginia_beach/toledo streams excluded — those are another agent's uncommitted
  in-flight work, unrelated to US-385).
- **Deferred** (recorded on ticket): manifest slimming (needs a focused
  tri-surface stream).
