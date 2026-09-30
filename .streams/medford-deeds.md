# Stream log — medford-deeds — 2026-09-30

## Claim

- **Stream id:** `medford-deeds`
- **Leaf files created/edited:**
  - corpus file `medford.yaml` (a `deeds` spec); the module note in
    `cities/medford.py`
  - `src/producers/tolerant_http.py` (new), `arcgis_client.py` (requests go
    through it), `watermarks.py` (the county host takes ANSI literals)
  - `scripts/feed_staleness_probe.py` (its metadata request goes through
    `tolerant_http.get`)
  - tests: `test_medford_deeds.py` and `test_tolerant_http.py` (new),
    `test_scheduler_boundaries.py`, `test_snapshot_reach.py`,
    `test_deeds_party_names.py`
  - notes added to `docs/research/deeds-probe-2026-09-30.md`,
    `snapshot-reach-2026-09-30.md` and `four-family-depth-2026-09-30.md`,
    this file, `.streams/dispatch-log.md`
- **Spine files touched:** `config.py` (the sales layer). `pytest -m
  interlock` passes.
- **Generated surfaces:** `apps/product/public/facts.json` and
  `cities/medford.json`. The dashboard lists metros by name, so it is
  unchanged.

## Intent

Register Medford's deeds from Jackson County's `PropertySales` layer, the
next step `bend-deeds` named. No httpx request to the county's server
completed.

## Decisions

- 2026-09-30 — Read the county's server through the standard library for
  listed hosts, not by patching h11 or the byte stream: the server sends
  `Content-Security-Policy : ...` (a space before the colon), h11 rejects it,
  and `http.client` loses every header after it unless its header lines are
  fixed as they are read. Callers still get `httpx.Response` objects.
- 2026-09-30 — List the host (`TOLERANT_HEADER_HOSTS`) rather than falling
  back on the error, so no request is sent twice.
- 2026-09-30 — Keep `SiteCity = 'MEDFORD'` (the city), not `MEDFORD/COUNTY`
  (unincorporated land with Medford addresses), and no `metro_clip`: the city
  feeds cover the city, and the one sale just east of the box is in it.
- 2026-09-30 — Ids join `AccountId` (the layer's per-account key),
  `SalesDate` and `DocumentNumber`: a sale can cover several accounts (304
  rows carried 291 document numbers).

## Current step

Done.

## Next step

Tacoma deeds (Pierce County's headerless pipe-delimited `sale.zip`, joined to
`Tax_Parcels`, kept to the box with `metro_clip`).
