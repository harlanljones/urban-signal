// Fixed offline client workload. Real shipped queue/parse/merge/LOD/source submission;
// HTTP and MapLibre/GPU are boundaries, not measured network or browser rendering.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { createContext, runInContext } from "node:vm";
import { createHash } from "node:crypto";

type Feature = { properties: { h3_index: string; [key: string]: unknown }; [key: string]: unknown };
type Collection = { features: Feature[]; [key: string]: unknown };
type Manifest = {
  cities: string[];
  tile_indexes: Record<string, Record<string, { cities: string[] }>>;
  metro_index: { city_id: string; center: { lat: number; lng: number } }[];
};
const record = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value);
const strings = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every(item => typeof item === "string");
function collection(value: unknown): value is Collection {
  return record(value) && Array.isArray(value.features) && value.features.every(feature =>
    record(feature) && record(feature.properties) && typeof feature.properties.h3_index === "string");
}
function manifestSchema(value: unknown): value is Manifest {
  return record(value) && strings(value.cities) && record(value.tile_indexes) &&
    Object.values(value.tile_indexes).every(index => record(index) &&
      Object.values(index).every(tile => record(tile) && strings(tile.cities))) &&
    Array.isArray(value.metro_index) && value.metro_index.every(metro =>
      record(metro) && typeof metro.city_id === "string" && record(metro.center) &&
      typeof metro.center.lat === "number" && Number.isFinite(metro.center.lat) &&
      typeof metro.center.lng === "number" && Number.isFinite(metro.center.lng));
}
function centersSchema(value: unknown): value is Record<string, [number, number]> {
  return record(value) && Object.values(value).every(point =>
    Array.isArray(point) && point.length === 2 && point.every(coordinate =>
      typeof coordinate === "number" && Number.isFinite(coordinate)));
}
const parseCollection = (text: string): Collection => {
  const value: unknown = JSON.parse(text);
  assert.ok(collection(value), "Invalid pinned tile GeoJSON");
  // Measured prediction latency is telemetry, not tile content. Freeze it so
  // each invocation parses identical response bytes, regardless of build speed.
  for (const feature of value.features) {
    if (Object.hasOwn(feature.properties, "inference_latency_ms")) feature.properties.inference_latency_ms = 0;
  }
  return value;
};

const root = process.argv[2];
assert.ok(root, "Snapshot directory is required");
const html = readFileSync("apps/dashboard/public/index.html", "utf8");
const slice = (start: string, end: string) => {
  const first = html.indexOf(start);
  const last = html.indexOf(end, first);
  assert.ok(first >= 0 && last > first, `Missing shipped loader boundary: ${start}`);
  return html.slice(first, last);
};
const source = slice("    const fetchedTiles", "    // National overlay cache") +
  slice("    function updateViewportTiles()", "    function setupGridLayers()");
const manifestValue: unknown = JSON.parse(readFileSync(join(root, "manifest.json"), "utf8"));
assert.ok(manifestSchema(manifestValue), "Invalid pinned manifest");
const manifest = manifestValue;
const centersValue: unknown = JSON.parse(readFileSync(join(root, "benchmark-parent-centers.json"), "utf8"));
assert.ok(centersSchema(centersValue), "Invalid pinned H3 centers");
const centers = centersValue;
const pinned: unknown = JSON.parse(readFileSync("scripts/autoresearch_coverage.json", "utf8"));
assert.ok(record(pinned) && Object.values(pinned).every(strings), "Invalid coverage fixture");
const cities = Object.keys(pinned).sort();
assert.deepEqual([...manifest.cities].sort(), cities);
const documents = new Map<string, Collection>();
const responseCache = new Map<string, string>();
const inventories = new Map<string, { parents: string[]; signature: string }>();
const signature = (features: Feature[]) => createHash("sha256").update(JSON.stringify(
  [...features].sort((a, b) => a.properties.h3_index.localeCompare(b.properties.h3_index)),
)).digest("hex");
for (const res of [7, 8, 9]) {
  const index = manifest.tile_indexes[String(res)];
  assert.ok(index && Object.keys(index).length, `Missing LOD ${res}`);
  for (const parent of Object.keys(index).sort()) {
    documents.set(`${res}/${parent}`, parseCollection(readFileSync(join(root, "gridtiles_res", String(res), `${parent}.json`), "utf8")));
  }
  for (const city of cities) {
    const parents = Object.keys(index).filter(parent => index[parent].cities.includes(city)).sort();
    assert.ok(parents.length, `Missing ${city} LOD ${res}`);
    const cells = new Map<string, Feature>();
    for (const parent of parents) for (const feature of documents.get(`${res}/${parent}`)!.features) {
      cells.set(feature.properties.h3_index, feature);
    }
    inventories.set(`${city}/${res}`, { parents, signature: signature([...cells.values()]) });
  }
}
const workloadHash = createHash("sha256");
for (const [key, doc] of [...documents.entries()].sort(([a], [b]) => a.localeCompare(b))) {
  workloadHash.update(key + "\0" + signature(doc.features));
}
const workloadIdentity = workloadHash.digest("hex");
assert.equal(workloadIdentity, "d8052e4a05b73106987293093087d2666a02bb04e54ab2b7fe4855c8b9be7fc9",
  "Pinned tile workload changed; an explicit rebaseline is required");

