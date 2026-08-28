/**
 * Transport-free snapshot query module.
 *
 * Pure extraction of the snapshot-reading logic that the HTTP and MCP adapters
 * in `index.ts` previously duplicated. This module has no knowledge of HTTP
 * envelopes, MCP JSON-RPC, ETags, or headers: it reads Workers KV snapshots via
 * the shared `kvJson`/`getManifest`/`normalizeCity` helpers and returns plain
 * data objects (or plain `{ error }` values on rejection — never throws, to
 * mirror adapter semantics).
 *
 * US-188: additive. Neither adapter imports this yet (wiring is US-189/US-190).
 * The policy encoded here is the HTTP-adapter reference: min_lims defaults to
 * the manifest catalyst_threshold (?? 85), bounded to [0, 100]; the limit clamp
 * is the HTTP default (50) / max (500); borough normalization trims, upper-cases,
 * and collapses spaces/hyphens to underscores. The MCP adapter historically
 * drifted on all three (stored-threshold default, 25/100 clamp, no trim) — see
 * the US-188 report; these functions are the consolidation target.
 */

import {
  type Env,
  type Manifest,
  type CatalystEntry,
  type CatalystPayload,
  kvJson,
  getManifest,
  normalizeCity,
  H3_PARENT_PATTERN,
} from "./index";

function normalizeBorough(raw: string): string {
  return raw.trim().toUpperCase().replace(/[\s-]/g, "_");
}

// ---------------------------------------------------------------------------
// Catalyst paging policy — EXPLICIT PRODUCT DECISION (US-190)
// ---------------------------------------------------------------------------
//
// PRODUCT DECISION (recorded US-190, analysis in US-188): both the HTTP and
// MCP adapters MUST agree on a single catalyst paging/limit policy. We adopt the
// HTTP / manifest reference as the canonical policy and retire the historical
// MCP drift:
//
//   * default limit ................ 50   (MCP had defaulted to 25)
//   * hard max limit ............... 500  (MCP had clamped at 100)
//   * default min_lims ............. manifest.catalyst_threshold ?? 85
//                                     (MCP had used the STORED snapshot
//                                      threshold instead of the manifest)
//   * borough normalization ........ trim + uppercase + collapse spaces/hyphens
//                                     (MCP previously omitted the trim)
//   * get_submarkets honors borough  (MCP previously ignored the param)
//
// These two constants are the single source of truth. They are imported by
// index.ts for schema metadata so the docs cannot silently disagree. Do NOT
// re-introduce a second, adapter-local limit constant.
export const CATALYST_DEFAULT_LIMIT = 50;
export const CATALYST_MAX_LIMIT = 500;

// ---------------------------------------------------------------------------
// Catalysts
// ---------------------------------------------------------------------------

export interface CatalystQueryResult {
  city_id: string;
  threshold: number;
  borough: string | null;
  catalysts: CatalystEntry[];
}

/** Success carries the four documented fields; rejections carry `{ error }`. */
export type CatalystQueryOutcome = CatalystQueryResult | { error: string };

export async function queryCatalysts(
  env: Env,
  opts: { city: string; minLims?: number; limit?: number; borough?: string }
): Promise<CatalystQueryOutcome> {
  const manifest = await getManifest(env);
  const city = normalizeCity(opts.city, manifest);
  if (!city) return { error: `Unsupported city_id '${opts.city}'.` };

  const entry = await kvJson(env, `catalysts/${city}`);
  if (!entry) return { error: `No catalyst snapshot for city '${city}'.` };

  const stored = entry.value as CatalystPayload;
  const minLims = opts.minLims ?? (manifest?.catalyst_threshold ?? 85);
  if (!Number.isFinite(minLims) || minLims < 0 || minLims > 100) {
    return { error: "min_lims must be within [0.0, 100.0]." };
  }

  const limit = Math.min(Math.max(opts.limit ?? CATALYST_DEFAULT_LIMIT, 1), CATALYST_MAX_LIMIT);

  let catalysts = stored.catalysts;
  if (minLims > (stored.threshold ?? 85)) {
    catalysts = catalysts.filter((c) => Number(c.lims_score) >= minLims);
  }

  let boroughNorm: string | null = null;
  const boroughRaw = opts.borough;
  if (boroughRaw) {
    boroughNorm = normalizeBorough(boroughRaw);
    catalysts = catalysts.filter(
      (c) => String(c.borough).toUpperCase() === boroughNorm
    );
  }

  catalysts = catalysts.slice(0, limit);

  return {
    city_id: stored.city_id,
    threshold: minLims,
    borough: boroughNorm,
    catalysts,
  };
}

// ---------------------------------------------------------------------------
// Submarkets
// ---------------------------------------------------------------------------

export interface SubmarketQueryResult {
  city_id: string;
  submarkets: Record<string, Record<string, unknown>>;
}

export type SubmarketQueryOutcome = SubmarketQueryResult | { error: string };

