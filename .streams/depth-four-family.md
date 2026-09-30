# Stream log — depth-four-family — 2026-09-30

## Claim

- **Stream id:** `depth-four-family`
- **Leaf files created/edited:**
  - `docs/research/four-family-depth-2026-09-30.md` (new)
  - `docs/research/se-probe-tallahassee.md` (addendum)
  - `apps/api/src/spatial/cities/data/columbus.yaml`, `apps/api/src/spatial/cities/data/tallahassee.yaml`
  - `apps/api/src/spatial/cities/tallahassee.py` (SLA docstring, leaf mirror)
  - `apps/api/tests/unit/test_producers_columbus.py`, `test_producers_tallahassee.py`,
    `test_producers_snap.py`, `test_scheduler.py`
  - `.streams/city-columbus.md`, `.streams/city-tallahassee.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched (one hold):** `apps/api/src/config.py`
  (`arcgis_columbus_311_url`), `apps/api/src/spatial/city_registry.py`
  (`DatasetSpec.batch_limit`), `apps/api/src/producers/scheduler.py` (reads it).
- **Shared module edited, not in the spine manifest:**
  `apps/api/src/producers/watermarks.py` (`maps2.columbus.gov`).
- **Generated surfaces:** `apps/product/public/facts.json`,
  `apps/product/public/cities/columbus.json`, `cities/tallahassee.json`.

## Intent

Move metros that are one family short into the four-family tier (signal-roadmap
E3; wave-2 §1, depth before breadth). Probe 13 of the 32 three-family metros live
and register only feeds that pass the usual bar (row-level API on a supported
platform, working watermark, fresh, stable id, located, metro-scoped, nothing
personal mapped).

## Decisions

- 2026-09-29 23:10Z — Three research workers probed 13 metros (read-only on the
  repo). A container restart killed them mid-run; two were resumed from their notes.
- 2026-09-30 — Columbus 311 and Tallahassee `sla` (SNAP fallback) qualify; eleven
  metros stay (table in the research doc).
- 2026-09-30 — Columbus 311 filtered volume passes 1,000 rows on 22 of 64 weekdays
  (90-day count); added opt-in `DatasetSpec.batch_limit`, set 5,000 on the feed.
- 2026-09-30 — Found, not fixed: SNAP specs are state-wide with a 1,000-row
  snapshot cap (each metro job sees the same 1,000 lowest-`ObjectId` rows in its
  state); geocoder `FL` unit token and `#` cut drop the geocode context.

## Current step

Done. Tier counts 16 / 32 / 54 / 54 / 1 -> 18 / 30 / 54 / 54 / 1.

## Next step

Scope the 54 SNAP specs to their metro bboxes (with `batch_limit` where a bbox
holds more than 1,000 retailers).
