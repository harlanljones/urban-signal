# Stream log — us129-pittsburgh-deeds — 2026-08-25

## Claim

- **Issue:** US-129 — Register Pittsburgh deeds feed (WPRDC Allegheny sales)
- **Serial? Parallel:** Parallel spine agent. Owns only the Pittsburgh DEEDS block;
  all edits are additive within the Pittsburgh section. Interlock is gated by the
  orchestrator at close-out (`pytest -m interlock`).
- **Files changed (working tree, uncommitted):**
  - `apps/api/src/config.py` (added `ckan_pittsburgh_deeds_endpoint`)
  - `apps/api/src/spatial/city_registry.py` (Pittsburgh DEEDS spec + comment)
  - `apps/api/src/producers/deeds_acris_producer.py` (CkanClient + Pittsburgh sniff)
  - `apps/api/tests/unit/test_producers_pittsburgh.py` (deeds field-map/ckan/null-coord tests)
  - `README.md` (Pittsburgh deeds cell)
  - `.streams/us129-pittsburgh-deeds.md` (this log)

## Live probe (verified, not trusted)

Probed the WPRDC CKAN datastore `ckan://data.wprdc.org/5bbe6c55-bce6-4edb-9d04-68edeb6bf7b1`
on 2026-08-25.

- `datastore_search` (limit=1) → high-water/freshness sample row; schema is
  **all-uppercase**: `_id, PARID, FULL_ADDRESS, PROPERTYHOUSENUM, PROPERTYFRACTION,
  PROPERTYADDRESSDIR, PROPERTYADDRESSSTREET, PROPERTYADDRESSSUF,
  PROPERTYADDRESSUNITDESC, PROPERTYUNITNO, PROPERTYCITY, PROPERTYSTATE, PROPERTYZIP,
  SCHOOLCODE, SCHOOLDESC, MUNICODE, MUNIDESC, RECORDDATE, SALEDATE, PRICE, DEEDBOOK,
  DEEDPAGE, SALECODE, SALEDESC, INSTRTYP, INSTRTYPDESC`.
- `datastore_search_sql` aggregate (quoted identifiers required — the SQL endpoint
  folds unquoted identifiers to lowercase):
  - `count(*)` = **501,120**; `max("SALEDATE")` = **2026-08-24**;
    `max("RECORDDATE")` = **2026-08-24**; `min("SALEDATE")` = 2012-01-01;
    `min("RECORDDATE")` = **0212-08-01** (bad 4-digit year row — data artifact).
  - Column presence: `PRICE` not-null = 498,025/501,120 (99.4%);
    `DEEDBOOK` not-null = 500,553; `FULL_ADDRESS` not-null = 501,120 (100%).
  - `SALECODE` distribution (top): `3`=103,219, `0`=98,239, `H`=66,764,
    `14`=44,613, `36`=40,182, `9`=30,657, ... confirms the non-arm's-length /
    multi-parcel caveat ("3" love-and-affection, "H" multi-parcel).
- Incremental-where shape: `SELECT * FROM "<resource>" WHERE "RECORDDATE" > '2026-08-20'
  ORDER BY "_id" LIMIT 2` → 200 + rows with original-case keys and `PRICE` null on a
  `SALECODE='N'` sample. Confirms CkanClient's range-filter SQL path works unmodified
  and the producer sees the correct (case-preserved) column names.
- **Freshness & cadence:** matches the ticket — count, max SALEDATE, max RECORDDATE,
  daily ETL. LIVE daily confirm.

## Decisions

- **`platform="ckan"`** — same CkanClient as the registered Pittsburgh permits; no
  client change needed. `DeedsACRISProducer` previously lacked `self.ckan` (the
  `_client_for`/interlock `test_platform_clients_exposed` would raise), so added
  `self.ckan = CkanClient()` (a leaf wiring, no behavior change for other cities).
