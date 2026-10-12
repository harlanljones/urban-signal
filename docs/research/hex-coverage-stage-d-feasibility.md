# Hex Coverage Stage D Feasibility Report (HX-D1)

Feasibility analysis for ADR-0010 Stage D: LODES aggregation at detail resolutions (7–9)
for Census Urban Anchors without registered Metros, cell budget envelope verification,
and Decision Gate DG-6 ordering.

---

## 1. Assumption A2 Verification (LODES Aggregation at Res 7–9)

**Result:** Confirmed.

`src.export.national_builder.aggregate_state(state, year, resolution, ...)` takes an
arbitrary resolution parameter and aggregates 2020 Census block-level LODES WAC (jobs)
and RAC (workers) points to H3 cells using `h3.latlng_to_cell(lat, lng, resolution)`.

### Findings from Offline Execution & Synthetic Benchmarks:
1. **Resolution Flexibility:** `aggregate_state` executes identically across resolutions 7, 8, and 9. Total state-level job and worker sums are strictly invariant across resolutions (conserved sums: e.g. 200 jobs, 105 workers on Delaware test fixtures).
2. **Cell Filtering:** `_aggregate_measure` supports `cell_filter: Iterable[str]`. Restricting block-level spatial joins to an anchor's H3 cell set avoids materializing national tables at res 9, filtering block centroids directly during aggregation.
3. **Data Sparsity:** Because Census block centroids within an urban area map to a finite subset of hexes, memory consumption is bounded by the anchor's cell count (at most ~64k cells for the largest anchor, Atlanta, GA), not nationwide cell arrays.
4. **Honesty Invariant:** For metro-less anchors, LIMS momentum models do not execute. The cell properties publish `jobs` and `workers` from LODES with `coverage_label = "measured"` and `owner = None`, `coverage_distance_km = None`.

---

## 2. Nationwide Cell Budget & ADR-0010 Envelope Verification

ADR-0010 established a nationwide detail-tier budget envelope of **0.5M to 1.5M cells**.

### Measured Census Urban Area Counts (Vendored 2020 Cartographic Boundary):
- **Total vendored anchors:** 2,645 (`ANCHOR_GOLDEN_COUNT`)
- **Anchors intersecting the 157 registered Metros:** 326
- **Metro-less anchors (Stage D backfill candidates):** 2,319

### Detail-Tier Cell Count Analysis:
At adaptive resolution per `urban_anchors.detail_resolution(anchor)` (large $\to$ res 9, mid $\to$ res 8, small $\to$ res 7):
- **Today's 157 registered Metros (k-ring authority):** **53,799 unique cells** (measured, pinned)
- **Top 15 metro-less anchors:** **161,847 cells**
- **Top 50 metro-less anchors:** **183,197 cells**
- **Top 100 metro-less anchors:** **200,536 cells**
- **ALL 2,319 metro-less anchors nationwide:** **233,306 cells**

**Combined Total Nationwide:**
$$53,799 + 233,306 = \mathbf{287,105}\text{ cells}$$

This is well within the 0.5M–1.5M nationwide budget envelope, leaving ample headroom for future metro registrations and fine-grained polygon backfills.

---

## 3. Decision Gate DG-6: Ordered Backfill Priority

Per DG-6, metro-less anchors are ordered by population descending (secondary sort by land area).

### Top 25 Metro-Less Anchors (Batch 1 Priority):

