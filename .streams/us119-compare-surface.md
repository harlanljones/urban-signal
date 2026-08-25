# Stream log — us119-compare-surface — 2026-08-24

## Claim

- **Stream id:** us119-compare-surface
- **Leaf files I will create/edit:** `apps/product/pages/compare.html`, `apps/product/scripts/render-city.mjs`
- **Spine files I expect to need:** none (both target files are leaf surfaces; no shared edits applied)

## Intent

Surface the live dashboard's nearby-region comparison mode on the product site: add an honest section to `/compare/` describing nearby metros within 175 miles selectable/layered over the current city and preserved in exports, and — if it improves the CTA — mention comparison in the "Open the live map" affordance on city pages. Copy only; no routing changes.

## Decisions

- <2026-08-24> Claimed US-119 (`--assignee self`, `--state started`) and created this stream log.
- <2026-08-24> Dashboard reads only `?city=` via `deepLinkedCity()` (`apps/api/src/serving/dashboard.py:2286-2299`); the base city is the only URL-addressable state. The compare set (`activeCities`) is module-local state set via `applyComparison()` (`:1954-1969`), never read from or written to the URL or `sessionStorage`. **Compare state is NOT URL-addressable** → copy-only section on `/compare/`, no deep-link affordance beyond the existing `?city=` CTA. Evidence: only `URLSearchParams` read in the dashboard HTML is `.get('city')` (`:2291`); no param writes to the compare set.
- <2026-08-24> "Preserved in exports" is taken as stated in the ticket (compare selection persists across the dashboard's export/navigation flow); will phrase copy to match without overclaiming mechanics I cannot verify.

## Current step

Verification + final report.

## Next step

None (reporting).

## PROPOSED SHARED EDITS

These are proposed only — **not applied** (shared/out-of-scope files). The orchestrator decides.

### `apps/product/CHANGELOG.md` — Unreleased → Added entry

> - Documented the live dashboard's nearby-region comparison mode on `/compare/` and metro city pages: registered metros within 175 miles (haversine) are selectable and layered over the current city, sorted by display name, with an empty-state when no neighbor is in range, and the selection is preserved across export.

### `apps/product/public/llms-full.txt` — page-guide line change

Replace line 76:

> - Human product evaluation: `/dashboard`

with:

> - Human product evaluation: `/dashboard` (per-city `?city=<id>` deep links; compare control layers registered metros within 175 miles over the current city — compare set is not URL-addressable)
