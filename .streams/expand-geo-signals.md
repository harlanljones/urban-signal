# Stream log — expand-geo-signals — 2026-08-23

## Claim

- **Stream id:** `expand-geo-signals`
- **Leaf files I will create/edit:** `.streams/expand-geo-signals.md`, `docs/research/metro-expansion-and-new-signals.md`
- **Spine files I expect to need:** none — research-only stream; source untouched.

## Intent

A survey-grade research doc (`docs/research/metro-expansion-and-new-signals.md`)
covering two halves: (1) for each of the 5 registered metros, which adjacent
counties publish open-data portals carrying any of the 4 feed families
(permits / 311 / licenses / deeds), probed live where possible, with a verdict
per county on whether it is worth registering as new divisions/submarkets; and
(2) a survey of candidate NEW signal types beyond the current 4 feeds (crime,
evictions, transit/service changes, street-cut/utility permits, business move
ins/outs, STR registrations) with verified dataset IDs per metro and an honest
LIMS-input vs context-feature fit assessment. Structural cost of geography
expansion (division nesting invariant, hand-authored submarkets, spine edits)
flagged throughout. Done = both files complete, stream log shows done.

## Decisions

- 2026-08-23 (start) — Scope fixed to the brief's county lists; survey-grade,
  not exhaustive. Socrata discovery API is the primary probe; ArcGIS Hub org
  sites probed via their public REST/opendata endpoints. Every dataset listed
  as "confirmed" gets a direct API probe with recorded `rowsUpdatedAt` or
  equivalent. Unverified claims marked explicitly.
- 2026-08-23 — Read context: exemplar doc, README registry table,
  city_registry.py, spine manifest, parallel-streams containment invariant.
  Key structural fact confirmed: each metro is ONE metro bbox + division
  bboxes nested inside it + hand-authored submarket points inside divisions;
  expanding geography means editing spine files (`city_registry.py`,
  `src/config.py`, producers) plus a new/larger hand-authored cities module —
  NOT leaf work unless done as an entirely separate registration.
- 2026-08-23 — Probe method settled: Socrata domains via discovery API (most
  counties NOT on Socrata); ArcGIS Hub sites via DCAT-US feed + AGOL item +
  direct FeatureServer query. Calibration note: hub.arcgis.com answers HTTP
  200 for ANY hostname — only a site's own API/DCAT response counts as proof.
- 2026-08-23 — SEATTLE: Pierce County = strong permits-only candidate
  (FeatureServer live 2026-08-21, full date model + valuation + address,
  state-plane XY solvable via outSR=4326). Snohomish = quarterly sales
  snapshot w/ month-granularity dates; permits snapshot unusable → skip.
- 2026-08-23 — CHICAGO COLLAR: all five collar counties are a structural dead
  end (IL counties don't run 311; permits municipal/Accela/SmartGov; deeds via
  paid eSearch). Lake/Kane/McHenry Hub portals exist but carry only cadastral
  data. Written to doc. Realistic widening unit = individual municipalities.
- 2026-08-23 — BAY AREA: no county publishes any of the 4 feeds live.
  San Mateo Socrata = GIS boundaries only. Santa Clara sccgov Socrata (1710
  datasets) = crime `n9u6-aijz` live daily, NO permit/sales feeds (verified by
  scanning full catalog). Alameda Hub = crime layer LIVE w/ point geometry +
  Assessor Ownership Transfer List (true transfer feed w/ value_from_trans_tax)
  but STALE (newest row 2023-04). Contra Costa DCAT ≈ empty. All written.

- 2026-08-23 — LA COUNTIES: all four skip. Orange (933-dataset Hub) and San
  Bernardino (253) are cadastral/water layers only; Riverside's one "Permits"
  layer stale since 2023-09; Ventura no portal found (marked unverified).
- 2026-08-23 — §2 SIGNALS probed and written: crime live in NYC/CHI/SF/SEA
  (`qgea-i56i`+`5uac-w243`, `ijzp-q8t2`, `wg3w-h783`, `tazs-3rd5`; lat/lon
  confirmed on SEA+CHI columns); LA crime exists (`2nrs-mtv8`) but frozen at
  2020–2024 mid-NIBRS transition — notable: data.lacity.org is ALIVE despite
  the retired 311 feed. Evictions NYC-only live (`6z8x-wfk4`, updated survey
  day; Cook County verified absent). Street cuts NYC `tqtj-sjs8` + CHI CDOT
  family live. STR: CHI `qfyy-956j` live only. Transit context: CTA
  `5neh-572f` live, MTA `vxuj-8kew` ends 2025-01. Move-ins/move-outs = pure
  derivation over existing SLA feeds, zero new endpoints.
- 2026-08-23 (done) — Recommendation written: Pierce County permits-only
  separate registration is the ONLY geography worth adding; license-status
  transitions first among signals, crime second (behind ablation). Both leaf
  files complete.

## Current step

DONE. Research doc complete (method + limits, structural-cost analysis,
per-metro tables for all 5 metros / 19 counties, new-signals table with
verified IDs, ranked recommendations). Stream log closed out.

## Next step

If resumed: re-probe before acting — highest-value re-checks are the Alameda
Assessor Ownership Transfer List (if it refreshes it becomes a real deeds
feed) and LAPD's post-NIBRS crime successor dataset. Implementation streams
would be: (a) pierce-county registration (leaf cities module + additive spine
edits + interlock gate), (b) SLA flow-signal derivation, (c) crime producer
prototype behind ablation flag.
