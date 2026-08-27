# Wave 3 Phase-0 probe: Oklahoma City, OK

**Date of probe: 2026-08-27.** Every host, catalog, watermark, and row below was
probed live that day. Catalog `modified` / Hub item timestamps were never used
as evidence. "Live" means a newest-row read (watermark descending) returned
fresh data. Linear: US-204.

Success criterion (Wave 3, ADR 0004): a feed is registrable if it is *live*
and either natively geocoded **or** address-geocodable. Tier 1 = live + native
geocode; Tier 2 = live + address-only; Tier 3 = stale / no portal / wrong grain.

## Verdict

**Platform: ArcGIS Hub** (new portal) over a custom GIS catalog that is
sunsetting. **Register none. Wave-3-ready: no.** All four families are
**Tier 3**.

The 2026-08-25 south-central re-probe concluded OKC was CLI-unreadable because
`data.okc.gov` sits behind Incapsula. That wall is still real for curl. What
changed: the city now publishes a public ArcGIS Hub at
`open-okc.hub.arcgis.com` (DCAT answers; 81 catalog items, 58 datasets) whose
FeatureServers are queryable anonymously. The Hub does not contain building
permits, 311, business licenses, or market sales. Transactional permits live
in Accela Citizen Access; 311 lives in CitySourced / OKC Connect. Neither
exposes a bulk public API.

Prior PROVISIONAL "Building Permit FeatureServer" remains retracted (Tulsa
County Assessor misattribution, `JfsWgLAOPxX7NGuG` layer 195).

## Method

1. Resolve portal: official city pages (`vision.okc.gov/data`,
   `data.okc.gov`), Hub DCAT, old-portal datasets API (browser session to
   pass Incapsula), Socrata discovery, CKAN probe, AGOL owner search
   `AGOL_Content_OKC`, hosted org `services5.arcgis.com/2mOVdIcRtNH2JsSF`
   (299 FeatureServers enumerated by name).
2. Site-scoped Hub collection search (`/api/search/v1/collections/collectiondm3n84mi/items`)
   — not the unscoped Hub v3 search, which returns the whole ArcGIS Online
   mesh.
3. Row-level verify every family survivor and every near-miss: layer metadata,
   newest-row by watermark DESC, count, geocoding fields. Only newest-row
   reads count.

## Platform

| Surface | What it is | Probe result 2026-08-27 |
|---|---|---|
| `https://open-okc.hub.arcgis.com/` | **Correct portal.** ArcGIS Hub beta replacing `data.okc.gov` (sunset August 2026). Linked as "Beta Site" / "new data.okc.gov" from the old home page and from `vision.okc.gov/data`. | HTTP 200. DCAT ` /api/feed/dcat-us/1.1.json` = **81** items. Dataset collection = **58**. Existing `ArcGISClient` fits published layers. |
| `https://data.okc.gov/` | Legacy custom GIS portal (`/portal/page/start/`). Records API documented at `/portal/page/api` (`/services/portal/api/data/records/[ID]`, `/services/portal/api/datasets/`). | Incapsula challenge to curl (212-byte iframe). Browser session returns the catalog: **113** datasets in 16 groups. Same GIS overlays as the Hub (garage sales, work zones, land documents, zoning, footprints). No permits/311/SLA/deeds families. |
| `oklahomacity-ok.opendata.arcgis.com` | Stale Hub hostname from the 2026-08-25 survey | DCAT 404 "domain record does not exist"; search API 401 "private org id". Dead alias. |
| `okc.maps.arcgis.com` | AGOL org urlKey `OKC` | Portal `access: private`. |
| Socrata | `api.us.socrata.com/api/catalog/v1?domains=data.okc.gov` | `Domain not found`. Not Socrata. |
| CKAN | `data.okc.gov/api/3/action/package_search` | Incapsula HTML, not CKAN JSON. |
| `services5.arcgis.com/2mOVdIcRtNH2JsSF` | Hosted org used by `AGOL_Content_OKC` | 299 FeatureServers. Parks, surveys, marathons, `Infrastructure_Projects_OD`, parcel snapshots. **No** permit / 311 / license / deed names. |
| `access.okc.gov/aca/` | Accela Citizen Access (permits / licenses) | Interactive search UI only. No bulk FeatureServer. |
| `oklahomacityok.citysourced.com` | CitySourced (OKC Connect / Action Center) | Public report form. `api.citysourced.com` is OneView v2 (authenticated). No open bulk feed. Android package `com.citysourced.oklahomacityok`. |

