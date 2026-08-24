# Deeds feed watermark audit — slow source or wrong column?

**Stream:** `deeds-watermark-audit` · **Date:** 2026-08-24
**Trigger:** CI run 32703690250 of `feed-staleness-monitor` (probe dated
2026-08-24T07:57Z) found `deeds` stale in 6 of the cities that register it.
**Question:** for each stale deeds feed — genuinely slow source, wrong/lagging
watermark column, or dead service?

## Method

For every city: (1) read the declared `watermark_col` from
`apps/api/src/spatial/city_registry.py` (`REGISTRY`, `FeedType.DEEDS` specs;
endpoints live in `apps/api/src/config.py`); (2) sample the live API with curl
(`max(col)` aggregates + top-N rows ordered DESC, 15 s `--max-time`); (3) look
for better recency columns in sampled rows / layer metadata; (4) verdict.

The probe (`scripts/feed_staleness_probe.py:131-157`) orders by
`watermark_col DESC`, fetches a bounded 1000-row window, parses values via
`src/producers/watermarks.py::parse_watermark`, **drops values strictly after
now**, and takes the max. Two client behaviors matter downstream:

- `CartoClient.paginate` auto-applies a sentinel filter to date-named order
  columns: `<col> IS NOT NULL AND <col> >= '1900-01-01' AND <col> < '2101-01-01'`
  (`apps/api/src/producers/carto_client.py:122-139`) — so Philadelphia's window
  *includes* in-bounds garbage like 2066 while excluding 9798.
- `parse_watermark("2025")` returns `None` (bare 4-digit strings match no
  supported format), which is why San Francisco yields "no watermark parsed".

All curls below were run 2026-08-24. Truncated responses shown.

## Verdict table

