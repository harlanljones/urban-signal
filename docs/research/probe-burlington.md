# Wave 3 Phase-0 probe — Burlington, VT

**Date of probe: 2026-08-27.** Ticket US-316. Public ArcGIS Hub
(`burlingtonvt.opendata.arcgis.com`, 254 catalog items); every row read live
that day.

## Headline verdict

**T3 — the OpenGov permit extracts are FROZEN; 311/SLA/deeds absent. REJECT
/ defer (re-probe candidate).** The Hub is public and healthy, and the
permits family has excellent Tier-1 *shape* (native lat/lng 500/500, permit
ids, addresses) — but the OpenGov→ArcGIS sync died: all three extracts share
one identical ETL stamp, `DataUpdateDate` max **2026-04-27T01:01:24Z**, four
months before the probe. Newest permit status is also 2026-04-27. Frozen =
Tier 3 under the wave-3 tier definitions.

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| PERMITS | `services1.arcgis.com/1bO0c7PxQdsGidPK/.../OpenGov_Building/FeatureServer/0` (+`OpenGov_Zoning/0`, `OpenGov_Fire_Marshal/0`) | `StatusDate` max **2026-04-27T02:54:30Z** (DECK-26-11); `DataUpdateDate` max 2026-04-27T01:01:24Z | **native `Latitude`/`Longitude` 500/500 newest** + `StreetAddress` 490/500; point geom, WKID 4326 | newest 2026-04-27; extract frozen since | **3** (frozen) |
| 311 | none. `q=311` → **0**. "Things to Change Reports" = complaint subset, newest `SUBMITDT` **2018-09-19** | n/a | n/a | n/a | **3** |
| SLA | none. `q=license` / `q=business` → 0 relevant | n/a | n/a | n/a | **3** |
| DEEDS | none. `Property_Taxes` FeatureServer has **0 layers**; `Parcels` is assessment snapshot; no sales/deed datasets | n/a | n/a | n/a | **3** |

## Platform

Resolved: **ArcGIS Hub (public, 254 DCAT items) + one AGOL org**
(`services1.arcgis.com/1bO0c7PxQdsGidPK`). Socrata: `Domain not found` for
`burlingtonvt.opendata.arcgis.com`. Not CKAN.

OpenGov is the permitting system of record (`OpenGov Zoning and Zoning
Certificates of Occupancy Application & Permits`, `OpenGov Fire Building and
Trades Applications and Permits`, `OpenGov Fire Marshal Applications and
Permits`, plus a shell `OpenGov ROW Permits` layer whose fields are
`COL_A`-style placeholders). The four FeatureServices are the OpenGov
extracts.

## Permits detail (why frozen, why re-probe)

- `OpenGov_Building/0`: **141,701 rows**, point, `maxRecordCount` 1000.
- Columns: `RecordId`, `Department`, `RecordType`, `ProjectName`,
  `Description`, `ApplicationDate`, `PermitNo` (e.g. `CBP-26-322`,
  `DECK-26-11`), `PermitStatus`, `WorkflowStep`, `StreetAddress`,
  `StatusDate`, `ContractorOrOrganizationName`, `DateCompleted`,
  `PublicUrl`, `Latitude`, `Longitude`, `DataUpdateDate`,
  `EstimatedConstructionCost`.
- Newest rows (2026-04-27) are `Open` applications; native lat/lng
  44.5/−73.3 (Burlington) on 500/500.
- `DataUpdateDate` max is byte-identical (`2026-04-27T01:01:24Z`) across
  Building, Zoning, and Fire Marshal — a dead ETL run, not a citywide permit
  stoppage.
- If the sync resumes: **Tier 1 shape** (native geocode + address + id).
  Register then; do not register a frozen 4-month extract.

## Other families

- 311: no citywide service-request dataset. `HealthProblemReports`
  ("Things to Change Reports": `LOCDESC`, `PROBTYPE`, `SUBMITDT`, `STATUS`)
  is a narrow complaint form, newest **2018** — archive.
- SLA/licenses: nothing on the Hub; Burlington licensing runs inside OpenGov
  (UI only, no anonymous bulk feed).
- Deeds: no transaction stream. `Property_Taxes` service is empty;
  parcel layers carry assessment attributes, no sale date/price.

## Method, and its limits

Hub OGC collections search (`/api/search/v1/collections/dataset/items`,
254 matched) with family keywords; AGOL item→URL resolution; layer
metadata; `outStatistics` max + `orderByFields=<watermark> DESC` newest-row
reads; 500-row geocode completeness; count-only reads. Limits: the Hub
search v1 legacy `results` shape is gone — only the OGC collections endpoint
works; `OpenGov_ROW_Permits` rejects `orderByFields` queries (generic shell
layer). No statewide VT feed was treated as a Burlington substitute.

## Decision

**Do not register now.** Re-probe the three OpenGov extract services
(≤72 h before any implementation wave): if `DataUpdateDate` exceeds the
2026-04-27 stamp, Burlington flips to Tier 1 permits with native geocode.
Stamp: 2026-08-27.
