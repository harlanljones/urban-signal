# Stream log — city-des-moines — 2026-09-29

Copy of `.streams/_TEMPLATE.md`, updated at every step boundary. If this
stream is interrupted, the next agent starts from "Current step" below.

## Claim

- **Stream id:** `city-des-moines`
- **Leaf files I created/edited:**
  - `docs/research/probe-des_moines.md` (Phase-0 probe; written in every outcome)
  - `.streams/city-des-moines.md` (this file)
  - `.streams/dispatch-log.md` (one entry appended)
  - `apps/api/src/spatial/cities/des_moines.py`
  - `apps/api/src/spatial/cities/data/des_moines.yaml`
  - `apps/api/tests/unit/test_producers_des_moines.py`
- **Spine files touched (one hold, same as the registry entry):**
  `apps/api/src/config.py` (one settings field per registered endpoint),
  `apps/api/src/spatial/city_registry.py` (`CityId.DES_MOINES`).
- **Shared module edited, not in the spine manifest:**
  `apps/api/src/producers/watermarks.py` (`maps.dsm.city` added to
  `ANSI_DATE_LITERAL_HOSTS`).
- **Generated surfaces:** `apps/dashboard/public/index.html`
  (`python3 scripts/export_dashboard.py`), `apps/product/public/facts.json` and
  `apps/product/public/cities/des_moines.json` (`bun run facts:export`), README.md
  and PRODUCT.md metro counts 156 -> 157.
- **Explicitly NOT touched:** `apps/api/src/spatial/cities/data/huntsville.yaml`
  and `docs/research/probe-huntsville.md` (the two intentional Huntsville edits,
  permits cadence 7 -> 21 days; committed as `7ccc900` while this stream ran),
  no other city's registration, `docs/signal-roadmap.md`,
  `docs/expansion-roadmap-wave-3.md`.

## Intent

Probe Des Moines, IA row-level across the four core families (permits, 311, sla,
deeds) plus any other family found, then register `des_moines` ONLY if at
least one feed is live (newest row inside its cadence, documented row-level) and
geocodable (Tier 1 native points / Tier 2 address-only via the geocoder) and
servable by an existing platform client. If nothing qualifies: write the probe
doc with a REJECT/DEFER verdict and re-probe triggers, leave the registry
untouched, and report back. No commits, no pushes, no PRs; everything stays in
the working tree.

## Decisions

Findings go here the moment they are learned (F5). All times UTC. Row-level
reads only; catalog `modified` dates ignored.

- 2026-09-29T03:17Z — Claimed stream. Baseline `pytest -m interlock` = 35 passed.
  Working tree started with the two intentional Huntsville edits only (committed as
  `7ccc900` at 03:03Z, while the stream ran).
- 2026-09-29 — `data.dsm.city` = ArcGIS Hub, AGOL org id `HT7H9QGiZQoRJDpJ`
  (name `desmoines`). DCAT (65 datasets) re-read: reference layers + 2023 police
  summary tables only. Full AGOL org item search (398 public items; services
  directory 82 services) re-read: no permits / 311 / licenses / deeds layers. Only
  transactional-looking layer: `PSDP_Crime_Layer_View` (DMPD crime, see below).
- 2026-09-29 — City systems fingerprinted from www.dsm.city links:
  permits + business licenses = Tyler EnerGov Self-Service
  (`css.dmgov.org/EnerGov_Prod/SelfService`, v2025.3.1.25, anonymous public
  search API, NO platform client in this repo); 311 = myDSMmobile / Tyler
  Portico + CitySourced (`cityofdesmoinesia.tylerportico.com`,
  `desmoinesia.citysourced.com`); police portal = Tyler Data & Insights
  ("LERM", `desmoinesia-pd.data.socrata.com`, eight dataset IDs tested, all
  403 auth-required).
- 2026-09-29 — Polk County ArcGIS Enterprise 11.5 found via
  `maps.polkcountyiowa.gov/portal/sharing/rest/portals/self` helperServices:
  REST root is `gis4.polkcountyiowa.gov/server/rest/services` (21 folders). Live deed
  signal: `Public/Polk_County_Parcels/FeatureServer/2` (`Parcel` table, 220,002 rows,
  one per parcel), `LastDeededDate` newest 2026-09-24 19:38Z (book 20669 page 522).
  Table has NO geometry and its key `ParcelNumber` does not match the point layer's
  `parcel_number` (the shared `parcel_join` requires one identical key name) - see
  probe doc.
