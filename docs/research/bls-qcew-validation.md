# BLS QCEW — validation pass (slow-moving economic-context feature)

**Date of validation: 2026-08-25. US-122.** Verdict: **DEFER (conditional register-later)** —
the source and distribution are unambiguously good, but QCEW is the coarsest,
most-lagged, most-version-fragile signal in the current slow-moving-context wave and
heavily overlaps LODES; it should be registered only after LODES/BFS land and after
explicit NAICS/geography/suppression version handling is built.

## Method, and its limits

Validation combined documentary evidence with direct empirical probes of the live
open-data distribution:

- **Documentary (BLS pages, Wayback).** `www.bls.gov` and `download.bls.gov` return
  403 to this environment's HTTP clients (curl and webfetch both blocked), so every
  BLS documentation page was pulled from Wayback captures dated Aug 2025–Jan 2026:
  `data-files-guide.htm`, `additional-resources/open-data/home.htm`,
  `open-data/csv-data-slices.htm`, `about-data/documentation-guide.htm`,
  `downloadable-data-files.htm`, `revisions/`, `news-release-technical-note.htm`,
  `about-data/news-release-notes.htm`, `classifications/areas/qcew-area-titles.htm`.
- **Empirical (live `data.bls.gov`, reachable).** The CSV-slice API is served from
  `data.bls.gov`, which this environment *can* reach. I confirmed by direct probe:
  the exact 42-column quarterly layout, that county/state/MSA slices resolve, the
  newest available quarter, suppression frequency, and the MSA-area comparability
  seam. Numbers marked "verified live" below come from those probes on 2026-08-25.

**Limits.** (1) BLS documentation pages could only be read as Wayback copies, so the
exact *current* language of any given page is not confirmed against the live site —
but the empirical probes validate the operative facts (layout, lag, suppression)
directly. (2) The formal BLS terms-of-use page was not reachable; terms are inferred
from the U.S.-government public-domain status of the data and the keyless CSV-slice
endpoints, not from a live reading. (3) The comparison signals LODES (`us101`) and
BFS (`us102`) are being validated by parallel streams whose docs did not exist at
writing time; every LODES/BFS claim here is framed against their *stated* intent
(their stream files) and marked provisional. Verify against those docs before
relying. (4) I did not attempt a full pipelined ingestion; the reproducibility plan is
designed from the confirmed URL/file contract, not a live E2E run.

## Headline verdict

**DEFER.** QCEW publishes authoritative quarterly employment, establishment, and wage
data for every county and every MSA, and the open-data CSV distribution is keyless,
public-domain, and trivially reproducible (confirmed live). That is the good half. The
problem is fit and timing, not access. QCEW is *quarterly* with a ~2-quarter (≈5–8
month) publication lag, so as of 2026-08-25 the newest available quarter is 2025 Q4.
It is *county/MSA only* — far too coarse for the H3 7–9 / submarket scale that is
Urban Signal's core, so it can only ever be a metro/division-level context layer, not
a feature. Its two genuinely non-redundant axes (total wages, establishment counts)
are exactly the axes least relevant to a real-time parcel/telemetry-driven submarket
model, while its employment axis is largely redundant with LODES (both derive from the
same state unemployment-insurance wage-record universe). Worst, the series is
deliberately version-fragile: BLS states plainly that QCEW data "are not designed as a
time series," and the MSA/NAICS/geography seams are real and empirically large — the
2023 OMB MSA delineation switch produced a **-17.5% year-over-year employment
"change"** in the New Orleans-Metairie MSA at 2024 Q1 that is administrative, not
economic, and county×industry cells suppress at **~76%** in a small parish. Before it
can be a trustworthy feature it needs explicit NAICS-version, MSA-delineation, and
suppression null-handling, and it must demonstrate incremental walk-forward value
against LODES and BFS — neither of which exists yet and neither of which it cleanly
beats. That is a register-later proposition, not a reject: the ingestion is cheap and
the source is excellent, so it belongs in the pipeline as a *later* metadata/corroborator
layer once the metro-context value case is proven by LODES/BFS.

## Source assessment

