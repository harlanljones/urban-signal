# Stream log — bay-area-map-wiring — 2026-09-23

## Claim

- **Stream id:** `bay-area-map-wiring`
- **Leaf files created/edited:**
  - `apps/api/src/export/bay_area_context.py` (new — runs the US-439..443 pipelines, writes one per-hex table + meta)
  - `apps/api/tests/unit/test_bay_area_context.py` (new)
  - `apps/api/src/export/snapshot_builder.py` (extend — `--context-dir` join, sparse-key LOD averaging, `context_layers` manifest block)
  - `apps/api/tests/unit/test_export_snapshot.py` (extend)
  - `apps/api/src/producers/redfin_client.py` (stream the 1.5 GB tracker to disk instead of holding it in memory)
  - `apps/api/src/serving/dashboard.py` + regenerated `apps/dashboard/public/index.html` (metric picker optgroup, no-data legend, attribution, popup + inspector rows)
  - `apps/dashboard/src/index.ts` (manifest type + API doc line)
  - `.github/workflows/bay-area-context.yml` (new, weekly), `.github/workflows/batch-push.yml` (download artifact, pass `--context-dir`)
- **Spine files touched:** none. `producers/scheduler.py` and `producers/dob_permits_producer.py` are untouched: context layers are file-based (see `spatial/context_source.py`), not Kafka event feeds, and the permit fetch reuses the producer's row parser via a Kafka-free subclass.

## Intent

Get the five Bay Area data layers (US-439 LODES, US-440 market, US-441 permits,
US-442 transit, US-443 Overture) onto the map. Before this stream four of the
modules were imported by nothing and none reached a grid tile.

## Decisions

- 2026-09-23 — One table, joined by `h3_index`, not per-city code: every
  registered city's grid cells that fall in the table get the values, so San
  Jose and Oakland cells light up alongside San Francisco.
- 2026-09-23 — Nulls stay null: a cell outside a layer's coverage carries no
  property and no percentile, and the dashboard paints it "no data".
  Percentiles rank only valued cells; LOD aggregates average each key over the
  children that carry it.
- 2026-09-23 — Refresh cadence is a weekly workflow artifact, not the nightly
  publish: the sources refresh weekly to annually and the Redfin file alone is
  1.5 GB. The publish downloads the newest successful artifact and is
  unchanged when none exists.
- 2026-09-23 — Transit needs a `BAY_511_API_KEY` repository secret; without it
  the layer is recorded as skipped.
- 2026-09-23 — Not verified against live data from the build container: the
  network policy blocks lehd.ces.census.gov, api.511.org, data.sfgov.org,
  data.sanjoseca.gov, tigerweb and extensions.duckdb.org. First real run is the
  workflow's `workflow_dispatch`.

## Current step

Done — PR open.

## Next step

Trigger `bay-area-context` by hand once `BAY_511_API_KEY` is set, then check
`bay_area_context_meta.json` in the artifact for per-layer status.
