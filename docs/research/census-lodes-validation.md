# Census LEHD LODES — validation as a slow-moving contextual spatial signal

**Date of research: 2026-08-25.** The product pages and the LODES raw files were
probed live. I read the LODES Format Version 8.4 technical document and the
OnTheMap Data Overview (both PDFs, text-extracted locally) and I *downloaded and
aggregated the actual data files* for two pilot metros rather than only reading the
documentation. Where a claim could not be confirmed remotely it is marked
**unverified**. This is a *validation* document — no feed was registered, no `.py`
was touched.

## Method, and its limits

I validated on three layers, in order:

1. **Product facts.** Fetched the LODES code-samples overview, then
   downloaded `LODESTechDoc.pdf` (Format Version 8.4, Rev. 20251203) and
   `OnTheMapDataOverview.pdf` (OTM20251202) and extracted their text with
   `pdftotext`. I used the program's own words for job definition, reference
   period, coverage gaps, disclosure approval, geography base, and revision
   behavior — not memory.
2. **Live file structure.** Fetched the `LODES8/` directory listing and the
   per-state `la/` and `va/` trees, confirming `version.txt`, `<st>_xwalk.csv.gz`,
   `lodes_<st>.sha256sum`, and `od/`, `rac/`, `wac/` subdirectories exist. I
   downloaded `la_xwalk.csv.gz`, `va_xwalk.csv.gz`, the 2023 `WAC`/`RAC` S000
   JT00 files for both states, and the 2023 `OD` main files for both states.
3. **Measured metro aggregation.** Using only the published files, I filtered
   each state crosswalk to the two pilot metros (county FIPS, then the repo's own
   metro bbox), joined the published WAC/RAC counts to those blocks, and rolled
   the block internal-point coordinates into H3 7/8/9 with the `h3` library.

**Limits.** I did *not* probe every state-year path — coverage beyond LA and VA
is asserted only from the two documents' own coverage tables, not by listing all
51 state directories. I did not inspect the OD matrix to build a numeric commute
table (I only counted pair volumes); the OD `S000` job attribution is used as a
count, not as origin–destination content. "Incremental value against current
signals" is assessed by *concept* against the repo's feed families, not by running
an ablation (this is a leaf research stream; no pipeline was run). The exact
written reuse/licence terms page was **not fetched** — see Source assessment. No
point-estimate is presented as an interpreted market fact; every number below is a
measured file/aggregate characteristic or is quoted from the source documents.

## Headline verdict

**DEFER.** LODES is a genuine, authoritative, free, census-block-detail measure of
workplace concentration, residence-to-work flows, and worker/job composition — a
dimension **no existing Urban Signal feed measures** — and its granularity is
*superior* to the target units (census block is finer than H3 res 7–9), so unlike
the BFS case there is no granularity mismatch. I measured the two-metro pilot as
small and clean: NOLA ≈ 20,484 blocks → 4,663 H3 res-9 cells; Norfolk ≈ 4,271
blocks → 1,216 res-9 cells, with WAC/RAC joins a few thousand rows and per-metro
job counts in the low-hundreds-of-thousands. But the data does **not fit the feed
model in this repo** (`FeedType`/`DatasetSpec`/`PaginatingClient` are built around
geolocated, watermark-paginated municipal event streams; LODES is a stateless
state-wide gzip with a *createdate* and no per-row coordinates, so a feed
registration is structurally impossible without a new signal family and a new
bulk-file synthesis pipeline). And its cadence is ~annual with a ~28-month lag
(2023 data released Dec 2025, Q2 reference) — it can only ever be a **trailing
context/anchor**, never a leading signal or a LIMS term, and its block counts are
partly synthetic/disclosure-protected (CBDRB-FY21-249). Unless the project decides
it wants a structural labor/employment context layer wired in as its own signal
family (not an event feed), the integration cost outweighs a context-only role
that no existing signal depends on. Shelf it; the unblock path is specific and
small (below).

---

## Source assessment

- **Access / terms.** Census-produced federal data — U.S. government work, public
  domain (17 U.S.C. § 105). **No API key, no registration, no authentication** —
  verified directly: every file above was downloaded anonymously by plain
  `curl` to `https://lehd.ces.census.gov/data/lodes/LODES8/<st>/...`. Distribution
  is file-based: per-state gzipped CSVs plus a geography crosswalk. (The specific
  LEHD/OnTheMap written terms-of-use page was **not fetched — unverified**; the
  public-domain statutory basis and the unauthenticated access are the verified
  parts.)
