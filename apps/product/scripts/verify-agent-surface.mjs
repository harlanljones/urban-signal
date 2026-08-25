import { access, readdir, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { SITE_ORIGIN } from "./shell.mjs";

const site = resolve(import.meta.dirname, "..");
const repo = resolve(site, "../..");
const ROUTES = { home: "index.html", system: "system/index.html", evidence: "evidence/index.html", methodology: "methodology/index.html", architecture: "architecture/index.html", cities: "cities/index.html" };

const pages = {};
for (const [name, file] of Object.entries(ROUTES)) {
  pages[name] = await readFile(resolve(site, "dist", file), "utf8");
}
const html = pages.home;
const facts = JSON.parse(await readFile(resolve(site, "public/facts.json"), "utf8"));
const llms = await readFile(resolve(site, "public/llms.txt"), "utf8");
const full = await readFile(resolve(site, "public/llms-full.txt"), "utf8");

// Agent discovery markers must exist on EVERY route, not just the home page.
for (const [route, page] of Object.entries(pages)) {
  for (const marker of ['type="application/ld+json"', 'href="/llms.txt"', 'href="/facts.json"', 'href="/llms-full.txt"']) {
    if (!page.includes(marker)) throw new Error(`Missing agent discovery marker on /${route === "home" ? "" : route + "/"}: ${marker}`);
  }
  for (const stale of ["174m²", "E 139°", "UPDATED: AUG", "CATALYST WATCH"]) {
    if (page.includes(stale)) throw new Error(`Stale or misleading visible metadata remains on /${route === "home" ? "" : route + "/"}: ${stale}`);
  }
}

// Illustrative-value disclosures live with the score panel on /methodology/.
for (const disclosure of ["ILLUSTRATIVE H3 CELL", "EXAMPLE COMPOSITION", "not a live prediction or a performance claim"]) {
  if (!pages.methodology.includes(disclosure)) throw new Error(`Missing illustrative disclosure on /methodology/: ${disclosure}`);
}

if (facts.limitations.length < 3 || !llms.includes("Important limitations") || !full.includes("Claims and limitations")) {
  throw new Error("Agent resources do not state product limitations");
}
if (!facts.metros.length) throw new Error("facts.json lists no metros");

// The agent guide must route to every section page.
for (const path of ["/system/", "/evidence/", "/methodology/", "/architecture/", "/cities/"]) {
  if (!llms.includes(path)) throw new Error(`llms.txt omits section page ${path}`);
}

// The expanded context must explain the per-city machine briefs by name.
if (!full.includes("Per-city machine briefs")) throw new Error("llms-full.txt omits the per-city machine briefs section");
for (const field of ["watermark_col", "interval_seconds", "evidence_path", "generated_from"]) {
  if (!full.includes(field)) throw new Error(`llms-full.txt per-city briefs schema omits ${field}`);
}

for (const metro of facts.metros) {
  const detail = resolve(site, "dist/public/cities", `${metro.id}.json`);
  try {
    await access(detail);
  } catch {
    throw new Error(`Missing registry-derived city detail for ${metro.id} (run: bun run facts:export)`);
  }
  const parsed = JSON.parse(await readFile(detail, "utf8"));
  if (parsed.generated_from !== "apps/api/src/spatial/city_registry.py REGISTRY") {
    throw new Error(`City detail for ${metro.id} is not registry-derived`);
  }
  const cityPage = resolve(site, "dist/cities", metro.id, "index.html");
  try {
    await access(cityPage);
  } catch {
    throw new Error(`Missing generated city page for ${metro.id} (run: bun run build)`);
  }
  const page = await readFile(cityPage, "utf8");
  if (!page.includes(metro.name)) throw new Error(`City page ${metro.id} omits its own name`);
  if (!page.includes("/dashboard")) throw new Error(`City page ${metro.id} omits the dashboard link`);
  if (!page.includes(`/public/cities/${metro.id}.json`)) throw new Error(`City page ${metro.id} omits its machine twin`);
}

// The end-to-end evidence trace lives on /evidence/; agent surfaces must carry it too.
for (const path of ["apps/api/src/spatial/city_registry.py", "apps/api/src/schemas/models.py", "apps/api/src/spatial/h3_indexer.py", "apps/api/src/features/lims_calculator.py", "apps/api/src/export/snapshot_builder.py"]) {
  if (!pages.evidence.includes(path)) throw new Error(`Human evidence trace omits ${path}`);
  if (!full.includes(path)) throw new Error(`Agent evidence trace omits ${path}`);
}

// SEO: unique titles + descriptions per route; canonical + OG present; JSON-LD parses with expected types.
const titles = Object.values(pages).map((page) => page.match(/<title>([^<]*)<\/title>/)?.[1]);
if (titles.some((t) => !t) || new Set(titles).size !== Object.keys(pages).length) {
  throw new Error("Page titles are missing or not unique across routes");
}
const descriptions = Object.values(pages).map((page) => page.match(/name="description" content="([^"]*)"/)?.[1]);
if (descriptions.some((d) => !d) || new Set(descriptions).size !== Object.keys(pages).length) {
  throw new Error("Meta descriptions are missing or not unique across routes");
}
const expectedTypes = {
  home: ["WebSite"],
  system: ["TechArticle"],
  evidence: ["TechArticle"],
  methodology: ["TechArticle"],
  architecture: ["WebSite"],
  cities: ["WebSite"],
};
for (const [route, page] of Object.entries(pages)) {
  const path = route === "home" ? "/" : `/${route}/`;
  if (!page.includes(`<link rel="canonical" href="${SITE_ORIGIN}${path}">`)) throw new Error(`Missing canonical on ${path}`);
  if (!page.includes(`<meta property="og:url" content="${SITE_ORIGIN}${path}">`)) throw new Error(`Missing og:url on ${path}`);
  if (!page.includes('<meta name="twitter:card" content="summary">')) throw new Error(`Missing twitter:card on ${path}`);
  const blocks = [...page.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)].map((m) => JSON.parse(m[1]));
  const types = blocks.flatMap((block) => [
    block["@type"],
    ...(block["@graph"] ?? []).map((entity) => entity["@type"]),
  ]).filter(Boolean);
  for (const expected of expectedTypes[route]) {
    if (!types.includes(expected)) throw new Error(`Missing ${expected} JSON-LD on ${path} (found: ${types.join(",")})`);
  }
}

