# Stream log — west-vancouver_wa — 2026-08-28

## Claim

- **Stream id:** `west-vancouver_wa`
- **Leaf files created:**
  - `apps/api/src/spatial/cities/vancouver_wa.py`
  - `apps/api/src/producers/field_maps_vancouver_wa.py`
  - `apps/api/tests/unit/test_producers_vancouver_wa.py`
  - `.streams/west-vancouver_wa.md`
- **Spine files expected to need:** NONE (leaf-only stream)

## Intent

Register Vancouver, WA as a new metro area by live-probing
vancouverwa.opendata.arcgis.com (ArcGIS Hub) for 1-4 verified official feeds
(permits / 311 / business licenses / deeds), then building the leaf files:
`cities/vancouver_wa.py` (bbox + evidenced divisions/submarkets + FEED_SPECS),
`field_maps_vancouver_wa.py` (per-feed field maps), and
`tests/unit/test_producers_vancouver_wa.py` (spine-stable, byte-verbatim live
fixtures through the real client path). If no verifiable official feed exists,
REJECT with evidence — never use a stale mirror.

## Decisions

- 2026-08-28 — The ticket's `vancouverwa.opendata.arcgis.com` domain is a
  **decommissioned** legacy Open Data site ("This site is no longer
  supported"). The real open-data surface is the City of Vancouver, WA AGOL
  org (`CityOfVancouverGISAdmin`, org server
  `services.arcgis.com/oNvpY90qsPDizwkN`).
- 2026-08-28 — **PERMITS VERIFIED (Tier 1)**: `Permits_and_Code_Enforcement_Data_(public_view)`
  FeatureServer/0 "Permit Data" on the city's AGOL org. 44,744 total rows;
  44,742 with `csm_issued_date <= CURRENT_TIMESTAMP` (2 future sentinels,
  both Closed/ELECTRICAL, dated 2039/2049, excluded via where guard +
  scheduler US-111 future guard). Native point geometry via outSR=4326 is
  correct (extent -122.768..-122.464, 45.579..45.702); Y/X *attributes* are
  WA State Plane South feet (≈1.08e6 / 1.1e5) — never mapped. Watermark
  `csm_issued_date` is esriFieldTypeDate, where-clause queryable with ISO
  strings (NOT an ANSI_DATE_LITERAL_HOSTS member). Newest legit watermark
  2026-08-15T08:16:03+00:00 (`1786781763000`). PRIM_ADDR address fallback,
  0 nulls → needs_geocode=True. id_keys CSM_CASENO/sn/OBJECTID.
- 2026-08-28 — **Development-projects CMI layer NOT registered**:
  `Development_Projects_Mapped_WFL1` FeatureServer/3 (5,779 rows) is
  verified but carries a mixed-CRS trap — outSR=4326 geometry is garbage on
  ~4,620/5,779 rows (declared wkid 102100 but raw coords are ~-1.4e7 Web
  Mercator; native Latitude/Longitude columns are correct) — AND it would
  collide with the permits job name (same FeedType.PERMITS + city_id →
  `get_job_name` collision). Documented as evidence + Tier-3 companion.
- 2026-08-28 — **311 NOT available**: Street Lights (Open Service Requests)
  and Facility Inspection Service Requests (IPS) live on
  `gis.cityofvancouver.us` which requires tokens (public view only); AGOL
  items point at a token-gated server.
- 2026-08-28 — **DEEDS NOT available**: Clark County has no machine-readable
  deed feed (LandmarkWeb e-docs is a web app; taxlots are CAMA). Partial
  without deeds is fine per ticket.
- 2026-08-28 — **SLA NOT available**: no public city business-license feed
  on the hub; WA L&I/LCB state registries would be spine config companions
  (out of leaf scope).
- 2026-08-28 — **ONE-FEED PARTIAL metro** (Greenville precedent): PERMITS
  only. Divisions (6) from official NeighborhoodsCoV polygon centroids.
  Submarkets (13) from official neighborhood names + CMI Neighborhood
  evidence. Felida excluded (unincorporated, 1 permit row north of 45.70).

## Current step

Leaf files built and verified (46/46 tests pass, ruff clean, interlock gate 24/24 pass).

## Next step

Report to spine ticket. No spine edits from this leaf.

## Outcome

**Feeds verified:**
1. PERMITS — `Permits_and_Code_Enforcement_Data_(public_view)/FeatureServer/0`
   - Endpoint: `https://services.arcgis.com/oNvpY90qsPDizwkN/arcgis/rest/services/Permits_and_Code_Enforcement_Data_(public_view)/FeatureServer/0`
   - Platform: arcgis
   - 44,744 rows (44,742 with sentinel guard)
   - Watermark: `csm_issued_date` (esriFieldTypeDate, where-queryable ISO)
   - Newest: 2026-08-15T08:16:03+00:00 (1786781763000)
   - 90d count: 2,812; since 2026-01-01: 8,010
   - Geometry: native outSR=4326 point (correct); Y/X = WA State Plane feet (never map)
   - Address: PRIM_ADDR (0 nulls) → needs_geocode=True
   - Future sentinels: 2 (2039/2049) → excluded via `where=csm_issued_date <= CURRENT_TIMESTAMP`

**Rejected (with evidence):**
- 311: token-gated internal server (gis.cityofvancouver.us)
- SLA: no public city feed (WA L&I/LCB state registries = spine scope)
- Deeds: Clark County LandmarkWeb = web app, no API
- CMI development projects: mixed-CRS geometry trap + job-name collision

**Watermarks:** `csm_issued_date: 1786781763000` (2026-08-15T08:16:03+00:00)

**Tests:** 46/46 pass. Ruff: clean. Interlock gate: 24/24 pass.

## Spine delta

When the spine hold opens (separate ticket), the following additions are needed:

### CityId member
```python
VANCOUVER_WA = "vancouver_wa"
```

### Aliases
```python
"vancouver_wa": CityId.VANCOUVER_WA,
"vancouver-wa": CityId.VANCOUVER_WA,
"vancouver wa": CityId.VANCOUVER_WA,
"vancouver_washington": CityId.VANCOUVER_WA,
"vancouver washington": CityId.VANCOUVER_WA,
```

### Registry entry
```python
CityId.VANCOUVER_WA: CityRegistration(
    city_id=CityId.VANCOUVER_WA,
    name="Vancouver",
    state="WA",
    center={"lat": 45.6282, "lng": -122.6785},
    metro_bbox=VANCOUVER_WA_METRO_BBOX,
    division_bboxes=VANCOUVER_WA_DIVISION_BBOXES,
    submarkets=VANCOUVER_WA_SUBMARKETS,
    divisions=VANCOUVER_WA_DIVISIONS,
    job_suffix="vancouver_wa",
    datasets={
        FeedType.PERMITS: DatasetSpec(
            endpoint=settings.arcgis_vancouver_wa_permits_url,
            platform="arcgis",
            watermark_col="csm_issued_date",
            id_keys=["CSM_CASENO", "sn", "OBJECTID"],
            topic=settings.topic_permits,
            interval_seconds=300.0,
            producer_key="permits",
            expected_cadence_days=1,
            needs_geocode=True,
            geocode_context="Vancouver, WA",
            oid_field="OBJECTID",
            max_record_count=2000,
            order_by="csm_issued_date DESC",
            where="csm_issued_date <= CURRENT_TIMESTAMP",
            field_map=PERMITS_FIELD_MAP,
        ),
    },
)
```

### Config endpoint
```python
arcgis_vancouver_wa_permits_url: str = Field(
    default="https://services.arcgis.com/oNvpY90qsPDizwkN/arcgis/rest/services/"
    "Permits_and_Code_Enforcement_Data_(public_view)/FeatureServer/0",
)
```

### Dashboard wiring
- `METRO_META` entry for `vancouver_wa` with deep link `?city=vancouver_wa`
- Snapshot export coverage
- Res-5 grid-tile coverage in published manifest
- Byte-sync `apps/dashboard/public/index.html`

**Recommended Linear comment:** "Vancouver, WA verified as ONE-FEED PARTIAL metro (PERMITS only). Leaf files built at `apps/api/src/spatial/cities/vancouver_wa.py`, `apps/api/src/producers/field_maps_vancouver_wa.py`, `tests/unit/test_producers_vancouver_wa.py`. 46/46 tests pass. Ready for spine hold."

### REJECT recommendation
None — the permits feed is a strong Tier-1 registration. The rejections (311, SLA, deeds, CMI) are documented with evidence, not a reason to reject the whole metro.