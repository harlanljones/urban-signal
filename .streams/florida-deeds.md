# Stream log — florida-deeds — 2026-10-02

## Claim

- **Stream id:** `florida-deeds`
- **Leaf files created/edited:**
  - corpus files `tampa.yaml`, `gainesville.yaml` and `ocala.yaml` (a `deeds`
    spec each); `cities/tampa.py` and `cities/gainesville.py` (the module
    notes) and `cities/ocala.py` (the notes and `compose_deed_date`)
  - `csv_client.py` (a bare `CURRENT_DATE` resolves to today; the title-line
    check reads two rows instead of the whole file)
  - tests: `test_tampa_deeds.py`, `test_gainesville_deeds.py` and
    `test_ocala_deeds.py` (new); `test_csv_client.py` (the two client
    changes), `test_snapshot_reach.py` (the three windows),
    `test_producers_tampa.py` (deeds come from the corpus) and
    `test_wrong_place_permits.py` (Ocala now has deeds)
  - notes in `docs/research/two-family-depth-2026-09-30.md` and
    `snapshot-reach-2026-09-30.md`, this file, `.streams/dispatch-log.md`,
    and dated lines in `.streams/city-tampa.md`, `.streams/city-gainesville.md`
    and `.streams/us-286-lakeland.md`
- **Spine files touched:** `config.py` (the three sources) and
  `deeds_acris_producer.py` (a mapped deed type is stripped of its padding).
  `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/tampa.json`, `cities/gainesville.json` and `cities/ocala.json`. The
  dashboard lists metros by name, so it is unchanged.

## Intent

Register the property appraisers' sales the Florida probe verified for
Tampa, Gainesville and Ocala, and hold Lakeland's until the CSV client can
stream a zip member.

## Decisions

- 2026-10-02 — Read Tampa's sales from the City's copy of the Hillsborough
  County parcels rather than the Property Appraiser's own layer, whose
  newest sale was a week older. 90-day window, cap 10,000 (May to July 2026
  held 6,441), cadence 30 days.
- 2026-10-02 — Read Gainesville's sales from the Alachua County Property
  Appraiser's nightly extract, `Sales.txt` only, placed through the
  Property Appraiser's parcel layer on `prop_id`. 90-day window closed at
  today (a sale is keyed for 2079), cap 6,000, cadence 7 days.
- 2026-10-02 — Read Ocala's sales from the Marion County parcels on the
  City's server, dated the first of their month, over a window of whole
  months the server computes. Leave out the 51 polygons with a sale and no
  parcel number. Cap 15,000, cadence 45 days.
- 2026-10-02 — Hold Lakeland: Polk County's nightly sales member unpacks to
  518 MB, which the CSV client would read whole once a day.

## Current step

Done.

## Next step

Stream a zip member in the CSV client, then register Lakeland's deeds.
