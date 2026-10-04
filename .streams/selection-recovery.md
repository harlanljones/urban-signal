# Stream log — selection-recovery — 2026-10-04

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** `selection-recovery`
- **Leaf files I will create/edit:** `apps/api/src/serving/dashboard.py`, `apps/dashboard/tests/selection-race.test.js`, `.streams/selection-recovery.md`
- **Spine files I expect to need:** none

## Intent

Prevent stale prediction and coordinate-search responses from replacing current or cleared selections, and refresh the catalyst row highlight only after accepted selection state changes, and cancel pending inspector work when its open mobile drawer is dismissed.

## Decisions

<Appended as made. Findings go here the moment they are learned (F5) —
not at the end.>

- 2026-10-04 — Root cause confirmed: async prediction awaits can settle after another selection or clear; zoom updates the map selection before the inspector accepts its async result, while catalyst rows only re-render at zoom start. A third async entrypoint, coordinate/H3 search, also awaited prediction without checking whether selection changed. Dismissing an open right mobile inspector must invalidate pending results while leaving accepted selection intact; left menu and search close actions must not cancel it.

## Current step

Implemented generation invalidation in both prediction entrypoints and coordinate/H3 search, plus direct selection, clear, and right-inspector dismissal; added nine behavior tests against the extracted production functions.

## Next step

Focused Bun test passes (9/9); `git diff --check` passes. Parent owns static export and wider integration checks.
