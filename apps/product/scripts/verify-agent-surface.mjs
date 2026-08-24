import { access, readFile } from "node:fs/promises";
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
  const types = blocks.map((block) => block["@type"]);
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

console.log("AGENT_SURFACE_OK");
