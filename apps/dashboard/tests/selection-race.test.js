import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import vm from 'node:vm';
import { describe, expect, it } from 'bun:test';

const dashboardPath = join(import.meta.dir, '../../api/src/serving/dashboard.py');
const dashboardSource = readFileSync(dashboardPath, 'utf8');

function extractFunction(name) {
  const match = dashboardSource.match(new RegExp(`\\b(?:async )?function ${name}\\s*\\(`));
  if (!match) throw new Error(`Could not find ${name}`);
  const start = match.index;
  const open = dashboardSource.indexOf('{', start);
  let depth = 0;
  let quote = null;
  let lineComment = false;
  let blockComment = false;
  for (let i = open; i < dashboardSource.length; i++) {
    const ch = dashboardSource[i], next = dashboardSource[i + 1];
    if (lineComment) { if (ch === '\n') lineComment = false; continue; }
    if (blockComment) { if (ch === '*' && next === '/') { blockComment = false; i++; } continue; }
    if (quote) {
      if (ch === '\\') { i++; continue; }
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === '/' && next === '/') { lineComment = true; i++; continue; }
    if (ch === '/' && next === '*') { blockComment = true; i++; continue; }
    if (ch === '"' || ch === "'" || ch === '`') { quote = ch; continue; }
    if (ch === '{') depth++;
    if (ch === '}' && --depth === 0) return dashboardSource.slice(start, i + 1);
  }
  throw new Error(`Unclosed function ${name}`);
}

const functions = [
  'inspectH3CellWithNationalFallback', 'inspectH3Cell', 'clearSelection', 'handleHexSelection', 'searchCoordinateOrHex', 'closeMobilePanels', 'openMobilePanel'
].map(extractFunction).join('\n');
const coordinateHelpers = [
  'haversineDistance', 'getSubmarketInfoByCoords', 'resolveDivisionByNearestSubmarket', 'getBoroughNameByCoords'
].map(extractFunction).join('\n');

function harness(fetchImpl) {
  const state = { rendered: [], selected: null, clears: 0, toasts: [], flights: [] };
  const bodyClasses = new Set();
  const context = {
    selectionGeneration: 0,
    selectedH3Index: null,
    selectedLocationH3Index: null,
    selectedGeoAnchor: null,
    gridGeoJSON: null,
    map: null,
    shapChart: null,
    INSPECTOR_EMPTY_HTML: null,
    fetch: fetchImpl,
    renderCatalystFeed() { state.rendered.push(context.selectedLocationH3Index); },
    showToast(message) { state.toasts.push(message); },
    isMobileLayout: () => true,
    document: {
      body: { classList: {
        add(...classes) { classes.forEach(cls => bodyClasses.add(cls)); },
        remove(...classes) { classes.forEach(cls => bodyClasses.delete(cls)); },
        contains(cls) { return bodyClasses.has(cls); }
      } },
      getElementById() { return null; }
    },
    state,
    bodyClasses,
    syncToolbarActive() {},
    requestAnimationFrame() {},
    setTimeout() {},
    getSubmarketInfoByCoords: () => null,
    getBoroughNameByCoords: () => '',
    normalizeBorough: value => value,
    h3: {
      isValidCell: cell => cell === 'valid-cell',
      cellToLatLng: cell => {
        if (cell !== 'valid-cell') throw new Error('Invalid H3 cell');
        return [40, -73];
      },
      latLngToCell: (lat, lng) => {
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) throw new Error('Invalid latitude or longitude');
        return 'search-cell';
      }
    },
    FOCUS_ZOOM: 12,
    FOCUS_PITCH: 40,
    currentPerspective: '2D',
    REDUCED_MOTION: true
  };
  vm.runInNewContext(functions, context);
  return context;
}

function deferred() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return { promise, resolve };
}

const response = payload => ({ ok: true, json: async () => payload });

function coordinateHelperHarness() {
  const context = {
    SUBMARKETS: {
      Equator: { lat: 0, lng: 0, borough: 'Equator Borough' },
      Meridian: { lat: 40, lng: 0, borough: 'Meridian Borough' }
    }
  };
  vm.runInNewContext(coordinateHelpers, context);
  return context;
}