| Dimension | Finding | Evidence |
|---|---|---|
| **Distribution** | Open Data Access: keyless CSV *slices* covering the **most recent 5 years**, at `https://data.bls.gov/cew/data/api/<year>/<qtr>/<industry\|area\|size>/<code>.csv`. Full history (NAICS 1990→present, SIC 1975–2000) in year-bucketed zips at `data.bls.gov/cew/data/files/<year>/csv/…`. | data-files-guide (Apr 2025); open-data/home (Oct 2023); csv-data-slices; downloadable-data-files. Slices live-tested. |
| **File layout** | 42-column quarterly / 38-column annual CSV. Keys: `area_fips` (5-char), `own_code`, `industry_code` (NAICS/SuperSector), `agglvl_code`, `size_code`, `year`, `qtr`, `disclosure_code`, then levels + pre-computed location quotients + over-the-year change cols. | csv-data-slices (Sep 2024). Header confirmed live. |
| **Cadence** | Quarterly. National + state-level revision series also published after each news release. | revisions/ (Dec 2025). |
| **Publication lag** | Newest available quarter is **2025 Q4** as of 2026-08-25; **2026 Q1 returns 404** (not yet published). Per-quarter ≈5–6 months; the tail is ≈2 quarters behind "now." | **Verified live** (C3538 probes: 2025/1–2025/4 → HTTP 200; 2026/1 → 404). |
| **Revision policy** | Q1 data published **5×** (Sep ref-year → Dec → Mar → Jun → Sep), Q2 4×, Q3 3×, Q4 2×. "Data are preliminary and subject to revision until the data are finalized in the first quarter of the following year." Magnitudes small: establishments rarely change >±1% initial→final; employment/wages rarely >±0.1%. | revisions/ (Dec 2025); news-release-technical-note (Nov 2024). |
| **Geography** | National, state, **county (3,000+)**, and **MSA / CBSA / CSA** areas. County FIPS codes hold parity of state FIPS; **MSA-level rows use a C-prefixed 5-char code** (e.g. `C3538` New Orleans-Metairie MSA, `C4726` Virginia Beach-Chesapeake-Norfolk MSA). Independent cities (Norfolk, Virginia Beach, Chesapeake) and Alaska census areas appear as counties per FIPS; New England county data published for comparison. | area-titles + **verified live** (`C3538` resolves; bare `35380` 404s). |
| **Aggregation encoding** | `agglvl_code` encodes the geography×industry cross: `70`=county total, `71`=county×ownership, `72–78`=county×NAICS 2→6-digit; `50–5x`=state; `40–4x`=MSA; national/division variants. Ownership = `0` total, plus federal/state/local/private. | csv-data-slices; observed in live rows. |
| **Suppression** | Explicit `disclosure_code='N'` (plus `lq_disclosure_code`, `oty_disclosure_code`). Suppressed cells carry placeholder `estabs=1, empl=0`. **St. Bernard Parish (22087), 2023 Q1: 734 of 968 rows (~76%) suppressed** at county×industry detail; top-level total/ownership rows stay disclosable. State–local government data that were once suppressed were partially restored in 2022 (≈4.2M Jun-2022 employment). | csv-data-slices; news-release-notes (Sep 2025). **Suppression % verified live.** |
| **Coverage gaps (whole area)** | Colorado industry+substate data **suspended** Nov 2024 → resumed Feb 2025 after UI-modernization quality issues; statewide-only during the gap. (Matters: Denver is a registered metro.) | news-release-notes (Feb 2025 / Nov 2024). |
| **NAICS versioning** | NAICS **2022** used from **2022 Q1** full release (prior 2017, next ≈2027). NAICS revisions land at Q1. Also: establishments' industry/location/ownership classification re-verified on a **3-year cycle**, with changes introduced at Q1 — a source of discontinuity independent of NAICS revisions. | news-release-notes (Aug 2022); technical-note. |
| **Geography versioning** | **2023 OMB MSA/CBSA delineations** (Bulletin 23-01) take effect with the **2024 Q1** full data update (Sep 4, 2024); **historical data were NOT re-tabulated to the new definitions.** Connecticut replaced 8 counties with 9 planning-region county-equivalents starting 2024. | news-release-notes (Aug 2024); area-titles (CT note). MSA seam **empirically confirmed** below. |
| **Process change** | QCEW moved to **one data release** beginning with the 2024 Q4 publication (previously news-release-then-full-update). | news-release-notes (Jun 2025). |
| **Terms** | U.S. government dataset (public domain); no key for CSV slices. BLS attribution requested. Exact terms-of-use page **unverified** (site 403 to this env). | Live keyless slice success; terms page not reachable → mark unverified. |

### The MSA-delineation seam, empirically

