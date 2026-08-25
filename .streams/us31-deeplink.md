# US-31 — per-city dashboard deep links (?city= param)

**Claimed:** 2026-08-25, single-agent stream.

## Scope

- `apps/api/src/serving/dashboard.py` — map HTML: add `deepLinkedCity()` (?city=
  param validation against CITY_CONFIGS) and seed the DOMContentLoaded handler
  before geolocation. Leaf file (not in spine-manifest.txt).
- `apps/product/src/main.js` — /compare columns deep-link the live map
  (`/dashboard?city=<id>`).
- Regenerated artifacts: `apps/dashboard/public/index.html` (static copy),
  `apps/product/public/facts.json` + `cities/*.json` (registry drift from the
  parallel registration streams).

## Spine

No spine files touched: dashboard.py is leaf; registry/config untouched by this
stream. `pytest -m interlock` run anyway per the US-31 workflow contract
(dashboard wiring changed): 20 passed.

## Outcome

completed — gates evidenced on the ticket:
product-side redirect query preservation verified live (CF Pages forwards ?city=);
dashboard param parse browser-verified at 1091px and 390px emulation (boston +
charlotte preselect; atlantis/absent fall back to SF default); lint/typecheck/
build green; verify-agent-surface OK.
