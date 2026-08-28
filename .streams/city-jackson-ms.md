# Stream log — city-jackson-ms — 2026-08-28

Copy this file to `.streams/city-jackson-ms.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** `city-jackson-ms`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/jackson_ms.py` (NEW)
  - `apps/api/tests/unit/test_producers_jackson_ms.py` (NEW)
- **Spine files I expect to need:**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/serving/dashboard.py`
  - `apps/dashboard/public/index.html` (byte-sync via `python scripts/export_dashboard.py`)
  - `apps/product/public/facts.json`
  - `apps/product/public/cities/jackson_ms.json`

## Intent

Register Jackson, MS (`CityId.jackson_ms`) as a new Urban Signal metro per US-288:
deliver a verified leaf geometry module with divisions and submarkets and passing
containment tests; prefer a real public feed but fall back to SNAP SLA (MS slice)
if open.jacksonms.gov lacks permits/311 APIs. Wire the spine in the same hold
(REGISTRY + ALIASES + METRO_META + snapshot/grid + static copy) so Jackson
appears on the dashboard, and export product facts in the same PR.

## Decisions

- 2026-08-28 — No verifiable permits/311 dataset found on `open.jacksonms.gov`;
  initial registration uses `snap_sla_spec("MS")` only (no fake endpoints).

## Current step

Leaf geometry and containment tests implemented for `jackson_ms`.

## Next step

Wire `CityId.JACKSON_MS` in `city_registry.py` + `ALIASES`, add METRO_META +
byte-sync the static copy, regenerate product facts, then run `pytest -m interlock`.

