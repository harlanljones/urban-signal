# Dashboard UI polish

Implement the accepted production audit in `/workspace/us-dash-ui-audit/report.md` on an isolated feature branch. Keep Cloudflare serving and daily backend publication intact; do not activate shadow ingestion or change model validity claims.

## Parallel ownership

- Luna dashboard stream owns the embedded dashboard and browser regression tests: city search/active context/recent favorites, real-cell LOD motion with cancellation and reduced motion, selection continuity, source and coverage cues, compact unavailable attribution, 3D strength, mobile bottom sheet, comparison and threshold/reset.
- Luna offline-test stream owns deterministic FEMA crosswalk fixtures and tests. Preserve the unit-network guard and geography assertions.
- Root owns generated HTML export, integration, CI/CD preflight and final verification. Workers do not commit or deploy.

## Acceptance

Keep outgoing hexes while incoming data loads, settle to one current resolution after reversal, preserve geographic selection, avoid boundary oscillation, and honor reduced motion. Do not present publication time as source freshness. Mobile details must leave map context and avoid the existing navigation. Threshold reset restores all cells; compare pins retain truthful forecast/source availability.

Run Node dashboard regressions, Bun dashboard tests/typecheck, targeted FEMA tests, API suite where environment supports it, and mandatory repository preflight after the generated export. Production screenshots are baseline references; changes on this branch are not a production deployment.
