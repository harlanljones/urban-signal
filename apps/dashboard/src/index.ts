/**
 * Urban Signal edge worker.
 *
 * Serves the MapLibre dashboard as a static asset and answers /api/v1/* routes
 * from precomputed snapshot data pushed to Workers KV by GitHub Actions batch
 * runs (src/export/snapshot_builder.py). Response schemas mirror the FastAPI
 * serving API (src/serving/router.py) so the dashboard works unchanged.
 *
 * Also exposes an agent-discovery surface (all generated at the edge from the
 * same KV snapshot, so it stays current on every publish):
 *
 *   /robots.txt                              permissive policy + sitemap + agentmap
 *   /sitemap.xml                             canonical URLs incl. per-city deep links
 *   /auth.md                                 agent registration/auth statement
 *   /openapi.json                            machine-readable API contract (RFC-backed)
 *   /.well-known/api-catalog                 RFC 9727 linkset catalog
 *   /.well-known/oauth-protected-resource    RFC 9728 PRM (public resource, no AS)
 *   /.well-known/mcp/server-card.json        MCP Server Card (SEP-1649)
 *   /mcp                                     minimal MCP Streamable HTTP server
 *   /.well-known/agent-skills/index.json     Agent Skills discovery (RFC v0.2.0)
 *   /.well-known/agent-skills/<n>/SKILL.md   individual skill artifacts
 *   /.well-known/ai-catalog.json             ARD capability manifest
 *
 * Homepage responses carry RFC 8288 Link headers, and `Accept: text/markdown`
 * content negotiation returns a markdown rendering of the dashboard.
 */

// Route both adapters through the transport-free snapshot module (US-189/US-190).
// The limit constants come from snapshot.ts so the OpenAPI/MCP schemas below stay
// in lock-step with the single semantic source — see the PRODUCT DECISION comment
// in snapshot.ts.
import {
  queryCatalysts,
  querySubmarkets,
  lookupPrediction,
  fetchNationalIndex,
  fetchNationalRows,
  MAX_NATIONAL_PARENTS_PER_REQUEST,
  CATALYST_DEFAULT_LIMIT,
  CATALYST_MAX_LIMIT,
} from "./snapshot";

export interface Env {
  SNAPSHOT: KVNamespace;
  ASSETS: Fetcher;
}

const SERVICE_NAME = "urban-signal-product";
const APP_VERSION = "2.0.0";
const CACHE_CONTROL = "public, max-age=300";
const MANIFEST_TTL_MS = 60_000;
const DISCOVERY_CACHE_CONTROL = "public, max-age=600";
const MCP_SERVER_NAME = "urban-signal-dashboard";
const MCP_PROTOCOL_VERSION = "2025-06-18";
const DATA_SKILL_NAME = "urban-signal-data-api";
const MCP_SKILL_NAME = "urban-signal-mcp";

const CITY_ALIASES: Record<string, string> = {
  madison: "madison",
  madison_wi: "madison",
  nyc: "nyc",
  chicago: "chicago",
  san_francisco: "san_francisco",
  sf: "san_francisco",
  seattle: "seattle",
  sea: "seattle",
  king_county: "seattle",
  los_angeles: "los_angeles",
  la: "los_angeles",
  new_orleans: "new_orleans",
  norfolk: "norfolk",
  detroit: "detroit",
  austin: "austin",
  cincinnati: "cincinnati",
  boston: "boston",
  baltimore: "baltimore",
  montgomery: "montgomery",
  baton_rouge: "baton_rouge",
  denver: "denver",
  philadelphia: "philadelphia",
  philly: "philadelphia",
  washington_dc: "washington_dc",
  dc: "washington_dc",
};

let manifestCache: { value: Manifest | null; etag: string | null; expires: number } = {
  value: null,
  etag: null,
  expires: 0,
};

/** Clears the in-isolate snapshot caches (KV values + manifest). Used by the
 *  test suite to keep module-level cache state from leaking between cases. */
export function clearSnapshotCaches(): void {
  kvJsonCache = new Map();
  manifestCache = { value: null, etag: null, expires: 0 };
}

export interface Manifest {
  generated_at: string;
  app_version: string;
  cities: string[];
  resolution: number;
  k_ring: number;
  catalyst_threshold: number;
  tile_resolution?: number;
  tile_index?: Record<string, TileIndexEntry>;
  metro_index?: MetroMeta[];
}

interface TileIndexEntry {
  count: number;
  cities: string[];
  bbox: { min_lat: number; max_lat: number; min_lng: number; max_lng: number } | null;
}

interface MetroMeta {
  city_id: string;
  name: string;
  bbox: { min_lat: number; max_lat: number; min_lng: number; max_lng: number };
  center: { lat: number; lng: number };
}

const MAX_TILE_PARENTS_PER_REQUEST = 32;
export const H3_PARENT_PATTERN = /^[0-9a-f]{15}$/i;

export interface CatalystEntry {
  h3_index: string;
  lims_score: number;
  [key: string]: unknown;
}

export interface CatalystPayload {
  city_id: string;
  count: number;
  threshold: number;
  borough: string | null;
  catalysts: CatalystEntry[];
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function jsonError(status: number, detail: string): Response {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: {
      "content-type": "application/json",
      "x-content-type-options": "nosniff",
      "cache-control": "no-store",
    },
  });
}

function safeEcho(raw: unknown, max = 96): string {
  return String(raw ?? "")
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, max);
}

export function normalizeCity(raw: string | null, manifest: Manifest | null): string | null {
  if (!raw) return "nyc";
  const key = raw.trim().toLowerCase();
  const alias = CITY_ALIASES[key];
  if (alias) return alias;
  if (manifest && manifest.cities.includes(key)) return key;
  return null;
}

/** Parse and validate a comma-separated list of res-5 H3 parent indexes.
 *  Returns null when any token is malformed so callers can reject up front. */
function parseTileParents(raw: string): string[] | null {
  const tokens = raw
    .split(",")
    .map((token) => token.trim().toLowerCase())
    .filter((token) => token !== "");
  if (tokens.length === 0) return null;
  const parents: string[] = [];
  for (const token of tokens) {
    if (!H3_PARENT_PATTERN.test(token)) return null;
    if (!parents.includes(token)) parents.push(token);
  }
  return parents;
}

