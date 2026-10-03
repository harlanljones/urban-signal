# Stream log — charlotte-deeds — 2026-09-30

## Claim

- **Stream id:** `charlotte-deeds`
- **Leaf files created/edited:**
  - corpus file `charlotte.yaml` (a `deeds` spec); the module notes in
    `cities/charlotte.py`
  - tests: `test_charlotte_deeds.py` (new), `test_producers_charlotte.py`,
    `test_deeds_party_names.py`, `test_snapshot_reach.py`
  - notes in `docs/research/two-family-depth-2026-09-30.md` and
    `docs/research/four-family-depth-2026-09-30.md`, the Charlotte row of the
    README table, this file, `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the county's sales layer, and the
  Charlotte comment). `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/charlotte.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register the deeds source the two-family deeds probe found for Charlotte, the
next step `charlotte-permits` named, which gives Charlotte all four signal
families.

## Decisions

- 2026-09-30 — Read the county's `TaxParcelSales` ledger, not the
  `TaxParcel_camadata` parcel layer: the parcel layer keeps only each
  parcel's latest sale, holds future-dated rows and splits the deed's book
  and page into two columns.
- 2026-09-30 — One event per transfer and parcel, under the deed's book and
  page as the document id, so a deed's parcels share a Kafka key and a
  transfer repeated on a parcel's other property rows publishes once.
- 2026-09-30 — Cap the 90-day window at 15,000 rows: it held 8,925 on
  2026-09-30 and at most 11,009 over the past year.

## Current step

Done.

## Next step

Register Toledo's deeds from the Lucas County Auditor's sales layer, and what
the `311` research agents find for the two-family metros.
