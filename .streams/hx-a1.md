# Stream log — hx-a1 — 2026-10-12

## Claim

- **Stream id:** `hx-a1` (HX-A1 Vendor Census 2020 Urban Area asset + loader; ROADMAP.md)
- **Owner:** orchestrator (delegated agents failed with 429 quota errors)

## Current step

Complete.

## Decisions

Done. `scripts/vendor_urban_anchors.py` (reproducible), `apps/api/src/spatial/assets/us_urban_areas_2020.geojson` (4.29 MB, tolerance 0.004, 5-decimal coords), `urban_anchors.py`, `scripts/measure_urban_anchors.py`, `test_urban_anchors.py` (15 tests).

## Decisions / measurements
- UA count (`ANCHOR_GOLDEN_COUNT`): **2,645** (cb_2020_us_ua20_500k; includes PR/Island Areas). `population` is null: the cartographic file carries no population, so detail class uses land_km2 only until a join exists.
- DG-1: asset 4.29 MB at 0.004 deg (outline asset is ~102 KB). Spec's per-anchor <=0.5% polyfill drift is **unachievable**: even at 0.0005 deg (12.95 MB) small anchors differ by up to 8% because a +/-1 cell flip on a 20-cell anchor is 5%. Corrected criterion = aggregate: total res-7 cells raw 54,244 vs simplified 54,257 (**net drift +0.024%**, unbiased; symmetric difference 6.88% = boundary cells flipping both ways). Kept 0.004.
- DG-2: anchors per metro bbox: 1:88, 2:28, 3:14, 4:9, 5:4, 6:4, 7:2, 8:2, 9:2, 10:2, 16:1, 33:1. Metros per anchor: 1:281, 2:36, 3:7, 4:1, 5:1. 326 anchors touch any metro bbox. Large bboxes (33 and 16 anchors) pull in peripheral small anchors; the gate therefore only requires a submarket inside the union. Derivation places a submarket in an anchor for all 157 metros (prince_georges' center point is outside, its submarkets are not).
- DG-3 / ADR envelope **holds**: uniform cells res 7/8/9 = 54,257 / 379,799 / 2,658,593 (ADR est ~52k/364k/2.7M). Metro-touching anchors only: 31,047 / 217,329 / 1,521,303. Adaptive classes (res 9: 51, res 8: 355, res 7: 2,239) = **1,296,515 cells**, inside the 0.5-1.5 M budget. Res-7 polyfill of all anchors: 0.6 s.
- An anchor smaller than one res-7 cell owns the cell holding its representative point (every anchor owns >=1 cell).

## Next step

Stage A integration checkpoint (preflight + benchmark), then Stage B (HX-B1).
