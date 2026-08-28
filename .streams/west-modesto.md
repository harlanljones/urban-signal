# Stream log — west-modesto — 2026-08-28

## Claim

- **Stream id:** west-modesto
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/modesto.py`
  - `apps/api/src/producers/field_maps_modesto.py`
  - `apps/api/tests/unit/test_producers_modesto.py`
- **Spine files I expect to need:** NONE (leaf-only wave; spine delta reported to orchestrator in Outcome)

## Intent

US-231: verify Modesto, CA official open-data feeds live (ArcGIS Hub —
modestogov.com), then build the leaf trio (city geometry module + per-feed
field maps + byte-verbatim fixture tests through the real client path).
If no verifiable official feed exists → REJECT with evidence. No spine
files touched; no git commits; no Linear updates.

## Decisions

- 2026-08-28 — **Hub is a private org.** `modesto.opendata.arcgis.com/api/feed/dcat-us/1.1.json` → 401
  `{"message":"private org id for modesto.opendata.arcgis.com is not accessible"}`. Greenville precedent.
- 2026-08-28 — **Real GIS server found:** `gis.modestogov.com/hosting/rest/services` (ArcGIS Enterprise 12.1,
  needs browser UA). Public folders: ExternalServices + Utilities. **Hosted / InternalServices / TrakIT
  → 403 Forbidden** (TrakIT = their permit system → no public permits surface).
- 2026-08-28 — **PERMITS REJECT:** no public row-level permits feed. TrakIT 403; AGO "Perf Mgmt" permit
  dashboards embed aggregate data with no service URLs; `Map_Layer_Service_External/32 Development Projects`
  is a showcase point layer (internal_identification/Type/Symbol/COUNT_/Value/Lat/Long — no dates, no case ids);
  `Concurrent_Project_Map` AGO = Name/Objective/Status story layer.
- 2026-08-28 — **311 REJECT:** Modesto 311 = "GoModesto" on **PublicStuff** (city embeds
  `iframe.publicstuff.com/#?client_id=1000044`). PublicStuff API is undocumented legacy XML-RPC
  (`/api/requests` → "Request method not provided"/"Malformed XML" for every envelope tried);
  widget config.js exposes only a CDN path. No Socrata/ArcGIS 311 surface (AGO hosted: 68 services,
  none 311-family; `IT_Work_Orders` is internal IT, `Litter` is a program layer).
