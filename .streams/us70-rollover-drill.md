# Stream log — us70-rollover-drill — 2026-08-24

## Claim

- **Stream id:** `us70-rollover-drill`
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/rollover.py` (new)
  - `scripts/rollover_drill.py` (new)
  - `apps/api/tests/unit/test_rollover_drill.py` (new)
  - `apps/api/tests/unit/test_feed_staleness_probe.py`
  - `.streams/us70-rollover-drill.md`
- **Spine files I expect to need:** `apps/api/src/producers/scheduler.py`
  (year-slice rollover detection + watermark reset + rollover metric event).

## Intent

US-70 (roadmap §8.2, risk R3): annual New Year rollover drill for every
year-sliced feed (DC permits/311, Boston 311, Baltimore 311). Deliver the
drill the ticket demands — a frozen-clock test advancing to Jan 2 that proves
the scheduler resolves the next-year layer/resource, resets the watermark
baseline, and emits a `rollover` metric event — plus the scheduler machinery
that makes it real at runtime (endpoint re-resolved per poll, switch detected,
baseline reset). A deliberately-unmapped year fails loudly. The staleness
monitor must not page on the freshness re-baseline at rollover.

Done = scheduler rollover handling, drill module + script, tests for green /
loud-fail / no-false-page, interlock gate + full suite green, US-70 resolved.

## Decisions

- 2026-08-24 — Scheduler currently resolves endpoints ONCE at construction;
  a scheduler running across New Year keeps polling last year's layer. Add a
  per-poll rollover check that re-resolves year-sliced endpoints against the
  calendar and, on a switch: repoints `job_metadata["endpoint"]`, resets the
  job's `high_watermark` to None (new layer re-baselines), increments a
  `rollovers` counter + `last_rollover` timestamp, and emits a Prometheus
  `urban_signal_feed_rollover_total` counter. Clock is injectable
  (`today_provider`) so the drill can freeze it at Jan 2.
- 2026-08-24 — Dedup cache is NOT cleared on rollover: ids are keyed
  `job:value` and a new year's layer has a new id space (SR-2027... vs
  SR-2026...), so no collisions; a full clear would only risk double-publishing
  other jobs' last window.
- 2026-08-24 — Loud failure semantics: `resolve_endpoint` falls back to the
  newest past year by design (graceful when the ETL publishes late), so the
  DRILL must detect the missing-mapping case itself: `drill_rollover(target)`
  requires every year-sliced feed to map `target.year` and raises
  `RolloverDrillError` otherwise. This is the "deliberately-unmapped year fails
  it loudly" acceptance.
- 2026-08-24 — Staleness monitor: `feed_staleness_probe` already resolves the
  endpoint per-date (`resolve_endpoint(spec, today=now.date())`), so at New
  Year it re-baselines against the new layer; a fresh new-year source (recent
  `lastEditDate`/rows) reports `stale=False`. The probe needs no code change —
  the guard is a test proving a post-rollover fresh layer does not page.
- 2026-08-24 — `rollover.py` + `scripts/rollover_drill.py` are new leaf
  modules (not in the spine manifest). `scheduler.py` is the only spine edit.

## Current step

DONE. Scheduler rollover machinery, drill module + CLI script, and tests all
in place; interlock gate green; full suite green (0 failures). Working tree
NOT committed (awaiting instruction).

## Next step

Linear resolution on US-70. If resumed: commit, then in December run
`python scripts/rollover_drill.py --frozen-date <next>-01-02` and append the
new year's mappings (they fail loudly until added).