- **File families.** Three per state: **OD** (origin–destination; jobs total on
  both a home block `h_geocode` and a work block `w_geocode`), **RAC** (residence
  area characteristics, jobs by home block), **WAC** (workplace area
  characteristics, jobs by work block). Plus `<st>_xwalk.csv.gz` (geography
  crosswalk), `version.txt`, and `lodes_<st>.sha256sum`.
- **Geographic granularity.** **Census block** (2020 census blocks; LODES V8 based
  on 2024 TIGER/Line shapefiles; V7/V6 used 2010 blocks). The crosswalk keys on
  `tabblk2020` and also emits the block **internal-point latitude/longitude**
  (`blklatdd` / `blklondd`) — a ready-made coordinate per block, so no separate
  TIGER geometry file is needed to geolocate a block. The crosswalk additionally
  exposes FIPS `cty`, CBSA/MSA (`cbsa`), place (`stplc`), tract/block-group, and
  other hierarchy codes for metro joins.
- **Cadence / latency / reference period.** LODES V8 covers **2002–2023** (Q2
  April–June is the reference period each year; a job is counted if held with
  positive earnings in the reference quarter *and* the prior quarter —
  "beginning-of-quarter" stock, not a flow). Release is file-drop, roughly annual:
  the `LODES8/` tree was last modified **2025-12-12** and the format doc is dated
  **2025-12-03**, i.e. the newest job year (2023) shipped ~28 months after the
  Q2-2023 reference. **The formal release calendar is not stated in either
  document — unverified** beyond "annual-ish"; the exact schedule is not published.
- **Coverage gaps (Table 1 / tech doc §Coverage).** No **OD/WAC** data for: Alaska
  2017–2023, Arizona 2002–2003, Arkansas 2002, DC 2002–2009, Massachusetts
  2002–2010, Michigan 2022–2023, Mississippi 2002–2003, New Hampshire 2002;
  Puerto Rico and U.S. Virgin Islands in **all** years. Those states still publish
  **RAC** (residents employed out-of-state). Both LA and VA are fully covered
  2002–2023 (verified live: OD/RAC/WAC for 2023 present).
- **Volume (measured, 2023, JT00 S000).** Whole-state `OD` main: **LA 1,631,945
  rows (~9.8 MB gz), VA 3,062,303 rows (~18.3 MB gz)**. `WAC`: LA 35,876 blocks /
  1,895,919 jobs (865 KB gz), VA 55,775 / 3,894,892 (1.3 MB). `RAC`: LA 88,415 /
  1,881,792 (2.2 MB), VA 114,163 / 3,924,600 (3.1 MB). Crosswalks: LA 2.5 MB, VA
  2.9 MB. The whole national 2002–2023 OD/WAC/RAC archive is tens of GB, but the
  metro subset needed for a signal is tiny (see Two-metro feasibility).
- **Revisions / reproducibility.** Strong. Each state ships `version.txt`
  (state + data vintage `YYYYMMDD` + format version) and `lodes_<st>.sha256sum`
  (SHA-256 per file). The program warns: **"The data vintage is not the same as
  the createdate"** and **"New or corrected data may cause newer vintages of data
  to be released. Only files that have new or changed data will be included in
  future vintages."** So a pipeline can pin a format version + vintage, verify
  checksums, and reproduce exactly — but should treat published files as
  vintage-specific (a later vintage may replace older files and backfill corrected
  counts). `createdate` is a per-file internal processing stamp, not a watermark.
- **Disclosure / syntheticity.** The Data Overview explicitly describes LODES V8
  as **"a partially synthetic dataset"**; the tech doc states the Census Bureau
  reviewed it and **approved the disclosure-avoidance practices, CBDRB-FY21-249**.
  Block-level counts are therefore **not exact** and carry disclosure noise.
- **Variables.** Segments S000 (total), SA (age ×3), SE (earnings ×3), SI
  (industry group ×3). Area characteristics add: NAICS sector (20), race (×6),
  ethnicity (×2), education (×4, 30+ only), sex (×2) — all 2009+; firm age (×5)
  and firm size (×5) — 2011+, WAC only, JT02 only. Job types: JT00 All, JT01
  Primary, JT02 All Private, JT03 Private Primary, JT04 All Federal, JT05 Federal
  Primary (Federal jobs from 2010; add OPM). Public/non-primary are derived by
  subtraction. REE/SA etc. are **not** on the OD matrix (OD carries only
  S000/SA/SE/SI segments).

