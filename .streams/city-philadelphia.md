# Stream log — city-philadelphia — 2026-08-23

## Claim

- **Stream id:** `city-philadelphia`
- **Leaf files I will create/edit:**
  - `src/spatial/cities/philadelphia.py`
  - `tests/unit/test_producers_philadelphia.py`
  - `.streams/city-philadelphia.md`
- **Spine files I expect to need (orchestrator-owned, NOT edited here):**
  - `src/spatial/city_registry.py` (CityId.PHILADELPHIA, aliases, registration)
  - `src/producers/permits_producer.py` + other producer wiring (`.carto` attr)
  - config / job-name wiring (`permits_philadelphia`)

## Intent

Wave C3: add Philadelphia as the first CARTO-platform city. Deliver a
spatial layer (metro bbox, None-guarded containment, 7–8 division bboxes,
16–18 submarkets, division catalog) and a unit-test module mirroring Detroit's
discipline — live-captured fixtures per feed, proposed DatasetSpec/field_map
assertions, xfail for spine-pending paths. All four feeds are CARTO tables at
phl.carto.com: `permits`, `public_cases_fc`, `business_licenses`, `rtt_summary`.

## Decisions

- 2026-08-23T00:00Z — Stream claimed; template copied as FIRST action.

All findings below verified live against phl.carto.com on 2026-08-23 via
`curl ... | python3 -m json.tool` (full row + `fields` type map per table).

- **SURPRISE — geocode_x/geocode_y are NOT lng/lat.** On `permits` and
  `business_licenses` these are PA South state-plane FEET (~x=2,698,810 /
  y=233,766). There is NO latitude/longitude column on either table; real
  coordinates live only in `the_geom` (hex WKB, SRID 4326), which CartoClient
  returns as an opaque string the parsers can't read. PROPOSAL: spine should
  register these specs with `extra["select"] = "*, ST_Y(the_geom) AS
  latitude, ST_X(the_geom) AS longitude"` so rows arrive with plain
  latitude/longitude keys matching the existing parser chains. Same for
  `rtt_summary` (deeds parser tolerates missing coords today, but geometry is
  better). `public_cases_fc` has real flat `lat`/`lon` columns — no select
  needed.
- **PERMITS** (`permits`, ~932k): keyset/date col `permitissuedate`
  (timestamptz); id `cartodb_id`; job_id=`permitnumber`; NO cost column
  anywhere → estimated_cost parses 0.0 by chain default (accepted).
  filing_date: no column → None.
- **COMPLAINTS_311** (`public_cases_fc`, ~5.9M): keyset `requested_datetime`;
  incident_id=`service_request_id` (chain term ✓); complaint_type=
  `service_name` (chain ✓); created `requested_datetime` (chain ✓);
  closed needs map entry `closed_datetime`. Newest-by-date row had NULL
  lat/lon AND null the_geom — fixture uses newest row WHERE lat IS NOT NULL
  (live-captured). NULL-coord rows return None from parser (guard).
- **SLA** (`business_licenses`): keyset `mostrecentissuedate`; year-3200
  sentinel SEEN LIVE ("3200-12-31T05:00:00Z") — CartoClient's
  `< '2101-01-01'` filter excludes it CLIENT-side (exact text in
  carto_client._sentinel_filter); parsers never see those rows. Map:
  license_id=`licensenum`, license_type=`licensetype`,
  effective_date=`initialissuedate`, expiration_date=`expirationdate`;
  dba falls to chain's business_name ✓; status via license_status ✓.
- **DEEDS** (`rtt_summary`, ~1.16M incl. mortgages): keyset `document_date`
  BUT document_date is frequently NULL and carries its own sentinel years
  (SEEN LIVE: "9798-06-12T08:00:00Z" on a real SATISFACTION OF MORTGAGE
  row). DECISION: watermark stays document_date (client-side sentinel+NULL
  filter makes it safe for paging), but recorded_date maps to
  **recording_date**, which exists and is populated even when document_date
  is null/sentinel — so the ingest-time-default fallback is a last resort,
  not the norm. Accepted caveat like NORA's zero price: mortgage/satisfaction
  docs carry NULL total_consideration → document_amount 0.0.
  doc_id=document_id (chain ✓); doc_type=document_type (chain ✓);
  parties grantors/grantees (semicolon-joined strings) via map;
  bbl=opa_account_num (often null — accepted).
- **job_suffix decision: `"philadelphia"`** (not "philly"); aliases
  {"philadelphia","philly","phl"}.
- **SURPRISE — 311 longitude chain lacks `lon`.** The shared complaints
  parser reads latitude/longitude/lng/long but NOT `lon` (Philly's
  spelling), so proposed COMPLAINTS_311 map carries
  latitude:["lat"], longitude:["lon"]. closed_datetime is already a chain
  term (map entry kept belt-and-braces). permitnumber/licensenum match no
  id-chain term → whole-row drops pre-map (Detroit pin shape).
- **KNOWN GAP — licensestatus spelling.** Table says `licensestatus` (no
  underscore); SLA parser reads row.get("license_status")/row.get("status")
  directly without first_mapped → status falls to end-date heuristic ACTIVE
  even on Inactive licenses. Spine follow-up proposed: add "licensestatus"
  term to the SLA status chain.
- **Chain-order caveat (DEEDS):** doc_amount checks total_assessed_value /
  assessed_value BEFORE the mapped document_amount; rtt_summary has an
  assessed_value column that would win when populated — acceptable today
  (null on most docs) but worth a spine look.
- Spatial layer: 8 divisions, 18 submarkets, metro bbox 39.87–40.14 /
  -75.28–-74.95 (PA city only). All live fixture coords verified inside:
  permits WKB → (39.94547, -75.14495); licenses WKB → (39.98243, -75.09347);
  rtt WKB → (39.97569, -75.14252); 311 lat/lon → (40.10042, -75.04347).

## Current step

Done. Spine applied by orchestrator; all gates green; dashboard map wired per the city registration rule.


