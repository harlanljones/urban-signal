# Stream log — us418-lims-lodes-blend-honesty — 2026-08-31

## Claim

- **Stream id:** `us418-lims-lodes-blend-honesty`
- **Leaf files I will create/edit:** `docs/research/us-418-lims-lodes-blend-honesty.md`, `.streams/us418-lims-lodes-blend-honesty.md`
- **Spine files I expect to need:** none (research-only, leaf-shaped; child of US-408)

## Intent

Research visual/data honesty of the blended LOD (metro-aggregated LIMS where coverage exists, LODES fallback elsewhere) for zoomed-out cross-metro comparison: are the two sources comparable at coarse res, how must the UI disclose mixed provenance (per-hex source flag, legend, tooltip), and what aggregation caveats (year vintage, denominators, H3 percentile correctness from US-415) apply. Deliverable: written recommendations for the dashboard's blended renderer disclosures, feeding US-408 closure.

## Findings

- The "blend" is actually a disjoint zoom-band handoff since US-422: LODES national overlay (res 4/5/6) below `ZOOM_FLOOR=6`, metro LIMS pyramid (res 7/8/9) at z≥6 — not a per-hex mix.
- Defect is presentation-layer: `nationalColorExpression` coalesces `*_national_pct → jobs_pct → workers_pct`, so every LIMS metric silently renders as LODES jobs/workers percentile below z6 while the legend title still says e.g. "LIMS Momentum Score". Labels stay 0/50/100 regardless of source.
- Provenance data exists but is unused: national parquet carries `year` + `signal_source`; tooltip path shows numeric props only.
- Builder-side honesty is solid (nulls stay null, no zero-fill, ranks over non-null, partly-synthetic CBDRB flag) — keep it.
- Comparability gaps: vintage (LODES pinned 2023 + 28-mo lag + backfilling vintages vs per-city LIMS as-of dates), construct (LEHD primary jobs/workers vs derived LIMS scores), per-city LIMS schema/cadence drift, cross-layer percentile bases differ, coverage asymmetry (no land mask, AK gaps).
- External anchors (Axis Maps choropleth guide, LEHD v8 tech doc, uncertainty-viz practice) all point to: legend must follow the source, tooltip provenance line, opacity/hatch distinctness for lower-fidelity class, coarse-res disclaimer.

## Outcome

- Done (research stream). Deliverable: `docs/research/us-418-lims-lodes-blend-honesty.md` (full run of the `map-blended-lod-honesty.md` stub).
- Verdict: blended compare **needs disclosure, not restriction** — the semantic switch at z6 must be surfaced (zoom-aware legend title/footnote, tooltip source/vintage line, optional crossing toast / reduced-opacity LODES style, "pattern not place" note). Cross-metric compare at national zoom is already de-facto disabled by the coalesce; keep raw LODES counts out of the UI.
- Unblocks US-412 (coalesce policy) and US-413 (fallback visibility/tooltip badge) with concrete, dashboard-side fixes.

