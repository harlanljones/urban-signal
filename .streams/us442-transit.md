# Stream log — us442-transit — 2026-09-13

## Claim

- **Stream id:** `us442-transit`
- **Leaf files I will create/edit:**
  - `apps/api/src/producers/bay_area_511_client.py`
  - `apps/api/src/spatial/transit_accessibility.py`
  - `apps/api/tests/unit/test_bay_area_511_client.py`
  - `apps/api/tests/unit/test_transit_accessibility.py`
  - `PR_DESCRIPTION.md`
- **Spine files I expect to need:** none. Follows the US-403
  (`gtfs_static_client.py`) precedent: a self-contained, network-free-testable
  compute module. Scheduler/registry wiring is out of scope (left as a
  follow-up, same as US-403's unresolved spine hold).

## Intent

Ingest the 511.org SF Bay Area regional GTFS bundle (32 operators) and score
every H3 res-9 hex's transit accessibility: Layer 1 = AM-peak (7-9a)
frequency-weighted stop density per hex; Layer 2 = k-ring (k=3) exponential
distance-decay (lambda=0.7) propagating that score to neighboring hexes.
Output per hex: `transit_connectivity_score` (0-100), `transit_mode_mix`
(fraction by mode), `peak_frequency` (decay-weighted trips/hour). Hexes with
no transit within 3 rings score 0, never null (achieved by a `get_score`
lookup helper with 0.0 default, since the sparse output map only lists
reached hexes).

## Decisions

- 2026-09-13 — Reuse `GtfsStaticClient.parse_feed_zip` (existing leaf,
  untouched) for the actual zip→dict parsing since 511's GTFS zips share the
  standard 5-file schema; `bay_area_511_client.py` only adds 511-specific
  catalog/download + multi-operator merge with per-operator id prefixing (real
  511 feeds reuse small numeric ids across agencies, so ids must be
  namespaced on merge to avoid cross-operator collisions).
- 2026-09-13 — AM peak weekday weight uses Mon-Fri only (5-day denominator),
  distinct from US-403's 7-day service_frequency, since AM peak is a
  commute-pattern concept.
- 2026-09-13 — route_type -> mode mapping covers GTFS base codes 0-7;
  unrecognized/extended codes default to "bus" (documented assumption).
- 2026-09-13 — Composite score uses a saturating (Michaelis-Menten form)
  normalization `100 * raw / (raw + HALF)` with HALF=20.0 decayed trips/hour,
  bounded in [0,100), monotonic, 0 at raw=0 — chosen over z-score compositing
  (composite_indices.py's convention) because the ticket asks for an absolute
  0-100 scale, not a relative/z-scored one.

## Current step

DONE. Implementation + tests complete and verified:
- `pytest tests/unit/test_transit_accessibility.py tests/unit/test_bay_area_511_client.py`
  — 51 passed.
- `pytest -m interlock` from `apps/api` — 25 passed, unaffected (no spine
  edit, as expected).
- `ruff check` on all four new files — clean.
- Full `python3 scripts/verify_cicd_preflight.py` (with `ruff`/venv on PATH
  and `PYTHONPATH=apps/api` for the script's own process, since it doesn't
  self-bootstrap those) — all 6 gates green.
- `PR_DESCRIPTION.md` written at the worktree root.

## Next step

None for this stream — no spine hold needed. Follow-up (out of scope, noted
in PR_DESCRIPTION.md): wiring `Bay511Client`/`transit_accessibility.score_feed`
into `scheduler.py` for a scheduled refresh and registering
`transit_connectivity_score`/`transit_mode_mix`/`peak_frequency` as
`EnrichedH3Feature` covariate fields — mirrors US-403's still-open spine hold
for the same reason (this ticket's acceptance criteria are all about
parsing+scoring, not scheduling).
