# Issue tracker: Linear

Issues and specs for this repo live in **Linear**. Agents drive it through the repo's
`bun run linear` wrapper rather than by calling the Linear API directly.

> **Resolved (2026-08-23):** the `linear` script exists in the root `package.json`
> (added with the Turborepo conversion); it delegates to the `linear` CLI
> (`@schpet/linear-cli`, on PATH at `~/.cache/.bun/bin/linear`).
> **If the command is not available, do not improvise an alternative** — no `gh issue`,
> no `.scratch/` markdown files, no direct API calls. Stop and tell the human, and
> carry on with whatever part of the task does not need the tracker.

## Conventions

All tracker operations go through `bun run linear`. Run `bun run linear --help` once at
the start of a session that needs the tracker, and use the subcommands it reports.

Do not guess at subcommand names or flags from this file — the wrapper's surface is the
source of truth, and this document deliberately does not enumerate it.

## When a skill says "publish to the issue tracker"

Create a Linear issue via `bun run linear`.

## When a skill says "fetch the relevant ticket"

Read the Linear issue by its identifier via `bun run linear`.

## States and labels

Linear has its own workflow states (Backlog / Todo / In Progress / Done / Canceled)
*and* labels. The five canonical triage roles in `docs/agents/triage-labels.md` are
**labels**, not states — applying `ready-for-agent` should not move an issue's state
unless a skill explicitly says to.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external GitHub PRs
as feature requests; `/triage` reads this flag.)_

The code lives on GitHub (`harlanljones/urban-signal`) while issues live in Linear, so
PRs and issues are in separate systems — there is no shared number space. Reference a
Linear issue from a PR by its identifier, never by a bare `#number`.
