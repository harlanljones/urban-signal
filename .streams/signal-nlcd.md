# Stream log — signal-nlcd — 2026-08-26

Copied from `.streams/_TEMPLATE.md` as the first action (phase 1, Claim).

## Claim

- **Stream id:** `signal-nlcd`
- **Leaf files I will create/edit:**
  - `docs/research/nlcd-validation.md` (the US-123 validation deliverable)
  - `.streams/signal-nlcd.md` (this log)
  - No new metrics module — see Decisions (code is NOT warranted; would require absent raster capability)
- **Spine files I expect to need:** **none.** This is a validation-only leaf. The
  conclusion is DEFER (do not register now), so no `FeedType`/`DatasetSpec`/platform
  or registry edit is required. If the verdict had been REGISTER, it would have
  forced a spine change (new raster platform + land-cover FeedType + H3 zonal engine)
  — that is exactly why this is a leaf now and not a registration.

## Intent

Validate, for Linear US-123, whether **annual NLCD land-cover change** can serve as a
signal in Urban Signal. Deliver `docs/research/nlcd-validation.md` covering data
source, geographic detail, update cadence, mapping to US spatial units, proposed
validation approach, incremental value vs current feeds, risks/dependencies, and a
recommendation (adopt/reject/defer). Build leaf-only: no spine file is touched.

## Decisions

- **2026-08-26 —** Reuse the already-probed live research in
  `docs/research/annual-nlcd-layers.md` (probed 2026-08-25, one day prior) as the
  evidence base for source facts; this deliverable re-validates specifically against the
  US-123 framing ("annual land-cover change signals") and states the registration
  decision. No new web probes needed — the facts are current and the dominant risk
  (collection-version drift) is unchanged.
- **2026-08-26 —** **No code module added.** A land-cover metrics kernel would operate
  on cell-level impervious/land-cover aggregates, but (a) no such aggregates exist —
  the repo has no raster/GeoTIFF platform, no land-cover `FeedType`, and no H3
  zonal-aggregation engine (verified: grep of `apps/api/src` for `raster/tif/gdal/
  rasterio` returns only the CARTO basemap `raster` *source*, not pixel ingest), and
  (b) the recommendation is DEFER, so writing a kernel now would be speculative and
  untestable. Per the task rule, code is added only when "clearly warranted"; it is not.
- **2026-08-26 —** **Verdict: DEFER (do not register now).** Source is excellent
  (public domain, CONUS-wide, 30 m, annual 1985→2025). Blocker is the repo's inability
  to ingest a raster and the annual-with-collection-rewrite cadence — both make it a
  slow-cadence context/validation signal, not an event feed, and a registration would
  require spine edits that are out of scope for a leaf. Therefore **no spine delta is
  needed** for this stream.

## Current step

Writing `docs/research/nlcd-validation.md`, then committing leaf files on `feat/nlcd`.

## Next step

If resumed: commit already-written leaf files; optionally kick the funded two-metro
pilot (Austin + New Orleans AOI clips) as a follow-up leaf, and route any REGISTER
decision to a spine stream (raster + H3-zonal capability) gated by `pytest -m interlock`.
