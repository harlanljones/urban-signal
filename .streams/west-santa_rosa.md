# Stream log — west-santa_rosa — 2026-08-28

## Claim

- **Stream id:** `west-santa_rosa` (US-247, West-region metro-expansion wave)
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/santa_rosa.py` (new)
  - `apps/api/src/producers/field_maps_santa_rosa.py` (new)
  - `apps/api/tests/unit/test_producers_santa_rosa.py` (new)
  - `.streams/west-santa_rosa.md` (this log)
- **Spine files I expect to need:** NONE (leaf contract; spine delta reported in Outcome)

## Intent

Live-probe Santa Rosa, CA official feeds (srcity.org primary per ticket, but
ticket says "PowerBI only — Fit: Medium-Low"; data.sonomacounty.ca.gov open data
secondary; Sonoma County deeds reachability). Register 1-4 verified feeds as
`FEED_SPECS` in a leaf-local `cities/santa_rosa.py` + per-feed field maps +
spine-stable tests with byte-verbatim live fixtures through the real client
path. Honest handling: mixed-CRS, future-date sentinels, ANSI-date hosts,
needs_geocode per ADR-0004, partial registration. If no verifiable official
feed exists → REJECT with evidence. No commits, no Linear updates, no spine
edits.

## Decisions

- 2026-08-28 — Claim filed. Ticket US-247 body read: "Data source: PowerBI only
  — Insights.SRCity.org; Fit: Medium-Low". Probe-first contract acknowledged.
- 2026-08-28 — Baseline: branch `chore/restore-metros-and-columbus` checked out
  (shared worktree; no branch/commit changes by this stream). Interlock
  baseline expected 24 passed — verified 24/24 at finish.
- 2026-08-28 — Phase A platform enumeration:
  - **City of Santa Rosa — PowerBI-only confirmed.** `Insights.SRCity.org`
    (also `data.srcity.org`) is a PowerBI dashboard hub (Building Permits,
    Community Service Requests, Police Calls for Service, Engineering
    Permits, Water Utility Permits, etc.) with NO public raw API. `insights.srcty.org`
    (ticket's hostname) is dead (000). The city AGOL org
    `santarosa.maps.arcgis.com` (orgId BhTdzxiJkq4oXsPh) holds only STALE
    snapshots: Building Permits FeatureServer max IssuedDate 2018-06 / max
    LastUpdated 2018-06 (20,913 rows); CallsForService CurrentYear tabular
    2020-01 (62,558 rows); CallsForService FeatureServer empty template
    (count 0); Crimes FeatureServer empty template (count 0); Parcels_Sold
    (814 rows) + RC Building Permits (2,674 rows) are 2017 Tubbs-Fire
    recovery-only. No 311 / SLA / deeds layer found.
  - **Sonoma County — Socrata data.sonomacounty.ca.gov (SoCo Data).**
    Catalog has ~103 items. Live feeds: Sheriff's Incident Data (3rsj-iche),
    Sheriff's Event Data (bpq8-s7gr), Planning Permits (m689-iiuu),
    Construction Permits (88ms-k5e7), Defaulted Tax Data (bp8v-uax7),
    Arrest Data (f6uf-eqmk). County Recorder unreachable (000) — deeds N/A.
- 2026-08-28 — Phase A feed verification:
  - **CRIME VERIFIED** — `3rsj-iche` Sonoma County Sheriff's Office Incident
    Data. 329,685 rows total; 104,564 city=SANTA ROSA. Watermark `date_time`
    (calendar_date), max verbatim `2026-08-27T12:37:13.000`; `upload`
    column 2026-08-28 (daily). 100% id unique (329,685/329,685); 0 null
    locations. Columns: id, agency_code, agency, incident_number, date_time,
    incident_type, location_type, city, intersection, location (Socrata
    point {latitude,longitude}), location_address, upload, location_city/
    state/zip. Geometry: **native Socrata point** (WGS84 degrees). Cadence:
    30 SANTA ROSA rows last 7d / 132 last 30d / 261 last 60d (~4/day).
    No future-dated rows. Crime per ADR-0004 (coordinates AND address).
  - **EVENT DATA NOT REGISTERED** — `bpq8-s7gr` (2,359,410 rows, fresh
    2026-08-27T23:55) is police dispatch events for SCSO/Windsor/Sonoma PD
    only — location_city empty, 0 SANTA ROSA rows. Not a Santa Rosa feed.
  - **PLANNING PERMITS NOT REGISTERED** — `m689-iiuu` (5,463 rows) is
    unincorporated-county-only, address-only (no geometry → needs_geocode),
    and the watermark `started` is STALLED (max 2025-05-30 — no advancing
    rows for 15 months despite daily rowsUpdatedAt). Not a live feed.
  - **CONSTRUCTION PERMITS NOT REGISTERED** — `88ms-k5e7` (25,926 rows)
    unincorporated-only, APN-only (no address, no geometry). Unusable.
  - **DEFAULTED TAX NOT REGISTERED** — `bp8v-uax7` fresh but property/tax
    records, address-only, no geometry; not deeds/sales.
  - **ARRESTS NOT REGISTERED** — `f6uf-eqmk` only 6 SANTA ROSA rows; PII
    (arrestee names).
  - **DEEDS N/A** — Sonoma County Recorder unreachable (000).
- 2026-08-28 — Feed decision: ONE feed (crime). Metro bbox admits the
  unincorporated sheriff-incident fringe around Santa Rosa (documented
  tradeoff, permissive-bbox doctrine). 6 divisions / 12 submarkets.
  No order_by on the spec beyond `date_time DESC`; no watermark_exclude
  (0 future-dated rows).

## Current step

Done — leaf files written, verified, tests green.

## Next step

None — final.

## Outcome

**1 feed verified → ONE-FEED PARTIAL metro, registered as a leaf**
(`apps/api/src/spatial/cities/santa_rosa.py`, `field_maps_santa_rosa.py`,
`test_producers_santa_rosa.py`):

- **CRIME** — Sonoma County Sheriff's Office Incident Data
  (`https://data.sonomacounty.ca.gov/resource/3rsj-iche.json`, Socrata,
  Tier 1, daily). Watermark `date_time` max `2026-08-27T12:37:13`; id_keys
  `["id","incident_number"]`; 329,685 rows / 104,564 SANTA ROSA; native
  Socrata point geometry (WGS84 degrees, 0 null); needs_geocode=False.
  3 fixtures byte-verbatim re-verified live (IDs …BCF75F / …B96D83 /
  …E6816, newest 3 by date_time).
