# Stream log — lincoln-311 — 2026-10-02

## Claim

- **Stream id:** `lincoln-311`
- **Leaf files created/edited:**
  - corpus file `lincoln.yaml` (a `311` spec); `cities/lincoln.py` (the
    module notes)
  - tests: `test_lincoln_311.py` (new)
  - notes in `docs/research/two-family-depth-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the request layer). `pytest -m
  interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/lincoln.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Read SeeClickFix's own ArcGIS Online org, where New Haven's requests come
from, for other registered metros that lack `311`, and register what fits.

## Decisions

- 2026-10-02 — Register Lincoln's view; of the org's 28 views, it is the only
  other one for a registered metro without requests.
- 2026-10-02 — Follow the view's arrival time (`CreationDate`), not the
  filing time: arrivals follow the object ids, and two of the 1,000 newest
  rows arrived after a request filed 14 minutes later than they were.
- 2026-10-02 — Keep requests outside the metro box: every request in 90 days
  names the City of Lincoln as its agency, and most of the 23 outside lie
  just south of the box.

## Current step

Done.

## Next step

Re-read the org's listing when the depth pass next runs; a new view for a
registered metro without requests registers the same way.
