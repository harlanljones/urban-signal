# Stream log — city-memphis — 2026-08-27

Phase-2 leaf stream for Linear US-201: Memphis, TN partial registration
(PERMITS + 311). Spine is serial after this stream; do not edit spine
files here.

## Claim

- **Stream id:** `city-memphis`
- **Leaf files I will create/edit:**
  - `.streams/city-memphis.md` (this file)
  - `apps/api/src/spatial/cities/memphis.py` (NEW)
  - `apps/api/src/producers/field_maps_memphis.py` (NEW)
  - `apps/api/tests/unit/test_producers_memphis.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html`

## Intent

Leaf-complete a PARTIAL Memphis metro from `docs/research/wave-3-probe-memphis.md`:
PERMITS `DPD_Building_Permits` (monthly cadence) + 311
`311_Request_Map_PROD` layer 0. Tests pass without `CityId.MEMPHIS`.
Record an exact spine delta.

## Decisions

- 2026-08-27 ~13:00 PT — Orchestrator dispatched this leaf after Honolulu
  and Orlando spines landed. Probe US-201 is Done / partial ready.
- 2026-08-27 ~13:05 PT — Live re-probe of both FeatureServers (layer
  describe + newest-row query, `outSR=4326`):
  - **PERMITS** `DPD_Building_Permits`: 27k point layer, `maxRecordCount`
    1000, OID **`ObjectId`** (not `OBJECTID`). Newest `Issued_Date` still
    2026-07-31 (`RES-ALT-26-000896`, 2218 Oxford Square Ct, native
    35.033 / −89.993). Columns match the probe. No X/Y. Prefer WGS84
    `Latitude`/`Longitude`. `needs_geocode=True` as a supplement for the
    ~5% coordinate gap (`Address` 500/500). Cadence **31 days** (month-end
    dump; PG County 311 precedent). Do not scrape Accela.
  - **311** layer 0: `maxRecordCount` 3000, OID `OBJECTID`. Newest
    `REPORTED_DATE` same-day (`INCIDENT_NUMBER` `8041445`; `INCIDENT_ID`
    is often null). `outSR=4326` geometry is WGS84. Do **not** map `X`/`Y`
    (mixed WGS84 / EPSG:2274). Watermark `REPORTED_DATE`, never
    `Closed_Date`. Drop CONTACT_* / owner-name / MLGW contact fields.
    Do not register sibling views.
- 2026-08-27 ~13:10 PT — Geography: 6 divisions, center 35.1495, −90.0490,
  `city_id="memphis"`. `SpatialRegistration` included. SLA / deeds absent
  (`get_memphis_dataset` raises).
- 2026-08-27 ~13:15 PT — Geocode caveat: live permit streets often end in
  `CT` (Court). `_STATE_RE` treats that as Connecticut, so ADR-0004 will
  **not** append `Memphis, TN` on those rows. Native WGS84 covers ~95%;
  this only hits the geocode supplement. Do not concatenate City/State
  onto `address_street` (Honolulu Hawaii-word precedent). Finding only —
  `geocoder.py` not edited.
- 2026-08-27 ~13:20 PT — Leaf tests green:
  `apps/api/.venv/bin/pytest tests/unit/test_producers_memphis.py -q`
  → **35 passed**. No `CityId.MEMPHIS`. No spine files touched.

## Files written

- `apps/api/src/spatial/cities/memphis.py`
- `apps/api/src/producers/field_maps_memphis.py`
- `apps/api/tests/unit/test_producers_memphis.py`
- `.streams/city-memphis.md` (this file)

## Tests

```
cd /home/harlan/dev/urban-signal/apps/api && .venv/bin/pytest tests/unit/test_producers_memphis.py -q
35 passed
```

No `CityId.MEMPHIS`. No spine edits.

## Current step

Spine applied 2026-08-27 ~13:20 PT (orchestrator, serial hold). PERMITS +
311. `pytest -m interlock` **22 passed**. Leaf tests **35 passed**.
METRO_META + `index.html` byte-synced.

## Next step

Linear US-201 comment + Done. No further code in this stream.

---

## Exact spine delta (DO NOT APPLY IN THIS STREAM)

Copy-paste for the serial interlock hold. Concurrent Wave-3 leaves
(Miami-Dade already on spine; Phoenix / St. Louis / Albuquerque may land
first) — append after whatever is last at hold time.

**PARTIAL:** PERMITS + 311 only. Do **not** register SLA, deeds, Accela,
or sibling 311 views (Reported Today / Last 7 Days).

### 1. `apps/api/src/config.py`

Add after the last Wave-3 city settings block (currently Miami-Dade):

```python
    # Memphis / Shelby County, TN (US-201): DPD building permits (monthly
    # ArcGIS dump) + citywide 311. Native WGS84 on permits; 311 prefers
    # outSR=4326 geometry (do not map mixed X/Y). Partial — no SLA/deeds.
    arcgis_memphis_permits_url: str = Field(
        default="https://services2.arcgis.com/saWmpKJIUAjyyNVc/arcgis/rest/services/DPD_Building_Permits/FeatureServer/0",
        description="Memphis DPD building permits ArcGIS FeatureServer layer URL",
    )
    arcgis_memphis_311_url: str = Field(
        default="https://311.memphistn.gov/server/rest/services/311/311_Request_Map_PROD/FeatureServer/0",
        description="Memphis 311 Request Map (layer 0) ArcGIS FeatureServer URL",
    )
```