export async function querySubmarkets(
  env: Env,
  opts: { city: string; borough?: string }
): Promise<SubmarketQueryOutcome> {
  const manifest = await getManifest(env);
  const city = normalizeCity(opts.city, manifest);
  if (!city) return { error: `Unsupported city_id '${opts.city}'.` };

  const entry = await kvJson(env, `submarkets/${city}`);
  if (!entry) return { error: `No snapshot for city '${city}'.` };

  const payload = entry.value as {
    city_id: string;
    submarkets?: Record<string, Record<string, unknown>>;
  };

  let submarkets = payload.submarkets ?? {};
  const boroughRaw = opts.borough;
  if (boroughRaw) {
    const norm = normalizeBorough(boroughRaw);
    submarkets = Object.fromEntries(
      Object.entries(submarkets).filter(
        ([, meta]) => String(meta.borough).toUpperCase() === norm
      )
    );
  }

  return { city_id: payload.city_id ?? city, submarkets };
}

// ---------------------------------------------------------------------------
// Prediction lookup
// ---------------------------------------------------------------------------

/**
 * Returns the cell prediction, or `{ error }` when the cell/snapshot is missing
 * or h3_index is blank. Strips `shap_attributions` only when `includeShap` is
 * explicitly `false` (the same trigger the adapters use).
 *
 * Reads the per-cell shard `cells/{h3_index}` first (US-385: one KV lookup per
 * request instead of parsing the monolithic `cells/index` value) and falls back
 * to the legacy single key while the compat window is open.
 */
export type PredictionOutcome = Record<string, unknown> | { error: string };

export async function lookupPrediction(
  env: Env,
  opts: { h3Index: string; includeShap?: boolean }
): Promise<PredictionOutcome> {
  const h3Index = opts.h3Index?.trim().toLowerCase();
  if (!h3Index) return { error: "'h3_index' is required." };
  if (!H3_PARENT_PATTERN.test(h3Index)) {
    return { error: "Malformed 'h3_index': expected a 15-char hex H3 cell index." };
  }

  let pred: Record<string, unknown> | undefined;

  const shard = await kvJson(env, `cells/${h3Index}`);
  if (shard) pred = shard.value as Record<string, unknown>;

  if (!pred) {
    const entry = await kvJson(env, "cells/index");
    if (entry) {
      const cells = entry.value as Record<string, Record<string, unknown>>;
      pred = cells[h3Index];
    }
  }

  if (!pred) return { error: `No precomputed prediction for cell '${h3Index}'.` };

  if (opts.includeShap === false) {
    const { shap_attributions: _omit, ...rest } = pred;
    return rest;
  }
  return pred;
}

// ---------------------------------------------------------------------------
// National hex layer (US-383)
// ---------------------------------------------------------------------------

export const NATIONAL_RESOLUTIONS = [4, 5, 6] as const;
// CONUS spans ~40 res-3 parents; one call must be able to fetch a full
// resolution's display set, so the cap sits above the gridtiles viewport cap.
export const MAX_NATIONAL_PARENTS_PER_REQUEST = 64;

export interface NationalIndexDocument {
  generated_at: string;
  resolutions: Record<
    string,
    { count: number; byte_size: number; sha256: string; parents: string[]; generated_at: string }
  >;
}

export type NationalIndexOutcome = NationalIndexDocument | { error: string };

export async function fetchNationalIndex(env: Env): Promise<NationalIndexOutcome> {
  const entry = await kvJson(env, "national/index");
  if (!entry) return { error: "No national layer snapshot published." };
  return entry.value as NationalIndexDocument;
}

export interface NationalRowsResult {
  res: number;
  count: number;
  cols: string[];
  rows: unknown[][];
  missing: string[];
}

export type NationalRowsOutcome = NationalRowsResult | { error: string };

export async function fetchNationalRows(
  env: Env,
  opts: { res: number; parents: string[] }
): Promise<NationalRowsOutcome> {
  if (!(NATIONAL_RESOLUTIONS as readonly number[]).includes(opts.res)) {
    return { error: `'res' must be one of ${NATIONAL_RESOLUTIONS.join(", ")}.` };
  }
  const entries = await Promise.all(
    opts.parents.map((parent) => kvJson(env, `national/${opts.res}/${parent}`))
  );
  const rows: unknown[][] = [];
  const missing: string[] = [];
  let cols: string[] | null = null;
  for (let i = 0; i < opts.parents.length; i += 1) {
    const entry = entries[i];
    if (!entry) {
      missing.push(opts.parents[i]);
      continue;
    }
    const chunk = entry.value as { cols?: string[]; rows?: unknown[][] };
    if (!cols && chunk.cols) cols = chunk.cols;
    rows.push(...(chunk.rows ?? []));
  }
  return { res: opts.res, count: rows.length, cols: cols ?? [], rows, missing };
}

// ---------------------------------------------------------------------------
// City catalog
// ---------------------------------------------------------------------------

export async function listCities(env: Env): Promise<string[]> {
  const manifest = await getManifest(env);
  return manifest?.cities ?? [];
}
