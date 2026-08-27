/**
 * Urban Signal product site edge worker.
 *
 * The static site stays fully static (scripts/build.mjs emits dist/, including
 * the agent discovery documents under dist/.well-known/); this worker wraps it
 * with the dynamic surface that static hosting cannot express:
 *
 *   Link headers (RFC 8288)      every response advertises api-catalog,
 *                                describedby, service-doc, service-desc, status
 *   Markdown negotiation         `Accept: text/markdown` returns the page's
 *                                build-time markdown twin (Content-Type:
 *                                text/markdown + x-markdown-tokens)
 *   /healthz                     liveness document (rel="status" target)
 *   /mcp                         minimal MCP Streamable HTTP server exposing
 *                                read-only product knowledge tools
 *
 * Everything else passes through to the asset service unchanged (including the
 * /dashboard redirect from public/_redirects).
 */
import {
  MCP_PROTOCOL_VERSION,
  MCP_SERVER_NAME,
  MCP_SERVER_TITLE,
  PRODUCT_MCP_TOOLS,
} from "./scripts/mcp-tools.mjs";

const APP_VERSION = "2.0.0";
const OPENAPI_TYPE = "application/vnd.oai.openapi+json";
const DASH_OPENAPI = "https://us-dash.harlanljones.com/openapi.json";

// ---------------------------------------------------------------------------
// Shared response plumbing
// ---------------------------------------------------------------------------

const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-methods": "GET, POST, OPTIONS",
  "access-control-headers": "content-type, accept, mcp-session-id, mcp-protocol-version",
  "access-control-max-age": "86400",
};

/**
 * RFC 8288 Link header advertising the machine-readable surfaces. Page routes
 * additionally advertise their own markdown twin via rel="alternate".
 */
function linkHeaderFor(pathname) {
  const parts = [
    '</.well-known/api-catalog>; rel="api-catalog"; type="application/linkset+json"',
    '</.well-known/openapi.json>; rel="service-desc"; type="application/vnd.oai.openapi+json"',
    `<${DASH_OPENAPI}>; rel="service-desc"; type="${OPENAPI_TYPE}"`,
    '</llms.txt>; rel="service-doc"; type="text/plain"',
    '</llms-full.txt>; rel="describedby"; type="text/plain"',
    '</facts.json>; rel="describedby"; type="application/json"',
    '</healthz>; rel="status"; type="application/json"',
    '</.well-known/mcp/server-card.json>; rel="describedby"; title="MCP server card"',
  ];
  const twin = markdownTwinPath(pathname);
  if (twin) parts.push(`<${twin}>; rel="alternate"; type="text/markdown"`);
  return parts.join(", ");
}

/** Map a page route to its markdown twin asset path (null when none applies). */
function markdownTwinPath(pathname) {
  if (pathname.endsWith(".md")) return null;
  if (pathname === "/" || pathname === "/healthz" || pathname === "/mcp") return null;
  if (pathname.startsWith("/.well-known/") || pathname.startsWith("/public/") || pathname.startsWith("/src/")) {
    return null;
  }
  if (/\.[a-z0-9]+$/i.test(pathname)) return null;
  return `${pathname.replace(/\/+$/, "")}/index.md`;
}

// Extensionless discovery documents and non-default media types that the asset
// service cannot infer from file extensions.
const CONTENT_TYPES = {
  "/.well-known/api-catalog": "application/linkset+json",
  "/.well-known/oauth-protected-resource": "application/json",
  "/.well-known/openapi.json": "application/vnd.oai.openapi+json",
  "/.well-known/mcp/server-card.json": "application/json",
};

function acceptsMarkdown(acceptHeader) {
  return (acceptHeader ?? "")
    .split(",")
    .some((part) => part.trim().toLowerCase().startsWith("text/markdown"));
}