- 2026-09-29 — data.iowa.gov is NO LONGER Socrata (Socrata catalog: "Domain not
  found"; `/resource/*.json` 404). It is the "Iowa Data Hub" (Next.js,
  BigQuery-backed, file download via a server action) - no row-level API, so no
  Iowa state license register is reachable at row level.
- 2026-09-29 — Polk/Akamai edge (`edgekey.net`) began answering "Access Denied"
  HTML partway through a burst of 82 windowed-count queries in about a minute
  (03:14Z). Backed off, no evasion attempted. One default-UA request at about 03:16Z
  (the 2,000-row deed page) then succeeded. The next six Polk requests (five at
  03:17Z, one at 03:30Z) carried a descriptive research User-Agent and all came back
  empty or refused (the 03:30Z reply is HTTP 403). Whether the block was rate- or
  User-Agent-based was not isolated. The first request at 04:18Z succeeded (HTTP 200)
  and every later Polk read was a single spaced request with the default curl
  User-Agent.
- 2026-09-29 — City ArcGIS Server found: `maps.dsm.city/p2/rest/services`
  (10.91, resolves straight to an address record). `External/EXTDynamicCodeCaseRentalLicense/MapServer`
  layer 0 "Code Case" (33,061 rows, native points, `DateOpened` newest 2026-09-25,
  weekday-continuous) and layer 1 "Rental License" (15,475 contact rows / 9,866
  licenses, native points, `IssuedDate` newest non-future 2026-09-25, 2 future-dated
  rows 2026-11-20 / 2026-12-05). Both truncate-reloaded 2026-09-27 06:00 CDT
  (`created_date` identical on every row; unchanged when re-read at 04:25Z and 07:48Z
  on 09-29, so the reload is not daily). Every other External layer probed: no
  permits/311 (RoadClosure 84 rows forward-dated to 2026-12-08, Street Use Events 51
  rows forward-dated, PoliceHomelessResponse 255 rows newest 2026-09-18, Crashes
  `crash_date` newest 2021-12-31 in a single 2023-07-28 load, BenchmarkingDSM last
  edit 2024-07-03 with `reportyear` max 2022, ProjectEcoDev 7 rows all 2015-03-30).
- 2026-09-29 — EnerGov anonymous search (`css.dmgov.org`) is live: newest
  permit PLMR-2026-002494 issued 2026-09-28T16:27:25; 351 permits in 7d, 1,363 in
  30d, 2,725 in 60d, 4,265 in 90d (bucketed locally from the newest 4,600 rows; the
  API ignores IssueDateFrom/To). Address-only (Tier 2 by data) but NO platform
  client exists (`KNOWN_PLATFORMS` has no energov) -> not registrable in this
  stream. Business/other licenses 232,707 (mostly animal / vacant-structure) - same
  blocker.
- 2026-09-29 — PSDP crime (`PSDP_Crime_Layer_View`, 122,243 rows, native
  anonymized points): newest `reported_date` 2026-08-31 (29 d); Jun/Jul/Aug each
  month-complete (2,797 / 2,812 / 2,725). AGOL item created 2026-07-08, not in the
  Hub catalog; no per-row load timestamp, so cadence unproven -> DEFER.
- 2026-09-29 — 311: CitySourced (`desmoinesia.citysourced.com`) is a
  browser app proxying `pages/ajax/callapiendpoint.ashx` (not exercised); Open311
  paths 404; Tyler Portico is an authenticated incident portal -> Tier 3.
- 2026-09-29 — PLATFORM DEFECT (pre-existing, not Des Moines): the scheduler
  calls `parse_socrata_row` for every job, but `ViolationsProducer` /
  `InspectionsProducer` (enforcement_signals_producer.py) only define `parse_row`;
  `ViolationEvent` also carries no watermark attribute the scheduler reads
  (`status_date` is not among them). Mock run of `poll_job` on `violations_boston`: 0
  produced, 1 DLQ route with "'ViolationsProducer' object has no attribute
  'parse_socrata_row'", watermark None. So registering Code Case as `violations`
  would only feed the DLQ -> NOT registered (spec kept in the probe doc). Code
  enforcement is also not 311 (Lynchburg, Scottsdale and Wichita precedents).
