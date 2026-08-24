import { readFile } from "node:fs/promises";

const repo = new URL("../", import.meta.url);
const dist = new URL("apps/product/dist/", repo);
const ROUTES = { home: "index.html", system: "system/index.html", evidence: "evidence/index.html", methodology: "methodology/index.html", architecture: "architecture/index.html", cities: "cities/index.html" };

const pages = {};
for (const [name, file] of Object.entries(ROUTES)) {
  pages[name] = await readFile(new URL(file, dist), "utf8");
}
const html = pages.home;
const js = await readFile(new URL("apps/product/src/main.js", repo), "utf8");
const registry = await readFile(new URL("apps/api/src/spatial/city_registry.py", repo), "utf8");
const facts = JSON.parse(await readFile(new URL("apps/product/public/facts.json", repo), "utf8"));
const product = await readFile(new URL("PRODUCT.md", repo), "utf8");

const registryIds = [...registry.matchAll(/^    CityId\.([A-Z_]+): CityRegistration\(/gm)].map((match) => match[1].toLowerCase()).sort();
const factIds = facts.metros.map(({ id }) => id).sort();
if (registryIds.length !== factIds.length || registryIds.some((id, index) => id !== factIds[index])) {
  throw new Error(`Marketing facts differ from registry IDs: registry=${registryIds.join(",")} facts=${factIds.join(",")}`);
}
if (!product.includes("metros are currently registered")) throw new Error("PRODUCT.md registered-metro statement is missing");
if (!html.includes("data-metro-count") || !js.includes("siteFacts.metros.length")) throw new Error("Rendered metro count is not bound to facts.json");

// Requirement phrases are asserted against the whole multi-page site (any page
// may carry them); the metro-count binding above stays home-specific.
const siteText = Object.values(pages).join("\n").toLowerCase();
for (const phrase of ["five inspectable contracts", "coverage is not a marketing footnote", "6-, 12-, and 18-month horizons", "explore a real signal", "audit the implementation"]) {
  if (!siteText.includes(phrase) && !js.toLowerCase().includes(phrase)) throw new Error(`Missing requirement: ${phrase}`);
}

for (const metro of facts.metros) {
  if (!metro.name || !metro.state || !Array.isArray(metro.feeds) || metro.feeds.length !== 4) throw new Error(`Malformed metro facts: ${metro.id}`);
}

console.log("SITE_CONTENT_OK");
