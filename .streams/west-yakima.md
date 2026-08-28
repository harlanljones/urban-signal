# Stream log — west-yakima — 2026-08-28

## Claim

- **Stream id:** `city-yakima`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/yakima.py`
  - `apps/api/src/producers/field_maps_yakima.py`
  - `apps/api/tests/unit/test_producers_yakima.py`
- **Spine files I expect to need:** NONE (leaf-only; no spine holds — the
  spine delta is a written handoff, not an edit)

## Intent

Onboard Yakima, WA (US-239) as a West-region metro: live-probe
yakimawa.gov open data (ArcGIS/Socrata) for 1-4 official municipal feeds
(permits / 311 / SLA / deeds; Yakima County deeds if reachable). If feeds
verify, build the Yakima leaf (spatial + field maps + spine-stable tests
with byte-verbatim live fixtures through the real client path). If no
verifiable official feed exists, report REJECT with evidence — never a
stale mirror.

## Decisions

- 2026-08-28 — Claimed stream `city-yakima` on branch
  `chore/restore-metros-and-columbus`; working tree was stashed by a
  concurrent process on main, switched to the ticket's branch (clean).
- 2026-08-28 — PHASE A probe (all live, all WGS84 native): found the city's
  real ArcGIS open data platform. `opendata.yakimawa.gov` is an ArcGIS Hub
  (org `drBwGNA3YMS2QPJd`, urlKey `yakima`, 57 datasets) but the Hub is only
  the door — the feed endpoints are on `gis.yakimawa.gov` REST. **No Socrata
  exists** (`data.yakimawa.gov` DNS-fails).
- 2026-08-28 — **PERMITS verified live**:
  `gis.yakimawa.gov/arcgis/rest/services/Planning/BuildingPermits/FeatureServer/0`
  — 2,228 rows, native point geometry (outSR=4326 WGS84 on every row),
  watermark `IssuedOnDate` newest `1787270400000` = `2026-08-21T00:00:00+00:00`
  (two co-newest rows); windows 7d=2 / 30d=87 / 60d=163; layer holds a
  ~2022-10 → now window (min(date) not staleness); host ACCEPTS ISO date
  literals (not an ANSI_DATE_LITERAL_HOSTS candidate); `maxRecordCount` 2000,
  OID `OBJECTID`; no valuation/cost column.
- 2026-08-28 — **YakBack 311 verified live at the data layer but
  SPINE-BLOCKED**: `gis.yakimawa.gov/arcgis/rest/services/YakBack/PublicRequest/MapServer/0`
  — 16,833 rows, native point geometry, watermark `dateOpened` newest
  `1787951534000` = `2026-08-28T21:12:14+00:00` (same-day), windows 7d=100 /
  30d=365 / 60d=782. BUT its `status` column is an **integer** (1=open,
  2=closed): `Complaints311Producer` maps it straight into
  `Complaint311Event.status: Optional[str]`, pydantic v2 rejects the int, and
  EVERY row drops (empirically confirmed: parse_socrata_row → None, "Input
  should be a valid string"). Registering it before a spine str-coercion
  would silently stream zero events → kept Tier 3. YFD Calls for Service
  (fire/EMS dispatch, 17,032 rows, native points) is a documented candidate,
  not a 311-family feed. YPD `Crimes_public` is crime (family-gated).
- 2026-08-28 — **County DEEDS = STALE static extracts, not live feeds**:
  Yakima County AGOL org `9Qz94N8Zml9hnG84` (YakimaCounty) has
  `Res_Sales_History` (23,340 rows) and `Sales_History` (41,138 rows) but
  `Res_Sales_History` newest SALE_DATE is **2024-12-20** (SALE_YEAR roll
  2010→2024) and `Sales_History` DOCUMENT_D is **2016** — frozen snapshots.
  Not registered (Greenville SLA-snapshot precedent).
- 2026-08-28 — **Registration decision: ONE-FEED PARTIAL metro (permits
  only)**. 6 divisions / 9 submarkets (Downtown, Nob Hill, North Yakima,
  Summitview, West Valley, South 16th, South Yakima, Terrace Heights, East
  Valley) — all evidence-based on the ticket's suggested divisions.
- 2026-08-28 — Built the three leaf files; permits parses cleanly through the
  REAL `ArcGISClient._flatten_feature` lift + `DOBPermitsProducer`
  (`B260592` → city_id "yakima", status ISSUED, job_type OT, issuance
  2026-08-21, geometry 46.5805/-120.6023). Tests are spine-stable (no
  REGISTRY/FeedType-wiring/division-resolution/geocode-call-count asserts).

## Current step

VERIFY done: `test_producers_yakima.py` 36 passed; `-k yakima` 36 passed;
`-m interlock` 24 passed / 0 failed; `ruff check` clean on all three leaf
files. Stream is FINISHED.

## Outcome

**Feeds verified live (1 registered):** PERMITS —
`gis.yakimawa.gov/arcgis/rest/services/Planning/BuildingPermits/FeatureServer/0`,
platform arcgis, 2,228 rows, watermark `IssuedOnDate` newest
`2026-08-21T00:00:00+00:00` (verbatim `1787270400000`), columns PermitID /
PermitType / PermitStatus / ProjectDescription / SiteStreet / SiteCity /
SiteState / SiteZipCode / SiteZone / SubmittedOnDate / IssuedOnDate /
created_date / last_edited_date / DaysDifference / OBJECTID; native WGS84
point geometry (outSR=4326), needs_geocode=True (ADR 0004 address fallback on
SiteStreet), no cost column (unmapped → 0.0). 3 fixtures byte-verbatim
(OBJECTID 13469 B260592 / 16276 B260780 / 988 B240818) run through the real
client path.

**Verified but NOT registered (evidence in Decisions):** YakBack 311 (integer
`status` drops every row in Complaints311Producer — needs a spine str-coercion
before registration); Yakima County sales layers (stale static extracts:
2024-12-20 / 2016 cutoffs); YFD Calls for Service (fire/EMS dispatch — no
311-family fit); Crimes_public (family-gated crime). No SLA feed exists (city
licenses are a SmartGov document portal).

**Tests:** `test_producers_yakima.py` 36 passed (spine-stable: city_id
strings, no CityId import, no REGISTRY/FeedType-wiring/division-resolution/
geocode-call-count asserts). Gates: `-k yakima` 36 passed; `-m interlock`
24 passed / 0 failed; `ruff check` clean on the three leaf files.

## Spine delta (handoff — recommended, NOT applied)

- **CityId member:** `YAKIMA = "yakima"` (append to `CityId` enum).
- **Aliases** (`_HANDWRITTEN_ALIASES`): `yakima`, `yakima_wa`, `yakima-wa`,
  `yakima wa`.
- **REGISTRY entry** (`_HANDWRITTEN_REGISTRY[CityId.YAKIMA]`): name "Yakima",
  state "WA", center {"lat": 46.6021, "lng": -120.5059}, geometry from
  `src.spatial.cities.yakima` (metro_bbox / division_bboxes / submarkets /
  divisions), datasets {PERMITS: `get_yakima_dataset(FeedType.PERMITS)`}.
- **Config** (`src/config.py`): add `yakima_permits_url =
  "https://gis.yakimawa.gov/arcgis/rest/services/Planning/BuildingPermits/FeatureServer/0"`
  and point the spec's endpoint at it.
- **311 follow-up (do NOT register yet):** the YakBack 311 feed is live but
  its integer `status` column drops every row. Spine must str-coerce
  `status` in `Complaints311Producer` (or the layer must publish a string
  status) before registering
  `gis.yakimawa.gov/arcgis/rest/services/YakBack/PublicRequest/MapServer/0`
  (watermark `dateOpened`, id_keys `requestId`, producer_key "311").
- **Not a REJECT:** permits verifies and is registered (partial metro, same
  shape as Greenville/Tucson one-feed leaves).