- 2026-09-29 — `maps.dsm.city` rejects ISO-string date literals in `where`
  (`IssuedDate > '2026-09-25T05:00:00'` -> 400 "Unable to complete operation")
  but accepts `date '2026-09-25'` (`>` returns 2, `>=` 19, `=` 17 for that day).
  Spine-adjacent delta: add the host to `ANSI_DATE_LITERAL_HOSTS`
  (src/producers/watermarks.py), as DC/Milwaukee/etc.
- 2026-09-29 — DECISION: register `des_moines` with ONE feed, `sla` = City
  Rental License layer (Tier 1, incremental on `IssuedDate`, cadence 7, filter
  `ContactType = 'Property Owner'`, `license_type` from `ContactType`, no contact
  columns mapped). No other family qualifies today (see probe doc). Geometry authored
  from the city's own neighborhood layer + Census TIGERweb places + Census geocoder
  anchors; only the `sla` seed is measured (742 licences 2026-07-01..09-29), the other
  four seeds are neutral.
- 2026-09-29 — Interlock initially failed
  `TestDashboardWiring::test_worker_static_copy_is_in_sync...` (stale `index.html`);
  fixed by `python3 scripts/export_dashboard.py`, not by weakening the test.
- 2026-09-29T07:54Z — Gates and G5, final (re-run after the last edit to this file):
  - `cd apps/api && python -m pytest -m interlock`: `35 passed, 4995 deselected`
  - `python -m pytest tests/unit/test_producers_des_moines.py`: `39 passed`
  - `python3 scripts/verify_cicd_preflight.py` (exit 0): interlock, dashboard <->
    product cross-ref, product facts:check, product lint, dashboard export and ruff
    check all `OK`; `CI/CD pre-flight green - all gates pass`.
  - `ruff check` on the changed and new Python files: `All checks passed!`
  - Privacy sweep of the new files: no email addresses, no phone numbers; contact
    columns in the test fixtures are `REDACTED`.
  - G5 (`scripts/backfill_probe.py --city des_moines --count`, newest 500 rows):
    500/500 parsed (1.0), 0 dropped, source_count 15,475; points 500/500, addresses
    500/500, in metro 500/500, division resolved 500/500 (probe shape and production
    shape both).
  - Map check: `des_moines` in `METRO_META` (chip + `?city=`), in `SUPPORTED_CITIES`,
    4 res-5 grid tiles in the built manifest, in `facts.json` and
    `cities/des_moines.json`.

## Follow-up claim: code cases as the `violations` feed (2026-09-29, same stream id)