async function sha256Hex(input: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function etagMatches(request: Request, etag: string): boolean {
  const header = request.headers.get("if-none-match");
  if (!header) return false;
  const bare = etag.replace(/^W\//, "");
  return header.split(",").some((candidate) => {
    const trimmed = candidate.trim();
    return trimmed === "*" || trimmed === etag || trimmed.replace(/^W\//, "") === bare;
  });
}

// Snapshot values are re-read far more often than they change (publishes are
// batch runs), and each read previously paid a full-body JSON.parse plus a
// SHA-256 over multi-MB payloads. Cache {value, etag} briefly; TTL matches the
// manifest cache so post-publish staleness stays bounded by the same bound.
type KvCacheEntry = { value: unknown; etag: string; expires: number };
let kvJsonCache = new Map<string, KvCacheEntry>();

export async function kvJson(env: Env, key: string): Promise<{ value: unknown; etag: string } | null> {
  const now = Date.now();
  const cached = kvJsonCache.get(key);
  if (cached && now < cached.expires) return cached;
  const raw = await env.SNAPSHOT.get(key);
  if (raw === null) {
    if (cached) return cached;
    return null;
  }
  const entry: KvCacheEntry = {
    value: JSON.parse(raw),
    etag: `"${(await sha256Hex(raw)).slice(0, 32)}"`,
    expires: now + MANIFEST_TTL_MS,
  };
  kvJsonCache.set(key, entry);
  return entry;
}

function withHeaders(body: string, status: number, extra: HeadersInit): Response {
  return new Response(body, {
    status,
    headers: {
      "content-type": "application/json",
      "x-content-type-options": "nosniff",
      "referrer-policy": "strict-origin-when-cross-origin",
      ...extra,
    },
  });
}

/** 304s should re-prime downstream caches (RFC 9110): echo validators + TTL. */
function notModified(baseHeaders: Record<string, string>, etag: string): Response {
  return new Response(null, {
    status: 304,
    headers: { ...baseHeaders, etag, "x-content-type-options": "nosniff" },
  });
}

export async function getManifest(env: Env): Promise<Manifest | null> {
  const now = Date.now();
  if (manifestCache.value && now < manifestCache.expires) return manifestCache.value;
  try {
    const raw = await env.SNAPSHOT.get("manifest");
    if (raw === null) return manifestCache.value; // stale beats a spurious 404
    const value = JSON.parse(raw) as Manifest;
    const etag = `"${(await sha256Hex(raw)).slice(0, 32)}"`;
    manifestCache = { value, etag, expires: now + MANIFEST_TTL_MS };
    return value;
  } catch {
    return manifestCache.value; // malformed publish: keep last known-good
  }
}

// ---------------------------------------------------------------------------
// Agent discovery surface
// ---------------------------------------------------------------------------

/** RFC 8288 Link headers advertised on every HTML response. */
const HOME_LINK_HEADERS = [
  '</.well-known/api-catalog>; rel="api-catalog"',
  '</openapi.json>; rel="service-desc"',
  `</.well-known/agent-skills/${DATA_SKILL_NAME}/SKILL.md>; rel="service-doc"`,
  '</sitemap.xml>; rel="sitemap"',
  '</.well-known/ai-catalog.json>; rel="describedby"',
].join(", ");

function discoveryHeaders(contentType: string, extra: Record<string, string> = {}): Headers {
  const headers = new Headers({ "content-type": contentType });
  headers.set("cache-control", DISCOVERY_CACHE_CONTROL);
  headers.set("access-control-allow-origin", "*");
  headers.set("access-control-allow-methods", "GET, POST, OPTIONS");
  headers.set("access-control-allow-headers", "content-type, mcp-session-id, last-event-id");
  for (const [key, value] of Object.entries(extra)) headers.set(key, value);
  return headers;
}

function robotsTxt(origin: string): Response {
  const body = [
    `# Urban Signal edge dashboard — ${origin}`,
    "User-agent: *",
    "Allow: /",
    "",
    "# Machine-readable discovery",
    `Sitemap: ${origin}/sitemap.xml`,
    `Agentmap: ${origin}/.well-known/ai-catalog.json`,
    "",
  ].join("\n");
  return new Response(body, { status: 200, headers: discoveryHeaders("text/plain; charset=utf-8") });
}

/**
 * Canonical URLs: the dashboard root plus one deep link per metro published in
 * the KV snapshot manifest (?city=<id> is validated against CITY_CONFIGS by the
 * client), so the sitemap tracks every publish automatically.
 */
async function sitemapXml(env: Env, origin: string): Promise<Response> {
  const manifest = await getManifest(env);
  const lastmod = manifest?.generated_at
    ? `<lastmod>${manifest.generated_at.slice(0, 10)}</lastmod>`
    : "";
  const locations = [
    `${origin}/`,
    ...(manifest?.cities ?? []).map((city) => `${origin}/?city=${city}`),
  ];
  const entries = locations.map((loc) => `  <url><loc>${loc}</loc>${lastmod}</url>`).join("\n");
  const body = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${entries}\n</urlset>\n`;
  return new Response(body, { status: 200, headers: discoveryHeaders("application/xml; charset=utf-8") });
}

function apiCatalog(origin: string): Response {
  const body = JSON.stringify(
    {
      linkset: [
        {
          anchor: `${origin}/api/v1`,
          "service-desc": [
            { href: `${origin}/openapi.json`, type: "application/vnd.oai.openapi+json" },
          ],
          "service-doc": [
            {
              href: `${origin}/.well-known/agent-skills/${DATA_SKILL_NAME}/SKILL.md`,
              type: "text/markdown",
            },
          ],
          status: [{ href: `${origin}/health`, type: "application/json" }],
          describedby: [{ href: `${origin}/.well-known/ai-catalog.json`, type: "application/json" }],
        },
      ],
    },
    null,
    2
  );
  return new Response(`${body}\n`, {
    status: 200,
    headers: discoveryHeaders("application/linkset+json"),
  });
}

/**
 * RFC 9728 Protected Resource Metadata. The edge API is public and read-only:
 * no authorization server issues tokens for it, and the empty
 * authorization_servers array states that formally.
 */
function protectedResourceMetadata(origin: string): Response {
  const body = JSON.stringify(
    {
      resource: `${origin}/`,
      authorization_servers: [],
      scopes_supported: [],
      bearer_methods_supported: ["header"],
      resource_documentation: `${origin}/auth.md`,
    },
    null,
    2
  );
  return new Response(`${body}\n`, {
    status: 200,
    headers: discoveryHeaders("application/json"),
  });
}

function authMd(): Response {
  const body = `# auth.md — Urban Signal Edge Dashboard

Urban Signal's dashboard data API is **public and read-only**. There are no
protected resources, no user accounts, and no agent registration step.

## Agent audience

Autonomous agents and AI assistants consuming precomputed geospatial snapshots:
submarket structure, H3 grids, commercial catalyst (LIMS) scores, and point
predictions for supported US metropolitan regions.

## Authentication methods

- None required. Every endpoint accepts anonymous HTTPS requests.

## Registration / provisioning

- None. Start calling immediately:
  - \`GET /api/v1/cities\` — list supported metros.
  - \`GET /openapi.json\` — full machine-readable API contract.
  - \`/.well-known/api-catalog\` — RFC 9727 service catalog.

## Credentials

- Not issued and not required. There are no OAuth flows on this host; the
  RFC 9728 document at \`/.well-known/oauth-protected-resource\` advertises an
  empty \`authorization_servers\` list as the formal statement.

## Etiquette

- Snapshot responses are CDN-cacheable (\`max-age=300\`) and carry ETags —
  send \`If-None-Match\` rather than re-fetching full payloads.
- Check \`x-snapshot-created\` to see when the current batch was published.
`;
  return new Response(body, { status: 200, headers: discoveryHeaders("text/markdown; charset=utf-8") });
}

// ---------------------------------------------------------------------------
// MCP Streamable HTTP server (read-only tools over the KV snapshots)
// ---------------------------------------------------------------------------

interface McpToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

const MCP_TOOLS: McpToolDefinition[] = [
  {
    name: "list_cities",
    description:
      "List the metropolitan regions that have precomputed Urban Signal snapshot data.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "get_submarkets",
    description: "List submarket identifiers and borough/division groupings for one metro.",
    inputSchema: {
      type: "object",
      properties: {
        city_id: { type: "string", description: "City identifier from list_cities (aliases like 'sf' or 'dc' are accepted)." },
        borough: { type: "string", description: "Optional borough/division filter (case-insensitive; honors the same normalization as the HTTP API)." },
      },
      required: ["city_id"],
      additionalProperties: false,
    },
  },
  {
    name: "get_catalysts",
    description:
      "Get the strongest commercial catalyst cells (H3 index + LIMS score) for one metro.",
    inputSchema: {
      type: "object",
      properties: {
        city_id: { type: "string", description: "City identifier from list_cities." },
        min_lims: { type: "number", minimum: 0, maximum: 100, description: "Minimum LIMS score filter." },
        // PRODUCT DECISION (US-190): MCP adopts the HTTP/manifest limit policy —
        // default 50, hard max 500. Keep these in sync with snapshot.ts.
        limit: { type: "integer", minimum: 1, maximum: CATALYST_MAX_LIMIT, description: `Maximum cells returned (default ${CATALYST_DEFAULT_LIMIT}).` },
        borough: { type: "string", description: "Optional borough/division filter." },
      },
      required: ["city_id"],
      additionalProperties: false,
    },
  },
  {
    name: "predict_cell",
    description:
      "Look up the precomputed catalyst forecast (and SHAP attributions unless suppressed) for one H3 cell.",
    inputSchema: {
      type: "object",
      properties: {
        h3_index: { type: "string", description: "Resolution-9 H3 cell index." },
        include_shap: { type: "boolean", description: "Include SHAP attributions (default true)." },
      },
      required: ["h3_index"],
      additionalProperties: false,
    },
  },
];

interface JsonRpcMessage {
  jsonrpc?: string;
  id?: string | number | null;
  method?: string;
  params?: Record<string, unknown>;
}

function rpcResult(id: string | number | null, result: unknown): Response {
  return new Response(JSON.stringify({ jsonrpc: "2.0", id, result }), {
    status: 200,
    headers: discoveryHeaders("application/json"),
  });
}

function rpcError(id: string | number | null, code: number, message: string): Response {
  return new Response(JSON.stringify({ jsonrpc: "2.0", id, error: { code, message } }), {
    status: 200,
    headers: discoveryHeaders("application/json"),
  });
}

function strParam(params: Record<string, unknown>, key: string): string | null {
  const value = params[key];
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

function numParam(params: Record<string, unknown>, key: string): number | null {
  const value = params[key];
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) {
    return Number(value);
  }
  return null;
}

function boolParam(params: Record<string, unknown>, key: string, fallback: boolean): boolean {
  const value = params[key];
  return typeof value === "boolean" ? value : fallback;
}

function trimCatalyst(entry: CatalystEntry): Record<string, unknown> {
  const out: Record<string, unknown> = {
    h3_index: entry.h3_index,
    lims_score: Number(entry.lims_score),
  };
  if (!Number.isFinite(out.lims_score as number)) out.lims_score = null;
  if (entry.borough !== undefined) out.borough = entry.borough;
  return out;
}

async function callTool(
  params: Record<string, unknown>,
  env: Env
): Promise<{ content: { type: string; text: string }[]; isError?: boolean }> {
  const toolName = strParam(params, "name");
  const args = (params.arguments ?? {}) as Record<string, unknown>;

  const text = async (payload: unknown): Promise<string> =>
    JSON.stringify(payload, null, 2);

  switch (toolName) {
    case "list_cities": {
      const manifest = await getManifest(env);
      const cities = manifest?.cities ?? [];
      return { content: [{ type: "text", text: await text({ count: cities.length, cities }) }] };
    }
    case "get_submarkets": {
      const manifest = await getManifest(env);
      const city = normalizeCity(strParam(args, "city_id"), manifest);
      if (!city) {
        return {
          content: [{ type: "text", text: `Unsupported city_id '${safeEcho(args.city_id, 64)}'. Call list_cities first.` }],
          isError: true,
        };
      }
      // PRODUCT DECISION (US-190): MCP now honors `borough`, matching the HTTP
      // adapter, via the shared snapshot query.
      const result = await querySubmarkets(env, {
        city,
        borough: strParam(args, "borough") ?? undefined,
      });
      if ("error" in result) {
        return { content: [{ type: "text", text: result.error }], isError: true };
      }
      const submarkets = Object.entries(result.submarkets).map(([id, meta]) => ({
        id,
        borough: (meta as Record<string, unknown>).borough ?? null,
      }));
      return {
        content: [{ type: "text", text: await text({ city_id: result.city_id, count: submarkets.length, submarkets }) }],
      };
    }
    case "get_catalysts": {
      const manifest = await getManifest(env);
      const city = normalizeCity(strParam(args, "city_id"), manifest);
      if (!city) {
        return {
          content: [{ type: "text", text: `Unsupported city_id '${safeEcho(args.city_id, 64)}'. Call list_cities first.` }],
          isError: true,
        };
      }
      // Route through the shared snapshot query. The limit/max/min_lims/borough
      // policy is identical to HTTP by PRODUCT DECISION (US-190); the adapter
      // keeps only its own transport envelope and trim shape.
      const result = await queryCatalysts(env, {
        city,
        minLims: numParam(args, "min_lims") ?? undefined,
        limit: numParam(args, "limit") ?? undefined,
        borough: strParam(args, "borough") ?? undefined,
      });
      if ("error" in result) {
        // Reachable error here is the out-of-range min_lims message, which
        // snapshot returns verbatim; unsupported-city is handled above.
        return { content: [{ type: "text", text: result.error }], isError: true };
      }
      return {
        content: [
          {
            type: "text",
            text: await text({
              city_id: result.city_id,
              count: result.catalysts.length,
              threshold: result.threshold,
              catalysts: result.catalysts.map(trimCatalyst),
            }),
          },
        ],
      };
    }
    case "predict_cell": {
      const h3Index = strParam(args, "h3_index");
      if (!h3Index) {
        return {
          content: [{ type: "text", text: "'h3_index' (resolution-9 H3 cell) is required." }],
          isError: true,
        };
      }
      // SHAP strip trigger is identical to the HTTP adapter: only when
      // include_shap is explicitly false.
      const result = await lookupPrediction(env, {
        h3Index,
          includeShap: boolParam(args, "include_shap", true) ? undefined : false,
        });
        if ("error" in result) {
          return { content: [{ type: "text", text: String((result as Record<string, unknown>).error) }], isError: true };
        }
      return { content: [{ type: "text", text: await text(result) }] };
    }
    default:
      return { content: [{ type: "text", text: `Unknown tool '${safeEcho(toolName, 64)}'.` }], isError: true };
  }
}

function mcpCorsHeaders(): Record<string, string> {
  const h = discoveryHeaders("application/json");
  return Object.fromEntries([...h.entries()].filter(([k]) => k.startsWith("access-control")));
}

async function mcpEndpoint(request: Request, env: Env): Promise<Response> {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: mcpCorsHeaders() });
  }
  if (request.method === "GET") {
    return jsonError(405, "Urban Signal MCP: POST JSON-RPC 2.0 messages to this endpoint (Streamable HTTP).");
  }
  if (request.method !== "POST") {
    return jsonError(405, "Method Not Allowed");
  }

  let message: JsonRpcMessage;
  try {
    message = (await request.json()) as JsonRpcMessage;
  } catch {
    return new Response(
      JSON.stringify({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }),
      { status: 400, headers: { "content-type": "application/json" } }
    );
  }

  // JSON-RPC batch arrays are out of scope for this read-only server.
  if (Array.isArray(message)) {
    return new Response(
      JSON.stringify({ jsonrpc: "2.0", id: null, error: { code: -32600, message: "Invalid Request: batch arrays are not supported" } }),
      { status: 400, headers: discoveryHeaders("application/json") }
    );
  }

  // Notifications (no id) take no reply beyond acceptance.
  if (message.id === undefined || message.id === null) {
    return new Response(null, { status: 202 });
  }

  try {
    switch (message.method) {
      case "initialize":
        return rpcResult(message.id, {
          protocolVersion:
            typeof message.params?.protocolVersion === "string"
              ? message.params.protocolVersion
              : MCP_PROTOCOL_VERSION,
          capabilities: { tools: { listChanged: false } },
          serverInfo: {
            name: MCP_SERVER_NAME,
            title: "Urban Signal Geospatial Data",
            version: APP_VERSION,
          },
          instructions:
            "Read-only access to precomputed urban catalyst snapshots. Call list_cities first, then get_submarkets/get_catalysts per metro, or predict_cell with a resolution-9 H3 index.",
        });
      case "ping":
        return rpcResult(message.id, {});
      case "tools/list":
        return rpcResult(message.id, { tools: MCP_TOOLS });
      case "tools/call": {
        const params = message.params ?? {};
        return rpcResult(message.id, await callTool(params, env));
      }
      default:
        return rpcError(message.id, -32601, `Method not found: ${safeEcho(message.method, 64)}`);
    }
  } catch (err) {
    console.error("mcp internal error:", err);
    return rpcError(message.id, -32603, "Internal error");
  }
}

