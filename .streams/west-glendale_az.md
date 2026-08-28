# Stream log — west-glendale_az — 2026-08-28

## Claim

- **Stream id:** `west-glendale_az`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/glendale_az.py`
  - `apps/api/src/producers/field_maps_glendale_az.py`
  - `apps/api/tests/unit/test_producers_glendale_az.py`
  - `.streams/west-glendale_az.md`
- **Spine files I expect to need:** NONE (leaf-only wave; spine hold owned by US-250/US-363 spine stream)

## Intent

Live-verify Glendale, AZ (glendaleaz.com) municipal open-data feeds (permits / 311 / SLA licenses / deeds — Maricopa County partial ok), then build the leaf-only registration: spatial module (bbox, divisions, submarkets, FEED_SPECS shaped exactly to `DatasetSpec`), per-feed field maps, and spine-stable unit tests with byte-verbatim live fixtures through the real client path. If no verifiable official feed exists, report REJECT with evidence. Never use a stale mirror.

## Decisions

- <2026-08-28> Probe target: `gismaps.glendaleaz.com/gisserver` (official City of Glendale ArcGIS Server 11.4, owner `GisAdmin_COG`) + `glendaleaz.opendata.arcgis.com` Hub. `SmartGov`/`Building_Safety` folders are token-protected (ArcGIS 499) → NO anonymous permits feed.
- <2026-08-28> **311 VERIFIED** — `OpenData/GLENDALEONE_EXTERNAL_REQUESTS_PTS` MapServer/0: 107,646 rows, native WGS84 point geometry (all rows carry geometry + Latitude/Longitude attrs), watermark `Request_Date` max **1785888000000 = 2026-08-05T00:00:00Z**. DateLoaded uniform **1785981615723 = 2026-08-06T02:00:15Z** → ETL currently 22 days stale; register with watermark so staleness alarms. Council_District values: BARREL/CACTUS/CHOLLA/OCOTILLO/SAHUARO/YUCCA. FULL_ADDRESS is anonymized block-level ("6700 BLOCK W DENTON LN").
- <2026-08-28> **SLA VERIFIED** — `OpenData/Business_Licenses` MapServer/1 table "Glendale Business Licenses": 9,856 rows, NO geometry (layer 0 "Throw Away" is a dummy), watermark `IssuedOn` (esriFieldTypeDateOnly, string YYYY-MM-DD) max **"2026-08-22"**, DateLoaded **1787842811000 = 2026-08-27T15:00:11Z** (fresh). needs_geocode=True on AddressLine1 (ADR-0004). LicenseStatus: CLOSED/EXPIRED/PENDING/SUSPENDED/VALID.
- <2026-08-28> **DEEDS** county-held (Maricopa) — `docs/research/probe-maricopa-sales-affidavits.md` says feasible but needs CSVClient delimiter + scheduler forwarding (spine-held). NOT in this leaf.
- <2026-08-28> Metro bbox from official CityBoundary polygon: lat 33.5078..33.6979, lng -112.4616..-112.1516 → permissive bbox lat 33.50..33.71, lng -112.47..-112.14. 6 divisions = the six council districts; 9 submarkets.

## Current step

Leaf files complete. All verifications pass.

## Next step

None — leaf is complete. Spine hold (US-250/US-363 spine stream) to add CityId.GLENDALE_AZ, aliases, REGISTRY entries, METRO_META, and dashboard byte-sync per city-registration rule.

## Outcome

### Feeds verified (2 of 4 candidates)

| Feed | Endpoint | Platform | Rows | Watermark col | Newest value | Geometry | Status |
|------|----------|----------|------|---------------|-------------|----------|--------|
| **311** | `OpenData/GLENDALEONE_EXTERNAL_REQUESTS_PTS` MapServer/0 | arcgis | 107,646 | `Request_Date` | 2026-08-05T00:00:00Z (1785888000000 ms) | Native WGS84 point (all rows) | VERIFIED |
| **SLA** | `OpenData/Business_Licenses` MapServer/1 | arcgis | 9,856 | `IssuedOn` | 2026-08-22 (DateOnly string) | None (table) → needs_geocode | VERIFIED |
| **Permits** | SmartGov / Building_Safety folders | — | — | — | — | — | REJECTED (token-protected, ArcGIS 499) |
| **Deeds** | Maricopa County (AGOL CSV Collection) | — | — | — | — | — | REJECTED (CSVClient delimiter + scheduler spine gap; docs/research/probe-maricopa-sales-affidavits.md) |

### Watermarks
- **311**: `Request_Date` max = 2026-08-05 (co-newest 5+ rows). `DateLoaded` uniform 2026-08-06 → ETL 22 days stale at probe; register so staleness probe alarms.
- **SLA**: `IssuedOn` max = "2026-08-22". `DateLoaded` 2026-08-27 (fresh). Snapshot ingestion.

### Column lists
- **311**: OBJECTID, DateLoaded, Request_Number, Status, Request_Date, Last_Action_Date, Close_Date, Request_Type_Group, Request_Type, Latitude, Longitude, Cross_Streets, Council_District, Responsible_Department_Name, ANON_BLOCK, FULL_ADDRESS
- **SLA**: OBJECTID, DateLoaded, LicenseType, BusinessType, BusinessName, AddressLine1, City, State, ZipCode, District, IssuedOn, LicenseStatus, ExpiresOn, ParcelLegalDesc

### Test results
- `test_producers_glendale_az.py`: **40/40 passed**
- `pytest -k glendale_az`: **passed**
- `pytest -m interlock`: **24 passed** (no interlock failures)
- `ruff check`: **clean** on all 3 files

### Leaf files created
- `apps/api/src/spatial/cities/glendale_az.py`
- `apps/api/src/producers/field_maps_glendale_az.py`
- `apps/api/tests/unit/test_producers_glendale_az.py`
- `.streams/west-glendale_az.md`

## Spine delta

For the spine hold (US-250/US-363 spine stream), the following are needed:

1. **CityId.GLENDALE_AZ** = "glendale_az" member in `CityId` enum (`apps/api/src/spatial/city_registry.py`).
2. **Aliases**: `glendale_az`, `glendale-az`, `glendale az`, `glendale_arizona`
3. **REGISTRY entry**: Two `DatasetSpec` rows keyed by `FeedType.COMPLAINTS_311` and `FeedType.SLA` using the FEED_SPECS dicts from `glendale_az.py`. Endpoints:
   - 311: `https://gismaps.glendaleaz.com/gisserver/rest/services/OpenData/GLENDALEONE_EXTERNAL_REQUESTS_PTS/MapServer/0`
   - SLA: `https://gismaps.glendaleaz.com/gisserver/rest/services/OpenData/Business_Licenses/MapServer/1`
4. **config.py**: No new settings needed (topic_311/topic_sla already exist).
5. **METRO_META**: `glendale_az` entry with city_id, center (33.55, -112.22), name "Glendale, AZ", metro chip + `?city=glendale_az` deep link.
6. **Dashboard byte-sync**: `apps/dashboard/public/index.html` tiles + `apps/dashboard/src/index.ts` snapshot export + `apps/dashboard/src/snapshot.ts` tile manifest.
7. **RECOMMENDATION**: Register as PARTIAL (2-feed; no permits, no deeds). The 311 watermark is stale (22 days) — the staleness probe will alarm until the ETL resumes. SLA is fresh and snapshot-mode.
