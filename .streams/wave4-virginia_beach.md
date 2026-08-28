# Wave 4 — Virginia Beach, VA (LEAF)

**Ticket:** US-354
**Agent:** leaf-implementation
**Status:** complete
**Claimed:** 2026-08-28

## Scope
- `apps/api/src/spatial/cities/virginia_beach.py`
- `apps/api/src/producers/field_maps_virginia_beach.py` (if needed)
- `apps/api/tests/unit/test_producers_virginia_beach.py` (new)
- `.streams/dispatch-log.md` (one row)

## Out of scope
city_registry.py, config.py, serving/dashboard.py, cities/__init__.py, existing tests, apps/product/**, git commit.

## Outcome — completed (2026-08-28, live re-probe)

All three feeds re-probed live against `services2.arcgis.com/CyVvlIiUfRBmMQuu`
(curl, JS-free stdlib):

| Feed | Endpoint | Newest row | Totals | Live checks |
|---|---|---|---|---|
| PERMITS | `Building_Permits_Applications_view/FeatureServer/0` (Table) | IssueDate **2026/08/21** | 105,454 | 7d(>=2026/08/20)=**247**, 60d=4,790 |
| SLA | `Business_Licenses_view/FeatureServer/0` (Table) | Begin_Date **07/31/2026** | 41,646 | zero Aug–Dec 2026; typed-2026=**2,862** |
| DEEDS | `Property_Sales_/FeatureServer/0` (Table) | Sales_Date **2026-08-10** | 594,771 | 7d=**0**, 60d=1,474 (batch caveat holds) |

Fixture rows byte-verified live (≥2/feed): permits 2026-MECC-10572 /
2026-BDRA-16146 / 2026-BDRN-17974; SLA OBJECTID 411161 / 412830; deeds
2015014001001990 (Pungo $0) / 2015104001001980 (Blvd $0) / 202603038274
(Anderson, $385k). Sales_Date epoch-ms 1786320000000 / 1785888000000 flatten
to the fixture ISOs.

Findings recorded in the leaf module docstring:
- SLA typed-2026 total is **2,862** — the probe's "2026 YTD 77" reproduces
  only as the newest-cohort window, not true YTD. max-OBJECTID rows carry
  2019–2025 Begin_Dates, so OBJECTID DESC is not a watermark ordering; the
  declared `%m/%d/%Y` typed window (ADR 0005) is mandatory.
- DEEDS still 7d=0 since the 2026-08-10 batch — inside the ~2–3-week cadence,
  within the probe's mid-September stall watch.

## Changeset
- `apps/api/src/spatial/cities/virginia_beach.py` — re-stamp paragraph added
  to the module docstring; module logic was already probe-accurate.
- `apps/api/src/producers/field_maps_virginia_beach.py` — unchanged (matches
  live columns verbatim).
- `apps/api/tests/unit/test_producers_virginia_beach.py` — existing; re-stamp
  note in docstring. 52 tests pass.

## Gates
- VB leaf suite: **52/52 passed**.
- Leaf-naming: per-module `VIRGINIA_BEACH_*` canonical constants green;
  suite-global count `test_city_leaf_naming.py` needs orchestrator bump
  57→62 (all five wave-4 leaves land together — existing test file, not
  leaf-editable).
- Interlock: **22/22 passed**.
- Full unit suite: **1797 passed / 3 skipped / 1 failed** — the single
  failure is the shared leaf-naming count (above, spine-side).

## Spine delta (for orchestrator)
VIRGINIA_BEACH CityRegistration with 3 DatasetSpecs (permits cadence 1d; SLA
cadence 365; deeds cadence 14d + batch alarm), FeedType enum + aliases,
config topics, METRO_META "Virginia Beach, VA", dashboard + index.html +
snapshot coverage, and `test_city_leaf_naming.py` count 57→62.