function mcpServerCard(origin: string): Response {
  const body = JSON.stringify(
    {
      serverInfo: {
        name: MCP_SERVER_NAME,
        title: "Urban Signal Geospatial Data",
        version: APP_VERSION,
      },
      description:
        "Read-only MCP server exposing precomputed urban catalyst snapshots: supported metros, submarket structure, H3 catalyst cells (LIMS scores), and point predictions.",
      transport: {
        type: "streamable-http",
        endpoint: `${origin}/mcp`,
      },
      capabilities: {
        tools: { listChanged: false },
      },
      tools: MCP_TOOLS.map(({ name, description }) => ({ name, description })),
    },
    null,
    2
  );
  return new Response(`${body}\n`, {
    status: 200,
    headers: discoveryHeaders("application/json"),
  });
}

// ---------------------------------------------------------------------------
// Agent Skills discovery (RFC v0.2.0)
// ---------------------------------------------------------------------------

interface SkillArtifact {
  name: string;
  description: string;
  body: string;
}

const DATA_API_SKILL: SkillArtifact = {
  name: DATA_SKILL_NAME,
  description:
    "Query Urban Signal's public geospatial snapshot API for supported US metros: submarket structure, H3 grid, top commercial catalyst cells (LIMS scores), and point forecasts. Use when an agent needs real-estate catalyst data without a browser.",
  body: `---
name: urban-signal-data-api
description: Query Urban Signal's public geospatial snapshot API for supported US metros — submarket structure, H3 grid, top commercial catalyst cells (LIMS scores), and point forecasts. Use when an agent needs real-estate catalyst data without a browser.
---

# Urban Signal Data API

Public, read-only, unauthenticated JSON API on Cloudflare Workers. All URLs
below are relative to the deployment origin (production:
https://us-dash.harlanljones.com).

## Endpoints

### GET /api/v1/cities
Catalog of supported metropolitan regions.

    curl https://us-dash.harlanljones.com/api/v1/cities

### GET /api/v1/submarkets?city_id=nyc[&borough=MANHATTAN]
Submarket dictionary for one metro, optionally filtered by borough/division.

### GET /api/v1/grid?city_id=chicago
Full H3 (resolution 9) grid with per-cell metrics. Large payload — prefer ETags.

### GET /api/v1/manifest
Snapshot metadata: supported metros with camera bboxes/centers, the res-5 H3
grid-tile index (parent -> count/cities/bbox), and publish thresholds.

### GET /api/v1/gridtiles?parents=852830bbfffffff,852ab2c3fffffff
Viewport tiles for lazy loading: merged GeoJSON for up to 32 res-5 parent
indexes. Valid parents come from \`tile_index\` in /api/v1/manifest. Each cell
carries \`<metric>_metro_pct\` and \`<metric>_national_pct\` percentile ranks so
all metros render on one comparable color scale.

### GET /api/v1/catalysts/all
Every metro's active catalysts in one document, attributed with city_id/city_name
and sorted by descending LIMS score.

### GET /api/v1/catalysts?city_id=austin&min_lims=90&limit=25
Strongest commercial catalyst cells. \`min_lims\` defaults to the publish
threshold (84); \`limit\` caps at 500.

### POST /api/v1/predict
Point forecast for one cell.

    curl -X POST https://us-dash.harlanljones.com/api/v1/predict \\
      -H 'content-type: application/json' \\
      -d '{"h3_index":"892a10708b7ffff","include_shap":true}'

\`h3_index\` is a resolution-9 H3 cell — derive it client-side from coordinates
with h3-js \`latLngToCell(lat, lng, 9)\`.

## Notes

- Snapshot endpoints return ETags; send \`If-None-Match\` to revalidate (304).
- \`x-snapshot-created\` dates the current batch publish.
- City aliases: \`sf\`→san_francisco, \`sea\`/\`king_county\`→seattle,
  \`la\`→los_angeles, \`philly\`→philadelphia, \`dc\`→washington_dc.
- Full contract: \`/openapi.json\` · Catalog: \`/.well-known/api-catalog\` ·
  Health: \`/health\`.
`,
};