- **`watermark_col="RECORDDATE"`** is a real column (unlike Cincinnati's synthesized
  SaleDate), so the feed stays **incremental** (no `ingestion_mode:"snapshot"`). The
  scheduler emits `RECORDDATE > '<hw>'`, CkanClient routes it to
  `datastore_search_sql` with the quoted identifier — verified live. `SALEDATE` trails
  by recording lag, so RECORDDATE is the ingest watermark.
- **`id_keys=["PARID","RECORDDATE","SALEDATE","DEEDBOOK","DEEDPAGE"]`** — the CKAN
  records preserve the original uppercase keys; `_extract_record_id` reads them
  verbatim. Multi-parcel sales share DEEDBOOK/DEEDPAGE, and one deed can bind several
  PARIDs, so the composite key is required (PARID alone is not unique across the
  feed). First key that is non-empty is the record id.
- **field_map is per ticket spec.** `doc_id` = PARID (then DEEDBOOK/DEEDPAGE as
  fallback), `bbl` = PARID, `document_amount` = PRICE, `recorded_date` = RECORDDATE,
  `doc_type` = INSTRTYP, `borough` = MUNIDESC/PROPERTYCITY, `incident_address` =
  FULL_ADDRESS. `incident_address` is inert for the deeds parser (DeedEvent has no
  address field) but is declared for metadata/downstream consistency.
- **No `where` / SALECODE filter.** The ticket spec declares none and the sweep
  recommends one only as a value-quality caveat. Registering the feed raw (like Cook
  County, which does not filter) keeps the stream complete; PRICE stays as-is
  (0/1/null tolerated, amount chain falls through to 0.0). Chose not to diverge from
  the ticket's exact `extra` — filtering would be a scope decision, not a registration
  decision, and would silently drop valid rows.
- **No geocoding / null-lat-lng tolerance.** The feed is address-only / PARID-only
  (verified: no coordinate columns). The deeds producer tolerates null lat/lng and
  emits null H3 (Cook County `wvhk-k5uv` precedent) — tested.
- **No dashboard wiring needed.** Pittsburgh was already a registered city on the map
  (selector option + CITY_CONFIGS + `apps/dashboard/public/index.html` copy), so a new
  *feed* for an already-listed city does not change the map. `TestDashboardWiring` /
  `TestSnapshotWiring` pass unchanged.
- **`expected_cadence_days: 7`** — daily feed, G11 declaration.

## Verification run

From `apps/api` (`.venv`, executed by this agent):

- Focused Pittsburgh feed + deeds-producer regression:
  `test_producers_pittsburgh.py`, `test_producers_cincinnati.py`, `test_field_maps.py`,
  `test_producers_chicago.py`, `test_producers_sf.py`, `test_producers_denver.py`,
  `test_producers_seattle.py`, `test_producers_columbus.py` → **passed** (counts in the
  report back; orchestrator re-runs the full interlock gate at close-out).
- `ruff check` on each touched file → no net-new findings.

## Discrepancy / open question

- **`min(RECORDDATE)` = 0212-08-01** — a corrupt 4-digit-year row (year 0212) in the
  earliest record. Non-blocking: it sorts far below any real date, so it never becomes
  the high watermark; flagging as a source-data quality artifact.
- **Ticket README wording drift.** The ticket said the current cell reads
  "— county sales address-only"; the shared working tree already had it as
  "— CKAN (WPRDC sales, price-bearing; pending US-129)". Settled on the ticket's
  requested cell: **"CKAN (WPRDC Allegheny sales; address-only)"**.
- **`PRICE` null/0/1.** 99.4% of rows carry a price; the remaining rows (non-market,
  `SALECODE='N'` etc.) parse with `document_amount=0.0`. Accepted (Cook County
  precedent), documented in the registry scope.
- **No `where` SALECODE filter** (see decisions). If a non-arm's-length exclusion is
  wanted later it belongs in a follow-up ticket, not this registration.
