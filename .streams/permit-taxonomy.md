# Stream log — permit-taxonomy — 2026-10-02

## Claim

- **Stream id:** `permit-taxonomy`
- **Leaf files created/edited:**
  - `src/features/permit_taxonomy.py` (`names_new_building` and
    `is_trade_permit`; the code `NB` counts only as a whole word)
  - tests: `test_permit_taxonomy.py`, and the city tests that pinned the old
    classes (`test_tucson_permits.py`, `test_producers_inland_empire.py`) or
    now pin the new ones (`test_texarkana_permits.py`,
    `test_abilene_permits.py`)
  - this file and `.streams/dispatch-log.md`
- **Spine files touched:** `dob_permits_producer.py` (a trade's permit that
  the old rules read as a new building becomes `A2`; a permit they left at
  `OT` that names a new building becomes `NB`). `pytest -m interlock`
  passes.
- **Generated surfaces:** none. Product facts and the dashboard count feeds,
  not permit classes.

## Intent

Classify new homes as new construction and trade permits as trade permits
in every metro, from the type names the 98 readable permits feeds publish.

## Decisions

- 2026-10-02 — Survey before changing rules: the newest rows (up to 1,000)
  of every registered permits feed, read the way a first poll reads them,
  counting only values from type columns (free-text descriptions were
  counted in memory and deleted). 98 of 100 feeds answered (93,511 rows);
  Scottsdale's host is off-limits and Augusta's backfill-shaped read fails
  (a separate fix).
- 2026-10-02 — Require "new" within one word of a building word, in either
  order: farther apart it named other things, such as a canopy in a San Jose
  description that opened with a project name holding "HOME".
- 2026-10-02 — Change the job type code only where the old rules gave `NB`
  (to `A2`, for a trade's permit) or `OT` (to `NB`): a keyword such as
  "addition" or "repair" keeps the class it gave.
- 2026-10-02 — Leave use-type names without "new" alone ("Single Family
  Dwelling" in Baltimore, Bowling Green, Salem and Longview could be any work
  on a house), and leave a new ADU, mobile home or manufactured home where
  it was.
- 2026-10-02 — Leave columns that are not type names to the field-map audit:
  ten feeds' maps miss their type column (every row defaults to `A1`), and
  Norfolk's and Montgomery's `New` work class spans trade permits.

## Current step

Done.

## Next step

The field-map audit (per-field coverage for every permits feed).