The signature risk. The `C3538` (New Orleans-Metairie MSA) slice for 2024 Q1 shows
over-the-year change of **−17.5% employment, −21.7% establishments** (*verified live*).
A ~17.5% year-over-year employment drop is not an economic event; it is the admin
artifact of comparing a newly-delineated 2024 area against a pre-delineation 2023
base, exactly at the documented 2024 Q1 switch. Two consequences for feature design:

1. **Do not build an un-reconciled MSA time series across the 2024 Q1 seam.** Any
   MSA-level feature that stitches pre-2024 and 2024+ values will carry a spurious
   structural break for every affected area (including the Norfolk/Hampton Roads metro,
   which was **renamed** from "Virginia Beach-Norfolk-Newport News" to
   "Virginia Beach-Chesapeake-Norfolk" under the 2023 definitions — itself proof of a
   boundary change).
2. **County FIPS rows are the stable spine.** County codes (outside Connecticut)
   survive the delineation change, so a county-level series aggregated up to a metro
   is more robust than the C-coded MSA series. Prefer county→aggregation over MSA codes.

BLS explicitly warns: "QCEW data are not designed as a time series. QCEW data are
simply the sums of individual establishment records and reflect the number of
establishments that exist in a county or industry at a point in time." Admin changes
(a multi-unit employer splitting into single-unit reports in 2008 Q1, large admin
changes in 2011 Q2, state-verified reporting improvements in 2014 Q3) all land at Q1
and are *not* present in the raw published microdata as clean adjustments (only the
news-release over-the-year figures are adjusted). So a naive published-value time
series contains administrative discontinuities that must be treated structurally.

## Urban Signal fit

Urban Signal's urban unit is per-city: `METRO_BBOX` → hand-authored `DIVISION_BBOXES`
(planning-district-shaped) → `SUBMARKETS`, indexed to **H3 7–9 cells** for the
H3-keyed event streams (permits/311/license/deed). Registered context signals
(e.g. LODES/BFS/NLCD) are the outlier on purpose: they are *contextual* and carry an
ablation requirement before they may enter LIMS (see `FeedType` US-72 comments in
`city_registry.py`).

QCEW maps onto this as a **metro/division-level trend layer, nothing finer**:

- **Metro level** = the C-coded MSA (`C3538`, `C4726`) or a county-sum. Both align
  cleanly to a `CityRegistration`'s `metro_bbox` / census-metro footprint. Good fit for
  a top-of-funnel macro indicator.
- **Division level (feed geography)** — QCEW has *no* sub-county geography. It cannot
  resolve to a division bbox or a submarket. QCEW's only sub-MSA unit is the county
  (parish), which in the current model would sit between metro and division and would
  not align to any hand-authored division. This is the core fit limitation.
- **H3 7–9** — unreachable. QCEW is a categorical-geography (county/MSA) series with
  no coordinates; it cannot produce H3-keyed events. It is "contextual only," exactly as
  the issue's risk states.

**Effective join strategy:** don't try to key QCEW to H3. Instead store it at the
`metro` (or `census_msa` + `county_fips`) grain alongside the city's existing
registration, and join it into aggregation only at that coarse grain (e.g. as a
per-metro covariate). The city modules already carry the parish/county composition in
their bboxes, so mapping a `metro`/`CityId` to its QCEW county set + MSA code is a
small declarative table — not a geometry problem.

## Incremental-value check

Framed against the siblings (provisional — confirm in `us101`/`us102` docs):

- **vs LODES (us101). High redundancy on the employment axis.** BOTH LODES and QCEW
  derive from the same universe — quarterly state unemployment-insurance (UI) wage
  records, place-of-employment (see QCEW technical note). QCEW total employment at a
  county and LODES workplace jobs at a county are near-duplicates of the same underlying
  economy. QCEW's differentiators over LODES: **wages** and **establishment counts**
  (LODES provides job *counts* by block/segment only), **quarterly** cadence (LODES is
  annual/8 releases) and **MSA×NAICS** cuts that LODES doesn't tabulate. Net: QCEW adds
  wages + establishments + quarterly cadence, but its headline employment signal is
  redundant. Marginal value = the *wage* and *establishment* axes, at quarterly cadence.
- **vs BFS (us102). Complementary, not redundant.** BFS is a *flow/formation* signal
  (EIN applications, projected/actual employer births, time-to-formation) — a leading
  business-dynamics indicator. QCEW is a *stock* (standing employment/wage base +
  establishment count). QCEW's establishment count can **corroborate** BFS formation,
  and the two together tell "births → stock," but they overlap only loosely. This is the
  one axis where QCEW adds something neither LODES nor BFS supplies cleanly.
