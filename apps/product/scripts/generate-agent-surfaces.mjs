/**
 * Build-time generator for the product site's agent discovery documents.
 *
 * Everything lands in dist/.well-known/ as static artifacts so the lint gate
 * can verify exactly what will be served:
 *
 *   /.well-known/api-catalog                    RFC 9727 linkset catalog
 *   /.well-known/oauth-protected-resource       RFC 9728 PRM (public, no AS)
 *   /.well-known/mcp/server-card.json           MCP Server Card (SEP-1649)
 *   /.well-known/agent-skills/index.json        Agent Skills discovery (v0.2.0)
 *   /.well-known/agent-skills/<n>/SKILL.md      skill artifacts (sha256-digested)
 *   /.well-known/ai-catalog.json                ARD capability manifest
 *
 * The edge API on us-dash.harlanljones.com publishes its own equivalent
 * surface (apps/dashboard/src/index.ts); the catalog and manifest here
 * cross-reference those live URLs rather than duplicating them.
 */
import { mkdir, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { SITE_ORIGIN } from "./shell.mjs";
import {
  MCP_SERVER_NAME,
  MCP_SERVER_TITLE,
  PRODUCT_MCP_TOOLS,
} from "./mcp-tools.mjs";

const DASH_ORIGIN = "https://us-dash.harlanljones.com";
const REPOSITORY = "https://github.com/harlanljones/urban-signal";
const OPENAPI_TYPE = "application/vnd.oai.openapi+json";

function jsonDocument(body) {
  return `${JSON.stringify(body, null, 2)}\n`;
}

// ---------------------------------------------------------------------------
// Skill artifacts
// ---------------------------------------------------------------------------

const PRODUCT_FACTS_SKILL = `---
name: urban-signal-product-facts
description: Consume Urban Signal's machine-readable product facts and registry-derived city briefs — registered metros, per-feed platforms, watermark columns, poll intervals, division/submarket structure, and provenance. Use when an agent needs structured ground truth about what Urban Signal covers instead of scraping rendered pages.
---

# Urban Signal product facts and city briefs

All resources are public JSON on ${SITE_ORIGIN}. They are generated directly
from the authoritative Python registry (\`REGISTRY\` in
\`apps/api/src/spatial/city_registry.py\`) via \`scripts/export_site_facts.py\`;
they are not hand-authored.

## Documents

- \`GET /facts.json\` — product-level document: \`metros\` (id, name, state,
  divisions, feed availability booleans, platform contracts), \`feed_labels\`,
  \`pipeline\` stages, \`model_horizons_months\`, and stated \`limitations\`.
- \`GET /public/cities/<id>.json\` — one brief per metro. Metro ids come from
  \`facts.json\` (\`metros[].id\`). Brief schema:

  - \`id\`, \`name\`, \`state\`: registry identity.
  - \`center\`, \`metro_bbox\`: coverage geometry.
  - \`divisions\`: key → \`{name, center, bbox, submarkets[]}\`.
  - \`feeds\`: keyed by \`permits\`, \`311\`, \`sla\`, \`deeds\`. Each non-null entry has
    \`platform\`, \`watermark_col\`, \`interval_seconds\`, \`topic\`. A \`null\` value means
    the feed is absent for that metro — absence is a fact, not a gap.
  - \`evidence_path\`: repository path of the metro's source-contract module.
  - \`generated_from\`: always \`"apps/api/src/spatial/city_registry.py REGISTRY"\`.

## Rules

- Treat \`facts.json\` as the coverage authority; never infer uniform four-feed
  coverage across metros.
- Prefer briefs over scraping HTML pages; if a metro or feed is missing from a
  brief, it is not registered.
- Hero cell values and score compositions shown on marketing pages are
  illustrative examples, not model outputs.
`;

const METHODOLOGY_SKILL = `---
name: urban-signal-methodology
description: Understand the Leading Indicator Momentum Score (LIMS) methodology behind Urban Signal — composition across 6-, 12-, and 18-month horizons, which inputs are measured vs illustrative, and how to cite the system's claims correctly. Use before quoting any Urban Signal number or claim in downstream analysis.
---

# Urban Signal methodology essentials

## Score composition

The Leading Indicator Momentum Score (LIMS) composes signal families from
municipal telemetry — building permits, 311 service requests, business
licenses, deeds — normalized onto H3 (resolutions 7/8/9) cells. Horizons are
6, 12, and 18 months. Feature ingredients include time-decayed CapEx density,
permit velocity, 311 shift dynamics, and license activity.

## What is illustrative (do not quote as results)

- Hero inspection fields on marketing pages.
- The displayed 68/100 composition walkthrough — an example composition, not a
  live prediction or performance claim.

## Claim discipline

- No customer, adoption, or independently validated performance claims exist.
- Feed coverage varies by metro; check \`/facts.json\` and
  \`/public/cities/<id>.json\` before asserting what a metro supports.
- Full reasoning lives at ${SITE_ORIGIN}/methodology/ with the evidence trace
  at ${SITE_ORIGIN}/evidence/ and source at ${REPOSITORY}.
`;

const SKILL_ARTIFACTS = [
  {
    name: "urban-signal-product-facts",
    description:
      "Consume Urban Signal's machine-readable product facts and registry-derived city briefs: registered metros, feed platforms, watermark columns, poll intervals, and provenance.",
    body: PRODUCT_FACTS_SKILL,
  },
  {
    name: "urban-signal-methodology",
    description:
      "Understand the LIMS momentum-score methodology, its 6/12/18-month horizons, and which published values are explicitly illustrative before citing Urban Signal anywhere.",
    body: METHODOLOGY_SKILL,
  },
];

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

function apiCatalog() {
  return jsonDocument({
    linkset: [
      {
        anchor: `${SITE_ORIGIN}/`,
        describedby: [{ href: `${SITE_ORIGIN}/facts.json`, type: "application/json" }],
        "service-desc": [{ href: `${SITE_ORIGIN}/.well-known/openapi.json`, type: OPENAPI_TYPE }],
        "service-doc": [
          { href: `${SITE_ORIGIN}/llms.txt`, type: "text/plain" },
          { href: `${SITE_ORIGIN}/llms-full.txt`, type: "text/plain" },
        ],
        status: [{ href: `${SITE_ORIGIN}/healthz`, type: "application/json" }],
        alternate: [{ href: `${SITE_ORIGIN}/.well-known/ai-catalog.json`, type: "application/json" }],
      },
      {
        // Live read-only data API served by the dashboard worker.
        anchor: `${DASH_ORIGIN}/api/v1`,
        "service-desc": [{ href: `${DASH_ORIGIN}/openapi.json`, type: OPENAPI_TYPE }],
        "service-doc": [
          {
            href: `${DASH_ORIGIN}/.well-known/agent-skills/urban-signal-data-api/SKILL.md`,
            type: "text/markdown",
          },
        ],
        status: [{ href: `${DASH_ORIGIN}/health`, type: "application/json" }],
      },
    ],
  });
}

/**
 * OpenAPI contract for this host's read-only JSON surface. These are static
 * registry-derived artifacts, so the spec enumerates exact metro ids.
 */
function siteApiSpec(facts) {
  const cityIds = facts.metros.map(({ id }) => id);
  return jsonDocument({
    openapi: "3.1.0",
    info: {
      title: "Urban Signal Product Knowledge API",
      summary: "Registry-derived product facts and per-city briefs served as static JSON.",
      description:
        "Read-only, unauthenticated documents generated from apps/api/src/spatial/city_registry.py REGISTRY via scripts/export_site_facts.py. Coverage facts are authoritative; never infer uniform feed coverage.",
      version: "2.0.0",
    },
    servers: [{ url: SITE_ORIGIN }],
    paths: {
      "/facts.json": {
        get: {
          operationId: "getProductFacts",
          summary: "Product-level facts: registered metros, feed platforms, pipeline stages, horizons, limitations.",
          responses: { "200": { description: "Product facts document.", content: { "application/json": { schema: { type: "object" } } } } },
        },
      },
      "/public/cities/{city_id}.json": {
        get: {
          operationId: "getCityBrief",
          summary: "One metro's registry-derived brief: geometry, divisions/submarkets, per-feed platform, watermark column, poll interval.",
          parameters: [
            {
              name: "city_id",
              in: "path",
              required: true,
              schema: { type: "string", enum: cityIds },
              description: "Metro id from facts.json metros[].id.",
            },
          ],
          responses: {
            "200": { description: "City brief document." },
            "404": { description: "No such metro id — ids are enumerable at /facts.json." },
          },
        },
      },
      "/llms.txt": {
        get: {
          operationId: "getAgentGuide",
          summary: "Agent guide: canonical resources, section pages, limitations.",
          responses: { "200": { description: "Plain-text guide.", content: { "text/plain": {} } } },
        },
      },
      "/llms-full.txt": {
        get: {
          operationId: "getFullAgentContext",
          summary: "Expanded agent context including the per-city brief schema.",
          responses: { "200": { description: "Plain-text context.", content: { "text/plain": {} } } },
        },
      },
      "/healthz": {
        get: {
          operationId: "getHealth",
          summary: "Liveness status for this host.",
          responses: { "200": { description: "Status document.", content: { "application/json": { schema: { type: "object" } } } } },
        },
      },
    },
  });
}

function protectedResourceMetadata() {
  return jsonDocument({
    // Public, read-only site: no authorization server issues tokens for it,
    // and the empty authorization_servers array states that formally.
    resource: `${SITE_ORIGIN}/`,
    authorization_servers: [],
    scopes_supported: [],
    bearer_methods_supported: ["header"],
    resource_documentation: `${SITE_ORIGIN}/auth.md`,
  });
}

function mcpServerCard() {
  return jsonDocument({
    serverInfo: {
      name: MCP_SERVER_NAME,
      title: MCP_SERVER_TITLE,
      version: "2.0.0",
    },
    description:
      "Read-only MCP server over the product knowledge base: registered metros with feed coverage, machine-readable product facts, registry-derived per-city briefs, and the llms.txt site guide.",
    transport: {
      type: "streamable-http",
      endpoint: `${SITE_ORIGIN}/mcp`,
    },
    capabilities: {
      tools: { listChanged: false },
    },
    tools: PRODUCT_MCP_TOOLS.map(({ name, description }) => ({ name, description })),
  });
}

function aiCatalog(facts) {
  const host = new URL(SITE_ORIGIN).hostname;
  const urn = (namespace, name) => `urn:air:${host}:${namespace}:${name}`;
  const cityIds = facts.metros.map(({ id }) => id);
  return jsonDocument({
    specVersion: "1.0",
    host: {
      displayName: "Urban Signal",
      identifier: `did:web:${host}`,
    },
    entries: [
      {
        identifier: urn("data", "product-facts"),
        displayName: "Urban Signal Product Facts",
        type: "application/json",
        url: `${SITE_ORIGIN}/facts.json`,
        representativeQueries: [
          "which metros does Urban Signal cover",
          "what municipal feed platforms does Chicago use",
          "what are the stated limitations of Urban Signal",
        ],
      },
      {
        identifier: urn("data", "city-briefs"),
        displayName: "Per-City Machine Briefs",
        type: "application/json",
        data: {
          pattern: "/public/cities/<id>.json",
          generated_from: "apps/api/src/spatial/city_registry.py REGISTRY",
          count: cityIds.length,
          ids: cityIds,
        },
        representativeQueries: [
          "list the boroughs and submarkets of New York City",
          "what is the permit feed watermark column in Austin",
          "does Baltimore publish deeds data",
        ],
      },
      {
        identifier: urn("documentation", "agent-guide"),
        displayName: "llms.txt Agent Guide",
        type: "text/plain",
        url: `${SITE_ORIGIN}/llms.txt`,
        representativeQueries: [
          "give me a summary of the Urban Signal product",
          "where is the evidence trace for one permit record",
        ],
      },
      {
        identifier: urn("documentation", "full-agent-context"),
        displayName: "Full Agent Context",
        type: "text/plain",
        url: `${SITE_ORIGIN}/llms-full.txt`,
        representativeQueries: [
          "explain the urban signal processing pipeline end to end",
          "what schema do the per-city machine briefs follow",
        ],
      },
      {
        identifier: urn("methodology", "lims-score"),
        displayName: "Leading Indicator Momentum Score Methodology",
        type: "text/html",
        url: `${SITE_ORIGIN}/methodology/`,
        representativeQueries: [
          "how is the momentum score composed",
          "which forecast horizons does urban signal support",
        ],
      },
      {
        identifier: urn("mcp", "site-tools"),
        displayName: "Urban Signal Site MCP Server",
        type: "application/json",
        url: `${SITE_ORIGIN}/.well-known/mcp/server-card.json`,
        representativeQueries: [
          "list registered urban signal metros via MCP",
          "get the machine brief for San Francisco",
        ],
      },
      {
        identifier: urn("api", "product-knowledge-api"),
        displayName: "Urban Signal Product Knowledge API",
        type: OPENAPI_TYPE,
        url: `${SITE_ORIGIN}/.well-known/openapi.json`,
        representativeQueries: [
          "fetch the product facts document for urban signal",
          "get the registry-derived brief for Denver",
        ],
      },
      {
        identifier: urn("api", "edge-data-api"),
        displayName: "Urban Signal Edge Data API",
        type: OPENAPI_TYPE,
        url: `${DASH_ORIGIN}/openapi.json`,
        representativeQueries: [
          "query catalyst cells with LIMS scores via the urban signal API",
          "post a point prediction request for an H3 cell",
        ],
      },
    ],
  });
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

export async function generateAgentSurfaces(dist, facts) {
  const wellKnown = resolve(dist, ".well-known");
  await mkdir(resolve(wellKnown, "mcp"), { recursive: true });

  await writeFile(resolve(wellKnown, "api-catalog"), apiCatalog());
  await writeFile(resolve(wellKnown, "oauth-protected-resource"), protectedResourceMetadata());
  await writeFile(resolve(wellKnown, "mcp/server-card.json"), mcpServerCard());
  await writeFile(resolve(wellKnown, "openapi.json"), siteApiSpec(facts));
  await writeFile(resolve(wellKnown, "ai-catalog.json"), aiCatalog(facts));

  for (const skill of SKILL_ARTIFACTS) {
    const skillDir = resolve(wellKnown, "agent-skills", skill.name);
    await mkdir(skillDir, { recursive: true });
    await writeFile(resolve(skillDir, "SKILL.md"), skill.body);
    skill.digest = createHash("sha256").update(skill.body, "utf8").digest("hex");
    skill.url = `${SITE_ORIGIN}/.well-known/agent-skills/${skill.name}/SKILL.md`;
  }

  await writeFile(
    resolve(wellKnown, "agent-skills/index.json"),
    jsonDocument({
      $schema: "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
      skills: SKILL_ARTIFACTS.map(({ name, type = "skill-md", description, url, digest }) => ({
        name,
        type,
        description,
        url,
        digest: `sha256:${digest}`,
      })),
    })
  );
}
