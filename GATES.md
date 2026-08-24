# Gates: US-29 product site v2

OWNS: apps/product/**, scripts/export_site_facts.py, GATES.md

Scope: complete the product site's multi-page information architecture, registry-derived city pages, agent surfaces, and release verification.

- [x] G1: Product build succeeds from the repository root.
  CHECK: bun run build
  EXPECT: SITE_BUILD_OK
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=729ddf613f73/31 entries; output=$ turbo run build | • turbo 2.10.11
- [x] G2: Repository lint and typecheck succeed.
  CHECK: bun run lint && bun run typecheck
  EXPECT: Tasks:
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=729ddf613f73/31 entries; output=$ turbo run typecheck | • turbo 2.10.11
- [x] G3: Product agent surfaces verify against the registered-city contract.
  CHECK: node apps/product/scripts/verify-agent-surface.mjs
  EXPECT: AGENT_SURFACE_OK
  EVIDENCE: `node apps/product/scripts/verify-agent-surface.mjs` → `AGENT_SURFACE_OK`.
- [x] G4: Multi-page output contains every required route and all registered city pages.
  CHECK: node apps/product/scripts/verify-multi-page.mjs
  EXPECT: MULTI_PAGE_OK
  EVIDENCE: `node apps/product/scripts/verify-multi-page.mjs` → `MULTI_PAGE_OK (6 section routes, 21 city routes)`.
- [x] G5: UI detector completes against changed product targets.
  CHECK: node /home/harlan/.agents/skills/impeccable/scripts/detect.mjs --json apps/product
  EXPECT: impeccable detect:
  EVIDENCE: Detector completed in degraded regex mode (parser modules unavailable), returned no findings; this is an undercount limitation, not a full clean bill of health.
- [x] G6: Product routes render at desktop and mobile widths with no console/runtime errors.
  EVIDENCE: Desktop browser verified `/`, `/system/`, `/evidence/`, `/methodology/`, `/architecture/`, `/cities/`, and `/cities/nyc/`; mobile viewport 390×844 verified no horizontal overflow and city metadata rendered correctly. Screenshots: `.impeccable/review/us29-desktop.png`, `.impeccable/review/us29-mobile.png`.
