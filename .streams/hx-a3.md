# Stream log — hx-a3 — 2026-10-12

## Claim

- **Stream id:** `hx-a3` (HX-A3 client res-6 bridge band; ROADMAP.md)
- **Owner:** orchestrator (delegated agents failed with 429 quota errors)

## Current step

Complete.

## Decisions

Done by orchestrator after the delegated agent hit a 429 quota error before editing.
- DG-4 shape implemented: **(b) underlay**. z in [6, 8.9): national res-6 flat fill, opacity 0.35 (primary band stays 0.7), no line, no extrusion even in 3D (US-422), national layers inserted before `h3-hex-fill` so they draw beneath the metro grid. Above 8.9 all national layers hidden and the national generation is bumped. `nationalResForZoom`: 4 / 5 (z<6) / 6.
- Browser check (modified client vs production snapshot): rural Kansas z7 -> res 6, 5,442 hexes, fill visible, extrusion none, opacity 0.35, beneath metro; /api/v1/national/6 requested. NYC z10 hidden.
- **Found a pre-existing production bug while checking** (see hx-a4): NYC z7 reported 'Coverage failed to load'.

## Next step

Stage A integration checkpoint (preflight + benchmark), then Stage B (HX-B1).
