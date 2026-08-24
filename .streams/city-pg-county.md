# Stream log — city-pg-county — 2026-08-24

## Claim

- **Stream id:** `city-pg-county` (Linear HJ-125, claimed via --assignee self)
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/prince_georges.py`,
  `apps/api/tests/unit/test_producers_prince_georges.py`
- **Spine files I expect to need:** `config.py`, `city_registry.py`,
  `cities/__init__.py`, `serving/dashboard.py`, synced
  `apps/dashboard/public/index.html`, plus a one-line `%Y%m%d` format
  addition to the duplicated `_parse_datetime` helpers in
  `complaints_311_producer.py` / `deeds_acris_producer.py`

## Intent

Register Prince George's County MD per HJ-125 (wave-2 §5 C8): 311 firm feed
(`2ywx-ipcd`, watermark `date_request_opened`, G11 exception cadence 30) plus
the conditional DEEDS-class parcel table (`qzrv-2tnv`) in D4 snapshot mode.
Dashboard wiring lands in the same spine hold per AGENTS.md city rule.

## Decisions

- 2026-08-24 — Feed 2 registers as snapshot (`watermark_col=""`,
  `ingestion_mode="snapshot"`, id-diff on account/objectid): one row per
  tax-account parcel, not a transaction stream; assessment mutations keep
  `transfer_date` unchanged, so an incremental filter would miss them. D7's
  sentinel machinery stays unused for now — it protects the probe and any
  future incremental promotion.
- 2026-08-24 — Parcel geometry is MultiPolygon with no centroid columns;
  following the DC deeds precedent the spec documents `non_spatial: True`
  instead of silently emitting null-H3 events or dropping the feed.
- 2026-08-24 — `_parse_datetime` lacks `%Y%m%d`: live parcel rows carry
  `transfer_date="20210505"` and would silently fall back to `now()` as the
  recorded date. One-line format addition in both duplicated producers.

## Current step

Spine edits.

## Next step

Gates + live parse-rate evidence, logs, resolve HJ-125.

## Outcome (2026-08-24)

Completed — 311 registered; parcel table DEFERRED with pinned findings.

**Registered:** FeedType.COMPLAINTS_311, socrata 2ywx-ipcd,
watermark date_request_opened, cadence 30 (G11 exception), 4-entry field_map
(service_request/request_name/date_request_opened/request_status). City
module prince_georges.py (1 division PRINCE_GEORGES_CORE, 4 submarkets),
CityId.PRINCE_GEORGES + 6 aliases, job_suffix pgmd. Dashboard wired in the
same hold: selector option, CITY_CONFIGS entry, cityCoordinates, autodetect
map, index.html resynced from get_dashboard_html(). _parse_datetime gained
%Y%m%d in both producers (parcel transfer_date "20210505" no longer silently
becomes now()).

**D9 finding (parcel table qzrv-2tnv does NOT clear snapshot parity):**
DeedsACRISProducer.parse_socrata_row extracts coordinates only from POINT
geometries; the table's MultiPolygon parcel shapes crash the extraction
("list index out of range") → every row parses to None (verified live).
Second blocker: the doc_id chain has no `account` fallback, so without a
registration-time field_map even geomless rows cannot form ids. Both pinned
as documentation tests in test_producers_prince_georges.py. Registering
anyway would page G5 forever — declined per ticket ("register 311 alone").
Path to promotion documented in the registry comment: harden geometry
(centroid/ring-walk), register in D4 snapshot mode with field_map
doc_id=account, document_amount=sales_price, recorded_date=transfer_date.

**Gates:** interlock 20 passed (incl. TestDashboardWiring three-layer check);
full suite 587 passed / 3 skipped / 0 failed (+8 tests); ruff clean on new
files, pre-existing spine debt unchanged (verified vs HEAD worktree).
**Live evidence:** parse rate 25/25 newest rows; division resolves
PRINCE_GEORGES_CORE; newest row 2026-07-17 matches ticket survey.
