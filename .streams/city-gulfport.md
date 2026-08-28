# Stream log — city-gulfport — 2026-08-28

Phase-2 leaf stream for Linear US-305: Gulfport, MS metro registration.
Spine is serial after this stream; do not edit spine files here.

## Claim

- **Stream id:** `city-gulfport`
- **Leaf files I will create/edit:**
  - `.streams/city-gulfport.md` (this file)
  - `docs/research/se-probe-gulfport.md` (NEW)
  - `apps/api/src/spatial/cities/gulfport.py` (NEW)
  - `apps/api/src/producers/field_maps_gulfport.py` (NEW)
  - `apps/api/tests/unit/test_producers_gulfport.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (CityId.GULFPORT, _HANDWRITTEN_ALIASES, REGISTRY)
  - `apps/api/src/config.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html` (city registration rule)

## Intent

Leaf-complete a Gulfport, MS metro registration, following the lynchburg.py
conventions. The brief flags this as hard/Medium-Low fit, honest NOT-VIABLE is
acceptable. Live-probe first; register only feeds that are live and
queryable. Candidates: City of Gulfport GIS (ArcGIS Server/Hub, Harrison
County), Harrison County GIS/ArcGIS Hub, gulfcoast regional portals. Family
set: PERMITS, COMPLAINTS_311, SLA (business licenses / STR / seafood-marine
licenses), DEEDS (Harrison County property sales).

## Decisions

- 2026-08-28 — Orchestrator claimed Linear US-305 and dispatched this leaf
  stream. Do NOT touch Linear, git commit/push, or PRs. Do NOT touch the
  untracked apps/site/ directory. Sibling agents edit other cities in the
  same tree — touch only my five files.

## Live probe (2026-08-28)

Trust live rows, not the brief. Full evidence in
`docs/research/se-probe-gulfport.md`. **VERDICT: NOT-VIABLE.**

| Feed | Platform / endpoint | Watermark col + newest | 7d / 60d / total | Geo | Verdict |
|---|---|---|---|---|---|
| SLA | arcgis; `maps.gulfport-ms.gov/.../CityServices/GPT_BusinessLicense/MapServer/0` | `ISSUE_DATE` **2024-12-12** (1733961600000) | 0 / 0 / 510 | address + State-Plane-feet pts (wkid 2254); PII OWNER_NAME | **FROZEN — reject** |
| SLA (main-st) | arcgis; `GPT_SocialDistMainStBusLic/MapServer/0` | `ISSUE_DATE` **2024-12-12** | 0 / 0 / same | same | **FROZEN — reject** |
| PERMITS | city server | — none | — / — / 0 | — | **no layer exists** |
| COMPLAINTS_311 | — | — none | — | — | **no feed anywhere** |
| DEEDS | `GPT_StCadastral/FeatureServer/5` Parcels | — none (no sale date/amount) | — / — / 108,080 | county-wide cadaster, PII NAME/ADDRESS | **not a transactions feed** |
| "Gulfport Permits" (AGOL `58e599…`) | arcgis-AGOL; `services1.arcgis.com/UCf4GN8d89BVnHt2/.../Gulfport_Permits/FeatureServer/0` | — none (no date col) | — / — / 492 | native pts + address | **WRONG CITY — Gulfport, FLORIDA** |
| County land records | `landrecords.co.harrison.ms.us/DuProcessWebInquiry/` | — none | — | — | web-form inquiry, no REST feed |
| County CAMA | `harrisonms.geopowered.com/propertysearch/` | — none | — | — | web app, no REST feed |
| State Socrata `data.ms.gov` | socrata | host unreachable | — | — | no portal |

**Cross-city collision (critical):** the most promising AGOL hit,
`Gulfport_Permits`, is the **wrong Gulfport** — rows carry `State="Florida "`,
`Zip_Code=33707`, web apps under `pwgulfportfl.maps.arcgis.com` (the FL city's
public-works org). Gulfport, MS is Harrison County (ZIPs 39501-39507). Rejected.

## Decisions

- 2026-08-28 — Orchestrator claimed Linear US-305 and dispatched this leaf
  stream. Do NOT touch Linear, git commit/push, or PRs. Do NOT touch the
  untracked apps/site/ directory. Sibling agents edit other cities in the
  same tree — touch only my five files.
- **NOT-VIABLE verdict locked.** No registration is fabricated. The leaf city
  module, field maps, and producer test file are NOT created (they would
  falsely register a feed). Only the research/probe doc + this log are
  delivered.

## Current step

Probe complete. Documented negative evidence in research doc; probe table
recorded here. No code leaf built (no live feed to register).

## Next step

Report VERDICT **NOT-VIABLE** back to the orchestrator with the probe table
and the cross-city collision note. Do not open a spine hold — there is
nothing to register. Re-probe when the freshness triggers in the research doc
are met.
