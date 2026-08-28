import { expect, test } from "bun:test";
import worker from "../src/index";

const CITY_IDS = [
  "nyc",
  "chicago",
  "san_francisco",
  "seattle",
  "los_angeles",
  "new_orleans",
  "norfolk",
  "detroit",
  "austin",
  "cincinnati",
  "boston",
  "baltimore",
  "montgomery",
  "baton_rouge",
  "denver",
  "philadelphia",
  "washington_dc",
  "prince_georges",
  "columbus",
  "nashville",
  "kansas_city",
  "minneapolis",
  "pierce",
  "milwaukee",
  "charlotte",
  "pittsburgh",
  "san_diego",
  "big",
  "dual",
] as const;

const ORIGIN = "https://urban-signal.test";

export function testEnv(options: { html?: string } = {}) {
  return {
    SNAPSHOT: {
      async get(key: string) {
        if (key === "manifest") {
          return JSON.stringify({
            generated_at: "2026-08-24T00:00:00Z",
            app_version: "2.0.0",
            cities: CITY_IDS,
            resolution: 9,
            k_ring: 1,
            catalyst_threshold: 85,
          });
        }
        if (key.startsWith("grid/")) {
          const city = key.slice("grid/".length);
          return JSON.stringify({
            type: "FeatureCollection",
            city_id: city,
            features: [
              {
                type: "Feature",
                id: "892a10708b7ffff",
                geometry: { type: "Polygon", coordinates: [[[-74.0, 40.7], [-74.0, 40.8], [-73.9, 40.8], [-74.0, 40.7]]] },
                properties: { h3_index: "892a10708b7ffff", city_id: city, lims_score: 97.5 },
              },
            ],
          });
        }
        if (key.startsWith("submarkets/")) {
          const city = key.slice("submarkets/".length);
          return JSON.stringify({
            city_id: city,
            count: 1,
            submarkets: { SUB_1: { borough: "Manhattan", score: 71.2 } },
          });
        }
        if (key === "catalysts/index") {
          return JSON.stringify({
            count: 3,
            threshold: 85,
            cities: ["chicago", "nyc"],
            catalysts: [
              { h3_index: "892a10708b7ffff", lims_score: 97.5, borough: "Manhattan", city_id: "nyc", city_name: "New York City" },
              { h3_index: "892a10708bfffff", lims_score: 88.0, borough: "Brooklyn", city_id: "nyc", city_name: "New York City" },
              { h3_index: "892830bbfffffff", lims_score: 86.0, borough: "Central / Downtown", city_id: "chicago", city_name: "Chicago" },
            ],
          });
        }
        if (key === "catalysts/nyc") {
          return JSON.stringify({
            city_id: "nyc",
            count: 3,
            threshold: 85,
            borough: null,
            catalysts: [
              { h3_index: "892a10708b7ffff", lims_score: 97.5, borough: "Manhattan", city_id: "nyc", city_name: "New York City" },
              { h3_index: "892a10708bfffff", lims_score: 86.0, borough: "Brooklyn", city_id: "nyc", city_name: "New York City" },
              { h3_index: "892830bbfffffff", lims_score: 91.0, borough: "Washington_Heights", city_id: "nyc", city_name: "New York City" },
            ],
          });
        }
        if (key === "catalysts/dual") {
          return JSON.stringify({
            city_id: "dual",
            count: 2,
            threshold: 90,
            borough: null,
            catalysts: [
              { h3_index: "892a10708b7ffff", lims_score: 97.5, borough: "Manhattan", city_id: "dual", city_name: "Dual" },
              { h3_index: "892a10708bfffff", lims_score: 86.0, borough: "Brooklyn", city_id: "dual", city_name: "Dual" },
            ],
          });
        }
        if (key === "catalysts/big") {
          const big = Array.from({ length: 600 }, (_, i) => ({
            h3_index: `892a100${(i % 1000).toString(16).padStart(3, "0")}${i.toString(16).padStart(4, "0")}`,
            lims_score: 90 - (i % 30),
            borough: "Queens",
            city_id: "big",
            city_name: "Bigville",
          }));
          return JSON.stringify({ city_id: "big", count: big.length, threshold: 85, borough: null, catalysts: big });
        }
        if (key.startsWith("catalysts/")) {
          const city = key.slice("catalysts/".length);
          return JSON.stringify({
            city_id: city,
            count: 2,
            threshold: 85,
            borough: null,
            catalysts: [
              { h3_index: "892a10708b7ffff", lims_score: 97.5, borough: "Manhattan" },
              { h3_index: "892a10708bfffff", lims_score: 86.0, borough: "Brooklyn" },
            ],
          });
        }
        if (key === "cells/index") {
          return JSON.stringify({
            "892a10708b7ffff": { h3_index: "892a10708b7ffff", lims_score: 97.5, shap_attributions: [{ f: "x", v: 0.4 }] },
          });
        }
        if (key.startsWith("cells/")) {
          // US-385 per-cell shard: only this cell is sharded in the fixture.
          const cell = key.slice("cells/".length);
          if (cell === "892830bbfffffff") {
            return JSON.stringify({
              h3_index: cell,
              lims_score: 91.0,
              source: "per-cell-shard",
            });
          }
          return null;
        }
        if (key.startsWith("national/")) {
          // US-383 national hex layer: index + two res-6 chunks.
          if (key === "national/index") {
            return JSON.stringify({
              generated_at: "2026-08-28T00:00:00+00:00",
              resolutions: {
                "6": {
                  count: 2,
                  byte_size: 260,
                  sha256: "a".repeat(64),
                  parents: ["832830fffffffff", "8326b9fffffffff"],
                  generated_at: "2026-08-28T00:00:00+00:00",
                },
              },
            });
          }
          if (key === "national/6/832830fffffffff") {
            return JSON.stringify({
              res: 6,
              parent: "832830fffffffff",
              year: 2023,
              signal_source: "census_lehd_lodes8",
              cols: ["h3", "jobs", "workers", "jobs_pct", "workers_pct"],
              rows: [["892a10708b7ffff", 1200, 900, 71.5, 66.25]],
            });
          }
          if (key === "national/6/8326b9fffffffff") {
            return JSON.stringify({
              res: 6,
              parent: "8326b9fffffffff",
              year: 2023,
              signal_source: "census_lehd_lodes8",
              cols: ["h3", "jobs", "workers", "jobs_pct", "workers_pct"],
              rows: [["8926b9fffffffff", 40, null, 12.5, null]],
            });
          }
          return null;
        }
        if (key.startsWith("gridtiles/")) {
          const parent = key.slice("gridtiles/".length);
          if (parent === "852830bbfffffff") {
            return JSON.stringify({
              type: "FeatureCollection",
              tile_parent: parent,
              tile_resolution: 5,
              features: [
                {
                  type: "Feature",
                  id: "892a10708b7ffff",
                  geometry: { type: "Polygon", coordinates: [[[-74.0, 40.7], [-74.0, 40.8], [-73.9, 40.8], [-74.0, 40.7]]] },
                  properties: { h3_index: "892a10708b7ffff", city_id: "nyc", city_name: "New York City", lims_score: 97.5, lims_score_national_pct: 100, lims_score_metro_pct: 96.4 },
                },
              ],
            });
          }
          if (parent === "852ab2c3fffffff") {
            return JSON.stringify({
              type: "FeatureCollection",
              tile_parent: parent,
              tile_resolution: 5,
              features: [
                {
                  type: "Feature",
                  id: "892a10708bfffff",
                  geometry: { type: "Polygon", coordinates: [[[-87.7, 41.9], [-87.7, 42.0], [-87.6, 42.0], [-87.7, 41.9]]] },
                  properties: { h3_index: "892a10708bfffff", city_id: "chicago", city_name: "Chicago", lims_score: 88.0, lims_score_national_pct: 71.2, lims_score_metro_pct: 50 },
                },
              ],
            });
          }
          return null;
        }
        if (key === "catalysts/index") {
          return JSON.stringify({
            count: 3,
            threshold: 85,
            cities: ["chicago", "nyc"],
            catalysts: [
              { h3_index: "892a10708b7ffff", lims_score: 97.5, borough: "Manhattan", city_id: "nyc", city_name: "New York City" },
              { h3_index: "892a10708bfffff", lims_score: 88.0, borough: "Brooklyn", city_id: "nyc", city_name: "New York City" },
              { h3_index: "892830bbfffffff", lims_score: 86.0, borough: "Central / Downtown", city_id: "chicago", city_name: "Chicago" },
            ],
          });
        }
        return null;
      },
    },
    ASSETS: {
      fetch: async () =>
        new Response(options.html ?? "<!DOCTYPE html><html><body>dashboard</body></html>", {
          status: 200,
          headers: { "content-type": "text/html; charset=utf-8" },
        }),
    },
  };
}

