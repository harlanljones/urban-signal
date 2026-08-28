# Stream log — west-stockton — 2026-08-28

## Claim

- **Stream id:** `west-stockton`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/stockton.py`
  - `apps/api/src/producers/field_maps_stockton.py`
  - `apps/api/tests/unit/test_producers_stockton.py`
- **Spine files I expect to need:** NONE

## Intent

US-230: probe stocktonca.gov open data (ArcGIS) live; verify 1-4 official feeds
(permits / 311 / business licenses / recorded deeds via San Joaquin County);
build leaf registration files for verified feeds only; spine-safe tests with
byte-verbatim live fixtures through the real client path. If no verifiable
official feed exists, REJECT with evidence. No commits, no Linear updates.

## Decisions

- 2026-08-28 — Ticket's claimed source `stocktonca.opendata.arcgis.com` is a DEAD
  Hub-v2 shell (JS-only page; all /api/* → 404). Not usable as evidence of a feed.
- 2026-08-28 — `data.stocktonca.gov` (Socrata) is a MISCONFIGURED SHELL serving the
  national catalog (Dallas Police Active Calls, Lottery Cash-4-Life, 0 own datasets
  for domain=data.stocktonca.gov). Trap — never register against it.
- 2026-08-28 — City's real GIS is `gisportal.stocktonca.gov/arcgis2` (ArcGIS Server
  11.3, valid TLS, no -k needed). Directory: Accela / CityWorks / Comcate /
  Forerunner / BuildingBlocks / Peregrine / SpatialWave folders all return
  `{"error":{"code":499,"message":"Token Required"}}` → permits, 311, code
  enforcement systems of record are SECURED. No public ACA/permits DNS
  (aca./permits./ocounter.stocktonca.gov all NXDOMAIN).
- 2026-08-28 — SLA VERIFIED: `OpenCounter/OpenCounterMap/MapServer/7` "Liquor
  License Locations" (ABC liquor licenses): 1,363 rows (ACTIVE 1241, PEND 84,
  SUREND 35, R64B 2, REVPEN 1); watermark max(OriginalIssueDate)=1783987200000 ms
  = 2026-07-14T00:00:00Z (min 1953); point geometry, native extent SR
  WKID 102643/latest 2227 (NAD83 California Zone 3 ftUS) — storage is CA state
  plane, served as WGS84 via outSR=4326; NO X/Y attribute columns; 0 null
  geometries ("Shape IS NULL" count=0); 1,123 licenses expire after today;
  all newest rows expire 2027-06-30 (ABC license year).
- 2026-08-28 — DEEDS REJECT: San Joaquin County GIS (sjmap.org, v10.05) exposes
  only Locators/PublicWorks (+ empty GoRequest folder); county AGO orgs hold
  infrastructure assets only; no recorder/deeds bulk surface.
- 2026-08-28 — 311 REJECT: Comcate secured (499); county GoRequest empty; no 311
  dataset on the city AGO org (services3.arcgis.com/waC30SNtVvCK7olj — transit/
  flood/planning layers, stale 2024 work-orders snapshot only).
- 2026-08-28 — PERMITS REJECT: Accela secured; OpenCounterMap = reference basemap
  (parcels/zoning/districts, no transactions); Forerunner secured.
- 2026-08-28 — Shape of leaf: SLA-only partial registration (ticket explicitly
  allows partial; city_id "stockton", FeedType.SLA only).
- 2026-08-28 — Mailing-zip trap found live: `PremiseZipcode` holds the license
  holder's MAILING zip, not premise zip (fixture 512: premise 950 W 11th St,
  Stockton with PremiseZipcode "95376" / MailCity "TRACY"). Unmapped; Mail* block
  dropped as `DROPPED_MAIL_COLUMNS`.
- 2026-08-28 — ANSI-date host verified: gisportal rejects ISO literals
  (`OriginalIssueDate > '2026-01-01'` → 400) and accepts ANSI
  (`> date '2026-01-01'` → count 61). Spine must add host to
  ANSI_DATE_LITERAL_HOSTS. No `where` guard needed (no future-dated sentinels:
  newest issue 2026-07-14 < probe 2026-08-28).
- 2026-08-28 — needs_geocode=True declared (ADR-0004) despite 0 null geometries
  at probe: geometry is the primary path, geocode is the supplement for any
  future null-geometry rows on PremiseAddress (Tucson discipline).
- 2026-08-28 — expected_cadence_days=7 with alarm_exempt=True: watermark is the
  ABC original issue date, not the republication timestamp (~1 issue/week, 61
  rows dated 2026); staleness alarms would false-positive on publication lag.
- 2026-08-28 — Division geometry: 7 divisions / 14 submarkets, south boundary at
  lng -121.285 (Fairgrounds anchor in SOUTH_CENTRAL, Weston Ranch in
  SOUTHEAST_WESTON). Fringe winery fixture (38.0775, -121.3104) is metro-contained
  but division-free by design.

## Outcome

**VERIFIED — partial (SLA-only) registration.**

- **Feeds verified: 1** — SLA liquor licenses,
  `https://gisportal.stocktonca.gov/arcgis2/rest/services/OpenCounter/OpenCounterMap/MapServer/7`
  (official City of Stockton ArcGIS Server 11.3; valid TLS).
  - Row count: **1,363** (ACTIVE 1241 / PEND 84 / SUREND 35 / R64B 2 / REVPEN 1).
  - Watermark: `OriginalIssueDate` (esriFieldTypeDate, epoch-ms); newest value
    verbatim: **1783987200000** (= 2026-07-14T00:00:00+00:00); min 1953.
  - Columns: OBJECTID, LicenseCode, FileNumber, OriginalIssueDate,
    ExpirationDate, PremiseName, PremiseAddress, PremiseAddress2, OwnerName,
    PremiseZipcode, MailAddress, MailAddress2, MailCity, MailState,
    MailZipcode, PremiseCensusTract, LicenseType, Status, Shape.
  - Geometry: native points in store SR WKID 102643/latest **2227 (NAD83
    California Zone 3 ftUS)** — served WGS84 via outSR=4326; **no X/Y attribute
    columns**; 0/1,363 null geometries.
  - LicenseType = raw CA-ABC code strings (20×265, 21×260, 41×240, 47×214,
    2×73, 58×58, ...).
