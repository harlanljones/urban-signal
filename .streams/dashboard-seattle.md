# Integration Spec — Add "Seattle Metro" to `src/serving/dashboard.py`

**Stream:** dashboard-seattle · **Status:** ready-for-integrator
**Sibling spec:** `.streams/dashboard-los_angeles.md` (LA stream) — both specs edit the SAME
shared file `src/serving/dashboard.py`. Integrator applies both, resolving trivially: all
insertions are additive lines at distinct anchor points; neither spec rewrites existing lines
except the two explicitly marked REPLACEMENT lines in §5 and §7.

All source values below were read from:
- `src/spatial/cities/seattle.py` — `SEATTLE_METRO_BBOX` (L13-18), `SEATTLE_DIVISION_BBOXES` (L21-26), `SEATTLE_DIVISIONS` BoroughMeta (L364-401).
- `src/spatial/city_registry.py` — `CityId.SEATTLE = "seattle"` (L54), registration center lat 47.6062 / lng -122.3321 (L324-332).
- `src/serving/dashboard.py` — line refs are to the pre-edit file; if LA is applied first, all anchors still match because LA's edits are also additive.

Verified with Python before writing this spec:
1. Every preset lat/lng lies inside its division bbox (`ALL` inside `SEATTLE_METRO_BBOX`). All True.
2. Guard box `SEATTLE_METRO_BBOX` contains all four division boxes. True.
3. The four source boxes are NOT pairwise disjoint: `SEATTLE_CORE × SOUTH_KING` overlap on
   lat [47.580, 47.590] × lng [-122.370, -122.290]; `EASTSIDE × SOUTH_KING` overlap on
   lat [47.500, 47.590] × lng [-122.260, -122.150]. `SEATTLE_CORE × NORTH_KING` touch only at
   the boundary line lat = 47.645. Ladder order therefore matters — see §4.
4. Ladder order `NORTH_KING → EASTSIDE → SOUTH_KING → (fallback SEATTLE_CORE)` maps all 20
   submarket points from `SEATTLE_SUBMARKETS` to their own declared borough. Zero mismatches.
5. A uniform random sample of metro-guard points shows ~27% fall in NO division box (Puget
   Sound / Elliott Bay water). Therefore SEATTLE_CORE must be an explicit catch-all return,
   exactly as SF ends its ladder with `return 'SAN_FRANCISCO_CORE'` and NYC with
   `return 'Manhattan'`. Do NOT try to enumerate CORE's rectangle as the last check.

---

## 1. City `<option>` (dashboard.py L1060-1063)

Insert one line after the chicago option (L1062), keeping the sibling emoji style:

```html
          <option value="seattle">🌲 Seattle Metro (4 Divisions)</option>
```

Resulting block:

```html
        <select id="city-select" class="city-select-dropdown" aria-label="Select Metropolitan Region" onchange="changeCity(this.value)">
          <option value="san_francisco" selected>🌉 San Francisco Bay Area (5 Divisions)</option>
          <option value="nyc">🗽 NYC (5 Boroughs)</option>
          <option value="chicago">🏙️ Chicago (6 Divisions)</option>
          <option value="seattle">🌲 Seattle Metro (4 Divisions)</option>
        </select>
```

---

## 2. `CITY_CONFIGS.seattle` entry (object starts L1183)

Insert after the closing `}` of the `san_francisco:` entry (L1262), before the `};` at L1263.
Keys spelled EXACTLY as in `SEATTLE_DIVISION_BBOXES`: `SEATTLE_CORE`, `NORTH_KING`, `EASTSIDE`, `SOUTH_KING`.

