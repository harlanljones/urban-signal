# Integration Spec — Add LOS ANGELES to the MapLibre Dashboard

Target file: `src/serving/dashboard.py` (single embedded HTML/JS/CSS document).
All line numbers below are **pre-edit** line numbers in that file. Apply sections 1–7
in any order; every code block is copy-pasteable verbatim.

Source-of-truth data (already merged, do not re-derive):
`src/spatial/cities/los_angeles.py` — `LA_METRO_BBOX` (L14–19), `LA_DIVISION_BBOXES`
(L22–29), `LA_DIVISIONS` BoroughMeta entries (L547–602); registry center from
`src/spatial/city_registry.py` L382 (`{"lat": 34.0522, "lng": -118.2437}`).

Verified before writing this spec:
- Every preset lat/lng falls inside its division bbox (python check, all 6 pass).
- Metro guard equals `LA_METRO_BBOX` exactly: lat 33.7–34.34, lng −118.63…−117.95.
- Coordinate ladder resolves 31/32 submarket centers to their true division; the one
  exception is Boyle Heights (see Uncertainties at bottom).

---

## 1. City `<option>` (insert into `<select id="city-select">`, after the chicago option on L1062, before `</select>` on L1063)

```html
          <option value="los_angeles">🌴 Los Angeles Metro (6 Divisions)</option>
```

(Emoji style follows siblings: 🌉 SF, 🗽 NYC, 🏙️ Chicago; 🌴 chosen for LA.)

---

## 2. `CITY_CONFIGS.los_angeles` entry (insert inside the `CITY_CONFIGS` object literal, after the `san_francisco` entry's closing `}` on L1262, before the object's closing `};` on L1263)

```js
      los_angeles: {
        center: [-118.2437, 34.0522],
        zoom: 10.2,
        pitch: 48,
        bearing: -10,
        name: 'Los Angeles Metro',
        allLabel: 'All LA',
        divisions: [
          { key: 'ALL', label: 'All LA', class: 'ALL' },
          { key: 'CENTRAL_LA', label: 'Central LA', class: 'CentralLA' },
          { key: 'WESTSIDE', label: 'Westside', class: 'Westside' },
          { key: 'SAN_FERNANDO_VALLEY', label: 'San Fernando Valley', class: 'SanFernandoValley' },
          { key: 'HARBOR_SOUTH_BAY', label: 'Harbor / South Bay', class: 'HarborSouthBay' },
          { key: 'SOUTH_LA', label: 'South LA', class: 'SouthLA' },
          { key: 'EASTSIDE_SGV', label: 'Eastside / SGV', class: 'EastsideSGV' }
        ],
        presets: {
          'ALL': { lat: 34.0522, lng: -118.2437, zoom: 10.0, pitch: 45, bearing: -10 },
          'CENTRAL_LA': { lat: 34.07, lng: -118.28, zoom: 12.5, pitch: 48, bearing: -10 },
          'WESTSIDE': { lat: 34.04, lng: -118.45, zoom: 12.0, pitch: 48, bearing: -10 },
          'SAN_FERNANDO_VALLEY': { lat: 34.19, lng: -118.44, zoom: 11.5, pitch: 45, bearing: -10 },
          'HARBOR_SOUTH_BAY': { lat: 33.81, lng: -118.29, zoom: 11.5, pitch: 45, bearing: -10 },
          'SOUTH_LA': { lat: 33.98, lng: -118.29, zoom: 12.0, pitch: 48, bearing: -10 },
          'EASTSIDE_SGV': { lat: 34.11, lng: -118.16, zoom: 11.5, pitch: 48, bearing: -10 }
        }
      },
```

Provenance of every number:
- `center`: registry center `[lng, lat]` = `[-118.2437, 34.0522]`.
- Division preset `lat`/`lng`: each BoroughMeta's `center_lat`/`center_lng`, verbatim.
- Division preset `zoom`: each BoroughMeta's `zoom`, verbatim (12.5 / 12.0 / 11.5 /
  11.5 / 12.0 / 11.5) — San Fernando Valley, Harbor/South Bay and Eastside/SGV are
  the largest divisions and carry the lowest zooms; all within 11.5–13.0 as required.
- `ALL` preset zoom 10.0 sits just under config `zoom: 10.2`, mirroring the sibling
  pattern (nyc 11.2→10.8, chicago 11.0→10.6, sf 11.8→11.0). Config zoom 10.2 is within
  the instructed 9.8–10.6 range for the wide LA metro; pitch/bearing match sibling
  conventions (config 48/−10; ALL 45/−10; large divisions 45, smaller 48).

