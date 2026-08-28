# Stream log — west-chandler — 2026-08-28

## Claim

- **Stream id:** west-chandler (leaf, West-region metro-expansion wave)
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/chandler.py
  - apps/api/src/producers/field_maps_chandler.py
  - apps/api/tests/unit/test_producers_chandler.py
- **Spine files I expect to need:** NONE

## Intent

Live-verify Chandler, AZ official open-data feeds (chandleraz.gov ArcGIS), then
build the leaf registration files (city spec + field maps + spine-stable tests)
for US-228. No spine edits, no commits, no Linear updates; outcome + spine
delta recorded here for the wave lead to wire.

## Decisions

- 2026-08-28 12:45 — Hub dead end: `chandleraz.opendata.arcgis.com/api/search/v1/collections/dataset`
  → 401 `{"message":"private org id for chandleraz.opendata.arcgis.com is not accessible"}`.
  Same private-org trap as Greenville. Old `gis.chandleraz.gov/arcgis/rest/services`
  (from 2018 web maps) is decommissioned (IIS 404 on every path).
- 2026-08-28 12:47 — Live server found: Chandler runs ArcGIS **Enterprise 11.5**
  proxied at `https://gis.chandleraz.gov/portalserver/rest/services` (the
  `/appsanonymous` path returns an identical service tree). 42 folders
  enumerated. AGOL org id `HIBNcuytta1apnkB` (services1.arcgis.com) hosts 941
  items, mostly dashboards/surveys.
- 2026-08-28 12:50 — **PERMITS VERIFIED**: `Tolemi/Building_Blocks/MapServer/0`
  = `LIS.ACCELA_ALL_PERMITS_V_HARD` (Accela permits, point layer).
  - Rows: **103,442** (live returnCountOnly). maxRecordCount 2000.
  - Watermark: `CREATE_DT` (only esriFieldTypeDate). Newest verbatim
    **1787702401000** = 2026-08-26T00:00:01+00:00; oldest 978480000000
    (2001-01-02); 2026 YTD 3,930; last-30d 455; last-7d 81; future-dated 0.
  - Columns: OBJECTID (OID), FULL_ADDRESS, ADDR_TYPE_DESC, RETIRED (N/Y),
    INSP_ZONE, INSPECTOR, SUPERVISOR, PERMIT_NBR, CREATE_DT, PROJECT_NM,
    B1_PER_TYPE, B1_PER_SUB_TYPE, PERMIT_STATUS, DETAIL_DESC, PERMIT_TYPE,
    PARCEL_NBR, ADDR_EID, FMA, JOB_VALUE (string, e.g. "4000"), SQ_FOOT,
    ECON_DEV_PRJ, FULL_ADDR, ZIP_CODE, PRI_CNTCT_* / PRI_CNTRCT_* / OWNER_*
    (PII), SHAPE.
  - Geometry: native point; **store SR = NAD83(HARN) StatePlane Arizona
    Central FIPS 0202, international feet** (extent WKT); `outSR=4326` lift
    verified (fixtures arrive WGS84). NO X/Y attribute pair exists → no
    `state_plane_*` spec fields needed (tucson style: store SR documented,
    never mapped). `SHAPE IS NULL` count = **0** → needs_geocode=False.
  - CREATE_DT semantics pinned by live data: it is the Accela **record
    creation (application) date**, not issuance — 2,307 pending-status
    permits carry CREATE_DT older than 90d, oldest pending back to 2006
    (FPT06-0042, "Applied", 2006-08-29). Map CREATE_DT → filing_date
    (Dallas CREATEDDATE convention); issuance_date undeclared — the view
    publishes no issue timestamp. Pipeline permit-velocity (issuance-based)
    will see NULL until an issuance column appears; cost/h3/status remain.
  - **ANSI-date host**: `CREATE_DT > date '2026-07-29'` works; ISO string
    literal → 400 "Unable to complete operation"; `DATEADD` unsupported.
    Spine must add `gis.chandleraz.gov` to `ANSI_DATE_LITERAL_HOSTS`
    (watermarks.py) — same family as gis.tucsonaz.gov.
  - RETIRED='Y' = 537 rows (address retirement flag, newest 2026-04-10, 0 in
    last 90d) — left unfiltered; PERMIT_TYPE null on 49,436 rows → job_type
    candidates lead with B1_PER_TYPE (22 distinct, no nulls observed).
