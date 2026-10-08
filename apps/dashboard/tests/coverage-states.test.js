// Hex-coverage Stage A/B Tasks 4-5: client coverage states + truthful legends.
//
// The dashboard is a single Python-served HTML document, so the client logic
// cannot be imported. Like national-overlay.test.js, these tests slice the
// relevant functions out of serving/dashboard.py by string and run them in a
// node:vm context. Keep the extracted functions free of DOM/map/manifest
// globals (the gating harness below supplies those as stubs).
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
  // Keep the `async` keyword when the function is async, otherwise the
  // extracted body loses its await scope.
  if (source.slice(start - 6, start) === 'async ') start -= 6;
  let depth = 0;
  let i = source.indexOf('{', start);
  const bodyStart = i;
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

function pureContext(names) {
  const context = createContext({});
  runInContext(names.map((name) => sliceFunction(SOURCE, name)).join('\n'), context);
  return context;
}

function call(context, expression) {
  return runInContext(expression, context);
}

test('nationalCoverageStatus gates on the manifest coverage block', () => {
  const ctx = pureContext(['nationalCoverageStatus']);
  assert.equal(call(ctx, 'nationalCoverageStatus(null)'), 'unavailable');
  assert.equal(call(ctx, 'nationalCoverageStatus({})'), 'unavailable');
  assert.equal(
    call(ctx, "nationalCoverageStatus({coverage:{national:{status:'available'}}})"),
    'available',
  );
  assert.equal(
    call(ctx, "nationalCoverageStatus({coverage:{national:{status:'stale'}}})"),
    'stale',
  );
  assert.equal(
    call(ctx, "nationalCoverageStatus({coverage:{national:{status:'nope'}}})"),
    'unavailable',
  );
});

test('coverageSchemaSupported rejects a newer schema and passes legacy', () => {
  const ctx = pureContext(['coverageSchemaSupported']);
  assert.equal(call(ctx, 'coverageSchemaSupported({})'), true);
  assert.equal(call(ctx, 'coverageSchemaSupported({coverage:{schema_version:1}})'), true);
  assert.equal(call(ctx, 'coverageSchemaSupported({coverage:{schema_version:2}})'), false);
});

test('appendSnapshotId appends with the right separator and omits when unset', () => {
  const ctx = pureContext(['appendSnapshotId']);
  assert.equal(
    call(ctx, "appendSnapshotId('/api/v1/national/4?parents=a,b', 'r-1')"),
    '/api/v1/national/4?parents=a,b&snapshot_id=r-1',
  );
  assert.equal(
    call(ctx, "appendSnapshotId('/api/v1/manifest', 'r-1')"),
    '/api/v1/manifest?snapshot_id=r-1',
  );
  assert.equal(call(ctx, "appendSnapshotId('/api/v1/manifest', null)"), '/api/v1/manifest');
});

test('nationalCacheKey includes the snapshot id', () => {
  const ctx = pureContext(['nationalCacheKey']);
  assert.equal(call(ctx, "nationalCacheKey('r-1', 5, 'p')"), 'r-1|5|p');
  assert.equal(call(ctx, "nationalCacheKey(null, 5, 'p')"), 'current|5|p');
});

test('backoffDelay uses the retry ladder and honors retry-after', () => {
  const ctx = pureContext(['backoffDelay']);
  assert.equal(call(ctx, 'backoffDelay(0)'), 500);
  assert.equal(call(ctx, 'backoffDelay(1)'), 1500);
  assert.equal(call(ctx, 'backoffDelay(2)'), 4000);
  // Retry-After (seconds) wins when it is longer than the ladder delay.
  assert.equal(call(ctx, 'backoffDelay(0, 3)'), 3000);
  assert.equal(call(ctx, 'backoffDelay(2, 1)'), 4000);
});

// ---- Gating harness: run the real updateNationalOverlay against stubs -------

function overlayContext(manifest) {
  const calls = { fetch: 0 };
  const context = createContext({
    snapshotManifest: manifest,
    SNAPSHOT_ID: null,
    coverageState: { national: 'loading', metro: 'loading' },
    nationalActive: { 4: [], 5: [], 6: [] },
    nationalActiveRes: null,
    nationalCache: { 4: new Map(), 5: new Map(), 6: new Map() },
    nationalFetched: { 4: new Set(), 5: new Set(), 6: new Set() },
    nationalInFlight: new Map(),
    nationalLoadGeneration: 0,
    nationalFailureGeneration: -1,
    currentMetric: 'lims_score',
    CONTEXT_METRICS: {},
    tileFeatures: new Map(),
    ZOOM_FLOOR: 6,
    fetch: () => {
      calls.fetch += 1;
      return Promise.resolve({ ok: false, status: 500, headers: { get: () => null } });
    },
    document: { getElementById: () => null },
    map: {
      getZoom: () => 4.0,
      getBounds: () => ({
        getWest: () => -100,
        getEast: () => -90,
        getSouth: () => 30,
        getNorth: () => 40,
      }),
      getSource: () => ({ setData: () => {} }),
      triggerRepaint: () => {},
    },
    h3: { latLngToCell: () => 'parent', cellToParent: () => 'parent' },
    // Referenced by the extracted function; not exercised on the gated paths.
    updateNationalLayerVisibilities: () => {},
    clearNationalOverlay: () => {},
    applyNationalData: () => {},
    updateCoverageLegend: () => {},
    nationalResForZoom: () => 4,
    res3ParentsCoveringBounds: () => [],
    nationalCacheKey: () => 'key',
    loadNationalBatch: () => Promise.resolve(),
  });
  const code = [
    sliceFunction(SOURCE, 'nationalCoverageStatus'),
    sliceFunction(SOURCE, 'coverageSchemaSupported'),
    sliceFunction(SOURCE, 'updateNationalOverlay'),
  ].join('\n');
  runInContext(code, context);
  return { context, calls };
}

test('absent coverage block reports unavailable and issues zero national fetches', async () => {
  const { context, calls } = overlayContext({ generated_at: '2026-10-07T00:00:00Z' });
  await runInContext('updateNationalOverlay()', context);
  assert.equal(context.coverageState.national, 'unavailable');
  assert.equal(calls.fetch, 0);
});

test('declared-unavailable national status issues zero national fetches', async () => {
  const { context, calls } = overlayContext({ coverage: { schema_version: 1, national: { status: 'unavailable' } } });
  await runInContext('updateNationalOverlay()', context);
  assert.equal(context.coverageState.national, 'unavailable');
  assert.equal(calls.fetch, 0);
});

test('an unsupported schema_version fails the read without fetching', async () => {
  const { context, calls } = overlayContext({
    coverage: { schema_version: 2, national: { status: 'available' } },
  });
  await runInContext('updateNationalOverlay()', context);
  assert.equal(context.coverageState.national, 'failed');
  assert.equal(calls.fetch, 0);
});
