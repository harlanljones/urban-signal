# US-433: Dense-grid legibility for dashboard map

## Summary

Reduced visual noise in the dashboard's H3 grid at metro zoom levels by making the outline stroke opacity zoom-dependent (nearly invisible at wide metro views, gently visible at street level), lowering the fill-opacity floor so low-value cells fade into the background, and adding a hover highlight layer so the grid feels interactive without requiring a click.

## Changes

- **`apps/api/src/serving/dashboard.py`** — Grid rendering improvements:
  - `h3-hex-line`: Changed `line-color` from a constant `rgba(148, 163, 184, 0.2)` to a zoom-interpolated expression (`0.04` at z7 → `0.15` at z10 → `0.35` at z14), and reduced `line-width` from `0.4–1.2` to `0.3–1.0`, so dense metro outlines don't read as checkerboard noise
  - `h3-hex-fill`: Lowered the fill-opacity floor from `0.42` to `0.25` and added an intermediate stop at `40→0.45` and `80→0.7`, so low-percentile cells are truly muted and value-aware emphasis is more pronounced
  - `updateMetricVisuals()`: Updated the dynamic opacity expression to match the new stops
  - Added `h3-hex-hover` line layer: a subtle `rgba(56, 189, 248, 0.55)` outline at 1.8px that tracks the cursor. Cleared on mouseleave or click
  - Added `hoveredH3Index` state variable and mousemove/mouseleave handlers on both `h3-hex-fill` and `h3-hex-extrusion` to drive the hover filter
  - Click handlers now clear the hover filter before setting selection, avoiding hover/selection visual overlap
- **`apps/dashboard/public/index.html`** — Regenerated static copy (byte-synced)

## Testing

- Interlock gate: `pytest -m interlock` — 24/24 pass
- CI/CD pre-flight: all 6 gates green (interlock, dashboard↔product cross-ref, product facts, product lint, dashboard export, ruff)
- Dashboard HTML generated successfully (139066 bytes)

## Notes

- The hover layer is a line-only highlight (no fill) so it doesn't interfere with the fill opacity or color ramp
- Line opacity at z7 (0.04) is intentionally near-invisible — at that zoom the metro grid is just entering view and full outlines would add noise; the color fill alone carries the data
- The selection layer (2.5px `#38bdf8` line + fill tint) remains far more prominent than the hover layer (1.8px, 55% alpha), so there's no ambiguity between hover and selection