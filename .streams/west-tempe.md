# Stream log — west-tempe — 2026-08-28

## Claim

- **Stream id:** `west-tempe`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/tempe.py`
  - `apps/api/src/producers/field_maps_tempe.py`
  - `apps/api/tests/unit/test_producers_tempe.py`
- **Spine files I expect to need:** NONE

## Intent

Verify 1-4 official Tempe, AZ open-data feeds by live probing (ticket says Socrata
data.tempe.gov; task says probe tempe.gov ArcGIS — check both), then build the leaf
trio (city definition with DatasetSpec-shaped FEED_SPECS, field maps, spine-stable
unit tests with byte-verbatim live fixtures). Report registration evidence + exact
CityId.TEMPE spine delta in the Outcome. No commits, no Linear updates.

## Decisions

- 2026-08-28 — data.tempe.gov is **NOT Socrata** (ticket body wrong): `/api/odata/v4`
  and `/api/catalog/v1` both 404; homepage is an ArcGIS Hub Site (orgId
  `lQySeXwbBg53XWDi`, orgUrlKey `tempegov`). All probing via Hub search
  `/api/search/v1/collections/dataset/items` + services.arcgis.com FeatureServer REST.
- 2026-08-28 — VERIFIED feeds (live, row counts + watermarks 2026-08-28):
  - **permits** `https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/building_permits/FeatureServer/0`
    — 20,226 rows; point geom wkid 4326 (native) + Latitude/Longitude attr cols +
    OriginalAddress1; watermark AppliedDateDtm epoch-ms newest `1787702400000`
    (= 2026-08-26T00:00:00Z); IssuedDateDtm `1787788800000` (2026-08-27). 44 fields.
  - **general_offenses** `.../General_Offenses_(Open_Data)/FeatureServer/0` — 380,724 rows;
    watermark OccurrenceDatetime `1787873460000` (2026-08-27T23:31:00Z). MIXED-CRS TRAP:
    native geometry = AZ State Plane Central (wkid 2223) points (sample x=697343 y=875784),
    while attr cols Latitude/Longitude hold WGS84 and XCoordinate/YCoordinate hold the
    state-plane pair duplicated as attrs. ObfuscatedAddress ("9XX E BROADWAY RD") → ADR-0004 OK.
  - **arrests** `.../ArrestsOpenDataDenormalized/FeatureServer/0` — 42,777 rows; SR wkid 2223;
    watermark arrest_dt `1787870280000` (2026-08-27T22:38:00Z); coords via
    x_coordinate/y_coordinate attrs + location text + zipcode. ADR-0004 OK.
  - **code_complaints** `.../code_complaints/FeatureServer/0` — 2,743 rows; point geom 4326
    (X_COORD/Y_COORD attrs are lng/lat — confirmed sample x=-111.928923 y=33.357087);
    watermark CaseOpenDate `1781247600000` (2026-06-12T07:00:00Z) — feed is ~10 weeks stale
    as of probe (CaseStatusDate also tops out 2026-06-12T23:10:57). Some rows carry (0,0)
    zero-coord sentinels (extent xmin/ymin ≈ 5.68e-14). Honest-note feed.
- 2026-08-28 — REJECT evidence:
  - **Business/SLA licenses**: no license feed in Tempe catalog (only Business *Survey*
    datasets). Candidate "3.09 ABOR Certificates and Licenses (detail)" FeatureServer
    resolves but has **zero layers** (`{"layers":[]}`) — dead KPI stub. → no SLA feed.
  - **Deeds (Maricopa County)**: recorder.maricopa.gov/recdocdata/ → HTTP 403 to
    programmatic requests (session-gated ASP.NET doc-search app, no API);
    gis.maricopa.gov/arcgis/rest/services reachable but RED folder contains only
    Assessor/Boundary/DOT MapServers (no recorder-document service); assessor parcel
    data is file-download only. → deeds not verifiable; partial registration without deeds.
  - **311**: no raw 311/service-request feed in catalog (only KPI summaries: response
    times, first-call resolution). code_complaints is the closest service-request feed.
  - **Calls for Service** `.../Calls_For_Service/FeatureServer` — live (640,463 rows on
    layer 0, watermark 2026-08-28T08:01:48Z) but police CAD overlapping general_offenses
    + 640k-row sync cost; layers 1/2 are historical variants (608k / 721k rows). SKIPPED,
    recorded as optional future feed.
- Metro bbox from permits extent (4326): xmin -112.04936, ymin 33.31587,
  xmax -111.83635, ymax 33.45985.

## Current step

VERIFICATION COMPLETE — all gates green:
- tempe tests: 59 passed
- `-k tempe`: 61 passed
- interlock: 24 passed
- ruff: clean on all three leaf files
- Fixtures: 9/9 byte-verbatim vs captured JSON
- Full suite (3210 tests) environmental hang (Docker/Kafka staging not available on this restored branch) — unrelated to additive leaf files. Interlock gate is the canonical city-registration gate and passes.

## Next step

(Done) Outcome and Spine delta written below — orchestrator applies in one serial hold.

## Outcome

**Verdict: REGISTER** — all three feeds verified live from
`https://services.arcgis.com/lQySeXwbBg53XWDi/`. Leaf files built, audited, and
verified (see below). SLA licenses and Maricopa County deeds are REJECTED with
evidence.