Second hold on this stream, opened after the `poll_job` / `parse_socrata_row` fix
(PR #67) removed the only blocker recorded for Code Case. Work is on
`claude/project-thread-ojmh0q-dsm-code-cases`, stacked on PR #67.

- **Leaf files I will create/edit:**
  `apps/api/src/spatial/cities/data/des_moines.yaml` (`datasets.violations`),
  `apps/api/src/spatial/cities/des_moines.py` (docstring only),
  `apps/api/tests/unit/test_producers_des_moines.py`,
  `docs/research/probe-des_moines.md`, `.streams/city-des-moines.md` (this file),
  `.streams/dispatch-log.md` (the Des Moines row).
- **Spine files I expect to need (one hold, same as the yaml entry):**
  `apps/api/src/config.py` (one settings field for the new endpoint). No
  `city_registry.py`, `scheduler.py` or producer edit is expected: the `violations`
  producer key, topic and `FeedType.VIOLATIONS` already exist.
- **Generated surfaces to re-run:** `bun run facts:export` (apps/product) and
  `python3 scripts/export_dashboard.py`; both compare against the registry.
- **Explicitly NOT touched:** every other city, the scheduler and the two
  enforcement producers, `watermarks.py` (`maps.dsm.city` is already an ANSI host).

### Follow-up decisions and findings: code cases (2026-09-29, times UTC)

- 22:20-22:50Z — Live re-probe of layer 0 (`maps.dsm.city` ArcGIS Server 10.91,
  default curl User-Agent, 26 requests a few seconds apart, no WAF response; one of
  them, a two-field distinct count, was rejected by the server for its shape). Rows **33,061** (unchanged; `created_date` still the single reload
  stamp 2026-09-27 06:00 CDT, so no reload on Mon 09-28 or Tue 09-29). Newest
  non-future `DateOpened` **2026-09-25** (35 rows), **0** future-dated rows (max
  over all rows is 09-25). `>= date` windows: 7d (on/after 09-22) **190**, 30d
  (08-30) **795**, 60d (07-31) 1,843, 90d (06-30) 2,908; the 7d and 30d were also
  confirmed with server-side `returnCountOnly`. 275 distinct opened days since
  2025-09-01; 256 in the trailing 12 months (2025-09-29..2026-09-25); **longest gap
  between consecutive opened days = 5 days** (2025-11-26 to 12-01 and 2025-12-24 to
  12-29, both holiday weeks; the next longest are 4 days). Weekday-continuous:
  Mon-Fri only, apart from 6 Sunday-dated days (19 rows).
- `DateOpened > date '2026-09-18'` with `orderByFields=DateOpened DESC,OBJECTID DESC`
  works (5 newest rows returned in OBJECTID-descending order within the shared
  day). The ISO string `DateOpened > '2026-09-24T05:00:00'` returns JSON error 400
  "Unable to complete operation." (HTTP 200 body). `> date '2026-09-25'` 0,
  `>= date` 35, `= date` 35, so `date '...'` is local midnight, like the rental
  layer. `maps.dsm.city` was already an ANSI host.
- `CaseNumber` is unique (33,061 distinct = rows, none blank), `DateOpened` never
  null. All 33,061 rows have a point inside the registered metro bbox (envelope
  count), layer extent lng -93.7085..-93.5015, lat 41.5016..41.6526 (four city
  divisions only). `CaseType`: 9 category values; `Status`: 18 workflow values.
- **`Description` is NOT mapped**: free text, 14,568 distinct values on 33,061 rows
  (12,977 empty), with staff initials, names and complaint notes. `Remark` is
  empty on all rows today (0 non-empty) but is a free-text column; editor columns
  hold one service account (1 distinct value each). With no mapping the shared
  producer's lower-case fallbacks (`description`, `case_type`) find nothing on
  these capitalized columns, so the event `description` is None (verified on the
  newest 500). Fixtures replace `Remark`, `Description` (where non-empty) and both
  editor columns with `REDACTED`.
- **Cadence 7** (alarm 14 days): the data gap alone justifies 3-4, but the reload is
  not proven daily (same map service as the rental layer; one reload stamp, none on
  09-28 or 09-29), and a weekly reload plus a holiday gap puts the newest opened
  day up to about 10 days old; 3 would false-alarm. Same value and reason as `sla`.
- `ArcGISClient.paginate` takes no `select`/`outFields`, so `outFields=*` cannot be
  narrowed by the spec: the free-text and editor columns still travel in a raw
  row, and would be written to the DLQ payload if a row failed to parse (0 of the
  newest 500 do; every row has a point). Platform-wide, not a Des Moines
  decision; flagged in the probe doc.
- Data-quality: every `Address` is served with a trailing space (500 of 500 newest);
  `parse_row` does not strip, so `ViolationEvent.address` keeps it. Not fixed here
  (shared producer, spine-adjacent); pinned in the tests.
- `scripts/backfill_probe.py` has no `violations` entry in `PRODUCERS`, so it cannot
  run this job as shipped (it would raise "No producer registered for key
  'violations'"; Austin and Boston violations are affected the same way).
  Not edited here (outside the claimed files); G5 runs its own `probe_feed` with the
  producer supplied by monkeypatch, the way `test_backfill_probe.py` does.

- Registration edits (one hold, back to back, interlock run straight after): yaml
  `datasets.violations` (arcgis, `DateOpened`, ids `CaseNumber` then `OBJECTID`,
  `order_by DateOpened DESC, OBJECTID DESC`, interval 1800, cadence 7, no `where`,
  field map `violation_id`/`code`/`status`/`status_date`/`address`) and
  `config.py` `arcgis_des_moines_code_cases_url`. No scheduler, producer, registry
  or `watermarks.py` edit. `des_moines.py` docstring only.
- Tests (`test_producers_des_moines.py`, 39 -> 60): real rows redacted as above, spec
  and field-map assertions, parse into `ViolationEvent`, and a `poll_job` test for
  `violations_des_moines` (events under `des_moines:<CaseNumber>`, watermark
  `2026-09-25T05:00:00` from `DateOpened`, next `where_clause` is
  `DateOpened > date '2026-09-25'`). Mutation-checked: mapping `Description`, changing
  the watermark column, dropping the OBJECTID tiebreak and pointing `status_date` at
  `DateClosed` each make 2-5 of the new tests fail.
- G5 (`scripts/backfill_probe.py`'s own `probe_feed`, producer supplied in-process,
  transport replaced by curl-captured rows because the shipped `PRODUCERS` table has no
  `violations`): newest 500 rows **500 / 500 parsed (1.0), 0 dropped**, source count
  33,061, `watermark_seen` 2026-09-25T05:00:00+00:00; points 500/500, in metro bbox
  500/500, addresses 500/500, division resolved 500/500, `description` set 0/500.
  Production shape (spec `order_by`) identical. Floor 99% (native points).
- Live cross-check through the real scheduler (orchestrator, after the agent pass):
  `poll_job` on `violations_des_moines` with only Kafka mocked published 500 / 500
  newest rows, 0 DLQ, watermark `2026-09-25T05:00:00`; the next poll sent
  `DateOpened > date '2026-09-25'` with the registered ordering and returned 0 rows,
  SUCCESS.
- Staleness check on the replayed sample: threshold 14 days, newest watermark
  2026-09-25, age 4.74 days at 22:50Z, not stale; the alarm would trip at about
  2026-10-09 05:00Z (15.04 days at 2026-10-10 06:00Z) without a new reload.
- Derived artifacts: `bun run facts:export` -> `SITE_FACTS_OK (157 metros)`, and
  `python3 scripts/export_dashboard.py` rewrote `index.html`; both are byte-identical
  to HEAD because `facts.json` covers only the permits/311/sla/deeds families and the
  dashboard is built from the registry's metros. README and PRODUCT count metros
  (157, unchanged) and not feeds, so neither changed.
- Gates, final (times UTC, after the last code edit; docs and `.streams` are not gate
  inputs):
  - `cd apps/api && python -m pytest -m interlock -v`: `35 passed, 5022 deselected`
  - `python -m pytest tests/unit/test_producers_des_moines.py -v`: `60 passed`
  - `python -m pytest tests/unit/test_scheduler.py -v` (offline proxies): `25 passed`
  - `python -m pytest tests/unit/test_producers_enforcement_signals.py -v`: `11 passed`
  - `python3 scripts/verify_cicd_preflight.py` (exit 0): interlock gate, dashboard <->
    product cross-ref, product facts:check, product lint, dashboard export and ruff
    check all `OK`; `CI/CD pre-flight green - all gates pass`.
  - `ruff check` on `config.py`, `des_moines.py`, `test_producers_des_moines.py`:
    `All checks passed!` (baseline at HEAD also clean).
  - Also green, one process each: `test_registry_cadence`, `test_derived_registry`,
    `test_acquisition`, `test_backfill_probe`, `test_backfill_loader`,
    `test_feed_staleness_probe`, `test_feedtype_taxonomy`, `test_field_maps`,
    `test_watermarks`, `test_scheduler_watermark_state`, `test_export_snapshot`.
- Raw captures (newest-500 pages, group-by and Description dumps) were kept in the
  scratchpad only and deleted at the end; the fixtures in the test file are the only
  copy, redacted.

## Current step

Follow-up done on `claude/project-thread-ojmh0q-dsm-code-cases` (stacked on PR #67):
`des_moines` now registers two feeds, `sla` (PR #66) and `violations` (the Code Case
layer). Gates green (see the follow-up decisions). Nothing is parked
mid-edit: the yaml entry, the settings field and the tests landed together and the
interlock ran clean afterwards.

## Next step

Open follow-ups (none started): make
`scripts/backfill_probe.py` know the `violations` (and `inspections`) producers so G5
runs without a harness, an EnerGov platform client, a two-key `parcel_join`, and the
re-probe triggers in `docs/research/probe-des_moines.md` (code cases: re-read
`created_date` after the next Sunday to see whether the reload is daily).
