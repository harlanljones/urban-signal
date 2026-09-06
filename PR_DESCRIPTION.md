# US-377: Register childcare licensing starter set TX/NY/NYC/DC as SLALicenseEvent

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
