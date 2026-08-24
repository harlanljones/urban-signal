# Urban Signal Product & Architecture Explorer (`apps/product`)

The interactive product overview and architectural learning site for Urban Signal.

---

## Overview

- **Multi-Page Static Site (ADR 0006):** 10 core section routes (`/`, `/system/`, `/evidence/`, `/methodology/`, `/architecture/`, `/cities/`, `/compare/`, `/glossary/`, `/changelog/`, `/faq/`) plus 21 dedicated city deep-dive pages (`/cities/<id>/`).
- **Single Source of Truth (`facts.json`):** Generated directly from the authoritative Python `REGISTRY` via `scripts/export_site_facts.py`.
- **Agent Context & Discovery:** Hosts `llms.txt`, `llms-full.txt`, and structured `facts.json` for agent-facing knowledge discovery.
- **Direct Link to Live Dashboard:** Contains routing and deep links to the production dashboard at [https://us-dash.harlanljones.com/](https://us-dash.harlanljones.com/).

---

## Live Dashboard Preview

| Live Geospatial Dashboard | Parcel Inspection & SHAP Attribution |
| :---: | :---: |
| ![San Francisco Bay Area Dashboard](../../docs/screenshots/dashboard-san_francisco.png) | ![Parcel Inspector](../../docs/screenshots/dashboard-inspector.png) |

---

## Development & Verification

```bash
# Build static site to dist/
bun run build

# Start local preview server (exports facts, builds, serves)
bun run dev

# Content, multi-page routing, and agent surface linting
bun run lint

# Export facts.json from Python city registry
bun run facts:export

# Check facts.json freshness against Python city registry
bun run facts:check
```

## Deployment

```bash
bun run deploy
```
