# Changelog

Notable changes to the Urban Signal product site (`apps/product`), newest first.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added
- Coverage expanded to **101 registered metros**, generated from the city registry (`apps/api/src/spatial/city_registry.py`) — a 70-metro expansion beyond the prior 30. Every metro gets a deep-dive page at `/cities/<id>/` and a machine-readable JSON twin at `/public/cities/<id>.json`; the sitemap now lists all 101 (plus the section pages).
- Documented the new feed families across system/evidence/cities pages: **crime**, **street-cut permits**, **energy benchmarking**, **bike/ped counters**, **GBFS bike-share**, and **childcare licensing**, plus the NPPES and POI diff producers — beyond the four score-driving families (permits, 311, licenses, deeds).
- Documented the **MapLibre GL national all-metros overlay** on the live dashboard: the low-zoom res-4/5/6 national hex overlay now renders as native MapLibre `geojson` layers (fed by `/api/v1/national/{res}`), replacing the former deck.gl UMD bundle and removing ~1MB of CDN scripts.

### Changed
- The dashboard API section and README now state 101 registered metros and point to `facts.json` as the authoritative coverage projection.

## Site v2 — multi-page information architecture (2026-08-24)
- Documented the live dashboard's nearby-region comparison mode on `/compare/` and metro city pages: registered metros within 175 miles (haversine) are selectable and layered over the current city, sorted by display name, with an empty-state when no neighbor is in range, and the selection is preserved across export.
- Documented the NYC Marshal's executed evictions stream (`6z8x-wfk4`) across the system, evidence, and cities pages as a context-only validation signal — Socrata, 15-minute poll, `executed_date` watermark — explicitly not a LIMS input.
- `/architecture/` now describes the realtime aggregation loop and catalyst alert dispatch: the feature aggregation worker recomputes touched H3 cells on a five-minute cooldown and emits catalyst alerts at LIMS ≥ 85.0 to `alerts.catalyst`, which the alert dispatcher consumer fans out to webhooks behind a per-city calibration gate and daily budget (ADR 0008).
- Direct deep-links from metro compare cards (`/compare/`) to the live dashboard with preselected city query param (`/dashboard?city=<id>`).
- Auto-generated deep-dive pages and machine-readable JSON twins for 6 additional metros: Minneapolis, Pierce County WA, Milwaukee, Charlotte, Pittsburgh, and San Diego (bringing total to 27 registered metros and 37 sitemap URLs at the time).

## Site v2 — multi-page information architecture (2026-08-24)

### Added
- Dedicated pages for `/system/`, `/evidence/`, `/methodology/`, `/cities/`, and
  `/architecture/`, each assembled from a content fragment plus metadata through
  a shared build-time shell (`scripts/shell.mjs`). The home page is now a hub
  linking into these routes instead of a single-page scroll.
- Per-metro subpages at `/cities/<id>/` for all 21 registered metros, generated
  at build time from the city registry (single source of truth:
  `apps/api/src/spatial/city_registry.py` `REGISTRY`). Adding a metro to the
  registry and running `facts:export` is the whole job — no page is hand-written.
- Machine-readable twins for every metro at `/cities/<id>.json`.
- Registry→facts generator `scripts/export_site_facts.py`; it replaces the
  hand-maintained `public/facts.json`, which now carries `schema_version: 2`
  and registry-derived per-city coverage detail.
- SEO pass: canonical URL, Open Graph tags, and JSON-LD structured data on
  every page; `sitemap.xml` with 27 URLs.

### Changed
- Agent surfaces (`llms.txt`, `llms-full.txt`) refreshed to describe the new
  routes, per-metro pages, and registry-derived facts schema.
- Content verification extended: `scripts/verify-site-content.mjs` covers the
  new routes, and `verify-agent-surface.mjs` now fails if any city twin is
  missing or not registry-derived.

### Removed
- Single-page `index.html` (replaced by the multi-page build output).

### Deployment
- Target unchanged: Cloudflare Workers static assets via wrangler
  (`assets.directory = ./dist`; deploy with `bun run deploy` from
  `apps/product`).
- `/dashboard` continues to redirect (301) to the external dashboard host
  (`https://us-dash.harlanljones.com`) via `_redirects`.
