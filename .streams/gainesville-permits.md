# Stream log — gainesville-permits — 2026-10-02

## Claim

- **Stream id:** `gainesville-permits`
- **Leaf files created/edited:**
  - corpus: `gainesville.yaml` (the `permits` spec reads Alachua County's
    `BuildingPermitsCS` layer)
  - `apps/api/src/spatial/cities/gainesville.py` (the County's field map, a
    `compose_permit_type`, the leaf copy of the spec and its scope note)
  - tests: `test_producers_gainesville.py`, `test_snapshot_reach.py`
  - this file, `.streams/city-gainesville.md` and `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (`arcgis_gainesville_permits_url`
  replaces `socrata_gainesville_permits_endpoint`). `pytest -m interlock`
  passes.
- **Generated surfaces:** product facts (Gainesville's permits platform,
  watermark and interval).

## Intent

Gainesville's permits feed polls a live source. The City's Socrata set
(`p798-x3nx`) holds nothing issued after 2023-02-28.

## Decisions

- 2026-10-02 — Read Alachua County Growth Management's `BuildingPermitsCS`
  layer on ArcGIS Online, loaded twice a week (its newest permit was issued
  the day before). It holds the permits the County issues: of 2,441 placed
  permits issued in the 90 days to 2026-10-01, 33 lie inside the City of
  Gainesville and about three quarters inside the metro box, which takes in
  the unincorporated fringe. The City's own permits stay uncovered: its live
  system (PermitGNV) is on Citizenserve, with no row API, and its one-off
  ArcGIS upload of 2026-07-31 has not changed since.
- 2026-10-02 — Snapshot a 90-day window, newest first, with a 4,000-row cap
  (1,992 permits in the window). Each load adds permits issued days earlier:
  97.7% of the window's rows were loaded after a permit issued later than
  them, so an issue-date watermark would skip them.
- 2026-10-02 — Keep the building, trade, pool, demolition, fire and sign
  permits; drop the right-of-way, irrigation, tree-removal, zoning, site
  ("Construction Permit") and temporary-use records. "Model Permit" has
  never been issued and would read as new homes.
- 2026-10-02 — A building permit's type reads with its sub-type ("Building
  Permit: New Construction"); trade permits keep their type. The County files
  a change of occupancy under its own type, so a "Renovation/Conversion"
  building permit reads as a renovation.
- 2026-10-02 — Never request the applicant, contractor or owner columns, the
  work description or the portal links.

## Current step

Done.

## Next step

The City of Gainesville's permits, if PermitGNV or its ArcGIS upload starts
publishing rows.
