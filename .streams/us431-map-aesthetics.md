# Stream log — us431-map-aesthetics — 2026-08-31

## Claim

- **Stream id:** `us431-map-aesthetics`
- **Leaf files I will create/edit:** none (pure spine hold)
- **Spine files I expect to need:** `apps/api/src/serving/dashboard.py` (single source of truth; regenerated static copy `apps/dashboard/public/index.html` via `scripts/export_dashboard.py`)

## Intent

US-431: night-shift cartography + color-ramp harmonization on the dashboard map. All 7 directions confirmed: (1) tonal night treatment of the Esri base, (2) dark-canvas-tuned percentile ramp replacing the traffic-light ramp, (3) zoom-scaled dense-grid outlines + value-aware fill, (4) scale bar / coordinate readout, (5) truthful legend regenerated from real ramp stops + height note + baseline key, (6) reduced-motion-safe camera/hover motion only, (7) selection affordance beyond the sky outline.

## Decisions

- Spine hold: all edits in one pass in `dashboard.py`, then export + interlock gate + full preflight before release.
- Ramp: `HEX_RAMP = [[0,#1f3a52],[35,#2f6f8f],[60,#5aa9a4],[80,#d9bd63],[92,#f2685c]]` — cool→warm divergence; coral reserved above p92. Single JS constant `hexRampExpr()` feeds all 4 layer sites; legend bar + ticks regenerated from the same constant (legend can't drift).
- Basemap: raster paint tonal treatment (sat −0.45, contrast 0.12, brightness 0.82, opacity 0.88; labels dimmed to 0.5) — no vignette/decoration.
- Grid: zoom-scaled slate outlines (`rgba(148,163,184,0.2)`, width 0.4→1.2 by zoom), value-aware fill-opacity (0.42→0.88 by percentile) replacing flat 0.78.
- Selection: new `h3-hex-selected-fill` layer (sky 0.3 fill) + 2.5px sky outline; filter set in both selection paths.
- Orientation: bottom-right readout — scale bar (Web Mercator m/px, nice-number rule) + z/lat/lng in Plex Mono; wired to `map.on('move')`.
- Legend: stop ticks 50/75/90, "Height ∝ value (3D)" note, hatched "Registry baseline — no precomputed snapshot" key.
- Motion: none added (Operate surface; existing camera/hover/zoom-hint already reduced-motion-safe).

## Outcome

Done. `export_dashboard.py` regenerated static copy (byte-sync verified by preflight); interlock gate 25/25 pass; full preflight green; JS syntax checked; impeccable detector run (regex-fallback mode, no findings).
