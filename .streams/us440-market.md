# Stream log — us440-market — 2026-09-13

## Claim

- **Stream id:** `us440-market`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/bay_area_zips.py` (new)
  - `apps/api/src/producers/redfin_client.py` (new)
  - `apps/api/src/spatial/zcta_boundaries.py` (new)
  - `apps/api/src/spatial/zip_h3_join.py` (new)
  - `apps/api/src/features/market_reconciliation.py` (new)
  - `apps/api/src/spatial/series_registry.py` (edit — add Redfin cross-ref note,
    no schema change)
  - `apps/api/tests/unit/test_redfin_client.py` (new)
  - `apps/api/tests/unit/test_zcta_boundaries.py` (new)
  - `apps/api/tests/unit/test_zip_h3_join.py` (new)
  - `apps/api/tests/unit/test_market_reconciliation.py` (new)
- **Spine files I expect to need:** none. Bay Area is already registered as
  `san_francisco` in `city_registry.py` (US-437 gave it 8 divisions / 83
  submarkets across all 9 counties) — no new city registration needed. Zillow
  ZORI/ZHVI are already declared in `series_registry.py`, which is not on the
  spine manifest. No scheduler wiring is required by the acceptance criteria
  (they ask for the ingest + join + reconciliation pipeline and its tests, not
  a new cron job).

## Intent

Redfin ZIP-tracker ingestion (new, gzipped TSV from the public S3 bucket,
filtered to Bay Area ZIP prefixes) + the ZIP-to-H3 res-9 area-weighted join
(ZCTA polygons from Census TIGERweb, intensive vars area-weighted, extensive
vars proportionally allocated) + Redfin/Zillow signal reconciliation with
configurable precedence weights, producing a monthly per-hex time series.
Done = all four new leaf modules exist, are unit-tested (single-ZIP hex,
multi-ZIP hex, missing-data fallback), `pytest -m interlock` still green
(untouched, but verify no regression), and PR_DESCRIPTION.md is written.

## Decisions

- 2026-09-13 — Confirmed via `grep`/`view` that no Redfin infra exists yet
  (ticket's "existing Redfin feed infrastructure" premise doesn't hold in this
  tree); building fresh, mirroring `series_client.py`/`series_registry.py`
  conventions but as a dedicated module since Redfin's gzipped multi-metric
  TSV shape doesn't fit `SeriesSpec` (one value column per spec).
- 2026-09-13 — Zillow ZORI/ZHVI are already registered in `series_registry.py`
  (`zori_zip`, `zhvi_zip`) per US-363. Nothing wires `SeriesClient` output into
  a scheduled job yet; out of scope for this ticket's acceptance criteria (no
  scheduler edit required).
- 2026-09-13 — ZCTA polygons: TIGERweb ArcGIS REST
  (`tigerWMS_Current/MapServer/2`, "2020 Census ZIP Code Tabulation Areas")
  returns full polygon GeoJSON per ZCTA with a plain `f=geojson` GET — no
  geopandas/fiona/pyshp dependency needed (verified live). Reuses
  `create_shapely_polygon`/`h3.cell_to_boundary` conventions from
  `geo_utils.py`. Reprojects to EPSG:3310 (CA Albers equal-area) via `pyproj`
  (already a dependency) for accurate area-ratio math.
- 2026-09-13 — `uv sync --frozen --extra dev` needed before `pytest` resolves;
  confirmed 2 pre-existing failures in `test_series_client.py` unrelated to
  this ticket (registry/CBSA drift) — not touching those.

- 2026-09-13 — Deviated from the ticket's literal Bay Area ZIP-prefix list:
  added `942` and, materially, `946` (Oakland/Alameda) to
  `BAY_AREA_ZIP_PREFIXES`. The ticket's list omits 946xx, which would silently
  drop Oakland (already a registered submarket, "Oakland Downtown", in
  `cities/san_francisco.py`) from "all Bay Area ZIPs" ingestion. Documented in
  the module docstring and PR_DESCRIPTION.md.
- 2026-09-13 — Ruff (`BLE001`/`S112`) flagged the broad `except Exception` in
  `zip_h3_join.py`/`zcta_boundaries.py` used to skip one bad ZCTA geometry
  without killing the whole join; matched the existing repo convention
  (`# noqa: BLE001 — <reason>`, seen in `geocoder.py`/`scheduler.py`) rather
  than narrowing the except, since the failure modes are third-party
  (shapely/h3) exceptions with no single common base type.

## Current step

Done. All 4 new test files pass (50 tests), `pytest -m interlock` green (35
tests, untouched — no spine files edited), `ruff check` clean on all new/
edited files, and the full `scripts/verify_cicd_preflight.py` gate is green
end-to-end (interlock, dashboard↔product cross-ref, product facts:check,
product lint, dashboard export, ruff). PR_DESCRIPTION.md written at repo
root. Confirmed the 2 pre-existing `test_series_client.py` failures
(CBSA/registry drift) and the e2e lightgbm segfault (`test_pipeline_e2e.py`)
reproduce identically on a clean stash of this branch — both unrelated to
this change, not touched.

## Next step

None — ready for human review. Leaving all work uncommitted per the no-git
rule.
