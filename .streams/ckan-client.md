# Stream log — ckan-client — 2026-08-23

## Claim

- **Stream id:** `ckan-client`
- **Leaf files I will create/edit:**
  - `src/producers/ckan_client.py`
  - `tests/unit/test_ckan_client.py`
  - `.streams/ckan-client.md`
- **Spine files I expect to need:** none (no producer/registry/scheduler edits; C5 wires later)

## Intent

Generic CKAN datastore client mirroring SocrataClient ergonomics (`paginate` with
endpoint_url/where_clause/order_by/batch_size/max_records) so the scheduler's poll
loop works unchanged against `ckan://<host>/<resource_id>` URIs. Boston permits +
311 are the verified targets. Reject non-datastore resources with readable errors.
Year-resource rollover hook for city_registry.

## Decisions

- 2026-08-23 — Claimed stream. Reading siblings + research doc first, then live-probing data.boston.gov.
- 2026-08-23 — **Live-probed data.boston.gov CKAN (all verified):**
  - Permits resource: `6ddcd912-32a0-43df-9908-63574f8c7e77`, datastore-active, `total: 660839`. Fields confirmed: `issued_date` (timestamp), `y_latitude`/`x_longitude` (numeric), `gpsy`/`gpsx` (state-plane).
  - 311 year resources confirmed: `254adca6…` ("NEW SYSTEM" current), `1a0b420d…` = 2026, `9d7c2214…` = 2025, one resource per year back to 2011.
  - **`filters` param is exact-match ONLY**: `{"issued_date": {"gt": "..."}}` → `error.query=["Invalid query"]`; `{"status":"Open"}` → success, total 377629. NOT usable for watermark queries.
  - **`datastore_search_sql` WORKS and is the watermark mechanism** on Boston: `WHERE issued_date > '2026-08-20T00:00:00' ORDER BY "_id" LIMIT n OFFSET m` → success; LIMIT+OFFSET both honored. No `total` in SQL results → short-page termination.
  - **Non-datastore rejection shape**: HTTP 200 with `{"success": false, "error": {"__type": "Not Found Error", "message": "Not found: Resource \"<id>\" was not found."}}`.
- 2026-08-23 — **Design:** where-clause translation parses Socrata-ish `<field> OP '<value>'` terms (OP ∈ =, !=, >, >=, <, <=, AND-combined). All-equality → `datastore_search` + `filters`; any range op → `datastore_search_sql` with quoted WHERE fragment. `order_by` maps to `sort=` / `ORDER BY`.
- 2026-08-23 — Endpoint URI: `ckan://<host>/<resource_id>`. `resolve_resource(today)` mirrors `city_registry.resolve_endpoint`: constructor takes optional `resource_by_year` dict + default resource; newest year ≤ today, else latest entry.

## Current step

DONE — all three files complete.

## Next step

None. Handoff notes for Wave C5:
- Register Boston with platform `"ckan"` and endpoints as `ckan://data.boston.gov/<resource_id>` URIs; expose `CkanClient` as `ckan` attribute on the Boston producer (scheduler `_paginating_client_for` dict-dispatch picks it up without edits).
- Permits: `ckan://data.boston.gov/6ddcd912-32a0-43df-9908-63574f8c7e77`, watermark `issued_date`. 311 current-year: `254adca6-64ab-4c5c-9fc0-a6da622be185`; use `CkanClient(resource_by_year={2026: "1a0b420d-99f1-4887-9851-990b2a5a6e17", ...})` + `resolve_resource(today)` at registration time (year resources verified back to 2011).
- Watermark mechanism: range clauses route to `datastore_search_sql` (verified working on Boston); equality-only clauses use `datastore_search` + `filters`.
- Note: `pytest.mark.live` is not registered in pyproject markers (spine file — not touched); emits an UnknownMarkWarning only.

## Results

- `src/producers/ckan_client.py` — 331 LOC. CkanClient: parse_endpoint (`ckan://host/res`), fetch_records (search vs search_sql routing), paginate (offset + `_total`/short-page termination, max_records exact clamp), resolve_resource, retry/backoff on 429/5xx, NonDatastoreResourceError rejection.
- `tests/unit/test_ckan_client.py` — 17 tests (15 unit passing; 2 `@pytest.mark.live` gated by URBAN_LIVE_PROBE=1, both pass live against data.boston.gov). Fixtures recorded from real probes incl. non-datastore error body and SQL watermark result.
- Verified live: permits total=660839; `filters` rejects range ops ("Invalid query"); `datastore_search_sql` supports WHERE/ORDER BY/LIMIT/OFFSET.
