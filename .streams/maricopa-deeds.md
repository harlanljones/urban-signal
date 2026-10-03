# Stream log — maricopa-deeds — 2026-09-30

## Claim

- **Stream id:** `maricopa-deeds`
- **Leaf files created/edited:**
  - corpus files `tempe.yaml`, `chandler.yaml`, `scottsdale.yaml`,
    `glendale_az.yaml` (a `deeds` spec each) and `phoenix.yaml` (its `deeds`
    spec moves from the affidavits file to the parcel layer)
  - `producers/watermarks.py` (`gis.mcassessor.maricopa.gov` joins
    `ANSI_DATE_LITERAL_HOSTS`)
  - tests: `test_maricopa_deeds.py` (new),
    `test_producers_enforcement_signals.py`, `test_scheduler_boundaries.py`,
    `test_snapshot_reach.py`, `test_deeds_party_names.py`
  - notes added to `docs/research/deeds-probe-2026-09-30.md`,
    `snapshot-reach-2026-09-30.md`, `four-family-depth-2026-09-30.md`,
    `feed-health-2026-09-30.md`, `probe-maricopa-sales-affidavits.md` and
    `wave-3-probe-phoenix.md`, this file, `.streams/dispatch-log.md`
- **Spine files touched:** `config.py`, one setting for the parcel layer and
  a note on the affidavits endpoint. `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/{chandler,glendale_az,phoenix,scottsdale,tempe}.json`. The
  dashboard lists metros by name, so it is unchanged.

## Intent

Register Tempe's deeds from the Maricopa County Assessor's parcel layer, the
next step `deeds-wave` named, and move Phoenix deeds to the same layer. The
layer covers the county, so Chandler, Scottsdale and Glendale gain deeds too.

## Decisions

- 2026-09-30 — One spec shape for all five: `JURISDICTION = '<city>'` and
  deeds dated in the 90 days before each poll, up to now, read whole every
  six hours with a composite id of `APN`, `DEED_DATE` and `DEED_NUMBER`.
  The server evaluates the relative dates, so a poll sends no date literal.
- 2026-09-30 — The upper bound stays: 173 deeds in the five cities are dated
  2044 to 2099.
- 2026-09-30 — Phoenix's affidavits file is no longer registered (it
  dead-lettered every row). Its setting and the leaf field map stay as a
  candidate.
- 2026-09-30 — Phoenix's metro box is unchanged. 33 of its 9,224 deeds lie
  just north of it along I-17, inside the city; they publish.
- 2026-09-30 — `expected_cadence_days: 14`: the newest full day trails by
  about two weeks and the layer loads about weekly.

## Current step

Done.

## Next step

Bend deeds from Deschutes County `GIS_SALES`, joined to the taxlot polygons
and filtered to Bend.
