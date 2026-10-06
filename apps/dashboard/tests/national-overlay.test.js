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
