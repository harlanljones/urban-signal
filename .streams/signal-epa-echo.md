# Stream log — signal-epa-echo — 2026-08-26

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** `signal-epa-echo`
- **Leaf files I will create/edit:** `docs/research/epa-echo-validation.md` + optional leaf module under `apps/api/src/spatial/` + optional unit test. This `.streams/signal-epa-echo.md` is a leaf log file.
- **Spine files I expect to need:** none. This is a signal-VALIDATION task (US-170). No registry/enums/producers/submarkets edits are needed; the deliverable is a research/validation document and, only if warranted, a self-contained leaf module with its own unit test that imports no spine symbols.

## Intent

Validate EPA ECHO (Enforcement and Compliance History Online) as a
compliance-event signal for neighborhood environmental risk. Produce evidence
about its source/API, facility & compliance events, geographic detail, update
cadence, and mapping to US spatial units (metro → division → submarket → H3
7–9). Conclude ADOPT / REJECT / DEFER with risks (event sparsity, geocoding)
and, if the signal is plausible as a leaf, a small self-contained module + unit
test. Do not touch spine files; if a spine edit turns out unavoidable, stop and
report the exact delta.

## Decisions

- 2026-08-26 — created claim; researching EPA ECHO API.

## Current step

Phase 2 DISCOVERY: researching EPA ECHO source/API and geography.

## Next step

Write `docs/research/epa-echo-validation.md`, decide ADOPT/REJECT/DEFER, add
leaf module + test only if warranted, then verify imports/tests and commit on
`feat/epa-echo`.
