# US-417 — MVT / PMTiles feasibility on the Cloudflare edge stack

**Date:** 2026-08-31 · **Stream:** `us417-mvt-pmtiles-cloudflare` (leaf, child of US-408)
**Supersedes the stub** `docs/research/map-mvt-feasibility.md` (keep that file as the planned-spike record; cross-linked).

## Verdict

**Feasible, with one clear winner:** pre-tiled PMTiles on R2 is production-viable on this stack today with no new infrastructure beyond one R2 bucket + custom domain. Worker-generated on-the-fly MVT is *possible* (CPU/subrequest budgets clear) but strictly worse here: our data is a static publish-time snapshot, so generating tiles per request buys nothing and adds a codec in the hot path. **Recommendation: stay GeoJSON through US-411, then swap the edge serving layer to PMTiles-on-R2 behind the existing `gridtiles` API shape; do not build a z/x/y Worker tiler.**

## Budget math vs. the 20 MiB / 5 MiB / 10 MiB limits

Code-confirmed budgets (`apps/api/src/export/snapshot_builder.py:82-87`): `MAX_KV_VALUE_BYTES = 20 MiB` (KV hard cap 25 MiB), `MAX_MANIFEST_BYTES = 10 MiB`, `NATIONAL_MAX_CHUNK_BYTES = 5 MiB` (measured res-6 national chunk ≈ 254 KB), `MAX_BULK_BYTES = 512 MiB`.

| Artifact | Today (GeoJSON) | PMTiles-on-R2 | Under budget? |
|---|---|---|---|
| National res-6 chunk (KV) | ~254 KB | n/a (stays KV) | ✅ huge headroom |
| Metro `gridtiles_res{7,8,9}/{parent}` chunks (KV) | each bounded ≤ 5 MiB by parent-res choice | n/a during seam period | ✅ by construction |
| Whole-metro pyramid as MVT | — | MVT pbf is typically ~35–60% of equivalent GeoJSON bytes for hex polygons; a full metro archive lands in single-digit MB | ✅ — and it's **one object**, not hundreds of keys |
| Whole national archive | — | R2 object limit is ~5 TiB; a few hundred MB archive is irrelevant | ✅ — the 20 MiB KV cap leaves the picture |
| Manifest | 10 MiB cap | pmtiles:// URL + zoom bounds replaces `tile_indexes` map → manifest *shrinks* | ✅ |

Key structural point: **the KV/R2 budget pressure mostly disappears** — one metro = one immutable archive fetched by range requests (~2 HTTP reads per cold tile, then browser-cached), instead of N parent chunks each paying the 5 MiB chunk-sharding design cost. The 5 MiB national-chunk budget is unaffected — national KV chunks are a separate pipeline.

## Candidate architecture A — pre-tiled PMTiles on R2 (recommended)

1. `build_snapshot` gains a `--pmtiles` stage: emit the existing `metro_cells`/`aggregate_values` features (unchanged inputs) as GeoJSONSeq, pipe to `tippecanoe` (BSD-2) per metro/LOD, then `pmtiles convert` (protomaps Go CLI) to `tiles/{city}_res{7,8,9}.pmtiles`.
2. Publish to R2 (objects up to ~5 TiB; free egress). Serve through a **custom domain** — `r2.dev` is explicitly not for production (throttled/429 at modest QPS).
3. Dashboard: `npm i pmtiles`, `maplibregl.addProtocol("pmtiles", protocol.tile)` once at boot; source `url: "pmtiles://https://tiles…/{city}_res9.pmtiles"`; min/maxzoom auto-derived. Supported on the pinned MapLibre 3.6.2 line (`addProtocol` is a long-stable API).
4. Compression: MVT payloads are protobuf (already compact); pmtiles internally gzips directories. Do **not** rely on edge gzip/brotli for `.pmtiles` — counterproductive on an already-compressed binary; serve with `Cache-Control: immutable` + `Accept-Ranges`. (Edge brotli of the GeoJSON path is doing the heavy lifting today; MVT replaces that with binary compactness + range caching.)

## Candidate architecture B — Worker-generated MVT on the fly

A Worker intercepts `/tiles/{z}/{x}/{y}.pbf`, reads the relevant KV chunk(s), clips hexes to tile bounds, and protobuf-encodes MVT (e.g. `vt-pbf`).

