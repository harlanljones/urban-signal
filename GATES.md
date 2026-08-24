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
