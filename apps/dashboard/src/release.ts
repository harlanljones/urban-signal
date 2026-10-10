/**
 * Content-addressed snapshot releases.
 *
 * A release manifest at `releases/<snapshot_id>` maps logical keys to
 * `objects/<sha256>`. Stage-B twins (`releases/<id>/<logical>`) stay in use
 * when that manifest is absent. One request reads one release; an unpinned
 * miss retries the whole query against the previous release once.
 */

import { AsyncLocalStorage } from "node:async_hooks";

export interface ObjectPointer {
  sha256: string;
  bytes: number;
}

export interface ReleaseManifest {
  schema_version: number;
  snapshot_id: string;
  model_id: string;
  feature_schema_version: string;
  as_of: string;
  source_revisions: Record<string, unknown>;
  parent: string | null;
  keys: Record<string, ObjectPointer>;
}

export interface ReleaseContext {
  snapshotId: string;
  previousId: string | null;
  keys: Record<string, ObjectPointer>;
}

export interface SnapshotKv {
  get(key: string): Promise<string | null>;
}

export interface ReleaseEnv {
  SNAPSHOT: SnapshotKv;
}

export class ReleaseUnavailable extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ReleaseUnavailable";
  }
}

export class MissingLogicalKey extends Error {
  constructor(readonly logicalKey: string) {
    super(`logical key '${logicalKey}' is not in this release`);
    this.name = "MissingLogicalKey";
  }
}

const releaseStore = new AsyncLocalStorage<ReleaseContext | null>();
const objectCache = new Map<string, { raw: string; value: unknown }>();

export function currentRelease(): ReleaseContext | null | undefined {
  return releaseStore.getStore();
}

export function clearReleaseCache(): void {
  objectCache.clear();
}

export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function isObjectPointer(value: unknown): value is ObjectPointer {
  if (!value || typeof value !== "object") return false;
  const pointer = value as Partial<ObjectPointer>;
  return typeof pointer.sha256 === "string" && pointer.sha256.length === 64 && typeof pointer.bytes === "number";
}

export function isReleaseManifest(value: unknown): value is ReleaseManifest {
  if (!value || typeof value !== "object") return false;
  const manifest = value as Partial<ReleaseManifest>;
  if (manifest.schema_version !== 1 || typeof manifest.snapshot_id !== "string") return false;
  if (!manifest.keys || typeof manifest.keys !== "object") return false;
  return Object.values(manifest.keys).every((entry) => isObjectPointer(entry));
}

interface Pointer {
  current: string;
  previous: string | null;
}

async function readPointer(env: ReleaseEnv): Promise<Pointer | null> {
  const raw = await env.SNAPSHOT.get("snapshot/current");
  if (raw === null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new ReleaseUnavailable("snapshot/current is malformed");
  }
  if (!parsed || typeof parsed !== "object" || typeof (parsed as Pointer).current !== "string") {
    throw new ReleaseUnavailable("snapshot/current is malformed");
  }
  const current = (parsed as Pointer).current;
  if (!current) throw new ReleaseUnavailable("snapshot/current is malformed");
  const previous = (parsed as { previous?: unknown }).previous;
  return { current, previous: typeof previous === "string" && previous ? previous : null };
}

export async function loadRelease(env: ReleaseEnv, snapshotId: string): Promise<ReleaseContext | null> {
  const raw = await env.SNAPSHOT.get(`releases/${snapshotId}`);
  if (raw === null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new ReleaseUnavailable(`release ${snapshotId} is malformed`);
  }
  if (!isReleaseManifest(parsed) || parsed.snapshot_id !== snapshotId) return null;
  const pointer = await readPointer(env);
  return {
    snapshotId,
    previousId: pointer && pointer.current === snapshotId ? pointer.previous : null,
    keys: parsed.keys,
  };
}

export async function resolveRelease(env: ReleaseEnv, requestedId?: string): Promise<ReleaseContext | null> {
  const pointer = await readPointer(env);
  if (!pointer && !requestedId) return null;
  const snapshotId = requestedId ?? pointer?.current;
  if (!snapshotId) return null;
  const release = await loadRelease(env, snapshotId);
  if (release) return release;
  if (requestedId) return null;
  const stageB = await env.SNAPSHOT.get(`releases/${snapshotId}/manifest`);
  if (stageB !== null) return null;
  throw new ReleaseUnavailable(`snapshot ${snapshotId} is not readable`);
}

export async function readReleaseEntry(
  env: ReleaseEnv,
  release: ReleaseContext,
  key: string,
): Promise<{ value: unknown; raw: string }> {
  const pointer = release.keys[key];
  if (!pointer) throw new MissingLogicalKey(key);
  const cached = objectCache.get(pointer.sha256);
  if (cached) return cached;
  const raw = await env.SNAPSHOT.get(`objects/${pointer.sha256}`);
  if (raw === null) throw new ReleaseUnavailable(`object ${pointer.sha256} is missing`);
  const digest = await sha256Hex(raw);
  if (digest !== pointer.sha256) {
    throw new ReleaseUnavailable(`object ${pointer.sha256} failed its checksum`);
  }
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new ReleaseUnavailable(`object ${pointer.sha256} is not JSON`);
  }
  const entry = { raw, value };
  objectCache.set(pointer.sha256, entry);
  return entry;
}

export async function readReleaseJson(env: ReleaseEnv, release: ReleaseContext, key: string): Promise<unknown> {
  return (await readReleaseEntry(env, release, key)).value;
}

export async function withRelease<T>(
  env: ReleaseEnv,
  requestedId: string | undefined,
  query: (release: ReleaseContext | null) => Promise<T>,
): Promise<{ value: T; snapshotId: string | null }> {
  const pointer = await readPointer(env);
  const snapshotId = requestedId ?? pointer?.current;
  if (!snapshotId) {
    const value = await releaseStore.run(null, () => query(null));
    return { value, snapshotId: null };
  }
  const release = await loadRelease(env, snapshotId);
  if (!release) {
    if (requestedId) {
      const value = await releaseStore.run(null, () => query(null));
      return { value, snapshotId: requestedId };
    }
    const stageB = pointer ? await env.SNAPSHOT.get(`releases/${pointer.current}/manifest`) : null;
    if (stageB !== null || !pointer) {
      const value = await releaseStore.run(null, () => query(null));
      return { value, snapshotId: null };
    }
    throw new ReleaseUnavailable(`snapshot ${snapshotId} is not readable`);
  }
  try {
    const value = await releaseStore.run(release, () => query(release));
    return { value, snapshotId: release.snapshotId };
  } catch (error) {
    const previousId = pointer?.previous;
    if (error instanceof ReleaseUnavailable && !requestedId && previousId && previousId !== release.snapshotId) {
      const previous = await loadRelease(env, previousId);
      if (!previous) throw error;
      const value = await releaseStore.run(previous, () => query(previous));
      return { value, snapshotId: previous.snapshotId };
    }
    throw error;
  }
}
