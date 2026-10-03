# Stream log — allentown-permits — 2026-09-30

## Claim

- **Stream id:** `allentown-permits`
- **Leaf files created/edited:**
  - corpus file `allentown.yaml` (a `permits` spec); `cities/allentown.py`
    (the module notes and `compose_permit_address`)
  - tests: `test_allentown_permits.py` (new), `test_snapshot_reach.py`
  - notes in `docs/research/two-family-depth-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the City's permits layer).
  `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/allentown.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register the permits source the probe of the eight north-eastern `sla`-and-
`deeds` metros found for Allentown, the next step `asheville-permits` named,
and record why the other seven stay without permits.

## Decisions

- 2026-09-30 — Read a 90-day window on `ISSUEDATE` as a snapshot, as
  Asheville's permits do: five of the window's 819 rows carry a time of day,
  which would make a watermark filter strict on its day.
- 2026-09-30 — Break ties on the permit number, not the object id, since the
  object ids look reassigned with each reload.
- 2026-09-30 — Join the five address columns in a leaf
  `compose_permit_address`, as Cape Coral and Henderson do.
- 2026-09-30 — Hold Burlington's permits export (frozen since 2026-04-27) and
  Providence's right-of-way permits (not building permits).

## Current step

Done.

## Next step

Register Allentown's and New Haven's `311`, and record the north-eastern
metros' `311` probe results.
