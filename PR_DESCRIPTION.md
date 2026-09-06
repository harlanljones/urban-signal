# Move Per-City Field Maps into Leaf DatasetSpecs (Completes ADR-0001 §9.2)

## Summary

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
