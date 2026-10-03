# Stream log — replace-stopped-feeds — 2026-10-03

## Claim

- **Stream id:** `replace-stopped-feeds`
- **Leaf files created/edited:**
  - corpus: `montgomery_al.yaml`, `lincoln.yaml` and `spokane.yaml` (each
    feed moves to a live source); `tulsa.yaml`, `columbus_ga.yaml`,
    `eugene.yaml` and `boston.yaml` (the stopped feeds go)
  - city modules `montgomery_al.py`, `lincoln.py`, `spokane.py`, `tulsa.py`,
    `columbus_ga.py`, `eugene.py` and `boston.py` (each new source, and why
    nothing replaces a retired feed)
  - those cities' tests and `test_snapshot_reach.py`
  - this file, the cities' stream files and `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (Montgomery's and Lincoln's settings
  point at the live layers, the LCB lists page replaces the data.wa.gov
  renewal set, and the settings of the five retired feeds go);
  `sla_licenses_producer.py` (the Excel client, and licence text without
  fixed-width padding). `pytest -m interlock` passes.
- **Generated surfaces:** product facts (`facts.json` and the seven cities'
  pages).

## Intent

The 2026-10-03 staleness census found eight feeds whose sources had
stopped. Harlan chose to look for a live source for each first, wire the
ones found, and retire the rest in one PR.

## Decisions

- 2026-10-03 — Montgomery permits: the City's own
  `HostedDatasets/Construction_Permits` layer (47,504 permits since 2021,
  loaded weekly, newest 2026-09-25) replaces `All_Permit_viewlayer`, which
  holds nothing issued after 2024-03-01. The spec reads the site address
  (`PhysicalAddress`), never the owner, contractor or mailing columns. Two
  live polls: the first published 830 of 1,000 rows (170 sit at 0,0 and
  `metro_clip` skips them); the second read the four permits of the newest
  day again and published none.
- 2026-10-03 — Lincoln permits: layer 6 (Recent Years) replaces layer 4, a
  calendar-year bucket that ended with 2025. `SD_APP_DD` trails `Issued` by
  up to about 16 months on 2% of rows, so the poll re-reads the newest 2,000
  rows as a snapshot. Two live polls: 1,270 published (730 fall outside the
  metro box), then none new.
- 2026-10-03 — Spokane licences: the LCB's weekly On-Premise workbook
  replaces data.wa.gov `9dee-kzm5` (last updated 2026-04-04), whose spec
  also took a person, the designated signee, as each premises' name. Two
  live polls, the first capped at 30 rows and geocoded by the Census
  geocoder: 30 published, 27 placed inside the box; the second read the
  newest day's licence again and published none. The workbook pads its
  trade names, addresses, cities and privileges, so the licence producer
  now trims the text it publishes, for every city; four other cities' tests
  had pinned stray spaces from their sources.
- 2026-10-03 — Retired, with no live replacement: Tulsa crime (an ArcGIS
  Online copy outside the City's org, newest incident 2019-01-24; the
  City's police folders ask for a token), Columbus GA permits (nothing
  issued after 2022-04-15; permits appear to have moved to Tyler EnerGov,
  which publishes no rows), Eugene 311 (camping work orders, newest
  2021-03-12) and deeds (City-owned land only; Lane County's sales layer
  holds nothing after 2024-12-06), and Boston deeds (the id was a CKAN
  package, so every read failed, and no Boston sales source is current).
- 2026-10-03 — Every metro stays registered.

## Current step

Done.

## Next step

Tulsa 311 from the City's "Open Data - Customer Care (Cases)" CSV, which
the City refreshed on 2026-09-28; Springfield OR permits from its Accela
records layer, inside Eugene's box; Lincoln's metro box, which misses the
southern and eastern edge where a third of the City's new homes are.
