# Stream log — us134-kansas-city-sla — 2026-08-25

- **Stream id:** `us134-kansas-city-sla` (Linear US-134, claimed).
- **Spine files I edit:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`,
  `apps/api/src/producers/sla_licenses_producer.py` (one additive `%Y%m%d` date
  format), `apps/api/tests/unit/test_producers_kansas_city.py`, `README.md`,
  `scripts/rejection_recheck.py`.
- **Scope:** Kansas City SLA registration. Additive only; other cities untouched.

## Live probe (before any edit) — data.kcmo.org pnm4-68wg (2026-08-25)

Fetched via direct HTTP/Socrata SoQL.

- **Endpoint live:** `https://data.kcmo.org/resource/pnm4-68wg.json`, HTTP 200.
- **Columns confirmed on the wire:** `id`, `business_type`, `address`, `city`,
  `state`, `zipcode`, `business_name` (mostly null), `dba_name`,
  `valid_license_for` (text `YYYYMMDD` expiration), `location`
  (`{"type":"Point","coordinates":[lng,lat]}`).
- **Row count:** `count(id)` = **28245**.
- **Geocode share:** `count(id) where location IS NOT NULL` = **27222** →
  **27222/28245 = 96.38%** (matches sweep's 96.4%).
- **Freshness:** metadata `rowsUpdatedAt` = 1768519845 → **2026-01-15 23:30:45 UTC**
  (~7mo stale — the suspected publishing lapse). No per-row date watermark.
- **valid_license_for distribution:** `20241231` = 3660, `20251231` = 22986,
  `20261231` = 1599. Matches the sweep (22,986 expired 2025 / 1,599 current 2026;
  the 3,660 @ 20241231 two-year-older stratum was not called out but is present).

### Discreps / open questions (does NOT block)

- **`location` is a GeoJSON Point, not a `{latitude,longitude}` dict.** The
  ticket / sweep field_map uses `latitude: ["location.latitude"]` and
  `longitude: ["location.longitude"]`. `field_maps.first_mapped` unwraps a dotted
  key via `container["latitude"]`, which does not exist on a GeoJSON Point —
  those two map keys are therefore dead. The SLA producer's generic
  `location`-container fallback (`loc.get("coordinates",[None,None])[1]/[0]`)
  DOES resolve the point, so events still carry real lat/lng and geocode to the
  expected 96.4%. Left the map as the ticket specifies (harmless); the producer
  fallback is what actually works. Alternative (mapping to a non-dotted key)
  is impossible: `first_mapped` has no `coordinates[N]` accessor.
- **`incident_address: ["address"]` is inert for the SLA producer.** `incident_address`
  is a 311-producer key (same finding as US-133). SLA `event.address` resolves via
  the bare `row.get("address")` chain instead, which fires because the raw column
  literally is `address`. Kept as the ticket specifies; production behavior correct.
- **`valid_license_for` is bare `YYYYMMDD`.** `sla_licenses_producer._parse_datetime`
  had no `%Y%m%d` format, so `expiration_date` would have parsed to None. Added
  `%Y%m%d` to the format tuple (additive; no other city feeds that format).
- **README cell:** the ticket calls the licenses cell "— no open endpoint", but the
  licenses (5th) column actually read "— Socrata (now geocoded; pending US-134)".
  Updated the licenses cell to "Socrata (business licenses; snapshot)"; permits
  ("— no open endpoint"), 311 ("Socrata"), deeds ("— no verified sales feed") unchanged.

## Decisions

- Register as Socrata, `watermark_col=""`, `id_keys=["id"]`,
  `extra["expected_cadence_days"]=90` (the ~7mo publish lapse), `extra["ingestion_mode"]="snapshot"`
  (Baton Rouge businesses precedent — no usable open-date watermark → D4 snapshot mode).
  `field_map` as the sweep §11 specifies (license_id, license_type, expiration_date,
  dba, latitude/longitude, incident_address, borough, zipcode).
- **Producer change:** add `%Y%m%d` to `_parse_datetime` so `valid_license_for`
  (`"20251231"`) yields a real `expiration_date`. No snapshot-mode producer logic:
  the producer just repaginates the full snapshot each run (REST watermark_col="").
- **No `needs_geocode`:** 96.4% carry native point geometry; the ~3.6% null-location
  rows emit as null-coord events (DC Basic Business Licenses non-spatial tolerance).
- **Rejection recheck:** `kc_sla` "location field only, no date column" is obsolete.
  Added `"valid_license"` to `watch_patterns` and a `superseded_by: "US-134"` so it
  flips to SUPERSEDED via the already-present `_ENTRY_CITY["kc_sla"] -> ("kansas_city","sla")`
  mapping now that `get_dataset(kansas_city, SLA)` succeeds.
- Kansas City is already a registered city (selector option + CITY_CONFIGS + worker
  static already present — HJ-120 registered the 311 feed), so no dashboard wiring
  edits are required; the interlock dashboard-wiring test keys on cities, not feeds.

## Verify (from apps/api, `.venv/bin/python -m pytest`)

- `tests/unit/test_producers_kansas_city.py` — 9 passed (2 geometry/registration,
  4 KC 311 parsing, 3 KC SLA parsing: field-map+point, missing-id drop, null-loc emit).
- SLA producer regressions: `test_producers_sf.py`, `test_producers_la.py`,
  `test_producers_new_orleans.py`, `test_producers_norfolk.py` — all passed.
- `tests/unit/test_interlock_gate.py::TestDashboardWiring` — 3 passed (no dashboard edits needed).
- Ruff: `config.py` 0 net-new (0→0); `city_registry.py` 0 net-new (29→29);
  `sla_licenses_producer.py` 0 net-new (19→19); `test_producers_kansas_city.py` 0 (0→0);
  `scripts/rejection_recheck.py` all clean. No changes committed.
