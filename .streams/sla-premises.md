# Stream log — sla-premises — 2026-09-30

## Claim

- **Stream id:** `sla-premises`
- **Leaf files created/edited:**
  - corpus files `lynchburg.yaml` and `tampa.yaml` (the `sla` blocks) and
    their mirrors `lynchburg.py` and `tampa.py`
  - tests: `test_producers_lynchburg.py`, `test_producers_tampa.py`,
    `test_scheduler_boundaries.py`
  - `docs/research/feed-health-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** none. `poll_job` runs any spec's `parcel_join`,
  whatever its producer.
- **Generated surfaces:** none. The endpoints and feed set are unchanged, so
  product facts and the dashboard are too.

## Intent

Place licences at their premises. Lynchburg geocoded a mailing block (40% of
licences mail outside the city); Tampa published an owner's mailing address
when a permit had none of its own, and fetched owners' names, phones and
emails.

## Decisions

- 2026-09-30 — Lynchburg joins `/41` on `Parcel_ID` with `row_key`
  `ParcelID`; centroid, as its deeds do. The `/2` locations layer holds
  several points per licence on that same parcel, so the parcel centroid is
  the one point.
- 2026-09-30 — A licence whose parcel has no polygon stays unplaced; it is
  never geocoded from the mailing block.
- 2026-09-30 — Tampa keeps its layer's points; only the address fallback and
  the fetched columns change.
- 2026-09-30 — The `sla` producer's standalone `run_stream` does not run
  parcel joins (the scheduler's poll does, and is what the deployment runs);
  left as is.

## Current step

Done.

## Next step

None for these feeds.
