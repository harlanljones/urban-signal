# Changelog

Notable changes to the Urban Signal product site (`apps/product`), newest first.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added
- Direct deep-links from metro compare cards (`/compare/`) to the live dashboard with preselected city query param (`/dashboard?city=<id>`).
- Auto-generated deep-dive pages and machine-readable JSON twins for 6 additional metros: Minneapolis, Pierce County WA, Milwaukee, Charlotte, Pittsburgh, and San Diego (bringing total to 27 registered metros and 37 sitemap URLs).

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
