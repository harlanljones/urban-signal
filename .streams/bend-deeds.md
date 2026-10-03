# Stream log — bend-deeds — 2026-09-30

## Claim

- **Stream id:** `bend-deeds`
- **Leaf files created/edited:**
  - corpus file `bend.yaml` (a `deeds` spec)
  - tests: `test_bend_deeds.py` (new), `test_scheduler_boundaries.py`,
    `test_backfill_loader.py`, `test_snapshot_reach.py`,
    `test_deeds_party_names.py`
  - `scripts/backfill_loader.py` (a backfill clips as the poll does)
  - notes added to `docs/research/deeds-probe-2026-09-30.md`,
    `snapshot-reach-2026-09-30.md` and `four-family-depth-2026-09-30.md`,
    this file, `.streams/dispatch-log.md`
- **Spine files touched:** `city_registry.py` (`DatasetSpec.metro_clip`),
  `scheduler.py` (the job carries the flag; `poll_job` skips rows placed
  outside the metro box and reports `outside_metro`), `config.py` (the sales
  table and the taxlot layer). `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/bend.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register Bend's deeds from Deschutes County's `GIS_SALES` table, the next
step `maricopa-deeds` named. The table is county-wide with no city column.

## Decisions

- 2026-09-30 — Keep Bend's sales by the metro box, not the account table's
  `City`: that is the postal city (238 of 1,220 "BEND" sales lie outside the
  box) and its `UGB` column is empty.
- 2026-09-30 — A server filter on the four township-range prefixes under the
  box (`1711`, `1712`, `1811`, `1812`; every one of the 50,356 taxlots that
  touch the box) halves the rows and the taxlot lookups; `metro_clip` drops
  the rest outside the box (29 of 1,048).
- 2026-09-30 — `metro_clip` skips a row before dedup and counts it, never
  dead-letters it, so a sale the join cannot place yet publishes on the poll
  that places it. A backfill clips the same way.
- 2026-09-30 — `Reject_Description_1` maps to `doc_type`, as Hartford's sale
  code does.

## Current step

Done.

## Next step

Medford deeds (Jackson County `PropertySales`): the HTTP client rejects the
server's malformed `Content-Security-Policy` header.
