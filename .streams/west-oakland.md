# Stream log — west-oakland — 2026-08-28

## Claim

- **Stream id:** `west-oakland` (US-223, West-region metro-expansion wave 7)
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/oakland.py` (new)
  - `apps/api/src/producers/field_maps_oakland.py` (new)
  - `apps/api/tests/unit/test_producers_oakland.py` (new)
  - `.streams/west-oakland.md` (this log)
- **Spine files I expect to need:** NONE (leaf contract; spine delta reported in Outcome)

## Intent

Live-probe official Oakland, CA feeds (Socrata data.oaklandca.gov primary; ArcGIS
secondary; Alameda County for deeds reachability). Register 1-4 verified feeds as
`FEED_SPECS` in a leaf-local `cities/oakland.py` + per-feed field maps + spine-stable
tests with byte-verbatim live fixtures through the real client path. Honest
handling: mixed-CRS, future-date sentinels, ANSI-date hosts, needs_geocode per
ADR-0004, partial registration. If no verifiable official feed exists → REJECT
with evidence. No commits, no Linear updates, no spine edits.

## Decisions

- 2026-08-28 — Claim filed. Ticket US-223 body read: "Data source: Socrata —
  data.oaklandca.gov, Fit: High". Probe-first contract acknowledged.
- 2026-08-28 — Baseline: branch `chore/restore-metros-and-columbus` checked out in
  worktree (git reports `main` at worktree root; shared tree, no branch/commit
  changes by this stream). Interlock baseline expected 24 passed — will verify.
- 2026-08-28 — Phase A evidence (data.oaklandca.gov IS Socrata; catalog = 313
  datasets enumerated via api.us.socrata.com catalog/v1 domains filter):
  - **311 VERIFIED** — `quth-gb8e` "Service requests received by the Oakland Call
    Center (OAK 311)". rowsUpdatedAt 2026-08-28T13:05:30Z; 1,185,559 rows,
    requestid unique (count distinct == count). Watermark `datetimeinit`
    (calendar_date), newest verbatim `2026-08-28T04:59:31.000`. Columns:
    requestid, datetimeinit, source, description, reqcategory, reqaddress
    (location), status, referredto, datetimeclosed, srx, sry, councildistrict,
    beat, probaddress, city, state, zipcode, :@computed_region_w23w_jfhw.
    Geometry: **srx/sry carry WGS84 degrees despite x/y names** (srx=lng,
    sry=lat; verified 2023-2026 rows across Phone/SeeClickFix sources — values
    -122.18..-122.29 / 37.73..37.81). `reqaddress` location dict carries
    garbage on SeeClickFix rows (lat 30.0099, lng -141.219) — never mapped.
    Null srx/sry: 23,897 (2%) → ADR-0004 geocode on probaddress. Cadence:
    17,715 rows since 2026-07-01, 26,788 since 2026-06-01. No future-dated rows.
  - **CRIME VERIFIED** — `ppgh-7dqv` "CrimeWatch Data" (OPD CrimeWatch full
    dataset). rowsUpdatedAt 2026-08-27T12:51:07Z; 1,281,231 rows. Watermark
    `datetime`, newest verbatim `2026-08-25T22:57:00.000`. Columns: crimetype,
    datetime, casenumber, description, policebeat, address, city, state,
    location (Socrata point), :@computed_region. Geometry: location = GeoJSON
    Point {coordinates:[lng,lat]} WGS84 — read natively by the crime parser's
    point-container fallback. Null location 58,587 (4.6%); address text present
    on 95.4% → ADR-0004-eligible (coordinates AND address). casenumber NOT
    unique (case 26-036393 carries 3 descriptions) → id_keys
    [casenumber, description]. Archive spans 1950-01-04 → 2026-08-25. No
    future-dated rows. Sibling rolling 90-day view `ym6k-rx7a` (7,990 rows,
    `location_1`) NOT registered: parser's GeoJSON fallback reads row["location"]
    only; the full archive serves history + 1-day freshness.
  - **PERMITS NOT AVAILABLE**: 0 permit/building-permit datasets in the 313;
    Accela citizen-portal hosts (acacontrib.oaklandca.gov,
    aca.oaklandca.gov) unreachable (HTTP 000); no Oakland building-permits
    feature service on ArcGIS Online.
  - **SLA NOT AVAILABLE**: no business-license/tax registry in the catalog;
    AGOL has only parcel NAICS overlays.
  - **DEEDS NOT AVAILABLE**: Alameda County LANDATA (landata.acgov.org)
    unreachable (HTTP 000); no anonymous bulk API. Partial registration
    without deeds per ticket.
- 2026-08-28 — Feed decision: TWO feeds (311 + crime). Metro bbox rectangle
  admits Alameda/Emeryville/Piedmont/San-Leandro-fringe (documented
  tradeoff, permissive-bbox doctrine). 7 divisions, 13 submarkets.
  No order_by on socrata specs (NYC precedent: stable `:id` pagination);
  no watermark_exclude (0 future-dated rows both feeds).

## Current step

Phase C — verification (leaf files already written by prior run; now
auditing, running tests, and filling Outcome + Spine delta).

## Verification

### Leaf-audit (spine-stable)

- `OAKLAND_CITY_ID: str = "oakland"` — plain string, no CityId import.
- No `CityId`, `REGISTRY`, `scheduler`, `division_resolution`, or
  `geocode_row_if_declared` call-count assertions anywhere.
- `FeedType` imported in test file (line 59) — standard leaf pattern
  (portland, tempe, scottsdale, etc. all do the same); used only to call
  `get_oakland_dataset(FeedType.*)`, never to assert on REGISTRY.
- FEED_SPECS extra dict keys match DatasetSpec dataclass fields exactly
  (`expected_cadence_days`, `watermark_exclude`, `ingestion_mode`,
  `needs_geocode`, `geocode_context`, `field_map`). `scope` is filtered
  out in `get_oakland_dataset` — not a DatasetSpec field.
- Byte-verbatim fixtures verified live: `_SR_1661517` and
  `_CRIME_26_036393A` match `$limit=1` probes exactly.

### Live re-probe (2026-08-28, $limit=1)

**311** `quth-gb8e`:
- Row 1661517, `datetimeinit` 2026-08-28T04:59:31.000
- srx=-122.28556105813014, sry=37.81142799277458 (WGS84 degrees)
- reqaddress poisoned (lat 30.009927, lng -141.219150)
- probaddress "1651 ADELINE ST", zipcode 94607, CCD3

**Crime** `ppgh-7dqv`:
- Case 26-036393A, `datetime` 2026-08-25T22:57:00.000
- location `[-122.23658, 37.79991]` (GeoJSON Point)
- address "1100 E 28TH ST", policebeat 17Y

### Test results

| Gate | Result |
|---|---|
| `test_producers_oakland.py` | 35 passed |
| `-k oakland` | 37 passed |
| `-m interlock` | 24 passed (leaf-naming pin failure is spine-owned, ignored) |
| `ruff check` on 3 files | All checks passed |

## Outcome

**Phase A: ACCEPT.** Two feeds verified (311 `quth-gb8e` + crime `ppgh-7dqv`)
on the official Socrata domain `data.oaklandca.gov`. PERMITS, SLA, and DEEDS
absent — partial registration per ticket. Both feeds carry coordinate
coverage with ADR-0004 geocode supplement. 311 has a srx/sry name trap
(columns named like projected x/y but carry WGS84 degrees) and a poisoned
reqaddress container — both handled in the field map. Crime has a non-unique
casenumber (id_keys pairs with description). 13 submarkets, 7 divisions.

## Spine delta (do NOT apply in this stream)

Copy-paste for the serial interlock hold:

1. `CityId.OAKLAND = "oakland"` (after `NASHVILLE` or wherever the next
   slot is)
2. Aliases in `_HANDWRITTEN_ALIASES`:
   - `oakland`, `oakland_ca`, `oakland ca`, `oak`, `oak-town`,
     `east_bay`, `east bay`, `alameda_county`, `alameda county`
3. `city_registry.py` imports:
   - `from src.spatial.cities.oakland import OAKLAND_DIVISION_BBOXES, OAKLAND_DIVISIONS, OAKLAND_METRO_BBOX, OAKLAND_SUBMARKETS`
   - `from src.producers.field_maps_oakland import OAKLAND_311_FIELD_MAP, OAKLAND_CRIME_FIELD_MAP`
4. `cities/__init__.py` export block (same four constants +
   `is_in_oakland_metro`, `is_in_greater_oakland_metro`)
5. `config.py`:
   - `socrata_oakland_311_endpoint = "https://data.oaklandca.gov/resource/quth-gb8e.json"`
   - `socrata_oakland_crime_endpoint = "https://data.oaklandca.gov/resource/ppgh-7dqv.json"`
6. `REGISTRY[CityId.OAKLAND]`:
   - name `"Oakland"`, state `"CA"`
   - center `{"lat": 37.8040, "lng": -122.2712}`
   - metro_bbox `OAKLAND_METRO_BBOX` (min_lat 37.696, max_lat 37.885,
     min_lng -122.360, max_lng -122.114)
   - job_suffix `"oakland"`
   - datasets: `FeedType.COMPLAINTS_311` + `FeedType.CRIME` (partial register)
   - **311**: endpoint `settings.socrata_oakland_311_endpoint`, platform
     `socrata`, watermark `datetimeinit`, id_keys `["requestid"]`,
     interval_seconds 180.0, producer_key `"311"`,
     needs_geocode=True, geocode_context="Oakland, CA",
     field_map=OAKLAND_311_FIELD_MAP, expected_cadence_days=1,
     ingestion_mode="incremental"
   - **crime**: endpoint `settings.socrata_oakland_crime_endpoint`,
     platform `socrata`, watermark `datetime`, id_keys
     `["casenumber", "description"]`, interval_seconds 1800.0,
     producer_key `"crime"`, needs_geocode=True,
     geocode_context="Oakland, CA",
     field_map=OAKLAND_CRIME_FIELD_MAP, expected_cadence_days=1,
     ingestion_mode="incremental"
7. `METRO_META` in `apps/api/src/serving/dashboard.py` **and** byte-synced
   `apps/dashboard/public/index.html`:
   - `oakland: { name: 'Oakland' }`
8. Dashboard wiring per city-registration rule: `METRO_META` entry,
   snapshot export coverage, res-5 grid-tile coverage in published manifest,
   `index.html` static copy. Red gate until wired.

## Next step

None — final. Linear US-223 comment with this spine delta.