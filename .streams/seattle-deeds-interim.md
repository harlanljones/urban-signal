# Stream log — seattle-deeds-interim — 2026-08-24

## Claim

- **Stream id:** `seattle-deeds-interim`
- **Leaf files I will create/edit:** none
- **Spine files I expect to need:** `apps/api/src/spatial/city_registry.py` (SEATTLE DEEDS comment block only)

## Intent

User directive: pursue `rpsale_extr` registration, access question first.
Resolve whether the AGO-restricted table is reachable via any public route;
if yes, verify + register; if no, land the interim posture recommended by
docs/research/seattle-deeds-replacement.md §Interim posture.

## Decisions

- 2026-08-24 — Access conclusively NOT solvable anonymously: AGO item → 403
  GWM_0003; org service directory (1,171 services) has no rpsale;
  gismaps.kingcounty.gov enumerated (31 folders) — Property/KCGIS carry no
  sales table beyond KingCo_PropertyInfo layer 3, the same frozen extract
  (110,857 rows). Both public copies of KC sales data are the dead layer.
- 2026-08-24 — Registration against an unverifiable endpoint would ship a
  permanently erroring feed and violates the verify-before-register rule, so
  no spec change. Landed the documented interim posture instead:
  KNOWN-DEAD PUBLICATION comment on the SEATTLE DEEDS spec pointing at the
  research doc and forbidding repoint-at-frozen-copy.
- 2026-08-24 — Terms blocker recorded for whoever unblocks access:
  rpsale_extr SDC terms are obtainer-only / no redistribution without
  written authorization; public-dashboard redistribution needs KC sign-off
  regardless of technical access.

## Current step

Hold closed — interlock 20 passed; full suite 567 passed / 0 failed
(concurrent user fixes cleared the two previously pre-existing failures);
ruff: no new findings in edited region.

## Next step

Human action: email giscenter@kingcounty.gov (draft supplied by orchestrator)
requesting public sharing of rpsale_extr or AGO access + terms sign-off for
dashboard redistribution. If KC declines: bulk-file producer path is the
fallback (new capability, spine work).