async function mcpCall(env: never, body: unknown): Promise<{ status: number; json?: Record<string, never> }> {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/mcp`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
    env
  );
  if (response.status === 202) return { status: 202 };
  const json = (await response.json()) as Record<string, never>;
  return { status: response.status, json };
}

// ---------------------------------------------------------------------------
// Existing API contract
// ---------------------------------------------------------------------------

test("accepts every city emitted by the snapshot builder", async () => {
  for (const city of CITY_IDS) {
    const response = await worker.fetch(
      new Request(`${ORIGIN}/api/v1/submarkets?city_id=${city}`),
      testEnv() as never,
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({ city_id: city });
  }
});

test("accepts the common Boston alias without changing the city", async () => {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/submarkets?city_id=boston`),
    testEnv() as never,
  );

  expect(response.status).toBe(200);
  expect(await response.json()).toMatchObject({ city_id: "boston" });
});

test("accepts a manifest city with no alias entry on every data route", async () => {
  for (const route of ["submarkets", "grid", "catalysts"]) {
    const response = await worker.fetch(
      new Request(`${ORIGIN}/api/v1/${route}?city_id=san_diego`),
      testEnv() as never,
    );

    expect([route, response.status]).toEqual([route, 200]);
  }
});

test("still rejects a city absent from the snapshot manifest", async () => {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/submarkets?city_id=atlantis`),
    testEnv() as never,
  );

  expect(response.status).toBe(400);
});

// ---------------------------------------------------------------------------
// Lazy-loading tiles + combined catalyst feed
// ---------------------------------------------------------------------------

test("manifest endpoint exposes tile index and metro metadata", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/manifest`), testEnv() as never);

  expect(response.status).toBe(200);
  const manifest = (await response.json()) as {
    cities: string[];
    metro_index?: unknown;
    tile_index?: Record<string, unknown>;
  };
  expect(manifest.cities.length).toBe(CITY_IDS.length);
});

