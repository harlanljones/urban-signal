# Stream log — feed-repairs — 2026-09-30

## Claim

- **Stream id:** `feed-repairs`
- **Leaf files created/edited:**
  - `docs/research/feed-health-2026-09-30.md` (new),
    `docs/research/snapshot-reach-2026-09-30.md` (known gaps point at it)
  - dataset blocks in `augusta`, `boise`, `boston`, `bridgeport`,
    `cape_coral`, `cincinnati`, `cleveland`, `dayton`, `fort_worth`,
    `hartford`, `henderson`, `lakeland`, `las_vegas`, `lexington`,
    `louisville`, `madison`, `milwaukee`, `new_haven`, `peoria`,
    `san_francisco`, `seattle`, `spokane` and `tampa` `.yaml`
  - leaf mirrors, composers and docstrings: `bridgeport.py`, `cape_coral.py`,
    `fort_worth.py`, `henderson.py`, `lakeland.py`, `lexington.py`,
    `madison.py`, `new_haven.py`; `src/producers/ct_liquor_specs.py` (new);
    `src/producers/state_license_specs.py` (docstring)
  - clients and producers outside the spine: `arcgis_client.py` (refuses a
    service-root page), `csv_client.py` (`newline=""`), `watermarks.py` (four
    date-literal hosts), `street_cut_permits_producer.py`
  - tests: `test_arcgis_client.py` and `test_ct_liquor_permits.py` (new), and
    the leaf, CSV, scheduler, SNAP, snapshot-reach and enforcement suites that
    pinned the old values
  - `.env.example` (San Francisco endpoints), product facts (`facts:export`),
    this file, `.streams/dispatch-log.md`
- **Spine files touched (one hold):** `apps/api/src/config.py` (endpoint
  defaults; Madison's Accela and Seattle's WA LCB fields removed),
  `apps/api/src/producers/scheduler.py`
  (routes `accela` and `excel`), `apps/api/src/producers/dob_permits_producer.py`
  (leaf address composers, count coercion).
- **Generated surfaces:** `apps/product/public/facts.json` and the
  `cities/*.json` of the cities whose feed facts changed.

## Intent

A one-poll check of all 367 jobs found 36 that fail outright, 8 that fetch
nothing and 16 that fetch rows but publish none. Repair what a spec, endpoint
or small client fix can reach, retract what has no public source, and list the
rest with the reason.

## Decisions

- 2026-09-30 — Repair in place where a verified replacement exists; every
  repair was re-polled live through `poll_job` before it landed.
- 2026-09-30 — Madison `permits` is retracted: no public, anonymous source of
  City of Madison building permits exists. Madison gets the SNAP `sla`
  fallback instead.
- 2026-09-30 — Connecticut `sla` reads liquor permits only
  (`ct_liquor_specs.py`); the state table holds every credential, and the old
  feeds published individuals' names as premises.
- 2026-09-30 — Lexington and Seattle `sla` move to the SNAP retailer slice:
  Lexington's ABC layer holds Jefferson County only, and Seattle's WA LCB
  letters log is statewide and empty. A current state licence table for either
  city should replace SNAP.
- 2026-09-30 — Boston's CKAN timestamps are text, so its three feeds declare
  text watermarks in the column's own format (ADR 0005) rather than ISO.
- 2026-09-30 — `ArcGISClient` raises on a page with no `features` key: five
  feeds registered at a service root had reported SUCCESS with zero rows.
- 2026-09-30 — Tulsa `311` stays registered: the city's case system has opened
  no case since 2026-08-27, so its 30-day view is empty.
- 2026-09-30 — Bend `crime` stays failing: the public replacement lists exact
  offense addresses where the old feed gave block ranges.
- 2026-09-30 — Lincoln and Sioux Falls `permits` stay registered: both are
  city-side outages with no replacement.
- 2026-09-30 — Scheduler semantics (watermark source, composite ids, parcel
  joins in `poll_job`, a batch hook for context observations) are the next
  change, not this one.

## Current step

Done.

## Next step

The scheduler change listed under "Found along the way" in the feed-health
note, then Phoenix deeds (streaming zip), Boston deeds and the Florida
cadastral feeds.
