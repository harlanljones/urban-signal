# Stream log — us123-nlcd — 2026-08-25

## Claim

- **Stream id:** us123-nlcd
- **Deliverable (leaf, no code):** `docs/research/annual-nlcd-layers.md`
- **Files created/edited:** `docs/research/annual-nlcd-layers.md`
- **No application code touched.** No `.py`, config, spine file, or test modified.

## Verdict

**DEFER** formal registration; **run the Austin + New Orleans two-metro pilot now**
as a leaf stream; plan the raster + H3 zonal capability as a spine stream.

## Evidence headlines

- Annual NLCD Collection 1.2 (June 2026) = six raster products, 30 m, **CONUS
  only**, annual **1985–2025**; public domain (USGS, DOI 10.5066/P94UXNTS).
- Version history 1.0 → 1.1 → 1.2 rewrites the whole 1985–series — a registered
  feed must pin collection version + effective date and re-snapshot on a bump.
- Destructive finding: the repo has **no raster/GeoTIFF platform** (grep of
  `apps/api` finds only the CARTO basemap MapLibre `raster` source; the
  `DatasetSpec.platform` contract is socrata/arcgis/ckan/csv, no `FeedType` for
  land cover, no H3 zonal-stats engine). Registration is spine-shaped, not a leaf.
- Distribution: MRLC Viewer AOI download (free, exact bbox) and EarthExplorer;
  **requester-pays** USGS AWS S3 (us-west-2, `s3://usgs-landcover/annual-nlcd/c1/v0/...`).
  `c1/v0` looks stale vs release v1.2 — live bucket layout UNVERIFIED.

## Storage (derived from 30 m + registered bboxes; compressed = ESTIMATE)

- New Orleans bbox (~2,470 km²) ≈ 2.7 MB raw per product-year; Austin bbox
  (~2,940 km²) ≈ 3.3 MB. Pilot (3 products × 41 yr, both metros) ≈ ~0.74 GB raw,
  ~100–250 MB compressed, **free** via MRLC AOI.
- National backfill: key 3-product subset ≈ 1.1 TB raw (123 layer-years), full
  six-product ≈ 2.2 TB raw; compressed ESTIMATE ~0.12–0.75 TB. Steady-state is
  ~a handful of layer-years per year — cheap.

## H3 fit

- 30 m pixel vs H3: res 7 ≈ 5,700 px/cell, res 8 ≈ 820 px/cell, res 9 ≈ 117
  px/cell. Recommend **aggregate at res 8**, rollup to res 7, keep res 9 behind a
  confidence/pixel-count floor (single-pixel classification noise dominates).

## Blockers to resolve

1. Are the CONUS mosaics Cloud-Optimized GeoTIFFs (windowed-read friendly)?
   UNVERIFIED.
2. Live S3 bucket path for release 1.2 (documented `c1/v0` appears stale).
   UNVERIFIED.
3. Raster platform + `FeedType` + producer + H3 zonal engine do not exist — must
   be added (spine) before REGISTER can be honoured.