- 2026-08-28 12:55 — **COMPLAINTS_311 REJECTED (Tier 3)**: full 42-folder
  enterprise sweep shows no service-request layer (GOGov/COC_GOGov publishes
  only base layers + "Permit Meter"); AGOL org search
  `orgid:HIBNcuytta1apnkB AND ("service request" OR 311)` → total 0.
  Chandler 311 is GOGov SaaS with no public bulk feed.
- 2026-08-28 12:55 — **SLA REJECTED (Tier 3)**: no business-license dataset
  on the server or in the org (org search returns only an
  Open_Database_License_Agreement PDF). AZ has no municipal general business
  license (TPT is state-administered); mirrors phoenix.py:8 ("no broader
  business-tax feed").
- 2026-08-28 12:57 — **DEEDS REJECTED (Tier 3)**: Maricopa County recorder
  (recorder.maricopa.gov) 403s anonymous scripted access, no bulk API —
  re-confirms phoenix.py:22-23 ("Deeds have no queryable watermark"). Same
  county as Phoenix.
- 2026-08-28 12:57 — **CRIME not registered**: Chandler's "Crime Map" is
  raidsonline.com (LexisNexis RAIDS SaaS, not a bulk feed); everything else
  is PIP aggregate dashboards (skip per ticket; ADR-0004 coordinate rule
  moot).
- 2026-08-28 13:00 — Divisions/submarkets grounded in the **live
  OpenData/LIS_OpenData/MapServer/2 (Subdivisions, 2,010 plats)** envelopes
  at outSR=4326: MARLBOROUGH ESTATES lng[-111.8938,-111.8897]
  lat[33.3466,33.3494]; SUN GROVES lng[-111.7727,-111.7553]
  lat[33.2047,33.2193]; OCOTILLO plats lng[-111.8933,-111.8240]
  lat[33.2311,33.2673]; FULTON RANCH lng[-111.8600,-111.8412]
  lat[33.2328,33.2476]; SPRINGFIELD lng[-111.8237,-111.7726]
  lat[33.2044,33.2192]; COOPER COMMONS lng[-111.8066,-111.7892]
  lat[33.2046,33.2192]; CIRCLE G AT RIGGS HOMESTEAD RANCH
  lng[-111.8023,-111.7922] lat[33.2191,33.2337]. Metro bbox grounded on the
  live GOGov/COC_GOGov/MapServer/11 city boundary envelope:
  lng[-111.9723,-111.7553] lat[33.2038,33.3613].
- 2026-08-28 13:05 — PII handling: fixtures redact PRI_CNTCT_*/PRI_CNTRCT_*/
  OWNER_* values (personal names/phones/emails in live rows); those columns
  are DROPPED_PII_COLUMNS and never map candidates, so redaction cannot
  affect parse outcomes. All other fixture bytes are verbatim from the
  2026-08-28 probe (orderByFields=CREATE_DT DESC, OBJECTID DESC, outSR=4326).

## Current step

DONE — leaf complete and verified; no commits made (per interlock).

## Next step

None for this leaf. Wave lead: execute the Spine delta above in one hold
(REGISTRY + aliases + ANSI_DATE_LITERAL_HOSTS + dashboard wiring + leaf-count
bump), then post the recommended Linear comment to US-228.

## Outcome

**Status: LEAF COMPLETE — 1 feed verified, registration-ready (partial, permits-only).**

### Phase A — live-probe results (2026-08-28)

| Family | Verdict | Evidence |
|---|---|---|
| PERMITS | **VERIFIED** | `Tolemi/Building_Blocks/MapServer/0` = `LIS.ACCELA_ALL_PERMITS_V_HARD` on `gis.chandleraz.gov/portalserver` (ArcGIS Enterprise 11.5). 103,442 rows; platform arcgis; native point geometry (store SR StatePlane AZ Central HARN intl ft, 0/103,442 null geometry); watermark `CREATE_DT` newest **1787702401000** = 2026-08-26T00:00:01+00:00 verbatim (oldest 2001-01-02; 3,930 in 2026 YTD; 455/30d; 81/7d; 0 future-dated); maxRecordCount 2000. |
| COMPLAINTS_311 | REJECT (Tier 3) | Chandler 311 is GOGov SaaS; `GOGov/COC_GOGov` publishes only base layers; 42-folder server sweep + org search `orgid:HIBNcuytta1apnkB AND ("service request" OR 311)` → total 0. |
| SLA | REJECT (Tier 3) | No business-license dataset on server or org (search → only a license-agreement PDF); AZ has no municipal general business license (TPT state-administered) — phoenix.py:8 precedent. |
| DEEDS | REJECT (Tier 3) | Maricopa County recorder 403s anonymous scripted access, no bulk API — re-confirms phoenix.py:22-23 ("no queryable watermark"). Same county. |
| CRIME | REJECT | "Crime Map" = raidsonline.com (RAIDS SaaS); rest are PIP aggregate dashboards (skip per ticket; ADR-0004 moot). |

Hub note: `chandleraz.opendata.arcgis.com` search API → 401 "private org id …
not accessible" (Greenville-style private-org trap); legacy
`/arcgis/rest/services` tree decommissioned (IIS 404). The Hub data source is
the same Enterprise server registered here.

### Phase B — leaf build

- `apps/api/src/spatial/cities/chandler.py` — metro bbox (rounded from live
  GOGov boundary envelope), 6 divisions / 10 submarkets grounded in live
  Subdivisions-plat envelopes (MARLBOROUGH ESTATES, SUN GROVES, OCOTILLO ×58,
  FULTON RANCH, SPRINGFIELD, COOPER COMMONS, CIRCLE G AT RIGGS HOMESTEAD
  RANCH) + downtown/airport anchors; `CHANDLER_FEED_SPECS` DatasetSpec-shaped
  (city_id string `"chandler"`, no CityId import); no `state_plane_*` fields
  (layer has no X/Y attributes — store SR documented, never mapped); honest
  handling: CREATE_DT→filing_date (2,307 pending permits >90d prove
  application-date semantics), needs_geocode=False, ANSI-date host noted.
- `apps/api/src/producers/field_maps_chandler.py` — PERMITS map
  (job_id=PERMIT_NBR+OBJECTID, filing_date=CREATE_DT, status=PERMIT_STATUS,
  job_type=B1_PER_TYPE→PERMIT_TYPE, cost=JOB_VALUE string, address=
  FULL_ADDRESS→FULL_ADDR, zipcode=ZIP_CODE, bbl=PARCEL_NBR/APN);
  DROPPED_PII_COLUMNS (PRI_CNTCT_*/PRI_CNTRCT_*/OWNER_*).
- `apps/api/tests/unit/test_producers_chandler.py` — spine-stable (plain
  `"chandler"` / `"permits"` strings; no CityId, no FeedType, no REGISTRY/
  scheduler/division-resolution/geocode-count asserts); 3 byte-verbatim live
  fixtures (PII values redacted — never map candidates) through the real
  `ArcGISClient._flatten_feature` → `DOBPermitsProducer.parse_socrata_row`
  path.

### Verification (from apps/api)

- `pytest tests/unit/test_producers_chandler.py -q` → **32 passed**, exit 0
- `pytest -k chandler -q` → **34 passed**, exit 0
- `pytest -m interlock -q` → **24 passed** (unchanged — leaf adds no spine)
- `ruff check` on all three files → All checks passed
- `tests/unit/test_city_leaf_naming.py`: chandler.py passes all four
  canonical-constant checks (`test_leaf_has_canonical_constants`);
  `test_all_expected_leaf_modules_present` FAILS pre-existing (asserts 97
  modules, working tree has 110 — the concurrent waves' new leaves; 109
  without mine) — that file is spine-forbidden for this leaf; the spine
  hold must bump the count when it lands all pending leaves.

### Spine delta (for the wave lead's spine hold — NOT done by this leaf)

1. `src/spatial/city_registry.py`:
   - `CityId.CHANDLER = "chandler"` (append after `TUCSON`).
   - `_HANDWRITTEN_ALIASES`:
     `"chandler": CityId.CHANDLER`, `"chandler_az"`, `"chandler-az"`,
     `"chandler az"` (do NOT claim `gilbert`/`sun_lakes`/`mesa`).
   - `CityRegistration(city_id=CityId.CHANDLER, name="Chandler", state="AZ",
     center={"lat": 33.3060, "lng": -111.8412}, metro_bbox=CHANDLER_METRO_BBOX,
     division_bboxes=CHANDLER_DIVISION_BBOXES, submarkets=CHANDLER_SUBMARKETS,
     divisions=CHANDLER_DIVISIONS, job_suffix="chandler",
     datasets={FeedType.PERMITS: <spec built from
     src/spatial/cities/chandler.py:CHANDLER_FEED_SPECS / get_chandler_dataset>)`.
   - Import `from src.spatial.cities.chandler import ...` alongside tucson.
2. `src/producers/watermarks.py`: **add `gis.chandleraz.gov` to
   `ANSI_DATE_LITERAL_HOSTS`** — the host rejects ISO date-string literals
   (verified 400) and only accepts `date 'YYYY-MM-DD'`; without this,
   incremental watermark comparisons fail.
3. `src/config.py`: no new settings required — the endpoint is a leaf
   constant (`CHANDLER_PERMITS_ENDPOINT`, tucson/greenville precedent). If
   the spine prefers settings-style URLs, mirror `settings.chandler_permits_url`.
4. Dashboard (same spine hold, enforced by `TestDashboardWiring` /
   `TestSnapshotWiring`): `METRO_META` chip for chandler + `?city=chandler`
   deep link, snapshot export coverage, res-5 grid-tile manifest entry, and
   the byte-synced `apps/dashboard/public/index.html` copy — the
   city-registration rule gates `pytest -m interlock` (currently 24 passed;
   must stay green after wiring).
5. Staleness: declare `expected_cadence_days=1` (455 permits/30d; newest row
   2026-08-26 at probe time — no alarm exemption needed).

Recommended Linear comment for US-228 (post spine hold):

> Chandler, AZ registered as `chandler` (West). PERMITS verified live against
> the city ArcGIS Enterprise (`gis.chandleraz.gov/portalserver` →
> `Tolemi/Building_Blocks/MapServer/0`, LIS.ACCELA_ALL_PERMITS_V_HARD):
> 103,442 rows, watermark CREATE_DT newest 2026-08-26T00:00:01Z, native
> outSR=4326 point geometry (store SR StatePlane AZ Central ft, 0 nulls).
> Note: CREATE_DT is the Accela application date (no issuance timestamp is
> published), so permit events carry filing_date only — issuance-based
> velocity sees Chandler after an issuance column appears; cost/H3/status
> flow today. 311 (GOGov SaaS), SLA (no municipal licenses in AZ), deeds
> (Maricopa recorder has no bulk API — same as Phoenix), and crime (RAIDS
> SaaS/aggregates) are Tier 3 and unregistered. Host added to
> ANSI_DATE_LITERAL_HOSTS (ISO literals 400). Leaf: chandler.py,
> field_maps_chandler.py, test_producers_chandler.py (32 tests); interlock 24 passed.
