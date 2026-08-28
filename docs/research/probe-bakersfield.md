# Wave 3 Phase-0 probe — Bakersfield, CA

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below was
read live that day. Hub `item.modified` is a label only; freshness evidence is
newest-row-by-watermark.

Linear: **US-331**. Ticket hint was ArcGIS Hub + Click2Gov
(`bakersfielddatalibrary-cob.opendata.arcgis.com`).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `bakersfielddatalibrary-cob.opendata.arcgis.com` | ArcGIS Hub ("Bakersfield Data Library") | STAC `/items`: `q=permit` → 3 hits; `q=311` → 0; `q=license` → 1 (Wireless Leases); `q=sale` → 2 |
| `gis.bakersfieldcity.us/webmaps/rest/services` | City ArcGIS Server | 14 folders (Planning has 1 service; General/Cadastre parcels) |
| Click2Gov | ticket hint; `bgate/permits/citizenserve.bakersfieldcity.us` all fail DNS | no bulk surface |

## Summary

| Family | Tier | Newest watermark | Geocode | Register? |
|---|---|---|---|---|
| Permits | **3** — Hub permit items are planning layers, mods 2022; no building-permit feed | n/a | n/a | **no** |
| 311 | **3** — no dataset | n/a | n/a | **no** |
| SLA | **3** — zero license datasets (license-keyword hit = Wireless Leases) | n/a | n/a | **no** |
| Deeds | **3** — Kern County recording; parcels layers carry **no sale-date/price columns** | n/a | n/a | **no** |

**Wave-3-ready: no.** Register nothing.

## Evidence (row-level where it matters)

- Hub items (owner `GIS_Portal_Admin`): `Wireless Leases` (mod 2022-10),
  `Conditional Use Permits` (planning; mod 2022-10), `Signs` (mod 2022-09),
  `Sales Map Lands` (city land-sale parcels, mod 2022-09 — not market
  sales), `Parcels` (mod 2024-03).
- `General/Cadastre/MapServer/1` parcels: 12 fields (`APN_ID`, `ATN_ID`,
  `ADDR_ID`, `DOC_TYPE`, `MAP_NUM`, `PHASE`, `LOT_NO`, `SOURCE`) — **zero
  date fields, no sale columns**.
- Planning REST folder contains only `MakingDowntown`. No permit / case /
  inspection service anywhere in the 14-folder directory.
- Kern County Clerk-Recorder has no anonymous bulk deed/sales API.

## Registration contract (`bakersfield`)

None. `get_dataset()` raises for PERMITS / 311 / SLA / DEEDS. Re-probe if the
city replaces Click2Gov with a feed-bearing portal or publishes permit data to
the Hub.
