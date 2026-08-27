# Wave 3 Phase-0 probe — Memphis, TN

**Date of probe: 2026-08-27.** Row-level ArcGIS reads (Hub DCAT + FeatureServer
`query` ordered by watermark DESC). "Newest row" is a feature actually
returned; Hub `modified` and leftover Socrata chrome were ignored.

**Verdict: REGISTER (partial).** Two Tier-1 families on the existing
`ArcGISClient`. Permits are monthly-batch (newest issued **2026-07-31**);
311 is same-day live. SLA and deeds have operational portals but no
watermarked public extract.

Platform: **ArcGIS Hub** at `data.memphistn.gov` (MEMEGIS org
`saWmpKJIUAjyyNVc`) plus a dedicated **ArcGIS Server** for 311 at
`311.memphistn.gov`. Not Socrata (federated discovery
`Domain not found: data.memphistn.gov`; `/api/catalog/v1` and
`/resource/<id>.json` 404). Not CKAN. No fifth client required.

---

## Method, and its limits

1. Hostname fingerprint: `data.memphistn.gov` (Hub HTML +
   `/api/search/v1` + DCAT-US 1.1, 69 items), `gis.memphistn.gov`,
   `311.memphistn.gov`, `maps.memphistn.gov`, `gis.shelbycountytn.gov`,
   four `*.opendata.arcgis.com` placeholders, Socrata discovery, CKAN
   `/api/3/action/status_show`.
2. Family search: Hub v3 `collections/dataset/items?q=…`, AGOL
   `sharing/rest/search` scoped to `orgid:saWmpKJIUAjyyNVc` and
   `owner:opmautomation_memegis`, GIS REST folder listings, DCAT title
   pass.
3. Row-level on every survivor: layer metadata, `returnCountOnly`,
   newest-row `orderByFields=<watermark> DESC`, recent-window counts,
   geocode-field completeness on the newest 500.
4. Replacement hunt for the missing families: Accela Develop 901
   (`aca-prod.accela.com/SHELBYCO`), Shelby County Clerk business-tax
   UI, Register of Deeds GIS / document search, county Parcel
   `SALES`/`RSALES` related tables, Innovate Memphis / Data Midsouth
   extract.

Limits: Hub search for "311" returns zero because 311 is not published
on the Hub catalog — it lives on a separate GIS server found via AGOL
item URL. County `RestaurantInformation` layer metadata timed out
(25s). Related tables `SALES`/`RSALES` on the county Parcel MapServer
are catalog-visible but not anonymously queryable (HTTP 500 / invalid
connection). A completely unpublished feed cannot be ruled out; the
69-item DCAT catalog and the MEMEGIS FeatureService search were read.

