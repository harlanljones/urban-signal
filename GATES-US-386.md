# Gates: US-386 registration-as-data

OWNS: apps/api/src/spatial/**, apps/api/src/config.py, apps/api/tests/**, docs/agents/spine-manifest.txt, GATES-US-386.md

Scope: Move city registration and endpoint declarations to validated declarative data while preserving all existing runtime exports and spine invariants.

- [x] G1: Declarative registry loader and compatibility tests pass
  CHECK: .venv/bin/python -m pytest -q tests/unit/test_city_data.py tests/unit/test_interlock_gate.py tests/unit/test_derived_registry.py tests/unit/test_city_registration.py
  EXPECT: passed
  CWD: apps/api
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal/apps/api; output=104 passed.

- [x] G2: Spine interlock gates pass
  CHECK: .venv/bin/python -m pytest -m interlock
  EXPECT: passed
  CWD: apps/api
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal/apps/api; output=24 passed, 2286 deselected.

- [ ] G3: Full API test suite passes
  CHECK: pytest -q
  EXPECT: passed
  CWD: apps/api
  EVIDENCE: pending; full suite produced four dots and then made no progress for more than two minutes, so it was interrupted for diagnosis.
