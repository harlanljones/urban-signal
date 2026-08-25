# Census Business Formation Statistics (BFS) — validation as a metro/county contextual signal

**Date of research: 2026-08-25.** Source pages were fetched live, and the program's
own "Notice" blocks (BFS index page) and the 2026 Release Schedule were read for
cadence/lag. Where a claim could not be confirmed remotely it is marked
**unverified**. This is a *validation* document — no feed was registered, no code
was touched.

## Method, and its limits

I probed the Census BFS product pages (main index, data, county, methodology,
definitions, FAQs, release schedule, about, and the current monthly press release)
and captured the program's own notice blocks verbatim. The repo side was read
only: the feed-registration model (`apps/api/src/spatial/city_registry.py` —
`CityId`, `FeedType`, `DatasetSpec`/`CityRegistration`, `get_dataset`,
`resolve_endpoint`), the urban-unit model (`spatial/cities/*.py` — metro bbox →
division bbox → submarket → H3 cells), and the existing derived business-license
flow (`sla_move_ins_90d` / `sla_move_outs_90d` in `features/pipeline.py`).

Limits: the Annual County product is shipped as an Excel workbook and a data
dictionary PDF that the fetch returned as binary (not text-extractable), so the
*exact column set* of the county file is **unverified**. The county assertion
below rests on the page title ("Business Applications by County") and the
methodology's description of "annual counts of state by county business
applications" (which names **BA**), plus the About page's statement that the
formation series are monthly-only. Weekly/monthly internals were not probed to the
row level. No numeric point-estimate from the data itself is quoted anywhere in
this document — every number is a cadence/lag/budget characteristic, not a data
value. The section "Urban Signal fit" compares against hand-authored metro
geographies read from the repo, not from a running pipeline.

## Headline verdict

**DEFER.** BFS is a real, authoritative, census-consistent measure of business
initiation (EIN applications) and employer formation, and it does measure a
concept the existing license feeds do not. But there is **no geography that is
both metro-matched and timely**: the monthly/near-real-time series are published
only at national / regional / state level (too coarse for a single metro), and the
county-level series — the only one that can approximate a metro — is **annual**,
released ~6 months after year-end, carries differentially private noise plus a
DAO 216-26 regime switch on the horizon, and provides **no sector (NAICS) detail**.
Versus the existing per-license `sla_move_ins_90d` / `sla_move_outs_90d` flow, BFS
adds a genuinely different numerator (new-entity formation, not licence churn) but
at a granularity far coarser than any Urban Signal unit (county ≫ division ≫
submarket ≫ H3 7–9) and with a multi-month lag that makes it a trailing context,
not a leading signal. It cannot improve H3/submarket-level calibration today, and
registering it would require a new `FeedType` (spine/registry change), a
county→metro mapping, and a version-aware transform for the January 2026
HBA/CBA restatement. All four of the issue's named risks materialise and
compound. Shelf it; revisit only if a sub-state, higher-frequency product appears.

---

## Source assessment

- **Access / terms.** Census-produced federal data — U.S. government work, public
  domain (17 U.S.C. § 105); no API key, no attribution required. Distribution is
  file-based: monthly/weekly as CSV, county-annual as an Excel workbook
  (`bfs_county_apps_annual.xlsx`, 496 KB, 2005–2025, released 2026-06-10), plus a
  data-dictionary PDF. **No dedicated public API endpoint was found or verified**;
  consumption would be file download + parse.
- **Geographies.** National, region, state, county. **2-digit NAICS sector detail
  is national-level only.** County data are the **annual** "Business Applications
  by County" product; monthly/weekly series are national/regional/state. (About
  page: "Annual County BFS data start from 2005 at an annual frequency … released
  approximately 6 months after year's end.")
- **Cadence / latency.** Monthly, released ~11–12 days after month-end (about:
  "released approximately 11-12 days after the end of the observed month"). Weekly
  series stopped publishing on their own cadence as of 2024-08-29 and are now
  bundled inside the monthly release. County: annual, ~6 months after year-end.
- **Lag anomaly (observed).** The 2026 Release Schedule shows the **September,
  October, and November 2025** monthly reports all released together on
  **2025-12-12** (originally scheduled 2025-10-08, 2025-11-13, and 2025-12-12),
  i.e. a three-month lump — consistent with an appropriations lapse around that
  window. Cause attributed **unverified**. This is durable evidence that "11–12
  day" cadence is a norm, not a guarantee.
- **Revisions.** SA/NSA series are revised on release for the prior two months and
  the same two months the prior year; formation series are revised annually and
  published with the December data; NAICS codes are revised annually for the prior
  five years. The 2021 high-propensity (HBA) definition change was applied back to
  2012 via retrapolation — the same pattern as the 2026 change (below).
