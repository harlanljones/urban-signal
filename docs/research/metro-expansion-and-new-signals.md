# Metro expansion and new signals — wider geography + signal survey

**Date of survey: 2026-08-23.** Portals marked **probed** were hit live that day
(Socrata discovery API, ArcGIS Hub DCAT feeds, or direct REST layer queries);
update timestamps are the dataset's own metadata unless noted. Anything not
probed is explicitly marked *unverified*. Re-probe before acting on this —
see `docs/research/city-expansion-candidates.md` for how a city can quietly
retire an endpoint.

## Method, and its limits

For each county adjacent to a registered metro I tried, in order: (1) the
Socrata discovery API (`api.us.socrata.com/api/catalog/v1?domains=<candidate>`)
against guessed domains; (2) ArcGIS Hub / Open Data sites found by web search,
via their DCAT-US 1.1 catalog feeds (`<site>/api/feed/dcat-us/1.1.json`) and,
for promising datasets, the underlying AGOL item + FeatureServer REST endpoint
(field list + two newest rows). A Hub site was only counted after its own API
answered; `hub.arcgis.com` returns HTTP 200 for any hostname, so bare status
checks prove nothing.

Limits: DCAT titles are a coarse filter — a feed may exist under a name my
grep missed, exactly as the city-expansion survey's top-hit caution warns.
Several county portals are *transactional* portals (Accela Citizen Access,
Tyler Energov) rather than open-data portals; those publish no machine-readable
feed at all and are recorded as such. Counties whose portal platform is CKAN
or OpenGov were out of probe scope this pass except where a search surfaced a
concrete dataset.

## 1. Wider geography per metro

Structural context first, because it prices every verdict below:

### How geography gets added, and what it costs

Each registered metro is one hand-authored module (`src/spatial/cities/<city>.py`):
a single `METRO_BBOX`, `DIVISION_BBOXES` nested inside it, and submarket points
nested inside divisions. The interlock gate (`pytest -m interlock`) enforces the
containment invariant — every submarket coordinate inside its division bbox,
every division bbox inside the metro bbox — plus alias closure over `REGISTRY`.
Per `docs/agents/parallel-streams.md`, the cities module is leaf work, but every
expansion also touches spine files: `src/config.py` (endpoints),
`src/spatial/city_registry.py` (registration), and producer field fallbacks.

Three shapes an expansion can take, cheapest first:

1. **New division(s) under the existing metro** — grow the metro bbox and add
   division bboxes + submarkets. No new registration; producers fan out via the
   existing per-feed endpoints. But a division's data still comes from ONE feed:
   a Socrata/ArcGIS endpoint is per-jurisdiction, so a Pierce County division of
   Seattle Metro cannot be fed by Seattle's permit endpoint. This shape only
   works when the county's data already flows through a feed the metro
   registers (rare outside King County).
2. **Separate registration (new CityId)** — the honest shape for cross-county
   data: each county becomes its own partial registration with its own
   endpoints, like LA registering only the feeds that exist. Costs one enum
   member, aliases, registry entry, endpoint fields, and field-mapping fallbacks
   in the shared producers — the recurring tax described in the prior survey.
3. **Multi-source metro** — keep one metro identity but let `DatasetSpec`
   become per-division or per-source lists. This is a real schema change to
   spine files and the scheduler, not additive; per the interlock rules it
   should be raised as a refactor rather than worked around.

The practical consequence: **geography follows data source, not adjacency.**
A county is worth adding only if its feeds are strong enough to justify a
separate registration (shape 2) — which is why most verdicts below are
"skip" despite real portals.

### Seattle Metro → Pierce, Snohomish

