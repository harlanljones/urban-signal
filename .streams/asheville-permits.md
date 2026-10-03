# Stream log — asheville-permits — 2026-09-30

## Claim

- **Stream id:** `asheville-permits`
- **Leaf files created/edited:**
  - corpus file `asheville.yaml` (a `permits` spec); the module notes in
    `cities/asheville.py`
  - tests: `test_asheville_permits.py` (new), `test_snapshot_reach.py`
  - notes in `docs/research/two-family-depth-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the City's permits layer) and
  `producers/watermarks.py` (the host joins `ANSI_DATE_LITERAL_HOSTS`).
  `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/asheville.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register the permits source the probe of the fifteen `sla`-and-`deeds`
metros found for Asheville, the next step `toledo-deeds` named, and record
why the probe's other six southern and western metros stay without permits
or `311`.

## Decisions

- 2026-09-30 — Read a 90-day window as a snapshot rather than a watermark
  on `date_opened`: some rows carry the day's date a second after midnight,
  and a live incremental poll left its watermark there, so its next filter
  would have passed over the rest of that day.
- 2026-09-30 — Map the opened date to both the filing and the issue date,
  since the layer has no issue date (as Pierce County and Augusta fall back
  to the application date); the status says whether a permit is issued.
- 2026-09-30 — Drop right-of-way, temporary-event, outdoor-vendor,
  over-the-counter and home-business records, and leave `job_value` out:
  three of 66,072 rows carry one, none from the past year.
- 2026-09-30 — Hold Anchorage's police camp reports, the Washoe sheriff's
  graffiti, dumping and abandoned-vehicle tracker (Reno) and Roanoke's
  right-of-way permits: each is one narrow slice of its family.

## Current step

Done.

## Next step

Register Allentown's permits and `311` and New Haven's `311`, and record the
north-eastern metros' probe results.
