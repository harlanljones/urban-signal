# AGENTS.md

Urban Signal — agent-facing conventions for this repo.

## Agent skills

### Issue tracker

Issues live in **Linear**, driven through the repo's `bun run linear` wrapper (that script
does not exist yet — see the setup gap note). See `docs/agents/issue-tracker.md`.

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
Before releasing a spine edit run the gate: `pytest -m interlock`. Stream
claims live in `.streams/<id>.md`; dispatches are recorded in
`.streams/dispatch-log.md`; `python scripts/interlock_gap.py <base>` reports
whether planned work is leaf-shaped.
