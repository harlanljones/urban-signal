import { expect, test, beforeEach } from "bun:test";
import worker, { clearSnapshotCaches, readSnapshotValue } from "../src/index";
import { testEnv } from "./index.test";
import {
  queryCatalysts,
  querySubmarkets,
  lookupPrediction,
  listCities,
  fetchNationalIndex,
  fetchNationalRows,
  fetchGridTiles,
  fetchSnapshotPointer,
} from "../src/snapshot";

beforeEach(() => clearSnapshotCaches());

const ORIGIN = "https://urban-signal.test";
const env = () => testEnv() as never;

async function httpJson(path: string, init?: RequestInit): Promise<{ status: number; body: any }> {
  const response = await worker.fetch(new Request(`${ORIGIN}${path}`, init), env());
  const body = response.status === 204 ? null : await response.json().catch(() => null);
  return { status: response.status, body };
}

// ---------------------------------------------------------------------------
// listCities — faithful to GET /api/v1/cities
// ---------------------------------------------------------------------------

test("listCities matches the HTTP /api/v1/cities catalog", async () => {
  const cities = await listCities(testEnv() as any);
  const { body } = await httpJson("/api/v1/cities");
  expect(cities).toEqual(body.cities.map((c: { city_id: string }) => c.city_id));
});

// ---------------------------------------------------------------------------
// queryCatalysts — faithful to GET /api/v1/catalysts
// ---------------------------------------------------------------------------

test("queryCatalysts returns the same values as the HTTP adapter", async () => {
  const { body } = await httpJson("/api/v1/catalysts?city_id=nyc");
  const result = (await queryCatalysts(testEnv() as any, { city: "nyc" })) as any;
  expect(result.city_id).toBe(body.city_id);
  expect(result.threshold).toBe(body.threshold);
  expect(result.borough).toBe(body.borough);
  expect(result.catalysts).toEqual(body.catalysts);
});

test("queryCatalysts honors an explicit limit, matching HTTP", async () => {
  const { body } = await httpJson("/api/v1/catalysts?city_id=big&limit=10");
  const result = (await queryCatalysts(testEnv() as any, { city: "big", limit: 10 })) as any;
  expect(result.catalysts.length).toBe(10);
  expect(result.catalysts.length).toBe(body.catalysts.length);
});

test("queryCatalysts default limit (50) matches HTTP", async () => {
  const { body } = await httpJson("/api/v1/catalysts?city_id=big");
  const result = (await queryCatalysts(testEnv() as any, { city: "big" })) as any;
  expect(result.catalysts.length).toBe(50);
  expect(result.catalysts.length).toBe(body.catalysts.length);
});

test("queryCatalysts clamps limit at the 500 max, matching HTTP", async () => {
  const { body } = await httpJson("/api/v1/catalysts?city_id=big&limit=600");
  const result = (await queryCatalysts(testEnv() as any, { city: "big", limit: 600 })) as any;
  expect(result.catalysts.length).toBe(500);
  expect(result.catalysts.length).toBe(body.catalysts.length);
});

test("queryCatalysts default min_lims comes from the manifest threshold (85)", async () => {
  const result = (await queryCatalysts(testEnv() as any, { city: "dual" })) as any;
  expect(result.threshold).toBe(85);
});

test("queryCatalysts rejects out-of-range min_lims with an error value (no throw)", async () => {
  const low = await queryCatalysts(testEnv() as any, { city: "nyc", minLims: -5 });
  const high = await queryCatalysts(testEnv() as any, { city: "nyc", minLims: 150 });
  expect("error" in low).toBe(true);
  expect("error" in high).toBe(true);
});

test("queryCatalysts rejects an unsupported city with an error value (no throw)", async () => {
  const result = await queryCatalysts(testEnv() as any, { city: "atlantis" });
  expect("error" in result).toBe(true);
});

test("queryCatalysts borough filter + normalization matches HTTP", async () => {
  for (const borough of ["Manhattan", "manhattan", "washington heights", "washington-heights"]) {
    const { body } = await httpJson(`/api/v1/catalysts?city_id=nyc&borough=${encodeURIComponent(borough)}`);
    const result = (await queryCatalysts(testEnv() as any, { city: "nyc", borough })) as any;
    expect(result.borough).toBe(body.borough);
    expect(result.catalysts).toEqual(body.catalysts);
  }
});

