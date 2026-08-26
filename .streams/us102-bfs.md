# Stream log — us102-bfs — 2026-08-25

## Claim

- **Stream id:** `us102-bfs`
- **Leaf files I will create/edit:** `docs/research/census-bfs-validation.md`
- **Spine files I expect to need:** none (read-only research stream)

## Intent

Validate Census Business Formation Statistics (BFS) as a metro/county contextual
signal: EIN applications, projected/actual employer formations, time-to-formation.
Verdict must be one of: register/reject/defer, backed by evidence on cadence, release
lag, revisions, sector detail, county granularity, and incremental value versus the
derived move-in/move-out business-license flow already in the pipeline.

## Decisions

- 2026-08-25 — **VALIDATION VERDICT: DEFER.** Wrote `docs/research/census-bfs-validation.md`.
  County-level BFS is annual only (~6-month lag), DP-noise (budget .5/.75) with a
  DAO 216-26 regime switch incoming, and no metro/county sector detail; the timely
  monthly series is national/regional/state only (too coarse for a metro). The Jan-2026
  HBA/CBA internet-sales exclusion restates the ENTIRE series (not a point fix) and
  the 2022-NAICS restatement adds a second vintage boundary — both need a version-aware
  transform. Doesn't improve H3 7-9 / division / submarket calibration; adds only a
  distinct (new-formation) numerator vs. the finer, timelier `sla_move_ins_90d` /
  `sla_move_outs_90d` flow. Revisit on a sub-state sub-annual product, a DAO-stable
  county regime, or a concrete explanatory-reporting (citation/context, not scoring) need.
  No code or config touched. Parent: US-102.

## Current step

Dispatched 2026-08-25 as part of the 5-stream validation wave.

## Next step

Produce `docs/research/census-bfs-validation.md` with the validation verdict.
