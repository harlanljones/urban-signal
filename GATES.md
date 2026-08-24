# Gates: HAR-43 marketing and learning site

OWNS: apps/site/**, GATES.md, DESIGN.md, .impeccable/review/**

Scope: Deliver the standalone Urban Signal marketing and learning site with product-truth content, city coverage, architecture exploration, responsive behavior, and production checks.

- [x] G1: The site package builds successfully
  CHECK: bun run build
  EXPECT: SITE_BUILD_OK
  CWD: apps/site
  EVIDENCE: `bun run build` in `apps/site` exited 0 and printed `SITE_BUILD_OK`.

- [x] G2: All registered cities and required product sections are present in the source
  CHECK: node scripts/verify-site-content.mjs
  EXPECT: SITE_CONTENT_OK
  EVIDENCE: `node scripts/verify-site-content.mjs` exited 0 and printed `SITE_CONTENT_OK`.

- [x] G3: The changed UI passes the mechanical design detector
  CHECK: node /home/harlan/.agents/skills/impeccable/scripts/detect.mjs --json apps/site/index.html apps/site/src/main.js apps/site/src/styles.css
  EXPECT: detector completed
  EVIDENCE: Detector exited 0 with no findings; it ran in degraded regex-only mode because optional parser modules are unavailable.

- [x] G4: Desktop and mobile renders are visually inspectable and show the complete first surface
  EVIDENCE: Captured and inspected `.impeccable/review/desktop.png` at 1440px and `.impeccable/review/mobile.png` at 390px after fixing the clipped hero field.
