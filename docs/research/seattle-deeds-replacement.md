# Seattle DEEDS replacement source — research findings

**Stream:** `deeds-seattle-replacement` · **Date:** 2026-08-24 (all live-API checks run this day)
**Follows:** `docs/research/deeds-watermark-audit.md` §Seattle — verdict was
DEAD PUBLICATION on the registered feed
(`PARCEL_SALES3YR_AREA_287/FeatureServer/0`, watermark `SaleDate` frozen at
2025-11-20, 277 days stale).
**Scope of this doc:** find and verify a live official replacement candidate.
Registering it is a **spine edit** (`apps/api/src/spatial/city_registry.py` +
`apps/api/src/config.py` + tests + dashboard wiring, gated by
`pytest -m interlock`) and is **OUT OF SCOPE for this stream.**

## Headline finding

**As of 2026-08-24 there is NO live, anonymously-queryable,
transaction-level recorded-deed / real-property-sale API published by King
County anywhere in its public portals.** The county's full weekly sales table
(`rpsale_extr`, 2,435,130 rows) exists as an ArcGIS Online feature *table*
but is access-restricted ("Not Public"; anonymous item reads return HTTP 403
`GWM_0003`). Every public sales publication KC maintains is either the same
frozen extract we already register, or not a transaction feed. A replacement
therefore requires one of: (a) KC granting AGO credentials or re-publishing a
public layer, or (b) a new bulk-file producer path against the Assessor's
download page. Neither is a registry swap.

## What the repo needs from a candidate (constraints derived from code)

- Platforms supported by `DeedsACRISProducer._client_for`: **socrata, arcgis,
  carto, ckan** (`apps/api/src/producers/deeds_acris_producer.py:72-77`;
  clients: `socrata_client.py`, `arcgis_client.py`, `carto_client.py`,
  `ckan_client.py`). ArcGIS pages by OID via `resultOffset`
  (`arcgis_client.py:187-217`) — exactly how the current feed runs
  (`extra={"oid_field": "OBJECTID", ...}`, city_registry.py:539).
- Row parser falls back across common spellings but expects lat/lng or a
  geometry-derived coordinate; missing coords produce events with null H3
  (`deeds_acris_producer.py:137-172`). PascalCase Seattle keys
  (`ExciseTaxNum`, `SalePrice`, `PIN`, `Sellername`, `Buyername`) are already
  special-cased (`deeds_acris_producer.py:107-109`, `119-133`, `201-231`);
  UPPERCASE variants would need a `field_map`.
- Watermark parsing supports ISO strings, `"YYYYMMDD"` text, epoch s/ms
  (`apps/api/src/producers/watermarks.py:10-48`). Bare **integer**
  YYYYMMDD (e.g. `20260815`) would be misread as epoch seconds
  (`watermarks.py:32-34`) — relevant caveat for Assessor extracts that store
  dates as numeric `YYYYMMDD`.

## Candidate comparison