Client fit if a family later appears on the Hub: existing `ArcGISClient`. No
fifth client is required by anything found today. Accela / CitySourced would
need a new scraper, which this wave does not authorize.

## Summary

| Family | Tier | Watermark (newest-row) | Geocode path | Register? |
|---|---|---|---|---|
| Permits | **3** | no building-permit feed. Closest live near-miss: Work Zones `Startdate` (string) = **2026-08-27** via `OBJECTID DESC` (213-row rolling occupancy, not issuance) | native point, wkid 103512 (OK state-plane feet) + `Worklocation` address | **no** |
| 311 | **3** | none published | Action Center / CitySourced only | **no** |
| SLA | **3** | Hotel Motel Tax: **no date field** (375-row lodging-tax snapshot) | native point + `Address` | **no** |
| Deeds | **3** | Land Documents `Date`: newest real easement **2026-07-21**; newest real `IndexType='D'` **2026-06-02**; **0 rows in last 30 days**. No sale price / grantee | native point (wkid 103512) + sparse `Address` (833/3658 of type D) | **no** |

## Per-family findings

### Permits — Tier 3 (none)

Hub site-scoped search `q=permit` returns three datasets: **Garage Sales**,
**Work Zones**, **Hotel Motel Tax**. None is a building-permit issuance stream.
`OpenData/Licensing_Permits/FeatureServer` layers are 0 Garage Sales, 1–3
impact-fee polygons — no building-permit layer hiding at a non-zero index.

Transactional building permits are in Accela Citizen Access
(`access.okc.gov/aca/`, modules include Building-Residential / Commercial,
demolition, trades). Search-only; no public bulk extract.

**Near-miss, live, do not register as permits — Work Zones.**

- Endpoint: `https://utility.arcgis.com/usrsvcs/servers/ead80c5e4e4e4c719359217f704a0c4c/rest/services/OpenData/Transportation/FeatureServer/5`
- Old-portal id 68; Hub item `ead80c5e4e4e4c719359217f704a0c4c` sublayer 5.
- Description: "permitted active work zones".
- Count: **213**. `Startdate LIKE '%2026%'`: 194; started `08/27/2026`: **7**
  (probe day). `Startdate` / `Enddate` are **strings** (`MM/DD/YYYY`), so
  `orderByFields=Startdate DESC` lexicographic-sorts and is **not** a
  watermark — `OBJECTID DESC` is the working newest-row order.
- Newest row (OID 2363904): `Worktype=Dumpster/Storage`, `Startdate=08/27/2026`,
  `workzonenumber=WZ-2026-01654`, `Worklocation=136 NW 18th St`, point geom.
- Worktypes mix dumpsters with `Building Construction`, `Road Construction`,
  utilities. Grain is **current occupancy**, not issuance: expired zones drop
  off (Tulsa-311-style rolling window, ~200 rows). Cannot backfill.
- Geometry: `esriGeometryPoint`, wkid **103512** (projected feet, Oklahoma
  North class; not WGS84). Address string `Worklocation`.

Dallas-style ROW-as-development-proxy does not apply: this is not an issuance
archive.

**Garage Sales** (live, wrong family): Hub
`…/Licensing_Permits/FeatureServer/0`, 43 rows, `Permit_Date` string newest
**2026-08-29** (future-dated weekend permits), native point + full address.
Yard-sale occupancy permits, not construction.

### 311 — Tier 3 (none)

Hub collection search `q=311`: **0**. Old-portal catalog: no service-request
dataset. Hosted org: no 311 / request / complaint FeatureServer (name scan of
299 services). SeeClickFix Open311 `jurisdiction_id=oklahoma-city`: 404.
`okc.citysourced.com` does not resolve.

The operational channel is the **Action Center**
(`https://www.okc.gov/Services/Action-Center`): phone (405) 297-2535, email,
SMS, OKC Connect. "Report online" and the Play Store package
`com.citysourced.oklahomacityok` identify **CitySourced**. The vendor API at
`api.citysourced.com` is OneView v2 (authenticated), not an open feed.
El Paso published a CitySourced/Accela 311 FeatureServer; OKC has not.

