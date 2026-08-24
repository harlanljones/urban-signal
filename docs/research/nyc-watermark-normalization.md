# NYC watermark normalization spike

## Finding

The NYC DOB permits feed `ipu4-2q9a` exposes `issuance_date` as text. The
captured corpus contains ISO dates through `2020-06-05` and `MM/DD/YYYY` values
after that, including `08/21/2026`. Lexical comparison is unsafe: the current
value beginning with `08/` sorts before the historical value beginning with
`2020-` even though it is newer.

## Decision

Generalize typed parsing and comparison as a small client-side utility. The
formats are not NYC-exclusive: the registry already spans ISO dates, RFC3339
timestamps, compact dates, epoch values, and text dates across Socrata,
ArcGIS, CARTO, and CKAN feeds. Keeping the parser in
`src/producers/watermarks.py` prevents each monitor or client from making a
different comparison decision. The staleness probe re-exports the shared
parser under its existing `parse_timestamp` name for compatibility.

Keep query construction source-specific. Socrata still receives the raw
column expression it understands; this spike does not pretend a generic
client can make a text column's server-side `>` filter chronological. NYC's
incremental scheduler path should use a typed-safe source query or a bounded
client-side reconciliation before enabling text-watermark incrementals.

## Evidence

- `tests/unit/test_watermarks.py` pins the mixed corpus and proves chronological
  comparison, sorting, invalid-value behavior, and newest-value selection.
- `tests/unit/test_feed_staleness_probe.py` proves the weekly probe consumes the
  shared behavior and catches a deliberately stale fixture.
