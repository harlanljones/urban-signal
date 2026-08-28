# SE probe — Pensacola, FL (US-304 leaf) — 2026-08-28

**Stream:** `city-pensacola` · **Linear:** US-304 · **Region:** Southeast
**Brief:** "GIS pages only — municipal GIS", fit Medium-Low, candidate doors
= City of Pensacola GIS / ArcGIS Server or Hub, Escambia County GIS / ArcGIS
Hub, data-escambia portals, + City of Pensacola permits.

**VERDICT: NOT-VIABLE.** No live public row-level feed exists for any of the
four signal families (PERMITS / COMPLAINTS_311 / SLA / DEEDS) from the City of
Pensacola or Escambia County. Every candidate is either a login-gated
application portal (Tyler TESS / Fortis, MyGovernmentOnline, Comcate/MyGov,
MGO Connect), a Web Map/App with no queryable table, or a static assessment /
asset layer that is not a records feed. No fabricatable registration — see
negative evidence table below. Re-probe is warranted if the county or city
publishes an open-data portal or ArcGIS Hub with records tables.

## Probe table

| Feed | Platform | Endpoint | Watermark col + newest | Rows | Geo availability | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | n/a | City: `fortisweb.cityofpensacola.com` (Fortis/Tyler TESS citizen search) — login page; county: `mgoconnect.org/cp?JID=224&PID=31` (MyGovernmentOnline SaaS) | none — no table | — | none | **login-gated UI, not a feed** |
| PERMITS | arcgis | `gismaps.myescambia.com/.../AccelaMain/MapServer` — only zoning/parcel/inspection-zone base layers | none | — | zone polygons | **base map, no permit records** |
| COMPLAINTS_311 | n/a | City 311: `agency.comcate.com/private-submission/create?crm_token=…` + `/290/Pensacola-311-Citizen-Support` | none | — | none | **private-submission web form, login-gated** |
| COMPLAINTS_311 | arcgis | Escambia code-enforcement inspections = Web Map / Web Mapping Application (search: "Escambia County Code Enforcement Inspections") | none | — | interactive map | **Web Map/App, no table** |
| SLA (BTR) | n/a | City `/284/Apply-for-a-New-BTR`, `/659/Renew-an-Existing-BTR` | none | — | none | **web form only** |
| SLA (contractor licensing) | n/a | County contractor licensing → `mgoconnect.org` | none | — | none | **login-gated portal** |
| DEEDS | n/a | Escambia Property Appraiser `escpa.org/CAMA/SaleSearch.aspx` | none (curl blocked, HTTP/2 stream error exit 92) | — | none | **web form, no API** |
| DEEDS | arcgis | County `Individual_Layers/parcels` FeatureServer 0 — monthly-static assessment snapshot | none — owner + assessed values | — | parcel polygons | **static assessment, NO sale date/price; owner PII** |

## Exhaustive searches performed (negative evidence)

All probes live 2026-08-28. Network from this host reaches ArcGIS Online,
both ArcGIS Hub web roots, `cityofpensacola.com`, `myescambia.com`, and
`escpa.org`.

1. **ArcGIS Online catalog search** (`www.arcgis.com/sharing/rest/search`,
   `num` up to 40) for these terms, filtered to Feature/Map services with a
   URL: `Pensacola`, `Pensacola permit`, `Pensacola building`,
   `Pensacola 311`, `Pensacola license`, `Pensacola complaint`,
   `Pensacola service request`, `Pensacola code enforcement`,
   `Pensacola development`, `Pensacola GIS`, `Pensacola open data`,
   `Escambia permit`, `Escambia County`, `Escambia property appraiser`,
   `Escambia parcel sales`, `Escambia business license`,
   `Escambia complaint`, `Escambia inspections`, `Escambia 311`.
   Results are overwhelmingly coastal / bathymetry / artificial-reef / SDAT
   "PFL" conservation layers and statewide parcel centroids — no municipal
   permit / 311 / license / sales-records table bearing the PNS context.
2. **City of Pensacola ArcGIS Hub** — `https://cityofpensacola-fl.opendata.arcgis.com`,
   and `.../data.json`, DCAT-us XML/JSON all 404 ("Domain record not found")
   or 401 ("private org id … not accessible"). `pensacola.maps.arcgis.com`
   org has NO open item inventory reachable; the only city ArcGIS artifact is
   a **Capital Improvements Public Dashboard** (`ffa46a7981604f928aba26f4275139f6`)
   — a Dashboard, not an event table.