test("query borough filters normalize stored and requested display labels consistently", async () => {
  const label = "Central / Downtown";
  const boroughEnv = {
    SNAPSHOT: {
      async get(key: string) {
        if (key === "manifest") {
          return JSON.stringify({ cities: ["chicago"], catalyst_threshold: 85 });
        }
        if (key === "catalysts/chicago") {
          return JSON.stringify({
            city_id: "chicago",
            threshold: 85,
            catalysts: [{ h3_index: "892830bbfffffff", lims_score: 90, borough: label }],
          });
        }
        if (key === "submarkets/chicago") {
          return JSON.stringify({
            city_id: "chicago",
            submarkets: { CORE: { borough: label } },
          });
        }
        return null;
      },
    },
  } as any;

  const catalysts = await queryCatalysts(boroughEnv, { city: "chicago", borough: "central / downtown" });
  const submarkets = await querySubmarkets(boroughEnv, { city: "chicago", borough: "central / downtown" });

  expect("error" in catalysts).toBe(false);
  expect("error" in submarkets).toBe(false);
  if ("error" in catalysts || "error" in submarkets) return;
  expect(catalysts.catalysts).toHaveLength(1);
  expect(Object.keys(submarkets.submarkets)).toEqual(["CORE"]);
});

// ---------------------------------------------------------------------------
// querySubmarkets — faithful to GET /api/v1/submarkets
// ---------------------------------------------------------------------------

test("querySubmarkets returns the same city_id/submarkets as the HTTP adapter", async () => {
  const { body } = await httpJson("/api/v1/submarkets?city_id=nyc");
  const result = (await querySubmarkets(testEnv() as any, { city: "nyc" })) as any;
  expect(result.city_id).toBe(body.city_id);
  expect(result.submarkets).toEqual(body.submarkets);
});

test("querySubmarkets borough filter matches the HTTP adapter", async () => {
  const { body } = await httpJson("/api/v1/submarkets?city_id=nyc&borough=Manhattan");
  const result = (await querySubmarkets(testEnv() as any, { city: "nyc", borough: "Manhattan" })) as any;
  expect(result.submarkets).toEqual(body.submarkets);
});

test("querySubmarkets rejects an unsupported city with an error value (no throw)", async () => {
  const result = await querySubmarkets(testEnv() as any, { city: "atlantis" });
  expect("error" in result).toBe(true);
});

// ---------------------------------------------------------------------------
// lookupPrediction — faithful to POST /api/v1/predict
// ---------------------------------------------------------------------------

test("lookupPrediction keeps shap_attributions when includeShap is omitted", async () => {
  const { body } = await httpJson("/api/v1/predict", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ h3_index: "892a10708b7ffff" }),
  });
  const result = (await lookupPrediction(testEnv() as any, { h3Index: "892a10708b7ffff" })) as any;
  expect(result).toEqual(body);
});

test("lookupPrediction strips shap_attributions when includeShap is explicitly false", async () => {
  const { body } = await httpJson("/api/v1/predict", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ h3_index: "892a10708b7ffff", include_shap: false }),
  });
  const result = (await lookupPrediction(testEnv() as any, { h3Index: "892a10708b7ffff", includeShap: false })) as any;
  expect(result).toEqual(body);
  expect(result.shap_attributions).toBeUndefined();
});

test("lookupPrediction trims h3_index like the HTTP adapter", async () => {
  const { body, status } = await httpJson("/api/v1/predict", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ h3_index: "  892a10708b7ffff  " }),
  });
  expect(status).toBe(200);
  const result = (await lookupPrediction(testEnv() as any, { h3Index: "  892a10708b7ffff  " })) as any;
  expect(result).toEqual(body);
});

test("lookupPrediction errors on a missing cell without throwing", async () => {
  const result = await lookupPrediction(testEnv() as any, { h3Index: "deadbeef" });
  expect("error" in result).toBe(true);
});

// ---------------------------------------------------------------------------
// lookupPrediction — US-385 per-cell shard precedence + legacy fallback
// ---------------------------------------------------------------------------

test("lookupPrediction prefers the per-cell shard when present", async () => {
  const result = (await lookupPrediction(testEnv() as any, {
    h3Index: "892830bbfffffff",
  })) as any;
  expect(result.lims_score).toBe(91.0);
  expect(result.source).toBe("per-cell-shard");
});

test("lookupPrediction falls back to the legacy cells/index value when no shard exists", async () => {
  const result = (await lookupPrediction(testEnv() as any, {
    h3Index: "892a10708b7ffff",
  })) as any;
  expect(result.lims_score).toBe(97.5);
  expect(result.shap_attributions).toEqual([{ f: "x", v: 0.4 }]);
});