const MCP_SKILL: SkillArtifact = {
  name: MCP_SKILL_NAME,
  description:
    "Connect an MCP client to Urban Signal's read-only Model Context Protocol server over Streamable HTTP to list metros, pull submarkets and catalyst cells, and look up H3 point predictions.",
  body: `---
name: urban-signal-mcp
description: Connect an MCP client to Urban Signal's read-only Model Context Protocol server over Streamable HTTP to list metros, pull submarkets and catalyst cells, and look up H3 point predictions.
---

# Urban Signal MCP Server

- Transport: Streamable HTTP (JSON-RPC 2.0) at \`/mcp\`.
- Protocol version: 2025-06-18.
- Server card: \`/.well-known/mcp/server-card.json\`.
- Authentication: none (public read-only data).

## Tools

- \`list_cities()\`
- \`get_submarkets(city_id)\`
- \`get_catalysts(city_id, min_lims?, limit?, borough?)\`
- \`predict_cell(h3_index, include_shap?)\`

## Handshake example

    POST /mcp
    content-type: application/json

    {"jsonrpc":"2.0","id":1,"method":"initialize","params":{
      "protocolVersion":"2025-06-18","capabilities":{},
      "clientInfo":{"name":"my-agent","version":"0.1"}}}

Then POST \`notifications/initialized\` (no id — expect HTTP 202), fetch
\`tools/list\`, and invoke with \`tools/call\`. Tool results arrive as
\`result.content[0].text\` JSON documents; failures carry \`isError: true\`.
`,
};

