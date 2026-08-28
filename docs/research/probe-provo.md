# Wave 3 Phase-0 probe — Provo, UT

**Probe stamp: 2026-08-27.** Every host, dataset, watermark, and row below was
read live that day. DCAT `modified` is a label only; freshness evidence is
newest-row-by-watermark.

Linear: **US-332**. Ticket hint was ArcGIS Hub + EnerGov
(`city-of-provo.opendata.arcgis.com`).

Success criterion (Wave 3 / ADR 0004): live **and** (native geometry **or**
address-geocodable). Tiers: **1** live + native geocode; **2** live +
address-only; **3** stale / absent / wrong family.

## Platform

| Host | What it is | Probe |
|---|---|---|
| `city-of-provo.opendata.arcgis.com` | ArcGIS Hub **"Provo Open Data"** — live site, DCAT feed `/api/feed/dcat-us/1.1.json` = **32 datasets** | all titles enumerated |
| `maps.provo.org` | city web/GIS host | `/arcgis/rest/services`, `/server/rest/services`, `/portal/rest/services` all **404**; no REST directory found |
| `opendata.gis.utah.gov` | Utah AGRC state Hub | `q=provo permit` → **0** |
| EnerGov (Tyler) | ticket hint; `citizenaccess/selfservice/energov.provo.org` all fail DNS | no bulk surface |
| `opendata.utah.gov` | (prior note: 404) | still down |

## Summary

| Family | Tier | Newest watermark | Geocode | Register? |
|---|---|---|---|---|
| Permits | **3** — no permit dataset on Hub (32 items, all reference) | n/a | n/a | **no** |
| 311 | **3** — no dataset; no Open311 found | n/a | n/a | **no** |
| SLA | **3** — no license dataset | n/a | n/a | **no** |
| Deeds | **3** — Utah County recording; no transaction stream | n/a | n/a | **no** |

**Wave-3-ready: no.** Register nothing.

## Evidence

- Full DCAT title list (32): Annexation Policy (2), school boundaries (2),
  CH/ADU/SOB/STR/TDR Overlays, Zoning, Neighborhoods, Cemetery Blocks/Lots/
  Burials, General Plan, Neighborhood Districts, Permit Parking Areas,
  Council Districts, Parking Facilities, Historical Buildings, Major/Local
  Street Plan, Sanitation Pickup Areas, Subdivisions, Bike Lanes, Address
  Points, Buildings, Bike Parking, Provo Streets, Park Amenities, Trails,
  Trailheads, Parks. **Zoning/overlay/reference only** — "Permit Parking
  Areas" is parking-district boundaries, not permit records; "Short-Term
  Rentals Overlay" is a zoning boundary, not STR licenses.
- Site is maintained (Neighborhoods + Parks `modified` = 2026-08-27) — the
  Hub is live but carries no transactional family.
- No 311/licensing/deed feeds anywhere on the Hub or state AGRC.

## Registration contract (`provo`)

None. `get_dataset()` raises for PERMITS / 311 / SLA / DEEDS. Re-probe if
Provo exposes EnerGov records or adds transactional layers to the Hub.
