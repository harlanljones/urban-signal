# Stream log — us133-norfolk-sla — 2026-08-25

- **Stream id:** `us133-norfolk-sla` (Linear US-133, claimed).
- **Spine files I edit:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`,
  `apps/api/src/producers/sla_licenses_producer.py` (one additive `premises_name`
  prepend), `apps/api/tests/unit/test_producers_norfolk.py`, `README.md`.
- **Scope:** Norfolk SLA registration. Additive only; other cities untouched.

## Live probe (before any edit) — data.norfolk.gov dpi6-sct5 (2026-08-25)

Fetched via direct HTTP/Socrata SoQL.

- **Endpoint live:** `https://data.norfolk.gov/resource/dpi6-sct5.json`, HTTP 200.
- **Columns confirmed on the wire:** `trading_as_name`, `naics`, `primary_owner`,
  `location_address`, `mailing_address`, `business_opened_date`,
  `latitude`, `longitude`, `geocoded_point` (`{"type":"Point","coordinates":[lng,lat]}`),
  `census_tract`. Native geometry is HERE — the Wave G2 "no geometry" verdict is obsolete.
- **Watermark format:** `business_opened_date` is Socrata DateTime
  (`"2026-08-25T00:00:00.000"`). `max(business_opened_date)` = `2026-08-25T00:00:00.000`.
- **Freshness:** `X-SODA2-Truth-Last-Modified` = `Tue, 25 Aug 2026 11:18:01 GMT` — today.
- **Placeholder:** `location_address` = `'NO NORFOLK ADDRESS REQUIRED 99999'` (special-event/no fixed premises).
- **Geocode share (raw):** count(*) all rows = **10100**.
- **Geocode share after filter** `where location_address != 'NO NORFOLK ADDRESS REQUIRED 99999'`:
  - total = **7542** (i.e. 2558/10100 = 25.3% are placeholder).
  - with `AND latitude IS NOT NULL` = **7256** → **7256/7542 = 96.2% geocoded**.
  - Matches the sweep exactly (7,256 / 96.2%).

### Discrepancy vs ticket (does NOT block)

- The ticket text mentions mapping `incident_address=location_address`, but the SLA
  producer has no `incident_address` field-map key (that is a 311-producer key). The
  SLA analog is `address_street`, which the producer uses as its address-geocode
  candidate and which the *final* `event.address` chain reads directly via
  `row.get("address")` — so I map `address_street: ["location_address"]`.
- The ticket lists `primary_owner` as a column to map. The SLA producer's
  `premises_name` chain is a bare `row.get(...)` chain that never consulted the field
  map. **Fixed with one additive prepend** of `first_mapped(row, field_map, "premises_name")`
  (no-op for cities whose map lacks the key; also a latent-fix that newly resolves
  NOLA/Milwaukee/Baton Rouge's already-declared `premises_name` keys — no test pins those).

## Decisions

- Register as Socrata, `watermark_col="business_opened_date"`,
  `id_keys=["trading_as_name","primary_owner","business_opened_date"]`,
  `extra["where"] = "location_address != 'NO NORFOLK ADDRESS REQUIRED 99999'"`.
- `field_map`: `license_id` (trading_as_name, primary_owner), `dba` (trading_as_name),
  `premises_name` (primary_owner), `license_type` (naics), `effective_date`
  (business_opened_date), `address_street` (location_address), `latitude`/`longitude`.
- No `needs_geocode`: 96% carry native coords; the where-filter drops the placeholder
  rows, so null-H3 share is ~3.8% — far below the G8' 5% ceiling.
- Norfolk is already a registered city (selector option + CITY_CONFIGS + worker static
  already present), so no dashboard wiring edits are required; the interlock
  dashboard-wiring test keys on cities, not feeds.