```js
      seattle: {
        center: [-122.3321, 47.6062],
        zoom: 10.4,
        pitch: 48,
        bearing: -10,
        name: 'Seattle Metro',
        allLabel: 'All Seattle',
        divisions: [
          { key: 'ALL', label: 'All Seattle', class: 'ALL' },
          { key: 'SEATTLE_CORE', label: 'Seattle Core', class: 'SeattleCore' },
          { key: 'NORTH_KING', label: 'North King', class: 'NorthKing' },
          { key: 'EASTSIDE', label: 'Eastside', class: 'Eastside' },
          { key: 'SOUTH_KING', label: 'South King', class: 'SouthKing' }
        ],
        presets: {
          'ALL': { lat: 47.6062, lng: -122.3321, zoom: 10.0, pitch: 45, bearing: -10 },
          'SEATTLE_CORE': { lat: 47.6120, lng: -122.3300, zoom: 12.5, pitch: 52, bearing: -12 },
          'NORTH_KING': { lat: 47.6950, lng: -122.3530, zoom: 12.0, pitch: 48, bearing: -10 },
          'EASTSIDE': { lat: 47.6350, lng: -122.1350, zoom: 11.5, pitch: 45, bearing: -10 },
          'SOUTH_KING': { lat: 47.4400, lng: -122.2850, zoom: 11.5, pitch: 45, bearing: -10 }
        }
      },
```

Value provenance (do not alter):
- `center` = registry center for CityId.SEATTLE (city_registry.py L324+): [-122.3321, 47.6062] in MapLibre [lng, lat] order.
- Preset lat/lng = each `BoroughMeta` `center_lat`/`center_lng` verbatim (seattle.py L367-368, L376-377, L385-386, L394-395). Zooms = each meta's `zoom` verbatim: CORE 12.5, NORTH_KING 12.0, EASTSIDE 11.5, SOUTH_KING 11.5 — EASTSIDE is geographically largest so it gets the lowest zoom; all within the required 11.5–13.0 band.
- Config zoom 10.4 covers the full King County guard box (lat span 0.50°); within required 10.0–10.8. Pitch 48 / bearing -10 match chicago/sf siblings; core preset uses the sibling "downtown" accent pitch 52 / bearing -12.
- Preset keys are the canonical division keys because `jumpToBorough()` (L1550-1553) looks up `cfg.presets[normalizeBorough(b)]`; normalizeBorough output for Seattle is defined in §3.
- OPTIONAL parity extra (SF has these at L1256-1260): human-label alias presets `'Seattle Core'/'North King'/'Eastside'/'South King'` duplicating the four entries above. Not required — §3 aliases already canonicalize those labels. Skip unless the integrator wants strict SF parity.

No short-alias line needed (cf. `CITY_CONFIGS.sf = CITY_CONFIGS.san_francisco;` at L1264) — the UI only ever submits `value="seattle"`.

---

## 3. `normalizeBorough` additions (function L1429-1454)

### 3a. No-filter default

Inside the `if (!b) {...}` block, after line 1432 (`if (currentCity === 'chicago') return 'Central / Downtown';`) and BEFORE the final `return 'Manhattan';` (L1433), insert:

```js
        if (currentCity === 'seattle') return 'SEATTLE_CORE';
```

### 3b. Collapsed-upper alias mappings

After line 1452 (the `MARINNORTHBAY` rule) and BEFORE `return clean;` (L1453), insert:

```js
      if (upper === 'SEATTLECORE') return 'SEATTLE_CORE';
      if (upper === 'NORTHKING') return 'NORTH_KING';
      if (upper === 'EASTSIDE') return 'EASTSIDE';
      if (upper === 'SOUTHKING') return 'SOUTH_KING';
```

Notes:
- `upper` here is `clean.toUpperCase().replace(/[\s\-_/]+/g, '')` (L1436), so `'Seattle Core'`, `'seattle-core'`, `'SEATTLE_CORE'` all collapse to `SEATTLECORE`.
- `'EASTSIDE' → 'EASTSIDE'` is an identity mapping kept for explicitness/symmetry with siblings.
- **EASTSIDE collision analysis (vs LA spec):** LA uses key `EASTSIDE_SGV` with collapsed alias `EASTSIDESGV` (LA spec §3). Seattle's collapsed token is `EASTSIDE`. The strings are distinct (`EASTSIDE` ≠ `EASTSIDESGV`), so the two alias tables do not collide and BOTH may be inserted into the same function in any order. Residual ambiguity: a user typing plain "Eastside" while viewing Los Angeles normalizes to `EASTSIDE`, which is not an LA division key — same failure mode as any unknown string today (falls through to `return clean;`, no tab matches). Harmless; no disambiguation possible without city-scoped alias tables, which is out of scope.

