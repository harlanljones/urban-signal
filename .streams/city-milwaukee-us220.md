# Stream log — city-milwaukee-us220 — 2026-08-30

Leaf stream for Linear US-220: Milwaukee CKAN feed supplementation.

## Claim

- **Stream id:** `city-milwaukee-us220`
- **Leaf files:**
  - `.streams/city-milwaukee-us220.md`
  - `apps/api/src/spatial/cities/milwaukee.py`
  - `apps/api/src/producers/field_maps_milwaukee.py`
  - `apps/api/tests/unit/test_producers_milwaukee_us220.py`
- **Spine files held by integrator (do not edit):** `city_registry.py`, `config.py`, producer dispatch/registration, dashboard/export files.

## Intent

Add researched Milwaukee CKAN feed specifications and field maps for US-220. The
serial integrator will verify/register only feasible feeds in a later spine hold.

## Status

- 2026-08-30 — claimed and dispatched; implementation in progress.
- 2026-08-30 — live CKAN probe selected five viable candidates; traffic crashes
  (zero rows) and zoning (missing resource) remain explicitly not viable.
- 2026-08-30 — leaf implementation and targeted tests complete; no shared
  spine files changed.
