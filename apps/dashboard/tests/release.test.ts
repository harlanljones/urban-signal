import { afterEach, beforeEach, expect, test } from "bun:test";
import worker, { clearSnapshotCaches } from "../src/index";
import {
  MissingLogicalKey,
  ReleaseUnavailable,
  clearReleaseCache,
  readReleaseJson,
  sha256Hex,
  withRelease,
  type ReleaseContext,
  type ReleaseEnv,
} from "../src/release";

beforeEach(() => {
  clearSnapshotCaches();
  clearReleaseCache();
});

afterEach(() => {
  clearSnapshotCaches();
  clearReleaseCache();
});

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map((item) => canonical(item)).join(",")}]`;
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).sort(([left], [right]) =>
      left < right ? -1 : left > right ? 1 : 0,
    );
    return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${canonical(item)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function objectEntry(value: unknown): Promise<{ raw: string; sha256: string }> {
  const raw = canonical(value);
  return { raw, sha256: await sha256Hex(raw) };
}

function memoryEnv(values: Record<string, string>, gets?: string[]): ReleaseEnv {
  return {
    SNAPSHOT: {
      async get(key: string) {
        gets?.push(key);
        return key in values ? values[key] : null;
      },
    },
  };
}

async function addressedRelease(id: string, objects: Record<string, unknown>, previous: string | null) {
  const stored: Record<string, string> = {};
  const keys: ReleaseContext["keys"] = {};
  for (const [logical, value] of Object.entries(objects)) {
    const entry = await objectEntry(value);
    stored[`objects/${entry.sha256}`] = entry.raw;
    keys[logical] = { sha256: entry.sha256, bytes: entry.raw.length };
  }
  const manifest = {
    schema_version: 1,
    snapshot_id: id,
    model_id: "synthetic-bundle",
    feature_schema_version: "features-v1",
    as_of: "2026-10-10",
    source_revisions: {},
    parent: previous,
    keys,
  };
  stored[`releases/${id}`] = canonical(manifest);
  return { stored, release: { snapshotId: id, previousId: previous, keys } satisfies ReleaseContext };
}

const CURRENT = "a".repeat(64);
const PREVIOUS = "b".repeat(64);

test("an unpinned multi-key read stays on one release and retries the previous release", async () => {
  const current = await addressedRelease(
    CURRENT,
    { "grid/nyc": { marker: "new" }, "grid/la": { marker: "missing" } },
    PREVIOUS,
  );
  delete current.stored[`objects/${current.release.keys["grid/la"].sha256}`];
  const previous = await addressedRelease(
    PREVIOUS,
    { "grid/nyc": { marker: "old" }, "grid/la": { marker: "old-la" } },
    null,
  );
  const env = memoryEnv({
    ...current.stored,
    ...previous.stored,
    "snapshot/current": canonical({ schema_version: 1, current: CURRENT, previous: PREVIOUS }),
    "grid/nyc": canonical({ marker: "legacy" }),
  });
  const seen: string[] = [];
  const outcome = await withRelease(env, undefined, async (release) => {
    if (!release) throw new Error("expected a release");
    seen.push(release.snapshotId);
    const nyc = await readReleaseJson(env, release, "grid/nyc");
    const la = await readReleaseJson(env, release, "grid/la");
    return { nyc, la };
  });
  expect(outcome.snapshotId).toBe(PREVIOUS);
  expect(outcome.value).toEqual({ nyc: { marker: "old" }, la: { marker: "old-la" } });
  expect(seen[0]).toBe(CURRENT);
  expect(seen.at(-1)).toBe(PREVIOUS);
});

test("a pinned missing object is 503 and does not leak the previous release", async () => {
  const current = await addressedRelease(CURRENT, { "grid/nyc": { marker: "new" } }, PREVIOUS);
  delete current.stored[`objects/${current.release.keys["grid/nyc"].sha256}`];
  const previous = await addressedRelease(PREVIOUS, { "grid/nyc": { marker: "old" } }, null);
  const env = memoryEnv({
    ...current.stored,
    ...previous.stored,
    "snapshot/current": canonical({ schema_version: 1, current: CURRENT, previous: PREVIOUS }),
  });
  await expect(
    withRelease(env, CURRENT, async (release) => {
      if (!release) throw new Error("expected a pinned release");
      return readReleaseJson(env, release, "grid/nyc");
    }),
  ).rejects.toBeInstanceOf(ReleaseUnavailable);
});

test("a deleted logical key does not fall back to an older release", async () => {
  const current = await addressedRelease(CURRENT, { "grid/nyc": { marker: "new" } }, PREVIOUS);
  const previous = await addressedRelease(PREVIOUS, { "grid/nyc": { marker: "old" }, "grid/la": { marker: "old" } }, null);
  const env = memoryEnv({
    ...current.stored,
    ...previous.stored,
    "snapshot/current": canonical({ schema_version: 1, current: CURRENT, previous: PREVIOUS }),
  });
  await expect(
    withRelease(env, undefined, async (release) => {
      if (!release) throw new Error("expected a release");
      return readReleaseJson(env, release, "grid/la");
    }),
  ).rejects.toBeInstanceOf(MissingLogicalKey);
});

test("a malformed pointer fails closed and a missing pointer preserves legacy reads", async () => {
  await expect(
    withRelease(memoryEnv({ "snapshot/current": "not-json" }), undefined, async () => "ok"),
  ).rejects.toBeInstanceOf(ReleaseUnavailable);
  const legacy = await withRelease(memoryEnv({ "grid/nyc": canonical({ marker: "legacy" }) }), undefined, async (release) => {
    expect(release).toBeNull();
    return "legacy";
  });
  expect(legacy).toEqual({ value: "legacy", snapshotId: null });
});

test("object cache keys are the physical hash", async () => {
  const current = await addressedRelease(CURRENT, { "grid/nyc": { marker: "new" } }, null);
  const gets: string[] = [];
  const env = memoryEnv(
    { ...current.stored, "snapshot/current": canonical({ schema_version: 1, current: CURRENT, previous: null }) },
    gets,
  );
  await withRelease(env, undefined, async (release) => {
    if (!release) throw new Error("expected a release");
    await readReleaseJson(env, release, "grid/nyc");
    await readReleaseJson(env, release, "grid/nyc");
    return null;
  });
  const objectGets = gets.filter((key) => key.startsWith("objects/"));
  expect(objectGets).toEqual([`objects/${current.release.keys["grid/nyc"].sha256}`]);
});

test("the worker serves one content-addressed release and accepts the snapshot alias", async () => {
  const product = {
    generated_at: "2026-10-10T00:00:00Z",
    app_version: "2.0.0",
    cities: ["nyc"],
    resolution: 9,
    k_ring: 1,
    catalyst_threshold: 85,
    snapshot_id: CURRENT,
    coverage: { schema_version: 1, national: { status: "unavailable" }, metro: { mode: "sparse_registry" } },
  };
  const grid = { type: "FeatureCollection", city_id: "nyc", features: [{ properties: { marker: "addressed" } }] };
  const current = await addressedRelease(CURRENT, { manifest: product, "grid/nyc": grid }, null);
  const env = {
    SNAPSHOT: {
      async get(key: string) {
        const values = {
          ...current.stored,
          "snapshot/current": canonical({ schema_version: 1, current: CURRENT, previous: null }),
          "grid/nyc": canonical({ features: [{ properties: { marker: "legacy" } }] }),
        };
        return key in values ? values[key] : null;
      },
    },
    ASSETS: { fetch: async () => new Response("ok") },
  };
  const response = await worker.fetch(
    new Request(`https://urban-signal.test/api/v1/grid?city_id=nyc&snapshot=${CURRENT}`),
    env as never,
  );
  expect(response.status).toBe(200);
  expect(response.headers.get("x-snapshot-id")).toBe(CURRENT);
  const body = (await response.json()) as { features: { properties: { marker: string } }[] };
  expect(body.features[0].properties.marker).toBe("addressed");
});

