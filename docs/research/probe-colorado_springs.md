# Wave 3 Phase-0 probe — Colorado Springs, CO

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below was
read live that day. Catalog `modified` is a label only; freshness evidence is
newest-row-by-watermark.

Linear: **US-323**. Ticket hint was "Socrata + Accela"
(`data.coloradosprings.gov`).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `data.coloradosprings.gov` | **Socrata** — but only **16 datasets**: Open Budget Revenue/Expense, Capital Projects, Open Checkbook (3), airport traffic, and 10 reference maps. `data.json` = 6 finance datasets. | no family data |
| `policedata.coloradosprings.gov` | separate Socrata subdomain: crime/crash/citation data | wrong family |
| `cosgis.opendata.arcgis.com` | ArcGIS Hub site (HTTP 200, "City of Colorado Springs") | **search index empty** — `matched: None` on all queries; DCAT feed = **0 datasets**; `/api/v3/views.json` 404. Dead/retired Hub. |
| `www.arcgis.com` AGOL org `COSGIS` | 92 items: trash/recycle, imagery, LUC zoning, property reference | reference only |
| Accela | ticket hint; `accela/aca/champ/epermits/permits.coloradosprings.gov` all fail DNS; no ACA host resolvable | no anonymous bulk API surface found |

## Summary

| Family | Tier | Newest watermark | Geocode | Register? |
|---|---|---|---|---|
| Permits | **3** — no open dataset; Accela portal not publicly resolvable | n/a | n/a | **no** |
| 311 | **3** — GoCOS app; no bulk/Open311 found | n/a | n/a | **no** |
| SLA | **3** — zero license datasets on Socrata; Hub empty | n/a | n/a | **no** |
| Deeds | **3** — El Paso County recording; no transaction stream | n/a | n/a | **no** |

**Wave-3-ready: no.** Register nothing.

## Permits — Tier 3

Socrata domain has **zero** permit datasets (16 total, all finance/maps).
CivicData Accela CKAN `package_search?q=colorado springs` → **count=0**.
AGOL search `title:"colorado springs" AND permit` → 0. The Accela hint in the
ticket could not be substantiated: no Citizen Access host answers
(`accela.cosprings.gov` guesses also fail DNS). Development-services pages
that reference Accela are HTML only.

## 311 — Tier 3

GoCOS! is the resident app; no Open311 / bulk CRM endpoint discovered.

## SLA — Tier 3

No license dataset on `data.coloradosprings.gov` or the (empty) Hub.
Colorado state Socrata hits (`4ykn-tg5h` Business Entities, `7s5z-vewr`
Professional/Occupational Licenses) are **statewide Secretary-of-State /
DORA** data, not city SLA — wrong grain for a city registration.

## Deeds — Tier 3

El Paso County Clerk & Recorder has no anonymous bulk deed/sales API. COSGIS
AGOL holds reference parcel layers without sale-date columns.

## Registration contract (`colorado_springs`)

None. `get_dataset()` raises for PERMITS / 311 / SLA / DEEDS. Re-probe if COS
opens an Accela Citizen Access host or repopulates `cosgis.opendata.arcgis.com`.
