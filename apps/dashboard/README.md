# Urban Signal Edge Dashboard (`apps/dashboard`)

The edge deployment for Urban Signal, running on Cloudflare Workers with static assets and Workers KV snapshot caching.

> **Live Production URL:** [**https://us-dash.harlanljones.com/**](https://us-dash.harlanljones.com/)

---

## Visual Interface

| San Francisco Bay Area | Parcel Inspector & SHAP Attribution |
| :---: | :---: |
| ![San Francisco Bay Area](../../docs/screenshots/dashboard-san_francisco.png) | ![Parcel Inspector](../../docs/screenshots/dashboard-inspector.png) |

| New York City (5 Boroughs) | Chicago (6 Divisions) |
| :---: | :---: |
| ![NYC](../../docs/screenshots/dashboard-nyc.png) | ![Chicago](../../docs/screenshots/dashboard-chicago.png) |

### Layered Multi-Region Comparison

| DC & Montgomery County | Comparison Menu |
| :---: | :---: |
| ![DC and Montgomery County](../../docs/screenshots/dashboard-dc-montgomery.png) | ![Comparison Menu](../../docs/screenshots/dashboard-comparison-menu.png) |

---

## Local Development & Deployment

### 1. Local Development
```bash
# Run local Worker development server with static asset binding
bun run dev
```

### 2. Build & Test
```bash
# Test suite
bun test

# Typecheck TypeScript edge router
bun run typecheck

# Dry-run build
bun run build
```

### 3. Deploy to Cloudflare Workers
```bash
bun run deploy
```

---

## Synchronizing Dashboard Updates

The canonical dashboard source lives in `apps/api/src/serving/dashboard.py`. When backend dashboard templates or client logic change:

```bash
# From repository root:
python scripts/export_dashboard.py
pytest -m interlock
```