- Runtime limits are not the blocker: paid CPU 30 s default (configurable to 5 min; free 10 ms), 128 MiB memory, 1000 subrequests/invocation — encoding one tile of a few thousand hexes is well under budget. Free plan would not be.
- Why it loses: (a) re-encodes the same static data every request — pure cost, no freshness win since the snapshot is publish-time anyway; (b) hex→tile clipping must re-implement the per-zoom LOD policy (res 7/8/9 selection) in the Worker, duplicating `coverage.py`; (c) response bytes ≈ what pre-tiling produces once, but paid per request; (d) KV chunk reads per tile add latency and subrequest spend.
- Only worth revisiting if tiles must reflect live data below snapshot cadence — not the current shape (ADR 0008 single-instance aggregator; snapshot publication is the freshness contract).

## The swap seam against coverage.py + gridtiles API

`apps/api/src/spatial/coverage.py` (docstring, US-408 note) already commits the seam: `metro_cells`/`aggregate_values` are the pyramid inputs, and the per-parent bucketing keys `gridtiles_res*/{parent}` map to `tiles/{z}/{x}/{y}.pbf` **without touching those signatures**. What must survive the swap:

- **Manifest shape.** Keep `manifest.tile_indexes` (res-9 legacy shim) intact for the compat window; add a `pmtiles` block (`{city: {res: url, minzoom, maxzoom, sha256, bytes}}`). Client prefers `pmtiles` when present, falls back to `gridtiles_res*` fetch — same pattern as the existing sharded-cells compat window.
- **API continuity.** `GET /api/v1/gridtiles?res=&parents=` remains the fallback path during rollout and for programmatic consumers; the interlock grid-tile coverage gate should be extended to assert the `pmtiles` manifest block rather than weakened.
- **Property fidelity.** Percentile honesty rules (`<metric>_metro_pct`/`_national_pct`, US-415 average-raw-then-rank) must survive tippecanoe: disable attribute quantization where it would collapse float percentiles, and add a sampled-cell property-parity check (MVT↔GeoJSON) in CI.

## Risks

1. **tippecanoe availability/reproducibility** — pin version in the build image; record `tippecanoe --version`, `h3` version, `manifest.generated_at` per run (same discipline as the sha256'd national index).
2. **Range-request serving correctness** — PMTiles needs `Range` + CORS on the tile domain; verify through our Workers routing/custom domain, not r2.dev.
3. **Two renderers during transition** — dashboard carries both the GeoJSON viewport-fetch path and the pmtiles source until cutover; keep the 120k-feature eviction cap for the GeoJSON fallback only.
4. **KV-published vs R2-published skew** — a failed R2 upload must not strand the manifest pointing at a stale archive; mirror the national-index integrity pattern (sha256 + bytes per entry).
5. **Unmeasured byte delta** — the ~35–60% estimate is literature-based, not measured on our hexes; run the planned tippecanoe spike on `nyc, chicago` res 7/8/9 (per the stub's method in `docs/research/map-mvt-feasibility.md`) before committing the migration ticket.

## Recommendation (decision input for US-408 "Plan MVT next")

1. Ship GeoJSON LOD now (as planned); the seam is already correct and costs nothing extra.
2. Approve **PMTiles-on-R2** as the target architecture; reject Worker-tiled MVT.
3. Next concrete step (~1 spike ticket): tippecanoe byte-size spike + one `nyc` pmtiles on a test R2 bucket behind a custom domain, dashboard `addProtocol` behind a flag, verify range requests + property parity.
4. Migration then becomes: builder `--pmtiles` stage → manifest `pmtiles` block → dashboard cutover → deprecate `gridtiles_res*` keys after the compat window.

## Sources

- PMTiles v3 spec — github.com/protomaps/PMTiles (spec/v3): 127-B header, root dir ≤16,384 B, range-request reads, internal gzip.
- docs.protomaps.com/pmtiles/maplibre — `pmtiles` npm protocol + `maplibregl.addProtocol`, `pmtiles://` URL scheme.
- developers.cloudflare.com/kv/platform/limits — 25 MiB value cap (both plans).
- developers.cloudflare.com/r2/platform/limits — ~5 TiB objects, r2.dev throttled (custom domain required for prod).
- developers.cloudflare.com/workers/platform/limits — CPU 10 ms free / 30 s paid (→5 min), 128 MiB memory, 1000 subrequests paid.
- Code: `apps/api/src/export/snapshot_builder.py:62-105`, `apps/api/src/spatial/coverage.py:29-32`, `apps/api/src/serving/router.py:279-352`.
