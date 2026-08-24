# Stream log — city-montgomery-co — 2026-08-24

## Claim

- **Stream id:** city-montgomery-co
- **Leaf files:** `src/spatial/cities/montgomery.py`, `tests/unit/test_producers_montgomery.py`
- **Spine files expected:** `src/config.py`, `src/spatial/city_registry.py`, `src/spatial/cities/__init__.py`, `src/serving/dashboard.py`, `src/export/snapshot_builder.py`, `apps/dashboard/public/index.html`, `apps/product/src/main.js`, `README.md`

## Intent

Register Montgomery County MD's point-geocoded permit families and liquor
licensees via Socrata ×2. Explicitly exclude MC311 because it is zip-only and
cannot satisfy the spatial ingestion gate.

## Decisions

- 2026-08-24 — Claimed HAR-26 after HAR-16 was confirmed completed and the issue was re-read as open and unassigned.

## Current step

Implementation complete; focused, interlock, producer, site, and build checks are green.

## Evidence

- Public Socrata metadata verified for `m88u-pqki`, `i26v-w6bd`, `b6ht-fw3x`, `qxie-8qnp`, and `c6rw-fazn`.
- `pytest -q tests/unit/test_producers_montgomery.py tests/unit/test_interlock_gate.py tests/unit/test_export_snapshot.py`: 30 passed.
- `pytest -q tests/unit/test_producers_*.py -m 'not live'`: 327 passed.
- `pytest -q -m interlock`: 20 passed.
- `node scripts/verify-site-content.mjs`: `SITE_CONTENT_OK`.
- `bun run build && bunx turbo typecheck build`: successful.

## Next step

Post implementation evidence to HAR-26; leave live/staging validation as the remaining acceptance step.