const SKILL_ARTIFACTS: SkillArtifact[] = [DATA_API_SKILL, MCP_SKILL];

async function agentSkillsIndex(origin: string): Promise<Response> {
  const skills = await Promise.all(
    SKILL_ARTIFACTS.map(async (skill) => ({
      name: skill.name,
      type: "skill-md",
      description: skill.description,
      url: `${origin}/.well-known/agent-skills/${skill.name}/SKILL.md`,
      digest: `sha256:${await sha256Hex(skill.body)}`,
    }))
  );
  const body = JSON.stringify(
    {
      $schema: "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
      skills,
    },
    null,
    2
  );
  return new Response(`${body}\n`, {
    status: 200,
    headers: discoveryHeaders("application/json"),
  });
}

function agentSkillDoc(skillName: string): Response {
  const skill = SKILL_ARTIFACTS.find((candidate) => candidate.name === skillName);
  if (!skill) {
    return jsonError(404, `Unknown skill '${skillName}'. See /.well-known/agent-skills/index.json.`);
  }
  return new Response(skill.body, {
    status: 200,
    headers: discoveryHeaders("text/markdown; charset=utf-8"),
  });
}

// ---------------------------------------------------------------------------
// ARD capability manifest
// ---------------------------------------------------------------------------

function aiCatalog(origin: string): Response {
  const host = new URL(origin).hostname;
  const body = JSON.stringify(
    {
      specVersion: "1.0",
      host: {
        displayName: "Urban Signal",
        identifier: `did:web:${host}`,
      },
      entries: [
        {
          identifier: `urn:air:${host}:api:data-api`,
          displayName: "Urban Signal Edge Data API",
          type: "application/vnd.oai.openapi+json",
          url: `${origin}/openapi.json`,
          representativeQueries: [
            "which metros does Urban Signal cover",
            "get the OpenAPI contract for the catalyst forecast API",
          ],
        },
        {
          identifier: `urn:air:${host}:mcp:dashboard-tools`,
          displayName: "Urban Signal MCP Server",
          type: "application/mcp-server-card+json",
          url: `${origin}/.well-known/mcp/server-card.json`,
          representativeQueries: [
            "top commercial catalyst cells in New York",
            "forecast for H3 cell 892a10708b7ffff",
          ],
        },
        {
          identifier: `urn:air:${host}:data:cities`,
          displayName: "Supported Metropolitan Regions",
          type: "application/json",
          url: `${origin}/api/v1/cities`,
          representativeQueries: [
            "is Chicago available on Urban Signal",
            "list cities with catalyst snapshot data",
          ],
        },
        {
          identifier: `urn:air:${host}:data:catalysts`,
          displayName: "Commercial Catalyst Cells Feed",
          type: "application/json",
          url: `${origin}/api/v1/catalysts?city_id=nyc&limit=25`,
          representativeQueries: [
            "strongest retail catalyst scores in Manhattan",
            "which H3 cells exceed a LIMS score of 90 in Austin",
          ],
        },
        {
          identifier: `urn:air:${host}:discovery:agent-skills`,
          displayName: "Agent Skills Index",
          type: "application/json",
          url: `${origin}/.well-known/agent-skills/index.json`,
          representativeQueries: [
            "how do I query the Urban Signal API programmatically",
            "connect an MCP client to Urban Signal",
          ],
        },
      ],
    },
    null,
    2
  );
  return new Response(`${body}\n`, {
    status: 200,
    headers: discoveryHeaders("application/json"),
  });
}

// ---------------------------------------------------------------------------
// OpenAPI contract for the edge data API
// ---------------------------------------------------------------------------

function openApiResponse(description: string): Record<string, unknown> {
  return { description, content: { "application/json": { schema: { type: "object" } } } };
}

const CITY_ID_PARAM: Record<string, unknown> = {
  name: "city_id",
  in: "query",
  required: false,
  schema: { type: "string", default: "nyc" },
  description:
    "Metropolitan region identifier (see /api/v1/cities). Aliases accepted: sf, sea, king_county, la, philly, dc.",
};

