# Stream log — yakima-311-deeds — 2026-10-02

## Claim

- **Stream id:** `yakima-311-deeds`
- **Leaf files created/edited:**
  - corpus file `yakima.yaml` (a `311` and a `deeds` spec);
    `cities/yakima.py` (the module notes and dropped columns);
    `producers/watermarks.py` (the host takes ANSI literals)
  - tests: `test_yakima_311.py` and `test_yakima_deeds.py` (new);
    `test_producers_yakima.py` (a leaf-mirror test renamed)
  - notes in `docs/research/two-family-depth-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the request and parcel layers).
  `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/yakima.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register what the western group's probe verified for Yakima, its fastest
route to all four families.

## Decisions

- 2026-10-02 — List the whole host in `ANSI_DATE_LITERAL_HOSTS`: the
  permits layer, which took ISO strings on 2026-08-28, now rejects them as
  the request layer does, and every permits poll after the first was
  failing.
- 2026-10-02 — Keep the request layer's fixed Pacific Standard Time for
  literals although its values are local clock times: literals and values
  then match exactly, and the summer hour's lead only holds the watermark
  back until the newest requests are past.
- 2026-10-02 — Read the parcels' text sale dates through a server-side cast
  in a 90-day snapshot instead of a text watermark: sales arrive about nine
  days late and part-days fill in afterwards, which a watermark that moved
  past a day would miss.

## Current step

Done.

## Next step

Register the other western deeds (Aurora, Boulder, Fort Collins, Salem,
Vancouver) and what the Florida and south-eastern groups verify.
