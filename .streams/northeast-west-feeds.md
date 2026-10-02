# Stream log — northeast-west-feeds — 2026-10-02

## Claim

- **Stream id:** `northeast-west-feeds`
- **Leaf files created/edited:**
  - corpus files `lincoln.yaml` and `manchester.yaml` (a `deeds` spec each)
    and `tucson.yaml` (a `permits` spec), and their `cities/*.py` modules
    (the notes)
  - tests: `test_lincoln_deeds.py`, `test_manchester_deeds.py` and
    `test_tucson_permits.py` (new); `test_snapshot_reach.py`
  - notes in `docs/research/one-family-depth-2026-10-02.md` and
    `snapshot-reach-2026-09-30.md`, this file and `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the three sources). `pytest -m
  interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and the three
  `cities/*.json`. The dashboard lists metros by name, so it is unchanged.

## Intent

Register the feeds the north-eastern and western groups of the one-family
probe verified: deeds for Lincoln and Manchester NH, and permits for Tucson.

## Decisions

- 2026-10-02 — Window Lincoln's sales on the recording date, keyed on the
  instrument number alone: the two numbers that repeat in the window are the
  same sale listed twice, parcel, price and day alike.
- 2026-10-02 — Read Manchester's parcels as a 90-day window on the cast sale
  date, not a watermark: the assessor posts sales two to four weeks after
  they close, and a watermark would pass over them. `expected_cadence_days`
  21, so the alarm waits six weeks.
- 2026-10-02 — Leave out the 58 Manchester parcels the City keeps off its
  internet maps (`Suppress_Internet_Access = 'Yes'`), though none had a sale
  in the window.
- 2026-10-02 — Read Tucson's residential layer (`PermitsCode/MapServer/85`)
  alone: one source per spec, and the commercial layer holds a quarter as
  many permits. Keep the work class ahead of the type for the job type,
  though neither names the model permits and new dwellings as new
  construction to the job type codes.
- 2026-10-02 — Accept the clip of Tucson's southern and south-eastern
  annexations (about a fifth of the permits): widening the metro box would
  change its grid tiles, which belongs in its own change.
- 2026-10-02 — Hold Pima County's yearly sales files (a sale year spans two
  files, and the CSV client reads one fixed file), Long Beach's requests (a
  composite `lat, lon` point), Buffalo's holes-in-road work orders (one kind
  of request), Manchester's public works tickets (resident intake stopped
  after 2026-09-02), Buffalo's 2026-27 roll (no deed dates), Polk County's
  sales file (66 days stale) and Sonoma County's parcel sales (about 145
  days behind).
- 2026-10-02 — Caps from the busiest 90 days found (Lincoln 1,371, Tucson
  1,329); Manchester's 735 fits the default 1,000.

## Current step

Done.

## Next step

None for these three feeds. The held sources wait on the re-checks or the
client changes named in the research note.