// Sitemap must enumerate every route including every city page.
const sitemap = await readFile(resolve(site, "dist/sitemap.xml"), "utf8");
const sitemapLocs = [...sitemap.matchAll(/<loc>([^<]*)<\/loc>/g)].map((m) => m[1]);
const expectedPaths = ["/", "/system/", "/evidence/", "/methodology/", "/architecture/", "/cities/", ...facts.metros.map((metro) => `/cities/${metro.id}/`)];
for (const expected of expectedPaths) {
  if (!sitemapLocs.includes(`${SITE_ORIGIN}${expected}`)) throw new Error(`Sitemap missing ${expected}`);
}

// ---------------------------------------------------------------------------
// Agent discovery surface: markdown twins, .well-known documents, MCP/WebMCP.
// The scanner-facing contract lives in scripts/generate-agent-surfaces.mjs and
// worker.mjs; these checks pin what will actually be served.
// ---------------------------------------------------------------------------

// Every HTML route must have its text/markdown twin next to it, fronted by an
// H1 and the canonical provenance note.
const SECTION_DIRS = ["system", "evidence", "methodology", "architecture", "cities", "compare", "glossary", "changelog", "faq"];
const routeDirs = [
  resolve(site, "dist"),
  ...SECTION_DIRS.map((dir) => resolve(site, "dist", dir)),
  ...facts.metros.map((metro) => resolve(site, "dist", "cities", metro.id)),
];
for (const dir of routeDirs) {
  const twin = resolve(dir, "index.md");
  try {
    await access(twin);
  } catch {
    throw new Error(`Missing markdown twin at ${twin.replace(site, "")}`);
  }
  const md = await readFile(twin, "utf8");
  if (!md.startsWith("# ") || !md.includes("the HTML page is canonical")) {
    throw new Error(`Malformed markdown twin at ${twin.replace(site, "")}`);
  }
}

