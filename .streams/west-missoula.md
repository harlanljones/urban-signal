# Stream log — west-missoula — 2026-08-28

## Claim

- **Stream id:** `west-missoula`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/missoula.py`
  - `apps/api/src/producers/field_maps_missoula.py`
  - `apps/api/tests/unit/test_producers_missoula.py`
- **Spine files I expect to need:** NONE

## Intent

Probe official City of Missoula (ci.missoula.mt.us) ArcGIS open-data feeds —
permits, 311/service requests, business licenses (SLA), and Missoula County
recorded deeds/sales. Register every feed that live-verifies with an official
feed (arcgis FeatureServer, native geometry or ADR-0004 geocode path). If no
verifiable official feed exists, REJECT with evidence — never a stale mirror.

## Decisions

<Appended as made. Findings go here the moment they are learned (F5) —
not at the end.>

- 2026-08-28 13:12 — Claimed stream from _TEMPLATE.md. Ticket US-235 body is
  thin ("ArcGIS Hub — city ArcGIS Hub"); must live-probe myself. Working tree
  is on `main` (dirty, concurrent waves in flight) — staying put rather than
  switching to `chore/restore-metros-and-columbus` to avoid disrupting
  in-flight agents; my three leaf files are all new untracked files so no
  conflict with the branch context.
- 2026-08-28 13:20 — Discovered official surfaces: City of Missoula Hub
  `missoulamaps-cityofmissoula.hub.arcgis.com` → city AGOL org
  `services.arcgis.com/HfwHS0BxZBQ1E5DY` (org id HfwHS0BxZBQ1E5DY, 282 Data
  items); Missoula County AGOL `services1.arcgis.com/NQWYt9dWr9BlL9QE`.
- 2026-08-28 13:25 — **PERMITS VERIFIED**: `AddressesWithPermits_mso`
  FeatureServer/0 = 122,448 rows, point geometry, store SR WKID 102700
  (NAD83 Montana State Plane, meters) with host honoring outSR=4326 (live
  fixtures return degrees). Watermark ApplicationDate (esriFieldTypeDate,
  epoch-ms→ISO on flatten): newest 1787788800000 = 2026-08-27T00:00:00+00:00,
  0 nulls, 0 future sentinels. id = RecordID (e.g. "2026-MSS-SWR-00946");
  OBJECTID is rebuild-dependent (newest live row = OBJECTID 1). max_record_count
  1000. No issuance-date column, no cost/valuation column. Null geometry 0 in
  3,000-row scan across 6 offsets. expected_cadence_days=1 (watermark 1 day
  old at probe).
- 2026-08-28 13:30 — **311 REJECTED**: no general citizen-request feed on
  either org. County `311_Debris_Overgrowth_WFL1` (240 rows) is a STALE
  PITTSBURGH MIRROR — neighborhoods "Brookline"/"Swisshelm Park", geometry
  -80.02°/40.39° (~1,600 mi from Missoula), Date 2022-08-31. City
  `Illicit_Discharge` (310 rows) and county `MS4_Maintenance_Request` (16
  rows) are narrow Survey123 stormwater surfaces. Not registered.
- 2026-08-28 13:30 — **SLA REJECTED**: no business-license feed on either
  org (title searches "license"/"business": 0 feeds on both).
- 2026-08-28 13:35 — **DEEDS PARTIAL**: Missoula County publishes no bulk
  recorded-document/sales feed on AGOL (org search for
  sale/deed/transfer/assess/appraisal: 0 Feature Services). `TaxAll` (60,807
  tax parcels, polygon) is assessment parcels with `conveyancedocs` string
  refs — not sales. Clerk & Recorder recorded documents are a search portal.
  Partial (permits only) is the honest shape.
- 2026-08-28 13:45 — Decided on divisions from the official 20-neighborhood
  `Neighborhoods_mso` layer (live probe): 7 boroughs / 20 submarkets, all
  submarket names = official city neighborhoods (Heart of Missoula,
  University District, Rose Park, Southgate Triangle, Miller Creek, Grant
  Creek, Lower/Upper Rattlesnake, Captain John Mullan, etc.).
- 2026-08-28 13:50 — Written the three leaf files:
  `apps/api/src/spatial/cities/missoula.py` (bbox, 7 divisions, 20
  submarkets, permits FEED_SPEC, `get_missoula_dataset`), 
  `apps/api/src/producers/field_maps_missoula.py`, 
  `apps/api/tests/unit/test_producers_missoula.py` (32 tests, 3 byte-verbatim
  fixtures through the real ArcGISClient flatten lift).
- 2026-08-28 14:00 — Verified: `pytest tests/unit/test_producers_missoula.py`
  32 passed; `pytest -k missoula` passed; `pytest -m interlock` 24 passed;
  ruff clean on all three files.

## Current step

DONE — leaf build + verification complete.

## Next step

Spine hold (not mine — leaf stream): register `CityId.MISSOULA` + aliases +
REGISTRY entry (copy the permits spec from `MISSOULA_FEED_SPECS`) + config
endpoint settings + METRO_META/dashboard byte-sync per the city-registration
rule. Recommend Linear comment on US-235: permits-only partial registration
(122,448 rows, watermark 2026-08-27); 311/SLA/deeds rejected with evidence.

## Outcome

- **Feeds verified:** 1 — PERMITS `AddressesWithPermits_mso` (arcgis
  FeatureServer/0, city AGOL org services.arcgis.com/HfwHS0BxZBQ1E5DY).
  122,448 rows, point geometry (store SR 102700 Montana State Plane meters,
  host honors outSR=4326), watermark ApplicationDate newest
  2026-08-27T00:00:00+00:00 (1787788800000), 0 nulls, 0 future sentinels.
- **Feed rejections:** 311 (none; county layer is stale Pittsburgh mirror),
  SLA (none on either org), DEEDS (no bulk feed; partial).
- **Tests:** 32 pass (`test_producers_missoula.py`), `-k missoula` pass,
  `-m interlock` 24 pass, ruff clean.

## Spine delta

- Add `CityId.MISSOULA` member `MISSOULA = "missoula"` plus ALIASES entries
  (`missoula`, `missoula-mt`, `missoula_mt`, `missoula county`? county not a
  city alias — keep `missoula` + `missoula-mt` + `missoula_mt`).
- REGISTRY entry: name "Missoula", state "MT", center {lat 46.8721, lng
  -113.9940}, metro_bbox/division_bboxes/submarkets/divisions = the leaf's
  MISSOULA_* dicts (import `REGISTRATION` from the leaf or copy the dicts),
  datasets = {FeedType.PERMITS: copy of MISSOULA_FEED_SPECS["permits"] spec}
  — endpoint
  `https://services.arcgis.com/HfwHS0BxZBQ1E5DY/arcgis/rest/services/AddressesWithPermits_mso/FeatureServer/0`,
  watermark_col ApplicationDate, id_keys [RecordID, OBJECTID], oid_field
  OBJECTID, max_record_count 1000, order_by "ApplicationDate DESC",
  expected_cadence_days 1, needs_geocode False, field_map PERMITS_FIELD_MAP,
  topic raw.municipal.permits, interval_seconds 300.0.
- No config endpoint setting needed (spec carries the full endpoint URL,
  like Anaheim/Stockton leaves); verify config.py needs nothing new.
