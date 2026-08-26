# Census ACS — neighborhood baseline features evaluation (US-166)

**Date of research: 2026-08-26.** The ACS *data* API, the variable catalog, and the
Census Gazetteer tree were probed live from this environment. Where a claim could not
be confirmed remotely it is marked **unverified**. This is a *validation* document —
the only code shipped is a self-contained, network-free leaf helper
(`apps/api/src/spatial/acs_baseline.py`) plus a unit test; no feed was registered and
no spine file was opened.

## Method, and its limits

I validated on two layers:

1. **Live API probe.** Fetched the ACS variable metadata (`api.census.gov/data/2023/
   acs/acs5/variables/<code>.json`) for the candidate feature codes — confirmed each
   carries an estimate (`*_001E`) **and** a margin of error (`*_001M`, plus annotated
   `*_001MA`). A live *data* query (`.../acs5?get=...&for=state:22`) returned an
   explicit **"Missing Key"** page — i.e. the ACS Data API now **requires a (free)
   Census Data API key** for data rows, though the variable-metadata endpoints remain
   keyless. This is a material change from the keyless LODES file downloads and is
   flagged below.
2. **Geolocation path probe.** Listed `www2.census.gov/geo/docs/maps-data/data/
   gazetteer/2023_Gazetteer/` and downloaded `2023_Gaz_tracts_national.zip` to confirm
   the internal-point columns (`INTPTLAT`/`INTPTLONG`) — **present on tracts, places,
   ZCTA, counties, but the block-group Gazetteer was removed** (no `*_Gaz_blockgroups_*`
   in the 2023 tree). Block-group centroids must therefore come from a TIGER/Line
   block-group shapefile or be *derived* from the LODES crosswalk block internal points
   (`blklatdd`/`blklondd`), since a 15-char block FIPS (`tabblk2020`) shares its first
   12 chars with its block group. The sibling LODES validation wave already proved that
   crosswalk downloads are keyless and clean, so the geolocation dependency is satisfiable
   without a new source.

**Limits.** I did not obtain an API key, so no live block-group *estimate* rows were
pulled; the feature set below is built from the confirmed variable catalog and standard
ACS geography/cadence facts, not from a measured metro extract. MOE magnitudes at block
group are asserted from the known ACS design (small samples per BG) rather than measured
on a specific metro; a real pilot should print per-feature CV at res 7/8/9 before adoption.

## Headline verdict

**ADOPT (as a trailing context/baseline layer) — conditional on a free API key and an
H3 rollup.** ACS is the best-fit source in the validation wave for the *neighborhood
baseline features* the repo hardcodes today (`base_lims`, `capex`, `permit_vel`,
`shift_ratio`, `sla` in `SubmarketMeta`): it is demographic/housing/income/commute by
nature, it reaches the **block group** (the finest geography that nests cleanly under
H3 7–9), it is **not** synthetic (survey estimates with transparent 90% MOEs, unlike
LODES), and its **5-year cadence lags only ~12 months** (2023 5-year released Dec 2024)
— an order of magnitude fresher than LODES' ~28-month lag. The decisive risk is the
**margin of error at block-group scale**, which is solved the same way LODES' synthetic
noise is: roll up to H3 res 7–9 (hundreds of block groups per cell) with the repo's
existing `dynamic_spatial_fallback` for sparse cells, propagating MOE by the Census
quadrature formula rather than averaging. Crucially, unlike LODES, ACS *can* be wired as
a feed-shaped pull (keyed HTTP GET, stable variable codes, per-geography rows) — but it
still needs a **block-group → H3 resolution step** (no coordinates on the row), so it
is a leaf *baseline-enrichment* module, not a drop-in `FeedType`, unless/until a
baseline signal family is added.

---

## Source assessment

- **Access / terms.** U.S. federal public-domain data (17 U.S.C. § 105). **The data API
  now requires a free `key` parameter** (verified: "Missing Key" response). Keys are
  free, rate-limited (~500 req/day unauthenticated historically; with key, higher
  daily cap), and stored as a secret/config value — a trivial but real integration
  dependency. Metadata endpoints are keyless. File products (Gazetteer, TIGER/Line,
  the underlying CSVs) remain keyless at `www2.census.gov`. **Written terms-of-use page
  not fetched — unverified**, but the public-domain statutory basis is the verified part.
- **Product families.** `acs1` (1-year, pop ≥ 65,000 only), `acs3` (discontinued),
  `acs5` (5-year, **all geographies incl. block groups**, most reliable), plus DP
  (profile) and S (subject) table views over the same estimates. For *neighborhood*
  features at block group, **only `acs5` qualifies** — `acs1` omits block groups
  entirely.
