// Display-resolution clamp (ADR-0010 §3.2, HX-B8). The dashboard is a single
// Python-served HTML document, so these functions are sliced out of
// serving/dashboard.py and run in a node:vm context with the globals they read.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createContext, runInContext } from 'node:vm';

const SOURCE = readFileSync(
  new URL('../../api/src/serving/dashboard.py', import.meta.url),
  'utf8',
);

function sliceFunction(source, name) {
  const marker = `function ${name}(`;
  let start = source.indexOf(marker);
  assert.ok(start >= 0, `${name} is present in dashboard.py`);
  if (source.slice(start - 6, start) === 'async ') start -= 6;
  let depth = 0;
  const bodyStart = source.indexOf('{', start);
  let i = bodyStart;
  for (; i < source.length; i += 1) {
    const ch = source[i];
    if (ch === '{') depth += 1;
    else if (ch === '}') {
      depth -= 1;
      if (depth === 0) {
        i += 1;
        break;
      }
    }
  }
  assert.ok(depth === 0 && i > bodyStart, `balanced body for ${name}`);
  return source.slice(start, i);
}

/** Bounds stub shaped like a MapLibre LngLatBounds. */
function box(west, south, east, north) {
  return { getWest: () => west, getSouth: () => south, getEast: () => east, getNorth: () => north };
}

const NYC = { city_id: 'nyc', max_detail_res: 9, bbox: { min_lng: -74.3, max_lng: -73.7, min_lat: 40.4, max_lat: 41.0 } };
const LEGACY = { city_id: 'nyc', bbox: NYC.bbox }; // no max_detail_res: pre-HX-B8 manifest
const COARSE = { city_id: 'abilene', max_detail_res: 7, bbox: { min_lng: -100.0, max_lng: -99.0, min_lat: 32.0, max_lat: 33.0 } };

const BOX_NYC = box(-74.3, 40.4, -73.7, 41.0);
const BOX_COARSE = box(-100, 32, -99, 33);
const BOX_EMPTY = box(-95, 35, -94, 36);

/** Context carrying the sliced functions plus the bounds stubs they are given. */
function harness(manifest, activeLodRes = 7) {
  const context = createContext({
    snapshotManifest: manifest,
    activeLodRes,
    DEFAULT_DETAIL_CEILING: 9,
    BOX_NYC,
    BOX_COARSE,
    BOX_EMPTY,
    BOX_STUB: {},
  });
  runInContext(
    [sliceFunction(SOURCE, 'viewDetailCeiling'), sliceFunction(SOURCE, 'displayResForZoom')].join('\n'),
    context,
  );
  return (expr) => runInContext(expr, context);
}

test('the ladder is unchanged for a full-detail viewport', () => {
  const run = harness({ metro_index: [NYC] });
  assert.equal(run('displayResForZoom(8, viewDetailCeiling(BOX_NYC))'), 7);
  assert.equal(run('displayResForZoom(10, viewDetailCeiling(BOX_NYC))'), 8);
  assert.equal(run('displayResForZoom(12, viewDetailCeiling(BOX_NYC))'), 9);
  assert.equal(run('displayResForZoom(4, viewDetailCeiling(BOX_NYC))'), 7);
});

test('a coarse region caps the request instead of asking for hexes it never publishes', () => {
  const run = harness({ metro_index: [COARSE] });
  assert.equal(run('displayResForZoom(8, viewDetailCeiling(BOX_COARSE))'), 7, 'already at the ceiling');
  assert.equal(run('displayResForZoom(10, viewDetailCeiling(BOX_COARSE))'), 7);
  assert.equal(run('displayResForZoom(12, viewDetailCeiling(BOX_COARSE))'), 7, 'the res-9 request clamps to 7');
});

test('the ceiling is the max over metros intersecting the viewport, not the whole registry', () => {
  const run = harness({ metro_index: [NYC, COARSE] });
  assert.equal(run('viewDetailCeiling(BOX_NYC)'), 9, 'nyc viewport keeps res 9');
  assert.equal(run('viewDetailCeiling(BOX_COARSE)'), 7, 'abilene viewport caps at res 7');
  assert.equal(run('viewDetailCeiling(BOX_EMPTY)'), 9, 'no metro in view falls back to the default');
});

test('a manifest without max_detail_res, or unusable bounds, stays unclamped', () => {
  const run = harness({ metro_index: [LEGACY] });
  assert.equal(run('displayResForZoom(12, viewDetailCeiling(BOX_NYC))'), 9);
  assert.equal(run('viewDetailCeiling(BOX_STUB)'), 9, 'the offline loader passes an empty bounds object');
  assert.equal(run('viewDetailCeiling(null)'), 9);
  assert.equal(run('displayResForZoom(12, undefined)'), 9);
  assert.equal(run('viewDetailCeiling(BOX_NYC)'), 9, 'a metro with no ceiling recorded does not clamp');
});

test('hysteresis still holds at the boundary and respects the cap', () => {
  const wide = harness({ metro_index: [NYC] }, 9);
  assert.equal(wide('displayResForZoom(11.0, viewDetailCeiling(BOX_NYC))'), 9, 'stays at 9 once active');
  const capped = harness({ metro_index: [COARSE] }, 9);
  assert.equal(capped('displayResForZoom(11.0, viewDetailCeiling(BOX_COARSE))'), 7, 'the hysteresis result is capped too');
});