- **REJECTs (with evidence):**
  - PERMITS: Accela + Forerunner + CityWorks folders → 499 "Token Required";
    OpenCounterMap is a reference basemap (no transactions); no public citizen
    portal DNS.
  - 311: Comcate folder → 499 "Token Required"; sjmap.org GoRequest folder empty;
    nothing on the city AGO org except a stale 2024 work-orders snapshot.
  - DEEDS: San Joaquin County publishes no recorder/deeds bulk feed (sjmap.org =
    Locators/PublicWorks only; county AGO orgs = infrastructure assets).
  - Non-sources: stocktonca.opendata.arcgis.com (dead Hub-v2 shell, 404 APIs);
    data.stocktonca.gov (Socrata shell serving the NATIONAL catalog).
- **Tests (original build):** `pytest tests/unit/test_producers_stockton.py` → **33 passed**;
  `pytest -k stockton` → **35 passed, 3334 deselected**; `pytest -m interlock` →
  **24 passed** (unchanged); `ruff check` on the three leaf files → clean.
  Fixtures: 3 byte-verbatim live features (OBJECTID 512/1079/586, newest
  watermark rows) through the REAL client path — `ArcGISClient._flatten_feature`
  + `SLALicensesProducer.parse_socrata_row`.
- **Independent verification (2026-08-28):** ALL clean. Leaf files restored
  byte-identical from stash (concurrent west-missoula agent stashed -u at
  13:12, wiping all untracked wave files). Re-ran: 33 stockton tests passed,
  35 via `-k stockton`, 24 interlock (unchanged), ruff clean. Leaf verified.
- **Pre-existing spine failure (not caused by this stream):**
  `test_city_leaf_naming.py::test_all_expected_leaf_modules_present` asserts
  97 modules; it was already failing at **102** (concurrent southeast wave) —
  with `stockton.py` it is **103**. The spine must bump the count when both
  waves land. `test_leaf_has_canonical_constants` passes for stockton
  (STOCKTON_METRO_BBOX / _DIVISION_BBOXES / _SUBMARKETS / _DIVISIONS all present).
- Transient note: one `-k stockton` collection run mid-session hit ~95
  "AttributeError: 'Settings' object" collection errors — concurrent wave was
  mid-edit on `src/config.py`; re-ran clean minutes later. Nothing in this
  stream touches config.py.

## Spine delta

Exact spine changes for the interlock hold (for the recommended Linear comment):

1. **CityId member:** add `STOCKTON = "stockton"` to the `CityId` enum in
   `src/spatial/city_registry.py` (alphabetical near the S cities).
2. **ALIASES:** `"stockton": CityId.STOCKTON`, `"stockton_ca": CityId.STOCKTON`,
   `"stockton-ca": CityId.STOCKTON`, `"stockton ca": CityId.STOCKTON`.
