# Stream log — signal-hmda — 2026-08-26

## Claim

- **Stream id:** `signal-hmda`
- **Leaf files I will create/edit:** `docs/research/hmda-validation.md`; optional leaf module `apps/api/src/spatial/hmda_metrics.py` + `apps/api/tests/unit/test_hmda_metrics.py`
- **Spine files I expect to need:** none (read-only validation; no `FeedType`/`DatasetSpec`/registry edit)

## Intent

Validate HMDA (Home Mortgage Disclosure Act) loan-level public data as a
contextual signal for neighborhood change / investment pressure. Decide
adopt / reject / defer, backed by evidence on source, geography/temporal
detail, mortgage-activity metrics, and mapping onto the repo's H3 7–9 /
division / submarket units. No spine edit; if one proves required, stop and
report.

## Decisions

- 2026-08-26 — created claim; beginning discovery.
- 2026-08-26 — live HMDA JSON/CSV probing **blocked** in this sandbox (Data
  Browser is a client-rendered SPA returning index.html for all routes; dev-API
  page serves a .gov interstitial). Grounded doc in authoritative HMDA/CFPB
  documentation, marking live-unverified claims.
- 2026-08-26 — verdict **DEFER (reject-leaning)**: HMDA adds genuine but *narrow*
  independent coverage (investor-occupancy share, denial rate) no feed has, but
  duplicates DEEDS on the transaction core, is coarser than H3 7–9 (census
  tract), annual/~12–18-mo lag, and needs a spine change (new FeedType + bulk-CSV
  producer). Added leaf helper `apps/api/src/spatial/hmda_metrics.py` + test
  (13 pass); no spine edit.

## Current step

Leaf deliverables complete: `docs/research/hmda-validation.md` + leaf module +
test (passing). Awaiting final commit on `feat/hmda`.

## Next step

Commit leaf files on `feat/hmda` (blocked by repo `git commit*` deny rule; will
report if still denied). No spine delta; recommend DEFER.
