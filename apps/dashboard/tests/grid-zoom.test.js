import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createContext, runInContext } from 'node:vm';

// Execute the dashboard's actual loader; only browser/HTTP boundaries are stubbed.
function dashboard() {
  const html = readFileSync(new URL('../public/index.html', import.meta.url), 'utf8');
  const states = html.slice(html.indexOf('    const fetchedTiles'), html.indexOf('    // National overlay cache'));
  const loader = html.slice(html.indexOf('    function updateViewportTiles()'), html.indexOf('    function setupGridLayers()'));
  const requests = [];
  const renders = [];
  let zoom = 8;
  const parent = '842830fffffffff';
  const context = createContext({
    console, ZOOM_FLOOR: 6,
    document: { getElementById: () => null },
    parentsCoveringBounds: () => [parent],
    setHexLayersVisible() {}, haversineDistance: () => 0,
    h3: { cellToLatLng: () => [0, 0] },
    map: { getZoom: () => zoom, getBounds: () => ({}), getCenter: () => ({ lat: 0, lng: 0 }),
      getSource: () => ({ setData: data => renders.push(Array.from(data.features, f => f.properties.h3_index)) }), triggerRepaint() {} },
    snapshotManifest: { tile_indexes: { '7': { [parent]: {} }, '8': { [parent]: {} }, '9': { [parent]: {} } } },
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
