# Stream log — us27-sla-flow — 2026-08-24

## Claim

- **Stream id:** `us27-sla-flow`
- **Leaf files I will create/edit:**
  - `apps/api/src/features/pipeline.py`
  - `apps/api/src/consumers/spatial_enrichment_worker.py`
  - `apps/api/src/consumers/feature_aggregation_worker.py`
  - `apps/api/src/schemas/models.py`
  - `apps/api/src/schemas/avro/enriched_h3_feature.avsc`
  - `apps/api/tests/unit/test_features.py`
  - `apps/api/tests/unit/test_schemas.py`
  - `.streams/us27-sla-flow.md`
- **Spine files I expect to need:** `apps/api/src/config.py` (additive
  `sla_flow_ablation_enabled` flag only).

## Intent

Implement US-27 (Signals S1): derive business license **move-in / move-out
flow** counts per hex per window from the already-ingested SLA feeds — zero
new endpoints, no new `FeedType`. First-seen (`effective_date`) vs closure
(`expiration_date`) per license id per hex per 90d window, computed in the
DuckDB feature pipeline and emitted on the enriched H3 record. Per the
survey's standing rule for derived signals, the flow features ship **behind
an ablation flag** and never feed the LIMS score; production behavior with the
flag off is identical to today. Done = derivation + schema surfaces + tests,
interlock gate green, full suite green, Linear US-27 resolved with evidence.

## Decisions

- 2026-08-24 — Closure semantics: move-out = license whose `expiration_date`
  (lifecycle end) falls inside the window. Date-only derivation; snapshot
  `license_status` carries no transition timing, and feeds without a
  lifecycle-end column (e.g. Chicago's date_issued-only feed) contribute 0
  move-outs. `effective_date` future-dated rows (NOLA pattern) fall outside
  the window and are tolerated.
- 2026-08-24 — Window: 90 days for both flows, matching the existing
  `sla_new_filings_90d` naming. `sla_move_ins_90d` is the explicit flow
  counterpart; the legacy `sla_new_filings_90d` (60d window, feeds LIMS) is
  left untouched per the ablation rule.
- 2026-08-24 — Ablation gate = `config.sla_flow_ablation_enabled` (bool,
  default False). Off: flow counts computed as 0 and omitted from the LIMS
  path; the enriched record emits 0 defaults. On: derivation computed, stored
  in `feature_store_h3`, and emitted for ablation evaluation. Either way LIMS
  never reads them — promotion is a later step after lift is shown.
- 2026-08-24 — Producer (`sla_licenses_producer.py`) already parses
  `expiration_date` onto `SLALicenseEvent` and Avro; no producer edit needed.
  The gap was downstream: `raw_sla` dropped the column. Pipeline is global
  per-H3 so the derivation automatically covers every registered metro that
  has an SLA feed.

## Current step

DONE. All edits in place, tests green, US-27 resolved (Done) with evidence
comment. Working tree NOT committed (awaiting instruction).

## Next step

None. If resumed: commit the change set, then evaluate ablation lift by
training with `sla_move_ins_90d` / `sla_move_outs_90d` enabled before any LIMS
promotion.