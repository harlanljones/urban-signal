# Stream log — city-shreveport — 2026-08-30

## Claim

- Stream id: city-shreveport (US-267)
- Ticket hint: parish/city permits (Caddo GIS), pop ~385K, Fit Medium.
- Outcome: **REJECT — no leaf.** All four families Tier 3. No spine touch
  claimed or made.

## Intent (planned)

Onboard Shreveport, LA as a new South Central metro (CityId.shreveport) with
a verified transactional feed. This never reached the build stage.

## Decisions

- 2026-08-30 — LIVE probe. City AGOL org (`services3.arcgis.com/cEsSI6IR59h5UGE4`)
  is **reference-only (1107 items)**; Caddo Parish Public Works org
  (`services1.arcgis.com/ekpaOXhC7fFWoTJ9`) is **reference-only (16 items)**.
- 2026-08-30 — PERMITS **Tier 3**: no permit layer. City case-index layers
  (`MPC_CASE_INDEX` layer 2, `ZBA_CASE_INDEX` layer 4, `PZC_CASE_INDEX`
  layer 1) carry case number/type but **no DATE field**; PZC has only
  `USER_Year` (year integer, no watermark).
- 2026-08-30 — 311 **Tier 3**: Port City 311 = QScend
  (`shreveportla.qscend.com/311/request/add`) — login-gated
  (`account/signin`+`signup`), no public bulk list/API/watermark;
  `/311/feed/notices` is notices only.
- 2026-08-30 — SLA **Tier 3**: `Liquor Stores` / `LiquorStores_Oct4_2022`
  static Oct-2022 point snapshot, no date/watermark.
- 2026-08-30 — DEEDS **Tier 3**: Caddo Assessor parcels on DataScout
  (`actdatascout.com/RealProperty/Louisiana/Caddo`) — free search is
  per-parcel GUI; transaction histories + mapping are **Pro paid ($35/mo +
  $10 map)**; no open bulk/API/watermark. Third-party Caddo parcel/sales
  services are non-municipal/stale.
- 2026-08-30 — `gis.shreveportla.gov`, `gis.caddo.org`, `gis.caddo.gov`,
  `maps.caddo.org` all **DNS fail**; no self-hosted ArcGIS Server. No
  Socrata/CKAN host (`data.shreveportla.gov`, `opendata.louisiana.gov`,
  `data.louisiana.gov` all 000).

## Spine delta (NOT applied — informative only, would have been:
CityId.shreveport + REGISTRY + ALIASES + METRO_META + dashboard byte-sync;
config.py endpoint settings for the verified feed; feed specs from a leaf
`get_shreveport_dataset`)

## Files

- `docs/research/probe-shreveport.md` (REJECT doc, stamp 2026-08-30)
- Leaf files NOT created: `apps/api/src/spatial/cities/shreveport.py`,
  `apps/api/src/producers/field_maps_shreveport.py`,
  `apps/api/tests/unit/test_producers_shreveport.py`

## Current step

Reject. Ticket stays in Backlog / needs-triage for a future re-probe. No
commit, no Linear mutation.

## Next step

None. Re-probe if the city publishes permit records or a 311 export, or the
Parish assessor/Clerk of Court lands an anonymous bulk parcel/Sales stream.
