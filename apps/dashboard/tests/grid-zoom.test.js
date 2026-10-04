import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createContext, runInContext } from 'node:vm';

// Execute the dashboard's actual loader; only browser/HTTP boundaries are stubbed.
function dashboard(parents = null) {
  const html = readFileSync(new URL('../public/index.html', import.meta.url), 'utf8');
  const states = html.slice(html.indexOf('    const fetchedTiles'), html.indexOf('    // National overlay cache'));
  const loader = html.slice(html.indexOf('    function updateViewportTiles()'), html.indexOf('    function setupGridLayers()'));
  const requests = [];
  const renders = [];
  let zoom = 8;
  const parent = '842830fffffffff';
  const context = createContext({
    console, ZOOM_FLOOR: 6, REDUCED_MOTION: true, selectedGeoAnchor: null, selectedH3Index: null,
    document: { getElementById: () => null },
    parentsCoveringBounds: () => parents || [parent],
    setHexLayersVisible() {}, haversineDistance: () => 0,
    h3: { cellToLatLng: () => [0, 0] },
    map: { getZoom: () => zoom, getBounds: () => ({}), getCenter: () => ({ lat: 0, lng: 0 }),
      getSource: () => ({ setData: data => renders.push(Array.from(data.features, f => f.properties.h3_index)) }), triggerRepaint() {}, getLayer: () => null },
    snapshotManifest: { tile_indexes: Object.fromEntries([7, 8, 9].map(res => [res, Object.fromEntries((parents || [parent]).map(p => [p, {}]))])) },
    gridGeoJSON: null,
    fetch: url => new Promise(resolve => requests.push({ url, resolve })),
  });
  runInContext(states + loader, context);
  return {
    requests, renders,
    zoomTo(z) { zoom = z; runInContext('updateViewportTiles()', context); },
    async finish(index, cell, ok = true) {
      requests[index].resolve({ ok, json: async () => ({ features: [{ properties: { h3_index: cell } }] }) });
      await new Promise(resolve => setImmediate(resolve));
    },
  };
}

test('zooming between LODs sharing a parent requests the new resolution and replaces cells', async () => {
  const app = dashboard();
  app.zoomTo(8);
  await app.finish(0, 'coarse');
  app.zoomTo(10);
  assert.equal(app.requests.length, 2);
  assert.match(app.requests[1].url, /res=8&/);
  await app.finish(1, 'fine');
  assert.deepEqual(app.renders.at(-1), ['fine']);
  app.zoomTo(8);
  assert.equal(app.requests.length, 3);
  await app.finish(2, 'coarse');
  assert.deepEqual(app.renders.at(-1), ['coarse']);
});

test('an old resolution response cannot repaint or suppress the new resolution', async () => {
  const app = dashboard();
  app.zoomTo(8);
  app.zoomTo(10);
  assert.equal(app.requests.length, 2);
  await app.finish(1, 'fine');
  await app.finish(0, 'coarse');
  assert.deepEqual(app.renders.at(-1), ['fine']);
});

test('failed tile responses can be retried when the camera settles again', async () => {
  const app = dashboard();
  app.zoomTo(8);
  await app.finish(0, 'coarse', false);
  app.zoomTo(8);
  assert.equal(app.requests.length, 2);
});

test('rapid zoom reversals retain concurrency slots and discard both obsolete generations', async () => {
  const app = dashboard();
  app.zoomTo(8);
  app.zoomTo(10);
  app.zoomTo(12);
  assert.equal(app.requests.length, 2);
  await app.finish(0, 'coarse');
  assert.equal(app.requests.length, 3);
  assert.match(app.requests[2].url, /res=9&/);
  await app.finish(2, 'finest');
  await app.finish(1, 'fine');
  assert.deepEqual(app.renders.at(-1), ['finest']);
  app.zoomTo(8);
  assert.equal(app.requests.length, 4);
  await app.finish(3, 'coarse');
  assert.deepEqual(app.renders.at(-1), ['coarse']);
});


test('outgoing grid stays rendered until the incoming resolution is ready', async () => {
  const app = dashboard();
  app.zoomTo(8); await app.finish(0, 'coarse');
  app.zoomTo(12);
  assert.deepEqual(app.renders.at(-1), ['coarse']);
  assert.match(app.requests[1].url, /res=9&/);
  await app.finish(1, 'fine');
  assert.deepEqual(app.renders.at(-1), ['fine']);
});

test('failed partial incoming batches retain outgoing cells until retry completes', async () => {
  const app = dashboard(Array.from({length: 33}, (_, i) => 'parent-' + i));
  app.zoomTo(8); await app.finish(0, 'coarse-a'); await app.finish(1, 'coarse-b');
  app.zoomTo(12);
  await app.finish(3, 'fine-b');
  assert.deepEqual(app.renders.at(-1), ['coarse-a', 'coarse-b']);
  await app.finish(2, '', false);
  assert.deepEqual(app.renders.at(-1), ['coarse-a', 'coarse-b']);
  app.zoomTo(12); await app.finish(4, 'fine-a');
  assert.deepEqual(app.renders.at(-1), ['fine-b', 'fine-a']);
});

test('hysteresis suppresses repeated LOD changes near a boundary', async () => {
  const app = dashboard();
  app.zoomTo(8); await app.finish(0, 'coarse');
  app.zoomTo(9.05); assert.equal(app.requests.length, 1);
  app.zoomTo(9.2); await app.finish(1, 'middle');
  app.zoomTo(8.95); assert.equal(app.requests.length, 2);
  app.zoomTo(8.8); assert.equal(app.requests.length, 3);
});


test('polygon expansion reaches exact real geometry without changing metric values', () => {
  const html = readFileSync(new URL('../public/index.html', import.meta.url), 'utf8');
  const code = html.slice(html.indexOf('    function handoffGeometry('), html.indexOf('    function cancelGridHandoff('));
  const context = createContext({ h3: { cellToLatLng: cell => cell === 'parent' ? [2, 2] : [1, 1], cellToParent: () => 'parent' } });
  runInContext(code, context);
  const feature = { type: 'Feature', properties: { h3_index: 'child', delta_6m_p50: 0.15 }, geometry: { type: 'Polygon', coordinates: [[[0.9, 1], [1.1, 1], [1, 1.1], [0.9, 1]]] } };
  context.feature = feature;
  const first = runInContext('handoffGeometry(feature, 0, 8, 9)', context);
  const last = runInContext('handoffGeometry(feature, 1, 8, 9)', context);
  assert.notDeepEqual(JSON.parse(JSON.stringify(first.geometry)), feature.geometry);
  assert.deepEqual(JSON.parse(JSON.stringify(last.geometry)), feature.geometry);
  assert.equal(last.properties, feature.properties);
  assert.equal(feature.properties.delta_6m_p50, 0.15);
});
