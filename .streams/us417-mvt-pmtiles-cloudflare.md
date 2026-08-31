# Stream log — us417-mvt-pmtiles-cloudflare — 2026-08-31

## Claim

- **Stream id:** `us417-mvt-pmtiles-cloudflare`
- **Leaf files I will create/edit:** `docs/research/us-417-mvt-pmtiles-cloudflare.md`, `.streams/us417-mvt-pmtiles-cloudflare.md`
- **Spine files I expect to need:** none (research-only, leaf-shaped; child of US-408)

## Intent

Research vector tile (MVT/PMTiles) feasibility on this stack's Cloudflare edge (Workers + KV/R2 + Pages): can the existing snapshot/KV pipeline emit MVT or PMTiles within the 20MiB KV value / 5MiB national chunk budgets, what serving path works (static R2/Pages vs Worker-tiled), and what the GeoJSON→MVT swap seam looks like against `src/spatial/coverage.py` and `GET /api/v1/gridtiles`. Deliverable: written feasibility memo with recommended architecture and open risks, feeding the US-408 "Plan MVT next" decision.

## Findings

### Code read (2026-08-31)

- Actual paths: builder is `apps/api/src/export/snapshot_builder.py` (not `src/spatial/`); seam module is `apps/api/src/spatial/coverage.py`; metro route `GET /api/v1/grid` in `apps/api/src/serving/router.py:279` (on-the-fly GeoJSON, res 7-9, k_ring 0-3); `/api/v1/gridtiles` is served on the edge from the KV snapshot (`gridtiles_res{res}/{parent}.json` keys + manifest `tile_indexes`), not computed in Python.
- Budgets confirmed in code: `MAX_KV_VALUE_BYTES = 20 MiB` (KV hard cap 25 MiB), `MAX_MANIFEST_BYTES = 10 MiB`, `MAX_BULK_BYTES = 512 MiB` (wrangler kv bulk put), `NATIONAL_MAX_CHUNK_BYTES = 5 MiB` (measured res-6 chunk ~254 KB). LOD parents: res 7/8 → res-4 parents, res 9 → res-5 parents; legacy `gridtiles/{parent}` + `tile_index` shim retained for res 9.
- `coverage.py` docstring already declares the swap seam: `gridtiles_res*/{parent}` → `tiles/{z}/{x}/{y}.pbf` without touching `metro_cells`/`aggregate_values` signatures — the same inputs an MVT pyramid would consume.
- Existing stub `docs/research/map-mvt-feasibility.md` targets this issue; this memo supersedes it (cross-link both).

### Web research (2026-08-31)

- **KV limits** (developers.cloudflare.com/kv/platform/limits): value 25 MiB max both plans, key 512 B, 1000 ops/invocation, 1 write/s per key. Our 20 MiB build budget confirmed as 5 MiB headroom under the hard cap.
- **R2 limits** (r2/platform/limits): object size up to ~5 TiB (4.995 TiB via multipart), no object count limit, 100 custom domains/bucket. r2.dev endpoints are rate-limited/throttled and not for production — production PMTiles serving must go through a custom domain or a Worker binding. R2 egress is free; the PMTiles docs' Cloudflare page recommends R2 + custom domain as the reference serving path.
- **Workers limits** (workers/platform/limits): paid CPU 30 s default (configurable up to 5 min), free 10 ms; 128 MiB memory; 1000 subrequests/invocation paid (50 free); 50 Cache API calls/request. Streaming responses have no hard wall-time limit while client connected. A z/x/y MVT Worker (protobuf encode ~thousands of small polygons) fits CPU budget comfortably; the constraint is cold-start + subrequest pattern, not CPU.
- **PMTiles v3 spec** (protomaps/PMTiles spec/v3): single-file archive — 127-byte header, root directory within first 16,384 bytes, JSON metadata (TileJSON vector_layers), leaf directories, tile data. Clients read via HTTP range requests (2 per cold tile lookup typical, cached); works on any static storage supporting Range (R2 S3 API + custom domain does). Internal compression is gzip or none per archive; outer transport gzip/brotli of .pmtiles is NOT useful (already-compressed MVT payloads inside) — serve with Cache-Control immutable + Accept-Ranges: bytes.
- **MapLibre integration** (docs.protomaps.com/pmtiles/maplibre): `npm i pmtiles`, `maplibregl.addProtocol("pmtiles", protocol.tile)`, source `url: "pmtiles://https://.../tiles.pmtiles"`; min/maxzoom auto-derived. Works with current MapLibre GL JS (addProtocol API long-stable; dashboard pins 3.6.2 — supported).

## Outcome

- Deliverable: `docs/research/us-417-mvt-pmtiles-cloudflare.md` (full memo, supersedes stub `docs/research/map-mvt-feasibility.md`).
- Verdict: feasible; recommend pre-tiled PMTiles on R2 (custom domain, pmtiles:// protocol in MapLibre 3.6.2), reject Worker-generated MVT. Budget pressure (20MiB/5MiB/10MiB) largely dissolves since archives go to R2 (~5TiB objects) and the manifest shrinks.
- Linear US-417 comment posted with doc reference.
- Note: task brief said snapshot builder lives in `apps/api/src/spatial/` — actual path is `apps/api/src/export/snapshot_builder.py`.
