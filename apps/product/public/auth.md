# auth.md — Urban Signal product site

This site (`https://urban-signal.harlanljones.com`) publishes **public,
read-only** product knowledge: marketing and methodology pages, machine-readable
facts, per-city briefs, and discovery documents. There are no protected
resources on this host.

## Agent audience

AI agents, assistants, and pipelines that need structured ground truth about
what Urban Signal covers — registered metros, feed contracts, methodology
boundaries — or that connect to the read-only MCP server at `/mcp`.

## Authentication methods

- **None required.** Every endpoint on this host accepts anonymous HTTPS
  requests. No cookies, tokens, or API keys exist or are issued.

## Registration / provisioning

- **None.** There is no account system and no agent registration step. Start
  reading immediately:
  - `GET /facts.json` — product-level facts (metros, feeds, limitations).
  - `GET /llms.txt` — agent guide to the whole site.
  - `GET /.well-known/api-catalog` — RFC 9727 catalog of services.
  - `POST /mcp` — MCP Streamable HTTP server (card:
    `/.well-known/mcp/server-card.json`).

## Credentials

- Not issued and not required. The RFC 9728 document at
  `/.well-known/oauth-protected-resource` advertises an empty
  `authorization_servers` list as the formal statement of this: no OAuth
  authorization server issues tokens for resources here.
- The live data API on `https://us-dash.harlanljones.com` is likewise public
  and unauthenticated; its statement lives at
  `https://us-dash.harlanljones.com/auth.md`.

## Etiquette

- Honor caching: pages and discovery documents are CDN-cacheable; snapshot
  endpoints return ETags — send `If-None-Match` instead of re-fetching.
- Values marked illustrative in `/methodology/` are examples, not results;
  quote `/facts.json` for coverage claims.
- Bugs or data disputes: open an issue at
  https://github.com/harlanljones/urban-signal/issues.
