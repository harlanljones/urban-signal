# Stream log — dc-deeds — 2026-09-30

## Claim

- **Stream id:** `dc-deeds`
- **Leaf files created/edited:**
  - corpus file `washington_dc.yaml` (the deeds `parcel_join`)
  - `arcgis_client.py` (`fetch_centroid_index` gains `via`)
  - tests: `test_dc_parcel_join.py`, `test_producers_dc.py`,
    `test_scheduler_boundaries.py`
  - `README.md` (DC's deeds cell), `docs/research/feed-health-2026-09-30.md`,
    this file, `.streams/dispatch-log.md`
- **Spine files touched:** `scheduler.py` and `deeds_acris_producer.py`, one
  argument each: the parcel join passes the spec's `via` to the client.
  `pytest -m interlock` passes.
- **Generated surfaces:** none. The endpoint and feed set are unchanged, so
  product facts and the dashboard are too.

## Intent

Place DC's sales on their lots. The join read the Parcel Lots layer, which
holds only `PAR` parcels, and placed 12 of 4,996 sales.

## Decisions

- 2026-09-30 — Join the Owner Polygons layer (40) on `SSL`: 126 of 127
  non-condominium sales in a 200-sale sample matched.
- 2026-09-30 — A condominium unit takes its building's lot through
  `CONDORELATE` (table 52, `SSL` to `MAT_SSL`): 53 of the sample's 73 units.
  `REC_LOT` with the Record Lots layer would place 63, but needs a two-column
  key; left for later.
- 2026-09-30 — The hop is a generic optional `via` on `parcel_join`, so any
  spec whose layer lacks some keys can name a relating table.

## Current step

Done.

## Next step

None for DC `deeds`.