test("lookupPrediction strips shap from the legacy fallback when includeShap is false", async () => {
  const result = (await lookupPrediction(testEnv() as any, {
    h3Index: "892a10708b7ffff",
    includeShap: false,
  })) as any;
  expect(result.shap_attributions).toBeUndefined();
});

// ---------------------------------------------------------------------------
// fetchNationalIndex / fetchNationalRows — US-383 transport-free helpers
// ---------------------------------------------------------------------------

test("fetchNationalIndex returns the published index document", async () => {
  const result = (await fetchNationalIndex(testEnv() as any)) as any;
  expect(result.resolutions["6"].count).toBe(2);
  expect(result.resolutions["6"].parents).toContain("8326b9fffffffff");
});

test("fetchNationalIndex errors when no national snapshot is published", async () => {
  const emptyEnv = { SNAPSHOT: { get: async () => null } };
  const result = await fetchNationalIndex(emptyEnv as any);
  expect("error" in result).toBe(true);
});

test("fetchNationalRows merges chunk rows and reports missing parents", async () => {
  const result = (await fetchNationalRows(testEnv() as any, {
    res: 6,
    parents: ["832830fffffffff", "8326b9fffffffff", "8329999ffffffff"],
  })) as any;
  expect(result.res).toBe(6);
  expect(result.count).toBe(2);
  expect(result.cols).toEqual(["h3", "jobs", "workers", "jobs_pct", "workers_pct"]);
  expect(result.missing).toEqual(["8329999ffffffff"]);
  expect(result.rows).toEqual([
    ["892a10708b7ffff", 1200, 900, 71.5, 66.25],
    ["8926b9fffffffff", 40, null, 12.5, null],
  ]);
});

test("fetchNationalRows rejects resolutions outside the national pyramid", async () => {
  const result = await fetchNationalRows(testEnv() as any, {
    res: 9,
    parents: ["832830fffffffff"],
  });
  expect("error" in result).toBe(true);
});

// ---------------------------------------------------------------------------
// fetchGridTiles — US-412 res-aware metro LOD grid tiles
// ---------------------------------------------------------------------------

test("fetchGridTiles returns merged features for res-7", async () => {
  const result = (await fetchGridTiles(testEnv() as any, {
    res: 7,
    parents: ["842830fffffffff"],
  })) as any;
  expect(result.res).toBe(7);
  expect(result.count).toBe(1);
  expect(result.features[0].properties.h3_index).toBe("8728308ffffffffff");
  expect(result.features[0].properties.source).toBe("lod_aggregate");
  expect(result.missing).toEqual([]);
});

test("fetchGridTiles reports missing parents", async () => {
  const result = (await fetchGridTiles(testEnv() as any, {
    res: 7,
    parents: ["842830fffffffff", "8429999ffffffff"],
  })) as any;
  expect(result.count).toBe(1);
  expect(result.missing).toEqual(["8429999ffffffff"]);
});

test("fetchGridTiles errors on an invalid res value", async () => {
  const result = await fetchGridTiles(testEnv() as any, { res: 3, parents: ["842830fffffffff"] });
  expect("error" in result).toBe(true);
  const result2 = await fetchGridTiles(testEnv() as any, { res: 6, parents: ["842830fffffffff"] });
  expect("error" in result2).toBe(true);
});

// ---------------------------------------------------------------------------
// Hex-coverage Stage B: pointer resolution + release-qualified reads
// ---------------------------------------------------------------------------

const LEGACY_MANIFEST = { cities: ["nyc"], catalyst_threshold: 85 };

/** KV env backed by an explicit key -> JSON value map. */
function kvEnv(values: Record<string, unknown>) {
  return {
    SNAPSHOT: {
      async get(key: string) {
        return key in values ? JSON.stringify(values[key]) : null;
      },
    },
  } as any;
}

test("fetchSnapshotPointer returns null when no pointer is published", async () => {
  expect(await fetchSnapshotPointer(testEnv() as any)).toBeNull();
});

test("fetchSnapshotPointer returns the promoted release when present", async () => {
  const env = kvEnv({
    "snapshot/current": { current: "r-x", previous: "r-y", promoted_at: "2026-10-07T00:00:00Z" },
  });
  expect(await fetchSnapshotPointer(env)).toEqual({
    current: "r-x",
    previous: "r-y",
    promoted_at: "2026-10-07T00:00:00Z",
  });
});

test("fetchSnapshotPointer treats a malformed pointer as absent", async () => {
  expect(await fetchSnapshotPointer(kvEnv({ "snapshot/current": { previous: null } }))).toBeNull();
});

