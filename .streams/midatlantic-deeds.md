# Stream log — midatlantic-deeds — 2026-09-30

## Claim

- **Stream id:** `midatlantic-deeds`
- **Leaf files created/edited:**
  - dataset blocks in `albany`, `allentown`, `burlington`, `charleston_wv`,
    `dover`, `frederick`, `harrisburg`, `huntington_wv`, `manchester`,
    `portland_maine`, `providence` and `wilmington_de` `.yaml`
  - the same twelve leaf modules: deeds mirrors and docstrings, and
    `compose_deed_date` in `allentown.py`; `cincinnati.py` (its sale-date
    composer moved here from the deeds producer)
  - clients outside the spine: `arcgis_client.py` (sends `select` as
    `outFields`), `acquisition.py` (forwards `select` to ArcGIS),
    `watermarks.py` (the Kanawha County host)
  - tests: `test_midatlantic_deeds.py` (new), `test_arcgis_client.py`,
    `test_producers_snap.py`, `test_snapshot_reach.py`
  - `docs/research/feed-health-2026-09-30.md`,
    `docs/research/snapshot-reach-2026-09-30.md`, product facts
    (`facts:export`), this file, `.streams/dispatch-log.md`
- **Spine files touched (one hold):** `apps/api/src/config.py` (five deeds
  endpoints repaired, seven removed, Frederick's renamed to
  `socrata_frederick_deeds_endpoint`),
  `apps/api/src/producers/deeds_acris_producer.py` (a leaf `compose_deed_date`
  hook replaces Cincinnati's special case; Frederick SDAT rows autodetect).
- **Generated surfaces:** `apps/product/public/facts.json` and the twelve
  cities' `cities/*.json`.

## Intent

None of the 14 mid-Atlantic `deeds` feeds registered on 2026-09-06 ever
pointed at a live source. Repair the ones with a published last-sale or
transfer layer, retract the ones whose city publishes no sales anywhere, and
give each retracted city the SNAP retailer `sla` slice so it still polls a feed.

## Decisions

- 2026-09-30 — Repair Frederick (MD SDAT, Socrata `gx8c-a963`), Providence
  (the city's Parcels with CAMA layer), Burlington (VCGI Vermont Property
  Transfers, town 114), Allentown (the city's Tax Parcels Assessed layer) and
  Charleston WV (Kanawha County Assessor parcels, districts 09 to 14). Each was
  polled live through `poll_job` at its production cap before it landed.
- 2026-09-30 — Retract Albany, Dover, Harrisburg, Huntington, Manchester,
  Portland ME and Wilmington DE `deeds`: their county and state layers carry
  deed book and page at most, and the sales searches that exist are
  interactive sites. Each city gets `snap_sla_spec(state, metro_bbox)`.
  Wilmington's retraction is provisional: the county's `PropertySales`
  MapServer answers HTTP 472 to this network and could not be checked.
- 2026-09-30 — Never map an owner, grantor or buyer name. ArcGIS feeds list
  their columns in `select` so those columns stay on the server; Frederick's
  grantor column is read (Socrata has no `select` in this client) and never
  mapped.
- 2026-09-30 — Split sale dates are composed by the city leaf
  (`compose_deed_date`), not special-cased in the spine producer.
- 2026-09-30 — Burlington is incremental on `postedDate`, not `closeDate`,
  because late-posted returns would fall behind a closing-date cursor.
- 2026-09-30 — Roanoke (needs the parcel join in `poll_job`) and Richmond
  (needs an `.xlsx` reader and a monthly URL) stay registered and failing.

## Current step

Done.

## Next step

The scheduler-semantics change in the feed-health note's "Found along the
way", which also unblocks Roanoke through the parcel join in `poll_job`.
