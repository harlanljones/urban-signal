/**
 * Tool contracts for the product site's read-only MCP server (/mcp).
 * Shared by the edge worker (runtime dispatch) and the agent-surfaces build
 * step (server card), so the advertised contract can never drift from the
 * implemented one.
 */
export const MCP_SERVER_NAME = "urban-signal-site";
export const MCP_SERVER_TITLE = "Urban Signal Product Knowledge";
export const MCP_PROTOCOL_VERSION = "2025-06-18";

export const PRODUCT_MCP_TOOLS = [
  {
    name: "list_cities",
    description:
      "List every registered Urban Signal metro with its state and per-feed coverage (permits, 311, licenses, deeds).",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "get_product_facts",
    description:
      "Return the full machine-readable product facts document (metros, feed platforms, pipeline stages, horizons, limitations).",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "get_city_brief",
    description:
      "Return one metro's registry-derived JSON brief: center/bbox, divisions and submarkets, per-feed platform, watermark column, poll interval, and source-contract path.",
    inputSchema: {
      type: "object",
      properties: {
        city_id: { type: "string", description: "Metro id from list_cities (for example 'nyc', 'austin')." },
      },
      required: ["city_id"],
      additionalProperties: false,
    },
  },
  {
    name: "get_site_guide",
    description:
      "Return the llms.txt guide to the product site: canonical resources, section pages, per-city briefs, and stated limitations.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
];