- **vs municipal telemetry (permits/311/license/deed/crime).** Completely different
  granularity and cadence. Telemetry is H3-level, near-real-time, and drives the
  submarket model directly. QCEW cannot substitute for any of it; it only supplies a
  coarse "is the metro broadly growing/flat/contracting" background. It does **not**
  duplicate parcel/H3 municipal signals — it complements them at a macro layer.

**Bottom line for incremental value:** QCEW's distinct contribution is a
**metro-level quarterly wage + establishment trend layer** and a stock-side companion
to BFS. That is real but narrow, and it is the least-relevant axes for a real-time
submarket model. Its strongest-and-most-redundant axis (employment) is what LODES
already plans to supply. Because it must clear an ablation requirement *against LODES
and BFS* to enter LIMS, and LODES/BFS don't exist yet, the value proposition cannot be
tested today — and on the merit axis, the prior probability of QCEW clearing it is low
(redundant employment + lagged + coarse + version-fragile).

## Reproducible ingestion plan

From the approved, confirmed public distribution (`data.bls.gov` CSV slices — keyless,
no auth). Per-metro declarative config, one row per registered metro:

```
# area codes (verified live 2026-08-25)
MSA codes (C-prefixed 5-char):  C3538="New Orleans-Metairie, LA MSA"
                               C4726="Virginia Beach-Chesapeake-Norfolk, VA-NC MSA"
County FIPS (stable spine):    NOLA: 22071 Orleans, 22051 Jefferson, 22087 St. Bernard
                               NORFOLK/Hampton Roads: 51710 Norfolk, 51810 Virginia Beach,
                               51550 Chesapeake
```

Ingest procedure:
1. **Pull area slices** `GET https://data.bls.gov/cew/data/api/<year>/<qtr>/area/<area_fips>.csv`
   for the metro's MSA code AND each constituent county FIPS, for each quarter.
2. **Filter** to `own_code` for private (and/or total `0`), and to the target
   `agglvl_code`s you actually need — default to `70` (county total) and `40` (MSA
   total) plus the NAICS cut you need at the highest non-suppressed level. Avoid
   4–6-digit NAICS at county for small areas (see suppression).
3. **Version every row.** Persist, per record:
   - `naics_version` (capture the mode: 2022, →2027) — from the Q1 announcement the data
     conform to.
   - `area_version`/`delineation` (pre-2023 vs post-2023 OMB definitions; the seam is
     **2024 Q1**). Never span this seam in a single un-versioned MSA series.
   - `disclosure_code` + `lq_disclosure_code` + `oty_disclosure_code` as-is.
   - `revision_stage` (initial/1st..4th revision) if you care about finality; simplest is
     to only ingest the *final* value for past quarters and the latest for the tail.
4. **Null handling.** Treat `disclosure_code=='N'` (and the `lq_`/`oty_` variants and any
   blank numeric) as `NaN`, **not** zero. Empirically St. Bernard returns `estabs=1,
   empl=0` under suppression — a zero here is a lie. Keep the disclosure flag so the
   feature can mask suppressed cells.
5. **Revisions.** For walk-forward, use each quarter's *final* published value (Q1 final
   ≈ Sept of the following year) rather than first-release, to avoid conflating revision
   noise with signal. The revisions/ page publishes national/state revision deltas; the
   downloadable year-zips carry the finalized history for the full backfill.
6. **History depth.** Open-data slices cover the most recent 5 years; for deeper training
   history use the year-zips under `data.bls.gov/cew/data/files/<year>/csv/` (e.g.
   `2024_qtrly_by_area.zip`, `2024_annual_by_area.zip`), which go back fully. Choose the
   minimum depth adequate to a ~5-year walk-forward; QCEW's own "not a time series"
   caveat argues against expecting long-run stationarity anyway.

## Risks and dependencies (mapped to US-122)