describe('selection request races', () => {
  it('searches valid coordinates on the equator or prime meridian', async () => {
    for (const input of ['0,-75', '40,0', '0,0']) {
      const requests = [];
      const ctx = harness(async (_url, init) => {
        requests.push(JSON.parse(init.body));
        return { ok: false };
      });
      ctx.map = {
        flyTo(options) { ctx.state.flights.push(options); },
        getLayer: () => false
      };

      await ctx.searchCoordinateOrHex(input);

      expect(requests).toHaveLength(1);
      expect(requests[0]).toMatchObject({
        latitude: Number(input.split(',')[0]),
        longitude: Number(input.split(',')[1]),
        h3_index: 'search-cell'
      });
      expect(ctx.selectedLocationH3Index).toBe('search-cell');
    }
  });

  it('rejects malformed, partial, out-of-range, and invalid H3 searches without changing selection', async () => {
    for (const input of ['north,-73', '40oops,-75', '40,', '1,2,3', '91,-73', '40,181', '8not-a-cell']) {
      const requests = [];
      const ctx = harness(async (...args) => {
        requests.push(args);
        return { ok: false };
      });
      ctx.handleHexSelection({ h3_index: 'accepted', centroid_lat: 2, centroid_lng: 2 });
      ctx.map = {
        flyTo(options) {
          ctx.state.flights.push(options);
          if (Math.abs(options.center[1]) > 90 || Math.abs(options.center[0]) > 180) {
            throw new Error('Invalid LngLat coordinate');
          }
        },
        getLayer: () => false
      };
      ctx.state.rendered.length = 0;
      ctx.state.flights.length = 0;
      ctx.state.toasts.length = 0;

      await ctx.searchCoordinateOrHex(input);

      expect(requests).toHaveLength(0);
      expect(ctx.state.flights).toHaveLength(0);
      expect(ctx.state.toasts).toHaveLength(1);
      expect(ctx.selectedLocationH3Index).toBe('accepted');
      expect(ctx.state.rendered).toEqual([]);
    }
  });

  it('keeps zero-axis coordinates available to submarket and division lookup', () => {
    const ctx = coordinateHelperHarness();

    expect(ctx.getSubmarketInfoByCoords(0, 0).name).toBe('Equator');
    expect(ctx.getSubmarketInfoByCoords(40, 0).name).toBe('Meridian');
    expect(ctx.getBoroughNameByCoords(0, 0)).toBe('Equator Borough');
    expect(ctx.getBoroughNameByCoords(40, 0)).toBe('Meridian Borough');
  });

  it('does not cancel a pending valid search when a malformed search is entered', async () => {
    const d = deferred();
    const ctx = harness(() => d.promise);
    ctx.map = { flyTo() {}, getLayer: () => false };

    const pending = ctx.searchCoordinateOrHex('40,-73');
    await expect(ctx.searchCoordinateOrHex('north,-73')).resolves.toBeUndefined();
    d.resolve(response({ h3_index: 'search-cell', centroid_lat: 40, centroid_lng: -73 }));
    await pending;

    expect(ctx.selectedLocationH3Index).toBe('search-cell');
  });

  it('keeps the newer successful selection when responses resolve out of order', async () => {
    const requests = [];
    const ctx = harness(() => { const d = deferred(); requests.push(d); return d.promise; });
    const older = ctx.inspectH3Cell('older', 1, 1);
    const newer = ctx.inspectH3Cell('newer', 2, 2);
    requests[1].resolve(response({ h3_index: 'newer', centroid_lat: 2, centroid_lng: 2 }));
    await newer;
    requests[0].resolve(response({ h3_index: 'older', centroid_lat: 1, centroid_lng: 1 }));
    await older;
    expect(ctx.selectedLocationH3Index).toBe('newer');
    expect(ctx.state.rendered).toEqual(['newer']);
  });

  it('does not apply a stale national-only fallback after a newer selection', async () => {
    const requests = [];
    const ctx = harness(() => { const d = deferred(); requests.push(d); return d.promise; });
    const old = ctx.inspectH3CellWithNationalFallback('national-old', 1, 1, { h3_index: 'national-old' });
    const current = ctx.inspectH3CellWithNationalFallback('national-current', 2, 2, { h3_index: 'national-current', centroid_lat: 2, centroid_lng: 2 });
    requests[1].resolve(response({ h3_index: 'national-current', centroid_lat: 2, centroid_lng: 2 }));
    await current;
    requests[0].resolve({ ok: false });
    await old;
    expect(ctx.selectedLocationH3Index).toBe('national-current');
    expect(ctx.state.rendered).toEqual(['national-current']);
  });

  it('invalidates a pending prediction when selection is cleared', async () => {
    const d = deferred();
    const ctx = harness(() => d.promise);
    const pending = ctx.inspectH3CellWithNationalFallback('pending', 1, 1, { h3_index: 'pending' });
    ctx.clearSelection();
    d.resolve(response({ h3_index: 'pending', centroid_lat: 1, centroid_lng: 1 }));
    await pending;
    expect(ctx.selectedLocationH3Index).toBeNull();
    expect(ctx.state.rendered).toEqual([null]);
  });

  it('invalidates a pending prediction when a direct selection is accepted', async () => {
    const d = deferred();
    const ctx = harness(() => d.promise);
    const pending = ctx.inspectH3CellWithNationalFallback('pending', 1, 1, { h3_index: 'pending' });
    ctx.handleHexSelection({ h3_index: 'direct', centroid_lat: 2, centroid_lng: 2 });
    d.resolve(response({ h3_index: 'pending', centroid_lat: 1, centroid_lng: 1 }));
    await pending;
    expect(ctx.selectedLocationH3Index).toBe('direct');
    expect(ctx.state.rendered).toEqual(['direct']);
  });

  it('coordinates national and metro requests and renders catalyst state after acceptance', async () => {
    const requests = [];
    const ctx = harness(() => { const d = deferred(); requests.push(d); return d.promise; });
    const metro = ctx.inspectH3Cell('metro', 3, 3);
    const national = ctx.inspectH3CellWithNationalFallback('national', 4, 4, { h3_index: 'national', centroid_lat: 4, centroid_lng: 4 });
    requests[1].resolve(response({ h3_index: 'national', centroid_lat: 4, centroid_lng: 4 }));
    await national;
    requests[0].resolve(response({ h3_index: 'metro', centroid_lat: 3, centroid_lng: 3 }));
    await metro;
    expect(ctx.selectedLocationH3Index).toBe('national');
    expect(ctx.state.rendered).toEqual(['national']);
  });

  it('does not apply a coordinate search after a direct selection or clear', async () => {
    for (const action of ['direct', 'clear']) {
      const d = deferred();
      const ctx = harness(() => d.promise);
      const search = ctx.searchCoordinateOrHex('40,-73');
      if (action === 'direct') ctx.handleHexSelection({ h3_index: 'direct', centroid_lat: 2, centroid_lng: 2 });
      else ctx.clearSelection();
      d.resolve(response({ h3_index: 'searched', centroid_lat: 40, centroid_lng: -73 }));
      await search;
      expect(ctx.selectedLocationH3Index).toBe(action === 'direct' ? 'direct' : null);
      expect(ctx.state.rendered).toEqual(action === 'direct' ? ['direct'] : [null]);
    }
  });

  it('does not let a pending coordinate search replace a newer metro selection', async () => {
    const requests = [];
    const ctx = harness(() => { const d = deferred(); requests.push(d); return d.promise; });
    const search = ctx.searchCoordinateOrHex('40,-73');
    const metro = ctx.inspectH3Cell('metro', 3, 3);
    requests[1].resolve(response({ h3_index: 'metro', centroid_lat: 3, centroid_lng: 3 }));
    await metro;
    requests[0].resolve(response({ h3_index: 'searched', centroid_lat: 40, centroid_lng: -73 }));
    await search;
    expect(ctx.selectedLocationH3Index).toBe('metro');
    expect(ctx.state.rendered).toEqual(['metro']);
  });

  it('cancels a pending prediction when the open mobile inspector is dismissed', async () => {
    const d = deferred();
    const ctx = harness(() => d.promise);
    ctx.handleHexSelection({ h3_index: 'accepted', centroid_lat: 2, centroid_lng: 2 });
    ctx.document.body.classList.add('drawer-right-open');
    const pending = ctx.inspectH3CellWithNationalFallback('pending-mobile', 1, 1, { h3_index: 'pending-mobile' });
    ctx.closeMobilePanels();
    d.resolve(response({ h3_index: 'pending-mobile', centroid_lat: 1, centroid_lng: 1 }));
    await pending;
    expect(ctx.selectedLocationH3Index).toBe('accepted');
    expect(ctx.bodyClasses.has('drawer-right-open')).toBe(false);
    expect(ctx.state.rendered).toEqual(['accepted']);
  });

  it('keeps a pending prediction alive when only search or left menu is dismissed', async () => {
    for (const drawer of ['search-open', 'drawer-left-open']) {
      const d = deferred();
      const ctx = harness(() => d.promise);
      ctx.document.body.classList.add(drawer);
      const pending = ctx.inspectH3CellWithNationalFallback('pending-menu', 1, 1, { h3_index: 'pending-menu', centroid_lat: 1, centroid_lng: 1 });
      ctx.closeMobilePanels();
      d.resolve(response({ h3_index: 'pending-menu', centroid_lat: 1, centroid_lng: 1 }));
      await pending;
      expect(ctx.selectedLocationH3Index).toBe('pending-menu');
      expect(ctx.bodyClasses.has('drawer-right-open')).toBe(true);
    }
  });
});