test("gridtiles merges features across requested parents and reports missing", async () => {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/gridtiles?parents=852830bbfffffff,852ab2c3fffffff,8529999ffffffff`),
    testEnv() as never,
  );

  expect(response.status).toBe(200);
  const payload = (await response.json()) as {
    count: number;
    requested: number;
    missing: string[];
    features: { properties: { h3_index: string } }[];
  };
  expect(payload.requested).toBe(3);
  expect(payload.missing).toEqual(["8529999ffffffff"]);
  expect(payload.count).toBe(2);
  expect(payload.features.map((f) => f.properties.h3_index)).toEqual(["892a10708b7ffff", "892a10708bfffff"]);
});

test("gridtiles dedupes repeated parents and is case-insensitive", async () => {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/gridtiles?parents=852830BBFFFFFFF,852830bbfffffff`),
    testEnv() as never,
  );

  expect(response.status).toBe(200);
  const payload = (await response.json()) as { count: number; requested: number; missing: string[] };
  expect(payload.requested).toBe(1);
  expect(payload.count).toBe(1);
  expect(payload.missing).toEqual([]);
});

test("gridtiles rejects a missing, malformed, or oversized parents parameter", async () => {
  const missing = await worker.fetch(new Request(`${ORIGIN}/api/v1/gridtiles`), testEnv() as never);
  expect(missing.status).toBe(400);

  const malformed = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/gridtiles?parents=not-a-parent`),
    testEnv() as never,
  );
  expect(malformed.status).toBe(400);

  const oversized = Array.from({ length: 33 }, (_, i) => i.toString(16).padStart(15, "0")).join(",");
  const tooMany = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/gridtiles?parents=${oversized}`),
    testEnv() as never,
  );
  expect(tooMany.status).toBe(400);
});

// ---------------------------------------------------------------------------
// GET /api/v1/national[/res] — national hex layer (US-383)
// ---------------------------------------------------------------------------

test("national index returns the per-resolution chunk inventory", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/national`), testEnv() as never);

  expect(response.status).toBe(200);
  const payload = (await response.json()) as {
    generated_at: string;
    resolutions: Record<string, { count: number; parents: string[] }>;
  };
  expect(payload.resolutions["6"].count).toBe(2);
  expect(payload.resolutions["6"].parents).toContain("832830fffffffff");
  expect(response.headers.get("etag")).toBeTruthy();
});

test("national index honors ETag revalidation", async () => {
  const first = await worker.fetch(new Request(`${ORIGIN}/api/v1/national`), testEnv() as never);
  const etag = first.headers.get("etag") ?? "";
  const revalidated = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/national`, { headers: { "if-none-match": etag } }),
    testEnv() as never,
  );
  expect(revalidated.status).toBe(304);
});

