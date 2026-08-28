# Stream log — national-publish — 2026-08-28

## Claim

- **Stream id:** `national-publish`
- **Linear ticket:** US-383 (Publish national layer chunks + manifest block),
  child of US-381. US-382 (foundation) and US-385 (KV sharding + budgets) are
  Done; this builds directly on both.
- **Leaf files I will create/edit:**
  - `apps/api/src/export/snapshot_builder.py` (national chunk emission + manifest
    `national` block + `national/index` key)
  - `apps/api/tests/unit/test_export_snapshot.py` (national shard tests)
  - `apps/api/tests/unit/test_interlock_gate.py` (TestSnapshotWiring-style
    national coverage)
  - `apps/dashboard/src/snapshot.ts` (national chunk fetch helpers)
  - `apps/dashboard/src/index.ts` (GET /api/v1/national/{res} route)
  - `apps/dashboard/tests/index.test.ts`, `apps/dashboard/tests/snapshot.test.ts`
  - `.streams/national-publish.md` (this file)
- **Spine files I expect to need:** none.

## Intent

Make the national hex datasets servable through the existing Worker + KV
snapshot pipeline: per-res chunks sharded by res-3 parent (≤5 MiB budget),
`national/index` integrity key, manifest `national` summary block, and a
`GET /api/v1/national/{res}[?parents=...]` route mirroring `gridtiles`.

## Decisions

- 2026-08-28 — **Input source:** snapshot builder gains a `national_dir` param
  (CLI `--national-dir`) pointing at the national_builder output tree (Parquet
  chunks partitioned by res-3 parent + build_report.json). Absent/missing dir →
  no national block (backward compatible; snapshot-push job passes the dir).
- 2026-08-28 — **Boot manifest stays small:** manifest `national` block carries a
  per-res summary ({count, chunks, generated_at}); the full per-res detail
  ({byte_size, sha256, parents[], chunks{parent:{bytes,sha256,rows}}}) lives in
  its own `national/index` KV key.
- 2026-08-28 — **Chunk format = compact JSON (measured).** rows-of-arrays with a
  `cols` header (~254 KB per res-6 res-3 chunk, ~6.4K rows @30% non-null) vs
  base64-packed binary (24 B/row fixed layout, ~201 KB = 0.79x). The 21% saving
  does not justify a bespoke binary codec in both runtimes; JSON keeps kvJson
  parsing and client-side rendering trivial. Measured with
  /tmp/opencode/us383_format_measure.py; numbers recorded on the ticket.
- 2026-08-28 — **Sparse publication (honesty rule):** chunks publish only rows
  with ≥1 non-null metric; an absent hex means "no data". An all-null chunk
  publishes no key; it surfaces as `missing[]` on the route. Rolling per-res
  sha256 = hash over sorted `parent chunksha` lines; per-chunk sha256 = hash of
  the exact published bytes.
- 2026-08-28 — **Budget:** NATIONAL_MAX_CHUNK_BYTES = 5 MiB (ticket budget,
  tighter than US-385's 20 MiB KV guard); oversized chunks fail the build with a
  res-2-resharding hint.
- 2026-08-28 — **Route shape:** `GET /api/v1/national` serves the index doc;
  `GET /api/v1/national/{res}?parents=<csv>` merges chunk rows flat
  ({res, count, cols, rows, missing}) with sha-derived ETag + 304, mirroring
  gridtiles. MAX_NATIONAL_PARENTS_PER_REQUEST = 64 (CONUS spans ~40 res-3
  parents; one call must fetch a full resolution's display set). Query logic
  lives in snapshot.ts (fetchNationalIndex / fetchNationalRows) per the US-188
  consolidation direction; index.ts keeps only HTTP envelopes.

## Current step

Implementation complete and verified:
- Builder: `_publish_national_layers` + `national_dir` param + `--national-dir`
  CLI + manifest `national` block + `national/index` key.
- Worker: both routes + OpenAPI + API guide; snapshot.ts helpers.
- Tests: 4 new python unit tests (publish/absent/budget/boot-regression), gate
  class TestNationalWiring (publish + route wiring), 9 new bun tests.

## Verification (2026-08-28)

- Python: interlock 24 passed; full suite **1740 passed** (scoped excl. wave-4
  streams); ruff clean.
- Worker: 75 bun tests pass; `tsc --noEmit` clean; wrangler dry-run build clean.
- **wrangler dev (live):** built a real 458-key snapshot (nyc + national res-6
  fixture), seeded local KV (`wrangler kv bulk put --local`), served on :8799 —
  `/api/v1/national` returned the full index doc (count 3, sha256, parents);
  `/api/v1/national/6?parents=…` returned merged rows with ETag; If-None-Match
  replay → **304**; invalid res → **400**.
- Boot manifest: 19,030 B → 19,280 B (**+1.31%**, acceptance <10% ✓).

## Next step

Comment + resolve US-383. Then US-384 (deck.gl national display layer) is the
lowest-numbered open ticket.