Note: unlike `san_francisco` (which carries duplicate human-label preset keys,
L1256–1260), LA does NOT need alias presets — legacy/human-label filter strings are
canonicalized by the normalizeBorough additions in section 3.

Division-key spelling was cross-checked character-for-character against
`LA_DIVISION_BBOXES` keys: `CENTRAL_LA`, `WESTSIDE`, `SAN_FERNANDO_VALLEY`,
`HARBOR_SOUTH_BAY`, `SOUTH_LA`, `EASTSIDE_SGV`.

---

## 3. `normalizeBorough` additions (function starts L1429)

### 3a. Default division when no filter is given — insert a new line after L1432

```js
        if (currentCity === 'chicago') return 'Central / Downtown';
        if (currentCity === 'los_angeles') return 'CENTRAL_LA';
        return 'Manhattan';
```

(the new line is the middle one; recommended default is `'CENTRAL_LA'`)

### 3b. Upper-case collapsed alias mappings — insert after L1452, before `return clean;`

```js
      if (upper === 'CENTRALLA') return 'CENTRAL_LA';
      if (upper === 'WESTSIDE') return 'WESTSIDE';
      if (upper === 'SANFERNANDOVALLEY' || upper === 'SFV') return 'SAN_FERNANDO_VALLEY';
      if (upper === 'HARBORSOUTHBAY') return 'HARBOR_SOUTH_BAY';
      if (upper === 'SOUTHLA') return 'SOUTH_LA';
      if (upper === 'EASTSIDESGV') return 'EASTSIDE_SGV';
```

These inputs are what `getBoroughClass()` (L1456–1458) produces from the raw keys:
`normalizeBorough(b)` collapses `[\s\-_/]` and upper-cases, e.g. `'Harbor / South Bay'`
→ `'HARBORSOUTHBAY'`. Mapping them back to canonical SCREAMING_SNAKE keys keeps saved
filters and tag rendering consistent.

---

## 4. `getBoroughNameByCoords` additions (function starts L2477)

### 4a. No-coordinate default — insert a new line between L2480 and L2481

```js
        if (currentCity === 'chicago') return 'Central / Downtown';
        if (currentCity === 'los_angeles') return 'CENTRAL_LA';
        return 'Manhattan';
```

(the new line is the middle one)

### 4b. Los Angeles bbox ladder — insert after the SF block's closing `}` on L2489, before the Bronx check on L2490

Guard values are `LA_METRO_BBOX` copied exactly (min_lat 33.7, max_lat 34.34,
min_lng −118.63, max_lng −117.95); each ladder line is its `LA_DIVISION_BBOXES`
rectangle copied exactly.

