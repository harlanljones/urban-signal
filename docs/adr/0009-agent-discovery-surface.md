# ADR 0009: Agent Discovery Surface on the Product Site

**Status:** Accepted
**Date:** 2026-08-24
**Scope:** `apps/product` (edge worker, build emitter, discovery documents), `docs/dns-aid.md`
**Supersedes:** —
**Companion:** isitagentready audit goals; `apps/dashboard/src/index.ts` (sibling surface)

## Context

The product site exposes machine-readable knowledge (`facts.json`, per-city briefs,
`llms.txt`) but nothing that advertises it through the emerging agent-discovery
conventions. An isitagentready scan of `urban-signal.harlanljones.com` fails every
discovery check: no RFC 8288 Link headers, no `text/markdown` negotiation, no RFC 9727
API catalog, no OAuth protected-resource metadata, no auth.md, no MCP Server Card, no
skills index, no WebMCP tools, no ARD manifest, and no DNS-AID records. The dashboard
origin already ships most of this edge-generated (`apps/dashboard/src/index.ts`); the
product site — where agents land first — has none of it.

Options weighed:

1. **Zone-level fixes only** (Cloudflare Transform Rules + Markdown for Agents).
   Rejected: covers two checks; leaves catalogs/MCP/skills/ARD unaddressed and puts the
   contract outside the repository where it cannot be linted.
2. **Edge-generated everything** (dashboard's approach). Rejected here: the product site
   is fully static, so generating documents at request time would hide the served bytes
   from `bun run lint` and duplicate digest/spec logic into runtime code.
3. **Build-emitted documents + thin dynamic worker** (chosen).

## Decision

Keep the site static; split the surface by what can be precomputed:

- **Build time** (`scripts/generate-agent-surfaces.mjs`, new): emit
  `dist/.well-known/{api-catalog,oauth-protected-resource,openapi.json,mcp/server-card.json,agent-skills/index.json,ai-catalog.json}`
  plus sha256-digested SKILL.md artifacts. Digests cover final artifact bytes, so the
  index can never drift from what is served. The generator also authors an OpenAPI 3.1
  spec whose `city_id` enum is derived from `facts.json` — the same registry-derived
  discipline as every other export.
- **Runtime** (`worker.mjs`, new `main` with `run_worker_first: true`): RFC 8288 Link
  headers on every response (api-catalog, service-desc ×2, service-doc, describedby ×2,
  status, per-page markdown alternate), `Accept: text/markdown` negotiation serving
  build-time markdown twins (`index.md` beside every `index.html`, produced by a focused
  converter over our own regular HTML) with estimated `x-markdown-tokens`, explicit media
  types for extensionless well-known paths, `/healthz`, CORS on discovery paths, and a
  minimal MCP Streamable HTTP server at `/mcp`. Tool contracts live in one shared module
  (`scripts/mcp-tools.mjs`) consumed by both the server card and the dispatch table.
- **Browser** (`src/webmcp.js`, new): mirrors the four MCP tools via
  `navigator.modelContext` (both `registerTool()` and origin-trial `provideContext()`
  shapes, guarded no-op when absent).
- **Honesty constraints**: there are no protected resources and no authorization server,
  so RFC 9728 metadata publishes an empty `authorization_servers` array and `/auth.md`
  stays self-contained ("public, read-only, nothing to register"). No OIDC/OAuth AS
  metadata is fabricated. DNS-AID records require zone access and are documented in
  `docs/dns-aid.md` rather than faked.

## Consequences

- Every response now traverses the worker (`run_worker_first: true`): small per-request
  cost accepted in exchange for headers/negotiation applying to all routes; asset passthrough
  preserves `_redirects` behavior (`/dashboard` → dashboard host).
- `verify-agent-surface.mjs` gates the whole contract offline: twins exist per route and
  carry provenance front matter, linkset entries have anchors + relations, digests match
  artifact bytes, ARD entries carry exactly one of url/data with 2–5 representative queries,
  the OpenAPI enum equals `facts.json metros`, advertised MCP tools exist in the worker, and
  robots/head/footer reference the manifest.
- Markdown conversion is scoped to templates this repo controls; novel page constructs may
  need converter cases — the lint gate pins the shape of every twin so regressions fail loudly.
- DNS-AID remains red until `docs/dns-aid.md` records are applied to the zone and signed;
  it is the only goal not closable from inside the repository.
