# Stream log — carto-client — 2026-08-23

## Claim

- **Stream id:** `carto-client` (HAR-17, Wave F)
- **Leaf files I will create/edit:**
  - `src/producers/carto_client.py`
  - `tests/unit/test_carto_client.py`
  - `.streams/carto-client.md`
- **Spine files I expect to need:** none (read-only reference of
  `src/producers/socrata_client.py`, `src/producers/arcgis_client.py`,
  `src/spatial/city_registry.py`, `src/producers/scheduler.py`)

## Intent

A `CartoClient` mirroring socrata/arcgis clients' ergonomics (constructor,
backoff/retry on 429/5xx, logging, `paginate(...)` generator yielding
List[Dict]) that satisfies the `PaginatingClient` protocol, using keyset
paging against the CARTO SQL API (`phl.carto.com`), with sentinel-date
exclusion for watermark ordering. Unit tests against live-captured payload
fixtures; optional `@pytest.mark.live` contract test gated by
URBAN_LIVE_PROBE=1.

## Decisions

- 2026-08-23 (claim) — Endpoint accepted as either full SQL-API base URL
  (`https://phl.carto.com/api/v2/sql`) or bare domain (`phl.carto.com`) or
  `carto://<domain>/<table>` URI; table passed separately or parsed from URI.
- 2026-08-23 — **URI scheme chosen:** `carto://phl.carto.com/permits` preferred;
  full URL and bare domain forms also accepted (require explicit `table=` kwarg).
  All resolve to `GET https://<domain>/api/v2/sql?q=<sql>`.
- 2026-08-23 — **Keyset columns verified live per Philly table** (all have
  `cartodb_id`; order col from watermark):
  - `permits` → (`permitissuedate`, `cartodb_id`)
  - `public_cases_fc` → (`requested_datetime`, `cartodb_id`)
  - `business_licenses` → (`mostrecentissuedate`, `cartodb_id`)
  - `rtt_summary` → (`document_date`, `cartodb_id`)
- 2026-08-23 — **Sentinel filter text** emitted exactly:
  `<col> IS NOT NULL AND <col> >= '1900-01-01' AND <col> < '2101-01-01'`.
  Lexicographic bounds work for ISO timestamps (index-friendly, no casts).
  Auto-enables when the order column name contains "date";
  `exclude_sentinel_dates=False` disables. NULLs always excluded from keyset
  key columns (tuple comparisons with NULL are undefined in Postgres).
- 2026-08-23 — Live probes confirmed: year-3200 sentinel present in
  `business_licenses.mostrecentissuedate` (row cartodb_id=304425);
  `rtt_summary.document_date` frequently NULL; payload shape is
  `{"rows": [...], "time": float, "fields"/"total_rows": ...}`.
  Fixtures embedded trimmed captures of all four tables.

## Current step

Done.

## Next step

None — stream complete. Wiring happens in Wave C3 when Philadelphia registers
(`DatasetSpec.extra` should carry `{"order_by": ..., "id_col": "cartodb_id",
"exclude_sentinel_dates": True}` per dataset).
