# Stream log — baltimore-runtime-evidence — 2026-08-23

## Claim

- **Stream id:** `baltimore-runtime-evidence`
- **Leaf files I will create/edit:** `.streams/baltimore-runtime-evidence.md` only.
- **Spine files I will not edit:** registry, dashboard, producer, config, static-copy, and test source files.

## Intent

Run available read-only Baltimore feed probes with the repository `.venv`, then document G5–G9 evidence or precise external blockers. No live evidence will be claimed unless the command actually reaches the source or staging system.

## Decisions

- 2026-08-23 — Existing Baltimore implementation and prior closeout trails are preserved; this stream owns runtime evidence only.
- 2026-08-23 — `.venv/bin/python scripts/feed_staleness_probe.py --city baltimore --dry-run` attempted permits, 311, and SLA ArcGIS metadata/records. All three failed after four retries with `[Errno -3] Temporary failure in name resolution`; no source rows or freshness values were obtained.
- 2026-08-23 — No deterministic local oracle gap was found; no tests were added.

## Current step

Complete; runtime probe and focused local verification are recorded.

## Next step

Parent/integrator must rerun the live probe from a network-enabled environment and supply staging/database evidence before closing G5–G9.

## G5–G9 runtime evidence

- **G5 — blocked externally:** The available newest-record probe reached no Baltimore ArcGIS endpoint because DNS resolution failed for all three hosts. Therefore no newest-500 parse-rate percentage is claimed.
- **G6 — blocked externally:** No source `$select=count(*)` versus ingested-count/backfill endpoint or staging database credentials are available in this worktree; no parity percentage is claimed.
- **G7 — blocked externally:** No staging ingestion metrics or 24-hour soak receiver/database is available; the local source probe could not obtain timestamps because of DNS failure.
- **G8 — blocked externally:** No Kafka/PostGIS DLQ, duplicate, or null-H3 counters are available locally; no hygiene rates are claimed.
- **G9 — blocked externally:** No staging/PostGIS division-resolution group-by audit is available. Local geometry tests can verify declared containment only, not runtime row resolution.

## Local verification

- `.venv/bin/pytest -q apps/api/tests/unit/test_producers_baltimore.py apps/api/tests/unit/test_interlock_gate.py`: **25 passed**.
- `.venv/bin/python -m compileall -q apps/api/src/spatial/cities/baltimore.py scripts/feed_staleness_probe.py`: **passed**.
- `git diff --check`: **passed**.
- No registry/dashboard/producer/config/static-copy files were changed by this stream.