test("national chunks merge rows across parents and report missing", async () => {
  const response = await worker.fetch(
    new Request(
      `${ORIGIN}/api/v1/national/6?parents=832830fffffffff,8326b9fffffffff,8329999ffffffff`,
    ),
    testEnv() as never,
  );

  expect(response.status).toBe(200);
  const payload = (await response.json()) as {
    res: number;
    count: number;
    cols: string[];
    rows: unknown[][];
    missing: string[];
  };
  expect(payload.res).toBe(6);
  expect(payload.count).toBe(2);
  expect(payload.cols).toEqual(["h3", "jobs", "workers", "jobs_pct", "workers_pct"]);
  expect(payload.missing).toEqual(["8329999ffffffff"]);
  expect(payload.rows.map((row) => row[0])).toEqual(["892a10708b7ffff", "8926b9fffffffff"]);
  expect(response.headers.get("etag")).toBeTruthy();
});

test("national chunks honor ETag revalidation", async () => {
  const first = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/national/6?parents=832830fffffffff`),
    testEnv() as never,
  );
  const etag = first.headers.get("etag") ?? "";
  const revalidated = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/national/6?parents=832830fffffffff`, {
      headers: { "if-none-match": etag },
    }),
    testEnv() as never,
  );
  expect(revalidated.status).toBe(304);
});

test("national chunks reject invalid resolution and bad parents", async () => {
  const badRes = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/national/9?parents=832830fffffffff`),
    testEnv() as never,
  );
  expect(badRes.status).toBe(400);

  const noParents = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/national/6`),
    testEnv() as never,
  );
  expect(noParents.status).toBe(400);

  const malformed = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/national/6?parents=not-a-parent`),
    testEnv() as never,
  );
  expect(malformed.status).toBe(400);

  const oversized = Array.from({ length: 65 }, (_, i) => i.toString(16).padStart(15, "0")).join(",");
  const tooMany = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/national/6?parents=${oversized}`),
    testEnv() as never,
  );
  expect(tooMany.status).toBe(400);
});

test("catalysts/all returns the combined attributed feed", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts/all`), testEnv() as never);

  expect(response.status).toBe(200);
  const payload = (await response.json()) as {
    count: number;
    cities: string[];
    catalysts: { city_id: string; city_name: string; lims_score: number }[];
  };
  expect(payload.count).toBe(3);
  expect(payload.cities).toEqual(["chicago", "nyc"]);
  for (const entry of payload.catalysts) {
    expect(entry.city_name).toBeTruthy();
  }
});

// ---------------------------------------------------------------------------
// robots.txt + sitemap.xml
// ---------------------------------------------------------------------------

test("robots.txt references the sitemap and the agentmap", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/robots.txt`), testEnv() as never);

  expect(response.status).toBe(200);
  const body = await response.text();
  expect(body).toContain("User-agent: *");
  expect(body).toContain(`Sitemap: ${ORIGIN}/sitemap.xml`);
  expect(body).toContain(`Agentmap: ${ORIGIN}/.well-known/ai-catalog.json`);
});

test("sitemap.xml lists canonical URLs for every published metro", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/sitemap.xml`), testEnv() as never);

  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toContain("application/xml");
  const body = await response.text();
  expect(body).toContain("<loc>https://urban-signal.test/</loc>");
  expect(body).toContain("<lastmod>2026-08-24</lastmod>");
  for (const city of CITY_IDS) {
    expect(body).toContain(`<loc>${ORIGIN}/?city=${city}</loc>`);
  }
});

// ---------------------------------------------------------------------------
// Link headers + markdown negotiation on the homepage
// ---------------------------------------------------------------------------

test("homepage HTML carries RFC 8288 Link headers for discovery", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/`), testEnv() as never);

  expect(response.status).toBe(200);
  const link = response.headers.get("link");
  expect(link).toContain('</.well-known/api-catalog>; rel="api-catalog"');
  expect(link).toContain('</openapi.json>; rel="service-desc"');
  expect(link).toContain('rel="service-doc"');
  expect(link).toContain('rel="sitemap"');
});

