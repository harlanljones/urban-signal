# Stream log — tacoma-deeds — 2026-09-30

## Claim

- **Stream id:** `tacoma-deeds`
- **Leaf files created/edited:**
  - corpus file `tacoma.yaml` (a `deeds` spec); the module notes in
    `cities/tacoma.py`
  - `src/producers/csv_client.py` (a file with no header row takes the
    spec's `columns`; lines split without `io.StringIO`)
  - `src/producers/arcgis_client.py` (`fetch_centroid_index` takes a `where`)
  - tests: `test_tacoma_deeds.py` (new), `test_csv_client.py`,
    `test_dc_parcel_join.py`, `test_scheduler_boundaries.py`,
    `test_snapshot_reach.py`, `test_deeds_party_names.py`
  - notes added to `docs/research/deeds-probe-2026-09-30.md`,
    `snapshot-reach-2026-09-30.md` and `four-family-depth-2026-09-30.md`,
    this file, `.streams/dispatch-log.md`
- **Spine files touched:** `city_registry.py` (`DatasetSpec.columns`),
  `scheduler.py` (forwards `columns` to the CSV client; the parcel join
  passes its `where`), `config.py` (the sales file and the parcel layer).
  `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/tacoma.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register Tacoma's deeds from Pierce County's weekly `sale.zip`, the next step
`medford-deeds` named.

## Decisions

- 2026-09-30 — Name the file's columns in the spec (`columns`, forwarded like
  `zip_member` and `delimiter`) rather than guessing a header: the file's
  first line is a sale.
- 2026-09-30 — Keep to the city, not the box. Neither the file nor the parcel
  layer names a city, but the layer's `Tax_Area_Code` does: seven codes hold
  75,859 of the 75,908 parcels inside the city limits. The parcel join takes
  a `where`, so a sale outside them stays unplaced and `metro_clip` skips it.
  The box alone would have kept 232 sales in Lakewood, University Place,
  Fircrest, Ruston and unincorporated land, a third of those it holds.
- 2026-09-30 — Split CSV lines with a regex instead of `io.StringIO`, which
  holds four bytes a character: the 89 MB file's parse peaked at 339 MB
  instead of 510 MB. The line endings match `StringIO(newline="")`.
- 2026-09-30 — Read once a day with a 5,000-row cap: the file is rebuilt
  weekly and a poll downloads all 20.8 MB of it.
- 2026-09-30 — Ids join `ETN` and `Parcel Number`, the layout's primary key:
  a sale covers one or more parcels (452 rows carried 440 excise tax
  numbers).

## Current step

Done.

## Next step

Scottsdale 311 from the city's `OpenData_Tabular/MapServer/28` table, once
`maps.scottsdaleaz.gov` stops answering the probe with a block page.