| County | Portal | Feeds live | Updated | Verdict |
|---|---|---|---|---|
| Pierce, WA | `gisdata-piercecowa.opendata.arcgis.com` (ArcGIS Open Data v2.1) — probed | Permits: **yes** ("Permits Pierce County", FeatureServer `services2.arcgis.com/1UvBaQ5y1ubjUPmd/.../Permits_Pierce_County`) | 2026-08-21 (2 days before survey) | **Register permits-only, separate registration.** Strongest cross-county find of the survey. |
| Snohomish, WA | `snohomish-county-open-data-portal-snoco-gis.hub.arcgis.com` (ArcGIS Hub) — probed | Deeds/sales: partial ("Recent Property Sales"). Permits: unusable snapshot. 311/licenses: none | Sales layer modified 2026-08-19; newest row Jun-2026 (quarterly cadence) | **Skip for now**; revisit if a sales-only expansion is ever worth it |

Pierce detail (probed): 681k+ rows; fields include `applicationDate`,
`submittalDate`, `approvalDate`, `issuedDate`, `finalDate`, `buildingValuation`,
`projectValue`, `sqFtTotal`, `dwellingUnits`, `siteAddress`, `parcelNumber`,
plus `XCoord`/`YCoord` in WA State Plane feet — not lat/lon, but a point layer,
so the ArcGIS client's `outSR=4326` request pattern (as used for King County
sales) yields WGS84 directly. Date model matches Austin's richness (issue +
final + expiry-class fields), i.e. better than any currently registered city's
permit schema. Caveat: it is county *applications and permits* across six
departments (Building, Development Engineering, Environmental, Fire, Land Use,
Sewer) — filter to Building/Land-Use rows when computing CapEx density or the
feed reads noisy.

Snohomish detail (probed): "Recent Property Sales" (`services6.arcgis.com/z6WYi9VRHfgwgtyW/.../Recent_Property_Sales`)
carries `SALE_PRICE`, `PARCEL_ID`, `YEAR_SOLD`, `TRNSF_DATE` — but `TRNSF_DATE`
is a coarse `"Jun-2026"` string, cadence is quarterly per the Assessor page,
and there is no point geometry beyond parcel polygons. Fine for slow context;
useless for deed-velocity signals. "Active Permits" is a thin status snapshot
(`PARCEL_ID`, category, status; no dates, no valuation; metadata last touched
2021) — do not register as a permits feed.

Neither county publishes a 311 or business-license feed on its portal; liquor
licensing is state-level (WA LCB, already the model Seattle uses).

### Chicago → DuPage, Lake, Kane, Will, McHenry (collar counties)

| County | Portal | Feeds live | Updated | Verdict |
|---|---|---|---|---|
| DuPage, IL | none found — permitting is Accela Citizen Access (`aca-prod.accela.com/DUPAGE`) only | — | — | **Skip.** No open-data portal surfaced in search or probes. |
| Lake, IL | `data-lakecountyil.opendata.arcgis.com` (ArcGIS Hub, 1,537 datasets) — probed | None of the 4. Catalog is tax/TIF/parcel boundaries; closest hits are "Public Works permit fee areas" and building footprints | Mixed; core cadastral layers refreshed 2026-03 | **Skip** as feed source. Big portal, wrong content. |
| Kane, IL | `kanegisdata-kanegis.hub.arcgis.com` (ArcGIS Hub, 46 datasets) — probed | None. Parcels only (`KanePINList` MapServer: PIN, taxpayer, site address) | Parcel layer migrated hosts 2026 (`gistech.countyofkane.org`) | **Skip.** |
| Will, IL | `willcounty.gov/gis` = shapefile download page; permitting on SmartGov (`co-will-il.smartgovcommunity.com`) — not probed further | None machine-readable | — | **Skip.** |
| McHenry, IL | `data-mchenrycountygis.opendata.arcgis.com` (ArcGIS Hub); permits via SmartGov/OpenGov portals | None of the 4; has unincorporated-area **crime incidents** (relevant to §2) | Not date-probed | **Skip for feeds.** Note its crime layer as a §2 candidate. |

The collar counties are a structural dead end for the current 4-feed model:
Illinois counties generally do not run 311, building permits are
municipal (each village/city issues its own), county portals are cadastral,
and deeds are Clerk-recording functions published via paid search portals
(e.g. Lake County eSearch), not open APIs. If Chicago ever widens, the
realistic unit is *individual municipalities* (Evanston, Naperville, Aurora),
not counties — each a small partial registration like Austin would be.
Chicago's existing Cook County deeds feed remains the only county-scale
deeds source in the metro.

