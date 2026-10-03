# Stream log — richmond-crime — 2026-09-30

## Claim

- **Stream id:** `richmond-crime`
- **Leaf files created/edited:**
  - corpus file `richmond.yaml` (the crime block) and its mirror
    `richmond.py` (`CRIME_FIELD_MAP`, `CRIME_POINT_DECIMALS`,
    `RICHMOND_CRIME_ENDPOINT`, the crime feed spec)
  - `apps/api/src/producers/crime_incidents_producer.py`: a leaf's
    `CRIME_POINT_DECIMALS` rounds each point before it is indexed; simple
    assault is Part 2 in either word order
  - tests: `test_producers_richmond.py`, `test_producers_crime.py`,
    `test_snapshot_reach.py`
  - `docs/research/probe-richmond.md` (crime addendum),
    `docs/research/snapshot-reach-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched (one hold):** `apps/api/src/config.py` (the
  `arcgis_richmond_crime_url` settings field the interlock gate requires).
- **Generated surfaces:** none. Product facts list only permits, 311, SLA
  and deeds, so `facts:export` leaves them unchanged.

## Intent

Give Richmond a crime feed. The city publishes none and Henrico's terms
forbid commercial use; Chesterfield County's police offenses layer covers the
county's part of the metro box.

## Decisions

- 2026-09-30 — Round each point to three decimal places (about 100 m), the
  option recommended on the thread's decision card: the county masks the
  address to its hundred block but publishes the point unsnapped. The
  rounding lives in the crime producer behind a leaf constant, so no spine
  field is needed and every other city keeps its points.
- 2026-09-30 — A snapshot of the last 120 days rather than a watermark:
  `RecordDate` is the occurrence date and reports arrive up to 118 days late.
- 2026-09-30 — `IncidentorOffenseGenCategory` as the offense type (28
  categories); the `select` leaves `DimLocationAddress` and the county's
  coordinate columns behind.
- 2026-09-30 — Fix the simple-assault rule in the shared classifier rather
  than map Richmond's label: Boston and Chicago write simple assault the
  other way round too, and the rule already meant them to be Part 2.

## Current step

Done.

## Next step

The owner and party names in `deeds` (decision card).
