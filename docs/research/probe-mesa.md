# Wave 3 Phase-0 probe — Mesa, AZ

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below was
read live that day. Catalog `modified` is recorded only as a label;
**freshness evidence is always newest-row-by-watermark**.

Linear: **US-321**. Ticket hint was Socrata (`data.mesaaz.gov`).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `data.mesaaz.gov` | **Socrata** (domain confirmed via federated catalog `domains=` filter) | domain catalog = **41 datasets** |
| `maps.mesaaz.gov/server/rest/services` | ArcGIS Server | 25 folders; no `/arcgis` path (404s) |
| `mesaaz.hub.arcgis.com` / `mesa.opendata.arcgis.com` | Hub front-ends | not probed further; Socrata + Server are the real surfaces |

Direct-domain `data.mesaaz.gov/api/catalog/v1?limit=…` **falls back to the
federated Socrata catalog** (returns NYC/Missouri noise) — always filter with
`domains=data.mesaaz.gov`.

## Summary

| Family | Tier | Newest watermark | Geocode | Register? |
|---|---|---|---|---|
| Permits | **3** — no dataset exists; chart view only | n/a | n/a | **no** |
| 311 | **3** — MesaNow app, no bulk feed found | n/a | n/a | **no** |
| SLA | **3** — zero license datasets (`q=license` → 0) | n/a | n/a | **no** |
| Deeds | **3** — Maricopa County only; no sale-date stream (per `wave-3-probe-phoenix.md`) | n/a | n/a | **no** |

**Wave-3-ready: no.** Register nothing. Defer; re-probe if Mesa publishes
transactional feeds to `data.mesaaz.gov`.

## Permits — Tier 3 (no dataset)

- Domain catalog (41 datasets) contains **zero** permits datasets. The only
  permit artifact is `jtqq-sfuz` "Commercial Building Permits - By Issue
  Date" — a **`visualization_canvas_chart`** with no underlying resource
  (`columns: []`, no `parent_fxf`). Not queryable.
- Well-known Socrata permits ids (`ydr8-5enu`, `3syk-w9eu`, `ryhf-m453`) are
  **not on the Mesa domain** (404 on `/resource/<id>.json`) — they only appear
  in federated search noise.
- `maps.mesaaz.gov/server/rest/services` `Planning` folder: `Current_Cases_New`
  (ZON/PRS/DRB **Case History** layers), `Projects` — planning/zoning cases,
  wrong family. `Hosted` folder: parcels/redevelopment reference. No building
  permit service.
- Mesa's permit counter (Development Services) has no anonymous bulk API;
  Tyler/EnerGov citizen-portal host guesses
  (`selfservice/energov/citizenportal/permits.mesaaz.gov`) all failed DNS.

## 311 — Tier 3

No `311` / `service request` dataset on the Socrata domain (0 hits).
MesaNow is a resident app with no public bulk / Open311 endpoint found.

## SLA — Tier 3

`q=license` on the domain catalog → **0 results**. No business-license /
STR / liquor feed.

## Deeds — Tier 3

No deed/sale dataset on the Socrata domain. Mesa deeds are Maricopa County
recorded instruments; the county surfaces probed in
`wave-3-probe-phoenix.md` (parcel snapshots without a live sale-date stream)
apply to Mesa equally.

## Registration contract (`mesa`)

None. `get_dataset()` raises for PERMITS / 311 / SLA / DEEDS. Do not register
the permits chart view or the Planning case-history layers.
