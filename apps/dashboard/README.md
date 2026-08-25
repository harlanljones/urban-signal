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

## Agent discovery surface

The worker generates an agent-facing discovery layer at the edge from the same
KV snapshot (always current on publish):

| Route | Purpose |
| --- | --- |
| `/robots.txt` | permissive policy; references sitemap + agentmap |
| `/sitemap.xml` | canonical URLs incl. `?city=<id>` deep links per published metro |
| `/auth.md` | agent registration/auth statement (public, no auth) |
| `/openapi.json` | machine-readable contract for the edge data API |
| `/.well-known/api-catalog` | RFC 9727 linkset catalog |
| `/.well-known/oauth-protected-resource` | RFC 9728 PRM (public resource) |
| `/.well-known/mcp/server-card.json` | MCP Server Card (SEP-1649) |
| `/mcp` | read-only MCP Streamable HTTP server (JSON-RPC tools) |
| `/.well-known/agent-skills/index.json` | Agent Skills discovery index + SKILL.md artifacts |
| `/.well-known/ai-catalog.json` | ARD capability manifest |

Homepage responses carry RFC 8288 `Link` headers, and `Accept: text/markdown`
returns a markdown rendering of the dashboard. The browser page additionally
registers WebMCP tools via `navigator.modelContext.registerTool()` when
available. DNS-AID records are zone-level — see `deploy/dns/dns-aid.md`.

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
