# Stream log — city-austin-tabc — 2026-08-26

## Claim

- **Stream id:** `city-austin-tabc`
- **Leaf files I created/edited:**
  - `apps/api/src/producers/field_maps_austin_tabc.py` (new — TABC SLA field map, keyed by FeedType value `"sla"`)
  - `apps/api/src/spatial/cities/austin.py` (extended — docstring + `AUSTIN_TABC_SLA_SPEC` proposal, imports the field map)
  - `apps/api/tests/unit/test_producers_austin_tabc.py` (new — fixtures + parsing/field-map assertions, runs WITHOUT spine registration)
- **Spine files I expect the orchestrator to need (I did NOT touch these):**
  - `apps/api/src/spatial/city_registry.py` (REGISTRY `CityId.AUSTIN` gains `FeedType.SLA` dataset; no new enum member needed — TABC is an SLA)
  - `apps/api/src/spatial/cities/__init__.py` (already imports austin — no change needed)
  - `apps/api/src/producers/field_maps.py` (central entry derived from my per-city file — see Report)
  - `apps/dashboard/...` METRO_META + `apps/dashboard/public/index.html` byte-sync (City registration rule)
  - `apps/api/src/config.py` (no change — reuses `settings.topic_sla`)

## Intent

Add Austin's TABC liquor-license feed as a THIRD registered feed (the existing
PERMITS + COMPLAINTS_311 two-feed partial registration becomes three-feed).
The TABC dataset `7hf9-qc9f` carries a street `address` but no lat/lng, so it
registers under `FeedType.SLA` with `needs_geocode: True` and recovers
coordinates through the ADR 0004 geocoder. The shared `sla_licenses_producer`
needs NO new archetype — Austin parses through the generic field-map chain once
the map is in the registry.

## Decisions

- 2026-08-26 — Verified live schema of both TABC datasets against data.texas.gov:
  - `7hf9-qc9f` "TABC License Information" (126,488 rows) is the authoritative
    current license file. Real columns used: `license_id` (number), `license_type`
    (2-char code), `license_status`, `current_issued_date`, `expiration_date`,
    `trade_name`, `owner`, `address` (street string), `city`, `state`, `zip`,
    `county`. It HAS a street `address` string → geocodable under ADR 0004.
  - `kguh-7q9z` "TABCLicenses" is a 2021 AIMS-migration cross-walk
    (65,175 rows) with trailing-space-padded `locationaddress` and no
    authoritative status/issue dates. NOT a registration target.
- 2026-08-26 — `watermark_col` = `status_change_date` (advances on every Primary
  Status change: new issuance, renewal, suspension, surrender) — the only correct
  incremental-poll cursor for a slowly-churning license file.
- 2026-08-26 — NO new `FeedType` enum member required: TABC liquor licenses map
  onto the existing `FeedType.SLA`. NO new archetype in `sla_licenses_producer`:
  passing `city_id="austin"` resolves through the generic field-map chain, and
  the address geocodes via the already-wired `needs_geocode` path.
- 2026-08-26 — Field map keyed by the FeedType *value* string `"sla"` (not the
  enum) to avoid a circular import: `city_registry` imports `austin`, so `austin`
  must not import `city_registry` at module load. The spine re-keys with
  `FeedType(key)`.

## Current step

Leaf complete. Leaf tests pass (`pytest tests/unit/test_producers_austin_tabc.py`).
Spine deltas drafted in the report; awaiting orchestrator interlock.

## Next step

If this were the interlock step, apply the spine deltas in `city_registry.py`
(REGISTRY Austin `datasets[FeedType.SLA]`), copy the field map into the registry
spec's `extra["field_map"]`, add the Austin METRO_META entry + byte-sync
`index.html`, then run `pytest -m interlock`.
