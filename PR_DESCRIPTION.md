# US-437: Expand Division & Submarket Registry to Cover All 9 Bay Area Counties

## Summary

Expands the SF spatial module from **5 divisions / 41 submarkets** to **8 divisions / 83 submarkets**, achieving wall-to-wall coverage of all 9 Bay Area counties. Every county now has named submarkets and a dedicated division, eliminating the prior gaps in Napa/Sonoma, Solano, and Central/East Contra Costa.

## What changed

### 3 new divisions

| Division | Counties | Submarkets |
|---|---|---|
| `NORTH_BAY_WINE_COUNTRY` | Napa, Sonoma | Napa Downtown, Yountville, St Helena, Sonoma Plaza, Petaluma Downtown, Santa Rosa Downtown, Healdsburg |
| `SOLANO_CORRIDOR` | Solano | Vallejo Downtown, Mare Island, Benicia, Fairfield Downtown, Vacaville Downtown, Dixon |
| `OUTER_CONTRA_COSTA` | Central/East Contra Costa | Walnut Creek Downtown, Concord Downtown, Pleasant Hill, Martinez Downtown, Antioch Downtown, Pittsburg Downtown, Brentwood, San Ramon, Danville |

### Existing divisions expanded

| Division | Change |
|---|---|
| `EAST_BAY` | Added Union City (+1); Walnut Creek and Concord moved out to `OUTER_CONTRA_COSTA` |
| `PENINSULA` | Added San Carlos, Foster City, Belmont, Half Moon Bay (+4) |
| `SILICON_VALLEY_SOUTH_BAY` | Added Milpitas, Morgan Hill, Gilroy (+3) |
| `MARIN_NORTH_BAY` | Added Novato Downtown (+1) |
| `SAN_FRANCISCO_CORE` | No change (17 submarkets) |

### Files changed

- **`apps/api/src/spatial/cities/san_francisco.py`** — 8 division bboxes, 83 submarket definitions, updated `REGISTRATION`
- **`apps/api/src/spatial/cities/data/san_francisco.yaml`** — YAML mirror regenerated to match (83 submarkets, 8 divisions)
- **`apps/api/src/serving/dashboard.py`** — CSS variables, `.borough-btn`, `.borough-tag` rules, and JS normalizer cases for the 3 new divisions
- **`apps/api/tests/unit/test_submarkets.py`** — updated count assertions; fixed Walnut Creek/Concord division assertions; disambiguated Rockridge lookup; corrected Oakland-downtown city resolution
- **`apps/api/tests/unit/test_serving.py`** — updated division count and submarket count assertions
- **`apps/product/public/cities/san_francisco.json`** — regenerated via `bun run facts:export`
- **`apps/dashboard/public/index.html`** — regenerated via `python3 scripts/export_dashboard.py`

## Gate results

| Gate | Result |
|---|---|
| `pytest -m interlock` (35 tests) | ✅ PASS |
| dashboard ↔ product cross-ref | ✅ PASS |
| `bun run facts:check` | ✅ PASS |
| `bun run lint` (product site) | ✅ PASS |
| `export_dashboard.py` byte-sync | ✅ PASS |
| ruff check | ✅ PASS |
| `test_submarkets.py` (20 tests) | ✅ PASS |

`python3 scripts/verify_cicd_preflight.py` → **✓ CI/CD pre-flight green — all gates pass**

## Geographic coverage before / after

**Before:** SF Core, East Bay (Alameda + West CCC), Peninsula (San Mateo), Silicon Valley (Santa Clara), Marin — Napa, Sonoma, Solano, Central/East Contra Costa had no named submarkets.

**After:** All 9 counties have at least one division and multiple named submarkets. Coordinates anywhere in the Bay Area resolve to a local submarket within the 25 km distance cap.

## Notes

- Rockridge exists in both `oakland` and `san_francisco` registries; tests now pass `city_id="san_francisco"` to disambiguate.
- Oakland Downtown correctly resolves to `"oakland"` (pre-existing behavior documented in US-436 stream log).
- Walnut Creek and Concord test expectations updated to `OUTER_CONTRA_COSTA`.