---

## 4. `getBoroughNameByCoords` additions (function L2477-2495)

### 4a. No-coordinate default

Inside `if (!lat || !lng) { ... }` (L2478-2482), after L2480 (`if (currentCity === 'chicago') return 'Central / Downtown';`) and before `return 'Manhattan';` (L2481), insert:

```js
        if (currentCity === 'seattle') return 'SEATTLE_CORE';
```

### 4b. Bbox ladder

Guard box values copied EXACTLY from `SEATTLE_METRO_BBOX` (seattle.py L13-18):
min_lat 47.28, max_lat 47.78, min_lng -122.43, max_lng -122.00.
Division rectangles copied EXACTLY from `SEATTLE_DIVISION_BBOXES` (seattle.py L22-25).

Insert a self-contained, city-scoped block AFTER the no-coordinate default block (after L2482)
and BEFORE the SF coarse box at L2483 (`if (lat >= 37.0 && ...)`) :

```js
      if (currentCity === 'seattle') {
        // SEATTLE_METRO_BBOX guard (seattle.py): min_lat 47.28 max_lat 47.78 min_lng -122.43 max_lng -122.00
        if (lat >= 47.28 && lat <= 47.78 && lng >= -122.43 && lng <= -122.00) {
          if (lat >= 47.645 && lat <= 47.745 && lng >= -122.425 && lng <= -122.280) return 'NORTH_KING';
          if (lat >= 47.500 && lat <= 47.770 && lng >= -122.260 && lng <= -122.010) return 'EASTSIDE';
          if (lat >= 47.290 && lat <= 47.590 && lng >= -122.420 && lng <= -122.150) return 'SOUTH_KING';
        }
        return 'SEATTLE_CORE';
      }
```

Order justification (required reading for the integrator — do NOT reorder):
1. Source boxes genuinely overlap in two places (verified numerically):
   - `SEATTLE_CORE × SOUTH_KING`: lat [47.580, 47.590] × lng [-122.370, -122.290].
   - `EASTSIDE × SOUTH_KING`: lat [47.500, 47.590] × lng [-122.260, -122.150].
   `SEATTLE_CORE × NORTH_KING` touch only at the measure-zero line lat = 47.645;
   `NORTH_KING × EASTSIDE` and `NORTH_KING × SOUTH_KING` are disjoint by ≥0.02° gaps.
2. `NORTH_KING` first: uncontested, northernmost band.
3. `EASTSIDE` before `SOUTH_KING`: their overlap strip (Newcastle/Factoria/Renton-north corridor, e.g. 47.53,-122.19) belongs to the Eastside — Factoria is a Bellevue district; EASTSIDE wins ties.
4. `SOUTH_KING` third: takes the `CORE × SOUTH_KING` strip (lat 47.580–47.590, the Duwamish/SODO-edge band). Safe because every SEATTLE_CORE submarket sits strictly north of it (southernmost CORE submarket: Pioneer Square at lat 47.5995 > 47.590), while SOUTH_KING's bbox was deliberately drawn up to 47.590 toward its Beacon Hill/Georgetown submarkets. Verified: this order assigns all 20 submarket points to their declared borough with zero mismatches, and no submarket point of any division falls inside another division's box.
5. `SEATTLE_CORE` as catch-all `return` (not an enumerated rectangle): ~27% of random metro-guard points are open water (Puget Sound/Elliott Bay) inside the guard but in NO division rectangle; siblings handle the identical situation by ending on the core division (`return 'SAN_FRANCISCO_CORE'` L2488, `return 'Manhattan'` L2494). Enumerating CORE's rectangle instead would make those clicks fall through into the NYC ladder below and wrongly return `'Manhattan'`.
6. Wrapping in `if (currentCity === 'seattle') { ... }` guarantees Seattle coordinates can never leak into the SF/NYC checks that follow (the sibling ladders are not city-guarded; NYC boxes end with unconditional `return 'Manhattan'`, which would be wrong for out-of-guard Seattle panes, e.g. Tacoma).

