# Stream log — party-names — 2026-09-30

## Claim

- **Stream id:** `party-names`
- **Leaf files created/edited:**
  - corpus files for the 16 `deeds` specs that mapped `party1_grantor` or
    `party2_grantee` (Anchorage, Asheville, Baltimore, Canton, Chattanooga,
    Cincinnati, Cleveland, Columbus, Durham, Miami-Dade, Montgomery,
    Philadelphia, Phoenix, Prince George's, Raleigh, Tallahassee), and
    `reno.yaml` and `washington_dc.yaml` (a `select` for `deeds`)
  - leaf mirrors `anchorage.py`, `durham.py`, `miami_dade.py`, `phoenix.py`,
    `tallahassee.py` and `apps/api/src/producers/asheville_deeds_spec.py`
  - tests: `test_deeds_party_names.py` (new) and the `deeds` tests of 20
    cities and the Carto client, with people's names in fixtures redacted
  - `docs/research/feed-health-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched (one hold):**
  `apps/api/src/producers/deeds_acris_producer.py` (reads no grantor or
  grantee). `pytest -m interlock` passes.
- **Generated surfaces:** none. No city, feed or endpoint changes, so product
  facts and the dashboard are unchanged.

## Intent

Keep sellers' and buyers' names out of every `deeds` event, the option
recommended on the thread's decision card.

## Decisions

- 2026-09-30 — Remove the names in the producer, not only in the specs: its
  fallback chain read 16 column names from any row, so a spec without a map
  entry still published them.
- 2026-09-30 — Keep `party1_grantor` and `party2_grantee` in the Avro schema
  and the PostGIS columns, always null, so no consumer breaks.
- 2026-09-30 — Give Reno and DC `deeds` a `select`, since their layers carry
  owner names; the other 28 ArcGIS and Socrata `deeds` specs without one are
  left for a sweep that checks each layer's columns live.

## Current step

Done.

## Next step

DC `deeds` joins the Parcel Lots layer, which holds only `PAR` parcels, so it
places 12 of 4,996 sales; then Las Vegas `deeds`, which geocodes the owner's
mailing address.
