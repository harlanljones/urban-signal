# Dashboard selection and tile recovery

Fix the three reproduced bugs in `/workspace/us-dash-bug-audit/report.md`.

Luna selection stream owns selected-state globals, asynchronous metro/national inspection, direct/clear selection and linked catalyst highlighting. Older success/failure replies must not override a newer selection or reopen a cleared inspector. Accepting a selection must update the linked list immediately.

Luna loader stream owns tile-generation state and loader/status/retry helpers. Add bounded automatic backoff after transient failures, preserving outgoing cells and the global concurrency cap. Cancel stale retries on generation changes, distinguish successful empty data from failures, and present loading/retry/exhaustion honestly. Recovery must finish without moving the camera. Streams patch separate regions of the same leaf file and do not export/commit.

Root integrates the generated HTML, runs meaningful source-level async/timer regressions and production-origin candidate browser tests (no local server or production mutation), dashboard tests/typecheck/build and API integration/preflight. Independent final Luna review follows implementation. This stream does not activate live ingestion or change backend inputs.
