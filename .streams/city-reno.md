# Stream: city-reno

- **Linear:** US-161
- **Status:** completed
- **Leaf ownership:** `apps/api/src/spatial/cities/reno.py`, `apps/api/tests/unit/test_producers_reno.py`
- **Spine files expected:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, deeds producer wiring, dashboard metadata, snapshot exports, interlock tests
- **Intent:** Register Washoe County parcel sales as Reno's DEEDS feed; do not register stale permits, empty 311, or absent SLA feeds.
- **Claim decision:** Claimed US-161 after re-reading the open, unassigned issue and its audit comment; no blocking parent or child relation is present.
- **Outcome:** Registered Reno / Washoe County as a deeds-only ArcGIS feed using the live WashoeDataShare polygon layer. The stale permit, empty 311, and absent SLA families remain intentionally unregistered.
- **Verification:** `apps/api/.venv/bin/pytest -q apps/api/tests/unit/test_producers_reno.py apps/api/tests/unit/test_interlock_gate.py apps/api/tests/unit/test_scheduler.py apps/api/tests/unit/test_backfill_loader.py` (54 passed); `apps/api/.venv/bin/python scripts/export_site_facts.py`; `bun run facts:check` from `apps/product` (`FACTS_FRESH`, 37 metros); `node scripts/verify-site-content.mjs`; `git diff --check`.
