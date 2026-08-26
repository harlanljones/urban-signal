# Stream log — city-tampa — 2026-08-26

## Claim

- **Stream id:** `city-tampa`
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/tampa.py`, `apps/api/src/producers/field_maps_tampa.py`, `apps/api/tests/unit/test_producers_tampa.py`, `.streams/city-tampa.md`
- **Spine files I expect to need:** `src/spatial/city_registry.py` (CityId.TAMPA member, ALIASES, REGISTRY entry, config endpoints), `src/spatial/cities/__init__.py` (import + __all__), `src/producers/field_maps.py` (central field_map entry if any), `apps/dashboard` METRO_META + `public/index.html` sync, `src/config.py` (endpoint setting). Shared producers untouched — field_map mechanism already landed in Wave B.

## Intent

Tampa registers as a partial city with full permits plus partial alcohol-beverage SLA coverage. The permits layer is the City of Tampa `Planning/PermitsAll/FeatureServer/0` point feed, using `RECORD_ID` and the edit-stamp `LASTUPDATE`; the SLA layer is `Planning/AlcoholBeverage/FeatureServer/0`, using `ORD_PERMIT`/`APP_NUM` and `HISTORY_ACT_DT`. 311 is token-gated and no usable deeds feed was found. The geography module has 7 divisions and 19 submarkets with exactly-one claims, and the leaf tests remain self-contained.

## Decisions

- 2026-08-26 — Stream claimed; registration work completed in the orchestrator hold and tracked in Linear US-146.
- 2026-08-26 — **Live audit upgraded the feed scope.** `Planning/PermitsAll/FeatureServer/0` is a 2,606-row full permits point layer with `RECORD_ID`, `PROJECTSTATUS`, and date field `LASTUPDATE` (newest audited value 2026-08-24). `Planning/AlcoholBeverage/FeatureServer/0` is a 4,095-row point action-history layer with `ORD_PERMIT`, `APP_NUM`, `HISTORY_ACTION`, and `HISTORY_ACT_DT` (newest audited value 2026-08-24), supporting a partial SLA signal. 311 is token-gated and no usable deeds feed was found.
- 2026-08-26 — **Field maps use live ArcGIS names.** Permit fields map `RECORD_ID`, `LASTUPDATE`, `PROJECTSTATUS`, `RECORDTYPE`, `ADDRESS`, `ZIP`, and `NBROFUNITS`; SLA fields map `ORD_PERMIT`/`APP_NUM`, `ABSALETYPE`, `BUS_NAME`, `HISTORY_ACT_DT`, `HISTORY_ACTION`, `PERMIT_ADDR`, and `PERMIT_ZIP`. Coordinates come from ArcGIS point geometry flattened by `ArcGISClient`.
- 2026-08-26 — **Endpoint literal vs settings:** TAMPA_DATASETS uses the literal ArcGIS URL so the leaf imports cleanly without the spine `config.py` change. The spine REGISTRY entry should reference a new `settings.arcgis_tampa_permits_url` (see report delta). `topic` uses the existing `settings.topic_permits`.
- 2026-08-26 — Geography finalized: metro bbox 27.84–28.12 / -82.60–-82.22; 7 divisions, 19 submarkets; all nesting + exactly-one invariants asserted in-test and pass.

## Validation

- Leaf producer and registration tests pass.
- Registry, dashboard, snapshot, and static-copy wiring are complete.
- `pytest -m interlock` passes from the repository root.
- Facts export, product build, freshness, and site-content verification are green; Linear US-146 is resolved.