- 2026-08-28 — **DEEDS REJECT:** Stanislaus Clerk-Recorder online service = `crweb.stancounty.com`
  ("Online U.S. Applications" vendor search portal — interactive, pay-per-copy, no anonymous bulk API;
  govos/recordings subdomains don't resolve). City-parcel mirror
  `County_Parcels_Offline_External/0` = 168,712 polygons, fields: apn/asmt/taxyear/yearbuilt/wa_*/situs_* —
  **no sale price, no sale date, no document number** → cadastre, not deeds (Greenville parcel-CAMA precedent).
  modifydate newest epoch 1784933393000 (bulk-reload stamp) — refreshed but still not a deeds feed.
- 2026-08-28 — **SLA VERIFIED (partial registration):** `ExternalServices/Map_Layer_Service_External/FeatureServer/7`
  "Business Licenses". Live query 2026-08-28: **4,574 rows**, native point geometry WKID 102643
  (NAD83 California Zone 3 state-plane ft) lifted via outSR=4326 (verified: x=-121.0275, y=37.6594);
  **214/4574 null-geometry (95.3% coverage)**. Columns: OBJECTID, ACCOUNTNUM, BUSNAME, LOCSTNUM,
  LOCSTADDR1, LOCSUITE, LOCCITY, LOCST, LOCZIP1, LOCZIP2, LOCPHNUM, GlobalID.
  - **NO date fields** → incremental impossible; snapshot-only.
  - **No license_type / status / NAICS** → SLA events carry id+name+address only.
  - **No lastEditDate / editingInfo / timeInfo on the layer** → staleness probe would flag
    `oldest is None` → stale permanently → spec must carry `alarm_exempt=True` (NYC ENERGY_BENCHMARK precedent).
  - No X/Y attribute columns → no state_plane_* keys; geometry lift is the only coordinate path (Tucson precedent).
- 2026-08-28 — AGO org "City of Modesto GIS" (services1.arcgis.com/KN76x1eyfvozZO4M, 68 services) swept:
  nothing permits/311/deeds-family. County hosts (gis/gismaps/opendata.stancounty.com) do not resolve.

## Current step

DONE — leaf trio restored and audited on `chore/restore-metros-and-columbus`;
fixtures re-verified byte-verbatim against the live FeatureServer/7 (three
OBJECTID 2/3/4 rows, all twelve columns, outSR=4326 geometry), layer metadata
re-confirmed (maxRecordCount=2000, store SR WKID 102643, no date field, no
editingInfo/timeInfo), count re-confirmed 4,574. Tests 34/34, interlock 24/24,
ruff clean.

## Next step

(complete — see Outcome + Spine delta below)

## Outcome

**VERIFIED — partial (SLA-only) registration.** Modesto is a ONE-FEED PARTIAL
metro.

- **Feeds verified: 1** — SLA Business Licenses,
  `https://gis.modestogov.com/hosting/rest/services/ExternalServices/Map_Layer_Service_External/FeatureServer/7`
  (official City of Modesto ArcGIS Enterprise 12.1 server; browser UA required).
  - Row count: **4,574**; null-geometry **214/4574 (≈4.7%)**.
  - Watermark: **none** — the layer has no `esriFieldTypeDate` column
    (incremental impossible) → `watermark_col=""`, `ingestion_mode="snapshot"`.
  - Columns (exactly 12): OBJECTID, ACCOUNTNUM, BUSNAME, LOCSTNUM, LOCSTADDR1,
    LOCSUITE, LOCCITY, LOCST, LOCZIP1, LOCZIP2, LOCPHNUM, GlobalID.
  - Geometry: native points in store SR WKID **102643 (NAD83 California Zone 3
    state plane ftUS)** served as WGS84 via `outSR=4326`; **no X/Y attribute
    columns** → no `state_plane_*` spec keys (Tucson precedent).
  - No license-class/status/NAICS column → every event carries the shared
    parser's legacy `license_type` default ("On-Premises Liquor") — the
    registration caveat the spine hold must carry.
  - No editingInfo/timeInfo → `alarm_exempt=True` (KC SLA precedent, US-163).
  - `needs_geocode=False`: mapped address is a street string without a house
    number (no parts-join in the shared SLA chain) → fails ADR-0004 confidence
    gate (MC311 precedent); null-geometry rows drop.
  - Fixtures: 3 byte-verbatim live features (OBJECTID 2/3/4) through the REAL
    client path — `ArcGISClient._flatten_feature` + `SLALicensesProducer.parse_socrata_row`.
- **REJECTs (with evidence):**
  - PERMITS: TrakIT/Hosted/InternalServices folders → 403 Forbidden; only
    aggregate showcase layers (Development Projects, Concurrent_Project_Map)
    exist publicly — no dates, no case ids.
  - 311: GoModesto runs on PublicStuff vendor (iframe.publicstuff.com
    client_id=1000044) — undocumented legacy XML-RPC rejects every anonymous
    envelope; no Socrata/ArcGIS 311 surface (68 AGO services, none 311-family).
  - DEEDS: Stanislaus Clerk-Recorder is an interactive pay-per-copy search
    portal (crweb.stancounty.com) with no anonymous bulk API; the city parcel
    mirror (168,712 polygons) is a cadastre — no sale price/date/document no.
  - Non-sources: modesto.opendata.arcgis.com (private org, 401); county hosts
    (gis/gismaps/opendata.stancounty.com) do not resolve.
- **Tests:** `pytest tests/unit/test_producers_modesto.py` → **34 passed**;
  `pytest -k modesto` → **34 passed**; `pytest -m interlock` → **24 passed**
  (unchanged); `ruff check` on the three leaf files → clean.
- **Pre-existing spine failure (not caused by this stream):**
  `test_city_leaf_naming.py::test_all_expected_leaf_modules_present` asserts
  a fixed module count; with concurrent west/southeast waves in flight the
  count pin is stale and spine-owned — ignored per wave contract.
- **Branch note:** a concurrent wave process switched the worktree from
  `main` to `chore/restore-metros-and-columbus` mid-run, wiping the untracked
  leaf files; restored byte-exact from the session read + re-verified against
  live source before finalizing. No spine files touched.

## Spine delta

Exact spine changes for the interlock hold (for the recommended Linear comment):

1. **CityId member:** add `MODESTO = "modesto"` to the `CityId` enum in
   `src/spatial/city_registry.py` (alphabetical near the M cities).
2. **ALIASES:** `"modesto": CityId.MODESTO`, `"modesto_ca": CityId.MODESTO`,
   `"modesto-ca": CityId.MODESTO`, `"modesto ca": CityId.MODESTO`.
3. **REGISTRY entry** — import `MODESTO_*` constants + `MODESTO_SLA_FIELD_MAP`
   from the leaf, then:
   ```python
   CityId.MODESTO: CityRegistration(
       city_id=CityId.MODESTO,
       name="Modesto",
       state="CA",
       center={"lat": 37.6391, "lng": -120.9969},
       metro_bbox=MODESTO_METRO_BBOX,
       division_bboxes=MODESTO_DIVISION_BBOXES,
       submarkets=MODESTO_SUBMARKETS,
       divisions=MODESTO_DIVISIONS,
       job_suffix="modesto",
       datasets={
           FeedType.SLA: DatasetSpec(
               endpoint=settings.arcgis_modesto_sla_url,
               platform="arcgis",
               watermark_col="",
               id_keys=["ACCOUNTNUM", "OBJECTID"],
               topic=settings.topic_sla,
               interval_seconds=1800.0,
               producer_key="sla",
               expected_cadence_days=90,
               alarm_exempt=True,
               alarm_exempt_reason=MODESTO_SLA_ALARM_EXEMPT_REASON,
               ingestion_mode="snapshot",
               needs_geocode=False,
               oid_field="OBJECTID",
               max_record_count=2000,
               field_map=MODESTO_SLA_FIELD_MAP,
           ),
       },
   )
   ```
4. **config endpoint settings** (`src/config.py`):
   ```python
   # Modesto, CA (US-231): current business-license snapshot (ArcGIS Enterprise
   # FeatureServer/7; store SR WKID 102643 CA-Zone-3 ftUS, coords only via
   # outSR=4326 geometry lift; no date column -> snapshot + alarm-exempt).
   arcgis_modesto_sla_url: str = Field(
       default="https://gis.modestogov.com/hosting/rest/services/ExternalServices/Map_Layer_Service_External/FeatureServer/7",
       description="Modesto Business Licenses ArcGIS FeatureServer URL (SLA)",
   )
   ```
5. **`cities/__init__.py`:** add the Modesto import block + `__all__` entries
   (leaf module itself is untracked/wave-owned).
6. **test_city_leaf_naming.py:** bump the expected module count when the west
   wave + southeast wave both land (currently failing at a stale pin — see
   Outcome).
7. **Dashboard (city-registration rule):** the spine hold that adds
   `CityId.MODESTO` must ALSO add the `METRO_META` entry (metro chip +
   `?city=modesto` deep link), snapshot-export coverage, res-5 grid-tile
   coverage in the published manifest, and the byte-synced
   `apps/dashboard/public/index.html` copy in the SAME hold —
   `TestDashboardWiring`/`TestSnapshotWiring` fail `pytest -m interlock`
   otherwise. Never "docs later".

**Recommended Linear comment:** partial SLA-only registration per above; do
NOT register permits/311/deeds (evidence in stream log). Note the private-org
Hub trap (modesto.opendata.arcgis.com → 401) so no future ticket trusts it,
and the license_type parser-default caveat that must land with the spine hold.
