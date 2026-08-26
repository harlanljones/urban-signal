# HMDA mortgage-activity — validation as a contextual signal for neighborhood change / investment pressure

**Date of research: 2026-08-26.** The CFPB HMDA Data Browser and HMDA Platform
documentation were probed live. **Live JSON/CSV probing was blocked in this
environment** (see Method, limits): the Data Browser is a client-rendered SPA
that returns the same `index.html` for every `/data-browser/...` route, and the
developer-API documentation page serves a `.gov` interstitial, so the JSON API
host/path could not be exercised here. Every HMDA structural claim below is
therefore sourced from **authoritative HMDA/CFPB documentation** (statute,
regulatory definition, and the published LAR data dictionary) and is marked
accordingly; anything not confirmable from those docs is flagged **unverified**.
This is a *validation* document — no feed was registered, no `.py` was wired into
the pipeline (a small, unintegrated leaf metrics helper is provided as a
feasibility proof, never imported by spine code).

## Method, and its limits

I validated on two layers:

1. **Authoritative source facts.** HMDA statutory basis (12 U.S.C. § 2801 et
   seq.), CFPB administration since 2011 (Dodd-Frank transfer from the Federal
   Reserve Board), the covered-institution thresholds, the filing calendar, and
   the Loan Application Register (LAR) data dictionary (variables, action-taken
   codes, loan-purpose codes, occupancy-type codes). These are documented public
   facts, cited from CFPB/FFIEC HMDA materials.
2. **Repo fit by concept.** Mapping HMDA's geography (census tract), cadence
   (annual), and metrics (purchase/investor/denial) against the repo's feed
   families and its H3 7–9 / division / submarket units, using the same reasoning
   pattern applied to the LODES (`docs/research/census-lodes-validation.md`) and
   QCEW (`docs/research/bls-qcew-validation.md`) validations.

**Limits.** I did **not** download the loan-level dataset or run an aggregation
(environment blocked the file/API endpoints). No numeric metro rollup is
presented as a measured file characteristic — unlike the LODES validation, which
downloaded and aggregated real files. "Incremental value against current
signals" is assessed by *concept* against the repo's feed families, not by
running an ablation. The exact 2023 national record count and the precise
2024/2025 release dates are stated as approximate/documentation-derived and
flagged where uncertain.

## Headline verdict

**DEFER (reject-leaning).** HMDA is an authoritative, free, federal,
nationally-uniform mortgage-activity dataset whose **investor-occupancy share**
and **denial/credit-access rate** are dimensions **no existing Urban Signal feed
measures** — the `DEEDS` feed captures the *sale event* but cannot tell whether
a financed buyer was an investor vs. owner-occupier, and carries no denial-rate
axis. So HMDA adds *genuine independent coverage* on the buyer-type / financing
axis. **But** it duplicates the transaction/velocity core that `DEEDS` already
provides, it is **coarser than the target units** (census tract, not H3 res 7–9 —
the *inverse* of the LODES granularity situation), it is **annual with a
~12–18-month lag**, and it is **not an event stream** (no watermark, no per-row
coordinates, bulk CSV by tract), so registering it requires a **new signal
family + bulk-file producer + aggregate storage = a spine/interlock change**,
exactly out of scope for a leaf stream. Because the truly unique HMDA axes
(investor share, denial rate) are slow, tract-coarse *context only*, and the
transaction core is already covered by `DEEDS`, the case for the costly spine
change is weaker than LODES (which added an entirely missing demand-side
dimension). Shelf it; the unblock path is small and specific (below).

---

## Source assessment

- **Authority / terms.** HMDA is a U.S. federal law (12 U.S.C. § 2801 et seq.);
  data are collected by the CFPB and published as public data. The public
  datasets (modified LAR, aggregate reports) are U.S. government works —
  **public domain (17 U.S.C. § 105), no API key, no registration, no
  authentication** for the public Data Browser downloads and API. (The specific
  HMDA written terms-of-use page was **not fetched — unverified**; the
  public-domain statutory basis is the authoritative part.)
