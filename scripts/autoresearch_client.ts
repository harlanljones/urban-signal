// Execute the shipped dashboard's actual tile merge, not a copied implementation.
// Bun CPU microbenchmark: deliberately not a browser-rendering/CWV metric.
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { runInNewContext } from "node:vm";
import assert from "node:assert/strict";

const dashboard = readFileSync("apps/dashboard/public/index.html", "utf8");
const match = dashboard.match(/    function mergeTilePayload\(payload\) \{[\s\S]*?\n    \}/);
assert.ok(match, "Shipped tile merge function must remain benchmarkable");
const merge = runInNewContext(`let tileFeatures = new Map(); let gridDirty = false;
${match[0]}
({ reset() { tileFeatures.clear(); gridDirty = false; }, mergeTilePayload,
entries() { return [...tileFeatures.entries()]; }, dirty() { return gridDirty; } })`);
const root = process.argv[2];
const expected: Record<string, string[]> = JSON.parse(readFileSync("scripts/autoresearch_coverage.json", "utf8"));
const expectedCells = new Set(Object.values(expected).flat());
const payloads = readdirSync(join(root, "gridtiles")).sort().map(name =>
  readFileSync(join(root, "gridtiles", name), "utf8"));
const times: number[] = [];
for (let trial = 0; trial < 8; trial++) {
  merge.reset();
  const start = performance.now();
  for (const payload of payloads) merge.mergeTilePayload(JSON.parse(payload));
  // Repeated viewport loads must overwrite by H3, not duplicate cells.
  for (const payload of payloads.slice(0, 8)) merge.mergeTilePayload(JSON.parse(payload));
  const elapsed = performance.now() - start;
  const entries = merge.entries();
  assert.deepEqual(new Set(entries.map(([cell]: [string, unknown]) => cell)), expectedCells);
  assert.equal(merge.dirty(), true);
  for (const [cell, feature] of entries) assert.equal(feature.properties.h3_index, cell);
  if (trial >= 3) times.push(elapsed);
}
times.sort((a, b) => a - b);
console.log(`METRIC client_parse_merge_ms=${times[2].toFixed(3)}`);
