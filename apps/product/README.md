# Urban Signal Product & Architecture Explorer (`apps/product`)

The interactive product overview and architectural learning site for Urban Signal.

---

## Overview

- **Interactive Architecture:** Interactive visualization of municipal data streams, H3 indexing, time-decayed feature engineering, and multi-horizon inference.
- **Agent Context & Discovery:** Hosts `llms.txt`, `llms-full.txt`, and `facts.json` for agent-facing knowledge discovery.
- **Direct Link to Live Dashboard:** Contains routing and deep links to the production dashboard at [https://us-dash.harlanljones.com/](https://us-dash.harlanljones.com/).

---

## Live Dashboard Preview

| Live Geospatial Dashboard | Parcel Inspection & SHAP Attribution |
| :---: | :---: |
| ![San Francisco Bay Area Dashboard](../../docs/screenshots/dashboard-san_francisco.png) | ![Parcel Inspector](../../docs/screenshots/dashboard-inspector.png) |

---

## Development

```bash
# Build static site to dist/
bun run build

# Start local preview server
bun run dev

# Content & agent surface linting
bun run lint
```

## Deployment

```bash
bun run deploy
```
