# wave5-anchorage — US-330 Anchorage, AK (leaf implementation)

**Status: DONE (leaf)** — 2026-08-28, LEAF-IMPLEMENTATION agent (resume after
early prior-attempt death; only the field map existed).

## Scope (leaf contract)

- `apps/api/src/spatial/cities/anchorage.py` (new) ✅
- `apps/api/src/producers/field_maps_anchorage.py` (verify/fix) ✅
- `apps/api/tests/unit/test_producers_anchorage.py` (new) ✅
- `.streams/wave5-anchorage.md` + one dispatch-log outcome row ✅

**Forbidden (spine-held):** `city_registry.py`, `config.py`,
`serving/dashboard.py`, `cities/__init__.py`, existing test files,
`apps/product/**`. No git commit.

## Intent

DEEDS-only Tier-1 metro (per `docs/research/probe-anchorage.md`): assessor
`PropertyInformation_Hosted/FeatureServer/0` on
`services2.arcgis.com/Ce3DhLRthdwbHlfF`, watermark `Deed_Date`, daily
`PUBDATE` batch republish, last-deed-per-parcel snapshot grain, native parcel
polygons (`needs_geocode` NOT declared). Leaf ships `ANCHORAGE_*` constants
(5 divisions / 8 submarkets), DEEDS spec + field map, 40 spine-stable
producer-parse tests, and live re-probe fixtures captured byte-verbatim.

## Decisions

- 2026-08-28 (prior attempt) — reference analog `2a70e39:...rochester.py`
  did not exist then; durham was used as the deeds-led analog. 2026-08-28
  (resume) — rochester.py is NOW committed at `89d4307` and was mirrored as
  the designated analog (spec shape, `get_anchorage_dataset`, `__all__`).
- Field-map FIX vs prior attempt: added `address_street: ["Parcel_Address"]`
  (the composed site-address column; the five `GIS_Site_Street_*` parts are
  not `first_mapped`-concatenatable) and `zipcode: ["GIS_Site_Zipcode"]`
  (declarative address surface); restructured to `DEEDS_FIELD_MAP` +
  `FIELD_MAP` (rochester shape). `document_amount`/`doc_type` stay UNMAPPED
  (no price/deed-type column; assessed values must not masquerade — NOLA
  precedent); `party2_grantee: ["Owner_Name"]` (snapshot grain: current
  owner = last deed's GRANTEE, deliberately NOT durham's owner→grantor).
- Future `Deed_Date` sentinels (5 live, max 2035-03-03) are excluded at
  source by spec `where: "Deed_Date <= CURRENT_TIMESTAMP"` (tucson
  discipline; verified live). `watermark_exclude` deliberately NOT set —
  the arcgis path ignores it (CSV-client-only); scheduler US-111 future
  guard is the second line of defense.
- `expected_cadence_days: 3` — BATCH publication (daily `PUBDATE`
  republish; recordings land on business days), so Fri→Mon is a NORMAL
  3-day watermark gap; the alarm fires only when the daily batch stalls
  past a full weekend plus Monday. No `alarm_exempt` (the pace is healthy:
  7d=106 non-future rows at probe).
- Host accepts ISO-string date comparisons (`Deed_Date >
  '2026-08-25T12:00:00+00:00'` verified live) — NOT an
  `ANSI_DATE_LITERAL_HOSTS` candidate.
- Timezone quirk (module docstring): `Deed_Date`/`PUBDATE` are the layer's
  only `esriFieldTypeDate` columns; epoch-ms on the wire stamped **noon
  UTC** (`1787659200000` → `2026-08-25T12:00:00+00:00`), not local-midnight
  AKST/AKDT; client flattens to ISO UTC and `_parse_datetime` reads it via
  `fromisoformat`.
- Test guidance honored: no assertions on division/borough resolution
  results or geocode-hook call counts. Assert parse fields, source-
  neighborhood passthrough, H3 from fixture coords, bbox containment via
  leaf helpers, field-map mappings, watermark typing.

## Live re-probe (2026-08-28, re-stamped watermark)

- Newest NON-future `Deed_Date`: **2026-08-25** (probe-exact; three parcels
  on the date — OBJECTIDs 211515894 / 211522925 / 211547020). Five future
  sentinels still pin the lexical top (2035-03-03, 2034-01-30, 2029-05-06,
  2027-12-17, 2027-01-12).
- `PUBDATE` max **2026-08-26T23:23:21Z** — daily batch republish continues.
- `GIS_Site_City` counts: Anchorage 74,625 / Eagle River 9,653 / Chugiak
  3,274 / Girdwood 1,613 (Eagle River & Chugiak submarket strongly
  evidenced; Girdwood too thin to register but inside the metro box).
- Layer metadata re-verified: 84 attribute fields; `objectIdField`
  OBJECTID; `maxRecordCount` 2000; `esriGeometryPolygon`.
- Fixtures: 2 rows byte-verbatim (attributes + first ring at outSR=4326)
  — 211515894 (2101 W 47TH AVE, West Anchorage) and 211522925 (6620
  CIMARRON CIR, East Anchorage), centroids live-computed via the same
  shapely reduction the client performs.

## Gates

- `pytest tests/unit/test_producers_anchorage.py` — **40/40 passed**.
- `pytest tests/unit/test_city_leaf_naming.py -k anchorage` — **passed**.
- `pytest -m interlock -q` — **24/24 passed** (stays green).
- Full suite — **2150 tests / 1 failed / 0 errors / 3 skipped**; the ONLY
  failure is the spine-owned leaf-count pin (`test_all_expected_leaf_
  modules_present`, == 62; anchorage + concurrent wave-5 leaves make 69).

## Spine delta (orchestrator applies)

- `CityId.ANCHORAGE = "anchorage"` + ALIASES (`anchorage`, `anc`,
  `anchorage_ak` — spellings per house style) + `cities/__init__.py`
  re-exports of the leaf's `__all__`.
- `config.py`: `arcgis_anchorage_deeds_url: str = Field(default=
  "https://services2.arcgis.com/Ce3DhLRthdwbHlfF/arcgis/rest/services/
  PropertyInformation_Hosted/FeatureServer/0")`.
- `city_registry.py`: CityRegistration "Anchorage, AK" with the leaf's
  DEEDS DatasetSpec as-is (`ANCHORAGE_FEED_SPECS["deeds"]`): platform
  arcgis, watermark `Deed_Date`, id_keys Parcel_ID/GIS_ParcelNum11/OBJECTID,
  `where` sentinel guard, `order_by "Deed_Date DESC"`,
  `expected_cadence_days=3` (batch-publication rationale in scope),
  `needs_geocode=False`, `max_record_count=2000`, field_map =
  `field_maps_anchorage.DEEDS_FIELD_MAP`.
- `serving/dashboard.py` `METRO_META`: "Anchorage, AK" + `?city=anchorage`
  deep link + static `apps/dashboard/public/index.html` byte-synced copy.

## Current step / Next step

Leaf complete; nothing left. Orchestrator: apply the spine delta above,
bump the leaf-count pin (62 → 63+), re-run `pytest -m interlock`.