// Long-lived edge caching. Static, content-addressed assets (scripts, styles,
// icons) can be cached for a year with background revalidation; everything else
// (HTML, facts, llms docs) gets a short window so deploys propagate, but still
// serves instantly from cache and refreshes in the background. This replaces the
// default `max-age=0, must-revalidate` that forced a conditional round-trip on
// every single navigation.
const IMMUTABLE_ASSET = "public, max-age=31536000, immutable";
const FRESH_CONTENT = "public, max-age=300, stale-while-revalidate=86400";

function cacheControlFor(pathname, contentType) {
  if (pathname.startsWith("/healthz") || pathname === "/mcp") return "no-store";
  const type = (contentType ?? "").toLowerCase();
  if (/\.(css|js|mjs|svg|woff2?|ttf|ico|png|jpeg|jpg|webp|avif|gif)(\?|$)/i.test(pathname)) {
    return IMMUTABLE_ASSET;
  }
  if (type.includes("text/html")) return FRESH_CONTENT;
  if (type.includes("application/json") || type.includes("text/markdown") || type.includes("text/plain")) {
    return FRESH_CONTENT;
  }
  if (/\.(json|md|txt)(\?|$)/i.test(pathname)) return FRESH_CONTENT;
  return FRESH_CONTENT;
}

function decorate(response, { pathname, contentType, tokens, cacheControl } = {}) {
  const headers = new Headers(response.headers);
  if (contentType) headers.set("content-type", contentType);
  headers.set("link", linkHeaderFor(pathname));
  headers.append("vary", "Accept");
  if (tokens !== undefined) headers.set("x-markdown-tokens", String(tokens));
  const policy = cacheControl ?? cacheControlFor(pathname, response.headers.get("content-type"));
  if (policy) headers.set("cache-control", policy);
  if (pathname.startsWith("/.well-known/") || pathname === "/healthz") {
    for (const [key, value] of Object.entries(CORS_HEADERS)) headers.set(key, value);
  }
  return new Response(response.body, { status: response.status, headers });
}

async function readAsset(env, path) {
  return env.ASSETS.fetch(new Request(new URL(path, "https://assets.local")));
}

// ---------------------------------------------------------------------------
// MCP Streamable HTTP server (read-only product knowledge tools)
// ---------------------------------------------------------------------------

function rpcResult(id, result) {
  return new Response(JSON.stringify({ jsonrpc: "2.0", id, result }), {
    status: 200,
    headers: { "content-type": "application/json", ...CORS_HEADERS },
  });
}

function rpcError(id, code, message) {
  return new Response(JSON.stringify({ jsonrpc: "2.0", id, error: { code, message } }), {
    status: 200,
    headers: { "content-type": "application/json", ...CORS_HEADERS },
  });
}

function toolError(message) {
  return { content: [{ type: "text", text: message }], isError: true };
}

async function callTool(name, args, env) {
  switch (name) {
    case "list_cities": {
      const facts = JSON.parse(await (await readAsset(env, "/facts.json")).text());
      const cities = facts.metros.map(({ id, name, state, feeds }) => ({
        id,
        name,
        state,
        feeds_available: feeds.filter(Boolean).length,
      }));
      return { content: [{ type: "text", text: JSON.stringify({ count: cities.length, cities }, null, 2) }] };
    }
    case "get_product_facts": {
      const body = await (await readAsset(env, "/facts.json")).text();
      return { content: [{ type: "text", text: body }] };
    }
    case "get_city_brief": {
      const cityId = typeof args.city_id === "string" ? args.city_id.trim().toLowerCase() : "";
      if (!cityId) return toolError("'city_id' is required — call list_cities first.");
      const brief = await readAsset(env, `/public/cities/${encodeURIComponent(cityId)}.json`);
      if (!brief.ok) return toolError(`No city brief for '${cityId}'. Call list_cities for valid ids.`);
      return { content: [{ type: "text", text: await brief.text() }] };
    }
    case "get_site_guide": {
      const guide = await readAsset(env, "/llms.txt");
      return { content: [{ type: "text", text: await guide.text() }] };
    }
    default:
      return toolError(`Unknown tool '${String(name)}'.`);
  }
}