---

## Urban Signal fit

Urban Signal units are strictly nested: **metro bbox → division bbox(es) →
submarket → H3 cells 7–9** (H3 res 7 ≈ 5.16 km², res 8 ≈ 0.74 km², res 9 ≈ 0.105
km² per `spatial/h3_indexer.py`). Each event feed is metscope-bbox-filtered at
ingest, then each row → `h3_res7/8/9` via `H3SpatialIndexer.get_multi_res_hierarchy`.

**LODES is the inverse of the BFS granularity problem.** Census blocks are far
*finer* than an H3 res-9 cell, so it is never "too coarse" — the entire question
is how to roll block aggregates *up* to H3 7–9 and to the division/submarket
units, which is a clean aggregation, not an arbitrary downsampling.

The required crosswalk work, and it is small and well-defined:

1. **Block → coordinate.** Use the crosswalk's `blklatdd`/`blklondd` (block
   internal point). No TIGER block geometry is needed — the crosswalk *is* the
   geocoder. (Caveat: the internal point is "guaranteed inside the block" but is
   **not a centroid**, so point-in-H3 is approximate when blocks straddle a cell
   boundary; for metro/division scale this is immaterial, and rollup to res 7–9
   absorbs it.)
2. **Coordinate → metro.** Filter blocks by the repo's metro bbox, exactly as
   event feeds are bbox-filtered. Measured: NOLA bbox holds **20,484** of the
   21,447 county-FIPS blocks (the 963 dropped are eastern St. Bernard beyond the
   repo's `min_lng -89.62` — the bbox deliberately excludes the outer coast);
   Norfolk bbox holds **4,271** of 4,371 city blocks.
3. **Coordinate → division/submarket.** Reuse the existing coordinate resolution
   path (`get_division_for_coordinate` / `find_nearest_submarket`) on the block
   internal point — the same path event rows use, so no new joiner is needed.
4. **Rollup → H3.** For each block, `latlng_to_cell(blklatdd, blklondd, r)` and
   sum the WAC/RAC/OD count variables per cell. Unique-cell counts (measured):
   NOLA **res 9 = 4,663 / res 8 = 1,189 / res 7 = 280**; Norfolk **res 9 = 1,216**.
   This supports the repo's density-fallback pattern
   (`dynamic_spatial_fallback`): sparse-suburban cells fall back to a coarser
   parent, which is exactly the smoothing needed to de-noise disclosure.

**Does it add coverage the current feed-derived signals do not provide?** Decisively
yes, in kind. The feed families — permits, 311, SLA licenses, deeds, crime,
evictions, STR, street-cut — are all **event streams**: geolocated transactions at
a point (a permit issued, a complaint filed, a sale recorded, a crime reported,
an eviction executed, a listing short-rented). **None** of them measures the
**demand side**:
- **workplace concentration** (where jobs are),
- **residence-to-work flows** (who lives where relative to where they work),
- **worker/job composition** (age, earnings, industry, firm age/size).

That is a genuinely independent dimension of the metro, and it is the closest thing
in the pipeline to a structural anchor for the hardcoded submarket baselines
(`base_lims`, `capex`, `permit_vel`, `shift_ratio`, `sla` in `SubmarketMeta`) and
for office/commercial-adjacent fundamentals at the division scale. No existing
feed, and no combination of them, can reconstruct a job-density or earnings-
composition surface.

**The catch is the integration model, not the data.** A `FeedType` is required for
a `CityRegistration` to expose a signal, and each `DatasetSpec` assumes a
`PaginatingClient` (Socrata/ArcGIS/CKAN `$offset` paging), a `watermark_col`, and
`id_keys` per geolocated event row (`get_dataset` / `resolve_endpoint`). LODES
violates every one of those assumptions: it is a *stateless per-state gzip*, keyed
by a 15-char block code with **no lat/lng on the row** (crosswalk join needed), no
event semantics, no watermark (only `createdate`/vintage), bulk-file delivery, and
a ~annual vintage. Registering it "as a feed" is not a mapping-table exercise like
NOLA/Austin — it is a **new signal family** (`FeedType.WORKFORCE`/`JOB_DENSITY`),
a **new producer archetype** (download → crosswalk join → block→H3 rollup), and a
new table shape (H3-cell aggregates, not event rows). That is a spine/registry
change, beyond a leaf stream.

---

## Two-metro feasibility

Chosen pairs for the pilot, both registered metros, both fully-covered states:

| | **New Orleans** (LA) | **Norfolk** (VA) |
|---|---|---|
| Repo unit | `CityId.NEW_ORLEANS` (Orleans+Jefferson+St. Bernard) | `CityId.NORFOLK` (independent city) |
| Blocks in metro bbox | **20,484** | **4,271** |
| Unique H3 cells (res 7/8/9) | **280 / 1,189 / 4,663** | — / — / **1,216** |
| WAC workplace blocks / jobs | 7,211 / **404,544** | 1,488 / **130,869** |
| RAC residence blocks / workers | 13,507 / **351,623** | 3,028 / **90,578** |
| OD rows (work in metro / live in metro / both) | 368,511 / 322,254 / 261,696 (392,084 jobs) | (VA comparable) |

**Expected ingest path.** One crosswalk download per state (LA 2.5 MB / VA 2.9 MB
gz, one-time, pinned to 2020-geo vintage); per year, download the metro's WAC +
RAC S000 JT00 (a few MB) and the full-state OD main JT00 (LA 9.8 MB / VA 18.3 MB)
then filter to metro blocks. Join WAC/RAC/OD to the crosswalk on `w_geocode` /
`h_geocode` → `tabblk2020`, attach the block internal point, bbox-filter, roll up
to H3 7–9, and fold into the division/submarket resolution.

**Measured feasibility: easy.** The metro subset is small — tens of thousands of
blocks, a few hundred thousand jobs, a few thousand H3 cells per metro. Even
backfilling all 22 years (2002–2023), the NOLA-metro subset of OD is ~260–370k
rows/year (~7–8M rows total), which is far below the existing NYC/Austin event-row
backfills cited in `new-orleans-austin-verification.md`. Memory and wall-clock are
non-issues; the only real cost is the bulk-file + crosswalk + rollup synthesis
code, which is new but small, plus the per-state file naming (`<st>_od_main_JT00`,
`<st>_wac_S000_JT00`, `<st>_xwalk`) which is stable across years and documented.

**One caveat that makes Norfolk a good stress-test, not a blocker.** Both metros
are pre-defined by *bbox*, and Norfolk's bbox deliberately excludes Chesapeake /
Virginia Beach / Portsmouth / Hampton, so a naive whole-county WAC join would
over-count. The measured bbox filter (4,271 of 4,371 blocks) shows the correct
approach is **bbox-filtering the crosswalk blocks**, exactly as event feeds are
bbox-filtered — not a FIPS-county join. Both pilots resolve the same way; the
crosswalk's `cbsa`/`cty` fields are available as a secondary sanity layer but
should not be the primary metro gate.

---

## Independent coverage check (vs. the existing feed families)

| Dimension | Existing feed-derived signals | Census LEHD LODES |
|---|---|---|
| Unit | geolocated **event**, H3 cell | census **block** aggregate → H3 cell |
| Latency | near real-time (daily/weekly) | ~annual, **~28-month lag** (Q2 reference) |
| Concept | *events* (permit issued, complaint, sale, crime, eviction) | *stock/composition* (jobs, flows) |
| Coverage | only metros with that feed | every US block in covered state-years |
| Noise | none (record-level) | **partly synthetic** (CBDRB-FY21-249) |
| Dimensions | none (event + type/date) | age, earnings, industry, race, education, sex, firm age/size, OD flows |

**Does it add independent coverage?** Yes, but only in *kind* and only as context:
it measures a demand-side structural surface (workplace concentration, commute
flows, earnings/industry composition) that no event feed produces. It does **not**
add a timelier or finer *event-count* measure — it is strictly slower and aggregate
by design. For the repo's scoring goal (event velocity + value at H3, then ablation
into LIMS), LODES can contribute an **anchor/prior** (e.g. expected job-density or
earnings mix by submarket) and a **context narrative** ("this division is a job
concentration node"), but it cannot drive short-term change detection, which is the
whole point of the event feeds. Under the repo's rule (a signal is retained only if
it adds independent coverage and clears its family gate), LODES clears the
"independent coverage" test but not the "usable at target resolution/timeliness"
test for *scoring*; it clears both only for a **context** role.