| # | Candidate | Publisher | Coverage | Recency evidence (live check 2026-08-24) | Watermark candidate | Geometry | License/terms | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | **Real Property Sale Record Assessor extract table** (`rpsale_extr`), AGO item `96ff1f46173541b9a021a5fef1fdb8a9`, org `kingcounty.maps.arcgis.com` (= org id `Ej0PsM5Aw677QF1W`) | KCGIS Center (value-added extract of Dept. of Assessments data) | **Every recorded sale county-wide**, keyed ExciseTaxNum+MAJOR+MINOR; fields incl. `SALEDATE`, `SALEPRICE`, `RECNUMBER`, `SELLERNAME`/`BUYERNAME`, `SALEINSTRUMENT` (Warranty Deed, Quit Claim, Trustees Deed…), `SALEREASON`, `PRINCIPALUSE`, `PROPERTYTYPE`; 2,435,130 rows | SDC catalog: *"This dataset is updated on a weekly basis"*, LastUpdated **2026-08-18**; Next Update **Weekly**. Service itself **not anonymously reachable**: item JSON → `{"error":{"code":403,"messageCode":"GWM_0003","message":"You do not have permissions to access this resource or perform this operation."}}`; absent from the org's anonymous service directory (1,171 services listed) | `SALEDATE` (string `YYYYMMDD` per SDC domain sample "19341111 to 20060914" parses via `%Y%m%d`; if exposed as date/epoch-ms also fine) | **None — non-spatial table**; needs PIN join to public `PARCEL_AREA_439` for coordinates | SDC terms shown for this item: use restricted to obtainer/"authorized agents", no redistribution without written authorization — needs legal review before ingest | **RECOMMENDED TARGET — blocked on access** |
| 2 | **Assessor DataDownload bulk file** (Real Property Sales zip behind `info.kingcounty.gov/assessor/DataDownload/default.aspx`) | King County Department of Assessments (the authoritative primary — SDC metadata points here: *"Please visit the Assessor's website for authoritative data"*) | Same RPSale table as #1, as downloadable file | Page live (HTTP 200); file list is disclaimer/postback-gated (no clean JSON manifest found; `GetFiles`/`ListFiles` probes → 404). Cadence per SDC: weekly extracts | File-local: sort rows by `SaleDate` after load | None (table); same PIN-join need | Disclaimer cites RCW 42.56.070(9): lists of individuals may not be used for "commercial purposes" | **RUNNER-UP — needs new static-file producer capability** |
| 3 | Parcel Sales Last 3 Years — currently registered `PARCEL_SALES3YR_AREA_287/FeatureServer/0` **and its on-prem twin** `gismaps.kingcounty.gov/arcgis/rest/services/Property/KingCo_PropertyInfo/MapServer/3` (layer "Property sales in the last 3 years") | KCGIS Center | Last-3yr sales as parcel polygons | **Both frozen**: FeatureServer `editingInfo.lastEditDate = 1764334418927` → 2025-11-28T12:53:38Z, count 110,857, newest `SaleDate = 1763596800000` → **2025-11-20**; MapServer twin returns identical count (110,857) and identical top SaleDate — same stale extract mirrored | `SaleDate` (only time field) | Polygon (client lifts centroid) | Public open-data item | **REJECT — dead publication (both copies)** |
| 4 | `REALPROP_AREA_1289` (King County Real Property), `PARCEL_EXTR_213` (Parcel Record Assessor extract), `parcel_address_pub_area` | KCGIS Center | County-owned property interests / one-row-per-parcel snapshot w/ ownership+values | Live (PARCEL_EXTR item updated 2026-08-18) but **not transaction feeds**: no new row per sale; `REALPROP_AREA` fields are acquisition/inventory (`ACQ_DATE`, `PURCHASEPRICE`, `CUSTODIAN`…) for county-owned land only | none meaningful | polygons / table | Public | **REJECT — wrong signal** (per-parcel snapshots & government acquisitions ≠ market deeds; watermark would not move with sales) |
| 5 | WA State Geospatial Portal parcels — `geo.wa.gov` → `Current_Parcels` (`Parcels_2026`), org `jsIt88o09Q0r1j8h` | WA State (DNR/WA-Geoservices) | Statewide parcel boundaries only | Live: `lastEditDate 1775766076675` → 2026-04-09 — but all 17 fields contain **zero** sale/excise/deed/price/transfer columns | n/a | polygons | State open data | **REJECT — boundaries only, annual vintage** |
| 6 | PSRC Data Portal (`psrc-psregcncl.hub.arcgis.com`) | Puget Sound Regional Council (MPO) | Annual housing-development estimates derived from assessor extracts; no transaction-level sales product | n/a — aggregator, and nothing sale-level public | n/a | n/a | n/a | **REJECT — unofficial secondary/aggregated** |

Also checked and empty: `data.kingcounty.gov` (Socrata) catalog — zero hits for
excise/deed; "sales" returns only pet-license locations and a fleet catalog;
"parcel" returns legacy 2005 tables. `data.seattle.gov` — zero hits for
excise/sales/deeds. Global AGOL search for any public rpsale-derived view —
total 0. KC GIS Hub site search for "sales" surfaces only the dead layer.
WA DOR publishes REET only as quarterly county aggregates (no transactions).

## RECOMMENDATION

**Winner: `rpsale_extr` — Real Property Sale Record Assessor extract table**
(KCGIS Center publication of the Department of Assessments' excise-tax-based
sale record).

