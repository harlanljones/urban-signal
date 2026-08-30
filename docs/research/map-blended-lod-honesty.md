# Blended LIMS/LODES visual honesty for zoomed-out compare — research spike (US-418)

**Date of research: 2026-08-30 (stub — full run pending).** Blocks `US-412` edge `coalesce` logic and `US-413` dashboard fallback visibility. No `.py` edits.

## Method, and its limits

Planned primary-source layers, in order:

1. **Honesty rule.** Read `apps/api/src/export/national_builder.py:10` `honesty rule: hexes without data stay null (never zero-filled)` + `apps/api/src/spatial/national_grid.py:30` `NATIONAL_RESOLUTIONS=(4,5,6)` + `docs/research/census-lodes-validation.md:42` (LODES `28mo` lag, partially synthetic `CBDRB-FY21-249`) and `98` coverage gaps table. Use source docs, not memory.
2. **Current blend.** Read `apps/dashboard/public/index.html:1806` `nationalColorExpression` (`coalesce(*_national_pct, jobs_pct, workers_pct)`) + `1816` `nationalHeightExpression` + `snapshot_builder.py:122` `_apply_percentile_normalization` (LIMS `national_pct` rank) + `national_builder.py:312` `_attach_ranks` (LODES `jobs_pct`/`workers_pct` rank over non-null only).
3. **Screenshot matrix.** Capture `z 6 / 8 / 10` over `NYC→rural` transect (NYC metro core → NJ suburbs → rural PA) with (a) current LODES-only `national-h3-*`, (b) blended `coalesce(lims_national_pct, jobs_pct)` metro-aggregated LIMS, (c) blended with distinct fallback style (hatch/0.45 opacity for LODES). Record tooltip `source` badge when interpolated.
4. **Rank distribution check.** Compare LIMS `lims_score_national_pct` histogram (from `manifest` samples) vs LODES `jobs_pct` histogram (from `national/index` samples) — verify same green(`0`)→yellow(`50`)→red(`90`) ramp (`index.html:1806`) is not misleading when mixing signals.

**Limits.** No user study; honesty judged by rule `null stays null` + visual distinctness, not surveyed interpretation. Transect is 1 region; rural LODES null hexes remain null by rule (`_attach_ranks` leaves null ranks). No exact count presented as market fact — every number is measured file/aggregate characteristic or quoted from source.

## Source assessment (to be verified)

- **Access / terms.** LODES is Census public domain (`17 U.S.C. §105`), no auth, verified by `curl` in `census-lodes-validation.md:70`. Crosswalk `blklatdd`/`blklondd` provides block internal point — no TIGER geometry needed (`census-lodes-validation.md:84`).
- **File families.** `national/{res}/{res3_parent}.json` (`snapshot_builder.py:231` `_publish_national_layers`) with `cols (h3, jobs, workers, jobs_pct, workers_pct)` (`snapshot_builder.py:74` `NATIONAL_COLS`), vs `gridtiles_res7/8/9/{parent}` with `lims_score_national_pct`. Verify `NATIONAL_MAX_CHUNK_BYTES=5MiB` not exceeded.
- **Revision / reproducibility.** Pin `LODES8` format version + data vintage `YYYYMMDD` + `version.txt` per `census-lodes-validation.md:109`. Verify per-state `lodes_<st>.sha256sum`.

## Headline verdict (stub — to be filled after matrix)

**Pending.** Hypothesis: `coalesce(*_national_pct, jobs_pct)` on same ramp is honest *if* fallback hexes carry distinct visual (e.g., `0.45` opacity + dashed `line` or `(L)` badge) and tooltip shows `source: LODES jobs` vs `source: metro LIMS (k_ring_interpolated @ Xm)`. Without distinct style, blend misleads at `z 6-9` urban-rural boundary. Spike to confirm with side-by-side screenshots.

## Recommendation (stub)

- **If blend without style misleads:** ship `US-412` `coalesce` + `US-413` fallback style `line-opacity 0.22 → 0.45 dashed` for LODES, keep `fill-opacity 0.7` for LIMS-aggregated. Document honesty rule in `coverage.py` docstring and `dashboard.py` tooltip.
- **If blend is clear:** keep single ramp, add `source` badge only. Keep `null stays null` — absent hex means no data, not zero.
- **Do not zero-fill** territory hexes (`PR/VI`) or `AK 2017+` WAC gaps (`census-lodes-validation.md:97`) — they stay null and render as background.

## What unblocks

- `US-412` edge `nationalColorExpression` / `nationalHeightExpression` `coalesce` policy
- `US-413` `updateLayerVisibilities()` blended fallback + tooltip `source` badge

## Risks and dependencies

- `LODES` `jobs` vs `workers` `national_pct` are different surfaces — verify which fallback rank to `coalesce` with (`jobs_pct` vs `workers_pct` per `currentMetric`).
- `Percentile` histograms may differ (LIMS bimodal vs LODES log-normal) — verify ramp `0→50→75→90` not compressing one signal.
- `Vintage` drift — `Only files that have new or changed data will be included in future vintages` (`census-lodes-validation.md:111`) — pin vintage, verify SHA-256.

## Sources to cite (primary)

- `apps/api/src/export/national_builder.py:10`, `74`, `312`
- `apps/api/src/spatial/national_grid.py:30`
- `apps/api/src/export/snapshot_builder.py:74`, `122`
- `docs/research/census-lodes-validation.md:42`, `70`, `84`, `97`, `98`, `109`, `111`
- `apps/dashboard/public/index.html:1806`, `1816`, `1893`
