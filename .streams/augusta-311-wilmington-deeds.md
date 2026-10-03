# Stream log — augusta-311-wilmington-deeds — 2026-10-02

## Claim

- **Stream id:** `augusta-311-wilmington-deeds`
- **Leaf files created/edited:**
  - corpus files `augusta.yaml` (a `311` spec) and `wilmington_nc.yaml` (a
    `deeds` spec); `cities/augusta.py` and `cities/wilmington_nc.py` (the
    module notes)
  - `arcgis_client.py` (a host's zone for layers that declare none; one page
    from a layer that cannot page)
  - tests: `test_augusta_311.py` and `test_wilmington_nc_deeds.py` (new);
    `test_arcgis_client.py` (the zone and the paging stop) and
    `test_snapshot_reach.py` (the deeds window)
  - notes in `docs/research/two-family-depth-2026-09-30.md` (with the
    south-eastern probe) and `snapshot-reach-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`, and a dated line in `.streams/city-augusta.md`
- **Spine files touched:** `config.py` (the request layer and the parcel
  points). `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/augusta.json` and `cities/wilmington_nc.json`. The dashboard lists
  metros by name, so it is unchanged.

## Intent

Register what the south-eastern probe verified for Augusta and Wilmington,
NC, which each have permits and SNAP retailers: Augusta's requests and
Wilmington's deeds.

## Decisions

- 2026-10-02 — Read Augusta's open Cityworks requests incrementally, one
  request a poll: the server cannot page, so the client now stops after the
  first page on a layer whose metadata says so, instead of asking again
  until its cap.
- 2026-10-02 — Lend `augcw.augustaga.gov`'s layers Eastern time: the server
  reads a zone-less literal as local time without declaring a zone, and the
  scheduler stores watermarks without one.
- 2026-10-02 — Leave out Augusta's utility-locate tickets, subpoena queue
  and crew start entries, about a third of its rows: they are not residents'
  requests.
- 2026-10-02 — Read Wilmington's sales as a 90-day snapshot cast from the
  text dates, with a 4,500-row cap (April to June 2026 held 2,898), and a
  30-day cadence: the layer has no refresh stamp, and its newest sale was
  nine days old.

## Current step

Done.

## Next step

Register the Florida deeds (Gainesville, Lakeland, Ocala, Tampa). Augusta's
deeds wait until the County keys its sales within about a month of closing.