| City | Declared watermark_col | Observed max (live) | Better column? | Verdict | Registry change |
|---|---|---|---|---|---|
| nyc | `recorded_datetime` | `2026-07-31` (= probe) | No — `modified_date`/`good_through_date` max identical | GENUINELY SLOW (publication stall) | None |
| chicago | `sale_date` | `2026-07-14` (= probe) | No — no insert-timestamp column exists | GENUINELY SLOW (~5 wk MYDEC→Assessor publish lag, healthy volume) | None |
| san_francisco | `closed_roll_year` | unparseable `"2025"` → probe got nothing | Yes: `data_loaded_at` (max `2026-06-26T15:13:35Z`) | WRONG COLUMN (+ annual-by-design roll) | Change `watermark_col` → `data_loaded_at`; accept annual cadence or reclassify feed |
| seattle | `SaleDate` | `2025-11-20` (= probe) | No — only time field on layer; `lastEditDate` = `2025-11-28` | DEAD PUBLICATION (service alive, extract frozen ~9 mo) | No col fix possible; needs replacement source (spine decision) |
| new_orleans | `sale_date` | `2026-07-22` (= probe) | No — schema has exactly one date column | GENUINELY IRREGULAR (10 rows in all of 2026) | None (threshold/expectation issue, not column) |
| washington_dc | `SALE_DATE` | `2026-08-12` (= probe) | `GIS_LAST_MOD_DTTM` max = today `09:16Z` (proves liveness) | HEALTHY/BATCHY (12 d age vs 7 d threshold is normal CAMA batch cadence) | None |
| philadelphia *(future-dated artifact)* | `document_date` | raw max year **9798**; in-probe-window max `2066-06-01` (> now) | Yes: `recording_date` (max `2026-07-02T00:19Z`, continuous) | WRONG COLUMN (77 % NULLs + mortgage-term sentinels) | Change `watermark_col` + `order_by` → `recording_date` |
| detroit *(future-dated artifact)* | `sale_date` | raw top values `2925-12-24`, `2206-01-28`, `2202-11-20`, `2062-04-09` | n/a — real sales active (2 105 since Jun 1; `lastEditDate` yesterday) | HEALTHY SOURCE + typo-year artifacts (probe's ≤now filter absorbs them) | None (sentinels already documented in registry comment) |

## Per-feed evidence

### NYC — ACRIS Real Property Master (`bnx9-e6tj`), col `recorded_datetime`

```
$curl 'https://data.cityofnewyork.us/resource/bnx9-e6tj.json?$select=max(recorded_datetime)%20as%20max_recorded'
→ [{"max_recorded":"2026-07-31T00:00:00.000"}]

$curl '...?$order=recorded_datetime%20DESC&$limit=3'
→ document_id "2026071400105003", doc_type DEED, recorded_datetime 2026-07-31,
   modified_date 2026-07-31, good_through_date 2026-07-31 ...

$curl '...?$select=count(1)&$where=recorded_datetime > '"'"'2026-08-01'"'"''
→ [{"n":0}]

$curl '...?$select=max(modified_date),max(good_through_date),max(document_id)'
→ {"max_mod":"2026-07-31","max_gtd":"2026-07-31","max_docid":"FT_4990009008899"}
```

Zero rows recorded after Aug 1; the newest load (Socrata `rowsUpdatedAt`
2026-08-10 per CI) delivered data only through Jul 31. ACRIS normally trails
recordings by days, not 3½ weeks. `modified_date` and `good_through_date` peak
at the same instant as `recorded_datetime` — there is no fresher column to
switch to. **Verdict: source-side publication stall; right column.**

### Chicago — Cook County Assessor Parcel Sales (`wvhk-k5uv`), col `sale_date`

```
$curl 'https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json?$select=max(sale_date),min(sale_date),count(1)'
→ {"max_sale":"2026-07-14","min_sale":"1971-09-15","n":"2686366"}

$curl '...?$order=sale_date%20DESC&$limit=2'
→ sale_date 2026-07-14, is_mydec_date true, doc_no 2619521029 ... (no other timestamp field)

metadata api/views/wvhk-k5uv.json → rowsUpdatedAt 2026-08-19T19:36Z, name "Assessor - Parcel Sales"

per-month counts ($where=sale_date >= '2025-12-01', group by month):
Dec 6388 · Jan 4194 · Feb 4739 · Mar 6235 · Apr 6784 · May 5390 · Jun 2823 · Jul 523
```

Steady 4–7 k sales/month, but publication trails recording by ~5 weeks (Jul 14
is the newest recorded sale despite an Aug 19 load). The schema carries no
insert/load timestamp — `sale_date` is the only candidate. **Verdict:
genuinely slow upstream pipeline (MYDEC recorder → Assessor publish); right
column.**

### San Francisco — Assessor Historical Secured Property Tax Rolls (`wv5m-vpq2`), col `closed_roll_year`

```
$curl 'https://data.sfgov.org/resource/wv5m-vpq2.json?$order=closed_roll_year%20DESC&$limit=2'
→ closed_roll_year "2025" (string), ..., current_sales_date "1969-03-01",
   data_as_of "2026-06-26T12:56:13", data_loaded_at "2026-06-26T15:13:35"

$curl '...?$select=max(data_loaded_at),min(closed_roll_year),max(closed_roll_year),count(1)'
→ {"max_loaded":"2026-06-26T15:13:35.000","min_yr":"2007","max_yr":"2025","n":"3934467"}
```

This is not a deeds feed at all — it is the annual tax roll (roll years 2007–
2025 in one table, 3.93 M rows, loaded each June; CI's `rowsUpdatedAt`
2026-06-26 matches `data_loaded_at`). The declared watermark can never work:
`closed_roll_year` is the string `"2025"` and `parse_watermark` returns `None`
for it (no format matches), so the probe has parsed nothing all along. Even
parsed, it would mean Jan 1 2025. The per-parcel `current_sales_date` is the
parcel's historical last-sale date (1969 here) — useless for ordering.
`data_loaded_at` is the only real recency column and its max equals the annual
load. **Verdict: WRONG COLUMN over an ANNUAL source; recommend
`watermark_col="data_loaded_at"` at minimum, plus a product-level question
about whether an annual roll belongs in a weekly-freshness deeds signal.**

### Seattle — King County "Parcel sales history - last 3 years" (`PARCEL_SALES3YR_AREA_287/FeatureServer/0`), col `SaleDate`

```
$curl '.../PARCEL_SALES3YR_AREA_287/FeatureServer/0?f=json'
→ name "Parcel sales history - last 3 years"
   editingInfo.lastEditDate = 1764334418927 → 2025-11-28T12:53:38Z
   fields: PIN address ExciseTaxNum SaleDate SalePrice RecNumber ... (no insert/edit ts)

$curl '.../query?f=json&where=1%3D1&returnCountOnly=true'      → {"count":110857}
$curl '.../query?f=json&orderByFields=SaleDate%20DESC&outFields=SaleDate,SalePrice,ExciseTaxNum&resultRecordCount=2'
→ SaleDate 1763596800000 → 2025-11-20T00:00:00Z (twice)

org service list filtered for SALE/PARCEL → only PARCEL_SALES3YR_AREA_287; no fresher sibling.
```

The service responds and holds 110 857 rows, but its own `lastEditDate`
(2025-11-28) says nothing has been written to it in ~9 months, and its newest
sale is 2025-11-20 — matching the probe. There is no alternative recency
column on the layer. **Verdict: DEAD PUBLICATION — a rolling "last 3 years"
extract that stopped being refreshed. No registry column change can fix this;
finding/replacing the King County source (e.g., REET excise-tax sales) is a
spine-level decision.**

### New Orleans — NORA Sold Properties (`hpm5-48nj`), col `sale_date`

```
$curl 'https://data.nola.gov/api/views/hpm5-48nj.json'
→ name "NORA Sold Properties"; rowsUpdatedAt 2026-08-11T21:34Z
   cols: identifier property_address zip_code geopin council_district
         disposition_channel sale_date geocoded_column (+computed regions)

$curl '.../$select=max(sale_date),count(1)'            → {"mx":"2026-07-22","n":"5618"}
monthly counts since 2026-01-01: Jan 7 · Apr 1 · Jun 1 · Jul 1   (10 rows total YTD)
```

The registry already documents that this is the Redevelopment Authority's own
disposals list, not market deeds. It publishes a handful of rows per quarter;
the schema has exactly one date column. 33-day age is what this feed is.
**Verdict: genuinely irregular/slow; right (only) column. Consider whether the
7-day staleness threshold should apply to feeds registered with a known-caveat
cadence.**

### Washington DC — PROPERTY SALES (CAMA) (`Property_and_Land_WebMercator/FeatureServer/57`), col `SALE_DATE`

```
$curl '.../Property_and_Land_WebMercator/FeatureServer/57?f=json'
→ name "PROPERTY SALES (CAMA)"; editingInfo.lastEditDate = null
   date fields: SALE_DATE, GIS_LAST_MOD_DTTM

$curl '.../query?f=json&orderByFields=SALE_DATE%20DESC&outFields=SALE_DATE,SALE_PRICE,SSL,QUALIFIED&resultRecordCount=3'
→ SALE_DATE 1786507200000 → 2026-08-12T12:00Z (all three)

$curl '.../query?f=json&orderByFields=GIS_LAST_MOD_DTTM%20DESC&outFields=GIS_LAST_MOD_DTTM,SALE_DATE&resultRecordCount=2'
→ GIS_LAST_MOD_DTTM 2026-08-24T09:16:30Z (today), SALE_DATE 1900-01-01 sentinel on one row
```

Newest transaction is 12.2 days old — just over the 7-day threshold — but
`GIS_LAST_MOD_DTTM` is stamped today, so the layer is actively maintained and
sales arrive in batches. Note one row carries `SALE_DATE = 1900-01-01`
(another in-band sentinel, harmless under ≤now filtering since ordering DESC
puts it last). **Verdict: healthy/batchy; no change needed. If DC keeps
tripping the threshold, the fix is probe policy, not the column.**

## Future-dated watermark artifacts

### Philadelphia — RTT summary (`carto://phl.carto.com/rtt_summary`), col `document_date`

```
$curl 'https://phl.carto.com/api/v2/sql?q=select max(document_date), min(document_date),
        max(recording_date), count(*) from rtt_summary'
→ {"max_doc":"9798-06-12","min_doc":"182-02-06","max_rec":"2026-07-02T00:19:46Z","n":5135164}

bucket counts: >2100 → 4 rows · years 2026–2099 → 15991 · > now() → 5 · NULL → 3972522 (77%)

the five future-dated rows (document_date, recording_date, grantors → grantees):
  9798-06-12  2026-03-20  MORTGAGE ELECTRONIC REGISTRATION SYSTEMS INC;ROCKET MORTGAGE LLC → ADAMS DAVID J III
  9277-02-17  2026-03-19  MIDFIRST BANK;CENDANT MORTGAGE CORPORATION → WASHINGTON DENEEN Y
  8616-07-15  2026-02-26  VELOCITY COMMERCIAL CAPITAL LOAN TRUST 2025-P2 ...
  7445-05-29  2026-04-06  SDG 1513-1517 RIDGE AVE LLC → S&T BANK
  2066-06-01  2026-05-28  MORDECAI RONALD;MORDECAI ASHLEY → SECRETARY OF HOUSING AND URBAN DEVELOPMENT
```

`document_date` is the date printed **on** the document, and for mortgage-
related filings it frequently encodes a loan term/maturity year instead of a
transaction date (hence years 7445–9798 on MERS/bank assignment documents);
it is NULL in 77 % of rows. The specific `2066-06-01` row is a grantee deed to
HUD recorded 2026-05-28 whose printed document date was entered as a future
year. Meanwhile `recording_date` moves continuously (max 2026-07-02) — the
registry already maps `recorded_date ← recording_date` for exactly this
reason (city_registry.py:1471-1475 cites docs/research/non-socrata-platforms.md
§Philadelphia) but still watermarks/orders on `document_date`. Note the Carto
sentinel filter bounds are `[1900, 2101)`, so 2066 passes the filter and sits
at the very top of the probe's DESC window; only the probe's separate
`value <= now` filter removes it. **Recommendation: switch
`watermark_col` and `extra.order_by` to `recording_date`.**

### Detroit — Assessor Property Sales (`assessor_property_sales_view/FeatureServer/0`), col `sale_date`

```
$curl '.../assessor_property_sales_view/FeatureServer/0?f=json'
→ name "Property Sales"; editingInfo.lastEditDate = 1787517263445 → 2026-08-23T20:34Z (yesterday)
   sale_date type esriFieldTypeDateOnly ("Date that the property sale took place.")

$curl '.../query?f=json&orderByFields=sale_date%20DESC&outFields=sale_date,sale_id&resultRecordCount=4'
→ sale_date 2925-12-24 (sale_id 4855071) · 2206-01-28 · 2202-11-20 · 2062-04-09

counts: sale_date BETWEEN '2026-06-01' AND '2026-08-24' → 2105 · sale_date >= '2100-01-01' → 3
total rows: 534779
```

The source is alive and current (edited yesterday; 2 105 real sales in the
last ~12 weeks); the future dates are typo-year artifacts on individual
transactions (2925 ≈ 2025 digit slip; the true year cannot be confirmed from
the API alone — recorded honestly). Exactly 3 rows exceed 2100 plus at least
one (2062-04-09) inside the band. The probe's `value <= now` filter already
absorbs these, and city_registry.py:780-786 documents the `'2925-12-24'`
sentinel. **No change needed.**

### Reconciliation note (CI figures vs HEAD behavior)

CI reported philadelphia/detroit watermarks of 2066-06-01 / 2925-12-24. At
current HEAD those values are strictly-after-now and should be dropped by
`newest_watermark()` (scripts/feed_staleness_probe.py:156), leaving both feeds
fresh-ish (Philly ≈ 2026-08-10 document_date / 2026-07-02 recording_date;
Detroit ≈ mid-August real sales). Either the quoted figures predate commit
d2302fb (2026-08-23 22:05 -0700, which touched carto_client ordering) or they
were read from a raw/unfiltered view. Not resolved from available evidence;
does not change any verdict above — the future-dated values exist regardless.

## Recommendations (spine — apps/api/src/spatial/city_registry.py — DO NOT EDIT from this stream)

Any change below touches a spine file and MUST go through the interlock
process (`pytest -m interlock` from `apps/api`, stream claim in `.streams/`,
dashboard wiring check per AGENTS.md).

1. **philadelphia/deeds — `watermark_col`: `document_date` → `recording_date`,
   same for `extra.order_by`.** Highest-value fix: turns a permanently
   sentinel-poisoned watermark into a continuously moving one. Low risk — the
   field_map already uses `recording_date`.
2. **san_francisco/deeds — `watermark_col`: `closed_roll_year` →
   `data_loaded_at`.** Fixes a column that has never parsed. Product follow-up
   separately: decide whether an annual tax roll satisfies the deeds signal at
   all, or register the staleness expectation explicitly.
3. **seattle/deeds — no column change exists.** Needs a source-replacement
   investigation (King County excise/REET sales or a refreshed KC open-data
   layer). Until then the feed will flag stale weekly — consider documenting
   the known-dead state in the registry comment so pages are actionable.
4. **nyc / chicago / new_orleans / washington_dc — no changes.** All four use
   the correct (only) recency column; staleness reflects genuine upstream
   cadence (ACRIS stall, MYDEC publish lag, NORA irregular disposals, CAMA
   batches). If the 7-day default threshold is too tight for these, tune
   `--threshold-days`/per-feed expectations rather than the registry.
5. Optional hardening (leaf-friendly): the Carto sentinel bound `< '2101-01-01'`
   admits in-band garbage (2066). If recommendation 1 lands this becomes moot
   for rtt_summary, but other CARTO tables inherit the same exposure.

## Verification gaps

- Norfolk/deeds (registered, `transfer_date`) was outside the CI stale list
  and was not probed here.
- The exact reason CI's philadelphia/detroit figures differ from HEAD
  filtering behavior could not be determined from repo state alone (see
  reconciliation note).
- All seven primary endpoints were verified live on 2026-08-24; none blocked.