function openApiSpec(origin: string): Response {
  const spec = {
    openapi: "3.1.0",
    info: {
      title: "Urban Signal Edge Data API",
      summary: "Precomputed urban catalyst snapshots served from Cloudflare Workers KV.",
      description:
        "Read-only, unauthenticated mirror of the FastAPI serving API, backed by batch-published snapshots. Data refreshes on each publish; check x-snapshot-created.",
      version: APP_VERSION,
    },
    servers: [{ url: origin }],
    paths: {
      "/health": {
        get: {
          operationId: "getHealth",
          summary: "Liveness/readiness status with snapshot provenance.",
          responses: { "200": openApiResponse("Service status document.") },
        },
      },
      "/api/v1/cities": {
        get: {
          operationId: "listCities",
          summary: "Catalog of supported metropolitan regions.",
          responses: { "200": openApiResponse("City catalog.") },
        },
      },
      "/api/v1/manifest": {
        get: {
          operationId: "getManifest",
          summary:
            "Snapshot metadata: metros with camera bboxes, res-5 grid-tile index, thresholds.",
          responses: { "200": openApiResponse("Manifest document.") },
        },
      },
      "/api/v1/gridtiles": {
        get: {
          operationId: "getGridTiles",
          summary: "Fetch viewport tiles by comma-separated res-5 H3 parent indexes (max 32).",
          parameters: [
            {
              name: "parents",
              in: "query",
              required: true,
              schema: { type: "string" },
              description:
                "Comma-separated 15-char hex res-5 H3 parent indexes. Discover valid parents via /api/v1/manifest tile_index.",
            },
          ],
          responses: {
            "200": openApiResponse("Merged FeatureCollection across requested tiles; lists missing parents."),
            "304": { description: "ETag match — tiles unchanged." },
            "400": openApiResponse("Missing/malformed parents or over the per-request cap."),
          },
        },
      },
      "/api/v1/national": {
        get: {
          operationId: "getNationalIndex",
          summary:
            "National hex layer index: per-resolution chunk inventories (parents, sizes, sha256).",
          responses: {
            "200": openApiResponse("National layer index document."),
            "304": { description: "ETag match — index unchanged." },
            "404": openApiResponse("No national layer snapshot published."),
          },
        },
      },
      "/api/v1/national/{res}": {
        get: {
          operationId: "getNationalChunks",
          summary:
            "Fetch national hex chunk rows by resolution and comma-separated res-3 parent indexes (max 64).",
          parameters: [
            {
              name: "res",
              in: "path",
              required: true,
              schema: { type: "integer", enum: [4, 5, 6] },
              description: "National hex resolution.",
            },
            {
              name: "parents",
              in: "query",
              required: true,
              schema: { type: "string" },
              description:
                "Comma-separated res-3 H3 parent indexes. Discover valid parents via /api/v1/national.",
            },
          ],
          responses: {
            "200": openApiResponse("Merged chunk rows across requested parents; lists missing parents."),
            "304": { description: "ETag match — chunks unchanged." },
            "400": openApiResponse("Invalid resolution, missing/malformed parents, or over the per-request cap."),
          },
        },
      },
      "/api/v1/submarkets": {
        get: {
          operationId: "listSubmarkets",
          summary: "Submarket dictionary for one metro.",
          parameters: [
            CITY_ID_PARAM,
            {
              name: "borough",
              in: "query",
              required: false,
              schema: { type: "string" },
              description: "Filter to one borough/division (case-insensitive).",
            },
          ],
          responses: {
            "200": openApiResponse("Submarket payload (supports ETag revalidation)."),
            "304": { description: "ETag match — snapshot unchanged." },
            "400": openApiResponse("Unsupported city_id."),
            "404": openApiResponse("No snapshot published for the metro."),
          },
        },
      },
      "/api/v1/grid": {
        get: {
          operationId: "getGrid",
          summary: "Full H3 (resolution 9) grid with per-cell metrics for one metro.",
          parameters: [CITY_ID_PARAM],
          responses: {
            "200": openApiResponse("Grid payload (large; supports ETag revalidation)."),
            "304": { description: "ETag match — snapshot unchanged." },
            "400": openApiResponse("Unsupported city_id."),
            "404": openApiResponse("No grid snapshot published for the metro."),
          },
        },
      },
      "/api/v1/catalysts": {
        get: {
          operationId: "getCatalysts",
          summary: "Strongest commercial catalyst cells (H3 + LIMS score) for one metro.",
          parameters: [
            CITY_ID_PARAM,
            {
              name: "min_lims",
              in: "query",
              required: false,
              schema: { type: "number", minimum: 0, maximum: 100 },
              description: "Minimum LIMS score; defaults to the publish threshold (84).",
            },
            {
              name: "limit",
              in: "query",
              required: false,
              schema: { type: "integer", minimum: 1, maximum: 500, default: 50 },
            },
            {
              name: "borough",
              in: "query",
              required: false,
              schema: { type: "string" },
              description: "Borough/division filter (case-insensitive).",
            },
          ],
          responses: {
            "200": openApiResponse("Catalyst payload."),
            "304": { description: "ETag match — snapshot unchanged." },
            "400": openApiResponse("Unsupported city_id."),
            "422": openApiResponse("min_lims outside [0, 100]."),
            "404": openApiResponse("No catalyst snapshot published for the metro."),
          },
        },
      },
      "/api/v1/predict": {
        post: {
          operationId: "predictCell",
          summary: "Point lookup of a precomputed cell prediction.",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    h3_index: { type: "string", description: "Resolution-9 H3 cell index." },
                    include_shap: {
                      type: "boolean",
                      default: true,
                      description: "Set false to omit SHAP attributions.",
                    },
                  },
                  required: ["h3_index"],
                },
              },
            },
          },
          responses: {
            "200": openApiResponse("Prediction document."),
            "400": openApiResponse("Missing h3_index or malformed body."),
            "404": openApiResponse("No precomputed prediction for the cell."),
            "405": openApiResponse("Method not allowed (POST only)."),
          },
        },
      },
      "/api/v1/catalysts/all": {
        get: {
          operationId: "getAllCatalysts",
          summary:
            "Every metro's active catalysts in one attributed, LIMS-ranked feed document.",
          responses: {
            "200": openApiResponse("Combined catalyst payload (supports ETag revalidation)."),
            "304": { description: "ETag match — snapshot unchanged." },
            "404": openApiResponse("No combined catalyst snapshot published."),
          },
        },
      },
    },
  };
  return new Response(`${JSON.stringify(spec, null, 2)}\n`, {
    status: 200,
    headers: discoveryHeaders("application/vnd.oai.openapi+json"),
  });
}

// ---------------------------------------------------------------------------
// Markdown content negotiation for the homepage
// ---------------------------------------------------------------------------

function acceptsMarkdown(acceptHeader: string): boolean {
  return acceptHeader
    .split(",")
    .some((part) => part.trim().toLowerCase().startsWith("text/markdown"));
}

async function homeMarkdown(env: Env, origin: string): Promise<Response> {
  const manifest = await getManifest(env);
  const cities = manifest?.cities ?? [];
  const cityLines = cities.map((city) => `- \`${origin}/?city=${city}\``).join("\n");
  const body = `# Urban Signal — Real-Time Geospatial Intelligence

Urban Signal is a commercial catalyst forecasting engine: batch pipelines score
H3 (resolution 9) cells across US metropolitan regions and the edge worker
serves the precomputed snapshots. This page is normally an interactive MapLibre
dashboard; this markdown rendering describes the same surface for agents.

## Dashboard deep links

- \`${origin}/\` — dashboard (defaults to the last-detected metro)
${cityLines}

## Data API (no authentication required)

- \`GET ${origin}/api/v1/cities\` — supported metros.
- \`GET ${origin}/api/v1/manifest\` — snapshot metadata incl. res-5 tile index.
- \`GET ${origin}/api/v1/gridtiles?parents=<csv>\` — viewport tiles (max 32 parents).
- \`GET ${origin}/api/v1/national\` — national hex layer index (per-res chunk inventories).
- \`GET ${origin}/api/v1/national/{res}?parents=<csv>\` — national hex rows (res 4/5/6, max 64 res-3 parents).
- \`GET ${origin}/api/v1/submarkets?city_id=<id>[&borough=<name>]\` — submarket dictionary.
- \`GET ${origin}/api/v1/grid?city_id=<id>\` — full H3 grid (large).
- \`GET ${origin}/api/v1/catalysts/all\` — all metros' catalysts, attributed + ranked.
- \`GET ${origin}/api/v1/catalysts?city_id=<id>&min_lims=84&limit=50\` — top catalyst cells.
- \`POST ${origin}/api/v1/predict\` — body \`{"h3_index":"<r9-cell>","include_shap":true}\`.

Snapshot endpoints return ETags and an \`x-snapshot-created\` publish stamp.

## For agents

- OpenAPI contract: \`${origin}/openapi.json\`
- API catalog (RFC 9727): \`${origin}/.well-known/api-catalog\`
- MCP server: \`${origin}/mcp\` (card: \`${origin}/.well-known/mcp/server-card.json\`)
- Skills index: \`${origin}/.well-known/agent-skills/index.json\`
- Capability manifest: \`${origin}/.well-known/ai-catalog.json\`
- Authentication: none — see \`${origin}/auth.md\`
- Health: \`${origin}/health\`
`;
  return new Response(body, {
    status: 200,
    headers: discoveryHeaders("text/markdown; charset=utf-8", {
      vary: "Accept",
      "x-markdown-tokens": String(Math.ceil(body.length / 4)),
    }),
  });
}

// ---------------------------------------------------------------------------
// Routing
// ---------------------------------------------------------------------------

