# Stream log — nyc-permits-poll — 2026-10-03

## Claim

- **Stream id:** `nyc-permits-poll`
- **Leaf files created/edited:**
  - corpus: `nyc.yaml` (`permits` declares `issuance_date` as `%m/%d/%Y` text)
  - tests: `test_watermarks.py`; `test_scheduler.py`,
    `test_scheduler_boundaries.py`, `test_acquisition.py` and
    `test_feed_staleness_probe.py` (tests that used NYC's permits job as an
    ISO-timestamp fixture)
  - docs: `docs/research/feed-freshness-2026-10-03.md` and
    `docs/research/current-city-feed-gaps.md` (`dobrundate` cannot drive the
    poll)
  - this file and `.streams/dispatch-log.md`
- **Spine files touched:** none.
- **Generated surfaces:** none.

## Intent

Let NYC's permits poll read new permits after its first poll.

## Decisions

- 2026-10-03 — `ipu4-2q9a`'s `issuance_date` is text: ISO through 2020-06-05,
  `MM/DD/YYYY` since. Undeclared, the scheduler stored the newest date as ISO
  and sent `issuance_date >= '2023-03-13T00:00:00'`, which the server compares
  as text: no `MM/DD/YYYY` value sorts above it, and no ISO value is that new.
  Two live polls: the first read 1,000 rows, the second none.
- 2026-10-03 — Not `dobrundate`: it is the date of the set's last reload, and
  3,897,736 rows carry 2026-10-01 (the next run dates hold 1 to 447 rows), so
  a poll on it would re-read nearly the whole set after each reload.
- 2026-10-03 — Declared `watermark_type: text`, `watermark_format: '%m/%d/%Y'`,
  so the poll names the dates (`text_date_window`). Live: two polls from a
  fresh state read 1,000 rows each (the second through the date window), and
  two from the ISO watermark the old spec stored (2026-09-25) read the 88
  permits issued 2026-09-26 to 09-30, then only the watermark's day again
  (9 rows, all duplicates). The probe dates the feed 2026-09-30.
- 2026-10-03 — Eight scheduler tests drove NYC's permits job with ISO
  timestamps to exercise the timestamp path (boundaries, the future guard,
  the watermark source column); they now pin that path. The restore test
  checks a month-first future watermark beside an ISO one, and the probe's
  wiring test reads a month-first date.
- 2026-10-03 — Open question for its own change: the set holds the City's
  older filing system's permits (5,039 dated 2026 by 2026-08-22); permits
  filed in DOB NOW are in `rbx6-tga4`, not yet audited.

## Current step

Done.
