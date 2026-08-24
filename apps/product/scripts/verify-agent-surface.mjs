import { access, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const site = resolve(import.meta.dirname, "..");
const repo = resolve(site, "../..");
const html = await readFile(resolve(site, "index.html"), "utf8");
const facts = JSON.parse(await readFile(resolve(site, "public/facts.json"), "utf8"));
const llms = await readFile(resolve(site, "public/llms.txt"), "utf8");
const full = await readFile(resolve(site, "public/llms-full.txt"), "utf8");

for (const marker of ['type="application/ld+json"', 'href="llms.txt"', 'href="facts.json"', 'href="llms-full.txt"']) {
  if (!html.includes(marker)) throw new Error(`Missing agent discovery marker: ${marker}`);
}
for (const stale of ["174m²", "E 139°", "UPDATED: AUG", "CATALYST WATCH"]) {
  if (html.includes(stale)) throw new Error(`Stale or misleading visible metadata remains: ${stale}`);
}
for (const disclosure of ["ILLUSTRATIVE H3 CELL", "EXAMPLE COMPOSITION", "not a live prediction or a performance claim"]) {
  if (!html.includes(disclosure)) throw new Error(`Missing illustrative disclosure: ${disclosure}`);
}
if (facts.limitations.length < 3 || !llms.includes("Important limitations") || !full.includes("Claims and limitations")) {
  throw new Error("Agent resources do not state product limitations");
}
if (facts.metros.length !== 17) throw new Error(`Expected 17 verified metros, received ${facts.metros.length}`);

for (const entry of [...facts.metros, ...facts.pipeline]) {
  const path = entry.evidence_path || entry.source_path;
  if (!path) throw new Error(`Missing repository evidence path for ${entry.id}`);
  await access(resolve(repo, path));
}
for (const path of ["apps/api/src/spatial/city_registry.py", "apps/api/src/schemas/models.py", "apps/api/src/spatial/h3_indexer.py", "apps/api/src/features/lims_calculator.py", "apps/api/src/export/snapshot_builder.py"]) {
  if (!html.includes(path)) throw new Error(`Human evidence trace omits ${path}`);
  if (!full.includes(path)) throw new Error(`Agent evidence trace omits ${path}`);
}

console.log("AGENT_SURFACE_OK");