- **Suppression / noise.** County counts use **differentially private geometric
  noise** for all counties (privacy budget 0.5 for 2005–2018, 0.75 for 2019+);
  negative values are rounded to zero and state BA totals are made invariant
  "where the privacy budget allows," so some years will not sum to published
  totals. Critically, the county page states that **Commerce DAO 216-26 prohibits
  noise infusion**, and that while the June 2026 release still used DP noise
  (clearance began before the DAO), **future** county releases will implement
  disclosure avoidance in compliance with it — a disclosure-mechanism regime change
  that will break naive "year-over-year with noise-cancellation" assumptions.
- **Sector detail.** National 2-digit NAICS only (and weekly NAICS is
  national/regional/state). County level has **no** sector breakdown. Additionally,
  the **entire time series was restated from 2017 NAICS to 2022 NAICS** in the
  January 2026 monthly release (first release on 2022 NAICS), so sector-coded
  history is not comparable across that boundary.

### The January 2026 methodology change (verified, from the program's own notice)

From the BFS index page "Notice" block, verbatim:

> **Notice:** As of the January 2026 monthly release, applications associated with
> internet sales are excluded from the high-propensity (HBA) and corporation (CBA)
> application series. This methodology change was originally scheduled to occur
> during the November 2025 monthly release. The HBA and CBA definitions are updated
> for the **entire time series**. This update is associated with the periodic
> evaluation of the characteristics associated with high-propensity applications
> and their likelihood to turn into a business formation.

Two versioning consequences follow, each requiring a version-aware transform if the
series is ever used:

1. **Series scope:** the exclusion hits **HBA and CBA** only; the core **BA** series
   is unaffected (internet-sales applications presumably remain in BA). So any
   comparative use must pin the exact series and the vintage.
2. **Time-series break:** because HBA/CBA are restated "for the entire time series",
   a pre-Jan-2026 extract of HBA/CBA is **not directly comparable** to a post-Jan-2026
   extract at the same date. Combined with the 2022-NAICS restatement, both the
   sector-coded and the high-propensity series carry a vintage boundary at January 2026.

These are exactly the "version-aware transform" risk the issue flags — and I
confirmed the change is real and that it is *time-series-wide*, not a point fix.

---

## Urban Signal fit

Urban Signal units are strictly nested: metro bbox → division bbox(es) → submarket →
H3 cells 7–9. H3 cells at res 7 ≈ 5.2 km², res 8 ≈ 0.74 km², res 9 ≈ 0.105 km²
(Uber H3 standard). A U.S. county is orders of magnitude larger (median county on
the order of 10³ km², though highly skewed); it is larger than a typical division
or submarket and incomparably larger than any H3 7–9 cell. So:

- **Granularity mismatch is decisive.** BFS cannot inform neighborhood-level
  scoring; it is a metro/division-scale context at best, and even there it is
  coarser than the division bbox.
- **County→metro mapping is lossy and partial.** Metros in the repo are
  hand-authored boxes that only sometimes align with county (FIPS) boundaries.
  Some metros are clean multi-county unions (e.g. NOLA = Orleans + Jefferson + St.
  Bernard, which maps well to three county FIPS — and the repo's
  `JEFFERSON_METAIRIE_KENNER` / `ST_BERNARD_CHALMETTE` divisions are literally
  county-shaped). Others are **city-scoped and exclude their own county's
  outlying area** (e.g. Norfolk's bbox deliberately excludes Chesapeake / Virginia
  Beach / Portsmouth within Hampton Roads), so a whole-county BA count would
  systematically over-count a city metro. Chicago-style metros span many counties
  beyond the box. There is no county FIPS ↔ metro join in the pipeline today; it
  would have to be authored per metro.
- **Cadence eliminates the leading-signal role.** The two products are mutually
  exclusive in fit. The timely monthly series is **state/national** — far too
  coarse to be a metro signal (the repo is metro-scoped, so state-level is a
  macro-context, not a metro signal). The county series is **annual and ~6 months
  lagged** — trailing context, not a leading indicator, and noise-injected.
- **Sector detail does not exist at metro/county.** 2-digit NAICS is national-only,
  so no metro-level industry decomposition is possible.

**Conclusion on calibration:** annual, DP-noised, no-sector, 6-month-lagged county
counts cannot improve metro-level *calibration* of a signal whose resolution and
timeliness target H3 cells. The only plausible use is a coarse, quarterly/annual
"business formation is up/down vs. baseline" backdrop in explanatory reporting, and
even that would sit at metro scale where the per-license flow already provides a
finer, timelier, similarly-themed read. Whether that marginal context is worth the
registration cost is doubtful.

---

## Independent coverage check (vs. the existing SLA move-in/move-out flow)

