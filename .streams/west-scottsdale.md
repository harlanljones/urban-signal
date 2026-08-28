# Stream log — west-scottsdale — 2026-08-28

## Claim

- **Stream id:** west-scottsdale (US-227, West-region metro-expansion wave, branch chore/restore-metros-and-columbus)
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/scottsdale.py
  - apps/api/src/producers/field_maps_scottsdale.py
  - apps/api/tests/unit/test_producers_scottsdale.py
- **Spine files I expect to need:** NONE

## Intent

Live-probe Scottsdale, AZ official open-data feeds (data.scottsdaleaz.gov, ArcGIS/Socrata),
verify 1-4 of them (permits / 311 / business licenses / deeds), then build the leaf trio
(city module, field maps, producer tests) for verified feeds only. Report registry/config
registration details for a spine hold; no spine edits, no commits, no Linear updates.

## Decisions

- 2026-08-28 — Ticket body says Socrata (data.scottsdaleaz.gov); probing live, will also test ArcGIS REST fallback. Maricopa County recorder to be probed for deeds (partial registration acceptable without deeds).
- 2026-08-28 — TICKET BODY WRONG about platform: data.scottsdaleaz.gov is an **ArcGIS Hub Open Data** site (`/api/catalog/v1` 404s "Cannot GET"; homepage loads hubcdn.arcgis.com assets). The real data host is **maps.scottsdaleaz.gov/arcgis/rest/services** (ArcGIS Server **10.6**). No Socrata exists.
- 2026-08-28 — Candidates: OpenData_Tabular/12 Building Permits (TABLE, 288,121 rows, maxRecordCount 1000, supportsPagination), OpenData_Events/3 twin point layer (store SR WKID 2868), OpenData_Tabular/6 Business Licenses (TABLE, 19,944 rows, OID=ESRI_OID), OpenData_Events/1 Code Violations (18,470), OpenData_Events/2 Graffiti (907).
- 2026-08-28 — PERMITS VERIFIED: newest IssueDate 2026-08-21T00:00:00Z (permit_id 324348, 'SFR-CUSTOM IN SUBDIVISION'). 52.6% (151,704/288,121) carry native WGS84 Latitude/Longitude attributes (e.g. 33.6564984, -111.90865983); newest-window rows are null-lat → ADR-0004 geocode on `Address`. **NaN trap**: events-layer twin returns geometry `{'x':'NaN','y':'NaN'}` for null-geom features, which ArcGISClient._flatten_feature lifts as strings → register the TABLE (no geometry), map Latitude/Longitude attributes, geocode fallback on Address.
- 2026-08-28 — SLA VERIFIED: Business Licenses, 19,944 rows (19,922 guarded). **Future sentinels**: BusinessStartDate max = year 5202 (epoch 102014035200000, 'BOOTS AND BEER', Inactive) + forward-dated 2027-01-01 / 2026-11-19 / 2026-11-01 Actives → where guard `BusinessStartDate <= CURRENT_TIMESTAMP` (verified live). outStatistics max on the column 400s (epoch overflow) — newest read via orderByFields DESC: **2026-08-21T00:00:00Z** (APEX APPLIANCES, AcctNum 2045469). Address-only (ServAddrComp/ServCityStateZipComp) → needs_geocode.
- 2026-08-28 — 311-family REJECT per repo discipline: only Code Violations/Graffiti exist as complaint feeds; Lynchburg/Wichita precedent (city_registry.py:3745, field_maps_lynchburg.py) says code-enforcement is NOT COMPLAINTS_311. No true 311 SR feed (My_Services = trash/recycling schedules).
- 2026-08-28 — DEEDS REJECT: recorder.maricopa.gov (+ /recdocdata) 403 anonymous; no bulk API. Partial registration (permits + SLA) without deeds.
- 2026-08-28 — Feed set: PERMITS + SLA (2-feed partial).

## Current step

COMPLETE — leaf trio verified Phase B. All 52 unit tests pass, ruff clean, interlock 24 passed.

## Next step

None (leaf complete). Spine hold creates CityId.SCOTTSDALE + REGISTRY entry + dashboard wiring.

## Outcome

**ACCEPT — 2-feed partial metro.** Scottsdale, AZ (West region) is ready for spine registration.

Verified feeds:
- **PERMITS** — `OpenData_Tabular/MapServer/12` (standalone TABLE, 288,121 rows, 52.6% native WGS84 lat/lng attributes, geocode supplement on Address; watermark `IssueDate`, newest 2026-08-21T00:00:00Z; cadence 14d)
- **SLA** — `OpenData_Tabular/MapServer/6` (standalone TABLE, 19,944 rows guarded, `BusinessStartDate <= CURRENT_TIMESTAMP` where guard; address-only with geocode supplement; watermark `BusinessStartDate`, newest 2026-08-21T00:00:00Z; cadence 14d)