// RFC 9727 api-catalog: linkset entries carry anchors and service relations.
const catalog = JSON.parse(await readFile(resolve(site, "dist/.well-known/api-catalog"), "utf8"));
if (!Array.isArray(catalog.linkset) || catalog.linkset.length < 2) {
  throw new Error("api-catalog must list the site anchor and the edge data API");
}
for (const entry of catalog.linkset) {
  if (!entry.anchor?.startsWith("https://")) throw new Error("api-catalog entry missing absolute anchor");
  for (const rel of ["service-desc", "service-doc"]) {
    if (!entry[rel]?.[0]?.href) throw new Error(`api-catalog ${entry.anchor} omits ${rel}`);
  }
}

// The site's own OpenAPI spec must enumerate the real static JSON surface.
const openApi = JSON.parse(await readFile(resolve(site, "dist/.well-known/openapi.json"), "utf8"));
if (openApi.servers?.[0]?.url !== SITE_ORIGIN) throw new Error("openapi.json server origin mismatch");
const briefPath = "/public/cities/{city_id}.json";
for (const path of ["/facts.json", briefPath, "/healthz"]) {
  if (!openApi.paths?.[path]) throw new Error(`openapi.json omits ${path}`);
}
const briefEnum = openApi.paths[briefPath].get.parameters[0].schema.enum;
const metroIds = facts.metros.map(({ id }) => id).sort();
if (JSON.stringify([...briefEnum].sort()) !== JSON.stringify(metroIds)) {
  throw new Error("openapi.json city_id enum differs from facts.json metros");
}

// RFC 9728 protected resource metadata: public site, no authorization servers.
const prm = JSON.parse(await readFile(resolve(site, "dist/.well-known/oauth-protected-resource"), "utf8"));
if (prm.resource !== `${SITE_ORIGIN}/` || !Array.isArray(prm.authorization_servers)) {
  throw new Error("oauth-protected-resource must state the resource origin and authorization_servers");
}
if (prm.authorization_servers.length !== 0) {
  throw new Error("No OAuth AS exists — advertising one would mislead agents");
}
if (!prm.resource_documentation?.endsWith("/auth.md")) {
  throw new Error("oauth-protected-resource must point at auth.md");
}

