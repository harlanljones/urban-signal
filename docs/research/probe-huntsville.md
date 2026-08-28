# Wave 3 Phase-0 probe — Huntsville, AL (US-344)

**Date of probe: 2026-08-27/28.** Row-level ArcGIS reads (`query` ordered
by watermark DESC / windowed `returnCountOnly`). Catalog dates ignored.

**Verdict: REGISTER (partial, with a freshness caveat).** Building
permits are registerable (Tier 2 — native points + address, but the
updater went quiet 20 days before the probe; batch cadence undocumented).
311/SLA/deeds are Tier 3. The ticket hint (`maps.huntsvilleal.gov`) is
correct: a current ArcGIS Server 11.5 with a `Licenses` folder.

Platform: **ArcGIS Server** at
`https://maps.huntsvilleal.gov/server/rest/services` (39 folders,
currentVersion 11.5) plus AGOL org `FsRunHWuiGXWVv3B`
(`huntsvilleal.opendata.arcgis.com`, 150 items — reference layers
only; DCAT feed path absent on the site). Not Socrata, not CKAN.

---

## Method, and its limits

1. Hostname fingerprint: `maps.huntsvilleal.gov` (`/server` root live;
   `/arcgis` root empty), `data.huntsvilleal.gov` (DNS fail), Hub site
   `huntsvilleal.opendata.arcgis.com` (public, no items of interest).
2. Full REST folder walk (39 folders → services). Family-relevant
   folders: **Licenses** (`BuildingPermits`, `AlcoholBeverageLicenses`,
   `LiquorLicenses`), CommunityDevelopment (`ComcateAddresses`),
   CityServices (`MyHuntsvilleServices`), Planning
   (`PropertyData`, `FindAProperty`), Inspections (folder empty).
3. AGOL org keyword sweep (permit / 311 / request / license / sales /
   deed): zero transactional items.
4. Row-level on every survivor: fields, counts, newest watermark row,
   weekly window counts, `outSR=4326` geometry check.

Limits: Huntsville's permit system of record is behind the city
network; the MapServer is the public mirror. Comcate is the city's
code-enforcement/311 CRM; only an address lookup layer is published,
not the case data. Madison County (deeds) has no discoverable REST
host — county probate/courts are UI-only.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `maps.huntsvilleal.gov/server/rest/services/Licenses/BuildingPermits/MapServer/0` | `Permit_Issue_DateTime` = **2026-08-07** | native points (`Shape`, outSR=4326 verified) + `Address` | 7d **0**; Aug **38**; 60d **291**; total **18,448** | **2** (cadence caveat) |
| **311** | Comcate CRM — no public case layer (`MyHuntsvilleServices` is a facility finder) | n/a | n/a | n/a | **3** |
| **SLA** | `Licenses/AlcoholBeverageLicenses/MapServer/0` (971 rows, live to 2026-08-10) | — | points + address | — | **3** (wrong grain: state ABC alcohol licenses, not occupational) |
| **DEEDS** | none — Madison County probate/courts UI only | n/a | n/a | n/a | **3** |

---

## Permits — Tier 2 (register with re-probe gate)

`Licenses/BuildingPermits/MapServer` layer 0 `BuildingPermits` —
18,448 rows; sibling layer 1 `OccupancyCerts` (2,335+ rows).

- Columns: `PermitID` (numeric 696158…), `Permit_Issue_DateTime`,
  `Address`, `AddressID`, `OccupancyType` (Single Family /
  Commercial), `OccupancySubtype`, `TypeOfWork` (New Construction /
  Addition / Alteration / Demolition), `DemolitionType`,
  `NumberOfUnits`, `BuildingSize`, `ContractAmount`, `ActualCost`,
  `CensusTract`, `CouncilDistrict`, `Subdivision`, `Shape` (point).
- Watermark **`Permit_Issue_DateTime`** (date-typed). Newest row
  2026-08-07 (~19:39Z): 7501 Chadwell Rd SW, Addition, $5,000, native
  WGS84 (−86.5722, 34.6842) via `outSR=4326`.
- **Cadence caveat (the honesty clause):** weekly-ish batches of
  ~37–57/week through Jul 21, then 37 the week of Jul 28, 4 on Aug 4–7
  — and **0 rows after Aug 7** on an Aug 27 probe (7d=0). This fails
  the 7-day staleness gate as probed. It is either an ETL lag or a
  halted updater; the layer was current 3 weeks prior. Treat like the
  Memphis monthly-cadence precedent: register only with a documented
  cadence exception **and** re-probe `Permit_Issue_DateTime` ≤72 h
  before build; if still frozen in mid-September, treat as stalled and
  drop to T3.
- Geocoding: native points on the layer itself + `Address` text —
  both present; no ADR 0004 dependency.
- id_keys: `["PermitID"]`.

## 311 — Tier 3

City uses **Comcate** (CommunityDevelopment/ComcateAddresses is an
address master for the CRM). No service-request case layer is
published. `CityServices/MyHuntsvilleServices` is a facilities map
(police, museums, parks). "Huntsville 311" is a phone/app program. No
feed.

## SLA — Tier 3

`Licenses/AlcoholBeverageLicenses/MapServer/0` — 971 rows, points +
address, newest `ApplicationDate` **2026-08-10** (`INDIE AT INDIGO
LLC`). This is the state ABC **alcohol** license register mirrored by
the city — out-of-family grain (not occupational/business licenses;
same call as Memphis `RestaurantInformation`). Occupational licenses
(Huntsville Revenue) have no feed. Do not register; note as adjacent.

## Deeds — Tier 3

No Madison County GIS REST host found (`gis./maps.madisoncountyal.gov`
DNS fail; AGOL shows only third-party layers). Huntsville's own
`Planning/PropertyData` and `FindAProperty` are parcel snapshots, not
sales. Deeds = Madison County Probate — UI only.

---

## Hostnames tried (negatives)

| Surface | Result |
|---|---|
| `data.huntsvilleal.gov` | DNS fail |
| `huntsvilleal.opendata.arcgis.com` | public Hub site, reference layers only |
| `maps.huntsvilleal.gov/arcgis` | empty; `/server` is the live root |
| `Inspections` folder | listed but **empty** |
| Madison County hosts | no REST roots |
| Socrata discovery / CKAN | absent |

## Registration sketch (summary)

`city_registry.py` `HUNTSVILLE.datasets[FeedType.PERMITS]`:
`platform="arcgis"`, endpoint
`https://maps.huntsvilleal.gov/server/rest/services/Licenses/BuildingPermits/MapServer/0`,
watermark `Permit_Issue_DateTime`, id_keys `["PermitID"]`,
`extra={"expected_cadence_days": 7, "cadence_note": "batch updater; stalled-at-probe 2026-08-07 — re-probe gate"}`.
311 / SLA / DEEDS → `get_dataset()` raises.

**Re-probe the watermark ≤72 h before the implementation wave; the
register-now call stands only if rows resume.** Stamp: 2026-08-28.
