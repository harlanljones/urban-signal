# Stream log — toledo-deeds — 2026-09-30

## Claim

- **Stream id:** `toledo-deeds`
- **Leaf files created/edited:**
  - corpus file `toledo.yaml` (a `deeds` spec); the module notes in
    `cities/toledo.py`
  - tests: `test_toledo_deeds.py` (new), `test_producers_toledo.py`,
    `test_deeds_party_names.py`, `test_snapshot_reach.py`
  - notes in `docs/research/two-family-depth-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the Auditor's sales layer).
  `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/toledo.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register the other deeds source the two-family deeds probe found, the next
step `charlotte-deeds` named, and record why the probe's other seven metros
stay without deeds.

## Decisions

- 2026-09-30 — Window on the recorded date (`RECORDDT`), not the transfer
  date, which runs a median of ten days earlier and would leave the newest
  weeks thin.
- 2026-09-30 — One event per sale and parcel, under the sale's number as the
  document id, so a sale's parcels share a Kafka key.
- 2026-09-30 — Keep the county-wide layer to the metro box with
  `metro_clip` (2,154 of 2,296 rows in the window), as Tacoma, Bend and
  Scottsdale do.
- 2026-09-30 — Hold Dayton's, Oakland's and Omaha's sources: each is
  refreshed a year or more apart (Omaha's inferred from a single load date)
  and its 90-day window was empty.

## Current step

Done.

## Next step

Register what the permits and `311` research agents found for the fifteen
two-family metros with `sla` and `deeds`, starting with Asheville's permits.
