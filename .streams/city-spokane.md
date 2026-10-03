# Stream: city-spokane

- **Linear:** US-160
- **Status:** implemented; Linear US-160 completed
- **Leaf ownership:** `apps/api/src/spatial/cities/spokane.py`, `apps/api/tests/unit/test_producers_spokane.py`
- **Spine files expected:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, deeds/permit/SLA producer wiring, XLS client if needed, dashboard metadata, snapshot exports, interlock tests
- **Intent:** Register Spokane County DEEDS, GISspokane building/planning permits, and Washington LCB Spokane renewals; leave 311 unregistered.
- **Claim decision:** Claimed US-160 after re-reading the open, unassigned issue, its latest audit, and native relations. The issue has no relations.
- **Current step:** Complete.
- **Licences moved (2026-10-03):** the data.wa.gov renewal set (`9dee-kzm5`) was last updated 2026-04-04 and its spec took the designated signee, a person, as each premises' name. The feed now reads the LCB's weekly On-Premise workbook, City of Spokane rows only, geocoding each premises address (`.streams/replace-stopped-feeds.md`).