test("Accept: text/markdown returns a markdown rendering of the homepage", async () => {
  const env = testEnv() as never;
  const md = await worker.fetch(
    new Request(`${ORIGIN}/`, { headers: { accept: "text/markdown" } }),
    env,
  );

  expect(md.status).toBe(200);
  expect(md.headers.get("content-type")).toContain("text/markdown");
  expect(md.headers.get("x-markdown-tokens")).toBeTruthy();
  const body = await md.text();
  expect(body).toContain("# Urban Signal");
  expect(body).toContain(`${ORIGIN}/api/v1/cities`);

  // HTML stays the default without the header.
  const html = await worker.fetch(new Request(`${ORIGIN}/`), env);
  expect(html.headers.get("content-type")).toContain("text/html");
});

// ---------------------------------------------------------------------------
// API catalog / PRM / auth.md / openapi.json
// ---------------------------------------------------------------------------

test("api-catalog is an RFC 9727 linkset with service-desc and status", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/.well-known/api-catalog`), testEnv() as never);

  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toContain("application/linkset+json");
  const doc = (await response.json()) as { linkset: Record<string, never>[] };
  const entry = doc.linkset[0] as Record<string, { href: string }[]>;
  expect(entry.anchor).toBe(`${ORIGIN}/api/v1`);
  expect(entry["service-desc"][0].href).toBe(`${ORIGIN}/openapi.json`);
  expect(entry["service-doc"][0].href).toContain("/SKILL.md");
  expect(entry.status[0].href).toBe(`${ORIGIN}/health`);
});

test("oauth-protected-resource declares a public resource with no authorization servers", async () => {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/.well-known/oauth-protected-resource`),
    testEnv() as never,
  );

  expect(response.status).toBe(200);
  const doc = (await response.json()) as Record<string, unknown>;
  expect(doc.resource).toBe(`${ORIGIN}/`);
  expect(doc.authorization_servers).toEqual([]);
  expect(doc.resource_documentation).toBe(`${ORIGIN}/auth.md`);
});

test("auth.md documents anonymous access under an auth.md heading", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/auth.md`), testEnv() as never);

  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toContain("text/markdown");
  const body = await response.text();
  expect(body.startsWith("# auth.md")).toBe(true);
  expect(body.toLowerCase()).toContain("no agent registration");
});

test("openapi.json describes every public data route", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/openapi.json`), testEnv() as never);

  expect(response.status).toBe(200);
  const spec = (await response.json()) as { openapi: string; paths: Record<string, unknown> };
  expect(spec.openapi).toMatch(/^3\.1\./);
  for (const path of ["/health", "/api/v1/cities", "/api/v1/submarkets", "/api/v1/grid", "/api/v1/catalysts", "/api/v1/predict", "/api/v1/manifest", "/api/v1/gridtiles", "/api/v1/national", "/api/v1/national/{res}", "/api/v1/catalysts/all"]) {
    expect(spec.paths[path]).toBeTruthy();
  }
});

// ---------------------------------------------------------------------------
// MCP server + card
// ---------------------------------------------------------------------------

