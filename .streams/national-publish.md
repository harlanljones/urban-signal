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

- 2026-08-28 — Input source: snapshot builder gains a `national_dir` param
  (CLI `--national-dir`) pointing at the national_builder output tree (Parquet
  chunks partitioned by res-3 parent + build_report.json). Absent/missing dir →
  no national block (backward compatible; snapshot-push job passes the dir).
- 2026-08-28 — Boot manifest stays small: manifest `national` block carries a
  per-res summary ({count, chunks, generated_at}); the full per-res detail
  ({byte_size, sha256, parents[]}) lives in its own `national/index` KV key.

## Current step

Reading national_builder output schema, worker gridtiles route, and gate tests
before implementing.

## Next step

Design the chunk row format (compact JSON vs base64-packed — measure, pick,
document), then implement builder → worker → tests → gates.
