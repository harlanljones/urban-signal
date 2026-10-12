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
  assert.equal(call(ctx, 'coverageSchemaSupported({coverage:{schema_version:2}})'), true);
  assert.equal(call(ctx, 'coverageSchemaSupported({coverage:{schema_version:3}})'), false);
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
test('regionGeneration resolves from manifest.regions or falls back to snapshot id', () => {
  const ctx = pureContext(['regionGeneration']);
  assert.equal(call(ctx, "regionGeneration(null, 'metro/nyc', 'snap-1')"), 'snap-1');
  assert.equal(call(ctx, "regionGeneration({}, 'metro/nyc', 'snap-1')"), 'snap-1');
  assert.equal(
    call(ctx, "regionGeneration({ regions: { 'metro/nyc': 'gen-nyc-42' } }, 'metro/nyc', 'snap-1')"),
    'gen-nyc-42',
  );
  assert.equal(
    call(ctx, "regionGeneration({ regions: { 'metro/sf': 'gen-sf-1' } }, 'metro/nyc', 'snap-1')"),
    'snap-1',
  );
});

test('changedRegionIds compares previous and next manifest region generations', () => {
  const ctx = pureContext(['changedRegionIds']);
  assert.equal(call(ctx, 'changedRegionIds(null, null)'), null);
  assert.equal(call(ctx, 'changedRegionIds({}, {})'), null);
  assert.deepEqual(
    Array.from(call(ctx, "changedRegionIds({ regions: { 'metro/nyc': 'g1' } }, { regions: { 'metro/nyc': 'g1' } })")),
    [],
  );
  assert.deepEqual(
    Array.from(call(ctx, "changedRegionIds({ regions: { 'metro/nyc': 'g1', 'metro/sf': 'g1' } }, { regions: { 'metro/nyc': 'g1', 'metro/sf': 'g2' } })")),
    ['metro/sf'],
  );
  assert.deepEqual(
    Array.from(call(ctx, "changedRegionIds({ regions: { 'metro/nyc': 'g1' } }, { regions: { 'metro/nyc': 'g1', 'metro/sf': 'g1' } })")),
    ['metro/sf'],
  );
});

test('shouldEvictFeature matches features by region_id or city_id', () => {
  const ctx = pureContext(['shouldEvictFeature']);
  assert.equal(
    call(ctx, "shouldEvictFeature({ properties: { city_id: 'nyc' } }, new Set(['metro/nyc']))"),
    true,
  );
  assert.equal(
    call(ctx, "shouldEvictFeature({ properties: { city_id: 'sf' } }, new Set(['metro/nyc']))"),
    false,
  );
  assert.equal(
    call(ctx, "shouldEvictFeature({ properties: { region_id: 'anchor/12345' } }, new Set(['anchor/12345']))"),
    true,
  );
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
    NATIONAL_UNDERLAY_MAX_ZOOM: 8.9,
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
    coverage: { schema_version: 3, national: { status: 'available' } },
  });
  await runInContext('updateNationalOverlay()', context);
  assert.equal(context.coverageState.national, 'failed');
  assert.equal(calls.fetch, 0);
});

// ---- Cell provenance (ADR-0010 honesty labels) ----

function provenance(props) {
  const context = createContext({});
  runInContext(sliceFunction(SOURCE, 'coverageProvenance'), context);
  context.props = props;
  return runInContext('coverageProvenance(props)', context);
}

test('measured cells say they are the submarket\u2019s own cell', () => {
  assert.match(provenance({ coverage_label: 'measured', submarket: 'SoHo' }), /^Measured/);
});

test('interpolated cells name their source submarket and distance', () => {
  const text = provenance({ coverage_label: 'interpolated', submarket: 'SoHo', coverage_distance_km: 0.84 });
  assert.equal(text, 'Interpolated from SoHo, 0.8 km away');
});

test('an interpolated cell with no usable distance still states its provenance, never a fake number', () => {
  assert.equal(provenance({ coverage_label: 'interpolated', submarket: 'SoHo' }), 'Interpolated from SoHo');
  assert.equal(provenance({ coverage_label: 'interpolated', coverage_distance_km: 'n/a' }), 'Interpolated');
});

test('legacy coverage_source strings and LOD aggregates still resolve for one release', () => {
  assert.match(provenance({ coverage_source: 'center' }), /^Measured/);
  assert.match(provenance({ coverage_source: 'bounded', coverage_distance_km: 1 }), /^Interpolated/);
  assert.equal(provenance({ source: 'lod_aggregate' }), 'Aggregate of finer cells');
});