### 2. `apps/api/src/spatial/city_registry.py`

**Import** (with the other field-map / city imports):

```python
from src.producers.field_maps_memphis import FIELD_MAP as MEMPHIS_FIELD_MAP
from src.spatial.cities.memphis import (
    MEMPHIS_DIVISION_BBOXES,
    MEMPHIS_DIVISIONS,
    MEMPHIS_METRO_BBOX,
    MEMPHIS_SUBMARKETS,
)
```

**Enum** — add after the last CityId member:

```python
    MEMPHIS = "memphis"
```

**ALIASES** (`_HANDWRITTEN_ALIASES`) — add after the last city block:

```python
    # Memphis / Shelby County, TN
    "memphis": CityId.MEMPHIS,
    "memphis_tn": CityId.MEMPHIS,
    "memphis tn": CityId.MEMPHIS,
    "mem": CityId.MEMPHIS,
    "shelby_county": CityId.MEMPHIS,
    "shelby county": CityId.MEMPHIS,
    "shelby_county_tn": CityId.MEMPHIS,
```

**REGISTRY** (`_HANDWRITTEN_REGISTRY`) — append before the closing `}`.
Typed DatasetSpec fields (not `extra`):

```python
    CityId.MEMPHIS: CityRegistration(
        city_id=CityId.MEMPHIS,
        name="Memphis / Shelby County",
        state="TN",
        center={"lat": 35.1495, "lng": -90.0490},
        metro_bbox=MEMPHIS_METRO_BBOX,
        division_bboxes=MEMPHIS_DIVISION_BBOXES,
        submarkets=MEMPHIS_SUBMARKETS,
        divisions=MEMPHIS_DIVISIONS,
        job_suffix="memphis",
        # Partial like Austin/LA: PERMITS + 311. SLA/deeds are Tier 3
        # (Accela / Register-of-Deeds UIs). Permits are a monthly dump
        # (expected_cadence_days=31; 0 August 2026 rows on a 27 Aug probe
        # is month-end, not a dead archive). OID is ObjectId not OBJECTID.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_memphis_permits_url,
                platform="arcgis",
                watermark_col="Issued_Date",
                id_keys=["Record_ID", "ObjectId"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=31,
                needs_geocode=True,
                geocode_context="Memphis, TN",
                oid_field="ObjectId",
                max_record_count=1000,
                order_by="Issued_Date DESC",
                field_map=MEMPHIS_FIELD_MAP["permits"],
            ),
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.arcgis_memphis_311_url,
                platform="arcgis",
                watermark_col="REPORTED_DATE",
                id_keys=["INCIDENT_NUMBER", "OBJECTID"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                expected_cadence_days=1,
                needs_geocode=True,
                geocode_context="Memphis, TN",
                oid_field="OBJECTID",
                max_record_count=3000,
                order_by="REPORTED_DATE DESC",
                field_map=MEMPHIS_FIELD_MAP["311"],
            ),
        },
    ),
```

Shared `field_maps.py` does not need an edit (`resolve_field_map` reads
`spec.field_map`). Shared producers do not need an edit. `scheduler.py`
derives job names from REGISTRY (`permits_memphis`, `311_memphis`).

### 3. `apps/api/src/spatial/cities/__init__.py`

Import (after the last city block):

```python
from src.spatial.cities.memphis import (
    MEMPHIS_DIVISION_BBOXES,
    MEMPHIS_DIVISIONS,
    MEMPHIS_METRO_BBOX,
    MEMPHIS_SUBMARKETS,
    is_in_memphis_metro,
)
```

`__all__` append:

```python
    "MEMPHIS_METRO_BBOX",
    "MEMPHIS_DIVISION_BBOXES",
    "MEMPHIS_DIVISIONS",
    "MEMPHIS_SUBMARKETS",
    "is_in_memphis_metro",
```

### 4. `apps/api/src/serving/dashboard.py` METRO_META **and**
   `apps/dashboard/public/index.html` (byte-sync; city-registration rule)

Add after the last metro (currently `miami_dade`):

```javascript
      memphis: { name: 'Memphis / Shelby County' },
```

Must land in **both** files in the same spine hold. Snapshot export
coverage and res-5 grid-tile coverage in the published manifest are also
required before the gate is green — those are post-ingest, not this leaf.

### 5. Do not

- Register `FeedType.SLA` or `FeedType.DEEDS`.
- Scrape `aca-prod.accela.com/SHELBYCO`.
- Register sibling 311 layers (Reported Today / Last 7 Days / Transfer Pending).
- Map 311 `X`/`Y` (mixed WGS84 / EPSG:2274). ArcGISClient `outSR=4326` is the native path.
- Watermark 311 on `Closed_Date`.
- Touch `geocoder.py` for the Court/`CT` false-positive (finding only).

No new `FeedType`.
