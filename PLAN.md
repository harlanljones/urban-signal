# HAR-41 migration plan

Objective: make `apps/api` the canonical Turborepo location for the Python core while preserving the existing `src` import namespace and updating every supported execution surface.

## Depth tree

1. Contract and ownership
   - [completed] claim HAR-41 in Linear and establish the migration ledger
   - [completed] declare the dedicated interlock stream
2. Relocate Python package
   - [completed] move `src/`, `tests/`, `pyproject.toml`, and `uv.lock` under `apps/api`
   - [completed] update Python tooling and root scripts to execute from `apps/api`
3. Integrate execution surfaces
   - [completed] update Docker, Compose, Kubernetes, and CI paths
   - [completed] add the package to the workspace without duplicating Python ownership
4. Verify and report
   - [completed] run the migration gates and recheck Linear state

Verification note: the migrated unit and interlock suites are green. Existing serving/e2e tests require a reachable Kafka listener and stall in this sandbox, so they remain an environment-dependent follow-up rather than a migration failure.

Boundary: root `scripts/` remains in place because it is repository orchestration code; commands that import the API package will set their working directory or `PYTHONPATH` explicitly. Existing unrelated dirty files remain untouched.
