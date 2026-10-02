# Stream log — lakeland-deeds — 2026-10-02

## Claim

- **Stream id:** `lakeland-deeds`
- **Leaf files created/edited:**
  - corpus file `lakeland.yaml` (a `deeds` spec) and `cities/lakeland.py`
    (the module notes)
  - `csv_client.py` (a zip member is read as a stream: decompressed,
    decoded and parsed a piece at a time instead of whole)
  - tests: `test_lakeland_deeds.py` (new); `test_csv_client.py` (the
    streaming read) and `test_snapshot_reach.py` (the window)
  - notes in `docs/research/two-family-depth-2026-09-30.md` and
    `snapshot-reach-2026-09-30.md`, this file, `.streams/dispatch-log.md`,
    and a dated line in `.streams/us-286-lakeland.md`
- **Spine files touched:** `config.py` (the source). `pytest -m interlock`
  passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/lakeland.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register the Polk County Property Appraiser's sales for Lakeland, held in
`florida-deeds` because the CSV client read the 518 MB sales member whole.

## Decisions

- 2026-10-02 — Stream a zip member in the CSV client rather than special-case
  the feed: decompress and decode it a megabyte at a time, in the encoding
  the whole member would have chosen, found in a first pass. A read of
  Polk's file adds 6 MB to the peak instead of 1,041 MB.
- 2026-10-02 — Read only the parcels numbered 23 to 25: a Polk parcel number
  starts with its range and township, and every City parcel touching the
  metro box starts with one of the three. The join asks 66 times a poll
  instead of 166 and publishes the same 1,885 sales.
- 2026-10-02 — Key rows on parcel, date, book and page; cap 8,000 (the 90
  days in reach from 2025-02-17 held 5,272); cadence 14 days (the newest
  sale was eight days old on a nightly build).

## Current step

Done.

## Next step

None for Lakeland's deeds. Lakeland still lacks a `311` source.