test("mcp server card advertises tools over streamable HTTP", async () => {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/.well-known/mcp/server-card.json`),
    testEnv() as never,
  );

  expect(response.status).toBe(200);
  const card = (await response.json()) as {
    serverInfo: { name: string; version: string };
    transport: { endpoint: string };
    capabilities: Record<string, unknown>;
  };
  expect(card.serverInfo.name).toBe("urban-signal-dashboard");
  expect(card.serverInfo.version).toBe("2.0.0");
  expect(card.transport.endpoint).toBe(`${ORIGIN}/mcp`);
  expect(card.capabilities.tools).toBeTruthy();
});

test("mcp handshake, listing, and tool calls work over JSON-RPC", async () => {
  const env = testEnv() as never;

  const init = await mcpCall(env, {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "t", version: "0" } },
  });
  expect(init.status).toBe(200);
  const initResult = init.json!.result as unknown as {
    protocolVersion: string;
    serverInfo: { name: string };
  };
  expect(initResult.protocolVersion).toBe("2025-06-18");
  expect(initResult.serverInfo.name).toBe("urban-signal-dashboard");

  expect(await mcpCall(env, { jsonrpc: "2.0", method: "notifications/initialized" })).toEqual({ status: 202 });

  const listed = await mcpCall(env, { jsonrpc: "2.0", id: 2, method: "tools/list" });
  const tools = (listed.json!.result as unknown as { tools: { name: string; inputSchema: object }[] }).tools;
  expect(tools.map((tool) => tool.name)).toEqual(["list_cities", "get_submarkets", "get_catalysts", "predict_cell"]);
  for (const tool of tools) expect(tool.inputSchema).toBeTruthy();

  const called = await mcpCall(env, {
    jsonrpc: "2.0",
    id: 3,
    method: "tools/call",
    params: { name: "get_catalysts", arguments: { city_id: "sf", min_lims: 90 } },
  });
  const result = called.json!.result as unknown as { content: { text: string }[] };
  const payload = JSON.parse(result.content[0].text) as { city_id: string; catalysts: unknown[] };
  expect(payload.city_id).toBe("san_francisco");
  expect(payload.catalysts.length).toBe(1);

  const missing = await mcpCall(env, { jsonrpc: "2.0", id: 4, method: "tools/nope" });
  const err = missing.json!.error as unknown as { code: number };
  expect(err.code).toBe(-32601);

  const getResponse = await worker.fetch(new Request(`${ORIGIN}/mcp`), env);
  expect(getResponse.status).toBe(405);
});

// ---------------------------------------------------------------------------
// Agent skills discovery
// ---------------------------------------------------------------------------

test("agent-skills index digests match the served SKILL.md artifacts", async () => {
  const env = testEnv() as never;
  const response = await worker.fetch(
    new Request(`${ORIGIN}/.well-known/agent-skills/index.json`),
    env,
  );

  expect(response.status).toBe(200);
  const index = (await response.json()) as {
    $schema: string;
    skills: { name: string; type: string; description: string; url: string; digest: string }[];
  };
  expect(index.$schema).toBe("https://schemas.agentskills.io/discovery/0.2.0/schema.json");
  expect(index.skills.length).toBeGreaterThanOrEqual(2);

  for (const skill of index.skills) {
    expect(skill.type).toBe("skill-md");
    expect(skill.digest).toMatch(/^sha256:[0-9a-f]{64}$/);
    const artifact = await worker.fetch(new Request(skill.url), env);
    expect(artifact.status).toBe(200);
    expect(artifact.headers.get("content-type")).toContain("text/markdown");
    const body = await artifact.text();
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(body));
    const hex = Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
    expect(skill.digest).toBe(`sha256:${hex}`);
  }
});

// ---------------------------------------------------------------------------
// ARD manifest
// ---------------------------------------------------------------------------

test("ai-catalog.json is CORS-open with well-formed entries", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/.well-known/ai-catalog.json`), testEnv() as never);

  expect(response.status).toBe(200);
  expect(response.headers.get("content-type")).toContain("application/json");
  expect(response.headers.get("access-control-allow-origin")).toBe("*");

  const doc = (await response.json()) as {
    specVersion: string;
    host: { displayName: string; identifier: string };
    entries: {
      identifier: string;
      displayName: string;
      type: string;
      url?: string;
      data?: unknown;
      representativeQueries: string[];
    }[];
  };
  expect(doc.specVersion).toBe("1.0");
  expect(doc.host.identifier).toContain("did:web:");
  expect(doc.entries.length).toBeGreaterThan(0);
  for (const entry of doc.entries) {
    expect(entry.identifier).toMatch(new RegExp(`^urn:air:.+:[a-z]+:[a-z-]+$`));
    expect(entry.displayName).toBeTruthy();
    expect(entry.type).toContain("/");
    expect([entry.url !== undefined, entry.data !== undefined].filter(Boolean)).toEqual([true]);
    expect(entry.representativeQueries.length).toBeGreaterThanOrEqual(2);
    expect(entry.representativeQueries.length).toBeLessThanOrEqual(5);
  }
});

// ---------------------------------------------------------------------------
// US-187: snapshot contract safety-net tests (limit/max, min_lims, borough,
// trim shape, SHAP strip) for both the HTTP and MCP adapters.
// ---------------------------------------------------------------------------

async function mcpTool(env: never, name: string, args: Record<string, unknown>) {
  await worker.fetch(
    new Request(`${ORIGIN}/mcp`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "t", version: "0" } },
      }),
    }),
    env,
  );
  const response = await worker.fetch(
    new Request(`${ORIGIN}/mcp`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name, arguments: args } }),
    }),
    env,
  );
  const json = (await response.json()) as { result?: { content: { text: string }[]; isError?: boolean } };
  const result = json.result!;
  return {
    isError: Boolean(result.isError),
    payload: result.isError ? null : (JSON.parse(result.content[0].text) as Record<string, unknown>),
  };
}