The relevant comparison is the **`sla_move_ins_90d` / `sla_move_outs_90d`** pair
derived in `features/pipeline.py` (behind `sla_flow_ablation_enabled`) from the
already-ingested SLA licence feeds, plus the legacy `sla_new_filings_90d`. Key
contrasts:

| Dimension | SLA move-in/move-out flow | Census BFS |
|---|---|---|
| Unit | per-licence, H3 cell | county (annual) |
| Latency | effective/expiration dates → near real-time | annual, ~6-month lag |
| Concept | churn of *licensed* premises (bars, restaurants, liquor/occupational) | *new-entity* EIN formation & employer formation |
| Coverage | only metros with an SLA feed; only licensed trades | national, every county, all sectors (at national level) |
| Noise | none (record-level) | DP geometric noise at county |
| Sector | license-type granularity | none at county |

**Does BFS add independent coverage?** Conceptually yes — it measures *new employer
business formation*, which the licence feeds do not (they track existing licensed
occupants moving in/out, not the birth of a new paying entity). But that coverage
is independent in *kind* only, and it is delivered at a granularity and latency that
do not help the H3 scoring model. The SLA flow already supplies a finer, fresher
business-activity signal at the exact resolution Urban Signal scores on. BFS's
incremental value is an authoritative, comparable annual county numerator for
explanatory reporting — not new signal for calibration. Per the issue's rule
("retain only if it adds independent coverage"), BFS technically adds a distinct
numerator, but the coverage is not *usable* at the target resolution and timeliness.

---

## Risks and dependencies (mapped to the issue's risks)

1. **"County granularity too coarse for neighborhood-level scoring."** **Confirmed
   and binding.** County ≫ division/submarket ≫ H3 7–9; no per-neighborhood signal
   is recoverable.
2. **"Annual county counts use disclosure-avoidance noise; monthly series revised."**
   **Confirmed.** DP geometric noise at county (budget 0.5 / 0.75 by vintage); some
   county-years won't sum to state totals. Monthly series are concurrently revised
   (prior two months + same two months prior year) and formation series revised
   annually. **Plus a new, compounding risk I surfaced:** Commerce **DAO 216-26
   prohibits noise infusion**, so future county releases switch disclosure
   mechanisms — any county time series assembled now and appended to later would
   mix a DP-noise regime with a different regime. Treat county data as a regime
   point-in-time, not a stable series.
3. **"January 2026 methodology change excluding internet-sales applications …
   requires a version-aware transform."** **Confirmed, and it is
   time-series-wide.** HBA and CBA are restated for the *entire* series; a
   version-aware transform must (a) key on series (BA unaffected; HBA/CBA
   affected), and (b) not splice pre- vs post-Jan-2026 HBA/CBA. The concurrent
   2022-NAICS restatement adds a second vintage boundary for sector-coded series.
4. **Dependencies for any future registration.** A new `FeedType` (there is no
   BUSINESS_FORMATION / BFS member in the enum — `PERMITS`, `COMPLAINTS_311`,
   `SLA`, `DEEDS`, plus signal families `CRIME`, `STREET_CUT`, `EVICTIONS`, `STR`),
   a `DatasetSpec` + producer, a per-metro counties→bbox join, and the version-aware
   transform above. Registry/`get_dataset`/`resolve_endpoint` all assume a
   `DatasetSpec` with a watermark column and paginated extraction — none of which
   maps cleanly to an annual, file-based, non-geocoded county workbook; note that
   `DatasetSpec.extra` supports year-slicing (`endpoint_by_year`) but BFS county
   files are annual files, not per-year layers, and carry DP noise. These are all
   spine/interlock-adjacent changes, outside a leaf stream.
5. **Latency instability as a dependency.** The Sept/Oct/Nov-2025 lumped release
   shows federal shutdowns can delay BFS months at a time; a contextual feature
   built on it would be silent exactly during macro disruptions.

---

## Recommendation

**DEFER — do not register now.** The evidence does not support wiring BFS as a
metro/county contextual signal at the granularity and timeliness Urban Signal
requires. Registrar costs are nontrivial and touch spine files. **Revisit — and
re-evaluate — if any of the following arrives**:

1. A **sub-state, sub-annual** BFS product (metro/MSA or quarterly county), which
   would fix the granularity/timeliness mismatch at its root.
2. A stable **post-DAO-216-26** county disclosure regime (so the annual series
   becomes a comparable, non-noise-mixed series we can join to metros).
3. A concrete **explanatory-reporting requirement** that specifically wants a
   census-consistent annual county business-formation numerator at metro scale —
   in which case the registration should be a **citation/context** feed, not a
   scoring feed, version-keyed on series + NAICS vintage + the Jan-2026 boundary.

Until then, the existing `sla_move_ins_90d` / `sla_move_outs_90d` flow remains the
correct, finer, timelier business-activity signal, and BFS should not replace or
compete with it.