### SLA / business licenses — Tier 3 (none)

No general business-license or occupational-tax issuance feed.

**Hotel Motel Tax** (snapshot, not a license stream):

- Endpoint: `https://utility.arcgis.com/usrsvcs/servers/b6e78aa9a14c494f827ea0f24418cac7/rest/services/OpenData/Finance/FeatureServer/3`
- 375 rows. Fields: `LegalName`, `Address`, `Certificate` (int), `Sector`.
  **No issued/expiry/watermark date.** Newest-by-OID is just catalog order.
- Native point + address, but G1/G8 cannot be scheduled without a date.
- Accela license search exists on the citizen portal; no bulk extract.

### Deeds / sales — Tier 3 (none)

Oklahoma County Assessor publishes sales only through a click-through Public
Access System (`docs.oklahomacounty.org/AssessorWP5/`) and USB/upload bulk
files. No public FeatureServer (`orgname:"Oklahoma County"` Feature Service
search = 0). County GIS hostnames `gis.oklahomacounty.org` /
`maps.oklahomacounty.org` do not resolve.

**Near-miss — Land Documents** (city clerk index, not market sales):

- Endpoint: `https://utility.arcgis.com/usrsvcs/servers/fd9dbc810c9e4b3b8eb17887b796f0e5/rest/services/OpenData/Licensing_Subdivision/FeatureServer/8`
- 33,986 rows. Fields: `IndexType`, `Number`, `Date` (esriFieldTypeDate),
  `Location`, `Address`, `Grantor`, `Reference`. **No grantee, no sale price.**
- `IndexType` distinct: E 27,885 (easement), D 3,658 (deed), O 904
  (ordinance), DTO 596, ETO (remainder).
- Raw `ORDER BY Date DESC` is poisoned by sentinel dates (max epoch-ms
  228017980800000 ≈ year 9198). Bounded query
  `Date > timestamp '2020-01-01' AND Date < timestamp '2026-08-27'`:
  - all types: newest **2026-07-21** (easements; e.g. OBJECTID 33994,
    `IndexType=E`, Grantor `SHIKI 2 LLC`)
  - `IndexType='D'`: 91 since 2020, 5 in 2026 YTD, newest **2026-06-02**
    (OBJECTID 33980, Number 3286, Address `12224 N COUNTY LINE RD`, Grantor
    `FINCHER PROPERTIES LLC`, Reference `TC-0707`)
  - last 30 days: **0**
- Native point (wkid 103512). Type D with non-null `Address`: 833 / 3,658
  (22.8%).
- Grain: city-held easements / ordinances / occasional city deeds, not
  county recorded sales. Cadence fails a 7-day (and 30-day) staleness gate
  even if the grain were accepted.

`2011_2021_Parcel_Data` on the hosted org (272,322 polygons) is an assessment
snapshot (`Market_Value`, `Year_Built`, SpatialEst hyperlinks to Canadian
County) with **no sale date/price**.

## Hosts probed and rejected

| Host | Result |
|---|---|
| `gis.okc.gov/arcgis/rest/services` | Incapsula HTML |
| `maps.okc.gov` | DNS NXDOMAIN |
| `oklahomacity-ok.opendata.arcgis.com` | 404 / 401 private |
| `okc.maps.arcgis.com` | private org |
| Socrata `data.okc.gov` | domain not found |
| CKAN on `data.okc.gov` | Incapsula, not CKAN |
| `gis.oklahomacounty.org`, `maps.oklahomacounty.org` | DNS NXDOMAIN |
| SeeClickFix Open311 | 404 |
| Accela ACA | UI only (SSL name mismatch on some `access.okc.gov` paths from CLI) |

## Recommendation

Do not register Oklahoma City in Wave 3. The portal is **resolved** (ArcGIS
Hub at `open-okc.hub.arcgis.com`) and CLI-queryable, which closes the
2026-08-25 Incapsula gap, but the four feed families are not on it. Revisit
only if the city publishes Accela extracts or CitySourced 311 to the Hub
(migration is still in flight through August 2026) or if a county sales
FeatureServer appears.

Garage sales and work zones are live geocoded layers useful as **negative
controls** (wrong grain) if a later agent is tempted to register them as
permits.
