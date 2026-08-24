# Gates: HAR-41 Python core migration into apps/api

OWNS: apps/api/**, pyproject.toml, Dockerfile, docker-compose.yml, uv.lock, .github/workflows/**, deploy/k8s/**, PLAN.md, GATES-HAR-41.md, .streams/migration-apps-api.md

Scope: relocate the Python application and its tests under `apps/api`, then update local, container, CI, and deployment entry points to use the canonical package location.

- [x] G1: migration layout is canonical
  CHECK: test -f apps/api/pyproject.toml && test -d apps/api/src && test -d apps/api/tests && test ! -e pyproject.toml && test ! -e src && test ! -e tests && echo "migration layout verified"
  EXPECT: migration layout verified
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=8b135ff75a3d/30 entries; output=migration layout verified

- [x] G2: Python unit test suite passes from the migrated package
  CHECK: ../../.venv/bin/pytest -q --ignore=tests/e2e --ignore=tests/unit/test_serving.py && echo "python unit verification passed"
  EXPECT: python unit verification passed
  CWD: apps/api
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal/apps/api; path=8b135ff75a3d/30 entries; output=SKIPPED [1] ../../tests/unit/test_ckan_client.py:367: live probe disabled | python unit verification passed

- [x] G3: interlock invariants pass against the migrated package
  CHECK: ../../.venv/bin/pytest -q -m interlock && echo "interlock verification passed"
  EXPECT: interlock verification passed
  CWD: apps/api
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal/apps/api; path=8b135ff75a3d/30 entries; output=-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html | interlock verification passed

- [x] G4: container and deployment entry points reference apps/api
  CHECK: rg -q "apps/api" Dockerfile docker-compose.yml deploy/k8s/inference/inference-deployment.yaml deploy/k8s/consumers/keda-scaledobject.yaml && ! rg -q "COPY src/" Dockerfile && echo "deployment references verified"
  EXPECT: deployment references verified
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=8b135ff75a3d/30 entries; output=deployment references verified

- [x] G5: JavaScript workspace checks remain green
  CHECK: bun run typecheck && bun run build
  EXPECT: /Tasks:.*successful|successful/
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=8b135ff75a3d/30 entries; output=$ turbo run build | • turbo 2.10.11

- [x] G6: changed files have no whitespace errors
  CHECK: git diff --check && echo "whitespace verification passed"
  EXPECT: whitespace verification passed
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/harlan/dev/urban-signal; path=8b135ff75a3d/30 entries; output=whitespace verification passed
