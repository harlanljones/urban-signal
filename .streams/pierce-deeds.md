# Stream log — pierce-deeds — 2026-09-30

## Claim

- **Stream id:** `pierce-deeds`
- **Leaf files created/edited:**
  - corpus file `pierce.yaml` (a `deeds` spec); the module notes in
    `cities/pierce.py`
  - tests: `test_pierce_deeds.py` (new), `test_producers_pierce.py`,
    `test_snapshot_reach.py`, `test_deeds_party_names.py`
  - notes added to `docs/research/deeds-probe-2026-09-30.md` and
    `snapshot-reach-2026-09-30.md`, a "Not now" row for Pierce County's 311
    in `four-family-depth-2026-09-30.md`, this file, `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the descriptions of the sales file and
  the parcel layer now name both feeds). `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/pierce.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register Pierce County's deeds from the county's weekly `sale.zip`, the next
step `scottsdale-311` named.

## Decisions

- 2026-09-30 — Read the whole county. Pierce County's metro box spans the
  county and its submarkets include downtown Tacoma, so the parcel join takes
  no `where`; Tacoma's sales publish under both metros.
- 2026-09-30 — Reuse Tacoma's setting for the file and the parcel layer rather
  than declaring the same URLs twice; their descriptions now name both feeds.
- 2026-09-30 — Keep every other part of Tacoma's spec (window, cap, cadence,
  ids, columns, `select`), so the two feeds read the file the same way;
  `test_pierce_deeds.py` checks they stay alike.

## Current step

Done.

## Next step

Register what the two research agents find for the twelve metros that lack
permits and deeds.
