# Stream log — city-austin — 2026-08-23

## Claim

- **Stream id:** `city-austin`
- **Leaf files I will create/edit:** `src/spatial/cities/austin.py`, `tests/unit/test_producers_austin.py`, `.streams/city-austin.md`
- **Spine files I expect to need:** `src/spatial/city_registry.py` (CityId.AUSTIN, ALIASES, REGISTRY entry, config endpoints), shared producers untouched (field_map mechanism already landed in Wave B).

## Intent

Austin registers as a two-feed partial city (PERMITS `quv8-5ckq`, COMPLAINTS_311 `xwdj-i9he`, both Socrata data.austintexas.gov) with a full geography module (metro bbox, 6 division bboxes, 16 submarkets, BoroughMeta catalog with exactly-one claims), live-verified fixture tests mirroring NOLA discipline, and the proposed DatasetSpec field_map JSON recorded below for the orchestrator. Registration tests red until spine lands — expected.

## Decisions

- 2026-08-23 — Stream claimed; three-file constraint accepted.
- 2026-08-23 — **Registry-comment transcription (for orchestrator):** Austin SLA/DEEDS deliberately absent, LA-pattern. TABC statewide feeds (`7hf9-qc9f` "TABC License Information" 126k rows, `kguh-7q9z` "TABCLicenses" 78k on data.texas.gov) carry ZERO geocode columns (full column lists checked in research §Nearby-domain sweep) — registering means out-of-band address geocoding; parked. Travis County portal (`data.traviscountytx.gov`) is a FedRAMP Socrata shell: catalog API returns "Domain not found", `/api/views` 404s — county deeds unreachable via Socrata. data.austintexas.gov's own catalog is hollowed by the Texas ODP migration (unfiltered domain query returns only 3 internal Site Analytics views); legacy resource IDs still serve rows.
- 2026-08-23 — Live rows captured and verified untruncated: permits newest-by-issue_date = Parmer Commons finish-out (`2026-091956 BP`, issue_date `2026-08-06T00:00:00.000Z`, application_date `2026-03-26T00:00:00.000Z`, zip 78754, lat/lng direct, the_geom Point, council_district "1", work_type "Remodel"); its `total_job_valuation` is NULL (remodel rows carry only breakdown columns), so cost/filing fixtures use a second live row WITH total_job_valuation (`2026-101521 BP`). 311 newest-by-sr_created_date = `26-00276479` traffic-signal SR with sr_location_lat/long + sr_location_lat_long Point container + sr_location_council_district "5".
- 2026-08-23 — **Schema surprises vs research doc:** (1) permits `total_job_valuation` exists in the view schema but is NULL on remodel-heavy rows — cost map entry still correct, but expect a nontrivial null rate; (2) permits `location` column is a WKT STRING ("POINT(lng lat)"), not a dict — it sits ahead of `the_geom` in the dob container chain and blocks it; coords effectively come from direct latitude/longitude columns (both ✓ today); (3) work_type distribution verified live: "New" 101k / "Remodel" 80.9k / "Repair" 50.4k / "Demolition" 16.7k — note bare "New" does NOT match the chain's NB check ("NEW CONSTRUCTION"/"NEW BUILDING"/"NB"), so the proposed ordering mainly rescues DM ("Demolition") and A2-family ("Addition…") signal; (4) research's "status ✓ chain" for permits holds (`row.get("status")`); (5) 311 producer reads `status` via bare `row.get("status")` NOT first_mapped, and incident_address via bare `address/street_address/incident_address` NOT first_mapped — sr_status_desc/sr_location map entries are inert until the orchestrator extends those two chains (or accept status defaulting to "Open").
- 2026-08-23 — **PROPOSED DatasetSpec field_map JSON (verified against full live rows):**

PERMITS `quv8-5ckq` (watermark_col="issue_date", id_keys=["permit_number", "objectid"]):
```json
{"cost": ["total_job_valuation"],
 "filing_date": ["application_date"],
 "job_type": ["work_type", "permit_type"],
 "proposed_units": ["number_of_units"],
 "proposed_stories": ["number_of_floors"],
 "borough": ["council_district"]}
```
(job_id `permit_number`, latitude/longitude, issuance_date `issue_date`, zipcode `zip_code` all already resolve through the shared chains — no entries needed.)

COMPLAINTS_311 `xwdj-i9he` (watermark_col="sr_created_date", id_keys=["sr_number"]):
```json
{"latitude": ["sr_location_lat", "sr_location_lat_long.coordinates[1]"],
 "longitude": ["sr_location_long", "sr_location_lat_long.coordinates[0]"],
 "complaint_type": ["sr_type_desc"],
 "created_date": ["sr_created_date"],
 "closed_date": ["sr_closed_date"],
 "zipcode": ["sr_location_zip_code"],
 "borough": ["sr_location_council_district"],
 "descriptor": ["sr_type_desc"],
 "incident_address": ["sr_location"],
 "status": ["sr_status_desc"]}
```
NOTE: dotted-container syntax supports ONE nested level (`head.tail`), not `[n]` indexing — so if direct sr_location_lat/long were ever absent the container would need chain support; keep the direct columns as primary (they are explicit and ~99.4% populated). `status`/`incident_address` entries are forward-looking (see surprise #5). Registry-comment should also carry the TABC/FedRamp-shell absence rationale.

- 2026-08-23 — Geography finalized: metro bbox 30.10–30.62 / -98.05–-97.52 contains all live samples (Parmer Commons 30.367,-97.612; downtown 30.27,-97.74; Slaughter Ln 30.19; far NW -97.90). 6 divisions, 16 submarkets (DOWNTOWN_CAPITOL 3, EAST_AUSTIN_MUELLER 3, SOUTH_AUSTIN_SOCO 3, NORTH_AUSTIN_DOMAIN 2, WEST_AUSTIN_HILLS 3, PFLUGERVILLE_ROUND_ROCK_EDGE 2); all nesting/exactly-one invariants pass in-test.
- 2026-08-23 — Tests done: 31 collected → 16 pass-today, 5 xfail(strict=False, precise reasons), 10 registration-red until spine (expected; matches NOLA discipline). test_field_maps.py still green (no sniff regression).

## Current step

Done. Spine applied by orchestrator; all gates green.


## Next step

None. Interlock 17/17; city suite + full suite 390/390. xfail markers stripped post-spine (now hard assertions). Platform-routing note: Detroit's ArcGIS specs exposed that only the deeds producer exposed an arcgis client — the interlock completeness gate caught it and permits/311/SLA producers gained the same _client_for routing.
