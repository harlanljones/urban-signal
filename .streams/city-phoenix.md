# Stream log — city-phoenix — 2026-08-27

Phase-2 leaf stream for Linear US-197: Phoenix, AZ partial registration
(PERMITS + SLA/STR). Spine is serial after this stream; do not edit spine
files here.

## Claim

- **Stream id:** `city-phoenix`
- **Leaf files I will create/edit:**
  - `.streams/city-phoenix.md` (this file)
  - `apps/api/src/spatial/cities/phoenix.py` (NEW)
  - `apps/api/src/producers/field_maps_phoenix.py` (NEW)
  - `apps/api/tests/unit/test_producers_phoenix.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html`

## Intent

Leaf-complete a PARTIAL Phoenix metro from `docs/research/wave-3-probe-phoenix.md`:
PERMITS `Public/Planning_Permit/MapServer/1` plus ShapePHX `_DL` companion,
SLA = ShapePHX Short Term Rentals (STR is the SLA, not `FeedType.STR`).
Tests pass without `CityId.PHOENIX`. Record an exact spine delta.

## Decisions

- 2026-08-27 ~13:00 PT — Orchestrator dispatched this leaf after Honolulu
  and Orlando spines landed. Probe US-197 is Done / partial ready.
- 2026-08-27 ~12:55 PT — Live re-read of the three ArcGIS layers (same hosts
  as the probe). Planning_Permit newest issued row `PER_NUM=26010094`
  `PER_ISSUE_DATE` 2026-08-26T23:16:28Z, WGS84 (−112.005, 33.394).
  ShapePHX `_DL` companion `PERMIT_NUMBER=CTR-102505941-` geometry
  (−112.051, 33.568), `ADDRESS` null. STR `NAME=STR-2024-003813`
  native `LATITUDE`/`LONGITUDE` (33.621, −112.077), `PROPERTY_ADDRESS` suffix
  ` (Active)`.
- STR **is** `FeedType.SLA` (primary), not a companion and not `FeedType.STR`.
  Phoenix has no broader business-tax feed (unlike Orlando BTR+STR).
- Permits companion `shapephx_issued` is `_DL` only. Do not point at
  `ShapePHXPermitsPoints` (frozen 2022-06-29). Same field map, companion
  spellings as fallbacks (`PERMIT_NUMBER` / `PERMIT_ISSUE_DATE` / `PERMIT_TYPE`).
- `needs_geocode=False` on both families. Do not map companion `X`/`Y` or STR
  `NAD83_X`/`NAD83_Y` as WGS84.
- Skip 311 (Dynamics 365 portal, no bulk REST), deeds (no queryable watermark),
  liquor `LIQUOR_RACMap` (no date column), CKAN SOCDS aggregate.
- Geography: City of Phoenix proper (center 33.4484, −112.0740), six village
  groupings. Metro label for the spine: `Phoenix / Maricopa County`.
- Field maps live in `field_maps_phoenix.py`; city module imports them for
  leaf `PHOENIX_FEED_SPECS` / `get_phoenix_dataset`.
- Scheduler does **not** poll `companion_endpoints` today. ShapePHX `_DL`
  ingest is a follow-on unless companion polling is grown in the spine hold.

## Files written

- `apps/api/src/spatial/cities/phoenix.py`
- `apps/api/src/producers/field_maps_phoenix.py`
- `apps/api/tests/unit/test_producers_phoenix.py`

## Tests

```
cd /home/harlan/dev/urban-signal/apps/api && .venv/bin/pytest tests/unit/test_producers_phoenix.py -q
30 passed
```

No `CityId.PHOENIX`. No spine edits in this stream.

Transient collection error mid-run (`alias 'miami_dade' has no registration`)
was a concurrent Miami-Dade spine tear; retry after that hold landed was green.
Not a Phoenix blocker.

## Current step

Spine applied 2026-08-27 ~13:25 PT (orchestrator). PERMITS + SLA (STR).
`pytest -m interlock` **22 passed**. Leaf tests **30 passed**. Companion
ShapePHX `_DL` is metadata until companion polling exists.

## Next step

Linear US-197 Done. No further code in this stream.

---

## Exact spine delta (DO NOT APPLY IN THIS STREAM)

Copy-paste for the serial interlock hold. Partial metro: PERMITS + SLA only.
Do **not** register 311, deeds, liquor, the frozen non-`_DL` ShapePHX permits
layer, CKAN SOCDS, or `FeedType.STR`.

### 1. `apps/api/src/config.py`

Add after the Miami-Dade settings (near `arcgis_miami_dade_sla_enterprise_twin_url`):

```python
    # Phoenix / Maricopa County (US-197): Planning_Permit daily points +
    # ShapePHX STR as SLA. Native geometry (outSR=4326); no geocode.
    # Companion ShapePHXPermitsPoints_DL is weekly Issued; do not wire the
    # frozen non-_DL twin. No 311 / deeds.
    arcgis_phoenix_permits_url: str = Field(
        default="https://maps.phoenix.gov/pub/rest/services/Public/Planning_Permit/MapServer/1",
        description="Phoenix Planning_Permit layer 1 ArcGIS MapServer URL",
    )
    arcgis_phoenix_shapephx_permits_url: str = Field(
        default="https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/ShapePHXPermitsPoints_DL/MapServer/0",
        description="Phoenix ShapePHX Issued permits _DL companion ArcGIS MapServer URL",
    )
    arcgis_phoenix_sla_url: str = Field(
        default="https://mapportal.phoenix.gov/pds/rest/services/ShapePHX/ShapePHX_Short_Term_Rentals/MapServer/0",
        description="Phoenix ShapePHX Short Term Rentals ArcGIS MapServer URL (SLA)",
    )
```

