# Stream log — us125-san-diego-sla — 2026-08-25

## Claim

- **Issue:** US-125 — Register San Diego Business Tax Certificates feed (CSV SLA)
- **Solo leaf stream (final registration in the wave — no concurrency).** Additive-only;
  I own the San Diego SLA registration and did not touch other cities' blocks or the
  San Diego COMPLAINTS_311 block (US-124, already landed). The orchestrator holds the
  interlock; I did **not** run `pytest -m interlock` or the full suite.
- **Files changed (working tree, uncommitted):**
  - `apps/api/src/config.py`
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/producers/sla_licenses_producer.py`
  - `apps/api/tests/unit/test_producers_san_diego.py`
  - `README.md` (San Diego SLA coverage cell)
  - `.streams/us125-san-diego-sla.md` (this log)

## Live probe (verified, not trusted)

Probed on 2026-08-25 with curl against `seshat.datasd.org` (S3 + CloudFront).

- `sd_businesses_active_datasd.csv` → **HTTP 200**, `last-modified: Tue, 25 Aug 2026 09:06:01 GMT` (today),
  19,021,573 bytes, **59,875 rows**.
- **27 columns** (already lowercase in-source; `CSVClient` lowercases anyway — field_map uses
  lowercase keys), in order:
  `account_key, account_status, date_account_creation, date_cert_expiration,
  date_cert_effective, business_owner_name, ownership_type, date_business_start,
  dba_name, naics_sector, naics_code, naics_description, address_no, address_pd,
  address_road, address_sfx, address_no_fraction, address_city, address_state,
  address_zip, address_suite, address_pmb_box, address_po_box, bid, council_district,
  lat, lng`.
- **`account_key` is a float-string** (`'1974000024.0'`). Normalized `str(int(float(v)))`
  → `'1974000024'`. Round-trip verified for **all 59,875 rows — 0 failures**, max raw
  length 12 digits (no float-precision loss).
- **Geocode:** native `lat`/`lng` floats; 1,722/59,875 (~2.9%) missing coords. No `0.0/0.0`
  null-island placeholders in the sample. Some rows geocode outside the metro bbox
  (geocoder misplacement — normal; parsed and filtered downstream).
- **NAICS 72 (hospitality) present:** 4,138 rows (LIMS SLA term, mirrors LA/SF scope).
- **Date formats:** all `date_account_creation` / `date_cert_effective` / `date_cert_expiration`
  are 19-char `YYYY-MM-DD HH:MM:SS` — absorbed by `_parse_datetime` (`%Y-%m-%d %H:%M:%S`).
  Effective/expiration are future-dated by design (like NYC SLA); freshness is judged by
  **file refresh, not per-row dates** (snapshot feed).
- **`bid`** empty for 52,381/59,875 (~87%) rows — `borough` field_map lists `council_district`
  first, so it stays threaded from the district regardless.
- **Backfill / dict:** `sd_businesses_inactive_*` (plain + year-scoped) → **HTTP 403**
  (S3 AccessDenied, not currently published); `sd_businesses_dictionary_datasd.csv` → HTTP 200
  (metadata dictionary, 1,947 bytes — a reference file, not the data feed; not wired).
  The active snapshot is the single live data file.

## Decisions

- **`platform="csv"`**, `watermark_col="date_account_creation"`, `id_keys=["account_key"]`,
  `ingestion_mode="snapshot"`, `producer_key="sla"`, `topic=settings.topic_sla`,
  `interval_seconds=1800.0` (matches San Diego's other feeds). `topic_sla` = `raw.municipal.sla`.
- **Snapshot semantics:** with `ingestion_mode="snapshot"` the scheduler skips the incremental
  watermark `where` filter and re-pulls the full file each poll; cross-run dedup on
  `account_key` makes the re-poll a diff. (`watermark_col` still tracked for the high-watermark
  field, but snapshot mode gates the incremental predicate — Montgomery DEEDS is the same pattern.)
- **`field_map` columns lowercase** to match `CSVClient` header normalization. `license_id`
  from `account_key`; `effective_date`/`expiration_date` from the `date_cert_*` columns;
  `license_type` from `naics_description`+`naics_sector`; `dba` from `dba_name`; lat/lng native
  `lat`/`lng`; `borough` from `council_district`+`bid`; `address_street` from `address_road`.
- **`address_street`** maps to `address_road` (the canonical single address column; the CSV
  splits number/prefix/road/suffix/city/zip across separate columns with no composite). It is
  declared in the map per the ticket even though the SLA producer's `address` field currently
  reads raw `row.get(...)` chains — the same as Norfolk/Baltimore/DC/Montgomery, which all
  declare `address_street` without the producer consuming it. Native lat/lng means no ADR 0004
  geocode is needed. `address` on the event stays None for SD (consistent with existing SLA cities).
- **City sniff:** the SD row carries `dba_name` and `naics_description`, both of which would be
  captured by the SF branch, so a **San Diego branch is placed before the SF branch**, keyed on
  `account_key` AND a corroborating SD-only marker (`date_cert_effective` / `date_cert_expiration`
  / `naics_sector`). A row missing `account_key` cannot be the SD business-cert feed and falls
  through to SF. `run_stream` always passes an explicit `city_id`, so autodetect only governs
  manual/test paths.
- **`account_key` float-string normalization:** applied when `resolved_city == "san_diego"`,
  guarded by try/except so non-numeric/empty ids pass through untouched — only the SD branch is
  affected; other cities' `license_id` is unchanged.
- **CSVClient wired** into `sla_licenses_producer` (`self.csv = CSVClient()` + `"csv"` in
  `_client_for`), mirroring `complaints_311_producer` / `dob_permits_producer`. The producer is
  the only producer for `producer_key="sla"`; the scheduler already dispatches `csv` (line 365).
- **No dashboard / snapshot-export edits.** San Diego is already on the map (selector option +
  CITY_CONFIGS + static copy — wired under US-91 permits, confirmed by US-124). Adding a feed to
  an already-listed city does not change the dashboard or the snapshot export; `TestDashboardWiring`
  checks *city* presence, not per-feed, and San Diego is present. No `csv_client.py` change.

## Verification run

From `apps/api` (`.venv`), focused tests only (not interlock / not full suite — orchestrator runs
those at close-out):

- `test_producers_san_diego.py` → appends US-125 SLA tests (spec/platform/snapshot, lowercase
  field_map, row parse + account_key normalization, autodetect, SF-shadow regression, metro-bbox,
  CSVClient lowercase-snapshot path). Updated `test_san_diego_registration_scope_and_job_names`
  so SLA is now registered (`sla_sd`) and only DEEDS remains absent.
- `test_producers_la.py`, `test_producers_baltimore.py`, `test_producers_sf.py`, `test_field_maps.py`,
  `test_config.py`, `test_feedtype_taxonomy.py`, `test_registry_cadence.py` (SLA/registry/config
  regression) — see count in report.
- `ruff check` on touched Python files → zero net-new violations (pre-existing only).

## Discrepancy / open question

- **Backfill not live.** The sweep note said "backfill `sd_businesses_inactive_*`", but every
  inactive/active-year-scoped filename returns **HTTP 403** today (S3 AccessDenied). Only the
  active snapshot is published. This does not contradict the ticket (the ticket's endpoint is the
  active snapshot and the feed is snapshot-mode, full re-download each run) — recorded for accuracy.
- The plain `sd_businesses_active_datasd.csv` is unchanged/unextracted by `endpoint_by_year` since
  it is not year-scoped (a single live snapshot), so no D3 year-rollover entry is needed.
- `address_street` is declared but the SLA producer's `address` event field stays None — a
  pre-existing limitation shared by every SLA city that declares `address_street`; not in scope.
