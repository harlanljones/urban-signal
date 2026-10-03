# Stream log — charlotte-permits — 2026-09-30

## Claim

- **Stream id:** `charlotte-permits`
- **Leaf files created/edited:**
  - corpus file `charlotte.yaml` (a `permits` spec); the module notes in
    `cities/charlotte.py`; the county host in `producers/watermarks.py`
  - tests: `test_charlotte_permits.py` (new), `test_producers_charlotte.py`
  - notes in `docs/research/two-family-depth-2026-09-30.md` (new), the
    Charlotte row of the README table, this file, `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the county's permits layer, and the
  Charlotte comment). `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/charlotte.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register what the research agents found for the twelve metros that lacked
permits and deeds, the next step `pierce-deeds` named. Of the permits probe's
twelve, only Charlotte's source registers as it stands.

## Decisions

- 2026-09-30 — Read Mecklenburg County's `BuildingPermits_Accela` layer, not
  `AccelaAllPermits` (which adds trade permits) or the legacy
  `BuildingPermits` layer (about 3% of recent permits, numbered apart).
- 2026-09-30 — One event per permit: key on `permit_number`, as the other
  permits feeds do, with a tie-free order so a permit spanning parcels stands
  at the same parcel on every read.
- 2026-09-30 — Filter out rows without an issue date: the server sorts them
  first under `issue_date DESC`.
- 2026-09-30 — Hold Overland Park's permits for Kansas City: one suburb in
  Kansas would stand for a metro whose other feeds are Kansas City,
  Missouri's.

## Current step

Done.

## Next step

Register what the deeds and `311` research agents find for the two-family
metros.