function makeClient(city: string) {
  let zoom = 8;
  let requestedParents: string[] = [];
  let latest: unknown = null;
  let requests = 0;
  let bytes = 0;
  let submissions = 0;
  const metro = manifest.metro_index.find(metro => metro.city_id === city);
  assert.ok(metro, `Missing camera for ${city}`);
  const camera = metro.center;
  const element = { hidden: true, textContent: "" };
  const context = createContext({
    console, REDUCED_MOTION: true, selectedGeoAnchor: null, selectedH3Index: null,
    SNAPSHOT_ID: "offline-pinned", snapshotManifest: manifest, gridGeoJSON: null,
    coverageState: { national: "loading", metro: "loading" },
    coverageSchemaSupported: () => true, updateCoverageLegend() {},
    coverageLegendText: () => "No published cells in this view",
    appendSnapshotId: (url: string, id: string) => `${url}&snapshot_id=${id}`,
    parentsCoveringBounds: () => requestedParents,
    document: { getElementById: () => element },
    h3: { cellToLatLng: (parent: string) => {
      assert.ok(centers[parent], `Missing real H3 centroid ${parent}`);
      return centers[parent];
    } },
    map: {
      getZoom: () => zoom, getBounds: () => ({}), getCenter: () => camera,
      getLayer: () => null, triggerRepaint() {},
      getSource: () => ({ setData: (data: unknown) => {
        latest = data;
        submissions++;
      } }),
    },
    setHexLayersVisible() {},
    setTimeout: () => { throw new Error("Unexpected retry or timer in successful fixed workload"); },
    clearTimeout() {}, cancelAnimationFrame() {},
    fetch: async (url: string) => {
      const query = new URL(url, "https://offline.invalid").searchParams;
      assert.equal(query.get("snapshot_id"), "offline-pinned");
      const res = query.get("res");
      const parents = query.get("parents")!.split(",");
      const key = `${res}/${parents.join(",")}`;
      let encoded = responseCache.get(key);
      if (!encoded) {
        const features = parents.flatMap(parent => {
          const doc = documents.get(`${res}/${parent}`);
          assert.ok(doc, `Request outside pinned snapshot: ${res}/${parent}`);
          return doc.features;
        });
        encoded = JSON.stringify({ type: "FeatureCollection", res: Number(res), features, missing: [], count: features.length, requested: parents.length });
        responseCache.set(key, encoded);
      }
      requests++;
      bytes += Buffer.byteLength(encoded);
      return { ok: true, json: async () => JSON.parse(encoded!) };
    },
  });
  runInContext(source + `
    globalThis.loader = {
      updateViewportTiles,
      idle() { return tileFetchesActive === 0 && pendingTileParents.length === 0 && tilesInFlight.size === 0; },
      status() { return { res: renderedLodRes, ready: coverageState.metro === 'ready', retries: tileRetryCounts.size }; }
    };`, context);
  // This interface is the in-process object constructed by the VM code above.
  const loader = context.loader as {
    updateViewportTiles(): void;
    idle(): boolean;
    status(): { res: number; ready: boolean; retries: number };
  };
  return {
    async load(res: number) {
      const inventory = inventories.get(`${city}/${res}`)!;
      requestedParents = inventory.parents;
      zoom = res === 7 ? 8 : res === 8 ? 10 : 12;
      const before = { requests, bytes, submissions };
      const start = performance.now();
      loader.updateViewportTiles();
      for (let turns = 0; !loader.idle(); turns++) {
        assert.ok(turns < 10000, "Loader did not settle");
        await Promise.resolve();
      }
      const elapsed = performance.now() - start;
      assert.ok(collection(latest) && loader.status().ready && loader.status().res === res && loader.status().retries === 0);
      assert.equal(signature(latest.features), inventory.signature, `${city} LOD ${res} lost or changed cell data`);
      return { elapsed, requests: requests - before.requests, bytes: bytes - before.bytes, submissions: submissions - before.submissions };
    },
  };
}

const samples: number[] = [];
let totals = { requests: 0, bytes: 0, submissions: 0 };
// First traversal warms JIT and serialized boundary responses; five fresh-cache
// traversals are measured. Context construction and semantic checks are excluded.
for (let trial = 0; trial < 6; trial++) {
  const clients = cities.map(city => makeClient(city));
  let elapsed = 0;
  const counts = { requests: 0, bytes: 0, submissions: 0 };
  for (const client of clients) for (const res of [7, 8, 9, 9, 7]) {
    const result = await client.load(res);
    elapsed += result.elapsed;
    counts.requests += result.requests;
    counts.bytes += result.bytes;
    counts.submissions += result.submissions;
  }
  if (trial > 0) {
    samples.push(elapsed);
    if (trial > 1) assert.deepEqual(counts, totals, "Workload changed between trials");
    totals = counts;
  }
}
samples.sort((a, b) => a - b);
console.log(`METRIC tile_load_cpu_ms=${samples[2].toFixed(3)}`);
console.log(`METRIC tile_requests=${totals.requests}`);
console.log(`METRIC tile_response_bytes=${totals.bytes}`);
console.log(`METRIC tile_source_submissions=${totals.submissions}`);
console.log(`METRIC tile_view_steps=${cities.length * 5}`);
console.log(`ASI tile_workload_sha256=${workloadIdentity}`);
