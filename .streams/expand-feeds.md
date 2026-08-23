# Stream log — expand-feeds — 2026-08-23

## Claim

- **Stream id:** `expand-feeds`
- **Leaf files I will create/edit:** `.streams/expand-feeds.md`,
  `docs/research/current-city-feed-gaps.md`
- **Spine files I expect to need:** none (research-only; source is read-only)

## Intent

Live-probe every registered municipal feed across the five metros plus LA
replacement-feed candidates, and record the findings as they are learned in
`docs/research/current-city-feed-gaps.md`. Done looks like: (1) an LA 311
and LA deeds candidate table with dataset IDs, platforms, update dates,
coordinate fields, and required parser fallbacks; (2) an SF deeds-upgrade
verdict backed by evidence of exactly what was searched; (3) a freshness
audit table covering all ~19 registered endpoints with newest-record date
and row count, stale entries flagged. Every number in the doc comes from a
real HTTP GET made today; anything unverified says so.

## Decisions

- 2026-08-23 (start) — Scope fixed to three workstreams: LA gaps (priority),
  SF deeds assessment, all-feed freshness audit. Format mirrors
  `docs/research/city-expansion-candidates.md`. No source edits; findings
  only name what implementation *would* cost.
- 2026-08-23 — Probe recipe settled after first pass: catalog
  `rowsUpdatedAt` via `/api/views/<id>.json` (federated catalog returns
  nulls/misses), newest record via `$select=<wm>&$order=<wm> DESC&$limit=1`
  with `IS NOT NULL` guard. Text-typed watermarks need format-aware re-checks
  before declaring staleness (NYC permits proved this immediately).
- 2026-08-23 — FINDING (audit): Chicago deeds `x5kz-z7if` returns
  `dataset.missing` — a registered feed is dead. Replacement candidate found:
  Cook County Assessor Parcel Sales `wvhk-k5uv` (updated 2026-08-19, newest
  sale 2026-07-14, no coordinates).
- 2026-08-23 — FINDING (audit): NYC permits `ipu4-2q9a` is alive (newest
  issuance 08/21/2026) but its watermark column is text with two formats;
  naive max/ordering silently misses post-2020 rows. Flagged as caveat, not
  stale.
- 2026-08-23 — FINDING (audit): SF permits `i98e-46e2` is `not_found`
  (successor `i98e-djp9`, 1.29M rows, live). SF deeds `5cei-gny5` serves
  Eviction Notices; the real roll is `wv5m-vpq2` (roll year 2025, loaded
  2026-06-26, geocoded). Both fixes are config lines.
- 2026-08-23 — FINDING (LA 311): feed is back. Current set
  `2cy6-i7zn` MyLA311 Cases 2026 — refreshed today, 1,531,913 rows through
  2026-08-23T13:39Z, 93.8% geocoded via `geolocation__latitude(s)__s`;
  backfills `73a2-6ar5` (Mar–Dec 2025) and yearly sets 2015–2024. Registry
  comment ("archived 2013-2014 only") is obsolete. New Salesforce-style
  schema → six parser fallbacks named in the doc.
- 2026-08-23 — FINDING (LA deeds): no transaction-level source exists.
  County portal left Socrata for ArcGIS Hub (DCAT sweep of 1,109 datasets:
  zero sale/deed/transfer datasets; RR entries are electoral maps); AGOL
  title searches for parcel sales / transfer tax + Los Angeles: zero hits.
  Best substitute is Assessor Parcel Data rolls table (12.1M rows,
  `RecordingDate` + `CENTER_LAT/LON` + roll values, NO sale price) —
  recommendation: keep DEEDS unregistered for LA.
- 2026-08-23 — FINDING (audit): KC ArcGIS sales layer stale ~9 months
  (lastEditDate ≈ 2025-11-28, zero 2026 sales). WA LCB feed healthy but only
  23 rows by design (notifications, not a registry).

## Current step

DONE. Deliverable written: `docs/research/current-city-feed-gaps.md`
(method + limits, 18-row freshness audit, LA 311/deeds findings, SF verdict,
adjacent finds, implementation-cost section, explicit unverified list).
Both leaf files complete.

## Next step

For the orchestrator: the three config-line fixes (SF deeds → `wv5m-vpq2`,
SF permits → `i98e-djp9`, Chicago deeds → `wvhk-k5uv`) plus the LA 311
registration are ready to dispatch; run the interlock gate
(`pytest -m interlock`) on any branch that touches them.
Follow-up research candidates: King County GIS inquiry on the sales pause;
DOB NOW vs BIS completeness check for NYC permits.