---

## Risks and dependencies (mapped to the issue's risks)

1. **"Multi-year latency unsuitable for short-term change detection."** **Confirmed,
   and binding for any LIMS role.** 2023 data released ~Dec 2025 (reference
   Q2-2023) → ~28-month lag, ~annual cadence. This caps it to trailing context; it
   cannot be a leading signal. (Also note the Q2 "beginning-of-quarter" definition
   means each year is a *stock* snapshot, not a flow, so it is a level, not a
   velocity.)
2. **"Block-level figures partly synthetic/disclosure-protected (not exact
   counts)."** **Confirmed.** The Data Overview calls V8 "partially synthetic";
   DRB approval **CBDRB-FY21-249**. Block counts are not exact. Mitigations that
   are already repo-native: roll up to H3 res 7–9 (hundreds-to-thousands of blocks
   per cell) and use the density fallback (`dynamic_spatial_fallback`) for sparse
   cells — aggregation is exactly what reduces relative disclosure noise. But the
   absolute values remain non-exact, so they must be treated as an *index/ratio*
   signal, never a precise count.
3. **"Requires census-block geometry/crosswalk processing and city-level
   calibration."** **Partially mitigated by the data itself.** The crosswalk emits
   `blklatdd`/`blklondd` per block, so **no TIGER geometry file is needed** —
   this risk is lower than the issue assumed. The required processing is: crosswalk
   → bbox filter (needed; a FIPS-county join over-counts city-scoped metros like
   Norfolk) → block-point → H3 → plus division/submarket resolution via the
   existing coordinate path. "City-level calibration" remains a real task — the
   disclosure noise and the Q2-stock semantics both need an explicit
   interpretation rule (e.g. "years are comparable as levels, not per-cell deltas"),
   and the noise floor must be calibrated per division, not assumed.