- **Access paths.** Two public surfaces: the **HMDA Data Browser**
  (`https://ffiec.cfpb.gov/data-browser/...`) — web UI + JSON API + downloadable
  datasets — and the **Loan-Level Dataset (modified LAR)** CSV files (one per
  state per year, plus a national file), documented in the HMDA Platform
  data-dictionary. Both confirmed reachable (HTTP 200) but JSON-content blocked
  in this sandbox (SPA fallback).
- **Covered institutions / coverage.** Depository institutions and their
  affiliates above an asset threshold (≈ $56M in 2023, inflation-adjusted
  annually) report; since 2018 (filing year 2019) larger non-depository mortgage
  lenders above threshold also report. Coverage is **nationwide, all states +
  territories**, every year from 2001 onward in the modern schema. A metro
  subset (e.g. New Orleans, Norfolk) is a small slice of the national file.
- **Geographic granularity.** **Census tract** (11-digit FIPS: state+county+tract)
  is the **finest public geography** in the LAR. Exact addresses and
  lat/lng were removed from the public file for privacy (post-2010); the public
  LAR carries only the tract code (and `msa_md`, `state_code`, `county_code`).
  **This is coarser than H3 res 7–9**, so HMDA cannot be point-resolved into
  cells — it must be *areally apportioned* from tract → H3 (each tract spans many
  res-9 cells), which smears a tract metric across all cells it covers. The
  inverse of the LODES "block is finer than H3" situation: here the source is the
  coarse one, so there is **no intra-tract resolution gain**, only loss.
- **Cadence / latency / reference period.** **Annual.** Covered institutions
  file by **March 1** for the prior calendar year; CFPB publishes the public
  data typically **summer–fall** of the filing year (e.g. 2023 data released
  ~mid-2024). Effective lag **~12–18 months**. Each year is a **stock/flow of
  that calendar year's applications** — a level, not a continuous event stream.
- **Volume (approximate, documentation-derived).** Nationally on the order of
  **~10–13 million loan records per year** (2023); the metro subset needed for a
  signal is a few hundred thousand rows at most. The loan-level CSV is large
  (national file hundreds of MB zipped) but the metro filter makes a signal
  payload small — though, unlike event feeds, the *whole-year file* must be
  downloaded and filtered, not paginated.
- **Revisions / reproducibility.** HMDA is a **filed** dataset, not a revised
  time series — once published, a year's LAR is stable (the platform may correct
  institutional submissions, but the public annual snapshot is the unit). A
  pipeline can pin year + schema version; no watermark/vintage churn like LODES.
- **Key variables (LAR data dictionary).**
  - `action_taken`: 1 originated, 2 approved-not-accepted, 3 denied, 4 withdrawn,
    5 closed-for-incompleteness, 6 purchased loan, 7 preapproval approved,
    8 preapproval denied. → **denial rate** = (3) / (1,2,3,4,5,...) applications.
  - `loan_purpose`: 1 home purchase, 2 home improvement, 3 refinance (cash-out
    split out since 2018). → **purchase-loan intensity**.
  - `occupancy_type`: 1 owner-occupied principal dwelling, 2 second residence,
    3 **investor / non-owner-occupied**. → **investor-purchase share** (the
    decisive, deeds-reconstructable-never axis).
  - `loan_type`: 1 conventional, 2 FHA, 3 VA, 4 RHS/FSA. → **government-backed
    (FHA/VA) share** = first-time / lower-income buyer pressure.
  - `loan_amount`, `property_value` (originations; property value reporting
    expanded post-2018), `lien_status`, `rate_spread` (higher-priced flag),
    `debt_to_income_ratio` (2018+), `denial_reason`.

---

## Urban Signal fit

