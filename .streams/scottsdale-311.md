# Stream log — scottsdale-311 — 2026-09-30

## Claim

- **Stream id:** `scottsdale-311`
- **Leaf files created/edited:**
  - corpus file `scottsdale.yaml` (a `311` spec); the module notes in
    `cities/scottsdale.py`
  - tests: `test_scottsdale_311.py` (new)
  - notes added to `docs/research/four-family-depth-2026-09-30.md`, this
    file, `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the request table).
  `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/scottsdale.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register Scottsdale's 311 from the City's ScottsdaleEZ table, the next step
`tacoma-deeds` named, once `maps.scottsdaleaz.gov` answered again.

## Decisions

- 2026-09-30 — Follow `ClosedDate`, not `CreatedDate`: the City publishes a
  request only once it closes, a tenth of them more than 15 days after
  filing, so a filing-date watermark would pass over them.
- 2026-09-30 — Leave rows without a location to `metro_clip` rather than a
  server-side filter. The 4 to 5% without a point read "Data Not Available"
  and would otherwise go to the DLQ, and the poll's query stays the
  watermark comparison alone, the shape the host's permits feed sends.
- 2026-09-30 — Poll every six hours with a 3,000-row cap: the table refreshes
  about weekly (about 1,100 closings a week), and the host blocked a probe's
  burst of requests earlier the same day.
- 2026-09-30 — Keep the dates as the server stamps them (Arizona wall-clock
  time labelled UTC), as the repo does for Socrata's floating timestamps;
  the watermark round-trips in that frame.

## Current step

Done.

## Next step

Pierce County deeds from the same weekly `sale.zip` as Tacoma, county-wide.
