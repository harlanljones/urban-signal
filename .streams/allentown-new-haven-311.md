# Stream log — allentown-new-haven-311 — 2026-10-02

## Claim

- **Stream id:** `allentown-new-haven-311`
- **Leaf files created/edited:**
  - corpus files `allentown.yaml` and `new_haven.yaml` (a `311` spec each);
    `cities/allentown.py` and `cities/new_haven.py` (the module notes)
  - tests: `test_allentown_311.py` and `test_new_haven_311.py` (new),
    `test_arcgis_client.py`, `test_backfill_loader.py`,
    `test_producers_new_haven.py` (a test renamed to say it checks the leaf
    mirror)
  - `producers/arcgis_client.py` (reads coded-value names on request)
  - notes in `docs/research/two-family-depth-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the two request layers),
  `city_registry.py` (`DatasetSpec.decode_domains`), `scheduler.py` (forwards
  it to the ArcGIS client). `pytest -m interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json`,
  `cities/allentown.json` and `cities/new_haven.json`. The dashboard lists
  metros by name, so it is unchanged.

## Intent

Register the `311` sources the probe of the eight north-eastern `sla`-and-
`deeds` metros found, the next step `allentown-permits` named, and record why
the other six stay without requests.

## Decisions

- 2026-10-02 — Read Allentown's coded issue and status as their names through
  a new `decode_domains` spec flag; the ArcGIS client builds the names from
  the layer's coded-value domains with the metadata it already fetches, and
  every other feed reads its values as stored.
- 2026-10-02 — Leave Allentown's department column out: each issue belongs to
  one department, so it adds nothing.
- 2026-10-02 — Follow New Haven's filing time, as every registered `311` feed
  does; of the 500 rows the view received last, two arrived out of filing
  order, by two minutes at most.
- 2026-10-02 — Keep New Haven's requests south of the metro box (the Morris
  Cove shore) rather than clip them.
- 2026-10-02 — Hold Burlington's and Rochester's frozen request exports.

## Current step

Done.

## Next step

Re-check the held exports when they move; SeeClickFix's per-client ArcGIS
views are the route for Bridgeport, Canton and Frederick County if the
platform publishes them.