Urban Signal units are strictly nested: **metro bbox → division bbox(es) →
submarket → H3 cells 7–9** (`spatial/h3_indexer.py`: res 7 ≈ 5.16 km², res 8 ≈
0.74 km², res 9 ≈ 0.105 km²). Each event feed is bbox-filtered at ingest, then
each row → `h3_res7/8/9` via `H3SpatialIndexer.get_multi_res_hierarchy`.

**HMDA's granularity is the wrong direction for H3.** Census tracts average
~4,000 people and are typically 1–10 km² — **larger than an H3 res-7 cell** in
many dense metros, and far larger than res 9. A tract metric therefore cannot be
point-resolved; it must be **areally apportioned** (e.g. tract centroid → one H3
cell, or tract-area-weighted split across the cells it covers). Either way the
tract carries *no* sub-tract signal, so the repo's res-9 "micro block/parcel
catalyst" resolution is **unreachable** from HMDA — it can only ever inform
**division / submarket / res-7** context. This is a harder fit than LODES (block
→ H3 rollup preserved resolution) and worse than the event feeds (point-exact).

Required (future) mapping work, if ever registered:
1. **Tract → coordinate.** Use the tract **centroid** (Census TIGER
   `tract` shapefile / `tigerweb`; the LAR has no lat/lng). New geometry
   dependency not currently in the repo. (Caveat: centroid-in-cell assignment
   mislocates tracts that straddle a cell boundary; area-weighting needs tract
   polygons, which the LAR does not ship.)
2. **Coordinate → metro.** Filter by the repo's metro bbox exactly as event
   feeds are bbox-filtered (county FIPS alone over-counts city-scoped metros
   like Norfolk, by analogy to the LODES validation's Norfolk finding).
3. **Coordinate → division/submarket.** Reuse `get_division_for_coordinate` /
   `find_nearest_submarket` on the tract centroid — but note the centroid may
   land in a neighboring division for boundary tracts, so boundary tracts need a
   containment check, not just nearest-center.
4. **Rollup → H3.** Assign the tract's loan counts to its covering cell(s).
   Because a tract ≫ a res-9 cell, the honest target is **res 7** (macro) and
   division/submarket; res 8/9 would be pure areal smearing with no added signal.

**Does it add coverage the current feed-derived signals do not provide?** Partly.
The feed families — permits, 311, SLA, deeds, crime, evictions, STR,
street-cut — are all **events**. `DEEDS` measures the **sale/transfer event**
(velocity, value at the parcel). HMDA measures the **financed** side of
transactions plus **buyer type and credit access**:
- **investor-occupancy share** among purchase loans — a **speculation /
  capital-inflow pressure** signal that *no* event feed reconstructs (deeds
  record the transfer, not whether the buyer is an investor);
- **denial rate** — a **credit-access / distress** signal absent from every
  current feed;
- **FHA/VA (government-backed) share** — first-time / lower-income buyer
  pressure.

That is independent coverage on the **buyer-type and financing** axis. But it is
**redundant** with `DEEDS` on the *transaction-count / velocity* core (a home
purchase loan and a recorded deed are largely the same event, minus cash sales
and plus refis), and it is strictly **slower and coarser** than deeds. So HMDA's
net *unique* contribution is narrow: investor share + denial rate as
division/submarket context.

**The integration-model problem is the same class as LODES/QCEW.** A
`FeedType` is required for a `CityRegistration` to expose a signal, and each
`DatasetSpec` assumes a `PaginatingClient` (Socrata/ArcGIS/CKAN `$offset`),
a `watermark_col`, and `id_keys` per geolocated event row. HMDA violates all of
them: it is a **stateless per-state/annual CSV** (or bulk Data Browser download),
keyed by tract code with **no per-row coordinates**, no event semantics, no
watermark, bulk delivery. Registering it "as a feed" requires a **new signal
family** (`FeedType.MORTGAGE` / `INVESTOR_PRESSURE`), a **new producer
archetype** (download → tract→H3 areal apportionment), and a new **aggregate
(table) shape** (H3-cell / division loan-count aggregates, not event rows) — a
spine/registry change gated by `pytest -m interlock`, out of scope for a leaf
stream.

---

## Two-metro feasibility (concept, not measured)

Same anchors as the LODES validation (both registered metros, both fully HMDA-
covered states): **New Orleans** (LA: Orleans 22071, Jefferson 22051, St.
Bernard 22087) and **Norfolk/Hampton Roads** (VA: 51710/51810/51550).

- **Expected ingest path.** Download the modified-LAR CSV for the metro's state
  year (LA/VA, one file each, ~tens–hundreds of MB zipped), filter to the metro's
  county FIPS *then* bbox-filter the tract centroids (county join over-counts
  Norfolk per the LODES finding), attach tract centroid, resolve to division /
  submarket / res-7, and compute per-cell loan counts (purchase, investor,
  denied). No crosswalk join needed (tract is already the LAR geography), but a
  **tract-centroid geometry source is a new dependency**.
- **Feasibility of the *download + filter* step: easy.** Metro subset is small.
  But the **areal-apportionment + geometry dependency + new producer archetype**
  is the real cost, and it is spine-coupled.
- **Resolution ceiling.** Only division / submarket / res-7 context is honest;
  res 8/9 would be pure smearing. This caps HMDA to a coarse anchor, never a
  res-9 catalyst signal.

---

## Independent coverage check (vs. the existing feed families)

| Dimension | Existing feed-derived signals | HMDA mortgage activity |
|---|---|---|
| Unit | geolocated **event**, H3 cell (res 7–9) | **census tract** aggregate → res 7 / division only |
| Latency | near real-time (daily/weekly) | **annual, ~12–18-mo lag** |
| Concept | *events* (permit, complaint, sale, crime, eviction) | *financed transaction + buyer type + credit access* |
| Coverage | only metros with that feed | every US tract in covered years |
| Unique axes | none on buyer type / credit access | **investor share, denial rate, FHA/VA share** |
| Redundant with | `DEEDS` (transaction core) | `DEEDS` (purchase ≈ sale) |

**Does it add independent coverage?** Yes, but **narrowly**: only on the
buyer-type (investor occupancy) and credit-access (denial rate, government-
backed share) axes, which no event feed produces and which `DEEDS` cannot
reconstruct. It is **redundant** with `DEEDS` on transaction velocity/value, and
**inferior** to deeds on timeliness and resolution. Under the repo's rule (a
signal is retained only if it adds independent coverage *and* clears its family
gate at target resolution/timeliness), HMDA clears the "independent coverage"
test only on two narrow axes, and fails the "usable at target resolution /
timeliness" test for *scoring* — it clears both only for a **coarse context**
role, and even there it needs a spine change.