### SF Bay Area → San Mateo, Santa Clara, Alameda, Contra Costa

| County | Portal | Feeds live | Updated | Verdict |
|---|---|---|---|---|
| San Mateo, CA | `data.smcgov.org` (Socrata, 88 datasets) — probed | None of the 4. All GIS boundaries (parcels layer `nr6j-72z7`, no attributes beyond geometry) | Various | **Skip.** |
| Santa Clara, CA | `sccgov.data.socrata.com` (Socrata, 1,710 datasets) — probed | None of the 4. **Crime Reports `n9u6-aijz`** live (see §2). "Active Plan Check Application Tracker" `awpi-tuz7` is permit-adjacent but last updated 2023-03-30 — stale | Crime updated survey day | **Skip for geography**; prime §2 crime source. |
| Alameda, CA | `data.acgov.org` (ArcGIS Hub, 163 datasets) — probed | None of the 4 live. "Assessor Office Ownership Transfer List" is a true transfer feed (APN, `transfer_dt`, `value_from_trans_tax`) but **stale**: newest row 2023-04, layer untouched since 2025-07-07. **Crime Reports Jul2022–Present** live, point-geometry | Transfer list modified 2025-07-07; crime max incident ≈ 2026-08-15 | **Skip for now.** Re-check the transfer list annually — if it refreshes, it is the best deeds-shaped dataset of any surveyed county. |
| Contra Costa, CA | `contra-costa-gis-cocogis.hub.arcgis.com` (ArcGIS Hub, DCAT returned 2 datasets) — probed | None. Permits are Accela ePermits Center (transactional) | — | **Skip.** |

Notable negative result: **no Bay Area county publishes building permits,
311, licenses, or live sales/deeds as an open feed.** Permits sit in Accela
instances (Contra Costa confirmed; pattern likely county-wide), transfers sit
in Assessor systems published at annual granularity if at all. The SF
registration's EAST_BAY / PENINSULA / SILICON_VALLEY divisions are fed by
city portals (Oakland, San José, etc.), and that does not change at county
level. The one genuinely new thing here is crime data (§2): Santa Clara's
Socrata feed updates daily and covers Sheriff-patrolled areas; Alameda's
Hub feature layer carries point geometry and NIBRS-style descriptions.

### NYC metro → Westchester, Nassau, Suffolk (NY); Hudson, Bergen, Essex (NJ)

| County | Portal | Feeds live | Updated | Verdict |
|---|---|---|---|---|
| Westchester, NY | `gis.westchestercountyny.gov` GeoHub (ArcGIS Hub); parcels also mirrored on NYS clearinghouse `data.gis.ny.gov` ("Westchester County Parcels", 258k records) — probed via catalog pages | None of the 4. Assessment rolls live on ~25 municipal websites by design (NY tax-law structure) | Parcels layer updated 2026-08-07 | **Skip.** Fragmented-by-statute assessment data; no county feeds. |
| Nassau, NY | none found (no Hub/Socrata/CKAN portal surfaced in searches or probes) | — | — | **Skip** — *unverified beyond two searches + four failed domain probes*. |
| Suffolk, NY | `opendata.suffolkcountyny.gov` (ArcGIS Open Data, 282 datasets) — probed | None of the 4 current: "Licensed Tobacco Businesses **2016**", "Hunting Permits 2015–2016", "Sales Tax 2006–2017" all frozen; Tax Parcels refreshed 2026-04 | Stale license/permit sets; parcels live | **Skip.** A third-party registry mentions an active business-license dataset, but nothing current exists in the county's own catalog — treat that claim as unconfirmed. |
| Hudson, NJ | `hudson-county-gis-hudsoncogis.hub.arcgis.com` — probed via search results | None of the 4; apps/maps and a parcel viewer only | — | **Skip.** |
| Bergen, NJ | No county open-data portal; parcels flow to the **statewide** NJGIN service | None of the 4 directly | NJGIN statewide parcels updated week of 2026-08-17 incl. Bergen | **Skip.** NJ's real data path is `njogis-newjersey.opendata.arcgis.com` (statewide parcels+MOD-IV), which is context geometry, not a signal feed. |
| Essex, NJ | No NJ county portal found. Caution: `data-essexcounty.opendata.arcgis.com` is Essex County, **Ontario** — a name-collision trap | — | — | **Skip.** |

