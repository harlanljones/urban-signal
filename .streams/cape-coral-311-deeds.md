# Stream log — cape-coral-311-deeds — 2026-10-02

## Claim

- **Stream id:** `cape-coral-311-deeds`
- **Leaf files created/edited:**
  - corpus file `cape_coral.yaml` (a `311` and a `deeds` spec);
    `cities/cape_coral.py` (the module notes)
  - tests: `test_cape_coral_311.py` and `test_cape_coral_deeds.py` (new);
    `test_snapshot_reach.py` (the deeds window)
  - notes in `docs/research/two-family-depth-2026-09-30.md` and
    `snapshot-reach-2026-09-30.md`, this file, `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the request table and the parcel
  layer). `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/cape_coral.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register what the Florida group's probe verified for Cape Coral, which has
permits and SNAP retailers and lacks requests and deeds.

## Decisions

- 2026-10-02 — Read the City's `311 Issues NonSpatial` table, not the
  `311Issues` point layer the Hub item names: both carry the same overnight
  cut, and only the point layer holds the requester's name.
- 2026-10-02 — Set the request table's cadence to two days: it is loaded in
  one overnight cut, and the 2026-10-02 cut had not landed by 09:05Z, so a
  one-day cadence would alarm on a late load.
- 2026-10-02 — Read Lee County's sales as a 90-day snapshot with a 17,000-row
  cap rather than a watermark: sales arrive two to three weeks after their
  date, and March to May 2026 held 11,253.

## Current step

Done.

## Next step

Register the other Florida deeds (Gainesville, Lakeland, Ocala, Tampa) and
repair Ocala's and Orlando's permits.
