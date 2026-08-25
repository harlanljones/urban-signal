# Stream log — us121-architecture-alerts — 2026-08-24

## Claim

- **Stream id:** us121-architecture-alerts
- **Leaf files I will create/edit:** `apps/product/pages/architecture.html`
  (page copy), `apps/product/pages/architecture.json` (meta description —
  only if it needs a matching tweak), `.streams/us121-architecture-alerts.md`
  (this log)
- **Spine files I expect to need:** none — all target files absent from
  `docs/agents/spine-manifest.txt`; shared files (CHANGELOG, llms.txt,
  llms-full.txt) are PROPOSED SHARED EDITS only, not written by me

## Intent

Extend the `/architecture/` spine narrative to describe the realtime
aggregation loop and catalyst alert dispatch per ADR 0008:
feature aggregation worker → catalyst alerts at the public threshold
(LIMS ≥ 85.0) on `alerts.catalyst` → alert dispatcher worker → webhooks.
Honest-about-illustrative: describe the mechanism + cite evidence paths, do
not present alerts as a live customer-facing feed. No commits (local policy).

## Decisions

- 2026-08-24 — F1: `feature_aggregation_worker.py` consumes the four
  feature-relevant raw topics (permits/311/sla/deeds) under `cg_inference`;
  skips `source_mode=="backfill"` records and records without `h3_res9`;
  inserts into the pipeline raw table; per-cell cooldown = 300 s
  (`aggregation_cell_cooldown_seconds`); a record on a hot cell is absorbed
  (no recompute, no alert re-check); on compute it emits an enriched H3
  feature AND a `CatalystAlert` to `alerts.catalyst` when
  `lims_score >= settings.lims_threshold` (85.0). Failures → shared DLQ.
- 2026-08-24 — F2: `alert_dispatcher_worker.py` consumes `alerts.catalyst`
  on `cg_alerts`, constructs `CatalystAlert`, dispatches via
  `WebhookDispatcher.dispatch_alert` (calibration gate + daily budget +
  webhook fan-out; skips are not failures), uses restart-safe
  `JsonAlertStateStore`, in-memory `CityAlertBudget`; real failures → DLQ.
- 2026-08-24 — F3: `catalyst_alert.avsc` carries `city_id` (default `"nyc"`),
  alert fields (alert_id, h3_index, lims_score, predicted deltas,
  macro prob, centroid, timestamp). Not needed in page copy verbatim.
- 2026-08-24 — F4: architecture.html "Feature aggregation" node currently
  describes ingredients + "Catalyst alerts at LIMS ≥ 85.0" but no loop; links
  `lims_calculator.py` (score source). No ADR citations on this page. ADR
  citation pattern established on evidence.html: inline repo link to
  `docs/adr/<n>.md`, e.g. "The decision is recorded in ADR 0005."
- 2026-08-24 — F5: interactive arch map (line 7, `data-arch` buttons +
  `main.js` archDetails) is a separate visual subset; NOT touching it — the
  spine narrative is the section's detail surface.
- 2026-08-24 — EDIT: Feature aggregation node rewritten to describe the loop,
  stage-source link swapped from `lims_calculator.py` to
  `feature_aggregation_worker.py`; new "Alert dispatch" spine node added
  after it linking `alert_dispatcher_worker.py` with inline ADR 0008
  citation (matches evidence.html pattern); Kafka backbone consumers bullet
  extended with "alert dispatch"; architecture.json description gains
  "alert dispatch".
- 2026-08-24 — PROPOSED SHARED EDITS written to this log (CHANGELOG Unreleased
  entry + llms.txt / llms-full.txt architecture lines). Not applied.

## PROPOSED SHARED EDITS

Not applied by me (orchestrator applies). Exact text below.

### apps/product/CHANGELOG.md — Unreleased → Added (new bullet)

```
- `/architecture/` now describes the realtime aggregation loop and catalyst
  alert dispatch: the feature aggregation worker recomputes touched H3 cells
  on a five-minute cooldown and emits catalyst alerts at LIMS ≥ 85.0 to
  `alerts.catalyst`, which the alert dispatcher consumer fans out to webhooks
  behind a per-city calibration gate and daily budget (ADR 0008).
```

### apps/product/public/llms.txt — line 12 (Architecture bullet)

Current:
`- [Architecture](/architecture/): source producers, city registry, Kafka consumers, H3 enrichment, feature aggregation, PostGIS storage, ONNX horizons, edge snapshots.`

Proposed:
`- [Architecture](/architecture/): source producers, city registry, Kafka consumers, H3 enrichment, feature aggregation, catalyst alert dispatch, PostGIS storage, ONNX horizons, edge snapshots.`

### apps/product/public/llms-full.txt — line 32 (/architecture/ section)

Current:
`The system architecture map from source producers through city registry, Kafka consumers, H3 enrichment, feature aggregation, PostGIS storage, ONNX horizons, and edge snapshots.`

Proposed:
`The system architecture map from source producers through city registry, Kafka consumers, H3 enrichment, feature aggregation, catalyst alert dispatch, PostGIS storage, ONNX horizons, and edge snapshots.`

## Current step

DONE — leaf edits applied, `bun run typecheck` passed (exit 0), no build/lint
run (writes dist/). PROPOSED SHARED EDITS above, not applied. No commits
(local policy).

## Next step

Step 4 verify, then final report with PROPOSED SHARED EDITS block.
