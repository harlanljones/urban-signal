# US-308 / US-309 — Onboard New Haven, CT and Worcester, MA (already registered on main)

## Summary

Both New Haven (US-308) and Worcester (US-309) were **already registered on
`main`** before these tickets were picked up. This work verified the existing
registrations rather than adding new code.

## Verification performed

- **New Haven**: `City` enum member `NEW_HAVEN = "new_haven"`
  (`apps/api/src/spatial/city_registry.py:171`), leaf module
  `apps/api/src/spatial/cities/new_haven.py`, and corpus
  `apps/api/src/spatial/cities/data/new_haven.yaml` all confirmed present.
- **Worcester**: `City` enum member `WORCESTER = "worcester"`
  (`apps/api/src/spatial/city_registry.py:170`), leaf module
  `apps/api/src/spatial/cities/worcester.py`, and corpus
  `apps/api/src/spatial/cities/data/worcester.yaml` all confirmed present.
- **Interlock gate**: `python -m pytest -m interlock -q` from `apps/api` →
  **35 passed** (green).
- **Dashboard static copy**: regenerated via `scripts/export_dashboard.py` —
  byte-synced and current.
- **Product facts**: `bun run facts:export` succeeded
  (`SITE_FACTS_OK`, 142 metros) — not required, included for completeness.

## Result

Both registrations are present and the full interlock gate is green. No code
changes were required for either ticket. Dashboard static copy is current.

## Linear

- US-308 moved to **In Review** with comment:
  "Registration already present on main; verified pytest -m interlock green and
  dashboard static copy current."
- US-309 moved to **In Review** with comment:
  "Registration already present on main; verified pytest -m interlock green and
  dashboard static copy current."
