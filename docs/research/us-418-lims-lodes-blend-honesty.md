# LIMS/LODES blended LOD visual honesty — research (US-418, child of US-408)

**Date:** 2026-08-31. Full run of the spike stubbed in `docs/research/map-blended-lod-honesty.md` (2026-08-30). Research-only; no `.py`/dashboard edits. US-415 (H3 LOD percentile-aggregation correctness) is Done and out of scope here except as inherited context.

## 1. What the blend actually is today

Evidence (all verified in `apps/api/src/serving/dashboard.py`, byte-synced to `apps/dashboard/public/index.html`):

- **The blend is a zoom-band handoff, not a per-hex mix.** `ZOOM_FLOOR = 6` (`dashboard.py:1477`): below z6 the national LODES overlay owns the map (`nationalResForZoom` → res 4/5/6 via `/api/v1/national/{res}`); at z≥6 the metro LOD pyramid (res 7/8/9, LIMS) owns it. Since US-422 the bands are disjoint (`updateNationalLayerVisibilities`, `dashboard.py:1783-1803`) — "blended fallback" in code comments is historical.
- **Same ramp, different meaning.** `nationalColorExpression` (`dashboard.py:1756-1765`) is `coalesce(${currentMetric}_national_pct, jobs_pct, workers_pct)` on the shared 0→50→75→90 green→yellow→orange→red ramp. For every LIMS metric (lims_score, delta_6m_p50, delta_12m_spillover, prob_18m_macro_outperformance) there is **no** `*_national_pct` below z6, so the map silently falls back to LODES `jobs_pct` then `workers_pct` — a different construct (jobs/resident workers, LEHD primary-job counts) than the metric the legend titles.
- **Legend does not change.** `legend-metric-title` stays e.g. "LIMS Momentum Score" (`dashboard.py:2615-2629`) even while the visible hexes encode LODES jobs percentiles. Labels stay 0/50/100 regardless of source.
- **Provenance exists in the data but is not surfaced.** The national parquet carries `year` and `signal_source` ("census_lehd_lodes8") (`export/national_builder.py:19-23`); no dashboard code reads either. The tooltip/inspect path (`onNationalHexClick` → `inspectH3CellWithNationalFallback`, `dashboard.py:1816-1842`) shows numeric props only — no source line, no vintage line.
- **Builder-side honesty is good.** `national_builder.py:10-12`: nulls stay null (no zero-fill, no synthesis); territories and known gaps (AK WAC/OD 2017+) stay null; ranks over non-null only; block counts flagged as partly synthetic (CBDRB-FY21-249) "treat as an index, never an exact count." Right baseline — the gap is purely in the presentation layer.

## 2. Comparability problems (LIMS vs LODES, and LIMS-vs-LIMS)

1. **Vintage.** LODES is a single pinned year (DEFAULT_YEAR 2023, v8, ~28-month publication lag; vintage ≠ createdate, later vintages backfill — `docs/research/census-lodes-validation.md`). LIMS metro aggregates are per-city snapshots at differing as-of dates and cadences. A z4 view compares a 2023 national jobs baseline against 2026-era municipal LIMS as if one layer, and the metric meaning flips when the user crosses the z6 floor.
2. **Denominator / construct.** LODES = LEHD primary workplace jobs (WAC C000) and resident workers (RAC C000), block-aggregated, partly synthetic. LIMS metrics are derived scores (momentum, capex, permit velocity, prediction percentiles). The coalesce means the same ramp encodes "share of national primary-job density percentile" below z6 and "LIMS momentum percentile" above z6, with no visual seam.
3. **Schema drift across cities' LIMS.** Metro-aggregated LIMS arrives from municipal feeds with per-city field maps, cadences, and coverage (see `docs/research/metro-coverage-audit.md`, `current-city-feed-gaps.md`). At national zoom the coalesced fallback hides which metros have rich LIMS and which only exist via LODES.
4. **Percentile bases differ.** LODES ranks are computed nationally over non-null hexes; LIMS `*_national_pct` ranks come from the snapshot builder over metro res-9 cells. A p90 in one layer is not p90 of the same population as a p90 in the other. (US-415 fixed within-layer aggregation; cross-layer rank comparability is unverifiable by construction.)
5. **Coverage asymmetry.** LODES covers 50 states + DC with published state/year gaps; LIMS exists only inside registered metros. The z<6 layer looks "complete" nationally, inviting national-level readouts the data does not support (no land mask; cells spill over water — US-422 notes).

## 3. External best-practice anchors

