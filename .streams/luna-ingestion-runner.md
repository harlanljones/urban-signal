# Stream log — luna-ingestion-runner — 2026-10-03

## Claim

- **Stream id:** `luna-ingestion-runner`
- **Leaf files:** `apps/api/src/ingestion/runner.py`, `apps/api/tests/unit/test_ingestion_runner.py`, `.streams/luna-ingestion-runner.md`
- **Spine files:** none

## Intent

Implement commit, replay, normalization and fixed-as-of permit features using source/store interfaces, with fail-closed completeness and isolated feature publication.

## Decisions

- Scoped identity is NYC/feed plus only validated `identity_fields`; source row ID remains acquisition metadata.
- `complete` defaults false. Reconciliation removes absent identities only when both reconciliation and explicit full-scope completion are true.
- Store keys are relative to the configured object-store root/prefix: `raw/pages/`, `manifests/`, `features/`, and separate acquisition/features checkpoints.
- A manifest binds its parent key and hash, full source contract hash, fixed UTC as-of, actual acquisition time, completeness, query bounds, cursor, page hash and row counts.
- Replay verifies the complete hash-linked lineage and stored projected pages, restores deltas/reconciliations, recomputes windows, and reports whether the feature pointer matches the acquisition head.
- Receipts expose normalized records as JSON-safe lists. Storage request count is unknown at the adapter boundary; byte totals and store method-call counts are reported separately.
- Permit costs and predictions remain unavailable; the feature payload has alerts disabled and no production publishing capability.

## Current step

Implementation complete. Captured the checkpoint version before restore so any concurrent commit causes CAS conflict instead of dropping rows. Added a regression test for that interleaving and for a stale feature pointer.

## Verification

- `PYTHONPATH=. .venv/bin/python -m pytest tests/unit/test_ingestion_runner.py tests/unit/test_ingestion_source.py tests/unit/test_ingestion_store.py -q` — 67 passed.
- `.venv/bin/ruff check src/ingestion/runner.py tests/unit/test_ingestion_runner.py` — passed.

## Remaining integration notes

- CLI must call `SourceContract.assert_ready()` before live acquisition and set `input_mode="live"`; local fixture runs remain explicitly `local_fixture`.
- Live source completeness and durable provider guarantees remain gated by M1/M2 evidence. The CLI's record cap bounds memory; full bootstrap capacity beyond that cap still requires measurement and a resumable strategy.

## Root integration handoff
Luna runner/tools interrupted by usage limit; root completed local integration and focused verification. See docs/research/shadow-ingestion-validation-2026-10-03.md for tests and operational gates. Root owns CLI/workflow/test integration and commits; no spine changes.