The NYC-metro expansion is a structural dead end for the current feed model.
NY/NJ suburban counties publish cadastral layers and viewer apps, not
transactional feeds; permits sit in municipal building departments; deeds in
county clerks without APIs. The existing NYC registration already reaches
deeper (ACRIS) than any of its neighbors can.

### Los Angeles → Orange, Ventura, San Bernardino, Riverside

| County | Portal | Feeds live | Updated | Verdict |
|---|---|---|---|---|
| Orange, CA | `data-ocpw.opendata.arcgis.com` (ArcGIS Hub, 933 datasets) — probed | None of the 4. Cadastral/planning layers ("Parcels With Attributes", address points); permits are OC Planning transactional | Parcels modified 2024-09 | **Skip.** |
| Ventura, CA | No ArcGIS Hub/Socrata portal found under six candidate hostnames — *unverified beyond probes* | — | — | **Skip** pending a platform investigation nobody should spend yet. |
| San Bernardino, CA | `open.sbcounty.gov` / `open-data-sbcounty.hub.arcgis.com` (253 datasets) — probed | None of the 4. Water-district parcels, zoning, boundaries | Mixed; water parcels 2026-06 | **Skip.** |
| Riverside, CA | `gisopendata-countyofriverside.opendata.arcgis.com` (85 datasets) — probed | One stale "Permits" layer: newest metadata 2023-09-06, served from an enterprise MapServer — treat as dead | 2023-09 | **Skip.** |

The LA metro verdict mirrors Chicago's: California counties run assessors,
recorders, and public works — not 311 or licensing — so the four adjacent
counties add geography without adding signal. If Inland Empire or OC coverage
ever matters commercially, the honest unit is again individual cities
(Anaheim/Irvine/Santa Ana publish their own Socrata/ArcGIS feeds), each a
partial registration at Austin-like cost. Expanding the LA metro bbox to
include Riverside/San Bernardino would also stretch H3 cell counts and
division hand-authoring work across territory with zero new feeds behind it.

## 2. New signal types beyond the current four feeds

Legend: **live** = probed survey day with recorded `rowsUpdatedAt`;
**fresh-cadence** = probed, last refresh noted; *unverified-negative* = my
queries found nothing, which is weaker evidence than a confirmed absence.

### Summary table

| Signal | Measures | NYC | CHI | SF | SEA | LA |
|---|---|---|---|---|---|---|
| Crime incidents | Public-safety trajectory; NIBRS offense mix | `qgea-i56i` historic + `5uac-w243` YTD, fresh-cadence | **live** `ijzp-q8t2` (lat/lon) | **live** `wg3w-h783` | **live** `tazs-3rd5` (lat/lon) | `2nrs-mtv8` 2020–2024 archive, refreshed 2026-03-04, NIBRS transition |
| Evictions (executed/filings) | Household distress; rental-stock churn | **live** `6z8x-wfk4` (address+ZIP, geocode needed) | none in Cook County catalog (*probed*) | none transactional (*unverified-negative*) | none (*unverified-negative*) | none (*unverified-negative*) |
| Transit / service changes | Accessibility & foot-traffic shift | MTA `vxuj-8kew` daily ridership (ends 2025-01) | **live** `5neh-572f` L-station entries daily; `6iiy-9s97` bus+rail daily | agency portals, not city portal (*unverified*) | agency portals (*unverified*) | agency portals (*unverified*) |
| Street-cut / utility permits | Physical churn outside building CapEx; disruption proxy | **live** `tqtj-sjs8` Street Construction Permits (2022–) | **live** `pubx-yq2d` CDOT Permits; `jdis-5sry` Street Closures; `hr8i-6s6s` Current/Future | none surfaced on `data.sfgov.org` (*unverified-negative*) | none on open portal (*unverified-negative*) | none found (*unverified-negative*) |
| Business move-ins/move-outs | Formation/closure velocity | derivable from existing SLA feed (`w7w3-xahh` DCWP Issued Licenses, **live**) | derivable from existing licenses feed | derivable | derivable (incl. STR endorsements) | derivable |
| STR registrations | Investor-buyout pressure; neighborhood-transient share | no public list post-Local Law 18 (*unverified-negative*) | **live** `qfyy-956j` Active Shared Housing Registrations | registry publishes reports, not a dataset (*unverified-negative*) | inside business-license feed (STR endorsement field) — verify at implementation | home-sharing registrations not found (*unverified-negative*) |