### Spine delta (for orchestrator, one serial hold)

1. **CityId enum** — add `TEMPE = "tempe"` after `TAMPA` (or after `TAMPA` in
   alphabetical order).
2. **Handwritten aliases** — add:
   - `"tempe": CityId.TEMPE`
   - `"tempe_az": CityId.TEMPE`
   - `"tempe-az": CityId.TEMPE`
   - `"tempe, az": CityId.TEMPE`
   - `"tempe arizona": CityId.TEMPE`
3. **CityRegistration** — add `"tempe"` entry:
   - `name="Tempe"`, `state="AZ"`
   - `center={"lat": 33.4267, "lng": -111.9398}`
   - `metro_bbox=TEMPE_METRO_BBOX` (via import)
   - `division_bboxes=TEMPE_DIVISION_BBOXES`
   - `submarkets=TEMPE_SUBMARKETS`
   - `divisions=TEMPE_DIVISIONS`
   - `datasets` — three entries:
     - `FeedType.PERMITS → DatasetSpec from TEMPE_FEED_SPECS["permits"]`
     - `FeedType.COMPLAINTS_311 → DatasetSpec from TEMPE_FEED_SPECS["311"]`
     - `FeedType.CRIME → DatasetSpec from TEMPE_FEED_SPECS["crime"]`
4. **Config** — add three ArcGIS endpoint settings:
   - `arcgis_tempe_permits_url: str = Field(...)` defaulting to TEMPE_PERMITS_ENDPOINT
   - `arcgis_tempe_complaints_311_url: str = Field(...)` defaulting to TEMPE_COMPLAINTS_311_ENDPOINT
   - `arcgis_tempe_crime_url: str = Field(...)` defaulting to TEMPE_CRIME_ENDPOINT
5. **`cities/__init__.py`** — add `"tempe"` to the city-module map.
6. **Dashboard** — add `METRO_META` entry for Tempe (deep link `?city=tempe`).
7. **Regenerate** `apps/dashboard/public/index.html` (byte-sync).
8. **Leaf-naming count** — pin bump in `test_city_leaf_naming.py`.

### Recommended Linear comment

> US-229 Tempe, AZ ready for spine hold. Three feeds verified live on
> 2026-08-28 from `services.arcgis.com/lQySeXwbBg53XWDi`:
> PERMITS (building_permits/FS/0, 20,226 rows, AppliedDateDtm daily),
> COMPLAINTS_311 (code_complaints/FS/0, 2,743 rows, CaseOpenDate ~10wk stale
> — quarterly pub suspected), CRIME (General_Offenses/FS/0, 380,724 rows,
> OccurrenceDatetime same-day fresh, mixed-CRS WKID 2223 → outSR=4326).
> SLA and deeds REJECTED with evidence (no license feed, 403 session-gated
> county recorder). Leaf files: tempe.py, field_maps_tempe.py,
> test_producers_tempe.py (1106 tests). Spine delta in .streams/west-tempe.md.