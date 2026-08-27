# Stream log — city-albuquerque — 2026-08-27

Phase-2 leaf stream for Linear US-205: Albuquerque, NM partial registration
(PERMITS CSV only). Spine is serial after this stream; do not edit spine
files here.

## Claim

- **Stream id:** `city-albuquerque`
- **Leaf files I will create/edit:**
  - `.streams/city-albuquerque.md` (this file)
  - `apps/api/src/spatial/cities/albuquerque.py` (NEW)
  - `apps/api/src/producers/field_maps_albuquerque.py` (NEW)
  - `apps/api/tests/unit/test_producers_albuquerque.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html`
  - `apps/api/src/producers/dob_permits_producer.py` (compose_permit_address
    hook — documented, not applied)

## Intent

Leaf-complete a PARTIAL Albuquerque metro from
`docs/research/wave-3-probe-albuquerque.md`: daily CSV permits dump only.
Do not register the frozen AGIS FeatureServer, 311 CRM, frozen business
registration dump, or deeds. Tests pass without `CityId.ALBUQUERQUE`.
Record an exact spine delta.

## Decisions

- 2026-08-27 ~13:00 PT — Orchestrator dispatched this leaf after Honolulu
  and Orlando spines landed. Probe US-205 is Done / partial ready.
  311 stays T3 (CRM not queryable) unless a live re-probe of the MapServer
  contradicts the probe file — document, do not register 311 in this stream.
- 2026-08-27 ~13:10 PT — CSVClient `_normalize_header` collapses camelCase
  (`IssueDate` → `issuedate`, `ApplicationPermitNumber` →
  `applicationpermitnumber`). Field map lists BOTH original and normalized
  spellings. `csv_client.py` is not edited (St. Louis owns zip-member work).
- 2026-08-27 ~13:15 PT — CSVClient has no `IN` matcher; unknown clauses are
  a silent no-op. `Status IN ('Issued','Complete')` would ingest Expired.
  Spine `where` is `Status NOT IN ('Expired')` (drops the Expired majority;
  Issued + Complete + a small remainder pass).
- 2026-08-27 ~13:20 PT — Address is split across SiteNumber / SiteStreet /
  SiteStreetType / SiteStreetDirectional + SiteZip. `first_mapped` returns
  only the house number (`"1017"`, length < 6) so raw rows drop at
  `geocode_row_if_declared`. Leaf helper `compose_permit_address` joins to
  `1017 22ND ST NW, Albuquerque, NM 87104`. Spine producer must call it
  (same-hold additive edit to `dob_permits_producer.py`).
- 2026-08-27 ~13:25 PT — `IssueDate` `YYYYMMDD` already parses via Python
  3.11 `datetime.fromisoformat` (first branch of `_parse_datetime`). No
  format-tuple spine edit needed. Watermark remains `watermark_type=text`,
  `watermark_format=%Y%m%d`, `watermark_exclude=["20261224"]`.
- 2026-08-27 ~13:30 PT — Geography: City of Albuquerque / inner Bernalillo,
  `city_id="albuquerque"`, center 35.0844, -106.6504, six divisions,
  containment-sane. `needs_geocode=True`, `geocode_context="Albuquerque, NM"`.
  No new FeedType. Do not register AGIS `City_Building_Permits`.
- 2026-08-27 ~13:40 PT — Leaf tests green:
  `apps/api/.venv/bin/pytest tests/unit/test_producers_albuquerque.py -q`
  → **39 passed**. No `CityId.ALBUQUERQUE`. No spine files touched.

## Current step

Spine applied 2026-08-27 ~13:30 PT (orchestrator). PERMITS CSV only.
`compose_permit_address` hooked in `dob_permits_producer.py`. Interlock
**22 passed**. Leaf tests **39 passed**.

## Next step

Linear US-205 Done. No further code in this stream.

---

## Exact spine delta (DO NOT APPLY IN THIS STREAM)

Copy-paste for the serial interlock hold. **PARTIAL city: PERMITS CSV only.**
Do not add 311 / SLA / DEEDS. Do not point PERMITS at the frozen AGIS
`City_Building_Permits` FeatureServer (max DateIssued 2025-01-16).

Other wave-3 cities may land first; insert after the current last CityId
(miami_dade as of this leaf).

### 1. `apps/api/src/config.py`

Add after the Orlando (or current last-city) settings:

```python
    # Albuquerque / Bernalillo County (US-205): daily CABQ building-permits
    # CSV dump. Address-only (ADR 0004). AGIS City_Building_Permits is frozen
    # (max DateIssued 2025-01-16) and must not be wired.
    csv_albuquerque_permits_endpoint: str = Field(
        default="https://data.cabq.gov/business/buildingpermits/BuildingPermitsCABQ-en-us.csv",
        description="Albuquerque building permits daily CSV dump (US-205)",
    )
```

### 2. `apps/api/src/spatial/city_registry.py`

**Import** (with the other field-map / city imports):