test("readSnapshotValue reads the release-qualified key for a snapshot id", async () => {
  const env = kvEnv({
    manifest: LEGACY_MANIFEST,
    "grid/nyc": { marker: "legacy" },
    "releases/r-1/grid/nyc": { marker: "release" },
  });
  const result = await readSnapshotValue(env, "grid/nyc", "r-1");
  expect(result.ok).toBe(true);
  if (result.ok) expect((result.entry!.value as { marker: string }).marker).toBe("release");
});

test("readSnapshotValue returns a 503 failure for a missing release key (no fallback)", async () => {
  const env = kvEnv({ manifest: LEGACY_MANIFEST, "grid/nyc": { marker: "legacy" } });
  const result = await readSnapshotValue(env, "grid/nyc", "r-missing");
  expect(result.ok).toBe(false);
  if (!result.ok) {
    expect(result.status).toBe(503);
    expect(result.detail).toBe("Snapshot generation 'r-missing' is not available.");
    expect(result.headers?.["retry-after"]).toBe("5");
  }
});

test("readSnapshotValue fails closed on an unsupported coverage schema version", async () => {
  const env = kvEnv({ manifest: { ...LEGACY_MANIFEST, coverage: { schema_version: 2 } }, "grid/nyc": {} });
  const result = await readSnapshotValue(env, "grid/nyc", null);
  expect(result.ok).toBe(false);
  if (!result.ok) {
    expect(result.status).toBe(500);
    expect(result.detail).toBe("Unsupported snapshot schema version 2.");
  }
});

test("lookupPrediction reads the release-qualified cell shard for a snapshot id", async () => {
  const env = kvEnv({
    manifest: LEGACY_MANIFEST,
    "cells/892a10708b7ffff": { h3_index: "892a10708b7ffff", lims_score: 97.5, source: "legacy" },
    "releases/r-1/cells/892a10708b7ffff": { h3_index: "892a10708b7ffff", lims_score: 42, source: "release" },
  });
  const result = (await lookupPrediction(env, {
    h3Index: "892a10708b7ffff",
    snapshotId: "r-1",
  })) as any;
  expect(result.source).toBe("release");
});

test("lookupPrediction surfaces the 503 when a release shard is missing", async () => {
  const env = kvEnv({
    manifest: LEGACY_MANIFEST,
    "cells/892a10708b7ffff": { h3_index: "892a10708b7ffff", lims_score: 97.5 },
  });
  const result = await lookupPrediction(env, { h3Index: "892a10708b7ffff", snapshotId: "r-missing" });
  expect("error" in result).toBe(true);
  expect((result as any).status).toBe(503);
  expect((result as any).headers?.["retry-after"]).toBe("5");
});

test("queryCatalysts reads the release-qualified payload for a snapshot id", async () => {
  const env = kvEnv({
    manifest: LEGACY_MANIFEST,
    "catalysts/nyc": { city_id: "nyc", threshold: 85, catalysts: [{ h3_index: "a", lims_score: 90 }] },
    "releases/r-1/catalysts/nyc": {
      city_id: "nyc",
      threshold: 85,
      catalysts: [{ h3_index: "b", lims_score: 80 }],
    },
  });
  const result = (await queryCatalysts(env, { city: "nyc", snapshotId: "r-1" })) as any;
  expect(result.catalysts[0].h3_index).toBe("b");
});

test("fetchNationalIndex reads the release-qualified index for a snapshot id", async () => {
  const env = kvEnv({
    manifest: LEGACY_MANIFEST,
    "national/index": { generated_at: "legacy", resolutions: {} },
    "releases/r-1/national/index": {
      generated_at: "release",
      resolutions: { "6": { count: 1, byte_size: 1, sha256: "a", parents: ["p"], generated_at: "release" } },
    },
  });
  const result = (await fetchNationalIndex(env, { snapshotId: "r-1" })) as any;
  expect(result.generated_at).toBe("release");
});

test("fetchGridTiles reads the release-qualified tiles for a snapshot id", async () => {
  const env = kvEnv({
    manifest: LEGACY_MANIFEST,
    "gridtiles_res7/842830fffffffff": { features: [{ properties: { h3_index: "legacy" } }] },
    "releases/r-1/gridtiles_res7/842830fffffffff": {
      features: [{ properties: { h3_index: "release" } }],
    },
  });
  const result = (await fetchGridTiles(env, {
    res: 7,
    parents: ["842830fffffffff"],
    snapshotId: "r-1",
  })) as any;
  expect(result.features[0].properties.h3_index).toBe("release");
});
