# Wave 5 — Lynchburg, VA (LEAF)

**Ticket:** US-318
**Agent:** leaf-implementation
**Status:** complete
**Claimed:** 2026-08-28

## Scope
- `apps/api/src/spatial/cities/lynchburg.py` (new)
- `apps/api/src/producers/field_maps_lynchburg.py` (new)
- `apps/api/tests/unit/test_producers_lynchburg.py` (new, 59 tests)
- `.streams/dispatch-log.md` (one row)

## Out of scope
city_registry.py, config.py, serving/dashboard.py, cities/__init__.py,
existing tests, apps/product/**, git commit. No CityId import — all
`city_id="lynchburg"` strings.

## Outcome — completed (2026-08-28, live re-probe)

All three feeds re-probed live against
`mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer`
(curl, one service hosts everything):

| Feed | Endpoint | Newest row | Totals | Live checks |
|---|---|---|---|---|
| PERMITS | `/37` (TRAKiT tabular; `/18` points = T1 path) | StartDate **2026-08-26** (epoch-ms 1787702400000) | 49,757 | 7d **36**, Aug **134** — daily cadence confirmed |
| SLA | `/33` (tabular; `/2` points = T1 path) | LicenseIssued **2026-08-21** (1787270400000) | 2,182 | 7d **1**; typed-2026 **102** (probe's "YTD 77" was a narrower cohort window — recorded in docstring) |
| DEEDS | `/34` (tabular; no point layer) | SaleDate **2026-08-26** (1787702400000) | 195,460 | 7d **38** — same-day live |

Fixture rows byte-verified live (≥2/feed): permits COM26-00293 (Azdel,
$75k) / COM26-00381 ($150k) / RES26-00798 (NEW CONSTRUCTION); SLA 4609
"031386" Needle Ninja LLC / 4605 "031382" Riverfront Entertainment
Foundation (TradeName empty on both — Company is the live id/dba
fallback); deeds LRSN 8921 + 17439 (DocNo 260000257, $0 WILL split across
two LRSNs, fixed-width space padding) / LRSN 14196 (260005545, $180,000).
DocumentNo arrives space-padded to 32 chars — the producer's doc_id
`.strip()` absorbs it (test asserts the stripped value).

## Findings recorded in the leaf module docstring

- **ESRI_OID trap (new vs probe):** layer `/34` publishes NO
  `objectIdField` in its layer JSON — its OID column is `ESRI_OID`, and
  `orderByFields=OBJECTID` returns ArcGIS error 400 (verified live). The
  client's metadata fallback would pin `OBJECTID` and 400 every deeds
  page, so the deeds spec declares `order_by="ESRI_OID"` (the only kwarg
  `build_adapter_request` forwards for arcgis) plus `oid_field="ESRI_OID"`.
- All three watermarks are true date columns → ISO after client flatten,
  no ADR-0005 text-watermark declarations needed anywhere; plain ISO
  string comparison (`StartDate >= '2026-08-26T00:00:00+00:00'`) verified
  working on this host — **no `ANSI_DATE_LITERAL_HOSTS` entry required**.
- Deeds geocoding is probe Path A, wired as the typed
  `parcel_join={"parcel_layer": …/41, "join_key": "LRSN",
  "geometry_source": "centroid"}` (DC precedent) — the
  `run_stream` enrichment sets lat/lng before parse; unenriched rows stay
  lossless with null coords.
- No `Status` server-side filter on permits (probe's registration sketch
  registers the table whole; APPROVED/FINALED/EXPIRED/IN REVIEW
  vocabulary recorded in scope).
- 311 absent (TRAKiT Violation Cases is code enforcement — not registered).

## Changeset
- `apps/api/src/spatial/cities/lynchburg.py` — new leaf module: METRO_BBOX
  grounded in the live `/41` Parcel-layer extent (lat 37.3326-37.4694,
  lng -79.2714--79.0850), 3 divisions / 7 submarkets (Downtown, Riverfront,
  Diamond Hill, Tinbridge Hill, Heritage, Boonsboro, Wyndhurst — Forest
  edge NOT evidenced in probe, omitted), FEED_SPECS, `get_lynchburg_dataset`,
  canonical `__all__`, `REGISTRATION`.
- `apps/api/src/producers/field_maps_lynchburg.py` — new; three maps; deeds
  `doc_type` deliberately UNMAPPED (ConveyanceForm/SaleType are
  space-padded fixed-width strings; unmapped → producer defaults "DEED").
- `apps/api/tests/unit/test_producers_lynchburg.py` — new; 59 tests,
  spine-stable per the wave-5 contract: parse fields, source-neighborhood
  passthrough, H3 from fixture coords (res-7 equality vs independent h3
  computation), bbox containment, field-map mappings. NO
  division/borough-resolution asserts, NO geocode-hook call-count asserts.

## Gates
- Leaf suite: **59/59 passed**; `-k lynchburg`: **61 passed** (includes
  `test_leaf_has_canonical_constants[lynchburg]` — auto-discovered).
- Interlock: **24 passed / 0 failed** (gate grew 22→24 via in-flight spine
  edits; wave-4's "22/22" number is stale).
- Full suite: **2021 passed / 3 skipped / 1 failed** — the single failure
  is the spine-owned leaf-naming count pin (`== 62`; concurrent wave-5
  leaves make 63+). Orchestrator bumps the pin when landing the spine.

## Spine delta (for orchestrator)

1. **FeedType enum:** no new members needed — PERMITS / SLA / DEEDS all
   exist; COMPLAINTS_311 stays unregistered (no municipal 311 extract).
2. **CityId + aliases:** add `CityId.LYNCHBURG = "lynchburg"` plus
   `_HANDWRITTEN_ALIASES` entries (e.g. `"lynchburg"`, `"lynchburg, va"`,
   `"lynchburg va"` → `CityId.LYNCHBURG`).
3. **CityRegistration** in `_HANDWRITTEN_REGISTRY` —
   `CityId.LYNCHBURG: CityRegistration(
   city_id=CityId.LYNCHBURG, name="Lynchburg", state="VA",
   center=LYNCHBURG_CENTER (37.4135, -79.1422),
   metro_bbox=LYNCHBURG_METRO_BBOX,
   division_bboxes=LYNCHBURG_DIVISION_BBOXES,
   submarkets=LYNCHBURG_SUBMARKETS, divisions=LYNCHBURG_DIVISIONS,
   job_suffix="lynchburg", datasets={…})` with three DatasetSpecs:

   | Feed | endpoint (config settings name + default URL) | watermark_col | id_keys | cadence | notes |
   |---|---|---|---|---|---|
   | PERMITS | `arcgis_lynchburg_permits_url` = `https://mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer/37` | `StartDate` | `["RecordNo","OBJECTID"]` | **1d** (7d=36, same-day) | `order_by="OBJECTID"`, `oid_field="OBJECTID"`, `max_record_count=50000`, `needs_geocode=True`, `geocode_context="Lynchburg, VA"`, `non_spatial=True`, `field_map=PERMITS_FIELD_MAP` |
   | SLA | `arcgis_lynchburg_sla_url` = `…/MapServer/33` | `LicenseIssued` | `["LicenseNumber","OBJECTID"]` | **365d** (annual mid-year renewal trickle; 7d=1 is the register's nature) | same flags; `field_map=SLA_FIELD_MAP` |
   | DEEDS | `arcgis_lynchburg_deeds_url` = `…/MapServer/34` | `SaleDate` | `["LRSN","DocumentNo"]` | **1d** (same-day circuit-court pull; 7d=38) | `order_by="ESRI_OID"` **mandatory**, `oid_field="ESRI_OID"`, `parcel_join={"parcel_layer": …/MapServer/41, "join_key": "LRSN", "geometry_source": "centroid"}`, `needs_geocode=True`, `non_spatial=True`, `field_map=DEEDS_FIELD_MAP` |

   All specs: `platform="arcgis"`, `topic=settings.topic_{permits,sla,deeds}`
   (existing settings — no new config keys beyond the three URLs),
   `interval_seconds` 300/600/600. No text-watermark declarations (all
   date-typed). No `ANSI_DATE_LITERAL_HOSTS` change (host accepts plain
   ISO string comparisons — verified live).
4. **METRO_META:** `"Lynchburg, VA"` — plus dashboard chip, `?city=`
   deep link, snapshot export coverage, res-5 grid-tile manifest coverage,
   and the byte-synced `apps/dashboard/public/index.html` static copy
   (city-registration rule). Then bump `test_city_leaf_naming.py`
   count pin to the new leaf total and reconcile the two leaf-test
   behaviors that change post-registration: SLA geocode hook becomes
   spec-gated (`spec.needs_geocode` resolves) and deeds
   `run_stream` parcel enrichment activates — parse-level assertions in
   `test_producers_lynchburg.py` were written to be invariant to both.
5. **Watermark windows (re-stamped 2026-08-28, all feeds):** PERMITS
   StartDate 2026-08-26 (49,757 total; 7d 36; Aug 134); SLA LicenseIssued
   2026-08-21 (2,182 total; 7d 1; typed-2026 102); DEEDS SaleDate
   2026-08-26 (195,460 total; 7d 38). All three ≤72h of implementation.
