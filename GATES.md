# Gates: documentation and screenshot refresh

OWNS: README.md, apps/api/README.md, docs/**, GATES.md

Scope: Refresh current-codebase documentation and capture live dashboard evidence for multi-region comparison.

- [x] G1: Documentation references the current dashboard comparison behavior
  CHECK: rg -n "Washington DC|Montgomery|comparison|screenshot|dashboard" docs README.md apps/api/README.md
  EXPECT: dashboard comparison references found
  EVIDENCE: G1 command returned current references in README.md, apps/api/README.md, docs/dashboard.md, and docs/expansion-roadmap.md.

- [x] G2: Dashboard source and static copy pass the interlock wiring gate
  CHECK: ./.venv/bin/python -m pytest -m interlock apps/api/tests/unit/test_interlock_gate.py
  EXPECT: 20 passed
  EVIDENCE: 20 passed in 1.12s; CWD /home/harlan/dev/urban-signal.

- [x] G3: Captured screenshots exist and are non-empty
  CHECK: node -e "const fs=require('fs'); for (const p of ['docs/screenshots/dashboard-dc-montgomery.png','docs/screenshots/dashboard-comparison-menu.png']) { if (!fs.existsSync(p) || fs.statSync(p).size < 10000) process.exit(1) } console.log('screenshots present')"
  EXPECT: screenshots present
  EVIDENCE: screenshots present; live browser captures are 1920x1080 PNGs.

- [x] G4: Changed files have no whitespace errors
  CHECK: git diff --check
  EXPECT: command exits 0
  EVIDENCE: command exited 0.

## Environment-management repair

- [x] G5: Database, bucket, and ONNX defaults are canonical across source, examples, Compose, and docs
  CHECK: python - <<'PY'
    from pathlib import Path
    files = {p: Path(p).read_text() for p in ['.env.example', 'README.md', 'docker-compose.yml', 'apps/api/src/config.py']}
    assert all('urbansignal' in text for text in files.values())
    assert all('urban-signal-features' in text for text in files.values())
    assert all('CPUExecutionProvider' in text for text in files.values())
    print('canonical environment defaults present')
    PY
  EXPECT: canonical environment defaults present
  EVIDENCE: canonical environment defaults present.

- [x] G6: Production startup rejects placeholder credentials
  CHECK: rg -n "production.*(credential|password|secret)|reject|placeholder|default" apps/api/src/config.py docs/environment.md README.md
  EXPECT: production
  EVIDENCE: project-venv runtime check raised the expected ValidationError for placeholder credentials; valid production credentials were accepted.

- [x] G7: Environment-management documentation covers precedence and deployment paths
  CHECK: rg -n "\.env|Compose|Kubernetes|precedence|secret|CPUExecutionProvider|CUDAExecutionProvider" docs/environment.md README.md
  EXPECT: Kubernetes
  EVIDENCE: docs/environment.md and README.md contain precedence, Compose, Kubernetes Secret, and CPU/CUDA guidance.

- [x] G8: Changed files have no whitespace errors and Python parses
  CHECK: git diff --check && python -m py_compile apps/api/src/config.py
  EXPECT: command exits 0
  EVIDENCE: command exited 0.

## HJ-44 expansion closure gates

Scope: verify the current repository implementation and the remaining model/alerting slice before closing HJ-44. Staging-only evidence remains a manual gate when no staging credentials are available.

- [x] G9: Registry and verified feed-job targets are met
  CHECK: ./.venv/bin/python - <<'PY'
    from src.spatial.city_registry import REGISTRY
    cities = len(REGISTRY)
    jobs = sum(len(reg.datasets) for reg in REGISTRY.values())
    assert cities == 17, cities
    assert jobs == 55, jobs
    print(f'accepted current total: {cities} cities, {jobs} feed jobs')
  PY
  EXPECT: accepted current total: 17 cities, 55 feed jobs
  EVIDENCE: 17 cities and 55 feeds verified; the roadmap documents 55 as the safe current total and 57 as aspirational.

- [x] G10: Expansion registrations are wired through the interlock
  CHECK: ./.venv/bin/python -m pytest -m interlock apps/api/tests/unit/test_interlock_gate.py
  EXPECT: 20 passed
  EVIDENCE: 20 passed in 0.99s.

- [x] G11: Open-child focused implementation tests pass
  CHECK: PYTHONPATH=. ./.venv/bin/python -m pytest -q apps/api/tests/unit/test_producers_boston.py apps/api/tests/unit/test_producers_baltimore.py apps/api/tests/unit/test_producers_montgomery.py apps/api/tests/unit/test_feed_staleness_probe.py apps/api/tests/unit/test_calibration.py
  EXPECT: passed
  EVIDENCE: 25 tests passed with PYTHONPATH=. so the top-level scripts import resolves.

- [x] G12: Model and dispatcher implementation satisfies local HJ-29 coverage
  CHECK: PYTHONPATH=. ./.venv/bin/python -m pytest -q apps/api/tests/unit/test_calibration.py apps/api/tests/unit/test_dispatcher.py
  EXPECT: passed
  EVIDENCE: 9 tests passed after removing the serving-package eager-import cycle.

- [x] G13: Changed files remain clean
  CHECK: git diff --check
  EXPECT: command exits 0
  EVIDENCE: command exited 0.

- [ ] G14: Staging ingestion and alert delivery evidence exists
  MANUAL: Run the documented staging soak/probe with configured credentials and attach the result to HJ-23, HJ-25, HJ-26, and HJ-27 before claiming HJ-44 complete.