3. **REGISTRY entry:**
   ```python
   CityId.STOCKTON: CityRegistration(
       city_id=CityId.STOCKTON,
       name="Stockton",
       state="CA",
       center={"lat": 37.9577, "lng": -121.2900},
       metro_bbox=STOCKTON_METRO_BBOX,
       division_bboxes=STOCKTON_DIVISION_BBOXES,
       submarkets=STOCKTON_SUBMARKETS,
       divisions=STOCKTON_DIVISIONS,
       job_suffix="stockton",
       datasets={
           FeedType.SLA: DatasetSpec(
               endpoint=settings.arcgis_stockton_sla_url,
               platform="arcgis",
               watermark_col="OriginalIssueDate",
               id_keys=["FileNumber", "OBJECTID"],
               topic=settings.topic_sla,
               interval_seconds=600.0,
               producer_key="sla",
               expected_cadence_days=7,
               alarm_exempt=True,
               alarm_exempt_reason=STOCKTON_SLA_ALARM_EXEMPT_REASON,
               ingestion_mode="snapshot",
               needs_geocode=True,
               geocode_context="Stockton, CA",
               order_by="OriginalIssueDate DESC",
               oid_field="OBJECTID",
               max_record_count=2000,
               state_plane_crs="EPSG:2227",   # store SR documentation only
               state_plane_units="ftUS",      # NO x/y cols exist on the layer
               field_map=STOCKTON_SLA_FIELD_MAP,  # import from field_maps_stockton
           ),
       },
   )
   ```
   (import `STOCKTON_SLA_FIELD_MAP` / bbox / submarket / division constants from
   `src.spatial.cities.stockton`, as done for `TUCSON_*`.)
4. **config endpoint settings** (`src/config.py`):
   ```python
   # Stockton, CA (US-230): city liquor-license snapshot (ANSI-date host -
   # gisportal.stocktonca.gov is listed in ANSI_DATE_LITERAL_HOSTS; store SR
   # WKID 2227 CA-Zone-3 ftUS, coords only via outSR=4326 geometry lift).
   arcgis_stockton_sla_url: str = Field(
       default="https://gisportal.stocktonca.gov/arcgis2/rest/services/OpenCounter/OpenCounterMap/MapServer/7",
       description="Stockton liquor licenses ArcGIS MapServer URL (SLA)",
   )
   ```
5. **watermarks.py:** add `"gisportal.stocktonca.gov"` to
   `ANSI_DATE_LITERAL_HOSTS` (verified live: ISO literal → 400, ANSI
   `date '2026-01-01'` → 200 count).
6. **test_city_leaf_naming.py:** bump expected module count 97 → 103 (or
   rework to per-leaf) — currently failing pre-existing at 102 (southeast wave)
   and 103 after this wave.
7. **Dashboard (city-registration rule):** the spine hold that adds
   `CityId.STOCKTON` must also add the `METRO_META` entry (metro chip +
   `?city=stockton` deep link), snapshot-export coverage, res-5 grid-tile
   coverage in the published manifest, and the byte-synced
   `apps/dashboard/public/index.html` copy in the SAME hold —
   `TestDashboardWiring`/`TestSnapshotWiring` will fail `pytest -m interlock`
   otherwise. Never "docs later".

**Recommended Linear comment:** partial SLA-only registration per above; do NOT
register permits/311/deeds (evidence in stream log). Note the two non-source
traps (dead Hub shell, national-catalog Socrata domain) so no future ticket
trusts them.

## Current step

Done — leaf built and verified; stream log finalized.

## Next step

Spine hold (separate stream): REGISTRY/ALIASES/METRO_META/dashboard byte-sync +
ANSI_DATE_LITERAL_HOSTS + naming-count bump, per Spine delta. Leaf files are
untracked and intentionally NOT committed (wave policy).

## Verification

Independent LEAF verification passed — 2026-08-28. The prior run died of an
account-quota error before returning its report; verification was re-run from
scratch: stream log Outcome + Spine delta complete; leaf files spine-stable
(city_id STRING "stockton", no CityId/REGISTRY/FeedType/scheduler/division-
resolution/geocode-call-count asserts); FEED_SPECS match DatasetSpec fields.
`pytest tests/unit/test_producers_stockton.py` → 33 passed;
`pytest -k stockton` → 35 passed; `pytest -m interlock` → 24 passed (unchanged);
`ruff check` on the three leaf files → clean.

NOTE for wave coordination: a concurrent agent (west-missoula) ran
`git stash -u` at 13:12, capturing ALL untracked wave files (every west-*/leaf
file + stream logs). The three leaf files + this log were restored byte-identical
from `stash@{0}^3` and re-verified clean. Whichever agent resolves the stash
must expect conflicts when popping the untracked commit against the restored
working tree — content is identical, so a `git checkout stash@{0}^3 -- .` (or
equivalent content-safe restore) is the clean resolution.