### Notes per signal

**Crime incidents** are the strongest genuinely-new feed family: four of five
metros have a live, geocoded, NIBRS-classified incident feed, three updating
on the survey day itself (`ijzp-q8t2`, `wg3w-h783`, `tazs-3rd5`). Column
checks confirmed `Latitude`/`Longitude` on Seattle's and Chicago's feeds;
SF's carries intersection/CNN plus point fields. NYC's two datasets refresh
monthly-ish (historic 2026-04-28, YTD 2026-07-27). LA City's feed is an
oddity worth flagging: `data.lacity.org` is alive and hosts LAPD crime even
though the 311 feed was retired — but "Crime Data from 2020 to 2024"
refreshed 2026-03-04 mid-NIBRS-transition means the series breaks around
2025; treat LA crime as unavailable until a NIBRS-successor dataset appears.
County-level bonus for the SF registration's context features: Santa Clara
`n9u6-aijz` (Socrata, updated survey day, address-only) and Alameda's Hub
layer (point geometry, max incident ≈ 2026-08-15, block-level addresses).
Fit: a real LIMS-input candidate — e.g. a "safety-shift ratio" analogous to
the 311 QoL/neglect ratio — but it needs its own decay window and type
filtering (drop Part-2 noise), and it correlates with 311, so ship it behind
an ablation.

**Evictions** are the highest-signal-per-row distress marker and the worst
coverage story: NYC Marshals' executed evictions (`6z8x-wfk4`) update daily
with executed dates, residential/commercial flags, and borough/ZIP (geocoding
is yours to do — no lat/lon). Cook County's catalog has no equivalent
(verified by empty catalog searches), and SF/SEA/LA evictions live in courts
and rent boards that publish PDFs or aggregate statistics. A single-metro
feature creates asymmetry across cities; recommend NYC-only ingestion as a
context/validation feature, not a LIMS input, until a second metro appears.

**Transit/service changes**: per-station CTA 'L' entries (`5neh-572f`,
updated 2026-08-13) is the one dataset granular enough to matter spatially;
MTA's systemwide daily ridership (`vxuj-8kew`) stopped at 2025-01 and other
agencies publish off-portal. Fit: context feature (station-proximity
covariates), not a hex-level leading indicator.

**Street-cut/utility permits**: NYC DOT street construction permits
(`tqtj-sjs8`, live) and Chicago's CDOT permit family (`pubx-yq2d`,
`jdis-5sry`, `hr8i-6s6s`, all live) are clean, daily-updated activity feeds;
Seattle and SF publish nothing equivalent on their open portals. Fit:
moderate — construction-adjacent disruption and utility reinvestment show up
here before building permits do, but the semantics overlap CapEx density, so
the safe use is a separate "disruption index" context feature rather than a
fourth term in LIMS.

**Business move-ins/move-outs** need no new source at all: every registered
metro already ingests a licenses feed whose rows carry issuance dates and
status/lifecycle fields. First-appearance vs. closure counts per hex per
window is a producer-side derivation over existing topics. This is the
highest-value, lowest-cost addition in this entire survey — it converts the
existing SLA feed from a stock signal into a flow signal.

