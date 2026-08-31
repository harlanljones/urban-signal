# Stream log — city-peoria — 2026-08-28

## Claim

- **Stream id:** `city-peoria`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/peoria.py` (new)
  - `apps/api/tests/unit/test_peoria_containment.py` (new)
  - `apps/product/public/cities/peoria.json` (new)
  - `apps/product/public/facts.json` (metros entry)
- **Spine files I expect to need:**
  - `apps/api/src/config.py` (settings entry for the deeds endpoint)
  - `apps/api/src/spatial/city_registry.py` (CityId member, ALIASES block, REGISTRY entry)
  - `apps/api/src/spatial/cities/__init__.py` (re-exports)
  - `apps/api/src/serving/dashboard.py` (METRO_META entry)
  - plus the byte-synced `apps/dashboard/public/index.html` static copy (not in the
    manifest, but gated by `TestDashboardWiring`)

## Intent

Register `CityId.peoria` (Peoria, IL) as a **partial registration — DEEDS only**,
per US-260. Done means: the interlock gate is green *and* Peoria appears on the map
(METRO_META chip + `?city=peoria` deep link, snapshot export coverage, res-5 grid
tiles, byte-synced dashboard static copy), per the city-registration rule in
AGENTS.md. No PERMITS/311/SLA feed exists for Peoria; `get_dataset()` must raise
readably for those three.

## Decisions

- 2026-08-28 — US-260's stated portal `peoria.opendata.arcgis.com` **does not exist**
  (`/data.json` → `Domain record(s) not found`). `*.opendata.arcgis.com` is a
  catch-all that returns HTTP 200 + a generic Hub shell for any subdomain, so a 200
  at the root is not evidence. Corrected the Linear issue.
- 2026-08-28 — Real DEEDS feed is on **Peoria County's** own ArcGIS server, not the
  city's: `https://gis.peoriacounty.gov/arcgis/rest/services/DP/ResidentialSales/MapServer/5`
  (`Current Year Sales`). Watermark `date_of_sale` (esriFieldTypeDate), max
  **2026-07-01**, 1,562 records, 34 fields, `supportsStatistics: true`.
- 2026-08-28 — Feed is **year-sliced** (2017→current) like Minneapolis 311, so it
  uses `endpoint_by_year`. The US-70 New Year rollover drill applies.
- 2026-08-28 — Trap: Hub search also surfaces a `City of Peoria **AZ**` business
  license layer. Wrong Peoria. Do not register it.
- 2026-08-28 — Baseline `pytest -m interlock` green before any edit: 24 passed.

- 2026-08-28 — Feed geometry **clears the Ocala bar**: `esriGeometryPoint` in Web
  Mercator (wkid 102100/3857), and `outSR=4326` returns true WGS84 lat/lng
  (verified: -89.5750, 40.7371). Not the county-plane X/Y that disqualified Ocala's
  sales layer. `arcgis_client.py` already supports "FeatureServer / **MapServer**
  layer endpoints", always requests `outSR=4326`, and lifts point geometry to
  latitude/longitude — **zero new machinery needed**.
- 2026-08-28 — Layer specifics: `objectIdField` is null in metadata but an
  `OBJECTID` (OID) field exists → set `oid_field='OBJECTID'`. `maxRecordCount` is
  **1000**, not the 16000 used by Minneapolis.
- 2026-08-28 — Sales-feed envelope sampled at lat 40.5581..40.9583,
  lng -89.9726..-89.4817. Metro bbox drawn wider (40.45..41.05, -90.05..-89.35);
  two divisions split by the Illinois River (PEORIA_CORE west, PEORIA_EAST east).
- 2026-08-28 — Leaf complete and green: `peoria.py` (190 lines) +
  `test_producers_peoria.py`, 9 passed. Includes a regression test that Peoria, AZ
  (33.58, -112.24) does **not** read as in-metro.

- 2026-08-28 — Field semantics verified against live records before mapping:
  `Name` is the 10-digit parcel PIN (→ `bbl`), `document_number` the deed id
  (→ `doc_id`), `PropClass` e.g. "Single-Fam" (→ `doc_type`), `prop_street` the
  address. **`total_assessed_value` is the assessor's value, not a sale price** —
  the feed publishes no consideration amount, so `document_amount` is left
  unmapped rather than carrying a number that would read as a price.
- 2026-08-28 — **Spine hold complete, gate green: 24 passed** (same 24 as baseline;
  deselected 3751 → 3762 with the new leaf tests). Spine edits made:
  `config.py` (`arcgis_peoria_deeds_url`), `city_registry.py` (import, `CityId.PEORIA`,
  3 aliases, DEEDS-only registration with `endpoint_by_year` 2017-2021),
  `cities/__init__.py` (re-exports + `__all__`), `serving/dashboard.py` (METRO_META).
- 2026-08-28 — Dashboard byte-sync regenerated via `scripts/export_dashboard.py`
  (121,743 bytes); `scripts/export_site_facts.py` → `SITE_FACTS_OK (102 metros)`,
  creating `apps/product/public/cities/peoria.json`. Both are registry-derived, not
  hand-edited.
- 2026-08-28 — Verified partial registration behaves: `get_dataset(PEORIA, DEEDS)`
  resolves; PERMITS/311/SLA each raise
  `"City 'peoria' has no '<feed>' feed registered (available: deeds)"`.
- 2026-08-28 — Ruff: new files clean; edited spine files unchanged from baseline
  (60/11/12/0 errors before and after), so no new lint introduced.

## Current step

Full `pytest` suite running to confirm nothing else regressed.

## Next step

If the suite is clean, commit leaf + spine together on a branch. Nothing is pushed:
this machine has no GitHub credentials (`gh auth status` → not logged in), so the
PR is a human step. US-260 remains the only Midwest metro with a verified live
feed — see the triage notes on US-252..US-262.

## 2026-08-30 — Post-US-427 adaptation

US-427 now derives METRO_META from REGISTRY via `_metro_meta_js()` — no manual
`dashboard.py` edit needed. After spine registration, `scripts/export_dashboard.py`
regenerates `apps/dashboard/public/index.html` (byte-sync) and `cd apps/product && bun run facts:export`
regenerates `facts.json` + `peoria.json`. Verified interlock + preflight green.
