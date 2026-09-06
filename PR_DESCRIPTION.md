# US-377: Register childcare licensing starter set TX/NY/NYC/DC as SLALicenseEvent
# Move Per-City Field Maps into Leaf DatasetSpecs (Completes ADR-0001 §9.2)

## Overview

Wires the childcare licensing starter set across 9 metropolitan areas (TX, NY upstate, NYC, DC) into `REGISTRY` under `FeedType.SLA` using the existing `sla_licenses_producer` pipeline.

## Changes

1. **Leaf Specs & Field Maps (`apps/api/src/producers/`):**
   - Cleaned up and finalized [childcare_specs.py](file:///home/harlan/dev/ft/US-377-childcare-registry/apps/api/src/producers/childcare_specs.py) and [field_maps_childcare.py](file:///home/harlan/dev/ft/US-377-childcare-registry/apps/api/src/producers/field_maps_childcare.py).
   - Implemented [`normalize_status`](file:///home/harlan/dev/ft/US-377-childcare-registry/apps/api/src/producers/field_maps_childcare.py) and [`passes_care_filter`](file:///home/harlan/dev/ft/US-377-childcare-registry/apps/api/src/producers/field_maps_childcare.py).

2. **Config Declarations (`apps/api/src/config.py`):**
   - Added endpoint fields in [`Settings`](file:///home/harlan/dev/ft/US-377-childcare-registry/apps/api/src/config.py) for all 4 childcare registries (`socrata_tx_hhsc_ccl_endpoint`, `socrata_ny_ocfs_endpoint`, `socrata_nyc_dohmh_childcare_endpoint`, `arcgis_dc_child_dev_endpoint`).

3. **City Definitions (`apps/api/src/spatial/cities/data/`):**
   - **TX Metros (Austin, Dallas, Fort Worth, El Paso):** Added `tx_hhsc_ccl_spec` with respective county slices (`TRAVIS`, `DALLAS`, `TARRANT`, `EL PASO`).
   - **NY Upstate Metros (Buffalo, Rochester, Syracuse):** Added `ny_ocfs_spec` with region codes (`BRO`, `RRO`, `SRO`).
   - **NYC:** Added `NYC_DOHMH_SPEC`.
   - **Washington DC:** Added `DC_CHILD_DEV_SPEC`.

4. **Product Facts Export:**
   - Synchronized `facts.json` and city facts via `bun run facts:export`.

5. **Tests & Verification:**
   - Created [test_childcare_specs.py](file:///home/harlan/dev/ft/US-377-childcare-registry/apps/api/tests/unit/test_childcare_specs.py) covering spec construction, endpoint namespacing, and row parsing.
   - Verified that `pytest -m interlock` (35 passed) and `python3 scripts/verify_cicd_preflight.py` (all 6 gates) pass cleanly.
This PR completes **Linear Ticket US-430** and fulfills the final step of **ADR-0001 §9.2**:
- Removed all 79 obsolete per-city `field_maps_<city>.py` files from `apps/api/src/producers/`.
- Consolidated per-city field map definitions directly into declarative city YAML corpus files (`apps/api/src/spatial/cities/data/<city_id>.yaml`) and city leaf spec modules (`apps/api/src/spatial/cities/<city_id>.py`).
- Retained 12 non-city and shared helper modules in `apps/api/src/producers/` (`field_maps.py`, `field_maps_ca_licenses.py`, `field_maps_childcare.py`, `field_maps_co_dora.py`, `field_maps_counters.py`, `field_maps_energy_benchmark.py`, `field_maps_fl_cadastral.py`, `field_maps_fmcsa.py`, `field_maps_michigan_lara.py`, `field_maps_ohio_elicense.py`, `field_maps_state_licenses.py`, `field_maps_tx_trec.py`).
- Updated all 75+ `test_producers_<city>.py` unit tests and related test suites to import directly from `src.spatial.cities.<city>` instead of obsolete `src.producers.field_maps_<city>`.
- Added missing test helper constants and normalization exports to leaf city modules without circular imports.
- Patched `BaseKafkaProducer` instantiation in scheduler tests to prevent background Kafka connection timeouts during unit tests.

## Changes

### 1. Obsolete Modules Removed (79 files)
- Deleted `apps/api/src/producers/field_maps_<city>.py` for all 79 individual cities.

### 2. Retained Shared & State/National Modules (12 files)
- `apps/api/src/producers/field_maps.py`
- `apps/api/src/producers/field_maps_ca_licenses.py`
- `apps/api/src/producers/field_maps_childcare.py`
- `apps/api/src/producers/field_maps_co_dora.py`
- `apps/api/src/producers/field_maps_counters.py`
- `apps/api/src/producers/field_maps_energy_benchmark.py`
- `apps/api/src/producers/field_maps_fl_cadastral.py`
- `apps/api/src/producers/field_maps_fmcsa.py`
- `apps/api/src/producers/field_maps_michigan_lara.py`
- `apps/api/src/producers/field_maps_ohio_elicense.py`
- `apps/api/src/producers/field_maps_state_licenses.py`
- `apps/api/src/producers/field_maps_tx_trec.py`

### 3. Leaf City Spec Enhancements
- Exported required constants and mappings in `apps/api/src/spatial/cities/` for `austin.py`, `boston.py`, `el_paso.py`, `honolulu.py`, `milwaukee.py`, `phoenix.py`, `portland.py`, `san_jose.py`, and `st_louis.py`.
- Maintained clean decoupling so leaves do not import `FeedType` or `city_registry` directly.

### 4. Test Suite Rewiring & Hardening
- Rewired imports across 75+ `apps/api/tests/unit/test_producers_*.py` files.
- Rewired `test_asheville_deeds_spec.py` to `src.producers.asheville_deeds_spec`.
- Wrapped `BaseKafkaProducer` in scheduler unit tests (`test_scheduler.py`, `test_scheduler_stagger.py`, `test_scheduler_watermark_state.py`) with `unittest.mock.patch`.
- Gracefully handled absent CalEnviroScreen centroid data file in unit tests.

## Verification

1. **Producer Unit Tests:**
   ```bash
   PYTHONPATH=.:../.. .venv/bin/pytest tests/unit/test_producers_*.py
   ```
   - **3,050 passed in 9.71s**

2. **Full CI/CD Pre-flight:**
   ```bash
   python3 scripts/verify_cicd_preflight.py
   ```
   - `--- interlock gate OK`
   - `--- dashboard ↔ product cross-ref OK`
   - `--- product facts:check OK`
   - `--- product lint OK`
   - `--- dashboard export OK`
   - `--- ruff check OK`
   - `✓ CI/CD pre-flight green — all gates pass`
