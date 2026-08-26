# Stream log — us132-pittsburgh-311 — 2026-08-25

## Claim

- **Issue:** US-132 — Register Pittsburgh 311 feed (WPRDC new dataset)
- **Parallel leaf stream.** Additive-only; I own the Pittsburgh 311 registration and did not touch other cities' blocks. The orchestrator holds the interlock; I did **not** run `pytest -m interlock` or the full suite.
- **Files changed (working tree, uncommitted):**
  - `apps/api/src/config.py`
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/tests/unit/test_producers_pittsburgh.py`
  - `README.md` (Pittsburgh 311 coverage cell)
  - `.streams/us132-pittsburgh-311.md` (this log)

## Live probe (verified, not trusted)

Probed on 2026-08-25 with HTTP GETs against `https://data.wprdc.org/api/3/action` (CKAN datastore).

- **Package** `pittsburgh-311-data` ("Pittsburgh 311 Data"), metadata_modified today (2026-08-25T18:15Z). Resource "311 Data" `5202679a-d243-402e-b82a-63189995a942` is `datastore_active: True` — a streaming datastore, not a file dump.
- **Schema confirmed (datastore_search, limit=1):** keys are lowercase, original-case — `unique_id`, `case_number`, `subject`, `subject_code`, `created_date_utc`, `closed_date_utc`, `status`, `latitude`, `longitude`, `geo_accuracy`, `neighborhood`, `council_district`, `ward`, `street`, `street_id`, `city`, `origin`, `case_owner`, `last_modified_date_utc`. Matches the sweep-doc §9 schema.
- **Watermark format:** `created_date_utc` is ISO without tz suffix (e.g. `2026-08-25T17:47:36`); `_parse_datetime` absorbs it via `fromisoformat`.
- **lat/lng are TEXT, not floats:** newest sample `latitude='40.44714'` (5-dec, `geo_accuracy=EXACT`), `'40.44'` (2-dec, `geo_accuracy=APPROXIMATE`) — exact/approximate split confirmed. `float()` cast is required and works on both.
- **Geocode share (newest-500 by `created_date_utc DESC`):** 963,380 total rows; newest 500 → 499 carry lat+lng (**99.8%**), all 500 non-null `geo_accuracy` (307 EXACT / 193 APPROXIMATE). Legacy (2015–2025) rows carry null lat/lng — confirmed the first `_id=1` row (2016) is `latitude=None`.
- **Freshness:** newest `created_date_utc` = `2026-08-25T17:47:36` (today, intraday); `last_modified_date_utc` newest = `2026-08-25T17:47:38` (today).
- **Old archive is obsolete:** `311-data` ("311 Data Archive") is a separate package whose "311 Data" resource `29462525-…` newest `create_date_utc` = **2025-03-10** (stale; the old archive schema uses `create_date_utc`/`request_type_name`, not `created_date_utc`/`subject`). The README's "address-only archive" verdict traces to this dead archive — obsolete.

## Decisions

- **`config.py`:** add `ckan_pittsburgh_311_endpoint = "ckan://data.wprdc.org/5202679a-d243-402e-b82a-63189995a942"`.
- **`city_registry.py` `PITTSBURGH.datasets[FeedType.COMPLAINTS_311]`:** `platform="ckan"`, `watermark_col="created_date_utc"`, `id_keys=["unique_id","case_number"]`, `producer_key="311"`, `interval_seconds=180.0`, `topic=settings.topic_311`, `extra={"expected_cadence_days":7, "scope":"City of Pittsburgh 311 (WPRDC Pittsburgh 311 Data; native lat/lng)", "field_map":{...}}`.
- **`field_map` keys are the 311 producer's canonical keys:** `incident_id`→`["unique_id","case_number"]`; `latitude`→`["latitude"]`; `longitude`→`["longitude"]`; `created_date`→`["created_date_utc"]`; `closed_date`→`["closed_date_utc"]`; `complaint_type`→`["subject"]`; `incident_address`→`["street"]`; `borough`→`["neighborhood","council_district","ward"]`. No `status`/`zipcode` entry — `status` is a bare chain fallback on the schema's own `status` column; Pittsburgh has no `zipcode` column.
- **No `needs_geocode` / `where` filter.** lat/lng are native and ~99.8% present in the newest window; legacy null-coord rows are dropped by the producer's hard drop (the exact behavior Boston/NYC lat-lng feeds already use). Not an address-only feed — no ADR 0004 path.
- **No `complaints_311_producer.py` change.** CKAN is already wired (`self.ckan` + `"ckan"` in `_client_for`), the field-map keys are generic, and the lat/lng text→`float()` cast is already in the parser (`float(lat_raw)` / `float(lng_raw)`). The `csv`/CSVClient wiring from US-124 is untouched.
- **No dashboard / snapshot wiring.** Pittsburgh is already on the map (selector option + CITY_CONFIGS + static copy — wired for its existing permits/deeds feeds). Adding a feed to an already-listed city does not change the dashboard; `TestDashboardWiring` iterates over *cities*, not per-feed, and passes unchanged.

## Verification run

From `apps/api` (`.venv`), focused tests only (not interlock / not full suite — orchestrator runs those at close-out):

- `test_producers_pittsburgh.py` → **passed** (all).
- `.venv/bin/ruff check` on each touched Python file → **zero net-new violations**.

## Discrepancy / open question

- Minor, non-blocking date deltas vs the ticket: the new resource "311 Data" was created 2026-03-04 (package created 2025-12-19 — ticket said 2025-12-19), and the old archive's "311 Data" newest `create_date_utc` is 2025-03-10, not the ticket's 2025-02-04. Both are stale-vs-live facts that change nothing: the NEW dataset is datastore-active and intraday-current, the archive is a separate, deeply stale package.
- The newest window is 99.8% geocoded, not a clean 100% — the single newest-500 row with null lat/lng is dropped by the producer's hard drop (expected; matches the "~100%" wording).
- The 311 `created_date_utc` is a naive-local ISO string (no tz suffix), same as the existing Boston 311 `open_dt` pattern — `_parse_datetime` yields a naive `created_date`; not a regression and not changed here.
