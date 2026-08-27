# Stream log — city-st-louis — 2026-08-27

Phase-2 leaf stream for Linear US-200: St. Louis, MO partial registration
(311 zip CSV + permits 30-day CSV + optional liquor SLA). Spine is serial
after this stream; do not edit spine files here.

## Claim

- **Stream id:** `city-st-louis`
- **Leaf files I will create/edit:**
  - `.streams/city-st-louis.md` (this file)
  - `apps/api/src/spatial/cities/st_louis.py` (NEW)
  - `apps/api/src/producers/field_maps_st_louis.py` (NEW)
  - `apps/api/tests/unit/test_producers_st_louis.py` (NEW)
  - `apps/api/src/producers/csv_client.py` (zip-member support IF required;
    this stream is the only one allowed to touch it)
  - `apps/api/tests/unit/test_csv_client.py` (only if csv_client.py changes)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html`
  - the four shared producers (`complaints_311_producer.py` etc.)

## Intent

Leaf-complete a PARTIAL St. Louis metro from
`docs/research/wave-3-probe-st-louis.md`: 311 `csb.zip` / year CSV,
permits ColdFusion 30-day CSV, optional liquor SLA snapshot. No deeds
(6-month lag). Tests pass without `CityId.ST_LOUIS`. Record an exact
spine delta. If CSVClient cannot read a zip member, add that as a leaf
edit to `csv_client.py` (not on the spine manifest) with tests.

## Decisions

- 2026-08-27 ~13:00 PT — Orchestrator dispatched this leaf after Honolulu
  and Orlando spines landed. Probe US-200 research file is complete.
- 2026-08-27 ~13:05 PT — Independent City of St. Louis only. Metro bbox
  excludes Clayton (~-90.338) and East St. Louis IL (~-90.151). Center
  38.6270, -90.1994. One division `STL_CORE`, six submarkets. `city_id=
  "st_louis"`, aliases include `stl`, `job_suffix="stl"`.
- 2026-08-27 — 311 `SRX`/`SRY` are EPSG:3857 Web Mercator meters. Helper
  `mercator_xy_to_wgs84` lives in `st_louis.py` (geo_utils.py is spine).
  Field map does **not** put srx/sry in lat/lng slots. Tests pin the
  1100 Ohio St sample `(-10043376.82, 4667655.54) → (-90.2212, 38.6219)`
  and that raw XY fail the WGS84 degree range. Wiring the helper into
  `complaints_311_producer.py` is a later spine hold.
- 2026-08-27 — CSVClient had no zip-member path. Additive `zip_member=
  '2026.csv'` kwarg extracts a named year file from `csb.zip`. Scheduler
  does not yet forward that kwarg (spine). `endpoint_by_year` values are
  member names (`2026.csv`), not URLs — `resolve_endpoint` must not treat
  them as URL replacements.
- 2026-08-27 — Permits: no permit number. Composite id helper
  `permit_composite_id` concatenates address|issuedate|applicationdescription.
  Scheduler `_extract_record_id` currently takes the first non-empty
  id_key (address) — collision risk documented. `ISSUEDATE` format
  `"%B, %d %Y %H:%M:%S"` is declared for CSVClient typed watermarks;
  shared permits `_parse_datetime` does not yet know that format (spine).
- 2026-08-27 — SLA liquor-only snapshot (Baltimore precedent).
  `STATUS_CODE='ACTIVE'`, drop expiration years 1969/3027. Leaf helpers
  `is_active_excise_license` / `is_excise_expiration_sentinel`. Do not
  register frozen ArcGIS Building_Permits, trades APIs, or deeds.
- 2026-08-27 — `zip_member` and `src_crs` are not DatasetSpec fields
  (US-186). Leaf getter strips them when building a typed spec; they
  stay on the dict extra for the spine copy.

## Current step

Spine applied 2026-08-27 ~13:35 PT (orchestrator). 311 zip + permits CSV +
liquor SLA. Mercator helper wired in 311 producer; `zip_member` on
DatasetSpec + scheduler; permits datetime format; composite permit id.
Interlock **22 passed**. Leaf 42 + csv_client 6 + scheduler green.

## Next step

Linear US-200 Done. No further code in this stream.

## Spine delta (do not apply in this stream)

```
# city_registry.py
CityId.ST_LOUIS = "st_louis"
ALIASES: st_louis, stl, saint_louis, st-louis, "st louis" → ST_LOUIS
import ST_LOUIS_* + REGISTRATION from cities.st_louis
REGISTRY[CityId.ST_LOUIS] = CityRegistration(
    city_id=CityId.ST_LOUIS,
    name="St. Louis",
    state="MO",
    center={"lat": 38.6270, "lng": -90.1994},
    job_suffix="stl",
    datasets={311, PERMITS, SLA}  # copy STL_*_SPEC; no DEEDS
)
# Promote extra zip_member / src_crs onto DatasetSpec or companion fields.

# cities/__init__.py — export st_louis

# config.py
csv_st_louis_311_endpoint = "https://www.stlouis-mo.gov/data/upload/data-files/csb.zip"
csv_st_louis_permits_endpoint = (
    "https://www.stlouis-mo.gov/customcf/endpoints/building-permits/"
    "building-permits-30-days-export.cfm?permitType=all&dataType=csv"
)
csv_st_louis_sla_endpoint = (
    "https://www.stlouis-mo.gov/data/upload/data-files/excise-data/"
    "excise-permits-licenses.csv"
)

# dashboard.py METRO_META (and index.html byte-sync)
st_louis: { name: 'St. Louis' }

# complaints_311_producer.py — apply mercator_xy_to_wgs84 when src_crs=EPSG:3857
#   (or state_plane_* analogue). Do not ingest SRX/SRY as degrees.
# dob_permits_producer.py — add "%B, %d %Y %H:%M:%S" to _parse_datetime
# scheduler.py — forward zip_member filename (resolved from endpoint_by_year
#   member names); keep endpoint as the zip URL.
```

## Pytest

- `tests/unit/test_producers_st_louis.py` — 42 passed (no CityId.ST_LOUIS)
- `tests/unit/test_csv_client.py` — 6 passed (2 existing + 4 zip-member)