async function serveSite(request: Request, env: Env, url: URL): Promise<Response> {
  const origin = url.origin;

  switch (url.pathname) {
    case "/robots.txt":
      return robotsTxt(origin);
    case "/sitemap.xml":
      return sitemapXml(env, origin);
    case "/auth.md":
      return authMd();
    case "/openapi.json":
      return openApiSpec(origin);
    case "/mcp":
      return mcpEndpoint(request, env);
    case "/.well-known/api-catalog":
      return apiCatalog(origin);
    case "/.well-known/oauth-protected-resource":
      return protectedResourceMetadata(origin);
    case "/.well-known/mcp/server-card.json":
      return mcpServerCard(origin);
    case "/.well-known/agent-skills/index.json":
      return agentSkillsIndex(origin);
    case "/.well-known/ai-catalog.json":
      return aiCatalog(origin);
    default:
      break;
  }

  if (url.pathname.startsWith("/.well-known/agent-skills/") && url.pathname.endsWith("/SKILL.md")) {
    const segments = url.pathname.split("/").filter(Boolean);
    // [.well-known, agent-skills, <name>, SKILL.md]
    if (segments.length === 4) return agentSkillDoc(segments[2]);
  }

  // Markdown content negotiation for the homepage.
  const wantsMarkdown =
    acceptsMarkdown(request.headers.get("accept") ?? "") &&
    (url.pathname === "/" || url.pathname === "/index.html");
  if (wantsMarkdown) return homeMarkdown(env, origin);

  const asset = await env.ASSETS.fetch(request);
  const contentType = asset.headers.get("content-type") ?? "";
  if (asset.ok) {
    const headers = new Headers(asset.headers);
    // Long-lived edge caching. The dashboard HTML (incl. its inline app script)
    // is immutable per deploy and safe to cache for a short window with
    // background revalidation; any other static asset gets a year-long cache.
    const isHtml = contentType.includes("text/html");
    if (isHtml) {
      headers.set("cache-control", "public, max-age=300, stale-while-revalidate=86400");
    } else if (/\.(css|js|mjs|svg|woff2?|ttf|png|jpe?g|webp|avif|gif|ico)(\?|$)/i.test(url.pathname)) {
      headers.set("cache-control", "public, max-age=31536000, immutable");
    }
    if (isHtml) {
      headers.set("link", HOME_LINK_HEADERS);
      headers.append("vary", "Accept");
      headers.set(
        "content-security-policy",
        [
          "default-src 'self'",
          "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net",
          "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
          "font-src 'self' https://fonts.gstatic.com",
          "img-src 'self' data: blob: https://*.arcgisonline.com https://unpkg.com",
          "connect-src 'self' https://*.arcgisonline.com",
          "worker-src 'self' blob:",
          "child-src 'self' blob:",
          "frame-ancestors 'self'",
          "base-uri 'self'",
          "form-action 'self'",
        ].join("; ")
      );
    }
    headers.set("x-content-type-options", "nosniff");
    if (!headers.has("referrer-policy")) headers.set("referrer-policy", "strict-origin-when-cross-origin");
    return new Response(asset.body, { status: asset.status, headers });
  }
  return asset;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    try {
      return await handleRequest(request, env);
    } catch (err) {
      console.error("unhandled worker error:", err);
      return jsonError(500, "Edge error: snapshot data temporarily unavailable.");
    }
  },
};

