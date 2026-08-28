# Stream log — city-pensacola — 2026-08-28

Phase-2 leaf stream for Linear US-304: Pensacola, FL metro onboarding
(RESEARCH + CODE leaf). Brief: "GIS pages only — municipal GIS", region
Southeast, fit Medium-Low. Pensacola is expected to be hard — an honest
NOT-VIABLE re-probe with documented negative evidence is a fully acceptable
outcome. Spine is serial after this stream; do NOT edit spine files here.
Do NOT touch Linear, git commit/push, or PRs (permission-denied). Do NOT
touch the parallel sibling work.

## Claim

- **Stream id:** `city-pensacola`
- **Leaf files I will create/edit:**
  - `.streams/city-pensacola.md` (this file)
  - `docs/research/se-probe-pensacola.md` (NEW — probe findings)
  - `apps/api/src/spatial/cities/pensacola.py` (NEW — if viable)
  - `apps/api/src/producers/field_maps_pensacola.py` (NEW — if viable)
  - `apps/api/tests/unit/test_producers_pensacola.py` (NEW — if viable)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (CityId.PENSACOLA, ALIASES, REGISTRY)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html` (city registration rule)

## Intent

Live-probe Pensacola, FL (City of Pensacola / Escambia County) municipal GIS
for row-level feeds in the PERMITS / COMPLAINTS_311 / SLA / DEEDS families.
Register ONLY live, fresh, queryable feeds (watermarks fresh, queryable).
Partial registration is correct; an honest NOT-VIABLE with documented
negative evidence is acceptable. If viable, build the leaf (pensacola.py +
field_maps_pensacola.py + test_producers_pensacola.py) following lynchburg.py
conventions, self-verifying spatial invariants, with tests that pass WITHOUT
a registry entry.

## Decisions

- 2026-08-28 — Orchestrator claimed US-304 and dispatched this leaf stream.
  Live probe FIRST (trust live rows over the brief). Spine hold deferred
  until leaf + live probe land.

## Live probe (2026-08-28, all live)

Trust live rows, not the brief. Full negative evidence in
`docs/research/se-probe-pensacola.md`.

| Feed | Platform | Endpoint | Watermark col + newest | Rows | Geo | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | n/a | City: `fortisweb.cityofpensacola.com` (Fortis/Tyler TESS) — login page; County: `mgoconnect.org/cp?JID=224&PID=31` (MyGovernmentOnline SaaS) | none | — | none | login-gated UI, not a feed |
| PERMITS | arcgis | `gismaps.myescambia.com/.../AccelaMain/MapServer` — zoning/parcel/inspector-zone base only | none | — | zone polygons | base map, no permit records |
| COMPLAINTS_311 | n/a | City 311 (`/290`) → Comcate `agency.comcate.com/private-submission/create?crm_token=…` | none | — | none | private-submission web form, login-gated |
| COMPLAINTS_311 | arcgis | Escambia code-enforcement inspections = Web Map / Web App | none | — | interactive map | Web Map/App, no table |
| SLA (BTR) | n/a | City `/284/Apply-for-a-New-BTR`, `/659/Renew-an-Existing-BTR` | none | — | none | web form only |
| SLA (contractor licensing) | n/a | County → `mgoconnect.org` | none | — | none | login-gated portal |
| DEEDS | n/a | Escambia Prop Appraiser `escpa.org/CAMA/SaleSearch.aspx` | none (curl blocked, exit 92) | — | none | web form, no API |
| DEEDS | arcgis | County `Individual_Layers/parcels` FS 0 — monthly-static assessment snapshot | none — owner + assessed value | — | parcel polygons | static assessment, no sale date/price; owner PII |

## VERDICT

**NOT-VIABLE.** No live public row-level feed exists for any of the four
families from the City of Pensacola or Escambia County. Every candidate is a
login-gated application portal, an interactive Web Map/App with no queryable
table, or a static assessment/asset layer that is not records. No
fabricatable registration.

## Decisions

- 2026-08-28 — Orchestrator claimed US-304 and dispatched this leaf stream.
  Live probe FIRST (trust live rows over the brief). Spine hold deferred
  until leaf + live probe land.
- 2026-08-28 (probe complete) — **NOT-VIABLE**. Do NOT fabricate spatial
  data. No leaf `.py` files created. Research doc + stream log are the
  deliverable. Siblings untouched. `apps/api/src/spatial/cities/pensacola.py`,
  `field_maps_pensacola.py`, `test_producers_pensacola.py` are INTENTIONALLY
  NOT created.

## Evidence summary (why not viable)

- **City of Pensacola ArcGIS Hub** — `cityofpensacola-fl.opendata.arcgis.com`
  all data paths 401/404 ("private org id not accessible"); `pensacola.maps.arcgis.com`
  org has no open item inventory; only ArcGIS artifact is a Capital Improvements
  **Dashboard**, not an event table.
- **Escambia County ArcGIS Server** (`gismaps.myescambia.com`) — full service
  inventory enumerated; parcels/zoning/FLU/streets/assets/inspector-zones only.
  `AccelaMain` has no permit records. Hosted EnerGov/CountyLayer services are
  citizen-serve **base data**. `Individual_Layers/parcels` FS 0 = static monthly
  assessment snapshot (owner + `CURRMKT`; NO sale price/date; owner PII).
- **ArcGIS Online catalog search** — ~20 terms; results are coastal/reef/SDAT-PFL
  conservation + statewide parcel centroids, no PNS municipal records table.
- **No Socrata instance** — `data.escambiafl.gov`, `analytics.escambiafl.gov`,
  `data.cityofpensacola.com`, `data-escambia.opendata.arcgis.com`, etc.: 000/404.
- **Deeds** — appraiser `SaleSearch.aspx` is a web form (curl exit 92); Clerk of
  Court 403 (login/WAF). Nothing bulk/API.

## Files written

- `.streams/city-pensacola.md` (this stream log)
- `docs/research/se-probe-pensacola.md` (probe + negative evidence)

No leaf `.py` files (NOT-VIABLE). No tests to run (nothing built). No spine
edits.

## Spine delta

**NONE.** Registering nothing means no CityId enum line, no aliases, no
config.py keys, no REGISTRY entry, no METRO_META/`index.html` change. The
serial interlock hold needs no Pensacola work — a later re-probe (trigger
conditions in `se-probe-pensacola.md`) would produce a fresh delta.

## Re-probe triggers

- City/county publishes an open-data portal or ArcGIS Hub item with permit /
  service-request / license / parcel-transfer records (not base map).
- `mygovernmentonline.org` / MGO Connect exposes a documented public reporting
  API.
- Escambia Property Appraiser or Clerk of Court publishes a bulk parcel-sales
  or recorded-instrument download.

## Current step

Probe complete. VERDICT NOT-VIABLE. Research doc + stream log written. No
further code in this stream.

## Next step

Report back to orchestrator with the NOT-VIABLE verdict. Optionally add a
re-probe trigger note to orchestrator (US-304 stays open for a future city or
county open-data portal publication).
