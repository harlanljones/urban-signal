# Urban Signal — 20-second product promo (brief)

## Brief

A ~20-second promo for **Urban Signal** in Vercel's presentation style: one
idea per beat, crisp typography, polished motion, and a strong final call to
action. The project's own visual system (DESIGN.md) supplies the canvas
(ink), the accent (lime signal), and the type (DM Sans + DM Mono); Vercel's
presentation style supplies the pacing and the typographic confidence.

No music or VO is used — the edit is typographic and self-contained. Music
can be dropped on top later if the project source for it is approved.

## Verified product facts used (from README.md / PRODUCT.md)

- Real-time spatial intelligence & commercial catalyst forecasting engine
- Municipal telemetry: **permits, 311 complaints, licenses, deeds**
- Streams through **Apache Kafka** onto an **Uber H3** multi-resolution grid (Res 7, 8, 9)
- Predicts appreciation **6–18 months ahead** of public market listings
- **ONNX Runtime GPU inference** (CUDA FP16) on **Kubernetes**
- **49 registered metros** shown on the live national dashboard
- Live dashboard: **https://us-dash.harlanljones.com/**

Nothing beyond these facts is claimed. No fake metrics, no invented
testimonials, no overstated language.

## Structure (1920×1080, 30 fps, workarea 0–20 s)

| # | Window | Beat | Copy |
|---|--------|------|------|
| 1 | 0–4 s | Brand lockup | Eyebrow `REAL-TIME SPATIAL INTELLIGENCE`, title **Urban Signal**, rule, mono tagline |
| 2 | 4–8 s | The forecast | **6–18 months** / *ahead of the market* / mono qualifier |
| 3 | 8–12 s | The signal | Counting **49** metros · **4** feeds · **1** H3 grid + mono footnote |
| 4 | 12–16 s | The pipeline | Terminal-style `>` ingest/stream/grid/infer log |
| 5 | 16–20 s | CTA | **Explore the live dashboard** → `us-dash.harlanljones.com`, then fade to black |

Each beat is a hard cut in on its own; text enters with a short slide-up +
fade (`cubicBezier(0,0.6,0.4,1)` / `cubicBezier(0,1,0,1)`), exits in a quick
fade, and siblings stagger by ~100–300 ms. The H3 hex field runs quietly
under the whole cut as texture (data URI SVG, rgba lime stroke).

## Files

- `index.tsx` — the composition (single scene, five beat sequences)
- `tokens.ts` — brand tokens (ink, lime, paper, DM Sans, DM Mono)
- `package.json`, `tsconfig.json` — project scaffold (Diffusion Studio project)

## Open / verify / export (on a machine with the app)

```sh
dapi open ~/Projects/urban-signal-promo   # open the folder
dapi check urban-signal-promo             # black frames, zero-duration, failed assets
dapi capture urban-signal-promo -t 1 5 9 13 17   # one frame per beat
dapi capture urban-signal-promo --count 1 --time 1.5   # frame 1.5 s, brand beat
```

Verify per beat against the table above, then reconcile captured frames with
this brief. Export only when prompted.

## Notes / known gaps

- Fonts: DM Sans / DM Mono must be installed on the machine that renders
  (`dapi fonts` to confirm). If missing, swap `tokens.ts` to an installed
  family and re-check — nothing else changes.
- The hex field is a tiled SVG data URI; if the `<html>` capture behaves
  unexpectedly, replace it with a plain `<rect>` fill — it is texture, not
  content.
- No bundled audio; a music bed or VO can be added under the sequence once
  an approved source exists.
