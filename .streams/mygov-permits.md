# Stream log — mygov-permits — 2026-10-02

## Claim

- **Stream id:** `mygov-permits`
- **Leaf files created/edited:**
  - corpus files `texarkana.yaml` and `abilene.yaml` (a `permits` spec
    each) and `cities/texarkana.py` and `cities/abilene.py` (the notes)
  - `excel_client.py` (a workbook's text dates are compared and ordered as
    dates in the spec's format; `point_col`, with `point_lon_first`) and
    `csv_client.py` (`point_lon_first`; each quoted value of a `NOT IN` list
    is read whole)
  - `scripts/backfill_loader.py` (a text-dated workbook backfills newest
    first, as a CSV does)
  - tests: `test_texarkana_permits.py` and `test_abilene_permits.py` (new);
    `test_excel_client.py`, `test_csv_client.py` and
    `test_backfill_loader.py`
  - notes in `docs/research/one-family-depth-2026-10-02.md`, this file and
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the two sources), `city_registry.py`
  (`point_lon_first`), `scheduler.py` (the Excel client receives the
  watermark column, format and exclusions, `point_col` and
  `point_lon_first`; job metadata carries `point_lon_first`) and
  `dob_permits_producer.py` (reads `MM/DD/YYYY at H:MM AM`). `pytest -m
  interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json`,
  `cities/texarkana.json` and `cities/abilene.json`. The dashboard lists
  metros by name, so it is unchanged.

## Intent

Register the two Texas permit workbooks the one-family pass held: the Excel
client compared their text dates as strings, and the permits producer could
not read Abilene's times.

## Decisions

- 2026-10-02 — Texarkana reads report 370, the permits started in the
  previous calendar month, rather than the daily five-year report 369: 369
  has no permit number, and ids built from its other columns repeated
  (about 1.5% of rows). 370's month lag is accepted, with
  `expected_cadence_days` 35.
- 2026-10-02 — Leave Texarkana's non-building titles out by name, from the
  titles used in the year to 2026-10-02, as Midland's spec does; a new
  title passes until it is added.
- 2026-10-02 — Geocode Texarkana's project addresses (the workbook has no
  coordinates) with ", Texarkana, TX" appended, and keep the clip off: the
  rows are placed when parsed, after the clip.
- 2026-10-02 — Accept Abilene's monthly workbook a month behind, as
  Richmond's monthly transfers are (`expected_cadence_days` 45), clip the
  35 points the vendor placed in other states, and raise the cap to 2,500 so
  a month of storm repairs is read whole.
- 2026-10-02 — Leave the permit taxonomy for its own change: Abilene's new
  homes read as minor alterations and Texarkana's trade permits for new
  construction as new construction.

## Current step

Done.

## Next step

The permit taxonomy change (new homes as new construction; trade permits
not), which also touches Greenville, Laredo, Savannah and Tucson.
