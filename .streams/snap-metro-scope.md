# Stream log — snap-metro-scope — 2026-09-30

## Claim

- **Stream id:** `snap-metro-scope`
- **Leaf files created/edited:**
  - `docs/research/snap-metro-scope-2026-09-30.md` (new),
    `docs/research/four-family-depth-2026-09-30.md` (SNAP section points at the fix)
  - the 54 SNAP `sla` blocks in `apps/api/src/spatial/cities/data/*.yaml`
  - `apps/api/src/spatial/cities/tallahassee.py` (leaf mirror, docstrings);
    docstrings only in `lakeland.py`, `fort_smith.py`, `melbourne.py`,
    `apps/api/src/producers/state_license_specs.py`
  - `apps/api/tests/unit/test_producers_snap.py`, `test_producers_denver.py`,
    `test_producers_tallahassee.py`, `test_scheduler.py`; docstrings only in
    `test_producers_evansville.py`, `test_producers_huntsville.py`,
    `test_producers_canton.py`
  - this file, `.streams/dispatch-log.md`
- **Spine files touched (one hold):** `apps/api/src/spatial/city_registry.py`
  (`snap_sla_where`, `snap_sla_spec` takes the metro bbox and a `batch_limit`).
- **Generated surfaces:** none change (product facts carry no `where` clause;
  `facts:check` green).

## Intent

Fix the defect the depth pass found: every SNAP `sla` spec filtered by state only,
so each snapshot poll read the state's first 1,000 retailers by `ObjectId` and
tagged them with its own city.

## Decisions

- 2026-09-30 — Filter is the metro's state inside its metro bbox. The state term
  stays so a bbox crossing a state line keeps to the metro's state (908 retailers
  across 12 metros stay out, as before; 587 of them are Prince George's County's
  DC and Virginia neighbours).
- 2026-09-30 — `batch_limit` on the 18 metros whose bbox holds 667 or more
  retailers; each cap is at least 1.5 times the measured count, and a test pins
  the counts so a new SNAP metro must bring its own.
- 2026-09-30 — Live checks: all 54 exact `where` strings re-counted and matched;
  `poll_job` on Tallahassee (242 of 242) and Houston (4,205 of 4,205, five pages).

## Current step

Done. SNAP metros reach 34,686 of 34,686 retailers (were 5,694).

## Next step

The other 38 snapshot-mode feeds share the same cap; measure each and give the
ones larger than 1,000 rows a filter or a cap.
