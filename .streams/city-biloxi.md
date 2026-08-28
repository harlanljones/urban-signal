# Stream log — city-biloxi — 2026-08-28

Phase-2 leaf stream for Linear US-306: onboard Biloxi, MS as a new Urban
Signal metro area (region Southeast, fit Medium-Low). Registered feeds only
if live; Biloxi is expected hard — an honest NOT-VIABLE with documented
negative evidence is an acceptable outcome. Do NOT fabricate spatial data.
Spine is serial after this stream; do not edit spine files here.

## Claim

- **Stream id:** `city-biloxi`
- **Leaf files I will create/edit:**
  - `.streams/city-biloxi.md` (this file)
  - `docs/research/se-probe-biloxi.md` (NEW)
- **Planned leaf files NOT created — NOT-VIABLE verdict (see below):**
  - `apps/api/src/spatial/cities/biloxi.py`
  - `apps/api/src/producers/field_maps_biloxi.py`
  - `apps/api/tests/unit/test_producers_biloxi.py`
- **Spine files I expected to need (NOT edited — no registration):**
  - `apps/api/src/spatial/city_registry.py` (CityId.BILOXI, ALIASES, REGISTRY)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html` (city registration rule)

## Intent

Probe live row-level feeds for Biloxi, MS across the four families
(PERMITS / COMPLAINTS_311 / SLA / DEEDS), register ONLY live feeds (fresh
watermark, queryable), and build a leaf-complete Biloxi metro. Partial
registration is correct (Orlando registers SLA only). If nothing is live:
STOP with a documented NOT-VIABLE verdict.

## Decisions

- 2026-08-28 — Stream claimed. No prior Biloxi research doc exists.
- 2026-08-28 — Live probe complete across all candidate doors. Project
  is **NOT-VIABLE**. No feeds registered; no leaf files created. Full
  probe table and rationale in `docs/research/se-probe-biloxi.md`.

## Live probe table (2026-08-28)

Trust live rows, not the brief's "ArcGIS REST — municipal GIS, fit
Medium-Low" sketch. All four candidate doors probed (city on-prem GIS, city
AGOL org, Tyler TESS citizen portal, Cityworks, Harrison County GIS,
Harrison County AGOL, county appraisal, MS DMR, national Socrata catalog,
regional Hub open-data domains).

| Family | Platform | Endpoint | Watermark col + newest | 7d / 60d / total | Geo | Verdict |
|---|---|---|---|---|---|---|
| PERMITS | tyler | `biloxims.tylerportico.com/tess/citizen/` | none (login-walled) | — / — / — | none | **NOT VIABLE — login wall** |
| PERMITS | arcgis | `cityworks.../cw/FeatureServer/5` (Permit) | none; **0 rows** | 0/0/0 | no rows | **NOT VIABLE — empty** |
| COMPLAINTS_311 | arcgis | `cityworks.../cw/FeatureServer/1` (Request) | none; **0 rows** | 0/0/0 | no rows | **NOT VIABLE — empty** |
| COMPLAINTS_311 | arcgis | `cityworks.../cw/FeatureServer/2` (WorkOrder) | `InitiateDate` 2026-08-28 | bounded open-workorder view; 2,337 total | Web-Merc point; attribs = state-plane feet | **NOT VIABLE — public-works maintenance, not citizen 311** |
| SLA | — | no open source found | — | — | — | **NOT VIABLE** (business licenses only behind Tyler login wall) |
| DEEDS | arcgis | `geo.co.harrison.ms.us` parcels + LandRoll | none (assessment refresh only) | — | parcel polygons | **NOT VIABLE — assessment snapshot, no sale price/date/grantor** |
| DEEDS | arcgis | Harrison `CircuitClerk` folder | none | — | — | **NOT VIABLE — HTTP 499 token required** |

## Key evidence

- City on-prem `gis.biloxi.ms.us:6443` = **basemap only** (water, hydrants,
  meters, zoning, buildings, addresses, contours, wards). No permit / 311 /
  license / deed record table.
- City AGOL org (`cityofbiloxi.maps.arcgis.com`, hosted orgs
  `WJhHbwy2YfOSix5p` / `XwK5zAS8O0b6s3Tp`) = entertainment spots, parks,
  trees, 3D buildings, Go-Cup districts, golf-cart roadways. No permits/
  licenses/311/deeds.
- Tyler TESS (`biloxims.tylerportico.com`) = the city's permit system — an
  Angular SPA with "Former Employee Access" **login wall**, no public REST.
- Cityworks layers 1 (Request) and 5 (Permit) return **0 rows**; layer 2
  (WorkOrder) is live at 2,337 open maintenance work orders (EQUIPMENT
  MAINTENANCE / TRASH PICK-UP / INSTALL METER / ASPHALT REPAIR), no
  citizen-requester semantics.
- Harrison County parcels/LandRoll = **assessment snapshot** (owner, land/
  improvement values, tax districts, building count) — NO sale price, no
  sale/transfer date, no grantor/grantee.
- Harrison `CircuitClerk` folder = **HTTP 499 Token Required** (login gate;
  the actual land-records source).
- `HarrisonCADWebService` is Harrison County **TEXAS** (wkid 102738, Texas
  County Boundaries) — not Mississippi; discarded.
- MS DMR `gis.dmr.ms.gov` = shellfish/oyster harvest areas, reefs,
  tidelands, permitted leasing areas — environmental/resource layers, not a
  seafood/business-license register.
- National Socrata catalog (`api.us.socrata.com`): **0** datasets for
  "biloxi" or "gulfport" (resultSetSize 0).
- Hub/open-data domains `data.biloxi.ms.us`, `opendata.biloxi.ms.us`,
  `open.gulfport-ms.gov`, `data.gulfport-ms.gov` all **DNS-resolve fail**;
  `gis.biloxi.ms.us` times out; `co.harrison.ms.us` cert-name mismatch.

## Current step

Verdict rendered: **NOT-VIABLE**. Stream stops here per the dispatch brief.
No registration, no fabricated data.

## Next step

Report NOT-VIABLE back to the orchestrator with the probe table. No further
code in this stream. A re-probe is warranted only if the city publishes a
Socrata/ArcGIS Hub portal (<data|opendata>.biloxi.ms.us) or opens the
Cityworks Request/Permit layers / county CircuitClerk REST, none of which
is live today.
