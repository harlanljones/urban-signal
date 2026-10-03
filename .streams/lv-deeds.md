# Stream log — lv-deeds — 2026-09-30

## Claim

- **Stream id:** `lv-deeds`
- **Leaf files created/edited:**
  - corpus file `las_vegas.yaml` (the deeds block) and its mirror
    `las_vegas.py` (the deeds field map, `LAS_VEGAS_PARCEL_POLYGONS`, the
    deeds feed spec)
  - tests: `test_producers_las_vegas.py`
  - `docs/research/feed-health-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** none. The parcel join already runs in `poll_job`
  and the deeds producer's stream for any spec that declares one.
- **Generated surfaces:** none. The endpoint and feed set are unchanged, so
  product facts and the dashboard are too.

## Intent

Place each Las Vegas sale on its parcel. The spec geocoded the owner's
mailing address, which put at least a third of sales where their owner
receives mail and sent owners' addresses to the geocoder.

## Decisions

- 2026-09-30 — Join `CLV_PARCELS_POLY` (layer 7), which has a polygon for
  each of the table's 302,279 parcels, on `PARCEL`; centroid geometry, as
  DC's join uses.
- 2026-09-30 — A sale whose parcel has no polygon stays unplaced; it is never
  geocoded from the mailing columns.
- 2026-09-30 — Drop `APN` from the field map: the table has no such column.

## Current step

Done.

## Next step

DC `deeds` joins the Parcel Lots layer, which holds only `PAR` parcels, so it
places 12 of 4,996 sales.
