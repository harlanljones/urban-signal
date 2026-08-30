# Stream log — validate-nfhl — 2026-08-30

## Claim

- **Stream id:** `validate-nfhl`
- **Leaf files I will create/edit:** `docs/research/fema-nfhl-validation.md` (required), optionally a small leaf module + unit test under `apps/api/src/` and `apps/api/tests/unit/` if feasible. Also `.streams/validate-nfhl.md`.
- **Spine files I expect to need:** none

## Intent

Evaluate FEMA's National Flood Hazard Layer (NFHL) as a parcel/H3-level flood-risk context layer that complements the existing NFIP claims and disaster-declaration signals, for Linear US-389. Done means a validation document in the established convention (`docs/research/fema-nfhl-validation.md`) that (a) probes the live NFHL ArcGIS MapServer + overview page, (b) assesses polygon→H3 coverage aggregation, versioning by effective/map-revision date, and product-language risks, (c) maps the risks to the repo's feed families and event→H3 model, and (d) records a headline verdict (ADOPT/DEFER/REJECT) with rationale. If feasible, a spine-free leaf module + unit test proves the polygon→H3 rollup is possible without a spine edit. No feed is registered, no `FeedType` added, no spine file touched.

## Decisions

- 2026-08-30 12:5x — Stream claimed; reading existing validation docs (`epa-echo-validation.md`, `zbp-validation.md`) for the convention.
- 2026-08-30 — Live probes all succeeded against the public NFHL MapServer: 33 layers (Flood Hazard Zones id 28, NFHL Availability id 0, FIRM Panels id 3, LOMRs id 1, LOMAs id 34, Study_Info table id 41); Query+Data capabilities, `maxRecordCount` 2000, WGS84 `outSR=4326` supported. Nationwide Flood Hazard Zones count = 5,805,413; SFHA=2007 features in the New Orleans bbox; Houston bbox 6,815; Miami-Dade bbox 3,599. Polygon rings return as [lng,lat]. Field set includes FLD_ZONE, ZONE_SUBTY, SFHA_TF, STATIC_BFE, DEPTH, DFIRM_ID. FIRM Panels carry EFF_DATE + PRE_DATE; Study_Info INDX_EFFDT populated for many studies but carries ArcGIS null sentinels (year 8888/10000) for others. FEMA overview page 403-blocked from sandbox. `arcgis_client.py` fits point feeds but has no bbox geometry filter — polygon rollup needs the new leaf module.
- 2026-08-30 — Leaf module `apps/api/src/spatial/nfhl_rollup.py` + `apps/api/tests/unit/test_spatial_nfhl.py` written; 10 unit tests pass; ruff clean; `pytest -m interlock` green (exit 0). Polygon→H3 coverage proven live: NO floodplain bbox → 16 cells (res 7), 118 (res 8), 791 (res 9).

## Current step

Validation doc `docs/research/fema-nfhl-validation.md` written. Verdict: **DEFER** (strongest context-layer candidate yet; no spine edits). Live probes: MapServer fully open; fema.gov overview 403-blocked (marked in doc).

## Next step

Final verification pass and report (verdict, deliverable paths, probe success/failure, verification commands). Stream complete.
