# Gates: marketing site critique fixes and agent access

Scope: resolve all five critique priorities in order, then expose the same product truth to humans and machine readers

- [x] G1: evidence claims resolve to concrete repository-backed sources
  CHECK: node apps/dashboard/scripts/verify-agent-surface.mjs
  EXPECT: AGENT_SURFACE_OK
  CWD: .
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=8ad731cfae8c/31 entries; output=AGENT_SURFACE_OK

- [x] G2: mobile and desktop preserve a complete, navigable persuasion path
  EVIDENCE: terminal-browser inspected 1440x1000, 1024x900, and 390x844; mobile clientWidth=380 and scrollWidth=380; 5 of 17 metros shown before explicit expansion; CA filter returned 3; menu announced Close; two closing routes rendered

- [x] G3: marketing city coverage agrees with the authoritative registry
  CHECK: node scripts/verify-site-content.mjs
  EXPECT: SITE_CONTENT_OK
  CWD: .
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=8ad731cfae8c/31 entries; output=SITE_CONTENT_OK

- [x] G4: essential interface copy clears the readability and interaction floor
  EVIDENCE: terminal-browser at 390x844 measured min essential text=12px and min visible interactive target=43.99px (44px CSS floor); no horizontal overflow; desktop/intermediate/mobile visual inspection completed

- [x] G5: machine readers receive product facts, evidence links, and explicit limitations
  CHECK: node apps/dashboard/scripts/verify-agent-surface.mjs
  EXPECT: AGENT_SURFACE_OK
  CWD: .
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=8ad731cfae8c/31 entries; output=AGENT_SURFACE_OK

- [x] G6: the marketing site builds and its JavaScript parses
  CHECK: bun run --cwd apps/dashboard typecheck && node --check apps/dashboard/src/observatory.js && bun run --cwd apps/dashboard build
  EXPECT: SITE_BUILD_OK
  CWD: .
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=8ad731cfae8c/31 entries; output=$ node --check src/main.js | $ node scripts/build.mjs
