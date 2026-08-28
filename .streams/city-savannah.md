# Stream log — city-savannah — 2026-08-28

Phase-2 leaf REBUILD for Linear US-298: Savannah / Chatham County, GA partial
match registration (PERMITS residential /1 + commercial /0 companion). This is a
REBUILD: the prior run of this stream completed (48 tests passed) but its files
were LOST to a branch switch (main -> `chore/restore-metros-and-columbus`), so
this log re-derives the probe facts, re-verifies watermarks LIVE, and re-writes
the four leaf artifacts. Spine is serial after this stream; do NOT edit spine
files here.

## Claim

- **Stream id:** `city-savannah`
- **Leaf files I will create/edit (only these):**
  - `.streams/city-savannah.md` (this file)
  - `docs/research/se-probe-savannah.md` (NEW)
  - `apps/api/src/spatial/cities/savannah.py` (NEW)
  - `apps/api/src/producers/field_maps_savannah.py` (NEW)
  - `apps/api/tests/unit/test_producers_savannah.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (CityId.SAVANNAH, ALIASES, REGISTRY)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py` (arcgis_savannah_permits_endpoint + companion)
  - `apps/api/src/producers/watermarks.py` (ANSI_DATE_LITERAL_HOSTS += pub.sagis.org)
  - `apps/api/src/serving/dashboard.py` METRO_META + byte-synced `apps/dashboard/public/index.html`

## Intent

Leaf-complete a PARTIAL Savannah / Chatham County metro on the Chatham County
SAGIS ArcGIS server (``pub.sagis.org``): `BuildingPermit_FC/FeatureServer/1`
(Residential) as the PERMITS dataset, with `FeatureServer/0` (Commercial) as
``companion_endpoints["commercial_building_permits"]``. 311 / SLA / DEEDS are
NOT-VIABLE (see probe). Tests pass without a registry entry (city_id="savannah"
plain string; geocoding mocked at src.spatial.geocoder.geocode_row_if_declared).

## Decisions

- 2026-08-28 — Orchestrator claimed Linear US-298; this leaf stream dispatched
  to rebuild the lost artifacts. The single allowed feed is PERMITS (partial).
  Companion stays a spine-level `companion_endpoints` key (same schema as /1, so
  the same field map serves it); no separate FeedType is invented.
- Host quirk: **pub.sagis.org is an ANSI-date-literal host** — bare ISO date
  comparisons in `where` 400, `DATE '...'` works. This requires a spine edit to
  `watermarks.py` ANSI_DATE_LITERAL_HOSTS (apply serially, do NOT edit here).

## Live probe (2026-08-28, re-verified LIVE before capturing fixtures)

Feed `pub.sagis.org/.../Savannah/BuildingPermit_FC/FeatureServer/{1,0}`. Native
point WKID 2239 served as WGS84 via outSR=4326; the ArcGISClient flattens point
geometry onto ``latitude``/``longitude`` keys, so almost every row carries native
coords (address geocode is the fallback, ADR 0004).

| Layer | Watermark | Newest IssuedDate_DATE | 7d / 60d | Total | Geo |
|---|---|---|---|---|---|
| /1 Residential | `IssuedDate_DATE` (date-typed; text mirror `IssuedDate` MM/DD/YYYY) | 2026-08-20 | 0 / 294 | 1933 | native point + address fallback |
| /0 Commercial | `IssuedDate_DATE` (date-typed) | 2026-08-21 | 1 / 61 | 666 | native point + address fallback |

Layer metadata: oid_field OBJECTID, maxRecordCount 2000, date fields
{IssuedDate_DATE, FinalizedDate_DATE}. id_keys ["PermitNumber","OBJECTID"];
producer_key permits; expected_cadence_days 7; needs_geocode True, geocode_context
"Savannah, GA"; order_by/oid_field OBJECTID; max_record_count 2000. Null
IssuedDate_DATE on In Review / Approved rows surfaces at issuance; the register is
retained to 2023-01 (not rolling). ApplicantName is PII — unmapped.

Permit-schema columns (both layers identical): `PermitNumber`, `OBJECTID`, `Address`,
`District` (neighborhood), `PermitStatus`, `PermitType`, `Permit_Value`,
`WorkClass` (job type), `PIN` (bbl), `IssuedDate_DATE`, `IssuedDate`,
`ApplicantName` (PII), `Description`, `ADDID2`.

