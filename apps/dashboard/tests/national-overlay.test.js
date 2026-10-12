import { test } from 'bun:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createContext, runInContext } from 'node:vm';

function nationalRowsToFeatures() {
  const source = readFileSync(new URL('../../api/src/serving/dashboard.py', import.meta.url), 'utf8');
  const start = source.indexOf('    function nationalRowsToFeatures(payload)');
  const end = source.indexOf('    function applyNationalData()', start);
  assert.ok(start >= 0 && end > start, 'nationalRowsToFeatures helper is present');
  const context = createContext({
    h3: {
      cellToBoundary: () => [[40, -74], [40, -73.9], [40.1, -73.9]],
      cellToLatLng: () => [40.03, -73.97],
    },
  });
  runInContext(source.slice(start, end), context);
  return payload => {
    context.payload = payload;
    return runInContext('nationalRowsToFeatures(payload)', context);
  };
}

test('skips rows without percentile data and preserves a valid zero percentile', () => {
  const convert = nationalRowsToFeatures();
  const features = convert({
    cols: ['h3', 'jobs', 'workers', 'jobs_pct', 'workers_pct'],
    rows: [
      ['no-percentile', 100, null, null, null],
      ['zero-percentile', 100, null, 0, null],
      ['valid-percentile', null, 200, null, 75],
    ],
  });

  assert.deepEqual(Array.from(features, feature => feature.properties.h3_index), ['zero-percentile', 'valid-percentile']);
  assert.equal(features[0].properties.jobs_pct, 0);
  assert.equal(features[1].properties.workers_pct, 75);
});

// ---- Bridge band (ADR-0010): res-6 national underlay between the primary band and metro LOD ----

const SOURCE = readFileSync(new URL('../../api/src/serving/dashboard.py', import.meta.url), 'utf8');

function sliceFunction(name) {
  let start = SOURCE.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `${name} is present`);
  if (SOURCE.slice(start - 6, start) === 'async ') start -= 6;
  let depth = 0;
  let i = SOURCE.indexOf('{', start);
  for (; i < SOURCE.length; i += 1) {
    if (SOURCE[i] === '{') depth += 1;
    else if (SOURCE[i] === '}' && --depth === 0) { i += 1; break; }
  }
  return SOURCE.slice(start, i);
}

function constant(name) {
  const match = SOURCE.match(new RegExp(`const ${name} = ([0-9.]+);`));
  assert.ok(match, `${name} is declared`);
  return Number(match[1]);
}

function bridgeHarness(zoom, perspective = '2D') {
  const layers = new Map(['national-h3-fill', 'national-h3-line', 'national-h3-extrusion'].map(id => [id, { visibility: 'none', paint: {} }]));
  const loads = [];
  const state = { zoom, generation: 0 };
  const context = createContext({
    ZOOM_FLOOR: 6,
    NATIONAL_UNDERLAY_MAX_ZOOM: constant('NATIONAL_UNDERLAY_MAX_ZOOM'),
    NATIONAL_UNDERLAY_OPACITY: constant('NATIONAL_UNDERLAY_OPACITY'),
    NATIONAL_PRIMARY_OPACITY: constant('NATIONAL_PRIMARY_OPACITY'),
    currentPerspective: perspective,
    coverageState: { national: 'loading', metro: 'loading' },
    snapshotManifest: { coverage: { schema_version: 1, national: { status: 'available' } } },
    SNAPSHOT_ID: null,
    nationalActive: { 4: [], 5: [], 6: [] },
    nationalActiveRes: null,
    nationalCache: { 4: new Map(), 5: new Map(), 6: new Map() },
    nationalFetched: { 4: new Set(), 5: new Set(), 6: new Set() },
    nationalInFlight: new Map(),
    nationalLoadGeneration: 0,
    document: { getElementById: () => null },
    updateCoverageLegend() {}, applyNationalData() {}, clearNationalOverlay() {},
    res3ParentsCoveringBounds: () => ['832830fffffffff'],
    nationalCacheKey: (id, res, parent) => `${id}:${res}:${parent}`,
    loadNationalBatch: (res, parents, generation) => { loads.push({ res, parents, generation }); return Promise.resolve(); },
    map: {
      getZoom: () => state.zoom,
      getBounds: () => ({}),
      getLayer: id => layers.get(id),
      setLayoutProperty: (id, key, value) => { layers.get(id)[key] = value; },
      setPaintProperty: (id, key, value) => { layers.get(id).paint[key] = value; },
    },
  });
  runInContext([
    'nationalResForZoom', 'nationalCoverageStatus', 'coverageSchemaSupported',
    'updateNationalLayerVisibilities', 'updateNationalOverlay',
  ].map(sliceFunction).join('\n'), context);
  return { context, layers, loads, state };
}

test('national res 6 is reachable from the floor and res 4/5 keep their bands', () => {
  const { context } = bridgeHarness(7);
  const res = zoom => { context.zoom = zoom; return runInContext('nationalResForZoom(zoom)', context); };
  assert.deepEqual([4.9, 5, 5.9, 6, 7, 8.5].map(res), [4, 5, 5, 6, 6, 6]);
});

test('underlay band draws only a flat faint fill, even when the 3D perspective is selected', () => {
  const { context, layers } = bridgeHarness(7, '3D');
  runInContext('updateNationalLayerVisibilities()', context);
  assert.equal(layers.get('national-h3-fill').visibility, 'visible');
  assert.equal(layers.get('national-h3-fill').paint['fill-opacity'], constant('NATIONAL_UNDERLAY_OPACITY'));
  assert.equal(layers.get('national-h3-extrusion').visibility, 'none', 'no extrusion beneath metro hexes (US-422)');
  assert.equal(layers.get('national-h3-line').visibility, 'none');
  assert.ok(constant('NATIONAL_UNDERLAY_OPACITY') < constant('NATIONAL_PRIMARY_OPACITY'));
});

test('primary band keeps the 2D fill and 3D extrusion behaviour with full opacity', () => {
  const flat = bridgeHarness(5, '2D');
  runInContext('updateNationalLayerVisibilities()', flat.context);
  assert.equal(flat.layers.get('national-h3-fill').visibility, 'visible');
  assert.equal(flat.layers.get('national-h3-line').visibility, 'visible');
  assert.equal(flat.layers.get('national-h3-fill').paint['fill-opacity'], constant('NATIONAL_PRIMARY_OPACITY'));
  const tall = bridgeHarness(5, '3D');
  runInContext('updateNationalLayerVisibilities()', tall.context);
  assert.equal(tall.layers.get('national-h3-extrusion').visibility, 'visible');
  assert.equal(tall.layers.get('national-h3-fill').visibility, 'none');
});

test('above the underlay band every national layer is hidden', () => {
  const { context, layers } = bridgeHarness(9.2);
  runInContext('updateNationalLayerVisibilities()', context);
  for (const layer of layers.values()) assert.equal(layer.visibility, 'none');
});

test('res-6 chunks are requested in the bridge band and not requested above it', async () => {
  const bridge = bridgeHarness(7);
  await runInContext('updateNationalOverlay()', bridge.context);
  assert.deepEqual(bridge.loads.map(load => load.res), [6]);

  const metro = bridgeHarness(9.2);
  await runInContext('updateNationalOverlay()', metro.context);
  assert.equal(metro.loads.length, 0);
  assert.equal(metro.context.nationalLoadGeneration, 1, 'stale national reads are cancelled above the band');
});