| Issue risk | Assessment | Mitigation |
|---|---|---|
| **Contextual only, not H3-level real-time** | Confirmed. County/MSA only, no coordinates → no H3 events. | Accept as metro/division context covariate only; never a LIMS event term; hold to the ablation gate. |
| **Suppression → explicit null handling** | Confirmed and severe: ~76% suppressed in a small parish at county×industry detail; `disclosure_code='N'` + `empl=0` placeholder. | Keep disclosure flags; null (not zero) suppressed cells; restrict NAICS detail to large counties or 2–3-digit SuperSector cuts. |
| **NAICS / geography revisions → explicit version handling** | Confirmed, two distinct seams: NAICS 2022→(≈2027) at Q1; **OMB MSA delineation at 2024 Q1** (empirical −17.5% artifact). Plus 3-yr classification re-verification back-loaded to Q1. | Dry `naics_version` + `area_version` columns; never stitch across 2024 Q1 MSA seam; prefer county→aggregate over C-coded MSA; version CT planning-region codes (2024+). |
| **MSA-delivery / area-designation changes** | Confirmed. 2023 OMB delineations effective 2024 Q1 (history not re-tabulated); Norfolk-area MSA renamed; QCEW moved to a single data release at 2024 Q4. | Track the area-titles CSV as an artifact; re-pull annually; treat area_code as a versioned dimension. |
| **Whole-area publication outages** | Confirmed: Colorado industry+substate suspended Nov 2024–Feb 2025 (UI modernization). | Treat per-area coverage-gap flags; don't impute across a suspension; surface as a data-quality flag, not a signal change. |
| **Lag vs.** a real-time app | Newest = 2025 Q4 as of 2026-08-25 (≈2 quarters). | Only for slow-moving trend/context; never a near-real-time input; align `expected_cadence_days` to the quarterly release calendar. |
| **"Not designed as a time series" (admin discontinuities)** | BLS's own caveat; admin changes (2008 Q1, 2011 Q2, 2014 Q3) land at Q1 un-adjusted in the published microdata. | Apply explicit discontinuity handling; consider adjusted OTY-derived (not level) features; prefer to use BLS-adjusted over-the-year values where a level discontinuity is suspected. |
| **Incremental value unproven / redundant with LODES** | Employment axis near-duplicate of LODES (same UI source); only wages/establishments add, and they're the least-relevant axes. | Do not register until LODES/BFS land; require the walk-forward ablation vs LODES+BFS; drop if it adds nothing. |

**Dependencies.** (1) LODES (`us101`) and BFS (`us102`) must be validated/built first —
the ablation requirement is defined *against* them. (2) A version-aware store/state
model (the repo already versions DatasetSpec `extra` / config; a new `context_signal`
registry entry would need `naics_version` + `area_version` + disclosure masks). (3) A
coverage-gap/discussion document for whole-area outage handling. (4) No existing
producer is a fit — this is neither Socrata nor ArcGIS, so it needs new keyless-HTTP-CSV
ingest (small; the `PaginatingClient` protocol does not apply). None of this is spine
touching; it can be a leaf module.

## Recommendation

**Defer, and register later with preconditions.** Endorse the distribution (keyless,
public-domain, reproducible; confirmed live) and the source (authoritative UI-record
county/MSA data). Do *not* register QCEW into the pipeline now, because: (1) it must be
evaluated for incremental value against LODES and BFS, neither of which exists yet;
(2) it is the coarsest (county/MSA) and most lagged (~2 quarters) of the three, and the
least relevant to H3 7–9 / submarket real-time analysis; (3) its MSA+NAICS+suppression
versioning burden is high and its employment axis is redundant with LODES. When the
wave's LODES/BFS verdicts land:

- If LODES/BFS register as context layers, **add QCEW only for the two axes they lack**
  — quarterly metro **wage** and **establishment** trend (as a BFS-stock corroborator) —
  keyed at `metro`/`county_fips` + `naics_version` + `area_version`, with disclosure
  masks. Do not re-add the employment axis.
- If the metro-context layer is itself deferred/rejected, **reject QCEW** — it is a
  strict subset of that decision and adds nothing at H3 scale.
- Before any register, run one evidence pass in exactly two current metros — **New
  Orleans** (C3538; 22071/22051/22087) and **Norfolk/Hampton Roads** (C4726;
  51710/51810/51550) — measuring: publication lag, actual suppression rate at the target
  NAICS cut, the magnitude of the 2024-Q1 MSA seam, and walk-forward Δ-AUC/LIMS increment
  over LODES+BFS-only. The two-metro test is where the DEFER becomes a REGISTER or a
  REJECT.

**Practical near-term use (optional, zero-cost):** even if not a registered feature,
the same two-metro dataset can seed the metro-level "context" display today at near-zero
cost, because ingestion is one HTTP GET per area per quarter and storage is tiny
(~1,768 rows per MSA slice). Worth holding as a manual reference until the value case is
proven.