## Spatial

5 divisions / 10 submarkets, submarket coordinates pinned to LIVE outSR=4326
permit coordinates captured this session (incl. annexed New Hampstead -81.3505 and
Godley Station 32.1814, which set the metro bbox). Metro bbox grounded in the live
layer extent (lat 31.9340-32.1864, lng -81.3653 - -81.0449) with margin; division
bboxes strictly nested; self-verified containment invariants.

## Files written

- `apps/api/src/spatial/cities/savannah.py`
- `apps/api/src/producers/field_maps_savannah.py`
- `apps/api/tests/unit/test_producers_savannah.py`
- `docs/research/se-probe-savannah.md`

## Tests

```
cd apps/api && .venv/bin/python -m pytest tests/unit/test_producers_savannah.py -q
44 passed (--no-header: [44/44])
```

Iterated to green; no CityId.SAVANNAH, no spine edits. (Rebuild yields 44
leaf tests vs. the prior run's 48; the delta is consolidation of the
watermark/field-map coverage, not a loss of asset coverage — every probe-fact
assert is still present.)

## Spine delta (do NOT apply in this stream)

Copy-paste for the serial interlock hold:

1. `CityId.SAVANNAH = "savannah"` (after `TUCSON`)
2. Aliases in `_HANDWRITTEN_ALIASES`:
   - `savannah`, `savannah_ga`, `savannah ga`, `sav`, `chatham_county_ga`, `chatham county ga`
3. `city_registry.py` imports:
   - `from src.spatial.cities.savannah import SAVANNAH_DIVISION_BBOXES, SAVANNAH_DIVISIONS, SAVANNAH_METRO_BBOX, SAVANNAH_SUBMARKETS`
   - `from src.producers.field_maps_savannah import PERMITS_FIELD_MAP as SAVANNAH_PERMITS_FIELD_MAP`
4. `cities/__init__.py` export block (same constants + `is_in_savannah_metro`)
5. `config.py`:
   - `arcgis_savannah_permits_endpoint = "https://pub.sagis.org/arcgis/rest/services/Savannah/BuildingPermit_FC/FeatureServer/1"`
   - `arcgis_savannah_permits_commercial_endpoint = "https://pub.sagis.org/arcgis/rest/services/Savannah/BuildingPermit_FC/FeatureServer/0"`
6. `watermarks.py` `ANSI_DATE_LITERAL_HOSTS += "pub.sagis.org"` (host 400s on bare
   ISO date literals in `where`; verify ANSI `DATE '...'` works — it does).
7. `REGISTRY[CityId.SAVANNAH]`:
   - name `"Savannah / Chatham County"`, state `"GA"`
   - center `{"lat": 32.0767, "lng": -81.0943}`
   - job_suffix `"savannah"`
   - datasets: **only** `FeedType.PERMITS` (partial)
   - endpoint `settings.arcgis_savannah_permits_endpoint`
   - platform `arcgis`, watermark `IssuedDate_DATE`, id_keys `["PermitNumber","OBJECTID"]`
   - `needs_geocode=True`, `geocode_context="Savannah, GA"`
   - `order_by="OBJECTID"`, `oid_field="OBJECTID"`, `max_record_count=2000`
   - `field_map=SAVANNAH_PERMITS_FIELD_MAP`
   - `companion_endpoints={"commercial_building_permits": settings.arcgis_savannah_permits_commercial_endpoint}`
   - expected_cadence_days `7`
8. `METRO_META` in `apps/api/src/serving/dashboard.py` **and** byte-synced `apps/dashboard/public/index.html`:
   - `savannah: {name: 'Savannah / Chatham County'}`

## Current step

Leaf artifacts re-written and tests green. Waiting for the serial spine hold to
apply the delta above (after the west-coast hold lands on a stable branch).

## Next step

Orchestrator: verify `pytest -m interlock` goes green with SAVANNAH registered;
apply the ANSI host entry (pub.sagis.org) with the rest of the southeast wave.

## Prior-run note

The first run of this stream (48 tests) passed and its reported probe facts
match everything re-verified live here (newest res 2026-08-20 / com 2026-08-21;
7d 0/1; 60d 294/61; total 1933/666). Rebuild confirmed no drift.