### 2. `apps/api/src/spatial/city_registry.py`

**Import** (with the other field-map / city imports):

```python
from src.producers.field_maps_phoenix import (
    PERMITS_FIELD_MAP as PHOENIX_PERMITS_FIELD_MAP,
    SLA_FIELD_MAP as PHOENIX_SLA_FIELD_MAP,
)
from src.spatial.cities.phoenix import (
    PHOENIX_DIVISION_BBOXES,
    PHOENIX_DIVISIONS,
    PHOENIX_METRO_BBOX,
    PHOENIX_SUBMARKETS,
)
```

**Enum** — add after `MIAMI_DADE = "miami_dade"`:

```python
    PHOENIX = "phoenix"
```

**ALIASES** — add after the Miami-Dade block, before the closing `}` of `_HANDWRITTEN_ALIASES`:

```python
    # Phoenix / Maricopa County, AZ
    "phoenix": CityId.PHOENIX,
    "phx": CityId.PHOENIX,
    "phoenix_az": CityId.PHOENIX,
    "phoenix az": CityId.PHOENIX,
    "maricopa_county": CityId.PHOENIX,
    "maricopa county": CityId.PHOENIX,
```

**REGISTRY** — append before the closing `}` of `_HANDWRITTEN_REGISTRY`. PERMITS + SLA only:

```python
    CityId.PHOENIX: CityRegistration(
        city_id=CityId.PHOENIX,
        name="Phoenix / Maricopa County",
        state="AZ",
        center={"lat": 33.4484, "lng": -112.0740},
        metro_bbox=PHOENIX_METRO_BBOX,
        division_bboxes=PHOENIX_DIVISION_BBOXES,
        submarkets=PHOENIX_SUBMARKETS,
        divisions=PHOENIX_DIVISIONS,
        job_suffix="phoenix",
        # Partial: Planning_Permit + ShapePHX STR-as-SLA. No 311 / deeds.
        # Do not use FeedType.STR. Companion _DL is metadata until the
        # scheduler grows companion polling.
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_phoenix_permits_url,
                platform="arcgis",
                watermark_col="PER_ISSUE_DATE",
                id_keys=["PER_NUM", "PID", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                expected_cadence_days=1,
                oid_field="OBJECTID",
                max_record_count=2000,
                order_by="PER_ISSUE_DATE DESC",
                needs_geocode=False,
                companion_endpoints={
                    "shapephx_issued": settings.arcgis_phoenix_shapephx_permits_url,
                },
                field_map=PHOENIX_PERMITS_FIELD_MAP,
            ),
            FeedType.SLA: DatasetSpec(
                endpoint=settings.arcgis_phoenix_sla_url,
                platform="arcgis",
                watermark_col="ISSUED_DATE",
                id_keys=["NAME", "ID", "OBJECTID"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                expected_cadence_days=7,
                oid_field="OBJECTID",
                max_record_count=2000,
                order_by="ISSUED_DATE DESC",
                needs_geocode=False,
                field_map=PHOENIX_SLA_FIELD_MAP,
            ),
        },
    ),
```

### 3. `apps/api/src/spatial/cities/__init__.py`

Export block (same four constants + `is_in_phoenix_metro`):

```python
from src.spatial.cities.phoenix import (
    PHOENIX_DIVISION_BBOXES,
    PHOENIX_DIVISIONS,
    PHOENIX_METRO_BBOX,
    PHOENIX_SUBMARKETS,
    is_in_phoenix_metro,
)
```

and the matching `__all__` names.

### 4. `METRO_META` in `apps/api/src/serving/dashboard.py` **and** byte-synced `apps/dashboard/public/index.html`

```
phoenix: { name: 'Phoenix / Maricopa County' }
```

Run `python scripts/export_dashboard.py` (or equivalent) so the worker static
copy matches `get_dashboard_html()`. `SUPPORTED_CITIES` is derived from
`CityId`, so snapshot-export list coverage is automatic once the enum lands.
Grid-tile coverage is exercised by `TestSnapshotWiring` against a stub engine.

### 5. Do not register

- 311 / myPHX311 (Dynamics 365 portal, no bulk REST)
- Deeds / Maricopa sales affidavits (no queryable watermark this probe)
- `Public/LIQUOR_RACMap` (no date column)
- `ShapePHX/ShapePHXPermitsPoints/MapServer/0` (frozen 2022-06-29)
- CKAN `phoenix-az-building-permit-data` SOCDS aggregate
- `FeedType.STR` (STR is the SLA)

### 6. Companion polling follow-on

Scheduler does not poll `companion_endpoints` today. ShapePHX `_DL` ingest is
a follow-on: either grow companion polling (watermark `PERMIT_ISSUE_DATE`,
same `PHOENIX_PERMITS_FIELD_MAP` fallbacks) or accept Planning_Permit-only
permit ingest until then.
