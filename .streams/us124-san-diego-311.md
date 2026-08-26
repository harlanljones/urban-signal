# Stream log — us124-san-diego-311 — 2026-08-25

## Claim

- **Issue:** US-124 — Register San Diego 311 feed (Get It Done CSV)
- **Parallel leaf stream.** Additive-only; I own the San Diego 311 registration and did not touch other cities' blocks. The orchestrator holds the interlock; I did **not** run `pytest -m interlock` or the full suite.
- **Files changed (working tree, uncommitted):**
  - `apps/api/src/config.py`
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/producers/complaints_311_producer.py`
  - `apps/api/tests/unit/test_producers_san_diego.py`
  - `README.md` (San Diego 311 coverage cell)
  - `.streams/us124-san-diego-311.md` (this log)

## Live probe (verified, not trusted)

Probed on 2026-08-25 with curl against `seshat.datasd.org` (S3 + CloudFront).

- `get_it_done_requests_closed_2026_datasd.csv` → **HTTP 200**, `last-modified: Tue, 25 Aug 2026 07:08:23 GMT` (today), 277,841 raw lines.
- `get_it_done_requests_open_datasd.csv` → **HTTP 200** (companion open queue), 90,057 raw lines.
- **23 columns** (already lowercase in-source; `CSVClient` lowercases anyway — field_map uses lowercase keys):
  `service_request_id, service_request_parent_id, sap_notification_number, date_requested, case_age_days, case_record_type, service_name, service_name_detail, date_closed, status, lat, lng, street_address, zipcode, council_district, comm_plan_code, comm_plan_name, park_name, case_origin, referred, iamfloc, floc, public_description`.
- **Freshness:** newest `date_requested` = 2026-08-24 23:37 (closed) / 2026-08-24 23:58 (open). Matches the sweep doc.
- **Geocode:** 98.4% closed / 98.9% open carry native `lat`/`lng` floats (null-island guard covers the ~1.5% remainder).
- **Watermark format:** `date_requested` is ISO `YYYY-MM-DD HH:MM:SS.fff` (`2026-08-24 23:37:00.000`) — `_parse_datetime` absorbs via `fromisoformat`; string-compare watermark filter in `CSVClient._row_matches` works (ISO strings compare lexicographically).
- **Year-scoped backfills:** `closed_2016`…`closed_2026` all HTTP 200. `closed_2027` → **HTTP 403** (S3 AccessDenied — future-rollover entry, published next year). Confirmed the permits feed's `approvals_issued_2027_datasd.csv` is also 403 today, so this is the established `endpoint_by_year` rollover pattern (resolve_endpoint picks the newest non-future year).

## Decisions

- **`watermark_col="date_requested"`**, `id_keys=["service_request_id"]`, `platform="csv"`.
- **`endpoint_by_year`** carries 2016–2027 (2027 forward-looking like the permits feed). `companion_endpoints.open` = the daily-regenerated open-queue file (it holds the freshest still-open cases; the closed-year file only carries Closed/Referred).
- **`field_map` columns lowercase** to match `CSVClient` header normalization. Lat/lng read native `lat`/`lng`; `complaint_type` from `service_name`+`service_name_detail`; `borough` from `council_district`+`comm_plan_name`; zipcode native `zipcode`.
- **City sniff:** in `Complaints311Producer.parse_socrata_row`, SF's branch keys on `service_request_id` too, so SD rows (which also carry `service_request_id`) must not be captured by SF. Added a **San Diego branch placed before the SF branch** that requires `service_request_id` AND an SD-only corroborating marker (`date_requested` / `sap_notification_number` / `comm_plan_name`) before claiming the row. `run_stream` always passes an explicit `city_id`, so autodetect only governs manual/test paths; the SF autodetect regression is pinned by a test.
- **`CSVClient` wired** into `complaints_311_producer` (`self.csv = CSVClient()` + `"csv"` in `_client_for`), mirroring `dob_permits_producer`.
- **No dashboard / snapshot wiring.** San Diego was already on the map (selector option + CITY_CONFIGS + static copy — wired under US-91 permits). Adding a feed to an already-listed city does not change the dashboard. `TestDashboardWiring` passes unchanged (the interlock test checks *city* presence, not per-feed).
- **No `csv_client.py` change.** `_row_matches` already strips one layer of wrapping parens on HEAD, so the scheduler's parenthesized watermark where-clause is handled.

## Verification run

From `apps/api` (`.venv`), focused tests only (not interlock / not full suite — orchestrator runs those at close-out):

- `test_producers_san_diego.py` → **18 passed** (incl. 10 new US-124 tests: spec/platform/rollover, lowercase field_map, row parse, dates/address, autodetect, metro-bbox, null-island reject, SF-shadow regression, CSVClient watermark filter).
- 311-producer + registry/config/field-map regression: `test_producers_la.py`, `test_producers_baltimore.py`, `test_producers_sf.py`, `test_field_maps.py`, `test_config.py`, `test_feedtype_taxonomy.py`, `test_registry_cadence.py` (plus san_diego) → **102 passed**.
- `ruff check` on touched Python files → **zero net-new violations** (pre-existing only: config.py 0, complaints_311_producer.py 1 × BLE001 `except Exception` at HEAD line 304, city_registry.py 30 × import-order/typing/`datetime.now(timezone.utc)`, test_producers_san_diego.py 0).
- End-to-end offline parse (real probe row): `CSVClient`-shape dict → `parse_socrata_row(city_id="san_diego")` → Complaint311Event with correct incident_id / lat-lng / created+closed dates / zipcode / status / source_neighborhood. Job name = `311_sd`.

## Discrepancy / open question

- None blocking. Live probe matched the sweep doc exactly (23 cols, 98.4%/98.9% geocoded, newest `date_requested` 2026-08-24, Last-Modified today).
- Noted: `closed_2027` 403s today (expected future-rollover entry) — this is the same as the registered permits feed; `resolve_endpoint` never selects it before 2027.
- The existing `test_san_diego_registration_scope_and_job_names` asserted `COMPLAINTS_311 not in reg.datasets`; changed to assert it **is** registered (SLA/DEEDS remain absent). This test now lives alongside the other added 311 tests in the same file.
- `docs/expansion-roadmap.md` has no San Diego row/cell, so nothing to update there; the README coverage row was the doc change.
