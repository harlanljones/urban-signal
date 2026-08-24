/**
 * Urban Signal edge worker.
 *
 * Serves the MapLibre dashboard as a static asset and answers /api/v1/* routes
 * from precomputed snapshot data pushed to Workers KV by GitHub Actions batch
 * runs (src/export/snapshot_builder.py). Response schemas mirror the FastAPI
 * serving API (src/serving/router.py) so the dashboard works unchanged.
 */

interface Env {
  SNAPSHOT: KVNamespace;
  ASSETS: Fetcher;
}

const SERVICE_NAME = "urban-signal-product";
const APP_VERSION = "2.0.0";
const CACHE_CONTROL = "public, max-age=300";
const MANIFEST_TTL_MS = 60_000;

const CITY_ALIASES: Record<string, string> = {
  nyc: "nyc",
  chicago: "chicago",
  san_francisco: "san_francisco",
  sf: "san_francisco",
  seattle: "seattle",
  sea: "seattle",
  king_county: "seattle",
  los_angeles: "los_angeles",
  la: "los_angeles",
  new_orleans: "new_orleans",
  norfolk: "norfolk",
  detroit: "detroit",
  austin: "austin",
  cincinnati: "cincinnati",
  boston: "boston",
  baltimore: "baltimore",
  montgomery: "montgomery",
  baton_rouge: "baton_rouge",
  denver: "denver",
  philadelphia: "philadelphia",
  philly: "philadelphia",
  washington_dc: "washington_dc",
  dc: "washington_dc",
};

let manifestCache: { value: Manifest | null; expires: number } = {
  value: null,
  expires: 0,
};

interface Manifest {
  generated_at: string;
  app_version: string;
  cities: string[];
  resolution: number;
  k_ring: number;
  catalyst_threshold: number;
}

interface CatalystEntry {
  h3_index: string;
  lims_score: number;
  [key: string]: unknown;
}

interface CatalystPayload {
  city_id: string;
  count: number;
  threshold: number;
  borough: string | null;
  catalysts: CatalystEntry[];
}

