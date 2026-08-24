import { readFile } from "node:fs/promises";

const repo = new URL("../", import.meta.url);
const html = await readFile(new URL("apps/site/index.html", repo), "utf8");
const js = await readFile(new URL("apps/site/src/main.js", repo), "utf8");
const registry = await readFile(new URL("apps/api/src/spatial/city_registry.py", repo), "utf8");
const facts = JSON.parse(await readFile(new URL("apps/site/public/facts.json", repo), "utf8"));
const product = await readFile(new URL("PRODUCT.md", repo), "utf8");

const registryIds = [...registry.matchAll(/^    CityId\.([A-Z_]+): CityRegistration\(/gm)].map((match) => match[1].toLowerCase()).sort();
const factIds = facts.metros.map(({ id }) => id).sort();
if (registryIds.length !== factIds.length || registryIds.some((id, index) => id !== factIds[index])) {
  throw new Error(`Marketing facts differ from registry IDs: registry=${registryIds.join(",")} facts=${factIds.join(",")}`);
}
if (!product.includes(`Seventeen metros are currently registered`)) throw new Error("PRODUCT.md registered-metro count is stale");
if (!html.includes("data-metro-count") || !js.includes("siteFacts.metros.length")) throw new Error("Rendered metro count is not bound to facts.json");

for (const phrase of ["five inspectable contracts", "coverage is not a marketing footnote", "6-, 12-, and 18-month horizons", "explore a real signal", "audit the implementation"]) {
  if (!html.toLowerCase().includes(phrase) && !js.toLowerCase().includes(phrase)) throw new Error(`Missing requirement: ${phrase}`);
}

for (const metro of facts.metros) {
  if (!metro.name || !metro.state || !Array.isArray(metro.feeds) || metro.feeds.length !== 4) throw new Error(`Malformed metro facts: ${metro.id}`);
}

console.log("SITE_CONTENT_OK");
