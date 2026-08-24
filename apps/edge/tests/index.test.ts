import { expect, test } from "bun:test";
import worker from "../src/index";

const CITY_IDS = [
  "nyc",
  "chicago",
  "san_francisco",
  "seattle",
  "los_angeles",
  "new_orleans",
  "norfolk",
  "detroit",
  "austin",
  "cincinnati",
  "boston",
  "baltimore",
  "montgomery",
  "baton_rouge",
  "denver",
  "philadelphia",
  "washington_dc",
] as const;

function testEnv() {
  return {
    SNAPSHOT: {
      async get(key: string) {
        if (key === "manifest") {
          return JSON.stringify({
            generated_at: "2026-08-24T00:00:00Z",
            app_version: "2.0.0",
            cities: CITY_IDS,
            resolution: 9,
            k_ring: 1,
            catalyst_threshold: 85,
          });
        }
        if (key.startsWith("submarkets/")) {
          const city = key.slice("submarkets/".length);
          return JSON.stringify({ city_id: city, count: 1, submarkets: {} });
        }
        return null;
      },
    },
    ASSETS: { fetch: async () => new Response("not found", { status: 404 }) },
  };
}

test("accepts every city emitted by the snapshot builder", async () => {
  for (const city of CITY_IDS) {
    const response = await worker.fetch(
      new Request(`https://urban-signal.test/api/v1/submarkets?city_id=${city}`),
      testEnv() as never,
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({ city_id: city });
  }
});

test("accepts the common Boston alias without changing the city", async () => {
  const response = await worker.fetch(
    new Request("https://urban-signal.test/api/v1/submarkets?city_id=boston"),
    testEnv() as never,
  );

  expect(response.status).toBe(200);
  expect(await response.json()).toMatchObject({ city_id: "boston" });
});