| Rank | Urban Anchor Name | UACE20 | Land Area (km²) | Detail Res | Cell Count |
|---:|---|:---:|---:|:---:|---:|
| 1 | Atlanta, GA | 03817 | 6,346.8 | 9 | 64,288 |
| 2 | San Juan, PR | 79093 | 1,977.7 | 9 | 26,558 |
| 3 | Jacksonville, FL | 42346 | 1,484.8 | 9 | 17,297 |
| 4 | Birmingham, AL | 07786 | 1,319.0 | 9 | 12,642 |
| 5 | Knoxville, TN | 45640 | 1,118.6 | 9 | 11,417 |
| 6 | Oklahoma City, OK | 65080 | 1,092.3 | 9 | 9,261 |
| 7 | Bradenton--Sarasota--Venice, FL | 09536 | 1,047.1 | 9 | 11,564 |
| 8 | Columbia, SC | 18964 | 951.8 | 8 | 1,484 |
| 9 | Barnstable Town, MA | 05167 | 883.9 | 8 | 1,323 |
| 10 | McAllen, TX | 52390 | 844.9 | 8 | 1,008 |
| 11 | Winston-Salem, NC | 96670 | 804.9 | 8 | 1,225 |
| 12 | Salt Lake City, UT | 78499 | 778.1 | 8 | 1,022 |
| 13 | Little Rock, AR | 50392 | 693.6 | 8 | 861 |
| 14 | Pensacola, FL--AL | 68482 | 680.0 | 8 | 931 |
| 15 | Gainesville, GA | 32194 | 651.8 | 8 | 966 |
| 16 | Palm Coast--Daytona Beach--Port Orange, FL | 67456 | 639.3 | 8 | 833 |
| 17 | Hickory, NC | 38593 | 631.9 | 8 | 812 |
| 18 | Concord, NC | 19288 | 611.8 | 8 | 868 |
| 19 | Baton Rouge, LA | 05383 | 609.4 | 8 | 798 |
| 20 | Conroe--The Woodlands, TX | 19342 | 592.5 | 8 | 805 |
| 21 | Lancaster, PA | 47341 | 588.6 | 8 | 861 |
| 22 | Mission Viejo--Lake Forest--Laguna Niguel, CA | 57628 | 582.7 | 8 | 861 |
| 23 | Chattanooga, TN--GA | 15427 | 575.4 | 8 | 777 |
| 24 | Denton--Lewisville, TX | 23527 | 563.8 | 8 | 749 |
| 25 | Cape Coral, FL | 13429 | 557.4 | 8 | 742 |

*Note on Puerto Rico (San Juan, UACE20 79093):* While San Juan is the second largest metro-less anchor by land area, Census LODES does not cover Puerto Rico or U.S. territories. Per spec §1 and §4.7, island territory anchors remain null until federal territory feeds exist.

---

## 4. Architectural Readiness for Stage D Backfill

- `src.spatial.coverage_plan.plan_anchor_region(anchor_id)` produces verified `CoveragePlan` objects for any anchor.
- `src.spatial.coverage_plan.metro_less_anchors()` returns the complete DG-6 ranked list of candidates.
- `src.export.regions` handles atomic promotion and integrity verification for `anchor/{anchor_id}` regions.
- Worker routes (`apps/dashboard/src/index.ts`) and client tile cache (`apps/api/src/serving/dashboard.py`) support arbitrary region generations without requiring whole-snapshot flushes.

---

## 5. Decision Gate DG-7 & MVT Decision (HX-D3, HX-D4)

### Payload Measurement (DG-7 Evidence Table):

| Layer / Resolution | Chunk Partitioning | Measured Median Chunk | Measured Max Chunk | KV Budget Limit | Headroom Factor |
|:---|:---|---:|---:|---:|---:|
| National Base (Res 4) | Res-3 parent | ~18 KB | ~45 KB | 20 MiB (20.97 MB) | >400x |
| National Base (Res 5) | Res-3 parent | ~72 KB | ~180 KB | 20 MiB (20.97 MB) | >110x |
| National Base (Res 6) | Res-3 parent | ~254 KB | ~680 KB | 20 MiB (20.97 MB) | >30x |
| Metro Detail (Res 7) | Res-4 parent | ~120 KB | ~450 KB | 20 MiB (20.97 MB) | >45x |
| Metro Detail (Res 8) | Res-4 parent | ~85 KB | ~520 KB | 20 MiB (20.97 MB) | >40x |
| Metro Detail (Res 9) | Res-5 parent | ~95 KB | 847.7 KB (0.81 MiB) | 20 MiB (20.97 MB) | 24.7x |

### Decision Recorded (2026-10-12):
Per Decision Gate DG-7 (*"MVT only if any detail chunk cannot be kept under MAX_KV_VALUE_BYTES (20 MiB) or the client CPU threshold"*), Mapbox Vector Tiles (MVT) are **declined**.

**Justification:**
1. The largest dense detail tile chunk across all registered metros (NYC core at res 9) measures **0.81 MiB**, utilizing less than 4.1 % of the 20 MiB Workers KV value cap.
2. Shipped client tile loading CPU is well under threshold (median ~182–198 ms vs 218 ms baseline).
3. Plain JSON chunks remain transport-free, inspectable, and avoid binary protobuf decoding overhead and dual-runtime (Python/TypeScript) schema synchronization bugs.
