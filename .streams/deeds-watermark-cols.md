# Stream log — deeds-watermark-cols — 2026-08-24

## Claim

- **Stream id:** `deeds-watermark-cols`
- **Leaf files I will create/edit:** `apps/api/tests/unit/test_producers_philadelphia.py` (one pinned watermark assertion)
- **Spine files I expect to need:** `apps/api/src/spatial/city_registry.py` (SF deeds `watermark_col`, Philly deeds `watermark_col` + `extra.order_by`)

## Intent

Apply the two verified watermark-column corrections from
`docs/research/deeds-watermark-audit.md`: san_francisco deeds
`closed_roll_year` → `data_loaded_at`, philadelphia deeds
`document_date` → `recording_date` (watermark_col and carto keyset
`order_by` together). Done = edits applied, `pytest -m interlock` green,
SF/Philly producer tests + probe tests green, full unit suite green.

## Decisions

- 2026-08-24 — Scheduler consumes `watermark_col` generically
  (scheduler.py:174,191,297); deeds producer passes only
  `extra["order_by"|"id_col"|"select"]` to the carto client
  (deeds_acris_producer.py:319), so no producer-code change is needed —
  registry values only.
- 2026-08-24 — Seattle deeds replacement is a separate research stream
  (`deeds-seattle-replacement`); registering a new source stays out of this
  hold.
- 2026-08-24 — Pre-existing reds confirmed on pristine HEAD (d6eabf7) via
  throwaway worktree, not caused by this hold:
  `test_business_licenses_sentinel_exclusion_is_client_side`
  (CartoClient._build_query gained a `direction` arg the test never got) and
  `test_serving.py::test_unknown_city_rejection_400`. Ruff debt in
  city_registry.py imports/annotations is likewise pre-existing (31 on HEAD).

## Current step

Hold closed — all gates run.

## Next step

Record outcome in .streams/dispatch-log.md (orchestrator).
