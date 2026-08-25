/**
 * WebMCP bridge: exposes the site's key knowledge actions to AI agents in the
 * browser via navigator.modelContext (WICG WebMCP). The tool set mirrors the
 * edge MCP server at /mcp so agents get the same surface either way.
 *
 * The API is still shipping: Chrome's origin-trial build exposed
 * provideContext({tools}), while the current spec draft registers tools
 * individually with registerTool(). Both are supported here, guarded, and
 * no-ops when the API is absent.
 */

const SITE_GUIDE_URL = "/llms.txt";

async function fetchJson(url) {
  const response = await fetch(url, { headers: { accept: "application/json" } });
  if (!response.ok) throw new Error(`${url} returned ${response.status}`);
  return response.json();
}

const TOOLS = [
  {
    name: "list_cities",
    description:
      "List every registered Urban Signal metro with its state and how many of the four signal feeds (permits, 311, licenses, deeds) it publishes.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    async execute() {
      const facts = await fetchJson("/facts.json");
      return {
        count: facts.metros.length,
        cities: facts.metros.map(({ id, name, state, feeds }) => ({
          id,
          name,
          state,
          feeds_available: feeds.filter(Boolean).length,
        })),
        limitations: facts.limitations,
      };
    },
  },
  {
    name: "get_product_facts",
    description:
      "Return Urban Signal's machine-readable product facts: metros, feed platforms and cadences, pipeline stages, model horizons, and stated limitations.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    async execute() {
      return fetchJson("/facts.json");
    },
  },
  {
    name: "get_city_brief",
    description:
      "Return one metro's registry-derived brief: coverage geometry, divisions and submarkets, per-feed platform, watermark column, poll interval, and source-contract path.",
    inputSchema: {
      type: "object",
      properties: {
        city_id: { type: "string", description: "Metro id from list_cities (for example 'nyc')." },
      },
      required: ["city_id"],
      additionalProperties: false,
    },
    async execute({ city_id }) {
      const id = String(city_id ?? "").trim().toLowerCase();
      if (!id) throw new Error("city_id is required — call list_cities first.");
      const brief = await fetch(`/public/cities/${encodeURIComponent(id)}.json`);
      if (!brief.ok) throw new Error(`No city brief for '${id}' — call list_cities for valid ids.`);
      return brief.json();
    },
  },
  {
    name: "get_site_guide",
    description:
      "Return the llms.txt guide to this site: canonical resources, section pages, per-city machine briefs, and stated limitations.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    async execute() {
      const response = await fetch(SITE_GUIDE_URL);
      if (!response.ok) throw new Error(`${SITE_GUIDE_URL} returned ${response.status}`);
      return { content: await response.text() };
    },
  },
];

function register(modelContext) {
  // Unregistering is handled by the agent host dropping the page context;
  // the signal is still wired through where the API accepts one.
  const controller = new AbortController();
  if (typeof modelContext.registerTool === "function") {
    for (const tool of TOOLS) modelContext.registerTool(tool, { signal: controller.signal });
  } else if (typeof modelContext.provideContext === "function") {
    modelContext.provideContext({ tools: TOOLS }, { signal: controller.signal });
  }
}

if (typeof navigator !== "undefined" && navigator.modelContext) {
  try {
    register(navigator.modelContext);
  } catch {
    // Discovery surface only — never break page load over registration races.
  }
}
