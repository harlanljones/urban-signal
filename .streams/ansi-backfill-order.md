# Stream log — ansi-backfill-order — 2026-10-02

## Claim

- **Stream id:** `ansi-backfill-order`
- **Leaf files created/edited:**
  - `scripts/backfill_loader.py` (a backfill on a server that reads only
    date literals keeps the spec's own order, as `poll_job` sends it)
  - tests: `test_backfill_loader.py`
  - this file and `.streams/dispatch-log.md`
- **Spine files touched:** none.
- **Generated surfaces:** none.

## Intent

Let Augusta's permits backfill run: the loader dropped the spec's order on
every date-literal host, and Augusta's permits table has no object-id field
to page by, so its first page was refused.

## Decisions

- 2026-10-02 — Keep the spec's own order rather than forcing the watermark
  column newest first: several of these specs page by object id or by a
  composite order on purpose, and their polls prove that shape.
- 2026-10-02 — Check the shape live on every job on a date-literal host
  whose spec names an order (62): 60 answered, and the 2 that failed
  (Wilmington NC deeds, whose sale date is text; Phoenix's licence server,
  down) failed the same way with the order dropped.

## Current step

Done.

## Next step

Wilmington NC deeds: the backfill window compares a text sale date with a
timestamp. Melbourne permits: Palm Bay's layer was last issued on
2022-05-31.
