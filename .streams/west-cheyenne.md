# Stream log — west-cheyenne — 2026-08-28

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** west-cheyenne
- **Leaf files I will create/edit:** NONE (REJECT — no leaf files built)
- **Spine files I expect to need:** NONE

## Intent

Live-probe Cheyenne, WY (US-248) for any verifiable municipal open-data feed
(permits / 311 / SLA licenses / deeds; crime only with coords or address).
Ticket says "Data source: none — (none), Fit: Low" — an honest REJECT
candidate. If no feed verifies, reject with evidence. If one verifies,
partial registration is fine and I build the leaf files.

## Decisions

- 2026-08-28 — Claimed stream; copied template to .streams/west-cheyenne.md. Branch chore/restore-metros-and-columbus, clean of my files (untracked stream log only). Concurrency hazard noted: other agents run `git stash -u` / `git clean`; recovery path = stash@{0}^3.
- 2026-08-28 — **REJECT.** Live-probed every reachable candidate and found NO verifiable live municipal feed. All Cheyenne/Laramie County/Wyoming data is stale (2014-2024) or a private/restricted org. See evidence in `## Probe evidence` below. No leaf files built. Recommend closing US-248 as wontfix.

## Probe evidence (US-248 — Cheyenne, WY)

Ticket: "Data source: none — (none), Fit: Low". Probe performed 2026-08-28
(live HTTP + ArcGIS REST + Socrata-style checks; no mirrors used).

### 1. City of Cheyenne ArcGIS org (`services1.arcgis.com/e5t4ywWgRBNUuDeU`, 246 services) — only stale snapshots
- **LiquorPermits2022** — 83 records, but `serviceDescription` = "As of February, 2022" snapshot. No watermark column, no 2023-2026 update path. Stale by ~4.5y.
- **Cheyenne_Wyoming_Crash_Data / _updated** — 8,440 records, years 2020–2024 only (per-layer `groupByFieldsForStatistics=YEAR`: 2020=1636, 2021=1849, 2022=1614, 2023=1708, 2024=1633). Latest DATE 2024-12-31 — ~20 months stale. No 2025/2026 layer exists (`2025_All_Crashes`/`2026_All_Crashes` → 400 Invalid URL). Crash/accident data is not an eligible FeedType family (crime-only-with-coords per ADR-0004 does not cover traffic crashes), and it is stale regardless.
- **CitizenProblems_{landuse,road,trash,snowice,utility,parktree,public,survey}** (311-style) — ALL empty or a single 2021 row (CreationDate 1627580084009 = 2021-07-29). `editingInfo.dataLastEditDate` = 2021. Stale by ~5y.
- **Cases_current/current, Cases_public, Cases_reporter** — COVID-19 case dashboards (confirmed/recovered/deaths), not municipal permits/311.
- **Development (Annexation/Plats/Site Plans)** — 2014–2015 UDC cases (e.g. UDC-15-00440). Stale by ~11y.
- **Conditional_Use / Variances / Zone_Change** — mostly empty test rows ("mustang", "nr3", "1lot"). Stale.
- **Core_Fee_Waiver_Area_Permits** — CreationDate 1536961923721 = 2018-09. Stale by ~8y, 6+ rows only.
- **SanitationServices** — 2021 curbside pickup zones (static geography, no service-request records).
- No permits / 311 / SLA / deeds FeatureServer with a 2025-2026 update watermark anywhere on the org.

### 2. Laramie County ArcGIS (`maps.laramiecounty.com`) — assessor/parcel only, no deeds
- **CntyAssessor/property_restricted_ASR** — queryable parcels (street, owner name1/name2, netsf, taxyear, legal). Service is named "restricted"; fields carry NO sale price, NO transfer/sale date, NO deed columns → not a deeds feed. `taxyear` is assessment year, not a deed timestamp.
- **Planning/SmartGovParcels** — parcels/addresses powering SmartGov app; not a permit feed itself.
- **OpenGov/OpenGovData** — static boundaries/zoning/historic districts.
- **PubWorks/Facilities** — static facilities; **RAS_Super_Segments**, **Snow_Priority_Routes** — static.
- No permit/service-request/license feed.

### 3. Wyoming state
- **wyobiz.wyo.gov** — HTML business-entity search portal (200), NO public REST/CSV/JSON API; not an open-data feed. **sos.wyo.gov/API** → 404.
- **data.wyo.gov** → connection reset; **data-wyoming.opendata.arcgis.com** → private org (401 "private org id ... is not accessible").

### 4. City website / open-data portals
- **cheyennecity.org** → HTTP 403 on every path (WAF blocks direct requests; even the homepage). No public portal reachable for probing.
- **data-cheyenne.opendata.arcgis.com** → ArcGIS Hub shell but private org (search API 401).
- **gis.cheyennecity.org / arcgis.cheyennecity.org** → DNS NXDOMAIN.
- **seeclickfix cheyenne** → 400 (no place); **qalert** → no host; **mygov** → generic shell.

### Verdict
No verifiable municipal open-data feed with a 2025-2026 update watermark exists
for Cheyenne, WY. Every candidate is either a stale snapshot (2014-2024) or a
private/restricted org. Per the leaf brief ("if you confirm no verifiable
municipal open-data feed, REJECT with evidence"), this is an honest REJECT.
Partial registration is NOT warranted — even the one plausibly-eligible family
(SLA via LiquorPermits2022) is a frozen Feb-2022 snapshot with no watermark
column, which would false-alarm the staleness probe. No CityId, no registry
entry, no feed spec, no field maps, no fixtures were produced.

## Current step

REJECT complete — stream done. No git commits, no Linear updates.

## Next step

None (REJECT). Hand evidence to the spine/US-248 owner: recommend closing
US-248 as wontfix with the probe evidence above.

## Outcome

- **Feeds verified:** NONE (all stale or private/restricted)
- **REJECT evidence:** 2020-2024 crash data (stale ~20mo, not an eligible FeedType), Feb-2022 liquor snapshot (no watermark), 2021 311 views (empty/stale), 2014-2018 development/permits, restricted assessor with no deed columns, private ArcGIS orgs, WAF-403 city site, no WY state open-data API
- **Watermarks:** N/A (no feed registered)
- **Tests:** N/A (no leaf files built; interlock gate untouched, still 24 passed for prior work)
- **Spine delta:** REJECT — recommendation to close US-248 as wontfix. No CityId.CHEYENNE member, no aliases, no registry entry, no config endpoint settings.
