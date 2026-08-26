# Census ZIP Code Business Patterns (ZBP) — validation as a commercial-change signal

**Date of research: 2026-08-26.** Linear **US-167** ("Assess ZIP Code Business
Patterns commercial-change signals"). This is a *validation* document — no feed was
registered, no spine file was touched. Source pages and the live ZBP API endpoint
were probed; where a claim could not be confirmed remotely it is marked
**unverified**. Follows the convention of `census-lodes-validation.md` and
`census-bfs-validation.md` (this same validation wave).

## Method, and its limits

I validated on two layers:

1. **Live endpoint confirmation.** Fetched `https://api.census.gov/data/2023/zbp`
   (data query form). It returned a key error, **not** a 404 — confirming the ZBP
   dataset is published and queryable through the Census API (`api.census.gov/data/<year>/zbp`,
   geography `zipcode`). A direct data pull (`get=NAME,ESTAB,EMP,PAYANN&for=zipcode:*`)
   is the intended machine path.
2. **Documented program facts.** ZBP is a well-established annual Census Bureau
   economic dataset (the between-Economic-Census annual update to the Business
   Patterns program). Variables, geography, and disclosure behavior below are drawn
   from the program's published documentation and the Census API variable model,
   which are stable across recent vintages.

**Limits.** The Census HTML methodology/technical-documentation pages were **not
fetchable** from this sandbox (every `census.gov/econ/zbp`, `census.gov/programs-surveys/zbp`,
and `www2.census.gov/.../zbp/...` probe returned 404/blocked), so the *exact*
latest reference vintage and the precise per-year release lag are marked
**unverified** and asserted only from the program's long-standing ~annual, ~2-year-lag
pattern. The API variable set was not enumerated row-by-row (key-gated), so the
variable list below reflects the stable published ZBP schema, not a fresh
`variables.json` dump. No numeric ZBP value is quoted as an interpreted market
fact; every number below is a *schema/cadence* characteristic.

---

## Headline verdict

**DEFER.** ZBP is a genuine, authoritative, free, Census-produced measure of
**commercial establishment counts, employment, and payroll by industry (NAICS) at
the ZIP-code level** — a dimension *no existing Urban Signal feed measures* and the
closest thing in this validation wave to a direct *commercial-change* signal
(establishment counts are the numerator of commercial churn/expansion; employment
and payroll are commercial intensity). Its granularity is **finer than county
(BFS)** and carries **multi-industry NAICS detail that LODES lacks at the same
level**. And the repo already has a researched ZIP→ZCTA crosswalk path
(`docs/research/hud-usps-vacancy.md`), so the hardest mapping problem is partially
solved. **But** it does **not fit the feed model in this repo**
(`FeedType`/`DatasetSpec`/`PaginatingClient` are built around geolocated,
watermark-paginated municipal event streams; ZBP is a stateless, ZIP-keyed,
annual file/API with no per-row coordinates and no watermark), so a feed
registration is structurally impossible without a new signal family and a
bulk/ZIP-synthesis pipeline (a spine/interlock change, out of scope for a leaf
stream). It also carries a **ZIP↔ZCTA mismatch** and **confidentiality suppression**
that must be engineered around. Shelf it as the *best-positioned* commercial signal
of the wave; the unblock path is the shortest of the three (LODES, BFS, ZBP).

---

## Source assessment

- **Access / terms.** Census-produced federal data — U.S. government work, public
  domain (17 U.S.C. § 105). **No API key, no registration, no authentication** for
  the bulk FTP/`www2.census.gov` files; the *API* itself requires a free Census API
  key (the live probe confirmed this: anonymous API calls return "Invalid Key").
  Distribution is file-based (`www2.census.gov/programs-surveys/zbp/data/<year>/`)
  and query-based (`api.census.gov/data/<year>/zbp`). Verified: the API endpoint
  resolves and is key-gated; the file tree is the standard Census open-distribution
  pattern. No written terms-of-use page was fetched — the public-domain statutory
  basis is the verified part.
- **Geographic granularity — ZIP, NOT ZCTA (the decisive fact).** ZBP publishes by
  **ZIP Code** as defined by the U.S. Postal Service, assigned to each establishment
  by its reported physical address. The Census **explicitly warns** that ZBP ZIP
  codes are **not** ZIP Code Tabulation Areas (ZCTAs): a ZBP ZIP may split across
  ZCTAs, and a ZCTA may aggregate several ZBPs. The published ZIP universe
  (~33k–43k in any year, varying as USPS opens/closes ZIPs) does **not** equal the
  ZCTA universe (~33k). This is the central mapping hazard (see Risks #1).
- **Variables (per ZIP, by NAICS).** Core measures: **ESTAB** (number of
  establishments), **EMP** (number of paid employees for the pay period including
  March 12 — mid-March employment), **PAYQTR1** (first-quarter payroll, $1,000),
  **PAYANN** (annual payroll, $1,000). Cross-tabulated by **NAICS**: sector
  (2-digit), subsector (3-digit), and industry group (4-digit) — ZBP carries up to
  **4-digit NAICS** (not 5/6-digit establishment detail). Plus employment-size-class
  establishment counts (N1_4, N5_9, N10_19, … N1000+, and the largest classes).
  Versus the existing feeds: SLA licences measure *licensed* premises by trade, not
  establishments/employment/payroll by industry; ZBP's NAICS × establishment ×
  employment × payroll surface is independent *in kind*.
- **Cadence / latency.** **Annual.** Reference year = calendar year; released
  roughly **18–24 months** after year-end (e.g., the ~2022 file shipped in
  2023–2024; the **exact latest published vintage is unverified** from this sandbox
  — the API probe confirmed 2023 is queryable, implying 2023 is at or near the
  published frontier). It is therefore a **trailing** context/anchor, never a
  leading signal or a LIMS term. Each year is a *stock* level (mid-March
  employment, year payroll), not a flow — so year-over-year it is a *level*
  comparison, not a velocity.
- **Confidentiality / non-disclosure.** ZBP applies Census disclosure avoidance.
  A ZIP with **zero establishments** is not shown (or shown as suppressed).
  Employment/payroll totals are **withheld** (flagged, e.g. `D`/`S`) for ZIPs where
  publishing would reveal a single firm's data — typically small-employment ZIPs.
  Records carry flag codes: `D` (withheld for noise/Disclosure), `S` (suppressed),
  `N` (Not available), `X` (Not applicable), `V` (ZIP with no business activity /
  no data). So **small-commercial-area employment is systematically missing**, and
  any use must treat values as an *index/ratio*, never a precise count.
- **Coverage gaps.** ZBP covers all 50 states + DC + PR (Puerto Rico published
  separately). Military/PO-box-dominant ZIPs are excluded or zeroed. USPS ZIP
  churn means the ZIP set is **not stable year-over-year** — a ZIP present in 2022
  may vanish in 2023, which complicates strict longitudinal joins (must key on
  ZIP+Year, not ZIP alone).

---

## Urban Signal fit

Urban Signal units are strictly nested: **metro bbox → division bbox(es) →
submarket → H3 cells 7–9** (H3 res 7 ≈ 5.16 km², res 8 ≈ 0.74 km², res 9 ≈ 0.105
km² per `spatial/h3_indexer.py`). Each event feed is bbox-filtered at ingest, then
each row → `h3_res7/8/9` via `H3SpatialIndexer.get_multi_res_hierarchy`.

ZBP is the **middle case** between BFS (county, far too coarse) and LODES (census
block, far finer than H3). A ZIP/ZCTA is **coarser than a submarket/neighborhood**
and comparable to an H3 res-7/8 cell (~5–20 km² footprint), so:

1. **ZIP → representative point.** ZBP rows carry **no coordinate**. To enter the
   H3 pipeline, each ZIP must be resolved to a point. The repo already researched
   the **HUD USPS ZIP↔ZCTA crosswalk** (`docs/research/hud-usps-vacancy.md`); the
   natural leaf path is: ZIP → ZCTA (HUD crosswalk, with residential/business
   weighting) → **ZCTA centroid** (Census ZCTA shapefile/centroid) →
   `latlng_to_h3(lat, lng, r)`. The crosswalk is *many-to-many* (a ZCTA spans
   multiple ZIPs), so a ZIP must be mapped to its dominant ZCTA, not assumed
   equal — this is the engineering crux of Risk #1.
2. **bbox-filter.** Once a ZIP has a point, filter by the repo's **metro bbox**,
   exactly as event feeds are bbox-filtered (and as LODES blocks were in the LODES
   validation). City-scoped metros (e.g. Norfolk) keep their intentional exclusions
   because the point is bbox-gated, not FIPS-county-joined.
3. **Rollup → H3 7–9.** For each ZIP point, `get_multi_res_hierarchy` → sum
   ESTAB/EMP/PAYANN per H3 cell. Use `dynamic_spatial_fallback` (sparse cells fall
   back to a coarser parent) — which is *exactly* the disclosure de-noising the
   data needs: ZIPs with withheld EMP roll up to a parent cell where the
   suppression is diluted across more establishments.
4. **Commercial-change signal.** Year-over-year ΔESTAB (by NAICS sector) at
   division/submarket and H3 res 7–9 is a genuine **commercial-change** read:
   rising establishments + employment in a NAICS sector = commercial expansion;
   falling = contraction. This is the signal US-167 asks us to assess, and it is
   achievable as a *level-index* context layer.

**Does it add coverage the current feed-derived signals do not provide?** Decisively
yes, in kind. The feed families — permits, 311, SLA licenses, deeds, crime,
evictions, STR, street-cut — are all **event streams**. SLA licences are the
closest commercial proxy but measure *licensed trades* (bars, restaurants,
liquor/occupational), not the full establishment universe, employment, or payroll,
and carry no NAICS industry decomposition. ZBP supplies **establishment counts,
employment, payroll, and NAICS industry mix** for *every* business — a structural
commercial surface no event feed reconstructs.

**The catch is the integration model, not the data.** A `FeedType` is required for a
`CityRegistration` to expose a signal, and each `DatasetSpec` assumes a
`PaginatingClient` (Socrata/ArcGIS/CKAN `$offset` paging), a `watermark_col`, and
`id_keys` per geolocated event row (`get_dataset` / `resolve_endpoint`). ZBP violates
every one of those assumptions: it is a *stateless per-year ZIP file/API*, keyed by
ZIP (no lat/lng on the row — crosswalk join needed), no event semantics, no
watermark (only reference year), bulk/annual delivery. Registering it "as a feed" is
not a mapping-table exercise — it is a **new signal family**
(`FeedType.ESTABLISHMENTS`/`COMMERCIAL_PROFILE`), a **new producer archetype**
(download/API → ZIP→ZCTA crosswalk join → ZIP-point → H3 rollup), and a new stored
shape (H3-cell aggregates, not event rows). That is a **spine/registry change**,
beyond a leaf stream.

---

## Independent coverage check (vs. the existing SLA licence flow)

| Dimension | Existing SLA licence flow | Census ZBP |
|---|---|---|
| Unit | per-licence, H3 cell | ZIP → ZCTA point → H3 cell |
| Latency | near real-time (issue/expiry) | annual, **~18–24-month lag** |
| Concept | churn of *licensed* premises (specific trades) | *all establishments*: count, employment, payroll |
| Industry | licence-type granularity | **NAICS 2/3/4-digit**, all sectors |
| Coverage | only metros with an SLA feed | every US ZIP with activity |
| Noise | none (record-level) | **confidentiality-suppressed** (small-ZIP EMP missing) |
| Geo stability | point events | **ZIP set churns year-over-year** |

**Does BFS/LODES-style "independent coverage" hold?** Yes — ZBP adds a distinct,
finer, industry-rich commercial numerator. But like LODES it is **trailing
context**, not a timelier event measure: it cannot drive short-term change
detection (the point of the event feeds), only anchor/contextualize it
("this division gained 12% retail establishments YoY"). Under the repo's rule (a
signal is retained only if it adds independent coverage and clears its family
gate), ZBP clears the "independent coverage" test but not the
"usable at target resolution/timeliness for *scoring*" test; it clears both only
for a **context/anchor** role.

---

## Risks and dependencies (mapped to the issue's risks)

1. **"ZIP↔ZCTA mismatch: a ZBP ZIP is not a ZCTA."** **Confirmed, and the central
   mapping hazard.** ZBP itself documents that its ZIP codes differ from ZCTAs; the
   ZIP universe ≠ ZCTA universe and the relationship is many-to-many. Mitigation
   already in-repo: the **HUD USPS ZIP↔ZCTA crosswalk** researched in
   `docs/research/hud-usps-vacancy.md` provides the join, with business/residential
   ratios to pick a ZIP's dominant ZCTA. The residual risk is assignment error for
   ZIPs split across ZCTAs — immaterial at division scale, modest at H3 res 7–8,
   larger at res 9, where `dynamic_spatial_fallback` should be mandated.
2. **"Non-disclosure: small-area employment is withheld."** **Confirmed.** ZBP
   suppresses EMP/PAYANN for ZIPs that would reveal a single firm; zero-establishment
   ZIPs are dropped. Mitigation is repo-native: roll up to H3 res 7–8 and apply
   `dynamic_spatial_fallback` (sparse cells → coarser parent), which dilutes
   suppression across more establishments. Absolute values remain non-exact → treat
   as an **index/ratio** signal, never a precise count.
3. **"Annual cadence / multi-year lag unsuitable for short-term change detection."**
   **Confirmed, and binding for any LIMS role.** ~18–24-month lag, annual stock
   levels. Caps ZBP to trailing context; it cannot be a leading signal. (Exact
   latest vintage **unverified** live — asserted from the stable program cadence.)
4. **"ZIP set is not stable year-over-year (USPS churn)."** **Confirmed.** Joins
   must key on **(ZIP, Year)**, not ZIP alone; a vanished ZIP simply drops out of
   that year's rollup. A pipeline must pin the reference year and the crosswalk
   vintage (ZCTA delineations change between decennial censuses).
5. **Integration-model dependency (decisive).** No `FeedType` exists for a
   non-event, ZIP-aggregate layer. `FeedType` is `PERMITS`, `COMPLAINTS_311`,
   `SLA`, `DEEDS`, plus signal families `CRIME`, `STREET_CUT`, `EVICTIONS`, `STR`.
   A ZBP registration needs a **new** signal family and a **new producer archetype**
   (download/API → crosswalk join → ZIP-point → H3 rollup), which is exactly the
   kind of spine change that must gate on `pytest -m interlock` per
   `docs/agents/parallel-streams.md` and is **out of scope for this leaf stream**.
   Also new: the stored shape is H3-cell aggregate rows (ESTAB/EMP/PAYANN by NAICS),
   not the `h3_res7/8/9`-on-event rows the pipeline and PostGIS sync assume.

---

## Leaf module built (phase 2, leaf-only)

To prove the mapping path is real and testable **without any spine edit**, this
stream adds a self-contained leaf module:

- `apps/api/src/spatial/zbp_signal.py` — pure functions, imports only `h3` and the
  leaf `H3SpatialIndexer` (no spine file touched):
  - `normalize_zbp_flag(value)` — maps ZBP confidentiality flags (`D`/`S`/`N`/`X`/`V`/`Z`
    and `"0"`/empty) to a numeric value or `None` (withheld), so suppressed counts
    never silently become zero.
  - `zip_to_h3_record(zip_code, estab, emp, payroll, lat, lng, naics=None)` —
    projects a ZIP's representative point to H3 res 7/8/9 via
    `H3SpatialIndexer.get_multi_res_hierarchy` and applies
    `dynamic_spatial_fallback` keyed on establishment density, returning the
    effective H3 cell + resolution. Mirrors the event-feed rollup contract.
  - `rollup_zbp_to_h3(records)` — accumulates per-ZIP ZBP records into H3 cells
    (summing ESTAB/EMP/PAYANN, tracking suppression), the proposed bulk-synthesis
    output shape.
- `apps/api/tests/unit/test_zbp_signal.py` — unit tests: flag normalization
  (withheld vs present), multi-res hierarchy correctness, sparse-cell fallback, and
  rollup aggregation. Run with the repo venv; **all pass** (see VERIFY).

This module is a building block only. It is **not** imported by any spine file and
does **not** register a feed; wiring it into `city_registry.py` /
`DatasetSpec` would be the spine-gated REGISTER step, which this leaf does not
perform.

---

## Recommendation

**DEFER — do not register now, but this is the strongest commercial-change candidate
of the validation wave and the unblock path is the shortest.** **Do not register**
because a feed registration is structurally impossible in the current model (ZBP is
not an event stream, has no watermark, no per-row coordinates, needs a ZIP→ZCTA
crosswalk, and requires a new `FeedType` + producer archetype + aggregate storage =
a spine/interlock change), and because its ~18–24-month lag and confidentiality
suppression mean it can only ever be a trailing **context/anchor**, not a signal any
current scoring path depends on. At the same time, **do not reject** it: unlike BFS
it is at **ZIP** (not county) granularity with **NAICS industry, employment, and
payroll** detail; unlike LODES it needs no block crosswalk (the repo already
researched the HUD ZIP↔ZCTA crosswalk); and it measures a dimension (commercial
establishment density, employment intensity, payroll, industry mix) that **no
existing feed provides** — making it the single best answer to US-167's
"commercial-change signal" question.

**What unblocks a future REGISTER** (any one, or in combination):

1. A positive **scope decision** that Urban Signal wants a structural
   **commercial-profile context layer** — a new `COMMERCIAL_PROFILE`/`ESTABLISHMENTS`
   signal family, its own `DatasetSpec`-adjacent spec, its own H3-aggregate table,
   and a ZIP-source producer — treated as context/LIMS-exempt (precedent:
   street-cut "disruption context only — never a LIMS term").
2. A concrete consumer that needs it — e.g. an explanatory **commercial-anchor**
   for a submarket (establishment Δ + employment mix by NAICS as a prior under the
   hardcoded `base_lims`/`capex`/`sla` baselines), or a "commercial churn YoY"
   view no event feed supplies.
3. If both arrive, **register metros where SLA already exists first** (producer
   precedent + bbox already authored), as a **year-over-year level index** at
   division/submarket and H3 res 7–9, pinned to a reference year + HUD-crosswalk
   vintage, with `dynamic_spatial_fallback` mandated and every suppressed value
   carried as `None` (never zero).

Until then, the existing SLA licence flow remains the correct *timely* commercial
signal, and ZBP should not be wired in as a scoring input — but it should be the
**first commercial-context source reopened** when a context layer is approved.
