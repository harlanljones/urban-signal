# Wave 3 Phase-0 probe — Roanoke, VA (US-314)

**Date of probe: 2026-08-27/28.** Row-level reads (ArcGIS `query` ordered by
watermark DESC / `returnCountOnly`). "Live" means a newest-row read confirmed
fresh data; catalog `modified` and layer `lastEditDate` were ignored.

**Verdict: REJECT (all four families Tier 3).** Roanoke has a real ArcGIS
Server but no registerable transactional feed. The ticket hint
(`roanokeva.opendata.arcgis.com`) is a 10-item Hub placeholder of reference
layers — not a data program.

Platform: **ArcGIS Server** at `maps.roanokeva.gov` (both `/arcgis` and
`/server` roots). Not Socrata (catalog empty; discovery miss). Not CKAN.
Hub site `roanokeva.opendata.arcgis.com` is public (org `KII0S5XRkpE66Ngk`,
owner `roanokeva`, 318 AGOL feature services) but its Hub catalog lists only
10 items, all reference layers.

---

## Method, and its limits

1. Hostname fingerprint: `roanokeva.opendata.arcgis.com` (Hub v3 live),
   `data.roanokeva.gov` (DNS fail), `maps.roanokeva.gov`,
   `gis.roanokeva.gov` (302), Socrata discovery, CKAN `status_show`.
2. AGOL org search `orgid:KII0S5XRkpE66Ngk` (318 services) with
   family keywords (permit / service request / license / sales / deed /
   311): only "ROW Permits" (right-of-way) and internal permit-print
   apps surfaced.
3. ArcGIS Server folder walk: CodeEnforcement (empty), Planning,
   LandRecords (empty), Real_Estate, Public (100+ layers), Utilities,
   and `/server` Hosted.
4. Row-level on every family survivor: fields, `returnCountOnly`,
   newest row by watermark, windowed counts.

Limits: QAlert layer row data may exist behind a secured view — the
anonymous layer advertises schema but returns 0 rows. Roanoke's citizen
requests may exist in the QAlert SaaS itself; no anonymous bulk feed.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `Public/Trakit_20221221/MapServer` (15 reference layers, no permit table) | n/a — snapshot named **2022-12-21** | n/a | n/a | **3** |
| **311** | `Public/QAlertMapping2/MapServer/0` (`QAlertIncidentsProd`) | **count = 0** anonymous (schema only: `sr_*` fields) | `sr_latitude`/`sr_longitude` present in schema | n/a | **3** |
| **SLA** | none found (Hub/AGOL/REST) | n/a | n/a | n/a | **3** |
| **DEEDS** | `/server/rest/services/Hosted/Proval_Transfer_History_Copy/FeatureServer/0` | `pxfer_date` = **2025-10-27**, `last_update` = **2025-11-06** | none on transfers (parcel_id only; parcels layer joinable) | 0 in 2026 | **3** (stale) |

---

## Permits — Tier 3 (frozen TRAKiT snapshot, no extract)

- Roanoke runs **TRAKiT** (`Public/Trakit_20221221` MapServer, layers are
  addresses/streets/parcels reference layers; no permit records table).
- No permit FeatureService anywhere on `maps.roanokeva.gov` (checked
  CodeEnforcement, Planning, LandRecords, Real_Estate, Public, /server
  Hosted) and none in the 318-item AGOL org.
- Citizen-facing TRAKiT / permit application is a UI. Do not register.

## 311 — Tier 3 (QAlert publicly empty)

- `Public/QAlertMapping2/MapServer/0` `QAlertIncidentsProd`:
  fields `OBJECTID, sr_source, sr_sourceID, sr_typeID, sr_typeDesc,
  sr_createDate, sr_updateDate, sr_comments, sr_latitude, sr_longitude,
  sr_status, sr_address`; maxRecordCount 1000.
- `returnCountOnly` on `1=1` → **0 rows** anonymous. Schema is public,
  data is not. `QAlert_HUC_6_Boundaries` / `QAlert_Sub_Watersheds` are
  reference layers.
- Roanoke's "Citizen Support Center" is QAlert SaaS. No open311 JSON
  endpoint found. If the city ever opens the layer, this is a
  same-shape T1 feed (`sr_createDate` + native lat/lng) — re-probe.

## SLA — Tier 3

No business/occupational-license dataset in the Hub catalog (10 items),
AGOL org (keyword sweep), or REST folders. Roanoke licenses via
Commissioner of the Revenue; no feed.

## Deeds — Tier 3 (real table, ~10 months frozen)

`Hosted/Proval_Transfer_History_Copy/FeatureServer/0` — **255,566** rows:
`parcel_id, lrsn, pxfer_date, sxfer_date, owner1, grantee, consideration,
docnum, deed_type, tfrtype, deed_book, deed_page, last_update` (+ hidden
geometry). Newest transfer **2025-10-27**; `last_update` max
**2025-11-06**; **0 transfers in 2026**. Updated annually, not a live
stream. `Hosted/Real_Estate_Master_Copy` (45,573 parcels) is the CAMA
ownership snapshot with addresses but no sale fields.

Watch item: if ProVal transfer history ever refreshes quarterly, this
becomes a T2 deeds candidate (geocode via parcel-address join). Check
`pxfer_date >= date '2026-01-01'` count at next wave.

---

## Hostnames tried (negatives)

| Surface | Result |
|---|---|
| `roanokeva.opendata.arcgis.com` | Hub v3 live, **10 items**, reference layers only |
| `data.roanokeva.gov`, `opendata.roanokeva.gov`, `arcgis.roanokeva.gov` | DNS fail |
| `gis.roanokeva.gov` | 302, no REST listing |
| `maps.roanokeva.gov` /arcgis + /server | Real ArcGIS Server; no permit/311 rows |
| Socrata discovery / catalog | domain not found / 0 |
| CKAN `status_show` | absent |

## Decision

**Reject Roanoke for Wave 3.** All families T3; no registerable feed.
Keep on watch: QAlert layer (if opened) and ProVal transfers (if
refreshed). Stamp: 2026-08-28.
