# Stream log — us126-cincinnati-deeds — 2026-08-25

## Claim

- **Issue:** US-126 — Register Cincinnati deeds feed (Hamilton County CSV)
- **Serial stream.** No other agent is editing spine files — interlock is held this whole hold.
- **Files changed (working tree, uncommitted):**
  - `apps/api/src/config.py`
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/producers/csv_client.py` (leaf — parenthesis-tolerant where)
  - `apps/api/src/producers/deeds_acris_producer.py`
  - `apps/api/tests/unit/test_producers_cincinnati.py`
  - `README.md`
  - `docs/expansion-roadmap.md`
  - `.streams/us126-cincinnati-deeds.md` (this log)

## Live probe (verified, not trusted)

Probed `https://www.hamiltoncountyauditor.org/download/transfer_dailysales_new.csv` on 2026-08-25 with curl.

- HTTP 200; `Content-Type: application/octet-stream`; `Last-Modified: Tue, 25 Aug 2026 10:47:51 GMT`; 174,614 bytes; 768 rows.
- **25 columns** (lowercased by `CSVClient`): `book, plat, parcel, parcelid, taxdistrict, ownername1, ownername2, land100, impr100, propertyclass, house#, streetname, streetsuffix, locationzipcode, monthsale, daysale, yearsale, numberpropertiesinsale, saleamount, valid, conveyancenumber, deedtype, appraisalarea, previousowner, propertynumber`.
- **Freshness:** composed `SaleDate` range = 2026-08-03 → 2026-08-17 (all August 2026). LIVE daily confirm.
- **`Valid` flag:** `Y`=705, `N`=63 → the `Valid='Y'` arms-length filter is correct (705 of 768).
- **`DeedType`:** WD 628, FD 51, LW 33, SV 21, QC 10, TD 8 (non-arms-length types present → filtered out with `Valid`).
- **Schema confirmed matches the sweep doc §3.** `OwnerName1/2` = grantee, `PreviousOwner` = grantor, `SaleAmount` = price, `ConveyanceNumber` = deed ref (shared across parcels), `PropertyNumber` = parcel, `AppraisalArea` = neighborhood, no single sale-date column (SaleDate must be synthesized from `MonthSale`/`DaySale`/`YearSale`).

## Decisions

- **`watermark_col="SaleDate"` is synthesized** (3 int cols, no single date column). The generic `CSVClient._row_matches` incremental where (`SaleDate > '<hw>'`) cannot filter a column that does not exist, so the feed is registered **`ingestion_mode="snapshot"`** — the bounded current-month file is re-pulled each poll and deduped on `ConveyanceNumber+PropertyNumber` (established snapshot pattern: KC SLA, MD SDAT deeds). Without snapshot, run #2 would silently drop every row (the where clause would resolve to NULL). High watermark is still tracked from `event.recorded_date` (informational).
- **`id_keys=["conveyancenumber","propertynumber"]`** — lowercase, because `CSVClient` lowercases headers (`_extract_record_id` reads them verbatim). Multi-parcel sales share `ConveyanceNumber`, so `PropertyNumber` disambiguates.
- **`where: "valid = 'Y'"`** filters non-arms-length rows as a registry/scheduler concern (never a silent parser drop — Denver $0-transfer precedent). `CSVClient._row_matches` previously rejected the scheduler's parenthesized base_where `"(valid = 'Y')"`, so I made it strip one layer of wrapping parens (leaf change).
- **`field_map` columns are lowercase** (CSVClient lowercases headers).
- **`needs_geocode: True` + `geocode_context: "Hamilton County, OH"` are declared but inert** — the deeds producer has no geocode hook site and a Denver test pins zero geocode calls; the producer tolerates null lat/lng (address-only). Geocoding is deferred to ADR 0004.
- **No dashboard wiring needed.** Cincinnati was already on the map (selector option + CITY_CONFIGS + static copy); adding a feed to an already-listed city does not change the dashboard. `TestDashboardWiring` / `TestSnapshotWiring` pass unchanged.

## Verification run

From `apps/api` (`.venv`):

- `pytest -m interlock` → **21 passed** (the interlock gate; all spine invariants green, incl. dashboard + snapshot wiring).
- Focused feed + deeds-producer regression:
  `test_producers_cincinnati.py` (13 passed), `test_producers_denver.py`, `test_producers_chicago.py`, `test_producers_sf.py`, `test_producers_seattle.py`, `test_field_maps.py`, `test_producers_san_diego.py` → **115 passed**.
- Registration-sensitive: `test_scheduler.py`, `test_scheduler_stagger.py`, `test_scheduler_watermark_state.py`, `test_feed_staleness_probe.py`, `test_rollover_drill.py`, `test_registry_cadence.py`, `test_export_snapshot.py`, `test_kafka_partition_wiring.py`, `test_feedtype_taxonomy.py`, `test_geocoder.py` → **86 passed**.
- `ruff check` on touched Python files → **zero net-new violations** (pre-existing repo violations unchanged: config 0, city_registry 29, csv_client 18, deeds 22, cincinnati test 0).
- End-to-end offline: `CSVClient` → `parse_socrata_row` over the real probe file → 705 `Valid='Y'` rows, parsed to DeedEvents with correct doc_id/bbl/amount/parties/type/SaleDate/AppraisalArea, null lat/lng, distinct `doc_id`+`bbl` for multi-parcel sales. Job name = `deeds_cinci`.

## Discrepancy / open question

- None blocking. The live probe matched the sweep-doc schema exactly (25 cols). The only deviation from the sweep sketch: added `ingestion_mode="snapshot"` (required because `SaleDate` is synthesized and cannot drive a column-level incremental where) and `where="valid = 'Y'"` (required to drop non-arms-length rows), neither of which the sweep sketch listed but both of which its caveats implied.
- Noted: the current-month CSV is a rolling window — as the month rolls, the snapshot re-pull naturally picks up the new month's file. The annual/YTD/prior-month companion files are not registered (out of scope for this ticket).