// (1) HTTP catalysts limit: default 50, clamp at 500
test("HTTP catalysts defaults to limit 50", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=big`), testEnv() as never);
  expect(response.status).toBe(200);
  const json = (await response.json()) as { catalysts: unknown[] };
  expect(json.catalysts.length).toBe(50);
});

test("HTTP catalysts clamps limit beyond the 500 max", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=big&limit=600`), testEnv() as never);
  expect(response.status).toBe(200);
  const json = (await response.json()) as { catalysts: unknown[] };
  expect(json.catalysts.length).toBe(500);
});

test("HTTP catalysts honors an in-range explicit limit", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=big&limit=10`), testEnv() as never);
  expect(response.status).toBe(200);
  const json = (await response.json()) as { catalysts: unknown[] };
  expect(json.catalysts.length).toBe(10);
});

// (2) Catalyst limit policy — CONSOLIDATED via PRODUCT DECISION (US-190):
// both adapters now use the HTTP/manifest policy (default 50, max 500). The
// historical MCP default of 25 and 100 clamp are intentionally retired.
test("MCP get_catalysts defaults to limit 50 (aligned with HTTP)", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "get_catalysts", { city_id: "big" });
  expect(isError).toBe(false);
  expect((payload!.catalysts as unknown[]).length).toBe(50);
});

test("MCP get_catalysts clamps limit at the 500 max (aligned with HTTP)", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "get_catalysts", { city_id: "big", limit: 600 });
  expect(isError).toBe(false);
  expect((payload!.catalysts as unknown[]).length).toBe(500);
});

// (3) min_lims bounds + default-source behavior for both adapters
test("HTTP catalysts rejects min_lims above 100 with 422", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=nyc&min_lims=150`), testEnv() as never);
  expect(response.status).toBe(422);
});

test("HTTP catalysts rejects min_lims below 0 with 422", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=nyc&min_lims=-5`), testEnv() as never);
  expect(response.status).toBe(422);
});

test("HTTP catalysts accepts an in-range min_lims (200)", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=nyc&min_lims=50`), testEnv() as never);
  expect(response.status).toBe(200);
  const json = (await response.json()) as { threshold: number };
  expect(json.threshold).toBe(50);
});

test("HTTP catalysts default min_lims comes from the manifest threshold (85)", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=dual`), testEnv() as never);
  expect(response.status).toBe(200);
  const json = (await response.json()) as { threshold: number };
  expect(json.threshold).toBe(85);
});

test("MCP get_catalysts rejects min_lims out of range with isError", async () => {
  const { isError } = await mcpTool(testEnv() as never, "get_catalysts", { city_id: "nyc", min_lims: 150 });
  expect(isError).toBe(true);
});

test("MCP get_catalysts accepts an in-range min_lims", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "get_catalysts", { city_id: "nyc", min_lims: 50 });
  expect(isError).toBe(false);
  expect(payload!.threshold).toBe(50);
});

test("MCP get_catalysts default min_lims comes from the manifest threshold (85), not the stored snapshot threshold", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "get_catalysts", { city_id: "dual" });
  expect(isError).toBe(false);
  expect(payload!.threshold).toBe(85);
});

// (4) Borough filtering + normalization (case / space / hyphen)
test("HTTP catalysts borough filter returns only matching borough", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=nyc&borough=Manhattan`), testEnv() as never);
  expect(response.status).toBe(200);
  const json = (await response.json()) as { catalysts: { borough: string }[] };
  expect(json.catalysts.length).toBe(1);
  expect(json.catalysts[0].borough).toBe("Manhattan");
});