Check order rationale — source-data overlaps (verified by python):
1. **CENTRAL_LA × EASTSIDE_SGV is a real area overlap** (lat 34.03–34.14 ×
   lng −118.28…−118.20). CENTRAL_LA is checked first because 3 of the 4 submarkets
   whose centers fall in the overlap band belong to CENTRAL_LA (Downtown Core, Arts
   District, Silver Lake/Echo Park vs Eastside's Boyle Heights).
2. **WESTSIDE × SOUTH_LA overlap slightly** (lat 33.98–34.03 × lng −118.38…−118.35);
   WESTSIDE is checked first (no submarkets live in the sliver; tie-break arbitrary).
3. All other pairs touch only on shared edges; inclusive comparisons send exact-edge
   points to whichever box is checked first (harmless).
4. SAN_FERNANDO_VALLEY is checked first so the shared lat-34.14 edge with CENTRAL_LA
   resolves to the Valley.

```js
      if (currentCity === 'los_angeles') {
        if (lat >= 33.7 && lat <= 34.34 && lng >= -118.63 && lng <= -117.95) {
          if (lat >= 34.14 && lat <= 34.34 && lng >= -118.63 && lng <= -118.28) return 'SAN_FERNANDO_VALLEY';
          if (lat >= 33.98 && lat <= 34.12 && lng >= -118.56 && lng <= -118.35) return 'WESTSIDE';
          if (lat >= 33.7 && lat <= 33.9 && lng >= -118.45 && lng <= -118.1) return 'HARBOR_SOUTH_BAY';
          if (lat >= 33.9 && lat <= 34.03 && lng >= -118.38 && lng <= -118.2) return 'SOUTH_LA';
          if (lat >= 34.03 && lat <= 34.14 && lng >= -118.35 && lng <= -118.2) return 'CENTRAL_LA';
          if (lat >= 34.03 && lat <= 34.2 && lng >= -118.28 && lng <= -117.95) return 'EASTSIDE_SGV';
          return 'CENTRAL_LA';
        }
      }
```

The trailing `return 'CENTRAL_LA';` is the in-guard catch-all for metro-area points
outside all six rectangles (uninhabited/ocean slivers such as the Malibu coast and the
area above lat 34.20 east of −118.28), mirroring how the SF ladder defaults to
`'SAN_FRANCISCO_CORE'`. Points outside the metro guard fall through to the existing
NYC checks unchanged (LA coordinates cannot collide with the other cities' ladders).

Simulation result over all 32 LA submarket centers with this exact ordering: 31/32
resolve to their true division; only Boyle Heights (34.034, −118.21) resolves to
CENTRAL_LA instead of EASTSIDE_SGV — unavoidable given the source rectangles (see
Uncertainties).

---

## 5. `detectUserDefaultCity` + geolocation detection (function L1352–~1400)

### 5a. Saved-city whitelist (REQUIRED) — replace L1355

Current:

```js
        if (saved && (saved === 'san_francisco' || saved === 'chicago' || saved === 'nyc')) {
```

Replace with:

```js
        if (saved && (saved === 'san_francisco' || saved === 'chicago' || saved === 'nyc' || saved === 'los_angeles')) {
```

Without this, a returning LA visitor is silently demoted to san_francisco.

### 5b. Geolocation branch — there are NO bbox gates; detection is nearest-center haversine via `findClosestCity` (L1334–1350), so auto-detection requires adding LA to its coordinate table

Replace the `cityCoordinates` object at L1335–1339:

```js
      const cityCoordinates = {
        'san_francisco': { lat: 37.7749, lng: -122.4194 },
        'chicago': { lat: 41.8781, lng: -87.6298 },
        'nyc': { lat: 40.7128, lng: -74.0060 },
        'los_angeles': { lat: 34.0522, lng: -118.2437 }
      };
```

Everything else in `detectUserDefaultCity` (geolocation timeout → san_francisco at
L1361–1371, permission-denied fallback at L1386–1391, sessionStorage write of the
detected id at L1383) is generic and needs no change. Note for reviewers: because
detection is pure nearest-center (no per-city bbox test), users in fringe areas
(e.g. Ventura County) could tip toward either LA or SF; acceptable, matches existing
behavior for the other cities.

---

## 6. CSS active-color rules for the six LA classes

Available color variables in `:root` (L50–81): exactly **five distinct colors** exist —
`--accent-primary` (#38bdf8), `--accent-success` (#34d399), `--accent-warning`
(#fbbf24), `--accent-danger` (#f43f5e), `--accent-purple` (#c084fc). The
`--division-*` (L77–81) and `--borough-*` (L71–75) groups duplicate those same five
hex values. **Six divisions, five colors: `EastsideSGV` REUSES `--accent-primary`.**

Two selector variants are needed per rule, matching the sibling multi-selector style
(L347–351, L687–691):
- PascalCase (`CentralLA`…) — applied directly by `renderDivisionTabs` via `d.class`
  (buttons);
- Collapsed-uppercase (`CENTRALLA`…) — produced by `getBoroughClass(borough)`
  (L1456–1458) for `.borough-tag` chips rendered at L1593/L1674/L2095, since raw
  division keys like `'CENTRAL_LA'` collapse to `'CENTRALLA'`.

Color assignment mirrors sibling conventions (primary=core/central, success/warning/
danger/purple for the geographic ring):

### 6a. Append after L351 (end of the `.borough-btn.active.*` block)

```css
    /* Los Angeles divisions */
    .borough-btn.active.CentralLA, .borough-btn.active.CENTRALLA { color: var(--accent-primary); }
    .borough-btn.active.Westside, .borough-btn.active.WESTSIDE { color: var(--accent-success); }
    .borough-btn.active.SanFernandoValley, .borough-btn.active.SANFERNANDOVALLEY { color: var(--accent-warning); }
    .borough-btn.active.HarborSouthBay, .borough-btn.active.HARBORSOUTHBAY { color: var(--accent-danger); }
    .borough-btn.active.SouthLA, .borough-btn.active.SOUTHLA { color: var(--accent-purple); }
    .borough-btn.active.EastsideSGV, .borough-btn.active.EASTSIDESGV { color: var(--accent-primary); }
```

### 6b. Append after L691 (end of the `.borough-tag.*` block)

```css
    .borough-tag.CentralLA, .borough-tag.CENTRALLA { color: var(--accent-primary); }
    .borough-tag.Westside, .borough-tag.WESTSIDE { color: var(--accent-success); }
    .borough-tag.SanFernandoValley, .borough-tag.SANFERNANDOVALLEY { color: var(--accent-warning); }
    .borough-tag.HarborSouthBay, .borough-tag.HARBORSOUTHBAY { color: var(--accent-danger); }
    .borough-tag.SouthLA, .borough-tag.SOUTHLA { color: var(--accent-purple); }
    .borough-tag.EastsideSGV, .borough-tag.EASTSIDESGV { color: var(--accent-primary); }
```

Do NOT use `--accent-emerald`, `--accent-amber`, or `--accent-crimson` (referenced by
the chicago rules at L682–684): they are **not defined** in `:root` — pre-existing
latent issue, not ours to fix here.

---

## 7. Full audit of per-city hardcoding (`grep -n "san_francisco|chicago|nyc" src/serving/dashboard.py`)

| Line(s) | What it is | Action |
|---|---|---|
| 1060–1063 | `<select>` options | Add option — section 1 |
| 1184 / 1208 / 1234 | CITY_CONFIGS entries | Add entry — section 2 |
| 1264 | `CITY_CONFIGS.sf = CITY_CONFIGS.san_francisco;` short alias | **No change needed.** Optional nicety: `CITY_CONFIGS.la = CITY_CONFIGS.los_angeles;` would mirror it, but nothing maps `'la'`→`'los_angeles'` in `changeCity` (L1471–1472 maps only `'sf'`), so skip unless that mapping is added too. Out of scope here. |
| 1266 | `let currentCity = 'san_francisco';` initial value | No change needed — pre-detection default intentionally stays SF; detection overrides it. |
| 1335–1340 | `findClosestCity` coordinate table | ADD los_angeles — section 5b (required for geo auto-detect). |
| 1355 | saved-city whitelist | ADD — section 5a. |
| 1361–1362, 1370–1371, 1390–1391 | failure/timeout fallback writes `'san_francisco'` | No change needed — generic deliberate fallback. |
| 1431–1433 | `normalizeBorough` no-filter defaults | ADD LA line — section 3a. |
| 1463, 1477, 1552, 1629 | `CITY_CONFIGS[currentCity] \|\| CITY_CONFIGS.nyc/san_francisco` fallbacks | No change needed — generic once the config exists. |
| 1510–1512 | `currentCity = detected \|\| 'san_francisco'` init flow | No change needed — generic. |
| 2479–2481 | `getBoroughNameByCoords` no-coord defaults | ADD LA line — section 4a. |
| 2483–2494 | coordinate ladders | ADD LA ladder — section 4b. |

Generic (data-driven) paths confirmed needing no change: `renderDivisionTabs`
(L1460–1468, builds buttons from `cfg.divisions`), filter application
(`selectBoroughFilter` L1538–1542, grid filter L2065), borough-tag rendering
(L1590–1593, L1665–1674, L2083–2095), and the `/api/v1/submarkets` per-city catalog
load (L1180–1181). The static header nav HTML (L1068–1075) hardcodes NYC buttons but
`renderDivisionTabs()` replaces its innerHTML on load/city change — visually verify
after integration, but no code change required.

---

## Uncertainties for the integrator to double-check

1. **Boyle Heights misassignment (known, accepted).** Its submarket center
   (34.034, −118.21) lies inside BOTH `CENTRAL_LA` and `EASTSIDE_SGV` source bboxes;
   the section-4b order sends it to CENTRAL_LA. The reverse order would instead strip
   Downtown Core, Arts District and Silver Lake/Echo Park from CENTRAL_LA (worse:
   3 wrong vs 1). Inherent coarseness of `LA_DIVISION_BBOXES`; fix belongs upstream
   in the Python bboxes, not the dashboard.
2. **WESTSIDE×SOUTH_LA sliver** (lat 33.98–34.03 × lng −118.38…−118.35) resolves to
   WESTSIDE; no submarkets affected today.
3. **Config-level camera numbers** (`zoom: 10.2`, ALL preset `zoom: 10.0`) are chosen
   within the instructed ranges (9.8–10.6), not derived from source data — adjust to
   taste during visual QA without breaking anything.
4. **Emoji 🌴** for the option label was not prescribed; swap freely.
5. **Tag-color coverage**: the dual-selector rules in section 6 assume tags always
   render with `getBoroughClass(normalizeBorough(key))` output (`CENTRALLA`,
   `SANFERNANDOVALLEY`, …). If a future payload ever emits raw keys with underscores
   as class names, add `.borough-tag.CENTRAL_LA`-style selectors too (same pattern as
   L687–691).
6. **Pre-existing bugs observed, deliberately not fixed by this spec**: chicago tag
   rules reference undefined vars `--accent-emerald/--accent-amber/--accent-crimson`
   (L682–684), and SF collapsed-uppercase tag classes (`SANFRANCISCOCORE`) match none
   of the SF selectors at L687 — LA gets correct coverage out of the box via the
   dual-selector form.
