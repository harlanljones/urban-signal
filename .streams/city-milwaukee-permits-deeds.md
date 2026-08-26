# Stream log — city-milwaukee-permits-deeds — 2026-08-26

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** `city-milwaukee-permits-deeds`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/milwaukee.py` (extend with PERMITS + DEEDS spec data + field maps)
  - `apps/api/src/producers/field_maps_milwaukee_permits_deeds.py` (new; re-exports FIELD_MAP keyed by FeedType)
  - `apps/api/tests/unit/test_producers_milwaukee_permits_deeds.py` (new; passes WITHOUT spine registration)
- **Spine files I expect to need (deferred to orchestrator interlock):**
  - `apps/api/src/spatial/city_registry.py` (REGISTRY[CityId.MILWAUKEE].datasets += PERMITS + DEEDS; no new FeedType members — both exist)
  - `apps/api/src/producers/field_maps.py` (NO edit — field maps are read from registry `extra["field_map"]`; the leaf data is the source of truth)
  - dashboard METRO_META + `apps/dashboard/public/index.html` sync (US-138 dashboard wiring)
  - `apps/api/src/config.py` (add verified Milwaukee CKAN CSV endpoints)

## Intent

Register Milwaukee PERMITS + DEEDS behind the two capabilities that US-138
unblocks: the ADR-0004 Postgres-replay geocoder (permits were address-only)
and the ADR-0005 typed text watermark (deeds were yearly-archive text dates).
The bulk of the work — feed specs as data, per-feed field maps, and contract
tests — lands entirely in leaf files; the spine edit is a small mechanical lift
of the spec dicts into `city_registry.REGISTRY`.

## Decisions

- 2026-08-26 — User approved the scope change from SLA-only. Both feeds use
  verified CKAN/OpenGov CSV downloads from `data.milwaukee.gov`; permits use
  `Date Issued`, and yearly property-sales snapshots use `Sale_date`.
- 2026-08-26 — Specs are stored as plain dicts in `milwaukee.py`, NOT
  `DatasetSpec` instances, to avoid a circular import (`city_registry` already
  imports `milwaukee`). The orchestrator wraps them in `DatasetSpec(...)` and
  binds `topic=settings.topic_permits` / `settings.topic_deeds`.
- 2026-08-26 — Live schema probes confirmed permits `Record ID`, `Address`,
  `Date Issued`, and deeds `PropertyID`, `Address`, `Sale_date`, `Sale_price`.
- 2026-08-26 — DEEDS `watermark_exclude` ships empty; any sentinel spellings
  (ADR-0005) are discovered live and appended at spine time. The mechanism is
  asserted in the test with a representative sentinel.
- 2026-08-26 — PERMITS `needs_geocode=True` + `geocode_context="Milwaukee, WI"`
  (ADR-0004); the test fixture supplies native geometry so parsing is verified
  without invoking the geocoder.

## Current step

Interlock complete: the registry, config, producers, typed CSV client, README,
and contract tests now register and consume both feeds. `pytest -m interlock`
passes.

## Next step

Run the focused Milwaukee/CSV tests and the full API suite, then update Linear
with the verified CKAN endpoints and test results.