async function handleMcp(request, env) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }
  if (request.method === "GET") {
    return new Response(
      JSON.stringify({
        detail: "Urban Signal MCP: POST JSON-RPC 2.0 messages to this endpoint (Streamable HTTP). Card: /.well-known/mcp/server-card.json",
      }),
      { status: 405, headers: { "content-type": "application/json", allow: "POST, OPTIONS", ...CORS_HEADERS } }
    );
  }
  if (request.method !== "POST") {
    return new Response(JSON.stringify({ detail: "Method Not Allowed" }), {
      status: 405,
      headers: { "content-type": "application/json", ...CORS_HEADERS },
    });
  }

  let message;
  try {
    message = await request.json();
  } catch {
    return new Response(
      JSON.stringify({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }),
      { status: 400, headers: { "content-type": "application/json", ...CORS_HEADERS } }
    );
  }

  // Notifications carry no id and take no reply beyond acceptance.
  if (message.id === undefined || message.id === null) {
    return new Response(null, { status: 202, headers: CORS_HEADERS });
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
          serverInfo: { name: MCP_SERVER_NAME, title: MCP_SERVER_TITLE, version: APP_VERSION },
          instructions:
            "Read-only product knowledge for Urban Signal: list_cities, get_product_facts, get_city_brief(city_id), get_site_guide.",
        });
      case "ping":
        return rpcResult(message.id, {});
      case "tools/list":
        return rpcResult(message.id, { tools: PRODUCT_MCP_TOOLS });
      case "tools/call":
        return rpcResult(
          message.id,
          await callTool(String(message.params?.name ?? ""), message.params?.arguments ?? {}, env)
        );
      default:
        return rpcError(message.id, -32601, `Method not found: ${String(message.method)}`);
    }
  } catch (error) {
    return rpcError(message.id, -32603, `Internal error: ${error instanceof Error ? error.message : "unknown failure"}`);
  }
}

// ---------------------------------------------------------------------------
// Routing
// ---------------------------------------------------------------------------

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const { pathname } = url;

    if (pathname === "/healthz") {
      return decorate(
        new Response(
          JSON.stringify({ status: "healthy", service: "urban-signal-product-site", version: APP_VERSION }),
          { status: 200, headers: { "content-type": "application/json", "cache-control": "no-store" } }
        ),
        { pathname }
      );
    }

    if (pathname === "/mcp") return handleMcp(request, env);

    if (
      request.method === "OPTIONS" &&
      (pathname.startsWith("/.well-known/") || pathname === "/healthz")
    ) {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // Markdown content negotiation: serve the page's build-time twin.
    if ((request.method === "GET" || request.method === "HEAD") && acceptsMarkdown(request.headers.get("accept"))) {
      const twinPath = markdownTwinPath(pathname);
      if (twinPath) {
        const twin = await readAsset(env, twinPath);
        if (twin.ok) {
          const body = await twin.text();
          return decorate(
            new Response(body, {
              status: 200,
              headers: { "content-type": "text/markdown; charset=utf-8", "cache-control": "public, max-age=300" },
            }),
            { pathname: twinPath, tokens: Math.ceil(body.length / 4) }
          );
        }
      }
    }

    let asset = await env.ASSETS.fetch(request);

    // Markdown twins requested directly (e.g. via the rel="alternate" link)
    // still need an explicit markdown content type.
    if (
      asset.ok &&
      pathname.endsWith(".md") &&
      !(asset.headers.get("content-type") ?? "").includes("text/markdown")
    ) {
      const headers = new Headers(asset.headers);
      headers.set("content-type", "text/markdown; charset=utf-8");
      asset = new Response(asset.body, { status: asset.status, headers });
    }

    if (asset.ok) return decorate(asset, { pathname, contentType: CONTENT_TYPES[pathname] });
    return asset;
  },
};