test("HTTP catalysts borough normalizes case", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=nyc&borough=manhattan`), testEnv() as never);
  const json = (await response.json()) as { catalysts: unknown[] };
  expect(json.catalysts.length).toBe(1);
});

test("HTTP catalysts borough normalizes spaces and hyphens to underscores", async () => {
  const bySpace = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=nyc&borough=washington heights`), testEnv() as never);
  expect((await bySpace.json() as { catalysts: unknown[] }).catalysts.length).toBe(1);
  const byHyphen = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=nyc&borough=washington-heights`), testEnv() as never);
  expect((await byHyphen.json() as { catalysts: unknown[] }).catalysts.length).toBe(1);
});

test("MCP get_catalysts borough filter matches after normalization", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "get_catalysts", { city_id: "nyc", borough: "brooklyn" });
  expect(isError).toBe(false);
  const cats = payload!.catalysts as { borough: string }[];
  expect(cats.length).toBe(1);
  expect(cats[0].borough).toBe("Brooklyn");
});

// (4b) US-190 drift resolution: MCP get_submarkets now honors `borough`, matching HTTP.
test("MCP get_submarkets honors the borough filter", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "get_submarkets", { city_id: "nyc", borough: "Manhattan" });
  expect(isError).toBe(false);
  const sub = payload!.submarkets as { id: string; borough: string }[];
  expect(sub.length).toBe(1);
  expect(sub[0].borough).toBe("Manhattan");
});

test("MCP get_submarkets without borough returns every submarket", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "get_submarkets", { city_id: "nyc" });
  expect(isError).toBe(false);
  expect((payload!.submarkets as unknown[]).length).toBe(1);
});

// (5) Catalyst trim shape: HTTP full vs MCP trimmed (3-field)
test("HTTP catalysts return full entries including extra attributes", async () => {
  const response = await worker.fetch(new Request(`${ORIGIN}/api/v1/catalysts?city_id=nyc`), testEnv() as never);
  expect(response.status).toBe(200);
  const json = (await response.json()) as { catalysts: Record<string, unknown>[] };
  const entry = json.catalysts[0];
  expect(entry.h3_index).toBeTruthy();
  expect(entry.lims_score).toBeTruthy();
  expect(entry.borough).toBeTruthy();
  expect(entry.city_id).toBe("nyc");
  expect(entry.city_name).toBe("New York City");
});

test("MCP get_catalysts return trimmed 3-field objects", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "get_catalysts", { city_id: "nyc" });
  expect(isError).toBe(false);
  const entry = (payload!.catalysts as Record<string, unknown>[])[0];
  expect(Object.keys(entry).sort()).toEqual(["borough", "h3_index", "lims_score"]);
  expect(entry.city_id).toBeUndefined();
  expect(entry.city_name).toBeUndefined();
});

// (6) SHAP strip: include_shap=false omits shap_attributions; true/omit keeps it
test("HTTP predict strips shap_attributions when include_shap=false", async () => {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/predict`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ h3_index: "892a10708b7ffff", include_shap: false }),
    }),
    testEnv() as never,
  );
  expect(response.status).toBe(200);
  const json = (await response.json()) as { shap_attributions?: unknown; h3_index: string };
  expect(json.shap_attributions).toBeUndefined();
  expect(json.h3_index).toBe("892a10708b7ffff");
});

test("HTTP predict keeps shap_attributions when include_shap=true", async () => {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/predict`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ h3_index: "892a10708b7ffff", include_shap: true }),
    }),
    testEnv() as never,
  );
  expect(response.status).toBe(200);
  const json = (await response.json()) as { shap_attributions?: unknown };
  expect(Array.isArray(json.shap_attributions)).toBe(true);
});

test("HTTP predict keeps shap_attributions when include_shap is omitted", async () => {
  const response = await worker.fetch(
    new Request(`${ORIGIN}/api/v1/predict`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ h3_index: "892a10708b7ffff" }),
    }),
    testEnv() as never,
  );
  expect(response.status).toBe(200);
  const json = (await response.json()) as { shap_attributions?: unknown };
  expect(Array.isArray(json.shap_attributions)).toBe(true);
});

test("MCP predict_cell strips shap_attributions when include_shap=false", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "predict_cell", { h3_index: "892a10708b7ffff", include_shap: false });
  expect(isError).toBe(false);
  expect((payload as { shap_attributions?: unknown }).shap_attributions).toBeUndefined();
});

test("MCP predict_cell keeps shap_attributions when include_shap=true", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "predict_cell", { h3_index: "892a10708b7ffff", include_shap: true });
  expect(isError).toBe(false);
  expect(Array.isArray((payload as { shap_attributions?: unknown }).shap_attributions)).toBe(true);
});

test("MCP predict_cell keeps shap_attributions when include_shap is omitted", async () => {
  const { isError, payload } = await mcpTool(testEnv() as never, "predict_cell", { h3_index: "892a10708b7ffff" });
  expect(isError).toBe(false);
  expect(Array.isArray((payload as { shap_attributions?: unknown }).shap_attributions)).toBe(true);
});