This retracts the 2026-08-25 south-heartland finding ("portal not
found" after probing `memphishealth.org` / `shelbycountytn.gov`). The
portal was `data.memphistn.gov` all along.

---

## Headline table

| Family | Endpoint | Newest row (watermark) | Geocoding | Recent window | Tier |
|---|---|---|---|---|---|
| **PERMITS** | `services2.arcgis.com/saWmpKJIUAjyyNVc/.../DPD_Building_Permits/FeatureServer/0` | `Issued_Date` = **2026-07-31T05:00:00Z** (date-only midnight CDT) | native `Latitude`/`Longitude` + point geom (473/500 newest) + `Address` 500/500 | Jul 2026 **583**; Aug 2026 **0**; 2026 YTD 2,826; total 27,100 | **1** (monthly cadence) |
| **311** | `311.memphistn.gov/server/rest/services/311/311_Request_Map_PROD/FeatureServer/0` | `REPORTED_DATE` = **2026-08-27T19:31:00Z** (same day) | native `X`/`Y` WGS84 on most rows; `outSR=4326` geometry; `Location_Address` 500/500 | Aug 2026 **12,987**; Last-7-Days layer 3,435; Reported-Today 438; total 395,216 | **1** |
| **SLA** | none. Accela ACA `aca-prod.accela.com/SHELBYCO` + County Clerk `secure.tncountyclerk.com` | n/a | n/a | n/a | **3** |
| **DEEDS** | none queryable. County Parcel related tables `SALES`/`RSALES` exist but 500; `QualifiedSales` MapServer has 0 layers; `CERT_TAX_PARCELS` is a CAMA snapshot (no sale date) | n/a | n/a | n/a | **3** |

**Keep or reject: REGISTER partial** — permits + 311. Austin/LA shape.
Existing `ArcGISClient`. Do not invent SLA or deeds from Accela /
Register-of-Deeds UIs.

---

## Permits — Tier 1 (monthly batch)

Hub item **DPD Building Permits** (`3018811a721a49a98843baeb29de6256`),
snippet: "new, alteration, and addition building permits issued since
January 2021. For more information visit develop901.com."

`https://services2.arcgis.com/saWmpKJIUAjyyNVc/arcgis/rest/services/DPD_Building_Permits/FeatureServer/0`

- 27,100 rows, point geometry (`esriGeometryPoint`), `maxRecordCount` 1000.
- Columns: `Record_ID` (e.g. `RES-ALT-26-000896`), `Issued_Date`,
  `Sub_Type` (`RES`/`COM` plus mixed long forms), `Construction_Type`
  (`NEW`/`ALT`/`ADD`/`ACC`), `Valuation`, `Address`, `City`,
  `Description`, `ZIP_Code`, `State`, `Latitude`, `Longitude`.
- Watermark `Issued_Date`. Newest row 2026-07-31 (RES-ALT-26-000896,
  2218 Oxford Square Ct, valuation $23,000, native 35.033 / −89.993).
- Oldest issued ~2021-01-04, matching the Hub snippet.
- Cadence: **0 rows issued in August 2026** on a 27 Aug probe; May 421 /
  June 376 / July 583. This is a month-end dump, not a dead archive.
  **Fails the 7-day staleness gate as published** until the August file
  lands; document a monthly-cadence exception at registration (PG County
  311 precedent).
- Geocoding: 473/500 newest rows have native lat/lng + geometry; 500/500
  have `Address`. The 5.4% coordinate gap is fillable via ADR 0004
  (`needs_geocode=True` as a supplement, not a requirement). Layer SR is
  Web Mercator; prefer the WGS84 attributes.
- Source system is Accela / Develop 901; the FeatureServer is the
  extract. Do not scrape `aca-prod.accela.com/SHELBYCO`.

**Register this layer.** Re-probe `Issued_Date` ≤72 h before build; if
August 2026 is still empty after mid-September, treat as stalled.

---

## 311 — Tier 1 (same-day live)

Not on the Hub catalog (search `q=311` / `service request` → 0). Found
via AGOL item "311 Requests" pointing at the city's 311 GIS server.

`https://311.memphistn.gov/server/rest/services/311/311_Request_Map_PROD/FeatureServer/0`

Sibling layers on the same service (do not register; they are filtered
views of layer 0): `Reported Today` (438), `Reported Last 7 Days`
(3,435), `Transfer Pending` (3,298). Table `CoM_311_Notes` is empty.

- 395,216 rows, point geometry, `maxRecordCount` 3000.
- Watermark **`REPORTED_DATE`**. Newest 2026-08-27 19:31 UTC (`8041417`,
  Code Enforcement — weeds occupied property). A later probe in the same
  session already saw `8041419`. Oldest `REPORTED_DATE` 2023-06-10.
- August 2026: 12,987 reported. Volume is production-grade.
- Geocoding path (native):
  1. Query `outSR=4326` — confirmed: newest geometry returns
     `x=-89.8677, y=35.0431`, `spatialReference.wkid=4326`.
  2. Attribute `X`/`Y` are WGS84 on 405/500 newest rows. 75/500 still
     carry State Plane feet (~800k / 270k, EPSG:2274); 20/500 nullish.
     **Do not blindly use `X`/`Y`.** Prefer `outSR=4326` geometry, or
     accept `X`/`Y` only when they look like lon/lat.
  3. `Location_Address` present on 500/500 newest as geocode fallback
     (not needed if (1) is used).
- SeeClickFix is intake, not the feed: `SCF_URL` / `SCF_Description`
  columns exist on the city layer. Do not pull SeeClickFix's own API.
- **PII — drop at ingest:** `CONTACT_NAME`, `CONTACT_EMAIL`,
  `CONTACT_PHONE`, `CONTACT_NAME_FIRST`, owner-name/address block,
  `MLGW_CUSTOMER` / `MLGW_CONTACT*` / `MLGW_EMAIL`.
- Do not watermark on `Closed_Date` (values exist in the future, e.g.
  2026-09-02 — scheduled close). `RESOLVED_DATE` newest 2026-08-26.

**Register layer 0.** Existing `ArcGISClient`; pass `outSR=4326`.

Open311 discovery `311.memphistn.gov/open311/v2/services.json` 404s.
`open311.memphistn.gov` 404s. Old Socrata IDs `hmd4-ddta` /
`aiee-9zqu` are dead leftovers.

---

## SLA — Tier 3 (portal only)

Hub `q=license` hit is **MPD Traffic Citations**, not occupational
licenses. AGOL org search for license / occupational / business tax /
STR returns wetlands, citations, and adopt-a-street — no business
registry FeatureServer. DCAT 69-item catalog has EDGE loans/PILOTs
and DMC projects (economic-development deals, not SLA).

**Live replacement, not a feed:**

- Develop 901 Accela Citizen Access
  (`https://aca-prod.accela.com/SHELBYCO/Welcome.aspx`) — planning,
  construction, signs, fire, **licenses**, and Memphis STR. Account UI.
- Shelby County Clerk business tax
  (`https://secure.tncountyclerk.com/`, TN Business Tax Act $15
  license). Annual gross-receipts tax files with TN DOR, not a city
  open-data table.
- County `ShelbyCounty/RestaurantInformation` FeatureServer exists
  (health inspections / restaurant points). Layer `/0` metadata timed
  out; even if live it is not an occupational-license registry.

Do not register.

---

## Deeds — Tier 3 (no queryable transaction stream)

| Surface | What it is | Feed? |
|---|---|---|
| Hub / MEMEGIS | no sales/deeds/transfer dataset | no |
| `BaseMap/QualifiedSales` MapServer | published name, **0 layers / 0 tables** | no |
| `BaseMap/Parcel` related tables `SALES` (8), `RSALES` (9) | catalog-listed CAMA sales tables | query HTTP 500 / "Invalid connection property" — not anonymous |
| `Parcel/CERT_TAX_PARCELS` | 352,614 polygons, `Latitude`/`Longitude`, `TAXYR`, owner, address — **no sale date / price / document no.** | CAMA snapshot, not deeds |
| `GenServ_Real_Estate_TaxParcels_ForSale*` | city surplus parcels for sale | token required (499); not recorded deeds |
| Register of Deeds GIS `gis.register.shelby.tn.us` | interactive parcel search → sales/deeds UI | not a stream |
| `search.register.shelby.tn.us` | document search | not a stream |
| Innovate Memphis / Data Midsouth "Property Transactions" | third-party cleaned 2016–2023 extract, modified 2026-02-02 | unofficial + closed archive; do not register (LA/unofficial-mirror rule) |

Same shape as a parcel file, not ACRIS. Do not register.

---

## Non-family live data (do not register as 311 / SLA / deeds)

| Dataset | Why it is not a family |
|---|---|
| `MPD_Public_Safety_Incidents` / `MPD_Traffic_Citations` | Crime / citations, not 311 |
| EDGE Loans / PILOTs / DMC Projects | Economic-development deals, not SLA |
| `HCD Property Investments` Experience app | Housing-program map, not deeds |
| `MAS_311_Tickets` (Animal Services) | Departmental subset; use the citywide 311 layer |
| Utility shutoffs, road closures | Ops layers |

---

## Replacement platforms (registrable vs not)

| Surface | What it is | Feed? |
|---|---|---|
| `data.memphistn.gov` | ArcGIS Hub, 69 DCAT items, leftover Socrata footer links | **Permits yes**; 311 not catalogued here |
| `services2.arcgis.com/saWmpKJIUAjyyNVc` | MEMEGIS AGOL org (~223 Feature Services) | Permits + reference layers |
| `311.memphistn.gov` | ArcGIS Server 11.x, folder `311` | **311 yes** (layer 0) |
| `gis.memphistn.gov` | City GIS (DPD folder is MPO only; Parcel is CAMA) | no family feeds |
| `maps.memphistn.gov` | Internal mapping (CRM/Tolemi folders empty; ForSale token-gated) | no |
| `memphis.opendata.arcgis.com` and three sibling Hub hosts | Generic empty Hub landing pages (~8 KB) | prior-survey traps; ignore |
| Accela `aca-prod.accela.com/SHELBYCO` | Develop 901 citizen portal | UI only |
| County Clerk / TN DOR | Business tax licenses | UI only |
| Register of Deeds | Document + GIS search | UI only |

No fifth-client build is justified. Both registerable feeds are
anonymous FeatureServer queries.

---

## Decision

**Register Memphis as a partial Wave-3 metro: PERMITS + 311.**

- Permits: Tier 1, monthly cadence exception, native geocode.
- 311: Tier 1, same-day, native geocode via `outSR=4326`.
- SLA / deeds: Tier 3 until Accela or the Register publishes a
  watermarked extract.

Re-probe both FeatureServer IDs ≤72 h before the implementation wave.
Stamp: 2026-08-27.
