# Stream log — city-honolulu — 2026-08-27

Phase-2 leaf stream for Linear US-193: Honolulu, HI geocoder-unlocked
registration (311 + PERMITS). Spine is serial after this stream; do not
edit spine files here.

## Claim

- **Stream id:** `city-honolulu`
- **Leaf files I will create/edit:**
  - `.streams/city-honolulu.md` (this file)
  - `apps/api/src/spatial/cities/honolulu.py` (NEW)
  - `apps/api/src/producers/field_maps_honolulu.py` (NEW)
  - `apps/api/tests/unit/test_producers_honolulu.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (CityId.HONOLULU, ALIASES, REGISTRY)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html` (city registration rule)
  - `apps/api/src/producers/complaints_311_producer.py` (`_parse_datetime` lacks
    Honolulu's `"August 26, 2026 at 11:52 PM"` format — documented, not applied)

## Intent

Leaf-complete a PARTIAL Honolulu metro: live Socrata 311 `jdy7-ftwe` and
PERMITS `4vab-c87q`, both `needs_geocode=True` (ADR 0004). Tests pass
without a registry entry. Re-probe ≤72h is required before treating
endpoints as verified.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed Linear US-193 and dispatched
  this leaf stream. Spine hold deferred until leaf + live probe land.
- 2026-08-27 12:35 PT — Live re-probe of `data.honolulu.gov`:
  - **311 `jdy7-ftwe` ("HNL 311 Reports") is LIVE.** Rolling 30-day snapshot,
    updated daily. `rowsUpdatedAt` 2026-08-27T10:00:23Z. 2,470 rows.
    Newest `id` = `R2026-23200`, `date_created` = "August 26, 2026 at 11:52 PM".
    9 columns, no coordinates. Address fields: `street` / `city` / `state`
    (`Hawaii`, not `HI`) / `zip_code`. Text watermark — lexical `$order` on
    `date_created` is wrong (July sorts after August); use `id DESC` or typed
    watermark `'%B %d, %Y at %I:%M %p'`. Map `incident_address` to `street`
    only so geocode_context `"Honolulu, HI"` is not doubled (full state name
    `Hawaii` does not match `_STATE_RE`).
  - **PERMITS `4vab-c87q` IS a closed archive.** Title "January 1, 2005 through
    June 30, 2025"; description says static snapshot. `max(issuedate)` =
    2025-07-01; `max(createddate)` = 2025-06-30; 0 rows with issuedate ≥
    2026-01-01; `rowsUpdatedAt` 2025-08-12. Catalog search found no live
    successor (other permit items are 2010–2017 filters). Address-only
    `joblocation` / `address`. Field map is authored so a successor can wire
    it; **do not register this resource as a live incremental feed** (stale
    mirror rule). Recommended spine apply: 311-only until a live permits
    resource appears.
- 2026-08-27 12:40 PT — Geography is City-and-County of Honolulu (island of
  Oahu). Six divisions, containment-sane. `city_id="honolulu"`.
  `needs_geocode=True`, `geocode_context="Honolulu, HI"`. No new FeedType.
- 2026-08-27 12:50 PT — Leaf tests green:
  `apps/api/.venv/bin/pytest tests/unit/test_producers_honolulu.py -q`
  → **23 passed**. No `CityId.HONOLULU`. No spine files touched.

## Current step

Spine applied 2026-08-27 ~13:00 PT (orchestrator, serial hold). 311-only.
`pytest -m interlock` **22 passed**. Leaf tests **23 passed**. METRO_META +
`index.html` byte-synced. `"%B %d, %Y at %I:%M %p"` added to 311
`_parse_datetime`. Permits `4vab-c87q` still withheld.

## Next step

Linear US-193 comment + Done. No further code in this stream.

---

## Exact spine delta (DO NOT APPLY IN THIS STREAM)

Copy-paste for the serial interlock hold. **BLOCKER:** register 311 only.
Do not add the PERMITS DatasetSpec against `4vab-c87q` (closed archive).
The permits field map is ready at `field_maps_honolulu.FIELD_MAP["permits"]`
for a live successor.

### 1. `apps/api/src/config.py`

Add after the Fort Worth settings (near `arcgis_fort_worth_permits_url`):

```python
    # Honolulu, HI (US-193): City and County of Honolulu Socrata. 311 is a
    # rolling 30-day snapshot (address-only, ADR-0004). Permits endpoint is
    # reserved for a live successor — 4vab-c87q is a closed archive through
    # 2025-06-30 and must not be wired as incremental.
    socrata_honolulu_311_endpoint: str = Field(
        default="https://data.honolulu.gov/resource/jdy7-ftwe.json",
        description="Honolulu HNL 311 Reports (rolling 30-day) Socrata endpoint",
    )
    socrata_honolulu_permits_endpoint: str = Field(
        default="https://data.honolulu.gov/resource/4vab-c87q.json",
        description="Honolulu building permits Socrata endpoint (CLOSED ARCHIVE through 2025-06-30; do not ingest as live)",
    )
```

### 2. `apps/api/src/spatial/city_registry.py`

**Import** (with the other field-map / city imports):

```python
from src.producers.field_maps_honolulu import FIELD_MAP as HONOLULU_FIELD_MAP
from src.spatial.cities.honolulu import (
    HONOLULU_DIVISION_BBOXES,
    HONOLULU_DIVISIONS,
    HONOLULU_METRO_BBOX,
    HONOLULU_SUBMARKETS,
)
```

**Enum** — add after `FORT_WORTH = "fort_worth"`:

```python
    HONOLULU = "honolulu"
```

**ALIASES** — add after the Fort Worth block, before the closing `}` of `ALIASES`:

```python
    # Honolulu / City and County of Honolulu (Oahu)
    "honolulu": CityId.HONOLULU,
    "honolulu_hi": CityId.HONOLULU,
    "honolulu hi": CityId.HONOLULU,
    "hnl": CityId.HONOLULU,
    "oahu": CityId.HONOLULU,
    "city_and_county_of_honolulu": CityId.HONOLULU,
    "city and county of honolulu": CityId.HONOLULU,
```

**REGISTRY** — append before the closing `}` of `REGISTRY`. 311 only:

```python
    CityId.HONOLULU: CityRegistration(
        city_id=CityId.HONOLULU,
        name="Honolulu / City and County of Honolulu",
        state="HI",
        center={"lat": 21.3069, "lng": -157.8583},
        metro_bbox=HONOLULU_METRO_BBOX,
        division_bboxes=HONOLULU_DIVISION_BBOXES,
        submarkets=HONOLULU_SUBMARKETS,
        divisions=HONOLULU_DIVISIONS,
        job_suffix="honolulu",
        # Partial registration like Austin/LA, but PERMITS is withheld:
        # 4vab-c87q is a closed snapshot through 2025-06-30 (US-193 live
        # probe 2026-08-27). 311 only until a live permits successor exists.
        datasets={
            FeedType.COMPLAINTS_311: DatasetSpec(
                endpoint=settings.socrata_honolulu_311_endpoint,
                platform="socrata",
                watermark_col="date_created",
                id_keys=["id"],
                topic=settings.topic_311,
                interval_seconds=180.0,
                producer_key="311",
                expected_cadence_days=1,
                rolling_window_days=30,
                watermark_type="text",
                watermark_format="%B %d, %Y at %I:%M %p",
                order_by="id",
                needs_geocode=True,
                geocode_context="Honolulu, HI",
                field_map=HONOLULU_FIELD_MAP["311"],
            ),
            # DO NOT ADD FeedType.PERMITS against 4vab-c87q.
            # Closed archive: max(issuedate)=2025-07-01, 0 rows in 2026,
            # rowsUpdatedAt 2025-08-12. Field map is HONOLULU_FIELD_MAP["permits"]
            # (joblocation/address, tmk, buildingpermitno/externalfilenum).
        },
    ),
```

If a live permits successor appears, the withheld spec would be:

```python
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.socrata_honolulu_permits_endpoint,  # REPLACE with live resource
                platform="socrata",
                watermark_col="issuedate",
                id_keys=["buildingpermitno", "externalfilenum", "objectid"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=1,
                needs_geocode=True,
                geocode_context="Honolulu, HI",
                field_map=HONOLULU_FIELD_MAP["permits"],
            ),
```

### 3. `apps/api/src/spatial/cities/__init__.py`

Import (after fort_worth):

```python
from src.spatial.cities.honolulu import (
    HONOLULU_DIVISION_BBOXES,
    HONOLULU_DIVISIONS,
    HONOLULU_METRO_BBOX,
    HONOLULU_SUBMARKETS,
    is_in_honolulu_metro,
)
```

`__all__` append:

```python
    "HONOLULU_METRO_BBOX",
    "HONOLULU_DIVISION_BBOXES",
    "HONOLULU_DIVISIONS",
    "HONOLULU_SUBMARKETS",
    "is_in_honolulu_metro",
```

### 4. `apps/api/src/serving/dashboard.py` METRO_META **and**
   `apps/dashboard/public/index.html` (byte-sync; city-registration rule)

Add after `fort_worth`:

```javascript
      honolulu: { name: 'Honolulu / City and County of Honolulu' },
```

Must land in **both** files in the same spine hold. Snapshot export coverage
and res-5 grid-tile coverage in the published manifest are also required
before the gate is green — those are post-ingest, not this leaf.

### 5. Optional same-hold: `apps/api/src/producers/complaints_311_producer.py`

Add `"%B %d, %Y at %I:%M %p"` to `_parse_datetime`'s format tuple. Without it,
Honolulu 311 `date_created` ("August 26, 2026 at 11:52 PM") falls back to
`datetime.now(UTC)`. This is a shared-producer spine edit; do not skip
silently — created_date quality depends on it.

No new `FeedType`. Shared `field_maps.py` does not need an edit
(`resolve_field_map` reads `spec.field_map`).
