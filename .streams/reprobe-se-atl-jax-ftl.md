# Stream log — reprobe-se-atl-jax-ftl — 2026-08-28

## Claim

- **Stream id:** `reprobe-se-atl-jax-ftl`
- **Leaf files I will create/edit:**
  - `.streams/reprobe-se-atl-jax-ftl.md` (this file)
  - `docs/research/southeast-reprobe-atl-jax-ftl.md` (NEW)
- **Spine files I expect to need:** none. Research-only re-probe. Explicitly
  forbidden from touching `apps/api/src/serving/dashboard.py`,
  `apps/dashboard/public/index.html`, `test_city_leaf_naming.py`,
  `.streams/dispatch-log.md`, any spine file, or any leaf city code.

## Intent

Re-assess the live viability of three Southeast cities whose wave-3 probes
(2026-08-27) judged all four signal families Tier 3 / not wave-ready: Atlanta
(US-336), Jacksonville (US-338), Fort Lauderdale (US-342). For each family
(PERMITS / COMPLAINTS_311 / SLA business+STR / DEEDS) re-verify live whether a
row-level open feed is now queryable with a fresh watermark (~≤30 days) and a
real schema, classifying each as (a) REGISTER, (b) REGISTER-PARTIAL with a
documented filter, or (c) KEEP-DEFERRED with precise re-probe triggers. Push one
level further than each wave-3 probe (AGOL orgs, hosted FeatureServers, county
servers) for any new door missed. This is a dispatcher request; the tickets are
already claimed by the orchestrator — no Linear edits, no commits, no PRs.

## Decisions

- **2026-08-28** — Atlanta. `opendata.atlantaga.gov` TLS still dead (strict
  `000`, `-k` gives Azure 404). Unofficial `Building_Permit_latest` FeatureServer
  (DCP org `5RxyIIJ9boPdptdo`) STILL FROZEN: newest `OrigOpened` 2026-01-29,
  `dataLastEditDate` unchanged 2026-01-29, 0 rows ≥30d / ≥60d. Hub CSV
  "All Building Permits 2019-2024" is the same frozen archive. New door search:
  DCP org has no live permit/311/license FeatureServer (`Code_Enforcement_Data_2021_2023`
  frozen 2023-12-29; a `Service Request` survey123 form in a *different* org
  `8gr8DRX2cvuioG1p` is a form, not municipal 311). All four families Tier 3
  still — **KEEP-DEFERRED**, no new feed.
- **2026-08-28** — Jacksonville. `opendata.coj.net` still DNS-unresolved (not
  retried; wave-3 DNS sweep exhaustive). JaxGIS `maps.coj.net/coj` ArcGIS Server
  11.1 alive. **DEEDS door: the `CityBiz/Parcels` MapServer last-sale snapshot
  IS fresh** — newest composite sale **2026-08-20**, SALESLYY=2026 total 22,505,
  30d (≥2026-07-29) **62**, July 2,114 / August 31. Native `LAT`/`LONG` on all.
  BUT it is a one-row-per-parcel last-sale overlay (no SALEPRICE / doc number),
  exactly the shape `docs/research/seattle-deeds-replacement.md` rejects — the
  watermark moves only when the same parcel re-sells, so **REGISTER-PARTIAL is
  not warranted for DEEDS** (wrong-shape, not wrong-jurisdiction). Duval PA
  monthly sales file unchanged: newest file as-of **08-10-2026** (rec03 max sale
  2026-07-22, ~5-week lag, no observed sale-price field) — still too laggy /
  incomplete. Permits (JAXEPICS SPA, `jaxepicsapi` 403), 311 (Oracle/RightNow,
  org search permit/311/license = 0), SLA (`Business_Data_WFL1` 2020 JSO
  snapshot, no date col) all still absent. **KEEP-DEFERRED**, but log the
  thawed deeds snapshot as a re-probe trigger.
- **2026-08-28** — Fort Lauderdale. City ArcGIS Server 10.9.1
  (`gis.fortlauderdale.gov/server/rest/services`) and Hub org `82LxCEC4N4AxRpwc`
  still live. **PERMITS** `BuildingPermits/0` STILL FROZEN at `SUBMITDT`
  **2026-03-16** (0 rows ≥30d/≥60d). **311** `ServiceRequest/0` STILL FROZEN at
  `REQUESTDATE` **2022-02-05**. **SLA** `BusinessLicense/0` STILL FROZEN —
  `ISSUEDATE` null 0/21,849, newest `EXPIREDATE` 2021-09-30 by wave-3, 0 rows
  ≥30d/≥60d. **DEEDS** `TaxParcel/0` live but **Broward-wide last-5-sales** —
  `SALEDATE1` newest **2026-08-13**, 405 countywide / **185 FTL-only** in 30d
  (≥2026-07-29), native lat/long. Same disposition as wave-3: live, geocoded, but
  county assessor snapshot over 19 municipalities + last-5 mutation → wrong home
  for a city DEEDS registration; belongs to a Broward county leaf. **Only** live
  city feed is `FranchisePermit` (11 edits ≥30d) but it's utility/right-of-way,
  wrong family. **KEEP-DEFERRED**; Do not register FTL to fill the Miami/Fort
  Lauderdale slot.

## Current step

All live ROW-level re-probes complete across all three cities every family.
Writing the research summary.

## Next step

Report back to orchestrator with the structured ATLANTA / JACKSONVILLE /
FORT LAUDERDALE / CROSS-CITY pattern. No further probing required unless a
triggered re-probe fires later (see triggers in the research file).