function jsonError(status: number, detail: string): Response {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function normalizeCity(raw: string | null): string | null {
  if (!raw) return "nyc";
  return CITY_ALIASES[raw.trim().toLowerCase()] ?? null;
}

async function sha1Hex(input: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function etagMatches(request: Request, etag: string): boolean {
  const header = request.headers.get("if-none-match");
  if (!header) return false;
  return header.split(",").some((candidate) => candidate.trim() === etag);
}

async function kvJson(env: Env, key: string): Promise<{ value: unknown; etag: string } | null> {
  const raw = await env.SNAPSHOT.get(key);
  if (raw === null) return null;
  return { value: JSON.parse(raw), etag: `"${(await sha1Hex(raw)).slice(0, 32)}"` };
}

function withHeaders(body: string, status: number, extra: HeadersInit): Response {
  return new Response(body, {
    status,
    headers: { "content-type": "application/json", ...Object.fromEntries(Object.entries(extra)) },
  });
}

async function getManifest(env: Env): Promise<Manifest | null> {
  const now = Date.now();
  if (manifestCache.value && now < manifestCache.expires) return manifestCache.value;
  const raw = await env.SNAPSHOT.get("manifest");
  if (raw === null) return null;
  const value = JSON.parse(raw) as Manifest;
  manifestCache = { value, expires: now + MANIFEST_TTL_MS };
  return value;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health" || url.pathname === "/live" || url.pathname === "/ready") {
      const manifest = await getManifest(env);
      return withHeaders(
        JSON.stringify({
          status: "healthy",
          service: SERVICE_NAME,
          version: APP_VERSION,
          environment: "production",
          snapshot_created: manifest?.generated_at ?? null,
        }),
        200,
        { "cache-control": "no-store", "x-snapshot-created": manifest?.generated_at ?? "" }
      );
    }

    if (!url.pathname.startsWith("/api/")) {
      return env.ASSETS.fetch(request);
    }

    const manifest = await getManifest(env);
    const supportedCities = (manifest?.cities ?? []).join(", ");
    const baseHeaders: Record<string, string> = {
      "cache-control": CACHE_CONTROL,
      "x-snapshot-created": manifest?.generated_at ?? "",
    };

    try {
      // GET /api/v1/cities
      if (url.pathname === "/api/v1/cities") {
        const cities = manifest?.cities ?? [];
        return withHeaders(
          JSON.stringify({ count: cities.length, cities: cities.map((id) => ({ city_id: id })) }),
          200,
          baseHeaders
        );
      }

      // GET /api/v1/submarkets?city_id=
      if (url.pathname === "/api/v1/submarkets") {
        const city = normalizeCity(url.searchParams.get("city_id"));
        if (!city) {
          return jsonError(
            400,
            `Unsupported city_id '${url.searchParams.get("city_id")}'. Supported cities: ${supportedCities}.`
          );
        }
        const entry = await kvJson(env, `submarkets/${city}`);
        if (!entry) return jsonError(404, `No snapshot for city '${city}'.`);
        if (etagMatches(request, entry.etag)) return new Response(null, { status: 304 });

        const payload = entry.value as Record<string, unknown>;
        const boroughFilter = url.searchParams.get("borough");
        if (boroughFilter) {
          const norm = boroughFilter.trim().toUpperCase().replace(/[\s-]/g, "_");
          const submarkets = Object.fromEntries(
            Object.entries(
              (payload.submarkets as Record<string, Record<string, unknown>>) ?? {}
            ).filter(([, meta]) => String(meta.borough).toUpperCase() === norm)
          );
          Object.assign(payload, {
            borough: norm,
            count: Object.keys(submarkets).length,
            submarkets,
          });
        }
        return withHeaders(JSON.stringify(payload), 200, {
          ...baseHeaders,
          etag: entry.etag,
        });
      }

      // GET /api/v1/grid?city_id=
      if (url.pathname === "/api/v1/grid") {
        const city = normalizeCity(url.searchParams.get("city_id"));
        if (!city) {
          return jsonError(
            400,
            `Unsupported city_id '${url.searchParams.get("city_id")}'. Supported cities: ${supportedCities}.`
          );
        }
        const entry = await kvJson(env, `grid/${city}`);
        if (!entry) return jsonError(404, `No grid snapshot for city '${city}'.`);
        if (etagMatches(request, entry.etag)) return new Response(null, { status: 304 });
        return withHeaders(JSON.stringify(entry.value), 200, {
          ...baseHeaders,
          etag: entry.etag,
        });
      }

      // GET /api/v1/catalysts?city_id=&min_lims=&limit=&borough=&resolution=
      if (url.pathname === "/api/v1/catalysts") {
        const city = normalizeCity(url.searchParams.get("city_id"));
        if (!city) {
          return jsonError(
            400,
            `Unsupported city_id '${url.searchParams.get("city_id")}'. Supported cities: ${supportedCities}.`
          );
        }
        const minLimsRaw = url.searchParams.get("min_lims");
        const minLims =
          minLimsRaw !== null && minLimsRaw !== ""
            ? Number(minLimsRaw)
            : (manifest?.catalyst_threshold ?? 85.0);
        if (!Number.isFinite(minLims) || minLims < 0 || minLims > 100) {
          return jsonError(422, "min_lims must be within [0.0, 100.0].");
        }
        const limitRaw = Number(url.searchParams.get("limit") ?? "50");
        const limit = Math.min(Math.max(Number.isFinite(limitRaw) ? limitRaw : 50, 1), 500);

        const entry = await kvJson(env, `catalysts/${city}`);
        if (!entry) return jsonError(404, `No catalyst snapshot for city '${city}'.`);
        if (etagMatches(request, entry.etag)) return new Response(null, { status: 304 });

        const stored = entry.value as CatalystPayload;
        let catalysts = stored.catalysts;
        if (minLims > (stored.threshold ?? 85.0)) {
          catalysts = catalysts.filter((c) => Number(c.lims_score) >= minLims);
        }
        const boroughFilter = url.searchParams.get("borough");
        if (boroughFilter) {
          const norm = boroughFilter.trim().toUpperCase().replace(/[\s-]/g, "_");
          catalysts = catalysts.filter(
            (c) => String(c.borough).toUpperCase() === norm
          );
        }
        catalysts = catalysts.slice(0, limit);

        const payload: CatalystPayload = {
          city_id: stored.city_id,
          count: catalysts.length,
          threshold: minLims,
          borough: boroughFilter ? boroughFilter.trim().toUpperCase().replace(/[\s-]/g, "_") : null,
          catalysts,
        };
        return withHeaders(JSON.stringify(payload), 200, {
          ...baseHeaders,
          etag: entry.etag,
        });
      }

      // POST /api/v1/predict — point lookup of precomputed cell predictions
      if (url.pathname === "/api/v1/predict") {
        if (request.method !== "POST") {
          return jsonError(405, "Method Not Allowed");
        }
        let body: Record<string, unknown>;
        try {
          body = (await request.json()) as Record<string, unknown>;
        } catch {
          return jsonError(400, "Invalid JSON body.");
        }

        const h3Index =
          typeof body.h3_index === "string" && body.h3_index.trim()
            ? body.h3_index.trim()
            : null;
        if (!h3Index) {
          return jsonError(
            400,
            "Edge snapshot requires 'h3_index'. Provide the H3 cell for ('latitude', 'longitude') via the client-side h3 resolver."
          );
        }

        const entry = await kvJson(env, "cells/index");
        if (!entry) return jsonError(404, "No prediction snapshot available.");

        const cells = entry.value as Record<string, Record<string, unknown>>;
        const pred = cells[h3Index];
        if (!pred) {
          return jsonError(404, `No precomputed prediction for cell '${h3Index}'.`);
        }
        if (body.include_shap === false) {
          const { shap_attributions: _omit, ...rest } = pred;
          return withHeaders(JSON.stringify(rest), 200, baseHeaders);
        }
        return withHeaders(JSON.stringify(pred), 200, baseHeaders);
      }

      return jsonError(404, "Not Found");
    } catch (err) {
      return jsonError(
        500,
        `Edge error: ${err instanceof Error ? err.message : "unknown failure"}`
      );
    }
  },
};
