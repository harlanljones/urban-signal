# Stream log — hx-d — 2026-10-12

## Claim
- **Stream id:** `hx-d` (ROADMAP.md HX-D1..D4; ADR-0010 Stage D: Adaptive anchor backfill, LODES at detail resolution, transport decision)

## Decisions & Verification
- **HX-D1 (LODES-at-Detail Feasibility):**
  - **Assumption A2 confirmed:** `national_builder.aggregate_state(state, year, resolution)` executes across resolutions 7, 8, and 9 with `cell_filter: Iterable[str]`. Job and worker sums are strictly conserved across resolutions.
  - **Envelope verification:** 2,319 metro-less Census Urban Areas at adaptive resolution contribute 233,306 cells. Combined nationwide detail cells: $53,799 + 233,306 = \mathbf{287,105}$ cells, well within the ADR-0010 0.5M–1.5M envelope.
  - **DG-6 ordered list:** Documented in `docs/research/hex-coverage-stage-d-feasibility.md` (top: Atlanta 64,288 cells, San Juan 26,558 cells, Jacksonville 17,297 cells, Birmingham 12,642 cells).
  - **Honesty rule:** Metro-less anchor regions have `owner = None`, `distance_km = None` (LIMS is null, never synthesized) and `label = "measured"` for LODES. `CoveragePlan.plan_anchor_region()` implemented.
- **HX-D2 (Anchor-Backfill Adapter):**
  - `apps/api/src/export/national_builder.py` implements `build_anchor_detail_region()`: aggregates LODES at the anchor's adaptive resolution, partitions into tile parents, stages with `stage_region()`, and promotes with `promote_region()`. Tested in `test_national_builder.py`.
- **HX-D3 (Payload Report & Property Slimming):**
  - Measured largest detail tile chunk across all registered metros: **847.7 KB (0.81 MiB)** for NYC core at res 9.
  - Headroom factor: 24.7x below the 20 MiB Workers KV hard budget ($0.81\text{ MiB} \ll 20\text{ MiB}$).
- **HX-D4 (MVT Decision):**
  - Per Decision Gate DG-7 (*"MVT only if any detail chunk cannot be kept under MAX_KV_VALUE_BYTES (20 MiB) or the client CPU threshold"*), Mapbox Vector Tiles are **declined**.
  - Plain GeoJSON transport-free chunks are maintained, avoiding binary protobuf encoding overhead, dual-runtime codec sync, and serialization fragility.
