# Stream log — west-billings — 2026-08-28

## Claim

- **Stream id:** `west-billings`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/billings.py`
  - `apps/api/src/producers/field_maps_billings.py`
  - `apps/api/tests/unit/test_producers_billings.py`
- **Spine files I expect to need:** NONE

## Intent

Onboard Billings, MT as a new metro area by live-verifying its official
municipal open-data feeds (permit/311/licenses/deeds — crime only with
coordinates/address per ADR-0004), then building a leaf producer (bbox,
divisions, FEED_SPECS, field maps, tests) without touching spine files.

## Decisions

- 2026-08-28 — Working tree sits on `main` with concurrent agents' uncommitted
  changes (incl. spine files). `chore/restore-metros-and-columbus` cannot be
  checked out without clobbering that in-flight work. Decision: stay on `main`,
  create ONLY my three new leaf files, never commit, never touch shared files.
- 2026-08-28 — Ticket US-234 hints `billings.opendata.arcgis.com` (ArcGIS Hub).
  Must live-probe; ticket body is thin.
- 2026-08-28 — PHASE A COMPLETE. Two verified feeds:

  **PERMITS** (81,016 rows, MapServer/0 on billingsgis.com):
    - Endpoint: ``https://billingsgis.com/arcgis_public/rest/services/ArcOnline_Public/BuildingPermits_CodeViolations_EXT/MapServer/0``
    - Watermark: ``Issue_Date`` (esriFieldTypeDate, newest 2026-08-11)
    - Native WGS84 in both geometry AND Latitude/Longitude attribute columns
    - Issue_Date is NOT where-clause queryable (ArcGIS 400) — orderByFields only
    - Duplicate Building_Permit_Num rows exist — OBJECTID secondary id_key
    - PII: Owner, Owner_Address, Owner_City/State/Zip, Contractor, Contractor_Num, Entered_By
    - needs_geocode: false

  **311/Service Requests** (245 rows, FeatureServer on services6.arcgis.com/rCC3yWJa2mjYtKDP):
    - Endpoint: ``https://services6.arcgis.com/rCC3yWJa2mjYtKDP/arcgis/rest/services/Requests_public_00e63199176f44b788fd43684476713d/FeatureServer/0``
    - Watermark: ``created_date`` (esriFieldTypeDate, newest 2026-08-27 — probe-day fresh)
    - Native WGS84 geometry, fields: reqid, reqcategory, reqtype, status, created_date, resolutiondt, details, locdesc
    - PII: pocfirstname, poclastname, created_user
    - needs_geocode: false

  **NOT VERIFIED**: SLA none, deeds (Yellowstone County unreachable), crime (stale 2024/2023 — not registering).

  Billings is a TWO-FEED PARTIAL metro.

## Current step

Phase B done — all tests pass. Finalizing stream log.

## Next step

Spine hold (by orchestrator): register CityId.BILLINGS + REGISTRY entry +
ALIASES + METRO_META + config endpoint fields + dashboard byte-sync.

## Outcome

**Feeds verified (2):**
- PERMITS: BuildingPermits_CodeViolations_EXT MapServer/0 (81,016 rows)
- 311: Requests_public FeatureServer/0 (245 rows)

**Feeds rejected (3):**
- SLA: none found in org
- DEEDS: Yellowstone County site unreachable, no AGOL org found
- CRIME: has coordinates but stale (2024, 2023) — not registering

**Watermarks:**
- PERMITS: Issue_Date newest 1786437732857 = 2026-08-11
- 311: created_date newest 1787808604235 = 2026-08-27

**Tests:** 40 passed (billings suite), 24 interlock passed, ruff clean.

## Spine delta

**CityId member:** `BILLINGS = "billings"`

**Aliases:** `"billings"`, `"billings_mt"`, `"billings-mt"`, `"billings mt"`,
`"billings_montana"`, `"billings montana"`, `"by"`

**Registry entry:**
```python
CityId.BILLINGS: CityRegistration(
    city_id=CityId.BILLINGS,
    name="Billings",
    state="MT",
    center={"lat": 45.7833, "lng": -108.5007},
    metro_bbox=BILLINGS_METRO_BBOX,
    division_bboxes=BILLINGS_DIVISION_BBOXES,
    submarkets=BILLINGS_SUBMARKETS,
    divisions=BILLINGS_DIVISIONS,
    job_suffix="billings",
    datasets={
        FeedType.PERMITS: DatasetSpec(
            endpoint=settings.billings_permits_url,
            platform="arcgis",
            watermark_col="Issue_Date",
            id_keys=["Building_Permit_Num", "OBJECTID"],
            topic=settings.topic_permits,
            interval_seconds=300.0,
            producer_key="permits",
            expected_cadence_days=1,
            needs_geocode=False,
            geocode_context="Billings, MT",
            oid_field="OBJECTID",
            max_record_count=2000,
            order_by="Issue_Date DESC",
            field_map=PERMITS_FIELD_MAP,
        ),
        FeedType.COMPLAINTS_311: DatasetSpec(
            endpoint=settings.billings_311_url,
            platform="arcgis",
            watermark_col="created_date",
            id_keys=["reqid", "OBJECTID"],
            topic=settings.topic_311,
            interval_seconds=300.0,
            producer_key="311",
            expected_cadence_days=1,
            needs_geocode=False,
            geocode_context="Billings, MT",
            oid_field="OBJECTID",
            max_record_count=2000,
            order_by="created_date DESC",
            field_map=BILLINGS_311_FIELD_MAP,
        ),
    },
)
```

**Config endpoint fields (in `src/config.py`):**
```python
billings_permits_url: str = Field(
    default="https://billingsgis.com/arcgis_public/rest/services/"
    "ArcOnline_Public/BuildingPermits_CodeViolations_EXT/MapServer/0"
)
billings_311_url: str = Field(
    default="https://services6.arcgis.com/rCC3yWJa2mjYtKDP/arcgis/rest/services/"
    "Requests_public_00e63199176f44b788fd43684476713d/FeatureServer/0"
)
```
