# Stream log — west-eugene — 2026-08-28

## Claim

- **Stream id:** west-eugene
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/eugene.py`
  - `apps/api/src/producers/field_maps_eugene.py`
  - `apps/api/tests/unit/test_producers_eugene.py`
- **Spine files I expect to need:** NONE (leaf-only)

## Intent

Live-probe Eugene, OR official open-data feeds (ArcGIS Hub at mapping.eugene-or.gov + ArcGIS Server at services3.arcgis.com/F7NiRLGNbA2hh7gE), verify 1-4 official feeds (311, SLA, deeds), and build the leaf files. The ticket's candidate domain `eugene.opendata.arcgis.com` is dead (404, no domain record). The real hosts are `mapping.eugene-or.gov` (ArcGIS Hub) and `services3.arcgis.com/F7NiRLGNbA2hh7gE` (City of Eugene ArcGIS Server).

## Decisions

- 2026-08-28 — Claimed stream; copied template.
- 2026-08-28 — Live-probed eugene.opendata.arcgis.com → 404, no domain record. Ticket domain is dead. Found real hub at mapping.eugene-or.gov (DCAT feed) and ArcGIS Server at services3.arcgis.com/F7NiRLGNbA2hh7gE (300+ feature services).
- 2026-08-28 — Verified 3 official feeds:
  1. **311** — `2020_2021CampingWorkOrders` (FeatureServer/0): 10,287 rows, camp/encampment code-enforcement service requests. CreatedOn watermark (newest 2021-03-12, oldest 2017-08-17). Point geometry (native Oregon State Plane N 2914 → outSR=4326 → WGS84). ServiceCod=PDD10 (Planning & Dev code enforcement), PFI10, SFS30, etc. Title, StatusText. Companion: HistoricalCampingWorkOrders (25,171 rows, similar schema).
  2. **SLA** — `Food_Service_Establishments_Updated_VIEW_CBE` (FeatureServer/0): 752 rows, food service establishment licenses. DisplayX/DisplayY (native decimal-degree lat/lng as attributes), geometry in Web Mercator 102100. Name, Licensee, Active. No date field → snapshot mode (hasStaticData: True). Updated_VIEW suggests periodic republication.
  3. **DEEDS** — `CityLandDeeds` (FeatureServer/0): 2,873 rows, city-owned property deed records (acquisitions/dispositions). DATE_ watermark (max 1782864000000 = 2026-06-30, min -4062700800000 = 1841). Polygon geometry → centroid via outSR=4326. ACQDIS (A=acquire, D=dispose), PROP. Companions: EasementDeeds (7,340 rows, DATE_ to 2026-06-30), ROWDeeds (4,380 rows, DATE_ to 2026-01-04).
- 2026-08-28 — Lane County property records: Web portal only (LMD-PRO / citizenserviceportal), not a bulk machine-readable feed. No Socrata/ArcGIS bulk feed found. City's own deed layers (CityLandDeeds etc.) are the verifiable deed record — partial (city-owned property only), per ticket's "partial without deeds is fine".
- 2026-08-28 — Permits: No public building-permit bulk feed. City uses ebuild web portal (pdd.eugene-or.gov/ebuild, Accela-style) — no API. CIP projects (Current_Projects: 27 rows, InfrastructureProjects: 81 rows) are capital projects, not permits. Lane County has no public permit bulk feed. Permits → NOT REGISTERED.
- 2026-08-28 — All feeds: Oregon State Plane North (WKID 2914) for most feeds; ArcGIS client requests outSR=4326, server-side reprojection verified. Food_Service is in Web Mercator 102100. No mixed-CRS traps beyond the normal state-plane lifts.
- 2026-08-28 — No future-date sentinels found on CityLandDeeds DATE_ (max 2026-06-30 is reasonable). No ANSI-date-only hosts — all ArcGIS FeatureServers with esriFieldTypeDate epoch-ms.
- 2026-08-28 — All three feeds have native geometry (point or polygon → centroid); no needs_geocode needed for primary coordinate source. Address columns available as fallback.
- 2026-08-28 — Leaf files built: eugene.py (8 divisions, 15 submarkets, 3 feed specs), field_maps_eugene.py (311/SLA/deeds field maps), test_producers_eugene.py (45 tests).
- 2026-08-28 — Deed DATE_ watermark: fixtures captured newest DATE_=1767571200000 = 2026-01-05T00:00:00+00:00 (the max row stat 1782864000000 = 2026-06-30 belongs to a later row; the top-3 DESC fixtures share 2026-01-05).

## Outcome

Three official feeds verified (City of Eugene ArcGIS Server, `services3.arcgis.com/F7NiRLGNbA2hh7gE`):

| Feed | Endpoint (FeatureServer/0) | Rows | Watermark col | Newest | Geometry |
|------|---------------------------|------|---------------|--------|----------|
| COMPLAINTS_311 | `2020_2021CampingWorkOrders` | 10,287 | CreatedOn | 2021-03-12 | point (OR State Plane 2914 → WGS84) |
| SLA | `Food_Service_Establishments_Updated_VIEW_CBE` | 752 | (none — snapshot) | — | point (Web Mercator → WGS84) |
| DEEDS | `CityLandDeeds` | 2,873 | DATE_ | 2026-06-30 (max stat) | polygon → centroid |

Columns:
- 311: FID, CreatedOn, Title, WorkDescri, ServiceCod, StatusText, DateTime, GlobalID
- SLA: UID, MatchAddr, DisplayX, DisplayY, Name, Licensee, Active, ObjectId, GlobalID
- Deeds: CITYDEED, GIS_ID, ACQDIS, WIDTH, MISC, DATE_, PROP, OBJECTID_1

NOT REGISTERED: permits (ebuild Accela web portal, no bulk API), Lane County records (web-portal-only). REJECTED-with-evidence: ticket's candidate `eugene.opendata.arcgis.com` is a dead domain (404, no domain record) — never a stale mirror; the real host is mapping.eugene-or.gov / services3.arcgis.com.

Tests: `pytest tests/unit/test_producers_eugene.py -q` → 45 passed. `pytest -k eugene -q` → 47 passed. `pytest -m interlock -q` → 24 passed (one transient tmpfs-quota failure cleared on re-run; not related to leaf). `ruff check` on all three files → clean.

## Spine delta

Required for the pending spine hold (do NOT touch shared files in this leaf):

- **CityId.EUGENE** member: `EUGENE = "eugene"` (string "eugene"; note: `Eugene_Businesses_AUG2025` layer is ReferenceUSA-derived commercial locations, NOT a city license feed — do not register).
- **ALIASES** — recommended: `EUGENE = "eugene"` (add `"Eugene"` / `"eugene-or"` if alias convention supports it).
- **REGISTRY entry** — from `EUGENE_FEED_SPECS` in `src/spatial/cities/eugene.py`, three feeds:
  - `311` → topic `raw.municipal.311`, endpoint `.../2020_2021CampingWorkOrders/FeatureServer/0`, watermark CreatedOn, id_keys [FID, GlobalID], interval 300s.
  - `sla` → topic `raw.municipal.sla`, endpoint `.../Food_Service_Establishments_Updated_VIEW_CBE/FeatureServer/0`, watermark "", snapshot mode, alarm_exempt=True.
  - `deeds` → topic `raw.municipal.deeds`, endpoint `.../CityLandDeeds/FeatureServer/0`, watermark DATE_, id_keys [CITYDEED, OBJECTID_1], interval 600s.
- **Config endpoint settings**: `topic_permits` NOT needed (no permits feed). `topic_311`, `topic_sla`, `topic_deeds` already exist in `config.py` (defaults `raw.municipal.*`). No new config keys required.
- **METRO_META / dashboard** — spine-owned: register `eugene` in REGISTRY, ALIASES, METRO_META (metro chip + `?city=eugene` deep link), snapshot export coverage, res-5 grid-tile coverage, and byte-synced `apps/dashboard/public/index.html` static copy, per city-registration rule (enforced by `test_interlock_gate.py::TestDashboardWiring` / `TestSnapshotWiring`).
- **Recommended Linear comment on US-225**: ACCEPT with correction — the ticket's candidate domain `eugene.opendata.arcgis.com` does not exist (404); the live host is `mapping.eugene-or.gov` (ArcGIS Hub) backed by `services3.arcgis.com/F7NiRLGNbA2hh7gE`. Registered 3 feeds (311 camping work orders, food-service SLA snapshot, city land deeds). Permits/Lane County deeds are web-portal-only and unregistered.