- **Geographic granularity.** **Block group** (12-digit FIPS: state 2 + county 3 +
  tract 6 + BG 1) is the finest ACS unit and the recommended baseline grain; census
  **tract** (6-digit within county) is the coarser fallback. Both nest under the repo's
  H3 7–9 cells (res 9 ≈ 0.105 km²; a block group is ~0.5–2 km², i.e. a handful of res-9
  cells, exactly the aggregation LODES proved works). **Coordinates are NOT on the ACS
  row** — geolocation requires a TIGER/Line BG shapefile or the LODES-crosswalk-derived
  BG internal point (see Method).
- **Cadence / latency / reference period.** ACS 5-year is released **annually**, each
  vintage covering a rolling 5-year window (2023 5-year = 2019–2023), published ~12
  months after the reference year-end (Dec 2024 for 2023). Each new 5-year **supersedes**
  the prior (overlapping windows) — so it is a slowly-revising *level*, not a flow. This
  is far fresher than LODES but still **trailing**: it can anchor baselines and priors,
  never drive short-term change detection (the event feeds own that).
- **Volume.** Per metro, block-group rows number in the low tens of thousands (a metro
  ≈ few thousand tracts → ~10–20k block groups); each row is ~1–2 KB of JSON. A full
  metro pull is a few MB and a few hundred API calls (batchable 50 vars/call) — trivial
  versus the event backfills. The variable catalog is stable year-to-year (table codes
  persist across vintages; the 2023 vintage is the current one).
- **Margins of error (the defining property).** Every estimate ships a 90%-CI MOE
  (`*_001M`; medians also ship `*_001MA`). At block group, sample sizes are small, so
  CVs are frequently high (10–30%+ on income/housing sub-counts). The cure is aggregation:
  rolling block groups up to H3 res 7–9 (hundreds of BGs per cell) shrinks the relative
  MOE by `1/sqrt(n)`, and the repo's `dynamic_spatial_fallback` already coarsens sparse
  cells. Counts aggregate by quadrature (`MOE_sum = sqrt(Σ MOE_i²)`); ratios/proportions
  by the Census ratio formula; **medians cannot be summed** and must be rolled up as a
  population-weighted mean of block-group medians (an approximation, flagged in code).

---

## Proposed baseline feature set

Semantic feature → ACS variable (all `acs5`, estimate + MOE). These map directly onto
the repo's hardcoded submarket baselines and onto candidate "demand anchor" context:

| Baseline feature | ACS variable | Type | Maps to repo baseline |
|---|---|---|---|
| Total population | `B01003_001E` | count | density prior |
| Median age | `B01002_001E` | median | demographic context |
| Race/ethnicity mix (Non-Hispanic White / Black / Asian / Hispanic) | `B03002` (002–013) | count→share | neighborhood composition |
| Median household income | `B19013_001E` | median | `capex`/`base_lims` anchor |
| Per-capita income | `B19301_001E` | median | income stress proxy |
| Poverty rate (ratio of poverty pop / total) | `B17020_001E` / `_002E` | ratio | distress signal |
| Total housing units | `B25001_001E` | count | stock prior |
| Owner-occupied share | `B25003_002E` / `_001E` | ratio | stability anchor |
| Renter-occupied share | `B25003_003E` / `_001E` | ratio | `sla`/`shift_ratio` context |
| Median gross rent | `B25064_001E` | median | renter cost burden |
| Median home value | `B25077_001E` | median | equity/permit-vel context |
| Housing cost burden ≥30% (share) | `B25070` (010 / 001) | ratio | distress signal |
| Means of transport to work | `B08301` (car / transit / walk / other) | count→share | commute context |
| Median travel time to work | `B08303_001E` | median | commute burden |
| Worked-from-home share | `B08302_001E` / `B08006` | ratio | post-COVID structure |
| Vehicles available per household | `B25046` | median/mean | car-dependence |

`acs_baseline.py` encodes this catalog (`ACS_BASELINE_FEATURES`) with each feature's
aggregation rule (`sum`, `ratio`, `weighted_median_approx`) so the rollup is mechanical.

---

## Urban Signal fit

Urban Signal units nest: **metro bbox → division → submarket → H3 7–9**
(`spatial/h3_indexer.py`). Today the submarket baselines (`base_lims`, `capex`,
`permit_vel`, `shift_ratio`, `sla`) are **hardcoded constants**. ACS is the natural
*data-derived* replacement or calibration source for those constants: instead of a
fixed `capex` number per submarket, derive a median-income / value-anchored prior and
let event feeds perturb it. The ingest shape is:

1. **Pull** block-group estimates + MOEs for the catalog (keyed API GET, batched 50
   vars/call), filtered by state+county FIPS inside the metro (or by a BG FIPS list).