**STR registrations** are thematically appealing and practically sparse:
Chicago's shared-housing registrations (`qfyy-956j`, live) is the only
standalone verified dataset; Seattle folds STR endorsements into its business
licenses; NYC stopped publishing a registration list under Local Law 18;
SF/LA registries aren't on their open portals. Context feature at best.

## 3. Recommendation

### Geographic expansion: one yes, everything else no

1. **Pierce County, WA — permits-only, as a separate registration (do first
   if any geography expands).** The only adjacent county in the survey with a
   live feed family that matches the ingestion model: a FeatureServer
   refreshed 2026-08-21 carrying application/submittal/approval/issued/final
   dates, building + project valuation, dwelling units, and site addresses —
   a richer date model than any currently registered city. Costs: one new
   hand-authored cities module (or a Pierce division block under a widened
   Seattle metro only if the multi-source schema change below happens), an
   ArcGIS `DatasetSpec` reusing the existing King County client pattern,
   `outSR=4326` for the state-plane coordinates, and field fallbacks in the
   permits producer.
2. **Snohomish County, WA — park.** Quarterly sales snapshots with month-level
   date strings are worth more as a future backfill/validation corpus than as
   a live feed.
3. **Everything else — skip.** Chicago collar counties, Bay Area counties,
   NYC-metro counties, and LA-adjacent counties all fail one of: no portal,
   portal exists but carries none of the four feed families, or feeds frozen
   for years. The recurring lesson across all five metros is that *county*
   governments are the wrong tier for these signals outside Washington:
   permits are municipal, 311 is big-city-only, licensing is city/state, and
   deeds sit behind clerk portals and assessor extracts.

**Structural cost warning.** There is no cheap way to bolt a county onto an
existing metro. Division bboxes must nest inside the metro bbox and submarket
points inside divisions (`pytest -m interlock`), but each jurisdiction's data
comes from its own endpoint — so "add Pierce as a Seattle division" silently
requires either per-division endpoints (a spine schema change to
`DatasetSpec`/scheduler) or feeding Pierce hexes from Seattle's endpoint
(wrong data). The honest shapes are a separate `CityId` registration
(additive spine edits, leaf-shaped cities module), or the per-division source
map refactor, which should go through the interlock-refactor path, not be
worked around. Either way the interlock gate must be extended/kept green.

### New signals, ranked by value over implementation cost

1. **License-status transitions (move-ins/move-outs) — do this first.**
   Zero new endpoints: derive first-seen/closed counts per hex from the four
   existing SLA topics. Turns a stock signal into a flow signal with pure
   producer/consumer work.
2. **Crime incidents — best new-feed candidate.** Verified live IDs in NYC
   (`5uac-w243` YTD + `qgea-i56i` historic), CHI (`ijzp-q8t2`), SF
   (`wg3w-h783`), SEA (`tazs-3rd5`); LA blocked by the NIBRS-transition gap.
   Prototype a safety-shift ratio behind ablation before promoting it into
   LIMS.
3. **Street-cut permits (NYC `tqtj-sjs8`, CHI CDOT family)** — useful
   disruption context; two of five metros; keep out of LIMS until shown to
   add signal beyond CapEx density.
4. **Evictions (NYC `6z8x-wfk4`)** — ingest NYC-only as context/validation;
   do not build cross-city features on one metro.
5. **STR registrations / transit ridership** — context features; Chicago's
   `qfyy-956j` and CTA station entries `5neh-572f` are the only datasets
   granular enough to bother with now.

### Survey caveats to carry forward

The Socrata discovery API's full-text search failed outright on some domains
(`data.smcgov.org`, `datacatalog.cookcountyil.gov` returned empty sets for
queries that catalog enumeration answered), so every negative above was
checked by full-catalog enumeration where feasible (Santa Clara's 1,710
datasets were scanned completely; Lake IL's 1,537 via title grep). Unauthenticated
SODA requests rate-limited during probing; a couple of column checks were
retried after backoff. All "unverified-negative" marks mean exactly that.
