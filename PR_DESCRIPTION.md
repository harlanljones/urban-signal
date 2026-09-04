# US-421: Register Boulder CO and Fort Collins CO permits + wire Texas & Colorado state super-feeds

## Summary

Implements the four items from the southwest/mountain expansion probe
(`docs/research/southwest-mountain-expansion-probe-2026-08-30.md`):

1. **Boulder, CO permits** — already live-registered (US-245); verified and
   documented, no code change needed.
2. **Fort Collins, CO permits** — new city registration (`fort_collins`),
   Building Permits feed from the City of Fort Collins ArcGIS Hub.
3. **Texas state super-feed** — TX TREC (broker/app), TDLR, and TABC specs
   (already built generically by US-397/US-372) verified to cover the six
   named metros' counties (Lubbock, Corpus Christi, Laredo, Rio Grande
   Valley, College Station, Killeen), with a new test suite proving it.
4. **Colorado DORA super-feed** — new leaf spec module for the statewide
   occupational and real-estate license registries, city-sliced for
   Boulder/Fort Collins.

Follows this repo's established "leaf spec, spine wires it" convention for
state super-feeds (see `tx_trec_specs.py` / `state_license_specs.py`,
US-397/US-372): the CO DORA specs are copy-pasteable `DatasetSpec` dicts,
proven against the live producer, but not registered into any
`CityRegistration` — that remains a separate spine decision, same as every
other state-super-feed leaf in this repo.

## Changes

- `apps/api/src/config.py` — added `arcgis_fort_collins_permits_url` setting.
- `apps/api/src/spatial/city_registry.py` — added `CityId.FORT_COLLINS`.
- `apps/api/src/spatial/cities/fort_collins.py` — new leaf module: metro
  bbox, 4 divisions, 8 submarkets, `REGISTRATION`.
- `apps/api/src/spatial/cities/data/fort_collins.yaml` — declarative
  definition wiring the `permits` feed (live-verified endpoint/schema, see
  Notes) into `REGISTRY`.
- `apps/api/src/spatial/cities/boulder.py` — docstring note reconciling the
  US-421 probe's re-flagged Boulder permits endpoint against the already-live
  US-245 registration (no functional change).
- `apps/api/src/producers/field_maps_co_dora.py` — new: field maps for CO
  DORA occupational (`7s5z-vewr`) and real-estate (`4zse-6bnw`) licenses.
- `apps/api/src/producers/co_dora_specs.py` — new: `co_dora_occupational_spec(city)`
  and `co_dora_realestate_spec(city)` leaf `DatasetSpec` builders.
- `apps/api/tests/unit/test_producers_fort_collins.py` — new: spatial
  geometry + registry wiring tests for Fort Collins.
- `apps/api/tests/unit/test_co_dora_specs.py` — new: spec-shape and
  parse-through-producer tests for both CO DORA registries.
- `apps/api/tests/unit/test_tx_southwest_superfeed_specs.py` — new: proves
  the existing generic TX TREC/TDLR/TABC spec builders construct correctly
  for every county behind the six named TX metros.
- `apps/dashboard/public/index.html` — regenerated via
  `scripts/export_dashboard.py` (adds the `fort_collins` METRO_META entry).
  This regeneration also incidentally repairs two pre-existing, unrelated
  unresolved git-merge-conflict markers (`<<<<<<< HEAD` / `>>>>>>>
  US-433-grid-legibility`) that had been checked into this generated file
  out of sync with its `src/serving/dashboard.py` source, plus a stale
  `PR_DESCRIPTION.md` left over from that same unmerged US-433 branch (this
  file). The export script is idempotent and rebuilds byte-for-byte from
  the live `REGISTRY`, so this is a straight resync, not new authored
  content.
- `apps/product/public/facts.json` and
  `apps/product/public/cities/fort_collins.json` — regenerated via
  `scripts/export_site_facts.py`.

## Testing

