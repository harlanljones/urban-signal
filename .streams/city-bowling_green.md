# Stream log — city-bowling_green — 2026-08-28

Phase-2 leaf stream for Linear US-300: Bowling Green / Warren County, KY
partial registration (PERMITS only on the city ArcGIS Server). Spine is serial
after this stream; do not edit spine files here.

## Claim

- **Stream id:** `city-bowling_green`
- **Leaf files I will create/edit:**
  - `.streams/city-bowling_green.md` (this file)
  - `docs/research/se-probe-bowling_green.md` (NEW)
  - `apps/api/src/spatial/cities/bowling_green.py` (NEW)
  - `apps/api/src/producers/field_maps_bowling_green.py` (NEW)
  - `apps/api/tests/unit/test_producers_bowling_green.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (CityId.BOWLING_GREEN, ALIASES, REGISTRY)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html` (city registration rule)

## Intent

Leaf-complete a PARTIAL Bowling Green metro on the city ArcGIS Server
`webgis.bgky.org` `CCPC/CCPC_Building_Permits_2010`: the native-point PERMITS
feed (`/5`). COMPLAINTS_311 / SLA / DEEDS are deliberately NOT registered
(partial registration allowed; `get_bowling_green_dataset` raises readable
KeyError for them). Tests pass without a registry entry. Re-probe ≤72h.

## Decisions

- 2026-08-28 — Orchestrator claimed Linear US-300 and dispatched this leaf
  stream. Only PERMITS is live and registrable. 311/SLA/DEEDS NOT-VIABLE.
- PERMITS is a **native point** layer (KY-North SP 102680, client always
  requests `outSR=4326`), so `needs_geocode=True` is **defensive only** and
  `non_spatial` is NOT set. No `state_plane_crs` needed (coords arrive as
  WGS84). No `parcel_join`.
- Watermark `created_date` (date-typed editor tracking). Host is
  **ANSI-date-literal** — document the `DATE '...'` requirement in the spine
  delta; do NOT edit `watermarks.py`.
- Field map leaves `address_street` unmapped (split `St_Number`/`St_Name`,
  no single line; native geometry carries the coordinate). No bbl/borough/zip
  candidates (SPID is a site-plan designation, not a parcel id).
- `_STATE_RE` false positive ("MT" in "MT VICTOR LANE") documented only;
  `geocoder.py` untouched. Path never taken (native coords).
- Spatial: 7 divisions, 10 submarkets (Mt Victor, Lovers Lane, Scottsville
  Rd, Nashville Rd, Bluestem Sheldrake, Three Springs Rd, Russellville Rd, KY
  Transpark, Fountain Square, WKU). Metro bbox grounded on live feed extent
  (36.79-37.19, -86.67--86.12). Self-verified containment.

## Live probe (2026-08-28, re-verified)

`https://webgis.bgky.org/server/rest/services/CCPC/CCPC_Building_Permits_2010/FeatureServer/5`.
ArcGIS Server 11.5, city-owned.

| Feed | Layer | Newest watermark | 7d / 60d / total | Geo | Verdict |
|---|---|---|---|---|---|
| PERMITS | `/5` Building Permits 2010+ | `created_date` 2026-08-24T18:06:08+00:00 (PermitNum 2026-1314, 24-unit apt @ 2633 Mt Victor Lane, OBJECTID 113479) | 22 / 386 / 29,691 | native point, outSR=4326 honored | **Tier 2 / registrable** |
| COMPLAINTS_311 | `Code_Cases/13` frozen 2023-01-31; `CCPC_Compliance_Inspections/2` = EPSC/construction compliance | n/a | n/a | n/a | **NOT-VIABLE** |
| SLA | no license register in 978-dataset org | n/a | n/a | n/a | **NOT-VIABLE** |
| DEEDS | `WARCO/Parcel_Reference` parcel snapshot; warrenpva.com unreachable; KY geoportal only Webster Co | n/a | n/a | n/a | **NOT-VIABLE** |

