# Stream log — snap-wave — 2026-09-30

## Claim

- **Stream id:** `snap-wave`
- **Leaf files created/edited:**
  - the `sla` block in 25 corpus files: `allentown`, `billings`,
    `bowling_green`, `bozeman`, `burlington`, `chandler`, `charleston_wv`,
    `fort_collins`, `frederick`, `grand_rapids`, `laredo`, `lincoln`,
    `missoula`, `montgomery_al`, `nampa`, `peoria`, `providence`, `richmond`,
    `roanoke`, `santa_fe`, `savannah`, `sioux_falls`, `tempe`, `topeka` and
    `yakima` `.yaml`
  - the same 25 leaf modules: a dated SLA note in the docstring, and the
    feed-mirror docstrings that named SLA as unregistered
  - tests: `test_producers_snap.py` (the retailer table, every registered
    metro has SLA), `test_producers_richmond.py` (Richmond's feed set)
  - `docs/research/snap-metro-scope-2026-09-30.md`, product facts
    (`facts:export`), this file, `.streams/dispatch-log.md`
- **Spine files touched:** none. The corpus files are leaf data; each block is
  what the existing `snap_sla_spec(state, metro_bbox)` builds.
- **Generated surfaces:** `apps/product/public/facts.json` and the 25 cities'
  `cities/*.json`.

## Intent

Give every registered metro an `sla` family. The US-364 extension covered
every SLA-less metro of its day; later waves registered 25 more without one.

## Decisions

- 2026-09-30 — Each block is copied from an existing SNAP block with only the
  `where` changed, so `TestSnapMetroScope` holds every one to the helper.
- 2026-09-30 — No caps: the largest metro, Grand Rapids, holds 664 stores,
  under two thirds of the default 1,000.
- 2026-09-30 — Grand Rapids takes SNAP too, although it was registered with
  geometry only: nothing in its leaf asks to keep it featureless.
- 2026-09-30 — The leaf feed mirrors stay leaf-authored feeds only; the SNAP
  spec lives in the corpus, as it does for the earlier SNAP metros, whose
  leaves have no mirrors.
- 2026-09-30 — Chandler and Tempe overlap (113 stores publish under both), as
  their other feeds already can; boxes stay as registered.

## Current step

Done.

## Next step

The backfill loader's missing client kwargs (`select`, `link_pattern`,
`zip_member`) and parcel join, or the object-id ordering of incremental feeds.
