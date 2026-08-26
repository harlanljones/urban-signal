# Stream log — city-tampa — 2026-08-26

## Claim

- **Stream id:** `city-tampa`
- **Leaf files I will create/edit:** `apps/api/src/spatial/cities/tampa.py`, `apps/api/src/producers/field_maps_tampa.py`, `apps/api/tests/unit/test_producers_tampa.py`, `.streams/city-tampa.md`
- **Spine files I expect to need:** `src/spatial/city_registry.py` (CityId.TAMPA member, ALIASES, REGISTRY entry, config endpoints), `src/spatial/cities/__init__.py` (import + __all__), `src/producers/field_maps.py` (central field_map entry if any), `apps/dashboard` METRO_META + `public/index.html` sync, `src/config.py` (endpoint setting). Shared producers untouched — field_map mechanism already landed in Wave B.

## Intent

Tampa registers as a ONE-feed partial city (PERMITS — City of Tampa "Single Family Permits", ArcGIS FeatureServer/32, Accela schema, point geometry, single-family-only) with a full geography module (metro bbox, 7 division bboxes, 19 submarkets, BoroughMeta catalog with exactly-one claims), a leaf `field_maps_tampa.py` (FIELD_MAP for the Accela columns), and self-contained fixture/registration tests that pass WITHOUT the spine being applied. SLA / 311 / DEEDS are deliberately absent (not verified) and `get_tampa_dataset()` raises a readable error for them.

## Decisions

- 2026-08-26 — Stream claimed; leaf-only constraint accepted (no spine edits, no git branch/commit, no Linear).
- 2026-08-26 — **DISCOVERY (no network at leaf-build time):** The ONLY Tampa feed verified in the repo research corpus is PERMITS. `docs/research/wave-2-city-candidates.md` (Tier 1 + US-78 row-level re-probe) confirms City of Tampa "Single Family Permits" = `arcgis.tampagov.net/arcgis/rest/services/OpenData/Planning/MapServer/32`, platform arcgis, `OPENED_DATE` newest 2026-07-21, `LASTUPDATE` 2026-08-22, point geometry, 1,028 rows (710 Issued), **single-family only** (Austin/LA-style partial). No SLA / 311 / DEEDS feed appears anywhere in `docs/research/*.md`, and no network access was available to confirm a Hillsborough County business-license / business-tax-receipt feed. Per the "register only what exists" rule (docs/agents/parallel-streams.md), SLA is therefore left UNREGISTERED; `get_tampa_dataset()` raises for it. **This contradicts the ticket title's "+ partial SLA"** — escalate to orchestrator: confirm a real Hillsborough business-license Socrata/ArcGIS endpoint before adding FeedType.SLA (do NOT point SLA at an unverified mirror).
- 2026-08-26 — **Field map is provisional Accela spelling.** `B1_PER_ID` / `B1_ALT_ID` come from the doc's "Accela schema: `B1_PER_ID*`" note; the remaining columns (`APPLICATION_STATUS`, `B1_WORK_FLOW`, `B1_EST_PROJ_COST`, `B1_SITE_ADDRESS`, `COUNCIL_DISTRICT`, `ZIP_CODE`) are the standard Accela names and MUST be confirmed against a live layer `describe` call at spine time. Coordinate parsing relies on ArcGISClient projecting the point geometry to latitude/longitude (no dotted field_map entry needed — matches Detroit/DC/Minneapolis permit precedent).
- 2026-08-26 — **Endpoint literal vs settings:** TAMPA_DATASETS uses the literal ArcGIS URL so the leaf imports cleanly without the spine `config.py` change. The spine REGISTRY entry should reference a new `settings.arcgis_tampa_permits_url` (see report delta). `topic` uses the existing `settings.topic_permits`.
- 2026-08-26 — Geography finalized: metro bbox 27.84–28.12 / -82.60–-82.22; 7 divisions, 19 submarkets; all nesting + exactly-one invariants asserted in-test and pass.

## Current step

Leaf complete; running leaf test + interlock gate to verify.

## Next step

Hand leaf + exact spine deltas to orchestrator for interlock (registry CityId.TAMPA + REGISTRY entry + ALIASES + __init__ import + dashboard METRO_META/index.html + config endpoint). Verify a Hillsborough SLA endpoint before adding FeedType.SLA.
