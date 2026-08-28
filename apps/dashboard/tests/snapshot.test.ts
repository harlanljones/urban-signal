import { expect, test } from "bun:test";
import worker from "../src/index";
import { testEnv } from "./index.test";
import {
  queryCatalysts,
  querySubmarkets,
  lookupPrediction,
  listCities,
} from "../src/snapshot";

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
