# AGENTS.md

Urban Signal — agent-facing conventions for this repo.

## Agent skills

### Issue tracker

Issues live in **Linear**, driven through the repo's `bun run linear` wrapper
(delegates to the `linear` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, each label string equal to its name (`needs-triage`,
`needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` at the repo root, one `docs/adr/` for all decisions
(ADR 0001 — Agent Interlock — is the first). See `docs/agents/domain.md`.

### Parallel agent streams

Spine/leaf partition, the three-phase interlock, and the invariants that gate a
spine edit. Read before running more than one agent at once. See
`docs/agents/parallel-streams.md` and `docs/agents/spine-manifest.txt`.
Before releasing a spine edit run the gate from `apps/api`: `pytest -m interlock`. Stream
claims live in `.streams/<id>.md`; dispatches are recorded in
`.streams/dispatch-log.md`; `python scripts/interlock_gap.py <base>` reports
whether planned work is leaf-shaped.

### City registration rule

**Never register a city without verifying it appears on the map.** A
registration is not done when `REGISTRY` accepts it — it is done when the city
shows up in the dashboard: a `METRO_META` entry (metro chip + `?city=` deep
link), snapshot export coverage, res-5 grid-tile coverage in the published
manifest, and the byte-synced `apps/dashboard/public/index.html` static copy.
This is enforced, not conventional: `apps/api/tests/unit/test_interlock_gate.py::TestDashboardWiring`
and `TestSnapshotWiring` fail any `pytest -m interlock` run where a registered
city is missing from the map. Wire the dashboard (or accept a red gate) in the
same spine hold as the registry entry — never "docs later".

### CI/CD pre-flight (must run before ending any task)

**Every change in this repo breaks CI/CD consistently unless the full pre-flight
passes first.** The `batch-push-deploy` workflow runs the gates below on every
push/PR to `main`; a failure blocks deployment. Run the pre-flight before
ending any task, not as a fixup afterward.

Single command:

```bash
python3 scripts/verify_cicd_preflight.py
```

What it checks (in order, stops on first failure):

1. **API interlock gate** — `pytest -m interlock` from `apps/api` (24 tests,
   covers closure, completeness, containment, dashboard wiring, snapshot export,
   and grid-tile coverage). Fails when a registered city is missing from the map
   or a registered endpoint has no settings field.

2. **Dashboard ↔ product-site cross-reference** — parses the `METRO_META` block
   out of `serving/dashboard.py` AND its byte-synced
   `apps/dashboard/public/index.html`, then compares both against `REGISTRY`
   and `apps/product/public/facts.json`. Fails when a city change landed on one
   surface but not the other (a new city on the dashboard map with no product
   page, or a product metro with no map chip). A registry change is only
   complete when the dashboard, the static copy, and the product facts all carry
   the same city set.

3. **Product facts drift** — `cd apps/product && bun run facts:check` — compares
   `facts.json` + `cities/*.json` against the live `REGISTRY`. Fails when any
   registry change (new city, new feed, changed endpoint) is not reflected in
   the product-site artifacts. **This is the most commonly broken gate** — fix
   with `bun run facts:export` from `apps/product`.

4. **Product site lint** — `cd apps/product && bun run lint` — builds the full
   product site (`dist/`), verifies agent surfaces, and confirms every route
   renders correctly for all registered cities.

5. **Dashboard export** — `python3 scripts/export_dashboard.py` — regenerates
   `apps/dashboard/public/index.html` from `serving/dashboard.py` and confirms
   byte-sync is exact.

6. **Ruff on changed files** — `ruff check` on any new or modified Python files
   in `apps/api/src/` and `apps/api/tests/`.

A clean pre-flight before the final commit means the CI push will pass. Run it
after every significant change, not just at the end.