---

## 5. `detectUserDefaultCity` + geolocation auto-detection

Auto-detection exists and is nearest-center based: `detectUserDefaultCity` (L1352-1396) reads
sessionStorage, then via `navigator.geolocation` calls `findClosestCity(lat, lng)` (L1334-1350),
which haversine-compares against a hardcoded `cityCoordinates` table using helper
`haversineDistance` (L1323-1332). Two exact edits:

### 5a. Saved-city whitelist — REPLACEMENT of L1355

Replace:

```js
        if (saved && (saved === 'san_francisco' || saved === 'chicago' || saved === 'nyc')) {
```

with:

```js
        if (saved && (saved === 'san_francisco' || saved === 'chicago' || saved === 'nyc' || saved === 'seattle')) {
```

### 5b. Nearest-center table — insert into `findClosestCity` `cityCoordinates` (L1335-1339)

After the `'chicago'` entry (L1337):

```js
        'seattle': { lat: 47.6062, lng: -122.3321 },
```

(Registry center for CityId.SEATTLE.) `haversineDistance` and the loop are generic — no other change needed. Note: adding seattle to this table changes nearest-city outcomes only for users physically closer to 47.6062,-122.3321 than to the existing three centers — i.e., the Pacific Northwest; intended behavior.

The several `try { sessionStorage.setItem('urban_dev_user_city', 'san_francisco'); } catch (e) {}` fallbacks (L1361, L1370, L1390) stay as-is: they are generic "no geolocation / denied / timeout" defaults shared by all cities.

---

## 6. CSS active-color rules (insert after L351)

Uses ONLY variables already defined in `:root`. Chosen vars (all confirmed present):

| Class | Division | Variable | Value | :root line |
|---|---|---|---|---|
| `.SeattleCore` | SEATTLE_CORE | `--accent-primary` | #38bdf8 | L60 |
| `.NorthKing` | NORTH_KING | `--accent-success` | #34d399 | L62 |
| `.Eastside` | EASTSIDE | `--accent-purple` | #c084fc | L68 |
| `.SouthKing` | SOUTH_KING | `--accent-warning` | #fbbf24 | L64 |

Each selector lists BOTH the PascalCase tab class (from §2 `divisions[].class`) and the raw
SCREAMING_SNAKE key, mirroring the SF pattern at L347-351 (tabs render `class="borough-btn ${d.class}"`,
while `getBoroughClass()` L1456-1458 derives the collapsed key form for tag elements).

```css
    .borough-btn.active.SeattleCore, .borough-btn.active.SEATTLE_CORE { color: var(--accent-primary); }
    .borough-btn.active.NorthKing, .borough-btn.active.NORTH_KING { color: var(--accent-success); }
    .borough-btn.active.Eastside, .borough-btn.active.EASTSIDE { color: var(--accent-purple); }
    .borough-btn.active.SouthKing, .borough-btn.active.SOUTH_KING { color: var(--accent-warning); }
```

