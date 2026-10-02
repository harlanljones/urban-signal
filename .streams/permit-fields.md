# Stream log — permit-fields — 2026-10-02

## Claim

- **Stream id:** `permit-fields`
- **Leaf files created/edited:**
  - corpus: `augusta.yaml`, `boise.yaml`, `chattanooga.yaml`,
    `evansville.yaml`, `hartford.yaml`, `laredo.yaml`, `louisville.yaml`,
    `nashville.yaml`, `philadelphia.yaml`, `topeka.yaml`,
    `virginia_beach.yaml` (each permits spec maps the columns its source
    publishes, names the columns it reads, and drops records that are not
    building permits)
  - city modules that keep a copy of those maps: `laredo.py` (the address
    composer replaces the unused key normaliser), `topeka.py`,
    `virginia_beach.py`, `boise.py`
  - `src/producers/field_maps.py` (a dotted key names a column of that name
    when the row has one)
  - `src/producers/ckan_client.py` (a filter the simple grammar does not
    cover keeps its SQL and gets its simple terms' columns quoted; the AND
    split respects quotes and parentheses; `select` names the columns)
  - `src/producers/acquisition.py` (CKAN takes `select`)
  - tests: `test_ckan_client.py`, `test_field_maps.py`,
    `test_producers_laredo.py`, `test_producers_chattanooga.py`,
    `test_producers_hartford.py`, `test_producers_nashville.py`,
    `test_producers_virginia_beach.py`, `test_topeka_311.py`,
    `test_producers_augusta.py`
  - this file and `.streams/dispatch-log.md`
- **Spine files touched:** `dob_permits_producer.py` (`_parse_datetime`
  reads Chattanooga's `2026-10-01 00:00:00 UTC` and Virginia Beach's
  `2026/08/21`). `pytest -m interlock` passes.
- **Generated surfaces:** none. Product facts and the dashboard count feeds,
  not the columns a feed maps.

## Intent

Make every permits feed fill the event fields its source can fill: the
issue and application dates, the work class, the status, the valuation and
the site address. The taxonomy stream found ten feeds whose maps missed
their type column; the audit measured every field of every permits feed.

## Decisions

- 2026-10-02 — Measure first: two live polls of every permits feed through
  `poll_job`, counting per field how many events the producer fills (no
  values printed), then the source's own columns from a sample of its
  newest rows. Eleven feeds mapped names their sources do not use.
- 2026-10-02 — Name each feed's columns (`select`) and leave out the people
  and free text the audit found: contractors and their addresses and
  phones, owners, assignees, clerks, applicants, contacts and descriptions.
- 2026-10-02 — Filter out records that are not building permits where the
  source mixes them in: Laredo's garage-sale, food-truck, fire-inspection,
  right-of-way and internal records; Chattanooga's street cuts and meter
  changes; Hartford's fee records and amendments.
- 2026-10-02 — Laredo: key on APP YR, APP NBR, PERMIT SEQUENCE and PERMIT
  TYPE together. A house and its trade permits share the application
  number, so keyed by it alone 571 of 1,000 rows dropped as duplicates.
  The CKAN row id stays the event's permit id, as it was.
- 2026-10-02 — Topeka: the layer renamed its columns and keeps its dates as
  text (`9/4/2026`), so the poll names the days since its watermark, and
  pages newest object first. A permit spanning several parcels has a row per
  parcel; the permit number keeps one.
- 2026-10-02 — Map one type column per feed, the one that names the trade
  where the source has one, and leave joining two columns to its own change.
  Three feeds split a new house across two columns: Chattanooga's
  "Residential Building Permit" class with its "New Construction" type (75
  of its newest 1,000 rows), Philadelphia's "Residential Building Permit"
  with its "New Construction" work type, and Laredo's "Residential" group
  with its "New Construction" tab. Their trade and demolition permits
  now read right; their new houses still read as minor work.
- 2026-10-02 — Augusta's permits layer is a table without an object id
  (its metadata names none), so its spec names the permit number as the
  column that keys its rows. Boise's map drops `X`, `Y` and an `id` key its
  layer does not have; its points come from the geometry.
- 2026-10-02 — Verify with the same two live polls: every audited feed
  published, and the share of events missing each mapped field fell to what
  the source leaves empty (Boise's records without an issue date, Hartford's
  older records without a ZIP, Topeka's without an address).

## Current step

Done.

## Next step

Permit types from two columns (Chattanooga, Philadelphia, Laredo), so a new
house reads as new construction. El Paso, Gainesville and Melbourne: their
permits sources stopped (2021, 2023, 2022).