Host quirk re-confirmed live:
```
where=created_date >= '2026-08-20T00:00:00+00:00'  -> ArcGIS error 400
where=created_date >= DATE '2026-08-20 00:00:00'   -> count=49 (works)
```
Layer metadata re-confirmed: `objectIdField=OBJECTID`, `maxRecordCount=2000`.
Feed extent (outSR=4326): lat 36.795-37.179, lng -86.661--86.125.

## Files written

- `apps/api/src/spatial/cities/bowling_green.py`
- `apps/api/src/producers/field_maps_bowling_green.py`
- `apps/api/tests/unit/test_producers_bowling_green.py`
- `docs/research/se-probe-bowling_green.md`

## Tests

```
cd apps/api && .venv/bin/pytest tests/unit/test_producers_bowling_green.py -q
37 passed
```

No `CityId.BOWLING_GREEN`. No spine edits.

## Spine delta (do NOT apply in this stream)

Copy-paste for the serial interlock hold:

1. `CityId.BOWLING_GREEN = "bowling_green"` (server id value; add after the
   current newest member)
2. Aliases in `_HANDWRITTEN_ALIASES`:
   - `bowling_green`, `bowling green`, `bowling_green_ky`, `bowling green ky`,
     `bowling-green`, `bgky`, `warren_county_ky`, `warren county ky`
3. `city_registry.py` imports:
   - `from src.spatial.cities.bowling_green import BOWLING_GREEN_DIVISION_BBOXES, BOWLING_GREEN_DIVISIONS, BOWLING_GREEN_METRO_BBOX, BOWLING_GREEN_SUBMARKETS`
   - `from src.producers.field_maps_bowling_green import BOWLING_GREEN_PERMITS_FIELD_MAP`
4. `cities/__init__.py` export block (same four constants + `is_in_bowling_green_metro`)
5. `config.py`:
   - `arcgis_bowling_green_permits_endpoint = "https://webgis.bgky.org/server/rest/services/CCPC/CCPC_Building_Permits_2010/FeatureServer/5"`
6. `REGISTRY[CityId.BOWLING_GREEN]`:
   - name `"Bowling Green / Warren County"`, state `"KY"`
   - center `{"lat": 36.9892, "lng": -86.4436}`
   - county-scale metro bbox `{"min_lat": 36.79, "max_lat": 37.19, "min_lng": -86.67, "max_lng": -86.12}`
   - job_suffix `"bowling_green"`
   - datasets: **only** `FeedType.PERMITS` (partial). Do **not** register
     311 / SLA / DEEDS.
   - endpoint `settings.arcgis_bowling_green_permits_endpoint`
   - platform `arcgis`, watermark `created_date`, id_keys `["PermitNum","OBJECTID"]`
   - `needs_geocode=True`, `geocode_context="Bowling Green, KY"`
   - `order_by="OBJECTID"`, `oid_field="OBJECTID"`, `max_record_count=2000`
   - `expected_cadence_days=1`
   - `field_map=BOWLING_GREEN_PERMITS_FIELD_MAP`
   - do **NOT** set `non_spatial`, `parcel_join`, or `watermark_type`
     (native-point, no join, true date column)
7. `METRO_META` in `apps/api/src/serving/dashboard.py` **and** byte-synced
   `apps/dashboard/public/index.html`:
   - `bowling_green: { name: 'Bowling Green / Warren County' }`

### Host quirk the spine hold must respect

`webgis.bgky.org` requires an **ANSI date literal** in the where clause:
`created_date > DATE 'YYYY-MM-DD HH:MM:SS'` — a bare ISO comparison
(`'2026-08-24T18:06:08+00:00'`) returns ArcGIS error 400. `watermarks.py` is
unchanged (the column is a true date; no ADR-0005 declaration). If any
spine-side incremental where-clause is constructed as a bare ISO string at
this host, it must use the `DATE '...'` literal form instead.

## Current step

Leaf complete. PERMITS registered (leaf-side), 311/SLA/DEEDS absent. Tests 37
passed, no registry entry. Spine delta recorded above, not applied.

## Next step

Hand the spine delta to the orchestrator for the serial interlock hold. No
further code in this stream.