3. **Escambia County ArcGIS Server** (`gismaps.myescambia.com/arcgis/rest/services`)
   — full service list enumerated: folders `Individual_Layers`,
   `JamesTestHospital`, `StormSurge2018`, `Utilities`, plus root services.
   Complete inventory is parcels / zoning / FLU / streets / hydrants /
   wetlands / hurricane-evacuation / assets (Lucity, Brightly) / inspection
   **zones** / code-enforcement **zones**. `AccelaMain` MapServer layers are
   CRAs, overlays, parcels, zoning, inspector zones — **no permit records**.
   Hosted EnerGov services (`EnerGovAdditional`, `EnerGov_Additional`,
   `EscambiaCounty_CountyLayerwbase`, `OpenGov_Map_Integration`) are
   citizen-serve **base data** (parcels, census, boundaries, districts) — no
   event tables. `Individual_Layers/parcels` FeatureServer 0 = monthly-static
   assessment snapshot: owner name + mailing block + `CURRASDLAND/CURRMKT`
   assessed values, `YEAR_` string — NO sale price, NO sale/record date, and
   carries owner PII (must not be registered as a deeds feed).
4. **City of Pensacola website** `www.cityofpensacola.com` — permits route
   through `fortisweb.cityofpensacola.com` (Fortis / Tyler TESS citizen
   search, login-gated) and `cityofpensacolafl.tylerportico.com/tess`.
   311 ("Pensacola 311 Citizen Support", /290) links to a Comcate
   **private-submission** web form with a CRM token param — not open data.
   Business Tax Receipts (SLA family) are Apply/Renew **web forms**
   (/284, /659). No Socrata / CKAN / open-data API anywhere on the domain.
5. **County permitting** — `myescambia.com/our-services/building-services/permitting`
   links to `mygovernmentonline.org` / `mgoconnect.org` (a vendor **SaaS
   permitting UI**, `JID=224&PID=31` for Pensacola), login-gated, no data API.
   `permits@myescambia.com` is a mailto.
6. **Socrata / open-data domain probes** — `data.escambiafl.gov`,
   `analytics.escambiafl.gov`, `data.escambiacountyfl.gov`,
   `opendata.escambiacountyfl.gov`, `escambiafl.data.socrata.com`,
   `data.cityofpensacola.com`, `data-escambia.opendata.arcgis.com` — all
   return `000` (no DNS / unreachable) or `404`. There is no Socrata instance
   for Pensacola or Escambia.
7. **Deeds** — Escambia Property Appraiser `www.escpa.org` live (200) but its
   `SaleSearch.aspx` is a web form (curl blocked by the server: HTTP/2 stream
   error, exit 92). Escambia Clerk of Court `escambiaclerk.com` returns 403
   (login/WAF gate). No parcel-sales CSV/ArcGIS layer exists.

## Why no registration

Every city in the registries that registers Pensacola-scale metros does so
because it found at least one queryable, watermark-bearing row feed. Pensacola
publishes **no** such feed: the four families all reduce to (a) login-gated
application portals, (b) interactive web maps with no queryable table, or
(c) static assessment / asset layers that are not records (and one parcels
layer even carries owner PII). Pointing a producer at a vendor SaaS UI, a web
form, or a login-wrapped Comcate/MyGov submission is exactly the "login-walled
portal" class the ticket's viability rule forbids. Registering the static
parcels assessment snapshot as DEEDS is wrong on multiple axes: no sale
price, no sale/record date (no watermark), and owner-PII exposure.

## Re-probe triggers

- City of Pensacola or Escambia County publishes an open-data portal or ArcGIS
  Hub item containing permit / service-request / license / parcel-transfer
  records (not base map).
- `mygovernmentonline.org` or the MGO Connect portal exposes a documented public
  reporting/export API.
- Escambia Property Appraiser or Clerk of Court publishes a bulk parcel-sales
  or recorded-instrument download.

## Files

Research only — no leaf `.py` files were created because the verdict is
NOT-VIABLE. Stream log: `.streams/city-pensacola.md`.