- **Axis Maps cartography guide (choropleth):** choropleths should encode rates/percentiles consistently; classed scales exist so readers can "get numbers off the map" — a legend that keeps one title/labels while the data source silently switches breaks that contract. A ramp assumes one data universe.
- **Census/LEHD LODES v8 tech doc (echoed in `census-lodes-validation.md`):** LODES is "a partially synthetic dataset"; block figures are disclosure-protected; publication lag ~2+ years; state coverage varies by year (AK WAC/OD gap 2017+); vintage ≠ createdate and newer vintages backfill corrections. LEHD treats LODES as suitable for magnitude/pattern indexing, not exact counts or tight cross-source comparison.
- **Uncertainty/mixed-provenance visualization practice (MacEachren et al.; newsroom conventions):** when one map mixes provenance or reliability, the standard devices are (a) a source/quality badge on hover, (b) a legend segment/footnote naming every source on the current view, (c) distinct texture (hatch/stipple) or reduced opacity for the lower-fidelity class, (d) a disclaimer when scales are percentile-normalized independently. The blend uses none today.

## 4. Concrete UI disclosure recommendations

Ordered by impact/effort. All dashboard-side; no schema change except where noted.

1. **Legend source line that follows the zoom band (highest priority, cheapest).** When `map.getZoom() < ZOOM_FLOOR`, set `legend-metric-title` to "Jobs density — LEHD LODES v8 (2023), national percentile" and add a footnote: "Zoom to ≥ z6 for metro LIMS signals (per-city municipal data, mixed vintages)." At z≥6 keep the LIMS title plus "— metro LIMS, mixed vintages."
2. **Rename or label the coalesce.** The bare `coalesce(${metric}_national_pct, jobs_pct, workers_pct)` means the legend title is often simply wrong. Minimal fix: item 1. Better: only coalesce to LODES for jobs/workers-shaped metrics; for LIMS-only metrics below z6, show LODES with an explicit "context layer (not {metric})" chip rather than a silent swap.
3. **Tooltip provenance line.** In `handleHexSelection` / `inspectH3CellWithNationalFallback`, render a first line: `Source: Census LEHD LODES v8 · 2023 · national percentile (partly synthetic; treat as index)` for national hexes, or `Source: {metro} LIMS · snapshot {date} · res-{n}` for metro hexes. `signal_source` and `year` are already in the parquet; thread them into the national chunk JSON cols if not already exposed.
4. **Visual distinctness at the seam (recommended).** Per the stub's hypothesis: reduced fill-opacity (~0.45) or dashed `national-h3-line` for LODES at z<6 vs solid LIMS at z≥6; or a one-time toast when the camera crosses ZOOM_FLOOR: "Now showing metro LIMS data — metric and vintage differ from the national view."
5. **Coarse-res disclaimer.** National res-4/5/6 cells (~6–175 km across, uniform grid, no land mask) must not be read as neighborhoods. Add at z<6: "Coarse national grid — pattern, not place."
6. **No-data honesty is already correct — keep it.** Null hexes render as background (AK gaps, territories). Do not zero-fill; if designers want them visible, use neutral gray mapped in the legend to "no data", never a ramp color.

## 5. Verdict: is blended compare defensible as-is?

**Needs disclosure — not restriction.** Within any single zoom band the layer is internally consistent (LODES everywhere below z6; single-metro LIMS above), so the dangerous case is the *silent semantic switch at the z6 boundary*, which items 1–4 fix at low cost. Cross-metric compare at national zoom is already de-facto disabled by the coalesce (all LIMS metrics degrade to jobs/workers percentile) — but silently and misleadingly; that is the actual defect, and legend/tooltip fixes suffice. A hard restriction (forced "national context" mode) would add friction without adding honesty. The one case that would justify restriction: exposing raw LODES counts as market facts (Census marks them partly synthetic). Rendering uses percentiles only — keep it that way, and keep "treat as an index" in tooltips.

## Sources

- `apps/api/src/serving/dashboard.py` (≈1477, 1566–1803, 1816–1842, 2615–2629)
- `apps/api/src/export/national_builder.py` (docstring 1–28; DEFAULT_YEAR, SIGNAL_SOURCE)
- `apps/api/src/export/snapshot_builder.py` (national layer publication, LIMS national_pct)
- `docs/research/census-lodes-validation.md` (vintage/backfill warnings, coverage gaps, syntheticity CBDRB-FY21-249, 28-mo lag)
- `docs/research/map-blended-lod-honesty.md` (spike stub this doc completes)
- `docs/research/map-lod-percentile-aggregation.md` (US-415, Done)
- Axis Maps Cartography Guide — Choropleth Maps (legend/classification/standardization)
- Census LEHD LODES v8 technical documentation (partially synthetic data; state/year coverage)
- Uncertainty-visualization practice (hatching/stippling/badge conventions for mixed-provenance maps)

