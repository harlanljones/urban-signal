# Stream log — deeds-wave — 2026-09-30

## Claim

- **Stream id:** `deeds-wave`
- **Leaf files created/edited:**
  - corpus files `nashville.yaml`, `hartford.yaml`, `denver.yaml` (a `deeds`
    spec each)
  - tests: `test_producers_nashville.py`, `test_producers_hartford.py`,
    `test_producers_denver.py`, `test_scheduler_boundaries.py`,
    `test_snapshot_reach.py`, `test_deeds_party_names.py`
  - `README.md` (the three deeds cells),
    `docs/research/deeds-probe-2026-09-30.md` (new), notes added to
    `snapshot-reach-2026-09-30.md`, `four-family-depth-2026-09-30.md`,
    `wave-3-feed-expansion.md`, `data-coverage-sweep-2026-08-25.md` and
    `northeast-new-england-expansion-probe-2026-08-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py`, four settings: the three deeds
  endpoints and Hartford's parcel layer. `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/{denver,hartford,nashville}.json`. The dashboard lists metros by
  name, so it is unchanged.

## Intent

Give the 22 metros that miss only deeds a deeds feed where a public source
exists. Two read-only research workers probed all 22 live; register the
sources that need no client change.

## Decisions

- 2026-09-30 — Nashville, Hartford and Denver register; Tempe, Bend, Medford
  and Tacoma have sources that need client work; Minneapolis and San Diego
  are held; thirteen have no source (table in the research doc).
- 2026-09-30 — Each reads its source's last sale per parcel, filtered to the
  90 days before each poll and read whole every six hours. The id joins the
  parcel, the sale date and the instrument, so a resale is new to the
  snapshot.
- 2026-09-30 — Denver reads the parcel layer's own sale fields. The sales
  table's `PARID` has lost `SCHEDNUM`'s leading zeros (0 of 200 match as
  sent, 198 of 200 padded), and the parcel join cannot pad a key.
- 2026-09-30 — Hartford's CAMA table has no geometry; its sales take their
  parcel's centroid through a `parcel_join` on `ParcelNumber`. The table's
  `City`, `State` and `Zip10` are the owner's mailing address and stay off
  the request.
- 2026-09-30 — Hartford `expected_cadence_days: 14`: the table has no edit
  stamp, so its load rhythm is unobserved.

## Current step

Done.

## Next step

Register Tempe from the Maricopa Assessor parcel layer and move Phoenix
deeds to it (`gis.mcassessor.maricopa.gov` joins `ANSI_DATE_LITERAL_HOSTS`).
