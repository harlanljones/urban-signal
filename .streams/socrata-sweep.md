# Stream log — socrata-sweep — 2026-08-23

## Claim

- **Stream id:** `socrata-sweep`
- **Leaf files I will create/edit:** `.streams/socrata-sweep.md`,
  `docs/research/socrata-sweep.md`
- **Spine files I expect to need:** none

## Intent

Systematic redo of the coarse city-expansion sweep
(`docs/research/city-expansion-candidates.md`): cross-domain Socrata catalog
scans (multiple phrasings per feed family, not top-hit-only), then live direct
resource verification on the top candidate metros. Deliverable is a ranked,
verified candidate table for permits / 311 / licenses / deeds-sales feeds, with
recommendation of next cities after New Orleans/Austin (excluded from ranking;
owned by another stream).

## Decisions

- 2026-08-23 — Method fixed: breadth-first via central catalog queries WITHOUT
  domain restriction (16 phrasings across the 4 families, ~3.3k raw hits),
  aggregated per-domain; curated ~55-domain targeted pass added because the
  global top-500 hides entire cities. Verification via direct `$limit=1`,
  `count(*)`, `IS NOT NULL` newest-row, and bounded-window counts. Scratch
  scripts + probe logs in `/tmp/opencode/socrata-sweep/` (outside repo).
- 2026-08-23 — Catalog learnings: freshness field here is
  `resource.data_updated_at` (ISO string); `/api/catalog/v1/domains` does not
  exist on this deployment; domain-local catalogs can 404 even for Socrata
  hosts — use central API with `domains=` filter, which doubles as a membership
  test (404 = not indexed). `/api/views/*` metadata blocked without app token,
  so column lists came from sample rows.
- 2026-08-23 — Top-hit trap reconfirmed and generalized: KC's `property sales`
  top hit is again the Monthly Car Auction (`7wyi-8tqr`); Fulton's was Vendor
  Payments; Mesa's "Tax Licenses" is monthly count aggregates; Mesa/Ramsey
  "service requests" hits are internal IT metrics. All avoided by name triage +
  direct probes.
- 2026-08-23 — Data traps found during verification: PG County
  `transfer_date` is YYYYMMDD text with `'ZZZZZZZZ'` sentinels (naive DESC /
  `>=` comparisons fabricate activity — 4,647 apparent vs 0 real transfers in
  60d); Cincinnati combo permits carry year-3201 sentinel dates; Norfolk
  permits carry future-dated applications; Norfolk `bnrb-u445` has point
  geometry but NO date column (unusable as watermark).
- 2026-08-23 — Ranking settled: **Norfolk 4/4** (incl. real transfer feed,
  freshest 2026-08-19), **Cincinnati 3/4** (33k/60d geocoded 311; no sales),
  **Baton Rouge 3/4** (geocoded 311 + point-geocoded business registry; no
  market sales). Next tier: Montgomery Cty MD (permits+licenses; MC311 lacks
  coordinates), Orlando (clean permits+licenses only). PG County near-miss.
  Norfolk arguably beats NOLA (narrower deeds) and Austin (2 families);
  Cincinnati/BR match NOLA's family count with stronger geo but lack sales.

## Current step

Done. Both leaf files written:
`docs/research/socrata-sweep.md` (full survey in established format: method +
limits, ranked table, six verified per-city subsections, skipped/dead-end list)
and this log. No other repo files touched; no git commands run (orchestrator
commits).

## Next step

If resumed: (1) decide whether Norfolk's fiscal-year dataset partitioning needs
a registry convention before onboarding; (2) optional re-probe of PG County in
~a quarter to see if permits/property feeds caught up; (3) Everett WA flagged
as best small-city find if a sub-market strategy ever exists.
