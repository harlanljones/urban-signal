# Stream log — d7-text-watermark — 2026-08-24

## Claim

- **Stream id:** `d7-text-watermark` (Linear HJ-114, claimed via --assignee self)
- **Leaf files I will create/edit:** `apps/api/src/producers/watermarks.py`,
  `apps/api/tests/unit/test_watermarks.py`,
  `scripts/feed_staleness_probe.py`,
  `apps/api/tests/unit/test_feed_staleness_probe.py`,
  `docs/adr/0005-typed-text-watermarks.md`
- **Spine files I expect to need:** `apps/api/src/producers/scheduler.py`
  (declarations into job_metadata, incremental WHERE guard, typed
  high-watermark branch)

## Intent

Land D7 as specified on HJ-114 / wave-2 §3 D7: declared
`extra={"watermark_type":"text","watermark_format":...,"watermark_exclude":[...]}`
resolved into a server-side NOT-IN guard plus typed client-side comparison,
so text columns like PG County's `ZZZZZZZZ` sentinel and NYC's mixed formats
cannot poison ordering or incremental filters. Done = acceptance list green
(PG live newest-row check, NYC regression test, interlock gate, ADR 0005).

## Decisions

- 2026-08-24 — Probe already survives sentinels (parse failures are dropped
  in watermarks.parse_watermark), so the probe change is optimization +
  consistency: pass the declared exclusion as where_clause so the bounded
  1000-row sample isn't wasted on garbage rows.
- 2026-08-24 — Scheduler stores RAW string high-watermark for text-typed
  columns (uniform declared format ⇒ lexical `>` stays sound server-side);
  non-text feeds keep the existing event-attr ISO path untouched.
- 2026-08-24 — No registry data changes in this delta: PG County registers
  in HJ-125 (blocked by this ticket); NYC needs no declaration (its problem
  is mixed formats, solved client-side by multi-format parse, no sentinel).

## Current step

Phase 2: leaf helpers + tests.

## Next step

Spine hold on scheduler.py, then gates, ADR 0005, live PG evidence, Linear
resolution.

## Outcome (2026-08-24)

Completed. Leaf helpers landed in watermarks.py; spine hold on scheduler.py
(job_metadata declarations, NOT-IN where guard, pre-parse typed high-watermark
tracking with legacy event-attr path gated off for text feeds). Gates:
interlock 20 passed; full suite 573 passed / 3 skipped / 0 failed; ruff clean
on all touched files (scheduler's 4 BLE001 findings pre-date this edit,
verified against HEAD).

Live acceptance evidence: PG County `qzrv-2tnv` plain DESC ordering surfaces
null/missing transfer_date rows first; guarded query excludes sentinels and
top-of-order returns real YYYYMMDD dates (20260529…). **Second sentinel
spelling discovered live: `XXXXXXXX` alongside `ZZZZZZZZ`** — HJ-125 must
declare both in watermark_exclude. Typed newest over the guarded sample =
2026-05-29.

ADR 0005 records the decision. HJ-114 resolved in Linear with evidence.