```python
from src.producers.field_maps_albuquerque import FIELD_MAP as ALBUQUERQUE_FIELD_MAP
from src.spatial.cities.albuquerque import (
    ALBUQUERQUE_DIVISION_BBOXES,
    ALBUQUERQUE_DIVISIONS,
    ALBUQUERQUE_METRO_BBOX,
    ALBUQUERQUE_SUBMARKETS,
)
```

**Enum** — add after the current last member:

```python
    ALBUQUERQUE = "albuquerque"
```

**ALIASES** — add before the closing `}` of `ALIASES`:

```python
    # Albuquerque / Bernalillo County, NM
    "albuquerque": CityId.ALBUQUERQUE,
    "albuquerque_nm": CityId.ALBUQUERQUE,
    "albuquerque nm": CityId.ALBUQUERQUE,
    "abq": CityId.ALBUQUERQUE,
    "bernalillo": CityId.ALBUQUERQUE,
    "bernalillo_county": CityId.ALBUQUERQUE,
    "bernalillo county": CityId.ALBUQUERQUE,
```

**REGISTRY** — append before the closing `}` of `REGISTRY`. Permits only:

```python
    CityId.ALBUQUERQUE: CityRegistration(
        city_id=CityId.ALBUQUERQUE,
        name="Albuquerque / Bernalillo County",
        state="NM",
        center={"lat": 35.0844, "lng": -106.6504},
        metro_bbox=ALBUQUERQUE_METRO_BBOX,
        division_bboxes=ALBUQUERQUE_DIVISION_BBOXES,
        submarkets=ALBUQUERQUE_SUBMARKETS,
        divisions=ALBUQUERQUE_DIVISIONS,
        job_suffix="albuquerque",
        # Partial registration like Boise / Austin / LA: PERMITS CSV only.
        # data.cabq.gov daily dump is live (newest non-future IssueDate
        # 2026-08-26). AGIS City_Building_Permits is frozen; 311 CRM is not
        # anonymously queryable; business-registration dump is frozen; no
        # deed transaction stream. CSVClient has no IN predicate — where is
        # NOT IN Expired (not Status IN Issued/Complete).
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.csv_albuquerque_permits_endpoint,
                platform="csv",
                watermark_col="IssueDate",
                id_keys=["ApplicationPermitNumber"],
                topic=settings.topic_permits,
                interval_seconds=1800.0,
                producer_key="permits",
                expected_cadence_days=1,
                watermark_type="text",
                watermark_format="%Y%m%d",
                watermark_exclude=["20261224"],
                where="Status NOT IN ('Expired')",
                needs_geocode=True,
                geocode_context="Albuquerque, NM",
                field_map=ALBUQUERQUE_FIELD_MAP["permits"],
            ),
        },
    ),
```

### 3. `apps/api/src/spatial/cities/__init__.py`

Import (after the current last city):

```python
from src.spatial.cities.albuquerque import (
    ALBUQUERQUE_DIVISION_BBOXES,
    ALBUQUERQUE_DIVISIONS,
    ALBUQUERQUE_METRO_BBOX,
    ALBUQUERQUE_SUBMARKETS,
    is_in_albuquerque_metro,
)
```

`__all__` append:

```python
    "ALBUQUERQUE_METRO_BBOX",
    "ALBUQUERQUE_DIVISION_BBOXES",
    "ALBUQUERQUE_DIVISIONS",
    "ALBUQUERQUE_SUBMARKETS",
    "is_in_albuquerque_metro",
```

### 4. `apps/api/src/serving/dashboard.py` METRO_META **and**
   `apps/dashboard/public/index.html` (byte-sync; city-registration rule)

```javascript
      albuquerque: { name: 'Albuquerque / Bernalillo County' },
```

Must land in **both** files in the same spine hold. Snapshot export coverage
and res-5 grid-tile coverage in the published manifest are also required
before the gate is green — those are post-ingest, not this leaf.

### 5. Same-hold: `apps/api/src/producers/dob_permits_producer.py`

`first_mapped` on a raw CABQ row returns only `sitenumber` (`"1017"`), which
is below `geocode_row_if_declared`'s length-6 floor — every row drops.
Before the geocode call, compose the address:

```python
            if resolved_city == "albuquerque":
                from src.spatial.cities.albuquerque import compose_permit_address
                composed = compose_permit_address(row)
                if composed:
                    row = {**row, "address_street": composed}
```

Insert after `field_map = resolve_field_map(...)` (or immediately before the
`addr_candidate = first_mapped(..., "address_street")` block). Additive,
Albuquerque-only. Do not skip silently — live geocoding depends on it.

`YYYYMMDD` `IssueDate` already parses via `datetime.fromisoformat`; do **not**
add `"%Y%m%d"` to `_parse_datetime` unless a later city needs the strptime
fallback.

No new `FeedType`. Shared `field_maps.py` does not need an edit
(`resolve_field_map` reads `spec.field_map`). Do not edit `csv_client.py`.