- Item: `https://kingcounty.maps.arcgis.com/home/item.html?id=96ff1f46173541b9a021a5fef1fdb8a9`
  (SDC metadata page: `https://www5.kingcounty.gov/sdc/Metadata.aspx?Layer=rpsale_extr`)
- Platform: `arcgis` feature **table** in org `Ej0PsM5Aw677QF1W`.
  ⚠️ Exact service URL is not discoverable anonymously (item read → 403
  GWM_0003). Do NOT guess the URL; obtain it via an authenticated AGO session
  or by asking KCGIS (giscenter@kingcounty.gov) to share the item/service
  publicly (as they do for `PARCEL_EXTR_213` etc.).
- Proposed `watermark_col`: **`SALEDATE`** — orders chronologically; SDC-documented
  string form parses through `parse_watermark`'s `%Y%m%d` branch
  (watermarks.py:13). Caveat: if the service exposes it as bare integer
  YYYYMMDD, add a normalization step or order-only usage — ints < 1e10 parse
  as epoch seconds today (watermarks.py:32-34).
- Proposed id_keys: `EXCISETAXNUM` + `MAJOR` + `MINOR` (+ `OBJECTID` if the
  hosted table carries one) — SDC: *"The unique identifier is Excise Tax
  Number plus Major plus MINOR."*
- Recency expectation: weekly loads (SDC: "updated on a weekly basis";
  observed LastUpdated 2026-08-18 vs audit date 2026-08-24).
- Field map required (UPPERCASE column names don't hit the parser's existing
  PascalCase fallbacks): `doc_id←EXCISETAXNUM(+PIN)`, `bbl←PIN`,
  `document_amount←SALEPRICE`, `party1_grantor←SELLERNAME`,
  `party2_grantee←BUYERNAME`, `recorded_date←SALEDATE`,
  `doc_type←SALEINSTRUMENT` (needs its decode table `kca6_saleinstrument_rpsale`
  applied, else codes like "2"/"15").
- Geometry: **absent** — non-spatial table. Options: (i) accept null lat/lng/H3
  initially (parser tolerates), (ii) enrich via PIN join to the public
  `PARCEL_AREA_439` polygon layer (updated 2026-08-22), which is what the dead
  3-year layer effectively precomputed.
- Terms caveat: SDC terms-of-use block for this item says data may be used
  "exclusively by the obtainer or their authorized agents" and not
  redistributed without written authorization — legal review before ingest.

**Runner-up: the Assessor DataDownload bulk Real Property Sales file**
(same authoritative table, publicly downloadable, weekly cadence) — but it is
a static zip, so it requires new producer capability (bulk-file ingestion +
watermark state), i.e., more spine work than an endpoint swap. It is also the
fallback if KC declines to share `rpsale_extr` with us.

**Interim posture (spine decision, not this stream):** until one of the above
lands, seattle/deeds stays registered-but-known-dead (277-day-old watermark;
probe will flag it weekly). Precedent exists for documenting such a caveat in
the registry comment (cf. NORA Sold Properties note, city_registry.py:686-690),
or the feed can be partially unregistered per docs/agents/parallel-streams.md.
Either way the dashboard wiring gate applies.

## Registration is a spine edit — OUT OF SCOPE here

Any registration touches `apps/api/src/spatial/city_registry.py` (SEATTLE
DEEDS DatasetSpec), `apps/api/src/config.py` (endpoint setting alongside
`arcgis_kc_sales_url`, config.py:113-119), unit tests including
`TestDashboardWiring`, and the synced `apps/dashboard/public/index.html`. Run
the gate `pytest -m interlock` from `apps/api` in the same spine hold
(AGENTS.md city-registration rule).

## Verification gaps

- `rpsale_extr` could not be sampled live (403 anonymous). Field list, types,
  and current max(SALEDATE) must be confirmed the moment access exists — the
  SDC attribute documentation reflects a stale domain snapshot (its SALEDATE
  example stops at "20060914") though the dataset itself updates weekly.
- The Assessor download page's file inventory is postback-gated; exact zip
  URL(s) and their refresh timestamps were not captured.
- eSales interactive search (`info.kingcounty.gov/assessor/esales/eSales.aspx`)
  is ASP.NET webforms with no evident JSON API — not pursued further.