// auth.md: self-contained statement with the required heading.
const authMd = await readFile(resolve(site, "dist/auth.md"), "utf8");
if (!/^# .*auth\.md/m.test(authMd)) throw new Error("auth.md H1 must contain 'auth.md'");
for (const required of ["Authentication methods", "Registration / provisioning", "Credentials"]) {
  if (!authMd.includes(required)) throw new Error(`auth.md omits '${required}'`);
}

// MCP server card: serverInfo, transport endpoint, capabilities.
const card = JSON.parse(await readFile(resolve(site, "dist/.well-known/mcp/server-card.json"), "utf8"));
if (!card.serverInfo?.name || !card.serverInfo?.version) throw new Error("server-card.json missing serverInfo name/version");
if (!card.transport?.endpoint?.startsWith("https://") || !card.transport.endpoint.endsWith("/mcp")) {
  throw new Error("server-card.json transport endpoint must be the /mcp URL");
}
if (!card.capabilities?.tools) throw new Error("server-card.json missing capabilities.tools");
const cardToolNames = card.tools.map((tool) => tool.name);
const workerSource = await readFile(resolve(site, "worker.mjs"), "utf8");
for (const toolName of cardToolNames) {
  if (!workerSource.includes(`case "${toolName}"`)) throw new Error(`Worker does not implement advertised tool '${toolName}'`);
}

// Skills discovery index: schema field, digest matches the artifact bytes.
const skillsIndex = JSON.parse(await readFile(resolve(site, "dist/.well-known/agent-skills/index.json"), "utf8"));
if (skillsIndex.$schema !== "https://schemas.agentskills.io/discovery/0.2.0/schema.json") {
  throw new Error("agent-skills/index.json $schema must be the v0.2.0 schema");
}
for (const skill of skillsIndex.skills) {
  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(skill.name)) throw new Error(`Invalid skill name '${skill.name}'`);
  if (skill.type !== "skill-md" || !skill.description || !skill.url) throw new Error(`Incomplete skill entry '${skill.name}'`);
  const artifact = await readFile(resolve(site, "dist/.well-known/agent-skills", skill.name, "SKILL.md"), "utf8");
  const digest = createHash("sha256").update(artifact, "utf8").digest("hex");
  if (skill.digest !== `sha256:${digest}`) throw new Error(`Digest mismatch for skill '${skill.name}'`);
  if (!/^---\nname: /.test(artifact)) throw new Error(`Skill '${skill.name}' lacks YAML frontmatter`);
}

// ARD manifest: exactly one of url|data per entry, urn identifiers, queries.
const ard = JSON.parse(await readFile(resolve(site, "dist/.well-known/ai-catalog.json"), "utf8"));
const host = new URL(SITE_ORIGIN).hostname;
if (!ard.specVersion || ard.host?.identifier !== `did:web:${host}`) throw new Error("ai-catalog.json host block malformed");
if (!Array.isArray(ard.entries) || !ard.entries.length) throw new Error("ai-catalog.json has no entries");
for (const entry of ard.entries) {
  const hasUrl = typeof entry.url === "string";
  const hasData = entry.data !== undefined;
  if (hasUrl === hasData) throw new Error(`${entry.identifier}: exactly one of url|data is required`);
  if (!entry.identifier?.startsWith(`urn:air:${host}:`)) throw new Error(`Bad ARD identifier: ${entry.identifier}`);
  if (!entry.displayName || !entry.type) throw new Error(`${entry.identifier} needs displayName and type`);
  const queries = entry.representativeQueries ?? [];
  if (queries.length < 2 || queries.length > 5) throw new Error(`${entry.identifier} needs 2-5 representativeQueries`);
}

// robots.txt must advertise the manifest; head/footer must link it.
const robots = await readFile(resolve(site, "dist/robots.txt"), "utf8");
if (!robots.includes(`Agentmap: ${SITE_ORIGIN}/.well-known/ai-catalog.json`)) {
  throw new Error("robots.txt missing Agentmap directive");
}
for (const [, page] of Object.entries(pages)) {
  for (const marker of ['rel="ai-catalog"', '/src/webmcp.js']) {
    if (!page.includes(marker)) throw new Error(`Page missing agent surface marker: ${marker}`);
  }
}

// Edge worker tripwires: Link relations, negotiation, healthz, MCP endpoint.
for (const wire of ['rel="api-catalog"', 'rel="describedby"', 'rel="service-doc"', 'rel="service-desc"', 'rel="alternate"; type="text/markdown"', 'text/markdown', "x-markdown-tokens", "/healthz", '"/mcp"']) {
  if (!workerSource.includes(wire)) throw new Error(`worker.mjs missing agent surface: ${wire}`);
}
const webmcpSource = await readFile(resolve(site, "src/webmcp.js"), "utf8");
if (!webmcpSource.includes("navigator.modelContext")) throw new Error("webmcp.js never checks navigator.modelContext");

console.log("AGENT_SURFACE_OK");