Rejected feeds:
- 311-family — code enforcement layers only (Code Violations, Graffiti), NOT COMPLAINTS_311 per Lynchburg/Wichita precedent
- Deeds — recorder.maricopa.gov returns 403 to anonymous probes

Platform: ArcGIS Server 10.6 on maps.scottsdaleaz.gov (NOT Socrata as the ticket claimed; data.scottsdaleaz.gov is ArcGIS Hub)

## Spine delta

The spine hold (forbidden in this leaf) must add:

### CityId member
```python
SCOTTSDALE = "scottsdale"
```

### Aliases (in ALIASES dict)
```python
"scottsdale": CityId.SCOTTSDALE,
"scottsdale az": CityId.SCOTTSDALE,
"scottsdale, az": CityId.SCOTTSDALE,
```

### Registry entry (in `_METRO_REGISTRY` or `_build_registry`)

```python
CityId.SCOTTSDALE: CityRegistration(
    city_id=CityId.SCOTTSDALE,
    name="Scottsdale, AZ",
    state="AZ",
    center={"lat": 33.4942, "lng": -111.9261},  # Old Town anchor
    metro_bbox=SCOTTSDALE_METRO_BBOX,
    division_bboxes=SCOTTSDALE_DIVISION_BBOXES,
    submarkets=SCOTTSDALE_SUBMARKETS,
    divisions=SCOTTSDALE_DIVISIONS,
    job_suffix="scottsdale",
    datasets={
        FeedType.PERMITS: DatasetSpec(
            endpoint="https://maps.scottsdaleaz.gov/arcgis/rest/services/OpenData_Tabular/MapServer/12",
            platform="arcgis",
            watermark_col="IssueDate",
            id_keys=["PermitNumber", "permit_id"],
            topic=settings.topic_permits,
            interval_seconds=300.0,
            producer_key="permits",
            oid_field="permit_id",
            max_record_count=1000,
            order_by="IssueDate DESC",
            expected_cadence_days=14,
            needs_geocode=True,
            geocode_context="Scottsdale, AZ",
            field_map=PERMITS_FIELD_MAP,
        ),
        FeedType.SLA: DatasetSpec(
            endpoint="https://maps.scottsdaleaz.gov/arcgis/rest/services/OpenData_Tabular/MapServer/6",
            platform="arcgis",
            watermark_col="BusinessStartDate",
            id_keys=["AcctNum", "OBJECTID"],
            topic=settings.topic_sla,
            interval_seconds=600.0,
            producer_key="sla",
            oid_field="OBJECTID",
            max_record_count=1000,
            order_by="BusinessStartDate DESC",
            expected_cadence_days=14,
            needs_geocode=True,
            geocode_context="Scottsdale, AZ",
            where="BusinessStartDate <= CURRENT_TIMESTAMP",
            field_map=SLA_FIELD_MAP,
        ),
    },
)
```

### Config endpoints (in `src/config.py` section "West-region city endpoints")
- `SCOTTSDALE_PERMITS_ENDPOINT` = `"https://maps.scottsdaleaz.gov/arcgis/rest/services/OpenData_Tabular/MapServer/12"`
- `SCOTTSDALE_SLA_ENDPOINT` = `"https://maps.scottsdaleaz.gov/arcgis/rest/services/OpenData_Tabular/MapServer/6"`
- `SCOTTSDALE_SLA_WHERE` = `"BusinessStartDate <= CURRENT_TIMESTAMP"`

### METRO_META entry (in `apps/dashboard/src/index.ts` or equivalent)
```typescript
{ city: "scottsdale", name: "Scottsdale, AZ", region: "west" },
```

### Dashboard wiring
Per the city-registration rule: METRO_META entry + snapshot export coverage + res-5 grid-tile coverage in published manifest + byte-synced `apps/dashboard/public/index.html` static copy. Interlock gate `TestDashboardWiring` and `TestSnapshotWiring` will fail until this is wired.

### Recommended Linear comment
```
Spine hold: register CityId.SCOTTSDALE + REGISTRY entry + ALIASES + config endpoints + METRO_META + dashboard byte-sync.

Leaf trio verified (US-227):
- apps/api/src/spatial/cities/scottsdale.py
- apps/api/src/producers/field_maps_scottsdale.py
- apps/api/tests/unit/test_producers_scottsdale.py

52/52 unit tests pass, ruff clean, interlock 24/24. Two feeds: PERMITS (OpenData_Tabular/12) and SLA (OpenData_Tabular/6). 311-family and deeds rejected per repo discipline. Platform is ArcGIS Server 10.6 (maps.scottsdaleaz.gov), NOT Socrata.

See .streams/west-scottsdale.md for full probe evidence.
```