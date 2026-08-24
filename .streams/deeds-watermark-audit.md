# Stream log — <stream-id> — <date>

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** <short-id, e.g. `city-new-orleans`>
- **Leaf files I will create/edit:** <exact paths — if you cannot name them,
  you are not decomposed enough to run in parallel>
- **Spine files I expect to need:** <paths from docs/agents/spine-manifest.txt>

## Intent

<One paragraph: what done looks like for this stream.>

## Decisions

<Appended as made. Findings go here the moment they are learned (F5) —
not at the end.>

- <timestamp> —

## Current step

<What is in flight right now, so an interrupting agent knows where the
write boundary was.>

## Next step

<What you would do next if you resumed yourself.>
# Stream log — deeds-watermark-audit — 2026-08-24

## Claim

- **Stream id:** deeds-watermark-audit
- **Leaf files I will create/edit:** .streams/deeds-watermark-audit.md, docs/research/deeds-watermark-audit.md
- **Spine files I expect to need:** NONE (apps/api/src/config.py recommendations only — interlock process)

## Intent

For each of the 6 stale deeds feeds (nyc, chicago, sf, seattle, new_orleans,
washington_dc) determine: genuinely slow source vs wrong/lagging watermark
column vs dead service. Also explain future-dated watermarks (philadelphia
rtt_summary 2066, detroit property sales 2925). Output:
docs/research/deeds-watermark-audit.md with per-feed verdict table, curl
evidence, recommendations (no spine edits).

## Decisions

- (start) config.py holds endpoints only; watermark_col specs must be in
  apps/api/src/spatial/city_registry.py — reading that next.

## Decisions

- 08-24T1x — Declared watermark_cols captured from city_registry.py:
  - nyc/deeds (bnx9-e6tj): `recorded_datetime`
  - chicago/deeds (wvhk-k5uv Cook County): `sale_date`
  - san_francisco/deeds (wv5m-vpq2): `closed_roll_year` (!)
  - seattle/deeds (KC PARCEL_SALES3YR_AREA_287 FS/0): `SaleDate`
  - new_orleans/deeds (hpm5-48nj NORA Sold Properties): `sale_date`
  - washington_dc/deeds (Property_and_Land FS/57): `SALE_DATE`
  - philadelphia/deeds (carto://phl.carto.com/rtt_summary): `document_date`
    (field_map maps recorded_date <- recording_date BECAUSE document_date is
    NULL/sentinel-prone — registry comment cites docs/research/non-socrata-platforms.md §Philadelphia)
  - detroit/deeds (assessor_property_sales_view FS/0): `sale_date` ('2925-12-24'
    typo-year sentinel tolerated per registry comment)

## Current step

Live curl sampling of each feed (max(declared col) + candidate recency columns + layer metadata).
- 08-24 — Live evidence collected (all 7 endpoints reachable, no blocks):
  - nyc: max(recorded_datetime)=2026-07-31; ZERO rows after Aug 1; max modified_date/good_through_date identical → source publication stall; right column.
  - chicago: max(sale_date)=2026-07-14; healthy monthly volume (4-6k) trailing ~5wk (MYDEC→Assessor publish); no insert-timestamp col → genuinely slow.
  - sf: closed_roll_year is string "2025" — parse_watermark can't parse it (why probe saw nothing); dataset = ANNUAL tax roll (2007-2025, 3.93M rows, data_loaded_at max 2026-06-26) → WRONG COLUMN + annual-by-design. Better col: data_loaded_at.
  - seattle: layer alive, 110857 rows, lastEditDate 2025-11-28 (~9mo frozen), no sibling sales service on org host, only SaleDate field → DEAD PUBLICATION; needs replacement source (spine decision).
  - new_orleans: NORA disposals, 10 rows in all of 2026, single date column → genuinely irregular; threshold issue not column issue.
  - washington_dc: max(SALE_DATE)=2026-08-12 but GIS_LAST_MOD_DTTM stamped today → healthy/batchy; 1900-01-01 sentinel noted; no change.
  - philadelphia: document_date poisoned — max year 9798 (MERS mortgage assignments w/ loan-term years), 77% NULLs, exactly ONE row in [now,2100): the 2066-06-01 HUD grantee deed recorded 2026-05-28. recording_date max=2026-07-02 continuous → WRONG COLUMN; recommend watermark_col+order_by → recording_date. CartoClient sentinel bound [1900,2101) admits 2066.
  - detroit: layer edited YESTERDAY (2026-08-23), 2105 real sales since Jun 1; sentinels = typo years (2925-12-24, 2206-01-28, 2202-11-20 ≥2100 count=3, +2062-04-09 in-band) absorbed by probe ≤now filter → healthy, documented in registry already.
- 08-24 — Reconciliation note recorded: CI-reported 2066/2925 watermarks inconsistent with HEAD newest_watermark() ≤now filtering; flagged honestly in findings doc.

## Outcome

Findings written to docs/research/deeds-watermark-audit.md:
verdict table + per-feed curl evidence + recommendations. Spine changes
recommended (NOT applied): philly watermark_col→recording_date (top value),
sf watermark_col→data_loaded_at; seattle needs source replacement (spine
decision); nyc/chicago/nola/dc correct-as-declared.

## Next step

Hand recommendations to a spine-holding stream for city_registry.py edits via
interlock gate (`pytest -m interlock` from apps/api). Optional leaf follow-up:
investigate King County REET/excise sales as seattle/deeds replacement source.
