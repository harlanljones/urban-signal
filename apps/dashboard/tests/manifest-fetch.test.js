// Manifest fetch retry (dashboard fetchManifest). The dashboard is a single
// Python-served HTML document, so the client logic cannot be imported; these
// tests slice the relevant async functions out of serving/dashboard.py and run
// them in a node:vm context with stubbed fetch/DOM globals.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createContext, runInContext } from 'node:vm';

const SOURCE = readFileSync(
  new URL('../../api/src/serving/dashboard.py', import.meta.url),
  'utf8',
);

/** Extract a balanced function body by name, keeping a leading `async`. */
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

/**
 * Build a harness running the real fetchManifest over a scripted fetch.
 * `responses` is consumed one entry per fetch call: `{ ok, body }` or
 * `{ throw: true }`. `sleep` records delays instead of waiting.
 */
function harness(responses, manifestState = { snapshotManifest: null, SNAPSHOT_ID: null }) {
  const calls = { fetch: 0, toasts: [], sleeps: [], changed: 0, legend: 0, pill: '' };
  const element = { textContent: '', classList: { add() {} }, title: '' };
  const context = createContext({
    ...manifestState,
    MANIFEST_MAX_RETRIES: 3,
    fetch: async () => {
      const next = responses[Math.min(calls.fetch, responses.length - 1)];
      calls.fetch += 1;
      if (next.throw) throw new Error('network');
      return { ok: next.ok, status: next.status ?? (next.ok ? 200 : 503), json: async () => next.body };
    },
    sleep: async (ms) => { calls.sleeps.push(ms); },
    backoffDelay: (attempt) => [500, 1500, 4000][Math.min(attempt, 2)],
    showToast: (message, type, label, action) => { calls.toasts.push({ message, type, label, action }); },
    populateContextMetrics: () => {},
    onSnapshotChanged: () => { calls.changed += 1; },
    updateCoverageLegend: () => { calls.legend += 1; },
    document: { getElementById: (id) => (id === 'stream-status-text' ? element : id === 'stream-pulse-dot' ? element : id === 'stream-status-pill' ? element : null) },
  });
  const code = [
    sliceFunction(SOURCE, 'fetchManifestOnce'),
    sliceFunction(SOURCE, 'fetchManifest'),
  ].join('\n');
  runInContext(code, context);
  return { context, calls, run: (expr) => runInContext(expr, context) };
}

const MANIFEST_A = {
  snapshot_id: 'r-1',
  generated_at: '2026-10-12T21:47:00+00:00',
  cities: ['nyc'],
  coverage: { schema_version: 1 },
};

test('a transient manifest failure retries and succeeds without an error toast', async () => {
  const h = harness([
    { throw: true },
    { ok: false, status: 503 },
    { ok: true, body: MANIFEST_A },
  ]);
  const result = await h.run('fetchManifest()');
  assert.equal(result, true);
  assert.equal(h.calls.fetch, 3);
  assert.deepEqual(h.calls.sleeps, [500, 1500]);
  assert.equal(h.calls.toasts.length, 0);
  assert.equal(h.context.SNAPSHOT_ID, 'r-1');
  assert.deepEqual(h.context.snapshotManifest, MANIFEST_A);
  assert.equal(h.calls.changed, 1, 'snapshot change is applied after the retry succeeds');
  assert.equal(h.calls.pill, '');
});

test('persistent manifest failure exhausts the ladder, then offers a retry', async () => {
  const h = harness([{ throw: true }]);
  const result = await h.run('fetchManifest()');
  assert.equal(result, false);
  assert.equal(h.calls.fetch, 4, 'one attempt plus three retries');
  assert.deepEqual(h.calls.sleeps, [500, 1500, 4000]);
  assert.equal(h.calls.toasts.length, 1);
  assert.equal(h.calls.toasts[0].label, 'Retry');
  assert.equal(typeof h.calls.toasts[0].action, 'function');
});

test('a same-id refresh updates coverage without firing the snapshot change path', async () => {
  const h = harness([{ ok: true, body: MANIFEST_A }], { snapshotManifest: MANIFEST_A, SNAPSHOT_ID: 'r-1' });
  await h.run('fetchManifest()');
  assert.equal(h.calls.changed, 0);
  assert.equal(h.calls.legend, 1);
});

test('a new-id refresh passes the outgoing manifest to onSnapshotChanged', async () => {
  const next = { ...MANIFEST_A, snapshot_id: 'r-2' };
  const h = harness([{ ok: true, body: next }], { snapshotManifest: MANIFEST_A, SNAPSHOT_ID: 'r-1' });
  await h.run('fetchManifest()');
  assert.equal(h.calls.changed, 1);
  assert.equal(h.context.SNAPSHOT_ID, 'r-2');
});