4. **Integration-model dependency.** The decisive one. No `FeedType` exists for a
   non-event, block-aggregate layer. `FeedType` is `PERMITS`, `COMPLAINTS_311`,
   `SLA`, `DEEDS`, plus signal families `CRIME`, `STREET_CUT`, `EVICTIONS`, `STR`.
   A LODES registration needs a **new** signal family and a **new producer
   archetype** (bulk download + crosswalk join + rollup), which is exactly the kind
   of spine change that must gate on `pytest -m interlock` per
   `docs/agents/parallel-streams.md` and is out of scope for a leaf stream. Also
   new: the stored shape is H3-cell aggregate rows, not the `h3_res7/8/9`-on-event
   rows the pipeline and Postgres sync assume (`pipeline.py`,
   `postgis_sync.py`).
5. **Vintage/revision dependency.** "Newer vintages … only files that have new or
   changed data" means a pipeline must pin a `LODES8` format version + a data
   vintage and verify the per-state SHA-256; it must not silently re-download
   newer corrected counts into a tight year-over-year feature without versioning.

---

## Recommendation

**DEFER** — do not register now, but this is the closest call among the validation
wave and the data side is fully proven. **Do not register** because a feed
registration is structurally impossible in the current model (LODES is not an
event stream, has no watermark, no per-row coordinates, and needs a new `FeedType`
+ producer archetype + aggregate storage = a spine/interlock change), and because
its ~28-month lag and synthetic block counts mean it can only ever be a trailing
**context/anchor**, not a signal any current scoring path depends on. At the same
time, **do not reject** it: unlike BFS there is *no granularity mismatch* (block is
finer than H3 7–9), the crosswalk already provides block coordinates (the biggest
assumed risk is mostly moot), ingestion volume is small (measured), and it measures
a dimension (workplace concentration, commute flows, employment composition) that
no existing feed provides.

**What unblocks a future REGISTER** (any one, or in combination):

1. A positive **scope decision** that Urban Signal wants a structural
   labor/employment **context layer** at all — a new `WORKFORCE`/`JOB_DENSITY`
   signal family, its own `DatasetSpec`-adjacent spec, its own H3-aggregate table,
   and a bulk-file producer — treated as context/LIMS-exempt (precedent: street-cut
   "disruption context only — never a LIMS term").
2. A concrete consumer that needs it — e.g. an **explanatory "demand anchor"** for
   a submarket (job density × earnings mix as a prior under the hardcoded
   `base_lims`/`capex`/`sla` baselines), or an office/commercial-exposure view that
   no event feed supplies.
3. If both arrive, **register New Orleans and Norfolk first** (both states fully
   covered, measured small, crosswalk clean), as a **year-over-year level context
   index at division/submarket and H3 res 7–9**, pinned to the `LODES8` 2020-geo
   vintage with SHA-256 verification, and explicitly calibrated to treat each year
   as a noisy but order-preserving level rather than an exact per-cell delta.

Until then, the existing event feeds remain the correct timely signal, and LODES
should not be wired in as a scoring input.