- `apps/api/.venv/bin/python -m pytest tests/unit/test_producers_fort_collins.py tests/unit/test_co_dora_specs.py tests/unit/test_tx_southwest_superfeed_specs.py -q` — all pass.
- `apps/api/.venv/bin/python -m pytest tests/unit -k "registry or fort_collins or boulder or co_dora or tx_southwest or tx_trec or state_license" -q` — all pass (one pre-existing, unrelated failure — `test_get_submarket_by_name_multi_city` (Rockridge ambiguous between Oakland/SF) — reproduces identically on `main`, untouched by this change).
- `python3 scripts/verify_cicd_preflight.py` (run with `PYTHONPATH=apps/api apps/api/.venv/bin/python`) — **all gates green**: interlock, dashboard↔product cross-ref, facts:check, product lint, dashboard export, ruff check.
- `scripts/export_site_facts.py --check` — `FACTS_FRESH (142 metros match REGISTRY)`.

## Notes

- **Boulder permits is already live.** The probe's cited endpoint
  (`open-data.bouldercolorado.gov/.../Construction_Permits/FeatureServer/0`)
  resolves to the ArcGIS Hub mirror of the same `Construction_Permits` table
  already registered under `boulder.py` (US-245) on the city's own AGOL org
  (`services.arcgis.com/ePKBjXrBZ2vEEgWd`) — live-verified as a non-spatial
  **Table** (`needs_geocode=True`), not the probe's claimed native point
  geometry. No change was needed or made to Boulder's registration.
- **Fort Collins permits schema does not match the probe.** The probe
  claimed fields `PERMITNUM, PERMIT_TYPE, SUB_TYPE, STATUS, APPLIED_DATE,
  ISSUED_DATE, VALUATION, FEES_PAID, CONTRACTOR_NAME, ORIGINAL_ADDRESS,
  PARCEL_NUMBER` with `ISSUED_DATE` as the watermark. The live FeatureServer
  behind the cited item id (`e0964db1f10c491a872d5d0e7dbbe13a` ->
  `services1.arcgis.com/dLpFH5mwVvxSN4OE/.../Building_Permits/FeatureServer/0`,
  live-verified 2026-09-03) is a 2,215-row "Current Building Permits" table
  with fields `PERMITNUM, PERMITTYPE, B1_APPL_STATUS, ADDRESS, ...` and
  **no date column at all** — no `APPLIED_DATE`/`ISSUED_DATE` exists.
  Geometry IS native WGS84 point (confirmed Tier 1 on that count), so the
  feed is registered with `needs_geocode=False`, but with
  `ingestion_mode="snapshot"` (`watermark_col=""`) rather than incremental,
  following the CO_LIQUOR/OR_CCB snapshot precedent (`state_license_specs.py`).
- **Colorado DORA dataset ids differ from the ticket.** `7s5z-vewr`
  (occupational licenses) is correct and live. The ticket's real-estate id
  `m4y3-x47v` 404s on `data.colorado.gov` (retired/renamed); the live current
  dataset is **`4zse-6bnw`** ("Licensed Real Estate Professionals in
  Colorado"), used instead. Neither dataset carries a county column (city
  only), so specs are city-sliced (`where: city = '<name>'`) rather than
  county-sliced, matching the CO_LIQUOR/CO_APPROVED precedent already in
  `state_license_specs.py`. Real-estate `licensefirstissuedate` is
  `MM/DD/YYYY` text with no server-side chronological ordering (same
  limitation as OR CCB), so that spec runs in snapshot mode; occupational
  `licensefirstissuedate` is ISO text and sorts correctly, so it runs
  incremental.
- **Texas super-feed "wiring"** follows this repo's existing convention: the
  county-parameterized spec builders in `tx_trec_specs.py` and
  `state_license_specs.py` already generalize over any TX county (they were
  built that way in US-397/US-372), so no new production code was needed —
  only a test suite proving each builder produces a correct, valid
  `DatasetSpec` with the right `where` clause for every county behind the
  six named metros (Lubbock=Lubbock, Corpus Christi=Nueces, Laredo=Webb,
  RGV=Cameron+Hidalgo, College Station=Brazos, Killeen=Bell).
- **CO DORA specs are LEAF, not registered**, matching every other
  state-super-feed leaf module in this repo (`tx_trec_specs.py`,
  `state_license_specs.py`): they construct valid `DatasetSpec`s and parse
  correctly through the unmodified `SLALicensesProducer`, but merging them
  into Boulder's/Fort Collins's `CityRegistration.datasets[FeedType.SLA]` is
  left as a spine decision, consistent with how every prior state-super-feed
  ticket in this repo (US-397, US-372, US-424, US-425) has landed.
