# Stream log — west-oxnard_ventura — 2026-08-28

## Claim

- **Stream id:** `west-oxnard_ventura`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/oxnard_ventura.py`
  - `apps/api/src/producers/field_maps_oxnard_ventura.py`
  - `apps/api/tests/unit/test_producers_oxnard_ventura.py`
- **Spine files I expect to need:** NONE

## Intent

Live-probe official ArcGIS open-data feeds for Oxnard, CA and San Buenaventura
(City of Ventura), CA; pick the strongest single-jurisdiction anchor (per repo
norm — miami_dade is the only composite); if feeds verify, build the leaf trio
(city module + FEED_SPECS, field maps, spine-stable tests) and record a spine
delta with the exact CityId member/registry/config fields a spine holder needs.
If no verifiable official feed exists, report REJECT with evidence. Ticket:
US-232. No git commits. No Linear updates.

## Decisions

- 2026-08-28 ~12:50Z — Ticket's Hub URLs are dead: `oxnard.opendata.arcgis.com`
  and `ventura.opendata.arcgis.com` both return
  `{"error":"Domain record(s) not found :: ... 404"}`; `venturacity.us` has no
  DNS. Real doors found live: Oxnard AGO org `oxnard.maps.arcgis.com`
  (orgid `PWexKTkN39Lf339y`, 124 feature services); City of Ventura hub
  `open-data-cityofventura.hub.arcgis.com` (DCAT, 37 datasets) backed by AGO
  org `dBVj4EXO3IdRPOqb` (205 feature services).
- 2026-08-28 ~12:55Z — Oxnard: only live event feed is **311 Requests**
  (hosted `services3.arcgis.com/PWexKTkN39Lf339y/.../Requests/FeatureServer/0`):
  235,026 rows, native point geometry, 11 fields, maxRecordCount 2000, newest
  `DateCreated` 1787834885000 = 2026-08-27T12:48:05+00:00. No hosted permits
  layer (full 124-title catalog scanned). `HTE_Layers_Businesses` license
  layers are a STALE 2021 snapshot (199+31 rows, newest `BLICENSEIS`
  2020-03, item last modified 2023-04) — REJECTED as SLA. No deeds.
- 2026-08-28 ~13:05Z — Ventura (City of San Buenaventura) verified LIVE:
  - **SLA** `OpenData_PSI_BusinessLicenses/FeatureServer/0` (org
    `dBVj4EXO3IdRPOqb`): 12,590 rows, native point geometry, maxRecordCount
    16,000, 24 fields; watermark `DATEISSUE` newest 1787814000000 =
    2026-08-27T07:00:00+00:00; 193 DATEISSUE-null rows; 0 null geometry in
    newest 500; ISO/ANSI date where-literals work (epoch-ms literals 400).
  - **311 (graffiti subset)** `Graffiti_Responses_Read_Only/FeatureServer/0`:
    22,085 rows, native point geometry, maxRecordCount 10,000; watermark
    `ReportedOn` newest 1787943600000 = 2026-08-28T19:00:00+00:00 (probe
    ~20:00Z — hours fresh); 0 null geometry in newest 500; no address column.
  - **CRIME** `OpenData_Police_Crimes/FeatureServer/0`: 85,974 rows, native
    point geometry (ADR-0004 satisfied — coords AND generalized block
    address), maxRecordCount 2000; watermark `Incident_Date_Start` newest
    1787783460000 = 2026-08-26T22:31:00+00:00; edit stamp `created_date`
    2026-08-28T16:26:54+00:00 (daily police sync); 0 null geometry and 0
    future dates in newest 500.
  - REJECTED: `Development_Projects_Public` (238-row polygon dashboard
    tracker, string `LastUpdate`), `EGOV_CSS` (reference
    address/street/parcel layers, no events), county recorder
    (recorder.countyofventura.org reachable=200 but vendor search portal,
    no bulk feed) → deeds stay unregistered (partial-without-deeds is fine).
- 2026-08-28 ~13:10Z — **ANCHOR = City of San Buenaventura (Ventura)**: 3
  verified live feeds (SLA + 311-family + crime) vs Oxnard's 1 (311). Single-
  jurisdiction registration; Oxnard 311 documented as future companion
  (metro companion ticket), NOT composited. Metro bbox covers Ventura city +
  immediate context and deliberately EXCLUDES the Oxnard plain so no future
  Oxnard rows can resolve into Ventura divisions.
- 2026-08-28 ~13:15Z — Mixed-CRS trap found: Ventura SLA attributes
  `BADDRX`/`BADDRY` are a local grid (in-city ≈ 22589–24716 / 19570–20086;
  0/0 on out-of-city rows) — NOT degrees, NOT CA state plane; never mapped,
  no `state_plane_*` spec keys declared (nothing on any of the three layers
  is state-plane; the aurora precedent applies only to state-plane sources).
  Coordinates come only from the outSR=4326 geometry lift on all three feeds.

## Current step

RESUMING after account-quota death (prior run: Phase B build wrote the city
module + field maps, then died before the test file / verification). Audit
found one defect: live SLA column is `BADDRY` (not `BADDY`) — field map
`DROPPED_NONADDRESS_COLUMNS` and both docstrings pinned the wrong name;
fixed. Test file was missing entirely — written now from a fresh live
re-probe (2026-08-28): SLA in-metro row OBJECTID 2263 (ST. JOSEPH @ MAYFAIR
OF LONDON, MIDTOWN) + out-of-city edge OBJECTID 1641 (OUTFRONT MEDIA,
LOS ANGELES), 311 newest objectid 25098, crime newest ObjectID 85795.

## Outcome

**ACCEPT.** Built all three leaf files for the Ventura-anchored
Oxnard–Ventura metro. Verified:

- `pytest tests/unit/test_producers_oxnard_ventura.py -q` — **37 passed**
- `pytest -k oxnard_ventura -q` — **39 passed** (37 leaf + 2 structural
  checks from `test_city_leaf_naming` / `test_city_registration`)
- `pytest -m interlock -q` — **24 passed** (leaf-naming pin count failure
  is spine-owned, ignored)
- `ruff check` on all three files — **All checks passed**

One defect caught and fixed in audit: field map `DROPPED_NONADDRESS_COLUMNS`
pinned `"BADDY"` but the live SLA column is `"BADDRY"` — corrected.

## Spine delta

A spine holder **must** add the following to register Oxnard–Ventura.
(Recommended Linear comment body follows at the end.)

### 1. CityId enum member (`src/spatial/city_registry.py`)

```python
OXNARD_VENTURA = "oxnard_ventura"
```

Place in the `CityId` class after the existing `OAKLAND` member (alphabetical).

### 2. Aliases (`src/spatial/city_registry.py` — `_HANDWRITTEN_ALIASES`)

```python
"oxnard_ventura": CityId.OXNARD_VENTURA,
"oxnard-ventura": CityId.OXNARD_VENTURA,
"oxnard ventura": CityId.OXNARD_VENTURA,
"ventura": CityId.OXNARD_VENTURA,
"san_buenaventura": CityId.OXNARD_VENTURA,
```

### 3. REGISTRY entry (`src/spatial/city_registry.py` — `_CITY_REGISTRY`)

```python
CityId.OXNARD_VENTURA: CityRegistration(
    city_id=CityId.OXNARD_VENTURA,
    name="Oxnard–Ventura, CA",
    state="CA",
    center={"lat": 34.2795, "lng": -119.2970},
    metro_bbox=OXNARD_VENTURA_METRO_BBOX,
    division_bboxes=OXNARD_VENTURA_DIVISION_BBOXES,
    submarkets=OXNARD_VENTURA_SUBMARKETS,
    divisions=OXNARD_VENTURA_DIVISIONS,
    datasets={
        FeedType.SLA: get_oxnard_ventura_dataset("sla"),
        FeedType.COMPLAINTS_311: get_oxnard_ventura_dataset("311"),
        FeedType.CRIME: get_oxnard_ventura_dataset("crime"),
    },
    job_suffix="",
),
```

### 4. Config endpoints (if `src/config.py` has a city-specific block)

No city-specific config block is needed — the three feeds all use the same
AGO org (`dBVj4EXO3IdRPOqb`) and the generic ArcGIS adapter. The
`topic_sla`/`topic_311`/`topic_crime` settings already exist with defaults.

### 5. Dashboard metro-meta wiring

Add `metro-chip` + `?city=oxnard_ventura` deep link and snapshot-export
coverage in `apps/dashboard/src/index.ts` (and/or `metro_jobs` in
`src/serving/dashboard.py`). Per the city-registration rule, this is required
in the same spine hold: `TestDashboardWiring` and `TestSnapshotWiring` fail
`pytest -m interlock` if a registered city is missing from the map.

### 6. `apps/spatial/cities/__init__.py`

Add the `from .oxnard_ventura import ...` line.

### 7. Leaf-naming pin count

`tests/unit/test_city_leaf_naming.py` has a count pin that will fail once
the enum member is added — accept the red gate and bump the pin.

### Recommended Linear comment

```
Spine delta for US-232 (Oxnard–Ventura, CA):

CityId: OXNARD_VENTURA = "oxnard_ventura"
Aliases: oxnard_ventura, oxnard-ventura, oxnard ventura, ventura, san_buenaventura
Feeds: SLA (FeedType.SLA, snapshot), COMPLAINTS_311 (FeedType.COMPLAINTS_311, incremental), CRIME (FeedType.CRIME, incremental)
Anchor: City of San Buenaventura (Ventura). Oxnard 311 documented as future companion metro — NOT composited.
Probe: 2026-08-28, all three feeds live on dBVj4EXO3IdRPOqb.
Leaf files: apps/api/src/spatial/cities/oxnard_ventura.py, apps/api/src/producers/field_maps_oxnard_ventura.py, tests/unit/test_producers_oxnard_ventura.py (37 tests pass, ruff clean, interlock 24).
Dashboard: wire metro-chip + snapshot export in same hold.
```

## Next step

None — leaf complete. The spine delta above is ready for a spine-holder.