# Stream log — worcester-311 — 2026-10-02

## Claim

- **Stream id:** `worcester-311`
- **Leaf files created/edited:**
  - corpus file `worcester.yaml` (a `311` spec) and `cities/worcester.py`
    (the notes)
  - `scripts/backfill_loader.py` (a backfill places rows from State Plane
    columns, as the poll does)
  - tests: `test_worcester_311.py` and `test_scheduler_state_plane.py`
    (new); `test_backfill_loader.py`, and the docstrings of
    `test_producers_aurora.py`
  - notes in `docs/research/two-family-depth-2026-09-30.md` and
    `one-family-depth-2026-10-02.md`, this file and
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the source) and `scheduler.py` (a
  spec's declared State Plane columns place each unplaced row before a
  parcel join or the clip). `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/worcester.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register Worcester's work orders, which the two-family pass held because
the `311` producer could not convert their State Plane coordinates.

## Decisions

- 2026-10-02 — Convert in the scheduler, from the spec's existing
  `state_plane_*` fields, rather than in the `311` producer as the licence
  producer does for Boston: the conversion places a row, as a parcel join
  does, and every producer and the backfills then read the same point. The
  step needs the CRS and both columns, so Stockton's and Boulder's licences,
  which name only a CRS, are untouched.
- 2026-10-02 — Convert only a row the client left unplaced. Aurora's
  permits and licences and Tempe's crime reports declare their columns
  beside their geometry; none of each feed's newest 1,000 rows lacked
  geometry, and Boston's licences land where the licence producer put them.
- 2026-10-02 — Leave out the utility mark-out requests (1,502 of the 15,926
  in 90 days), as Augusta's spec leaves out its utility-locate tickets: they
  are contractors' notices ahead of an excavation, not residents' requests.
  Keep the task forces' and inspectors' requests, which report conditions.
- 2026-10-02 — Read incrementally on the date-only `Date_Logged`, newest
  first, with a cap of 10,000: the table is updated weekly, and the busiest
  16 days of the year logged 6,660 requests besides mark-outs, so a missed
  update still fits. `expected_cadence_days` 7.
- 2026-10-02 — Do not clip: the table holds the City's own requests, and
  the 907 of the first poll's 10,000 past the metro box lie at the city's
  north, east and south edges. Widening the box would change its grid tiles
  and is left for its own change.

## Current step

Done.

## Next step

None for this feed.
