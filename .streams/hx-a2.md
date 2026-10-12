# Stream log — hx-a2 — 2026-10-12

## Claim

- **Stream id:** `hx-a2` (HX-A2 registry urban_anchors + gate (interlock hold); ROADMAP.md)
- **Owner:** orchestrator (delegated agents failed with 429 quota errors)

## Current step

Complete.

## Decisions

Done in one hold; gate green (`pytest -m interlock`, 37 tests).
- `registration.py` slot + kwarg (default `()`), `city_registry.py` field (default `()`), `city_data.py` threads optional `urban_anchors` from YAML (validator never rejected extra definition keys; only dataclass fields). No leaf city module or YAML touched; all 157 stay `()` so k-ring is authoritative.
- Gate: `TestUrbanAnchorWiring` (registered ids resolve, intersect metro bbox, hold a submarket; every metro has a derivable anchor holding a submarket - measured 157/157) + SPINE_INVARIANTS entry.

## Next step

Stage A integration checkpoint (preflight + benchmark), then Stage B (HX-B1).