async function handleRequest(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);

    if (url.pathname === "/health" || url.pathname === "/live" || url.pathname === "/ready") {
      const manifest = await getManifest(env);
      return withHeaders(
        JSON.stringify({
          status: "healthy",
          service: SERVICE_NAME,
          version: APP_VERSION,
          environment: "production",
          snapshot_created: manifest?.generated_at ?? null,
        }),
        200,
        { "cache-control": "no-store", "x-snapshot-created": manifest?.generated_at ?? "" }
      );
    }

    if (!url.pathname.startsWith("/api/")) {
      return serveSite(request, env, url);
    }

    const manifest = await getManifest(env);
    const supportedCities = (manifest?.cities ?? []).join(", ");
    const baseHeaders: Record<string, string> = {
      "cache-control": CACHE_CONTROL,
      "x-snapshot-created": manifest?.generated_at ?? "",
    };

    try {
      // GET /api/v1/cities
      if (url.pathname === "/api/v1/cities") {
        const cities = manifest?.cities ?? [];
        return withHeaders(
          JSON.stringify({ count: cities.length, cities: cities.map((id) => ({ city_id: id })) }),
          200,
          baseHeaders
        );
      }

      // GET /api/v1/submarkets?city_id=
      if (url.pathname === "/api/v1/submarkets") {
        const city = normalizeCity(url.searchParams.get("city_id"), manifest);
        if (!city) {
          return jsonError(
            400,
            `Unsupported city_id '${safeEcho(url.searchParams.get("city_id"))}'. Supported cities: ${supportedCities}.`
          );
        }
        const entry = await kvJson(env, `submarkets/${city}`);
        if (!entry) return jsonError(404, `No snapshot for city '${city}'.`);
        if (etagMatches(request, entry.etag)) return notModified(baseHeaders, entry.etag);

        // Borough filter + normalization live in snapshot.ts; the adapter only
        // formats the transport payload from the query result (ETag/304 come
        // from the raw entry above).
        const result = await querySubmarkets(env, {
          city,
          borough: url.searchParams.get("borough") ?? undefined,
        });
        if ("error" in result) return jsonError(404, result.error);
        const payload = entry.value as Record<string, unknown>;
        Object.assign(payload, {
          city_id: result.city_id,
          count: Object.keys(result.submarkets).length,
          submarkets: result.submarkets,
        });
        return withHeaders(JSON.stringify(payload), 200, {
          ...baseHeaders,
          etag: entry.etag,
        });
      }

      // GET /api/v1/grid?city_id=
      if (url.pathname === "/api/v1/grid") {
        const city = normalizeCity(url.searchParams.get("city_id"), manifest);
        if (!city) {
          return jsonError(
            400,
            `Unsupported city_id '${safeEcho(url.searchParams.get("city_id"))}'. Supported cities: ${supportedCities}.`
          );
        }
        const entry = await kvJson(env, `grid/${city}`);
        if (!entry) return jsonError(404, `No grid snapshot for city '${city}'.`);
        if (etagMatches(request, entry.etag)) return notModified(baseHeaders, entry.etag);
        return withHeaders(JSON.stringify(entry.value), 200, {
          ...baseHeaders,
          etag: entry.etag,
        });
      }

      // GET /api/v1/catalysts?city_id=&min_lims=&limit=&borough=&resolution=
      if (url.pathname === "/api/v1/catalysts") {
        const city = normalizeCity(url.searchParams.get("city_id"), manifest);
        if (!city) {
          return jsonError(
            400,
            `Unsupported city_id '${safeEcho(url.searchParams.get("city_id"))}'. Supported cities: ${supportedCities}.`
          );
        }
        // Transport parsing only. The min_lims/limit/borough policy, default
        // source, bounding, and filter/slice all live in snapshot.ts (PRODUCT
        // DECISION US-190); the adapter keeps the 422/404 envelope + wording.
        const entry = await kvJson(env, `catalysts/${city}`);
        if (!entry) return jsonError(404, `No catalyst snapshot for city '${city}'.`);
        if (etagMatches(request, entry.etag)) return notModified(baseHeaders, entry.etag);

        const minLimsRaw = url.searchParams.get("min_lims");
        const minLims =
          minLimsRaw !== null && minLimsRaw.trim() !== "" ? Number(minLimsRaw) : undefined;
        const limitRaw = url.searchParams.get("limit");
        const limit =
          limitRaw !== null && limitRaw.trim() !== "" && Number.isInteger(Number(limitRaw))
            ? Number(limitRaw)
            : undefined;

        const result = await queryCatalysts(env, {
          city,
          minLims,
          limit,
          borough: url.searchParams.get("borough") ?? undefined,
        });
        if ("error" in result) return jsonError(422, result.error);
        const payload: CatalystPayload = {
          city_id: result.city_id,
          count: result.catalysts.length,
          threshold: result.threshold,
          borough: result.borough,
          catalysts: result.catalysts,
        };
        return withHeaders(JSON.stringify(payload), 200, {
          ...baseHeaders,
          etag: entry.etag,
        });
      }

      // GET /api/v1/manifest — snapshot metadata: metros, tile index, thresholds
      if (url.pathname === "/api/v1/manifest") {
        if (!manifest) return jsonError(404, "No snapshot manifest published.");
        let etag = manifestCache.etag;
        if (!etag || manifestCache.value !== manifest) {
          etag = `"${(await sha256Hex(JSON.stringify(manifest))).slice(0, 32)}"`;
          manifestCache = { value: manifest, etag, expires: manifestCache.expires };
        }
        if (etagMatches(request, etag)) return notModified(baseHeaders, etag);
        return withHeaders(JSON.stringify(manifest), 200, {
          ...baseHeaders,
          etag,
        });
      }

      // GET /api/v1/gridtiles?parents=<h3-res5-parents-csv>
      // Viewport lazy-loading units produced by the batch snapshot builder.
      if (url.pathname === "/api/v1/gridtiles") {
        const rawParents = url.searchParams.get("parents");
        if (!rawParents || !rawParents.trim()) {
          return jsonError(400, "Query parameter 'parents' is required (comma-separated res-5 H3 parent indexes).");
        }
        const parents = parseTileParents(rawParents);
        if (!parents) {
          return jsonError(400, "Malformed 'parents' value: expected comma-separated 15-char hex H3 indexes.");
        }
        if (parents.length > MAX_TILE_PARENTS_PER_REQUEST) {
          return jsonError(400, `Too many parents requested (${parents.length}); max ${MAX_TILE_PARENTS_PER_REQUEST} per call.`);
        }

        const entries = await Promise.all(parents.map((parent) => kvJson(env, `gridtiles/${parent}`)));
        const features: Record<string, unknown>[] = [];
        const missing: string[] = [];
        for (let i = 0; i < parents.length; i += 1) {
          const entry = entries[i];
          if (!entry) {
            missing.push(parents[i]);
            continue;
          }
          const payload = entry.value as { features?: Record<string, unknown>[] };
          features.push(...(payload.features ?? []));
        }
        const body = JSON.stringify({
          count: features.length,
          requested: parents.length,
          missing,
          type: "FeatureCollection",
          features,
        });
        const etag = `"${(await sha256Hex(body)).slice(0, 32)}"`;
        if (etagMatches(request, etag)) return notModified(baseHeaders, etag);
        return withHeaders(body, 200, { ...baseHeaders, etag });
      }

      // GET /api/v1/national — national hex layer index (per-res chunk inventories)
      if (url.pathname === "/api/v1/national") {
        const result = await fetchNationalIndex(env);
        if ("error" in result) return jsonError(404, result.error);
        const body = JSON.stringify(result);
        const etag = `"${(await sha256Hex(body)).slice(0, 32)}"`;
        if (etagMatches(request, etag)) return notModified(baseHeaders, etag);
        return withHeaders(body, 200, { ...baseHeaders, etag });
      }

      // GET /api/v1/national/{res}?parents=<res-3-parent-csv>
      // National display-layer chunks published by the batch snapshot builder
      // from the national-builder output tree (US-383).
      const nationalMatch = url.pathname.match(/^\/api\/v1\/national\/(\d+)$/);
      if (nationalMatch) {
        const rawParents = url.searchParams.get("parents");
        if (!rawParents || !rawParents.trim()) {
          return jsonError(400, "Query parameter 'parents' is required (comma-separated res-3 H3 parent indexes).");
        }
        const parents = parseTileParents(rawParents);
        if (!parents) {
          return jsonError(400, "Malformed 'parents' value: expected comma-separated 15-char hex H3 indexes.");
        }
        if (parents.length > MAX_NATIONAL_PARENTS_PER_REQUEST) {
          return jsonError(400, `Too many parents requested (${parents.length}); max ${MAX_NATIONAL_PARENTS_PER_REQUEST} per call.`);
        }
        const result = await fetchNationalRows(env, { res: Number(nationalMatch[1]), parents });
        if ("error" in result) return jsonError(400, result.error);
        const body = JSON.stringify(result);
        const etag = `"${(await sha256Hex(body)).slice(0, 32)}"`;
        if (etagMatches(request, etag)) return notModified(baseHeaders, etag);
        return withHeaders(body, 200, { ...baseHeaders, etag });
      }

      // GET /api/v1/catalysts/all — every metro's catalysts, attributed and ranked
      if (url.pathname === "/api/v1/catalysts/all") {
        const entry = await kvJson(env, "catalysts/index");
        if (!entry) return jsonError(404, "No combined catalyst snapshot published.");
        if (etagMatches(request, entry.etag)) return notModified(baseHeaders, entry.etag);
        return withHeaders(JSON.stringify(entry.value), 200, {
          ...baseHeaders,
          etag: entry.etag,
        });
      }

      // POST /api/v1/predict — point lookup of precomputed cell predictions
      if (url.pathname === "/api/v1/predict") {
        if (request.method !== "POST") {
          return jsonError(405, "Method Not Allowed");
        }
        const contentType = request.headers.get("content-type") ?? "";
        if (!contentType.toLowerCase().includes("application/json")) {
          return jsonError(415, "Expected 'content-type: application/json'.");
        }
        const rawBody = await request.text();
        if (rawBody.length > 100_000) {
          return jsonError(413, "Request body too large (max 100 KB).");
        }
        let body: Record<string, unknown>;
        try {
          body = JSON.parse(rawBody) as Record<string, unknown>;
        } catch {
          return jsonError(400, "Invalid JSON body.");
        }

        const h3Index =
          typeof body.h3_index === "string" && body.h3_index.trim()
            ? body.h3_index.trim().toLowerCase()
            : null;
        if (!h3Index) {
          return jsonError(
            400,
            "Edge snapshot requires 'h3_index'. Provide the H3 cell for ('latitude', 'longitude') via the client-side h3 resolver."
          );
        }
        if (!H3_PARENT_PATTERN.test(h3Index)) {
          return jsonError(400, "Malformed 'h3_index': expected a 15-char hex H3 cell index.");
        }

        // Data + cell lookup + SHAP-strip trigger come from the shared snapshot
        // query; the adapter keeps its own 400/404 envelopes and wording.
        const result = await lookupPrediction(env, {
          h3Index,
          includeShap: body.include_shap === false ? false : undefined,
        });
        if ("error" in result) return jsonError(404, String((result as Record<string, unknown>).error));
        return withHeaders(JSON.stringify(result), 200, baseHeaders);
      }

      return jsonError(404, "Not Found");
    } catch (err) {
      console.error("edge error:", err);
      return jsonError(500, "Edge error: snapshot data temporarily unavailable.");
    }
}
