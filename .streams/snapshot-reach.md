# Stream log — snapshot-reach — 2026-09-30

## Claim

- **Stream id:** `snapshot-reach`
- **Leaf files created/edited:**
  - `docs/research/snapshot-reach-2026-09-30.md` (new),
    `docs/research/snap-metro-scope-2026-09-30.md` ("Not covered here" points at it)
  - 26 dataset blocks in 25 `apps/api/src/spatial/cities/data/*.yaml` files
    (`batch_limit`, `order_by`, two `where` filters, nine `interval_seconds`)
  - `scripts/backfill_loader.py` (keeps each spec's `where`)
  - `apps/api/tests/unit/test_snapshot_reach.py` (new), `test_scheduler.py`,
    `test_backfill_loader.py`, and the leaf suites that pinned the old values
  - this file, `.streams/snap-metro-scope.md`, `.streams/dispatch-log.md`
- **Spine files touched (one hold):** `apps/api/src/producers/scheduler.py`
  (a seen-set per snapshot job, the full-cap warning, `_NEWEST_FIRST`).
- **Generated surfaces:** none change (product facts carry no cap, order or
  `where`; `facts:check` green).

## Intent

Finish what the SNAP fix started: every snapshot feed's poll stops at its
`batch_limit` in table order, so a source larger than the cap hands every poll
the same first rows. Measure the other 38 snapshot feeds and make each reach
its rows.

## Decisions

- 2026-09-30 — Two shapes. A table that fits (with half again to spare) is
  read whole; a larger one is read newest first by the date it already tracks,
  with a window of at least 1.5 times the rows dated in the last 90 days, so a
  monthly batch with late recordings still lands inside it. Everything else is
  a listed gap with its reason; `test_snapshot_reach.py` makes a new snapshot
  feed pick one.
- 2026-09-30 — Multi-page windows break date ties with the object id or
  `:id`, since paging a shared date is not stable. Raleigh filters
  `SALE_DATE IS NOT NULL` (nulls sort first); Cleveland bounds its sort to 180
  days (the unbounded sort outlasts the client's 30-second timeout).
- 2026-09-30 — A poll that reads more than one page runs at most every 30
  minutes, so the fix raises portal load from about 2,700 to about 3,900
  requests a day rather than about 8,200.
- 2026-09-30 — Each snapshot job keeps its own seen-set (twice its cap): in the
  shared 100,000-id window, other feeds' ids evicted a snapshot's ids and it
  re-published unchanged rows.
- 2026-09-30 — Backfills keep each spec's `where`; the loader had dropped it
  for every feed, so a SNAP backfill read the national layer.

## Current step

Done. 15 feeds read in full, 16 newest first, 7 listed gaps (Kansas City and
Reno have no sortable date; Henderson, Phoenix, Boston, Ocala and Orlando need
feed repairs).

## Next step

Repair the feeds that fail or publish nothing: a one-poll check of all 367
jobs found 36 hard failures and 16 feeds that fetch rows but publish none.