---

## Risks and dependencies (mapped to the issue's risks)

1. **"Annual cadence / multi-month lag unsuitable for short-term change
   detection."** **Confirmed, binding for any LIMS/scoring role.** March-1 filing
   + summer/fall release → ~12–18-month lag, annual only. HMDA can only ever be a
   **trailing context/anchor**, never a leading signal. Same conclusion class as
   LODES/QCEW.
2. **"Tract-level, coarser than H3 res 7–9 — no intra-tract resolution."**
   **Confirmed, and worse than LODES.** Source is *coarser* than target, so
   areal apportioning smears; res 8/9 are unreachable as honest resolution. Caps
   HMDA to division / submarket / res-7 context. (LODES was finer-than-target and
   thus clean to roll up; HMDA is the opposite.)
3. **"Requires census-tract geometry / city-level calibration."** **Partially
   open.** The LAR already keys on tract, so no crosswalk join is needed — but a
   **tract-centroid (or polygon) geometry source is a new repo dependency** not
   present today (the LODES crosswalk shipped coordinates; HMDA ships none).
   "City-level calibration" is real: investor-share and denial-rate baselines
   differ enormously by metro and must be **ratio/index-normalized per metro**,
   never used as raw national counts. Boundary tracts need containment checks,
   not centroid-nearest, to avoid mis-assigning divisions.