- **NOT registered (Tier 3, with evidence):** PERMITS (city AGOL stale
  2018; county planning permits unincorporated + address-only + stalled
  watermark; construction permits APN-only), COMPLAINTS_311 (PowerBI-only),
  SLA (none found), DEEDS (Recorder unreachable 000). No REJECT — one
  verifiable live official feed exists and is meaningful for the metro.

**Gates (all green):** test_producers_santa_rosa.py 32/32; `-k santa_rosa`
34 passed; `pytest -m interlock` **24 passed / 0 failed** (verified 24/24 at
finish-time run immediately after the leaf landed — gate green; leaf-naming
count pin not touched by this leaf); ruff on the three files: All checks
passed. No commits, no Linear updates, no spine edits.
**Interlock re-run caveat:** a LATER full-collection interlock run (post-leaf)
errors in collection (121) because the concurrent **US-372 spine stream** has
an in-flight edit to `src/spatial/cities/portland.py` importing
`src.producers.field_maps_state_licenses`, which does not exist yet on disk
(`.streams/us372-spine.md` in flight). Not this leaf's work, not this leaf's
files — resolves when that spine stream lands its module.

## Spine delta (for the orchestrator's spine hold)

Exact leaf-to-spine handoff — **recommended: register as a ONE-FEED CRIME
PARTIAL metro**:

1. **CityId enum member:** `CityId.SANTA_ROSA = "santa_rosa"` (add to
   `_HANDWRITTEN_ALIASES` too: `"santa_rosa"`, `"santa-rosa"`,
   `"santa rosa"`, `"sr"`, `"sonoma_county"` → CityId.SANTA_ROSA).
2. **Registry entry** (`_HANDWRITTEN_REGISTRY`, city_id=CityId.SANTA_ROSA,
   name="Santa Rosa, CA", state="CA"):
   - center: {"lat": 38.4405, "lng": -122.7144}
   - metro_bbox / division_bboxes / submarkets / divisions: take verbatim
     from `SANTA_ROSA_METRO_BBOX`, `SANTA_ROSA_DIVISION_BBOXES`,
     `SANTA_ROSA_SUBMARKETS`, `SANTA_ROSA_DIVISIONS` in
     `src/spatial/cities/santa_rosa.py`.
   - datasets: `{FeedType.CRIME: DatasetSpec(...)}` from
     `SANTA_ROSA_FEED_SPECS["crime"]` (endpoint above, platform "socrata",
     watermark_col "date_time", id_keys ["id","incident_number"],
     topic=settings.topic_crime, interval 300.0, producer_key "crime",
     expected_cadence_days 1, needs_geocode False, order_by "date_time DESC",
     field_map=CRIME_FIELD_MAP).
   - job_suffix: e.g. "santa_rosa".
3. **config.py:** add `santa_rosa_crime_endpoint: str =
   "https://data.sonomacounty.ca.gov/resource/3rsj-iche.json"` (Socrata
   platform → `socrata_santa_rosa_crime_endpoint` per repo convention).
4. **cities/__init__.py:** export the santa_rosa module symbols.
5. **serving/dashboard.py METRO_META** + regenerate
   `apps/dashboard/public/index.html` + snapshot export (city-registration
   rule — the city must appear on the map in the same spine hold).
6. **test_city_leaf_naming.py** count pin: bump to include the new leaf
   (spine-owned; the -k santa_rosa run adds the canonical-constants tests).
7. NO watermarks.py change needed (Socrata accepts ISO literals; no
   ANSI-date host). NO snap_sla_spec needed (crime-only partial — the
   zero-SLA-less invariant applies to PERMITS-registered partials; confirm
   with orchestrator if the invariant must be held for crime-only metros).

**Linear recommendation (comment on US-247):** REGISTER as one-feed CRIME
partial; city's live data is PowerBI-only, city AGOL stale; county Sheriff
Incident Data is the verifiable live feed (fresh daily, native geometry,
104k SANTA ROSA rows). Do not open a spine hold expecting permits/311/SLA/
deeds — none exist as public feeds.
