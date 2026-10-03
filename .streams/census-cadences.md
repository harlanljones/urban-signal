# Stream log — census-cadences — 2026-10-03

## Claim

- **Stream id:** `census-cadences`
- **Leaf files created/edited:**
  - corpus: `bridgeport.yaml`, `new_haven.yaml` (`deeds` cadence 30 to 365)
    and `nyc.yaml` (`crime` cadence 30 to 92)
  - `apps/api/src/spatial/cities/bridgeport.py` and `new_haven.py` (the
    leaf mirrors' `deeds` cadence)
  - tests: `test_registry_cadence.py`, `test_producers_crime.py`,
    `test_producers_bridgeport.py`, `test_producers_new_haven.py`
  - this file and `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (a comment: NYC's crime set publishes
  quarters, not months). `pytest -m interlock` passes.
- **Generated surfaces:** none (product facts carry no cadence).

## Intent

Declare the publishing rhythm two sources state themselves, so the weekly
staleness check stops paging for feeds that are on schedule. From the
2026-10-03 census (`docs/research/feed-freshness-2026-10-03.md`).

## Decisions

- 2026-10-03 — Connecticut's Real Estate Sales set (`5mzw-sjtu`, Bridgeport's
  and New Haven's `deeds`): the portal's metadata says "Update Frequency:
  Annually", and each update adds one grand-list year (1 October to
  30 September). The 2026-08-12 update added sales to 2025-09-30, so the
  newest sale runs 10 to 23 months old. 365 days alarms at 730.
- 2026-10-03 — NYPD Complaint Data Current (`5uac-w243`, NYC `crime`): the
  portal's metadata says "Update Frequency: Quarterly", and the set holds
  complete quarters only. The 2026-07-27 update ran to 2026-06-30, so the
  newest complaint runs one to four months old. 92 days alarms at 184.
- 2026-10-03 — Live, through the probe with the new cadences: all three feeds
  read fresh (CT newest 2025-09-30, 368 days; NYC newest 2026-06-30, 95 days).
- 2026-10-03 — A fresher deeds source for Bridgeport and New Haven (a city
  assessor table, as Hartford's) would change coverage and is its own change.

## Current step

Done.
