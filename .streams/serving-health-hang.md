# Stream log — serving-health-hang — 2026-08-23

## Claim

- **Stream id:** serving-health-hang
- **Leaf files I will create/edit:** `apps/api/src/serving/app.py`, `apps/api/tests/unit/test_serving.py` only if a fixture/test seam is required
- **Spine files I expect to need:** none

## Intent

Make `tests/unit/test_serving.py::test_health_check` deterministic and non-blocking while preserving its assertions, and verify nearby serving tests with the project `.venv`.

## Decisions

- 2026-08-23 — Initial scope limited to serving initialization, serving test fixture, and config only if directly load-bearing.
- 2026-08-23 — Repro: synchronous Starlette TestClient hangs on a bare FastAPI app with installed FastAPI 0.141.1 / Starlette 1.6.0 / HTTPX 0.28.1; no serving lifespan or network path is involved.
- 2026-08-23 — Fix: constrain HTTPX to 0.27.x and use a synchronous adapter around HTTPX AsyncClient + ASGITransport in the serving tests; assertions remain unchanged.

## Current step

Focused health/metrics/root/dashboard tests pass; broader file run is still being bounded because it exceeds the focused serving scope.

## Next step

Report the dependency incompatibility, exact focused evidence, and any broader-test timeout without claiming live external evidence.