Reuse notes:
- Cross-city hex reuse is the established norm: `--accent-primary` (#38bdf8) is byte-identical to `--division-sf-core` and `--borough-manhattan`; `--accent-success` == `--division-east-bay` == `--borough-brooklyn`; etc. Reusing accents for Seattle follows suit and avoids touching `:root`.
- DO NOT copy Chicago's variable names `--accent-emerald` / `--amber` style tokens: the existing Chicago/Southwest rules reference `var(--accent-emerald)`, `var(--accent-amber)`, `var(--accent-crimson)` (L342-344, L682-684), but NONE of those variables are defined in `:root` (pre-existing bug — they silently resolve to nothing). This spec deliberately avoids them.
- `--accent-danger` (#f43f5e) was left unused; four divisions need four colors and danger-red reads as an error state. Swap `--accent-danger` in for `--accent-warning` on SouthKing if red is preferred.

---

## 7. Full audit of per-city hardcoding (grep `san_francisco|chicago|nyc` over dashboard.py)

| Lines | What it is | Action for seattle |
|---|---|---|
| 77-81 | `:root --division-*` vars (SF-only palette) | no change needed — §6 reuses `--accent-*` |
| 336-340 | `.borough-btn.active.<NYC class>` color rules | no change needed (NYC) |
| 341-346 | `.borough-btn.active.<Chicago class>` rules (reference UNDEFINED vars) | no change needed (Chicago; see §6 warning) |
| 347-351 | `.borough-btn.active.<SF class>` rules | no change needed (SF); Seattle rules appended after L351 — §6 |
| 676-680 | `.borough-tag.<NYC class>` rules | no change needed (NYC) |
| 681-686 | `.borough-tag.<Chicago class>` rules | no change needed (Chicago) |
| 687-691 | `.borough-tag.<SF class>` rules | RECOMMENDED addition after L691 (same vars as §6): see snippet below |
| 1060-1062 | `<option>` list | ADD option — §1 |
| 1183-1263 | `CITY_CONFIGS` entries | ADD seattle entry — §2 |
| 1264 | `CITY_CONFIGS.sf` short alias | no change needed (UI never sends `sea`; registry aliases like `king_county` are backend-only, not wired to the select) |
| 1266 | `let currentCity = 'san_francisco'` initial value | no change needed (generic default, overwritten by detectUserDefaultCity at L1509-1513) |
| 1323-1332 | `haversineDistance` helper | no change needed (generic) |
| 1335-1339 | `findClosestCity` `cityCoordinates` table | ADD seattle — §5b |
| 1340 | `let closest = 'san_francisco'` fallback | no change needed (generic) |
| 1355 | sessionStorage whitelist | REPLACE line — §5a |
| 1361, 1370-1371, 1390-1391 | geolocation-failure fallbacks writing `'san_francisco'` | no change needed (generic across cities) |
| 1431-1433 | `normalizeBorough` no-filter defaults | ADD seattle line — §3a |
| 1442-1452 | `normalizeBorough` collapsed aliases | ADD seattle aliases — §3b |
| 1471-1472 | `changeCity` `'sf'` → `'san_francisco'` normalization | no change needed |
| 1477, 1463, 1552 | `CITY_CONFIGS[currentCity] \|\| CITY_CONFIGS.nyc` guards | no change needed once §2 lands (guard only fires for unknown cities) |
| 1493-1505 | `loadSubmarkets()` fetches `/api/v1/submarkets?city_id=${currentCity}` | no change needed — backend registry already registers seattle (city_registry.py L54, L324-332) |
| 1510-1512 | DOMContentLoaded fallback `currentCity = 'san_francisco'` | no change needed (generic) |
| 1629 | `CITY_CONFIGS[currentCity] \|\| CITY_CONFIGS.san_francisco` guard | no change needed (same as above) |
| 2478-2482 | `getBoroughNameByCoords` no-coord defaults | ADD seattle line — §4a |
| 2483-2494 | SF/NYC coordinate ladder | no change needed to existing lines; INSERT seattle block before them — §4b |

Recommended `.borough-tag` additions (insert after L691, mirrors L687-691 pattern; tags render
division chips elsewhere in the UI — without them Seattle chips inherit default text color):

```css
    .borough-tag.SeattleCore, .borough-tag.SEATTLE_CORE { color: var(--accent-primary); }
    .borough-tag.NorthKing, .borough-tag.NORTH_KING { color: var(--accent-success); }
    .borough-tag.Eastside, .borough-tag.EASTSIDE { color: var(--accent-purple); }
    .borough-tag.SouthKing, .borough-tag.SOUTH_KING { color: var(--accent-warning); }
```

---

## Verification summary (performed before this spec was written)

- Division keys cross-checked character-by-character against `SEATTLE_DIVISION_BBOXES`
  (seattle.py L21-26): `SEATTLE_CORE`, `NORTH_KING`, `EASTSIDE`, `SOUTH_KING`. ✔
- Every §2 preset lat/lng inside its own division bbox; `ALL` inside `SEATTLE_METRO_BBOX`. ✔
- §4 guard literals equal `SEATTLE_METRO_BBOX` exactly (47.28 / 47.78 / -122.43 / -122.00). ✔
- Overlap analysis and ladder-order proof: see header items 3-5. ✔