test('the explicit label wins over a contradicting legacy source', () => {
  assert.match(provenance({ coverage_label: 'interpolated', coverage_source: 'center' }), /^Interpolated/);
});

test('cells with no provenance information render no provenance line', () => {
  assert.equal(provenance({}), '');
  assert.equal(provenance(null), '');
});

test('coverageLegendText shows rank epoch age when older than the snapshot (DG-10)', () => {
  const context = createContext({
    snapshotManifest: {
      generated_at: '2026-10-12T19:05:00Z',
      rank_epoch_at: '2026-10-05T00:00:00Z',
      coverage: { schema_version: 2 },
    },
    coverageSchemaSupported: () => true,
    CONTEXT_METRICS: {},
    currentMetric: 'lims_score',
    nationalCoverageStatus: () => 'available',
    coverageState: { national: 'ready', metro: 'ready' },
    tileFeatures: new Map([['c1', {}]]),
  });
  runInContext(sliceFunction(SOURCE, 'coverageLegendText'), context);
  const text = runInContext('coverageLegendText()', context);
  assert.match(text, /ranks 2026-10-05/);
});

test('a manifest with one changed region generation keeps other regions cached features', () => {
  const context = createContext({
    snapshotManifest: {
      snapshot_id: 'snap-2',
      regions: { 'metro/nyc': 'g1', 'metro/sf': 'g2' },
      tile_indexes: { '9': { 'p-nyc': { cities: ['nyc'] }, 'p-sf': { cities: ['sf'] } } },
    },
    nationalLoadGeneration: 0,
    tileLoadGeneration: 0,
    nationalCache: { 4: new Map(), 5: new Map(), 6: new Map() },
    nationalFetched: { 4: new Set(), 5: new Set(), 6: new Set() },
    tileFeatures: new Map([
      ['cell-nyc', { properties: { h3_index: 'cell-nyc', city_id: 'nyc' } }],
      ['cell-sf', { properties: { h3_index: 'cell-sf', city_id: 'sf' } }],
    ]),
    lodTileCache: new Map([
      [9, {
        features: [
          { properties: { h3_index: 'cell-nyc', city_id: 'nyc' } },
          { properties: { h3_index: 'cell-sf', city_id: 'sf' } },
        ],
        fetched: new Set(['p-nyc', 'p-sf']),
      }],
    ]),
    fetchedTiles: new Set(['p-nyc', 'p-sf']),
    tileParentCenters: new Map(),
    lodSwapPending: false,
    tileRetryTimers: new Map(),
    tileRetryCounts: new Map(),
    exhaustedTileRetries: new Set(),
    pendingTileParents: [],
    coverageState: { metro: 'ready' },
    activeLodRes: 9,
    gridDirty: false,
    map: null,
    invalidateNationalCaches: () => {},
    updateCoverageLegend: () => {},
  });
  const code = [
    sliceFunction(SOURCE, 'changedRegionIds'),
    sliceFunction(SOURCE, 'shouldEvictFeature'),
    sliceFunction(SOURCE, 'onSnapshotChanged'),
  ].join('\n');
  runInContext(code, context);

  const prevManifest = {
    snapshot_id: 'snap-1',
    regions: { 'metro/nyc': 'g1', 'metro/sf': 'g1' },
  };
  const nextManifest = {
    snapshot_id: 'snap-2',
    regions: { 'metro/nyc': 'g1', 'metro/sf': 'g2' },
    tile_indexes: { '9': { 'p-nyc': { cities: ['nyc'] }, 'p-sf': { cities: ['sf'] } } },
  };

  runInContext('onSnapshotChanged(prevManifest, nextManifest)', Object.assign(context, { prevManifest, nextManifest }));

  assert.equal(context.tileFeatures.has('cell-nyc'), true);
  assert.equal(context.tileFeatures.has('cell-sf'), false);
  assert.equal(context.fetchedTiles.has('p-nyc'), true);
  assert.equal(context.fetchedTiles.has('p-sf'), false);
  const cached = context.lodTileCache.get(9);
  assert.deepEqual(cached.features.map(f => f.properties.city_id), ['nyc']);
  assert.equal(cached.fetched.has('p-nyc'), true);
  assert.equal(cached.fetched.has('p-sf'), false);
});
