# Stream log — us103-hud-usps — 2026-08-25

## Claim

- **Stream id:** `us103-hud-usps`
- **Leaf files I will create/edit:** `docs/research/hud-usps-vacancy.md`
- **Spine files I expect to need:** none (read-only research stream)

## Intent

Assess HUD quarterly USPS address-vacancy aggregation as a contextual signal for
residential/business vacancy, long-duration vacancy, and development/change patterns.
Verdict must be one of: register/reject/defer, backed by evidence on access
(eligibility, sublicense terms, restricted access path), cadence, administrative
definitions, methodology-change risk, and incremental value versus existing
permit/license signals.

## Decisions

- **VERDICT: DEFER.** Access is restricted to registered governmental entities and
  non-profit organizations, and the sublicense confines use to a narrow "stated
  purpose" (measuring/forecasting neighborhood changes, assessing neighborhood
  needs, measuring/assessing HUD programs incl. HOME/CDBG/ADDI/ACA) with NO
  selling/licensing/distributing, NO marketing/promotion, confidential +
  proprietary (39 U.S.C. § 412 protects address lists), one-year term,
  D.C. venue. Urban Signal is a public forecasting dashboard with commercial
  investment metrics — direct conflict. Granularity is Census-TRACT aggregates
  (ZIP+4 → tract grouping), not point-level, so it does NOT fit the
  point→H3 7-9 producer model. See docs/research/hud-usps-vacancy.md.

## Evidence log (2026-08-25)

- huduser.gov/portal/datasets/usps.html — confirmed: 2005 HUD–USPS agreement,
  quarterly aggregate VA/NA counts, universe of all US addresses, res vs biz
  split, 90-day + duration-in-category (counting from 2005-11-18), admin
  definitions, MTC ("Move to Competitive") dramatic address increase warning.
- /portal/usps/sublicense_agreement.html — "Sublicense for Census TRACT Level
  Information": eligibility (govt + nonprofit registered), Stated Purpose,
  no-distribution clause, confidential/proprietary + 39 USC 412, 1-yr term.
- Register/login path: huduser.gov/apps/public/usps/register (+ /login); contact
  USPSVacancydata@hud.gov. Register-form specifics & full data dictionary are
  UNVERIFIED (interactive form / xlsx binary; not fetched).

## Current step

Dispatched 2026-08-25 as part of the 5-stream validation wave.

## Next step

Produce `docs/research/hud-usps-vacancy.md` with the validation verdict.
