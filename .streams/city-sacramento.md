# Stream: city-sacramento

- **Linear:** US-142
- **Status:** completed
- **Leaf ownership:** `apps/api/src/spatial/cities/sacramento.py`, `apps/api/tests/unit/test_producers_sacramento.py`
- **Spine files expected:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, producer wiring, dashboard metadata, snapshot exports, interlock tests
- **Intent:** Register Sacramento 311 and Sacramento County permits with native point geometry.
- **Claim decision:** Claimed US-142 after re-reading the open, unassigned issue and confirming no blocking relations. The latest audit comment upgrades the permit scope from the earlier address-only city layer to a native-point county layer.
- **Outcome:** Registered Sacramento 311 and Sacramento County permits as native-point ArcGIS feeds. The permit endpoint was resolved from the public ArcGIS web-map service metadata and its live schema was verified before registration.
- **Verification:** `apps/api/.venv/bin/pytest -q apps/api/tests/unit/test_producers_sacramento.py apps/api/tests/unit/test_interlock_gate.py` (26 passed); `apps/api/.venv/bin/python scripts/export_dashboard.py`; `bun run facts:check` from `apps/product` (`FACTS_FRESH`, 36 metros); `node scripts/verify-site-content.mjs`; `git diff --check`.
