# Urban Signal Product & Architecture Explorer (`apps/product`)

The interactive product overview and architectural learning site for Urban Signal.

---

## Overview

- **Multi-Page Static Site (ADR 0006):** 10 core section routes (`/`, `/system/`, `/evidence/`, `/methodology/`, `/architecture/`, `/cities/`, `/compare/`, `/glossary/`, `/changelog/`, `/faq/`) plus 27 dedicated city deep-dive pages (`/cities/<id>/`).
- **Single Source of Truth (`facts.json`):** Generated directly from the authoritative Python `REGISTRY` via `scripts/export_site_facts.py`.
- **Agent Context & Discovery:** Hosts `llms.txt`, `llms-full.txt`, and structured `facts.json` for agent-facing knowledge discovery.
- **Direct Link & Deep Links to Live Dashboard:** Contains routing and deep links (`/dashboard?city=<id>`) to the production dashboard at [https://us-dash.harlanljones.com/](https://us-dash.harlanljones.com/).

---

## Live Dashboard Preview

| Live Geospatial Dashboard | Parcel Inspection & SHAP Attribution |
| :---: | :---: |
| ![San Francisco Bay Area Dashboard](../../docs/screenshots/dashboard-san_francisco.png) | ![Parcel Inspector](../../docs/screenshots/dashboard-inspector.png) |

---

## Development & Verification

```bash
# Build static site (pages, markdown twins, .well-known documents) to dist/
bun run build

# Start local preview server (exports facts, builds, serves)
# Note: this plain HTTP server does not run worker.mjs — use the command below
# it for the full discovery surface (Link headers, /mcp, negotiation).
bun run dev

# Full edge surface locally: Link headers, text/markdown negotiation,
# /healthz, /mcp MCP server, CORS on /.well-known/*
bunx wrangler dev

# Content, multi-page routing, and agent surface linting
bun run lint

# Export facts.json from Python city registry
bun run facts:export

# Check facts.json freshness against Python city registry
bun run facts:check
```

## Agent discovery surface

| Surface | Where | Enforced by |
| :-- | :-- | :-- |
| RFC 8288 Link headers | every response (`worker.mjs`) | `verify-agent-surface.mjs` tripwires |
| Markdown twins (`Accept: text/markdown`) | `dist/**/index.md`, served by worker | twin-per-route + front-matter checks |
| API catalog (RFC 9727) | `/.well-known/api-catalog` | linkset anchor/relations checks |
| Product Knowledge OpenAPI | `/.well-known/openapi.json` | paths + city-id enum vs `facts.json` |
| Protected resource metadata (RFC 9728) | `/.well-known/oauth-protected-resource` | empty-AS + auth.md pointer |
| auth.md | `/auth.md` | required sections present |
| MCP server + card | `/mcp`, `/.well-known/mcp/server-card.json` | advertised tools exist in worker |
| Skills discovery index (v0.2.0) | `/.well-known/agent-skills/index.json` | sha256 digest vs artifact bytes |
| ARD manifest | `/.well-known/ai-catalog.json` | url/data exclusivity, query counts |
| WebMCP tools | `src/webmcp.js` via `navigator.modelContext` | script tag on every page |

Documents are emitted at build time by `scripts/generate-agent-surfaces.mjs`; the edge
worker only adds what static hosting cannot express. DNS-level discovery (DNS-AID) is
documented in [`docs/dns-aid.md`](../../docs/dns-aid.md) and requires zone changes.

## Deployment

```bash
bun run deploy
```
