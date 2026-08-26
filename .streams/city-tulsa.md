# Stream: city-tulsa

- **Linear:** US-158
- **Status:** implemented; Linear US-158 completed
- **Leaf ownership:** `apps/api/src/spatial/cities/tulsa.py`, `apps/api/tests/unit/test_producers_tulsa.py`
- **Spine files expected:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`, `apps/api/src/spatial/cities/__init__.py`, complaints producer wiring, dashboard metadata, snapshot exports, interlock tests
- **Intent:** Register Tulsa's Verint 311 service requests as a rolling-window-only feed; leave permits, deeds, and SLA unregistered.
- **Claim decision:** Continued the existing self-assigned US-158 claim after re-reading the open issue, latest live audit, and native relations. The issue has no relations.
- **Live contract:** `VerintCasesPublic` FeatureServer/0; `case_id` + `OBJECTID`; `case_opened`; point geometry; approximately 30-day rolling window.
- **Verification:** Tulsa contract tests, the interlock gate, generated site facts, site-content verification, and dashboard byte export all pass.
- **Leaf follow-up (this session):** Added the Boise-style per-city field-map leaf `apps/api/src/producers/field_maps_tulsa.py` exporting `FIELD_MAP`, and wired it into `tulsa.py` as the canonical `TULSA_311_SPEC` payload (leaf-only; spine untouched). The spine `city_registry.py` keeps its verbatim copy of the same spec/field_map. `pytest tests/unit/test_producers_tulsa.py` and `pytest -m interlock` both green.
- **Rolling-window handling:** Tulsa's public Verint FeatureServer is an approximately 30-day live view with no archive. Declared as data: `extra["rolling_window_days"]=30` and `extra["retention_days"]=30`, `platform="arcgis"`, `watermark_col="case_opened"`, `oid_field="OBJECTID"`. The shared `Complaints311Producer` pages ArcGIS by `OBJECTID` and watermarks on `case_opened`; no new producer archetype is required — `extra["field_map"]` (case_id/OBJECTID, case_opened, case_closed, case_status, case_type/case_reason/case_subject, case_external_ref) is the only per-city override needed; native point geometry resolves coordinates with no override.
- **Current step:** Complete.
