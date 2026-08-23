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
(neither exists yet; they get created lazily). See `docs/agents/domain.md`.

### Parallel agent streams

Spine/leaf partition, the three-phase interlock, and the invariants that gate a
spine edit. Read before running more than one agent at once. See
`docs/agents/parallel-streams.md` and `docs/agents/spine-manifest.txt`.
