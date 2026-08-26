# Stream log — signal-overture — 2026-08-26

## Claim

- **Stream id:** `signal-overture`
- **Leaf files I will create/edit:** `docs/research/overture-maps-evaluation.md`
- **Spine files I expect to need:** none (Tier-A validation stream; read-only research per
  `docs/agents/parallel-streams.md` and the dispatch log — US-169 is in the no-spine tier)

## Intent

Evaluate Overture Maps (the Linux Foundation open map dataset) as a place-change
spatial signal for Urban Signal: its building-footprint and place/POI features,
the native `added`/`removed`/`data_changed` changelog, source/API access, geographic
coverage, monthly update cadence, and mapping to the repo's metro bbox → H3 7–9 units.
Deliver a single research leaf with evidence, proposed validation, risks
(coverage gaps, freshness, retention, licensing), and an adopt/reject/defer verdict.
No code is warranted: registration would require a new (non-event) signal family and
producer archetype — a spine/interlock change — and the wave convention for validation
leaves (us101/us102/us122) is doc-only.

## Decisions

- 2026-08-26 — **VALIDATION VERDICT: DEFER.** Wrote `docs/research/overture-maps-evaluation.md`.
  Overture is the strongest candidate in the validation wave: it ships a **native**
  `added`/`removed`/`data_changed` changelog keyed on stable GERS IDs (unlike LODES,
  which had no change layer), global coverage, monthly cadence, keyless S3/DuckDB/CLI
  access, and reuses the repo's existing H3 indexer + bbox gate for metro extraction.
  It measures a genuinely independent physical-building-stock + commercial-presence
  surface no event feed provides, and could cross-validate permit-derived construction
  velocity. But it is **not an event stream** (no watermark, GeoParquet snapshot +
  changelog) → a feed registration needs a new signal family + producer archetype =
  a **spine/interlock change**, out of scope for a leaf. Plus: monthly + imagery-derived
  lag (trailing, not leading), 60-day public retention (must self-archive history),
  GERS-ID churn inflating change counts, and **buildings are ODbL** (share-alike legal
  gate). No code added — Tier-A doc-only convention; a premature module would be dead,
  unconsumed code (all consumers are spine feeds). Parent: US-169.

## Current step

Phase 2 (Build) complete: `docs/research/overture-maps-evaluation.md` written; stream
log updated. Awaiting the human/CI to run the gated `git commit` (repo blocks the agent
from committing) and then run `pytest -m interlock` + full suite at interlock time.

## Next step

No spine work is required or permitted from this leaf. If promoted later, pilot
New Orleans + Norfolk as a month-over-month building/place change index at H3 7–9,
gated on a new signal family (spine), legal ODbL sign-off, and self-archived history.
