# Stream log — western-deeds — 2026-10-02

## Claim

- **Stream id:** `western-deeds`
- **Leaf files created/edited:**
  - corpus files `vancouver_wa.yaml`, `boulder.yaml`, `fort_collins.yaml`
    and `salem_or.yaml` (a `deeds` spec each) and their `cities/*.py`
    modules (the notes)
  - `csv_client.py` (a plain download is decoded as it is read instead of
    through `response.text`) and `arcgis_client.py` (a layer that names no
    object-id field pages by the field it types as one)
  - tests: `test_vancouver_wa_deeds.py`, `test_boulder_deeds.py`,
    `test_fort_collins_deeds.py` and `test_salem_or_deeds.py` (new);
    `test_csv_client.py`, `test_arcgis_client.py` and
    `test_snapshot_reach.py`; the hand-made responses in
    `test_producers_albuquerque.py`, `test_producers_chattanooga.py`,
    `test_producers_cincinnati.py` and `test_producers_san_diego.py` (they
    now carry the body bytes the client reads)
  - notes in `docs/research/two-family-depth-2026-09-30.md` and
    `snapshot-reach-2026-09-30.md`, this file, `.streams/dispatch-log.md`,
    and dated lines in `.streams/west-vancouver_wa.md`, `west-boulder.md`,
    `west-salem_or.md` and `wave4-aurora.md`
- **Spine files touched:** `config.py` (the four sources). `pytest -m
  interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and the four
  `cities/*.json`. The dashboard lists metros by name, so it is unchanged.

## Intent

Register the deeds the western group's probe verified for Vancouver,
Boulder, Fort Collins, Salem and Aurora.

## Decisions

- 2026-10-02 — Read Clark County's hosted `TaxlotsforPublicUse` layer, not
  the `TaxlotsPublic` MapServer it replaces: the MapServer's portal item is
  marked for deletion on 2026-10-12, and both hold the same rows.
- 2026-10-02 — Read the three county files once a day through the CSV
  client, and decode a plain download as it is read: `response.text` held
  Larimer County's 101 MB file again as text, twice while httpx joined it,
  and added 385 MB to the read's peak; the streamed read adds 1 MB and yields
  the same rows.
- 2026-10-02 — Join Larimer's sales on the schedule number, not the parcel
  number: condominium units share a parcel number, and the layer holds one
  parcel per schedule number.
- 2026-10-02 — Page a layer that names no object-id field by the field it
  types as one: Larimer's parcels call theirs `OBJECTID_1`, and a page
  ordered by `OBJECTID` answered 400.
- 2026-10-02 — Close each file's window at today: Boulder's file carries
  eight rows dated as far as 2057 and Salem's three in November and December.
- 2026-10-02 — Map Salem's 2026 and 2027 files by year and fall back to the
  2026 file while the 2027 one is missing; sales of late December posted
  after the turn are not read.
- 2026-10-02 — Hold Aurora: Arapahoe County's parcels carry sales about
  eight weeks after their date, and Adams County's daily table covers only
  the city's Adams side.
- 2026-10-02 — Caps from the busiest 90 days found (Vancouver 4,221, Boulder
  4,334, Fort Collins 4,337, Salem 3,092); cadences from the newest sale's
  age (21, 14, 21 and 14 days).

## Current step

Done.

## Next step

None for these four metros' deeds. Aurora's deeds wait on Arapahoe posting
sooner or a feed that reads two counties; none of the five has a `311`
source.
