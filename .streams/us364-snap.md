# Stream log — us364-snap — 2026-08-27

## Claim

- **Stream id:** us364-snap
- **Leaf files I will create/edit:**
  - `apps/api/tests/unit/test_producers_snap.py` (new — parse-chain + registration-shape tests)
  - `.streams/us364-snap.md` (this log)
  - `.streams/dispatch-log.md` (outcome row, close-out)
  - `apps/product/public/` regenerated facts artifacts (mechanical `facts:export` output)
- **Spine files I expect to need:**
  - `apps/api/src/config.py` (SNAP endpoint setting)
  - `apps/api/src/spatial/city_registry.py` (starter-set SLA DatasetSpecs)

## Intent

Register USDA FNS SNAP Retailer Locator as `FeedType.SLA` DatasetSpecs on a
geographically spread starter set of 4–6 metros that currently have no SLA feed.
Same ArcGIS FeatureServer endpoint + shared field_map helper for all cities,
per-city `where` filter on State. Watermark = authorization start/last-update
column verified live. Zero new producer machinery — SLALicensesProducer as-is.
Gates: pytest -m interlock green, full suite green, ruff clean on touched paths,
product-site facts re-exported + lint green.

## Decisions

- 2026-08-27 — Ticket US-364 claimed and self-assigned.
- 2026-08-27 — **Live probe (a): FeatureServer resolved.**
  `https://services1.arcgis.com/RLQu0rK7h4kbsBq5/arcgis/rest/services/snap_retailer_location_data/FeatureServer/0`
  (single layer, serviceItemId 8b260f9a10b0459aa441ad8588c2251c). Fields:
  `Record_ID, Store_Name, Store_Street_Address, Additonal_Address (sic), City,
  State, Zip_Code, Zip4, County, Store_Type, Latitude, Longitude,
  Incentive_Program, Grantee_Name, ObjectId`. 252,080 rows total; TX alone
  20,715 (`where="State = 'TX'"` verified live). maxRecordCount=1000,
  objectIdField=ObjectId. `Record_ID` verified UNIQUE across all 252,080 rows
  (groupBy outStatistics: max group size 1) → license_id.
- 2026-08-27 — **Live probe (a) caveat: NO auth-date fields on the live
  layer.** `Authorization Date`/`End Date` exist only in the historical zip.
  Verified live: field list carries no esriFieldTypeDate column. The ticket's
  issued=auth-start / expiry=auth-end mapping applies to the historical zip:
  probed `https://www.fns.usda.gov/sites/default/files/resource-files/snap-retailer-locator-data2005-2025.zip`
  (23.1 MB, member `Historical SNAP Retailer Locator Data 2005-2025.csv`,
  703,441 rows, header `...,Authorization Date,End Date` M/D/YYYY — parseable
  by `_parse_datetime`). CSVClient zip_member fallback path is real but the
  zip is frozen at 2025-12-31; the live layer is the only forward-looking
  source → ArcGIS registered, zip documented for backfill follow-up.
- 2026-08-27 — **Live probe (b): cadence.** Item description (official):
  "The data is updated every 2 weeks." editingInfo.lastEditDate = epoch
  1787161209953 → 2026-08-19 (8 days before probe). → `expected_cadence_days=14`.
- 2026-08-27 — **Watermark/ingestion_mode.** No per-row date column on the
  live layer → `watermark_col=""` + `ingestion_mode="snapshot"` (KC SLA
  precedent, US-134): full registry pull per cycle, cross-run id-dedup turns
  re-polls into the add/remove diff — which IS the open/close signal here.
- 2026-08-27 — **H3 out-of-bbox behavior (verified in code).**
  `H3SpatialIndexer.get_multi_res_hierarchy` computes H3 for ANY lat/lng — no
  bbox gate. State-filtered rows outside the metro bbox still get global H3
  tags; metro scoping happens downstream (dashboards/jobs), not at parse.
- 2026-08-27 — **Starter set (6, geographically spread, all SLA-less today):**
  dallas (TX), denver (CO), columbus (OH), raleigh (NC), boise (ID), wichita
  (KS) — six distinct states. Per-city `where="State = '<ST>'"`. Same endpoint
  + shared module-level field map + `snap_sla_spec(state)` helper in the
  registry (DRY, additive spine edit).

## Current step

DONE — all gates green. Changeset left uncommitted for the maintainer.

## Next step

Nothing. (Follow-ups for future tickets: historical-zip auth-date backfill;
extend SNAP to remaining SLA-less metros; per-metro County/City where-filters
if state coarseness becomes a product problem.)

## Outcome (close-out)

- Starter set: dallas (TX), denver (CO), columbus (OH), raleigh (NC),
  boise (ID), wichita (KS) — six SLA-less metros, one per state, spread
  across South/Mountain/Midwest/Southeast/Northwest/Plains.
- Endpoint: `services1.arcgis.com/RLQu0rK7h4kbsBq5/.../snap_retailer_location_data/FeatureServer/0`
  via `settings.arcgis_snap_retailers_url`; shared `SNAP_SLA_FIELD_MAP` +
  `snap_sla_spec(state)` helper in city_registry.py (DRY; per-city delta is
  one line + comment).
- Acquisition contract: snapshot mode (no per-row date field on the live
  layer — verified), `watermark_col=""`, id_keys Record_ID/ObjectId
  (Record_ID unique across 252,080 rows — verified via groupBy outStatistics),
  `expected_cadence_days=14` (FNS: "updated every 2 weeks"; lastEditDate
  2026-08-19 at probe), interval 1800s, where="State = '<ST>'".
- Live layer carries NO auth start/end dates → events ship null
  issued/expiry; open/close signal comes from the id-dedup snapshot diff
  (KC SLA US-134 precedent). Historical zip (auth dates, frozen 2025-12-31)
  probed and documented as backfill follow-up, NOT registered.
- H3 caveat verified in code: no bbox gate — state-filtered out-of-metro rows
  still index global H3 cells; metro scoping stays downstream. In-bbox rows
  resolve real divisions (Dallas fixture → NORTH_DALLAS_PRESTON).
- Gates: `pytest -m interlock` 22 passed; full suite 1585 passed / 3 skipped
  (baseline 1574 → +11 new SNAP tests; 5 stale per-city tests refreshed
  faithfully); product `facts:export` + `bun run lint` green; ruff: identical
  rule-hit profile to baseline on all touched paths (zero new findings).
- Pre-existing dirty files NOT mine (left in changeset): `dispatcher.py`
  (wave-3 calibration set), `.streams/dispatch-log.md` (orchestrator entry).