test("a content-addressed manifest does not stick for the next legacy request", async () => {
  const product = {
    generated_at: "2026-10-10T00:00:00Z",
    app_version: "2.0.0",
    cities: ["nyc"],
    resolution: 9,
    k_ring: 1,
    catalyst_threshold: 85,
    snapshot_id: CURRENT,
  };
  const current = await addressedRelease(CURRENT, { manifest: product }, null);
  const addressedEnv = {
    SNAPSHOT: {
      async get(key: string) {
        const values = {
          ...current.stored,
          "snapshot/current": canonical({ schema_version: 1, current: CURRENT, previous: null }),
        };
        return key in values ? values[key] : null;
      },
    },
    ASSETS: { fetch: async () => new Response("ok") },
  };
  const first = await worker.fetch(new Request("https://urban-signal.test/api/v1/manifest"), addressedEnv as never);
  expect(first.status).toBe(200);
  expect(((await first.json()) as { generated_at: string }).generated_at).toBe("2026-10-10T00:00:00Z");

  const legacyEnv = {
    SNAPSHOT: {
      async get(key: string) {
        if (key === "manifest") {
          return JSON.stringify({
            generated_at: "2026-08-24T00:00:00Z",
            app_version: "2.0.0",
            cities: ["nyc"],
            resolution: 9,
            k_ring: 1,
            catalyst_threshold: 85,
          });
        }
        return null;
      },
    },
    ASSETS: { fetch: async () => new Response("ok") },
  };
  const second = await worker.fetch(new Request("https://urban-signal.test/api/v1/manifest"), legacyEnv as never);
  expect(second.status).toBe(200);
  expect(((await second.json()) as { generated_at: string }).generated_at).toBe("2026-08-24T00:00:00Z");
});
