import { access, readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const dist = resolve(root, "dist");
const facts = JSON.parse(await readFile(resolve(root, "public/facts.json"), "utf8"));
const required = [
  ["/", "index.html"],
  ["/system/", "system/index.html"],
  ["/evidence/", "evidence/index.html"],
  ["/methodology/", "methodology/index.html"],
  ["/architecture/", "architecture/index.html"],
  ["/cities/", "cities/index.html"],
];

for (const [route, file] of required) {
  await access(resolve(dist, file));
  const html = await readFile(resolve(dist, file), "utf8");
  if (!html.includes(`<link rel="canonical" href="https://urban-signal.harlanljones.com${route}">`)) {
    throw new Error(`Missing canonical route marker for ${route}`);
  }
}

const cityDirs = (await readdir(resolve(dist, "cities"), { withFileTypes: true }))
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name);
const expected = facts.metros.map((metro) => metro.id).sort();
const actual = cityDirs.filter((id) => id !== "index").sort();
if (JSON.stringify(actual) !== JSON.stringify(expected)) {
  throw new Error(`City route mismatch: expected ${expected.length}, found ${actual.length}`);
}
for (const id of expected) {
  await access(resolve(dist, "cities", id, "index.html"));
}

console.log(`MULTI_PAGE_OK (${required.length} section routes, ${expected.length} city routes)`);