4. **Integration-model dependency (decisive).** No `FeedType` exists for a
   non-event, tract-aggregate layer. Current families: `PERMITS`,
   `COMPLAINTS_311`, `SLA`, `DEEDS`, `CRIME`, `STREET_CUT`, `EVICTIONS`, `STR`.
   HMDA needs a **new** signal family (`MORTGAGE` / `INVESTOR_PRESSURE`), a
   **new producer archetype** (bulk CSV download → tract→H3 areal apportionment),
   and **new aggregate storage** (H3-cell / division loan-count rows, not
   `h3_res7/8/9`-on-event rows the pipeline and Postgres sync assume) — exactly
   the spine/interlock change `docs/agents/parallel-streams.md` gates, and out of
   scope for this leaf stream.
5. **Redundancy-with-DEEDS dependency.** Because purchase loans ≈ recorded
   deeds on the transaction core, registering HMDA mainly buys the investor /
   denial axes. If the project's `DEEDS` coverage is already strong in a metro,
   HMDA's marginal value there is small; it is most valuable precisely where
   `DEEDS` is weak/uneven (fragmented county recorders), which argues for a
   *selective* register, not a blanket one.

---

## Recommendation

**DEFER (reject-leaning)** — do not register now. HMDA is authoritative,
free, and nationally uniform, and its **investor-occupancy share** and
**denial/credit-access rate** are genuine independent coverage that `DEEDS` and
every other feed lack. **Do not register** because (a) it is **redundant with
`DEEDS`** on the transaction/velocity core that matters most for scoring, (b) it
is **coarser than the target units** (census tract → only res-7/division context,
the opposite of LODES's clean rollup), (c) it is **annual / ~12–18-mo lagged**,
so context-only, and (d) it needs a **spine/interlock change** (new `FeedType` +
bulk-CSV producer + aggregate storage) that is out of scope for a leaf stream. It
is a **weaker** defer than LODES: LODES added an entirely missing demand-side
dimension, whereas HMDA mostly overlaps `DEEDS` and contributes only two narrow
context axes. **Do not reject outright**: if a "buyer-type / speculation-pressure"
context layer is wanted, HMDA is the right source for it.

**What unblocks a future REGISTER (any one, or in combination):**

1. A positive **scope decision** for a structural **mortgage / buyer-type context
   layer** — a new `MORTGAGE`/`INVESTOR_PRESSURE` signal family, its own
   `DatasetSpec`-adjacent spec, its own H3-aggregate (division / submarket / res-7)
   table, and a bulk-CSV producer — treated as context/LIMS-exempt (precedent:
   street-cut "disruption context only — never a LIMS term").
2. A concrete consumer that needs it — e.g. an **explanatory "speculation
   pressure" feature** (investor-purchase share + denial rate as a prior under the
   hardcoded `base_lims`/`capex`/`sla` baselines), or a **credit-access /
   first-time-buyer exposure** view no event feed supplies.
3. If both arrive, **register selectively** — only metros where `DEEDS` coverage
   is weak/uneven (fragmented recorders) — as a **metro-normalized annual index at
   division / submarket and H3 res 7**, areally apportioned from tract centroids
   with boundary-tract containment checks, and explicitly calibrated so investor
   share / denial rate are **ratios within a metro**, never raw national counts.

Until then, `DEEDS` remains the correct timely transaction signal, and HMDA should
not be wired in as a scoring input. A small, **unintegrated** leaf helper
(`apps/api/src/spatial/hmda_metrics.py`) demonstrates the tract→H3 apportionment
and the investor-share / denial-rate computations so the future register path is
concrete; it is not imported by any spine or pipeline code.

---

## Leaf artifact

`apps/api/src/spatial/hmda_metrics.py` — pure functions:
`investor_purchase_share`, `denial_rate`, `government_backed_share`,
`rollup_tract_to_h3` (centroid assignment + optional area-weighted split), with
`apps/api/tests/unit/test_hmda_metrics.py`. No spine import; leaf-only.
