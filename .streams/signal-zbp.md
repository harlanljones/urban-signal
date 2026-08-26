# Stream log — signal-zbp — 2026-08-26

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** signal-zbp
- **Leaf files I will create/edit:** `docs/research/zbp-validation.md` + optional
  leaf module `apps/api/src/spatial/zbp_signal.py` and
  `apps/api/tests/unit/test_zbp_signal.py`
- **Spine files I expect to need:** none. This is a Tier-A validation/signal
  assessment leaf (Linear US-167). ZBP requires no spine edit to *assess*; if a
  future REGISTER is opened it would need a new signal family / FeedType
  (spine/interlock), which this leaf does not perform — it stops and reports if
  that boundary is ever crossed.

## Intent

Validate Census ZIP Code Business Patterns (ZBP) as a commercial-change signal for
Urban Signal: establish source/access, geographic unit (ZIP vs ZCTA), variables
(establishments, employment, payroll, NAICS), cadence/lag, confidentiality
behavior, and the mapping path from ZIP to the repo's H3 7–9 spatial units. Conclude
adopt / reject / defer with a concrete unblock path. No feed is registered; no
spine file is touched.

## Decisions

- 2026-08-26 — Claimed stream; created branch `feat/zbp`. Phase-1 template copied.
- 2026-08-26 — Verified live that the ZBP API endpoint exists
  (`api.census.gov/data/2023/zbp` returned a key error, not 404), confirming the
  dataset is published and queryable; detailed methodology HTML pages were not
  fetchable from this sandbox, so vintage-specific cadence facts are marked
  **unverified** where material.
- 2026-08-26 — Conclusion: **DEFER** as a registered feed (same spine-gated reason
  as LODES/BFS — no event-stream shape, needs a new signal family), but note ZBP is
  the *strongest* commercial-change candidate of the validation wave because it
  carries establishment/employment/payroll by NAICS at ZIP level and the repo
  already has a ZIP→ZCTA crosswalk path researched (docs/research/hud-usps-vacancy.md).

## Current step

Writing `docs/research/zbp-validation.md` (phase 2 leaf build) after discovery.

## Next step

Add an optional self-contained leaf module `apps/api/src/spatial/zbp_signal.py`
(ZIP→H3 projection + confidentiality-flag normalization) with a unit test, run the
test, then commit both leaf files on `feat/zbp`.