2. **Geolocate** each block group to an H3 cell: derive the BG internal point from the
   LODES crosswalk block points (12-char prefix of `tabblk2020`) or a TIGER BG
   centroid, then `latlng_to_cell(., res)` per `H3SpatialIndexer`. No new coordinate
   source is strictly required.
3. **Roll up** to H3 7–9 by the catalog's agg rule, propagating MOE (sum quadrature /
   ratio formula / weighted-median approx), then apply `dynamic_spatial_fallback` for
   sparse cells — the same smoothing that de-noises LODES.
4. **Fold into** `SubmarketMeta` baselines as a trailing prior/context, never as a LIMS
   term (precedent: street-cut "disruption context only").

**Incremental coverage vs. existing feeds.** The event feeds (permits, 311, SLA, deeds,
crime, evictions, STR, street-cut) are all *transactions*. None measures the *structural
neighborhood* — who lives there, what they earn, how they house and commute. ACS is the
demand/structure half of the metro that no event feed can reconstruct, and it is the
first validation-wave source that is (a) non-synthetic and (b) fresh enough (~1 yr) to
serve as a standing baseline rather than a 28-month-stale anchor.

---

## Risks and dependencies (mapped to the issue's risks)

1. **"Margin-of-error at small geographies."** **Confirmed and binding at block group.**
   Small BG samples give 10–30%+ CVs on sub-counts. Mitigation (repo-native): roll up
   to H3 res 7–9 and use `dynamic_spatial_fallback`; propagate MOE by the Census
   quadrature/ratio formulas so every published feature carries its own uncertainty.
   Medians are aggregated as a weighted mean (approx) and flagged. Residual block-group
   noise is acceptable only because it is *smoothed by aggregation*, never used raw.
2. **"Latency unsuitable for short-term change detection."** **Partly mitigated.** ACS
   5-year lags ~12 months (vs LODES' ~28) and revises yearly, so it is a *trailing
   baseline/prior*, not a leading signal. This is by design: it backs the hardcoded
   `base_lims`/`capex`/`sla` constants, which are themselves slow, not the event-driven
   LIMS terms. Recommendation: **context/anchor role only**, never a scoring input.
3. **"Requires block-group geometry/crosswalk processing."** **Real but small.** ACS
   rows carry no coordinates; the 2023 Gazetteer dropped block groups. The fix is to
   reuse the LODES crosswalk block internal points (keyless, already proven) or a TIGER
   BG shapefile to attach a BG centroid, then `H3SpatialIndexer`. This is the same
   join LODES needs, so the cost is shared, not new.
4. **API-key dependency.** **New finding (verified).** The data API now returns
   "Missing Key"; a free Census Data API key must be configured as a secret and passed
   on every request. Low effort but a real secret/config addition — note it in
   `config.py`/deploy docs when adopted (that edit is spine-ish and out of this leaf's
   scope; flagged for the adopting stream).
5. **Median-variable aggregation.** Medians (`B19013`, `B25064`, `B25077`, `B08303`,
   `B01002`, `B19301`) cannot be summed; the leaf module uses a population-weighted
   mean of BG medians as a documented approximation. Treat aggregated medians as
   indicative, not exact — another reason ACS is *context*, not a precise count.

---

## Recommendation

**ADOPT as a trailing neighborhood-baseline / context layer, conditional on (a) a free
Census Data API key being configured and (b) an H3 res 7–9 rollup with MOE propagation.**
Do **not** reject: ACS is the only validation-wave source that is non-synthetic, reaches
block groups, and is fresh enough (~1 yr) to replace or calibrate the repo's hardcoded
submarket baselines (`base_lims`, `capex`, `permit_vel`, `shift_ratio`, `sla`) with a
data-derived demand/structure prior. Do **not** wire it as a `FeedType`/LIMS term — it
is a slow level, not an event, so it belongs in the baseline/context path, not the
scoring path. The accompanying leaf module (`acs_baseline.py`) is the mechanical
rollup + MOE-propagation core; the remaining work (API-key config, block-group→H3
resolution wiring, `SubmarketMeta` baseline substitution) is a small adopting stream and
touches config/spine, so it is explicitly **out of scope for this leaf**.

**Unblocks a future REGISTER/adopt:**
1. Configure a free Census Data API key (secret) and a batched `acs5` pull per metro.
2. Reuse the LODES crosswalk (or TIGER BG) to attach BG centroids → H3 res 7–9.
3. Roll up by `ACS_BASELINE_FEATURES` agg rules with MOE propagation + spatial fallback.
4. Substitute/calibrate the hardcoded `SubmarketMeta` baselines with the resulting
   division/submarket priors, keeping them LIMS-exempt context.
