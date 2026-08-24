# HJ-44 Completion Plan

Acceptance gates:

- [ ] A1: Registry has 17 cities and approximately 57 feed jobs; platform counts and intentional omissions are documented.
- [ ] A2: Every city is wired in the registry, dashboard selector, `CITY_CONFIGS`, and synced edge static copy.
- [ ] A3: Baltimore, Montgomery County, and Boston have focused/live evidence for G1–G10.
- [ ] A4: Weekly staleness monitoring passes stale-fixture detection and staging webhook verification.
- [ ] A5: Model calibration implements warm-up, per-city gates, attribution drift checks, and city alert rate limiting.
- [ ] A6: `pytest -m interlock` and the full suite pass, or every environmental blocker is resolved and recorded.
- [ ] A7: Scorecard and `.streams/dispatch-log.md` contain final yield, spine share, and incident evidence.

Streams:

- `closeout-baltimore`: audit/fix Baltimore evidence and closeout artifacts.
- `closeout-montgomery`: audit/fix Montgomery evidence and closeout artifacts.
- `closeout-boston`: audit/fix Boston evidence and closeout artifacts.
- `verify-staleness`: finish staging/fixture verification for the monitor.
- `model-calibration`: implement HJ-29 model and alert gates.
- `integration`: parent agent reruns gates, reconciles counts, and updates Linear.
