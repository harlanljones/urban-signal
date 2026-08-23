# ADR 0001: Agent Interlock

**Status:** Proposed
**Date:** 2026-08-23
**Scope:** urban-signal
**Supersedes:** —

An orchestration pattern and six metrics for running coding agents in parallel
against one repository — derived from a three-stream build that was interrupted
mid-write and left the mainline broken.

## Contents

1. [The incident](#1-the-incident)
2. [Failure modes](#2-failure-modes)
3. [Spine and leaf](#3-spine-and-leaf)
4. [The pattern](#4-the-pattern)
5. [The invariant gate](#5-the-invariant-gate)
6. [Metrics](#6-metrics)
7. [This session, scored](#7-this-session-scored)
8. [Adoption](#8-adoption)
9. [Limits and open questions](#9-limits-and-open-questions)

## 1 · The incident

Three agent streams were dispatched against this repository at once: one
orchestrating agent-driven development of a Seattle city registration, one doing
the same for Los Angeles, and one researching further cities to cover. The
session was interrupted. What survived was this:

```
# working tree at takeover
 M src/config.py
 M src/spatial/cities/__init__.py
 M src/spatial/city_registry.py
?? src/spatial/cities/seattle.py

# the Los Angeles stream and the research stream left nothing at all
```

The Seattle stream had added a `CityId.SEATTLE` enum member, nine lookup
aliases, four dataset endpoints, and a complete 401-line city module. It had
not added the corresponding `REGISTRY` entry. The result imported cleanly,
type-checked, and passed most of the suite:

```
normalize_city('seattle') -> CityId.SEATTLE
SEATTLE in REGISTRY:      False
```

So `normalize_city("seattle")` returned an identifier that nothing could
resolve. Two producers index the registry without a guard, and would raise
`KeyError` on any Seattle request. The tree was not merely incomplete — it was
confidently wrong, in a way that static checks and the existing test suite both
waved through.

That is the failure this document is about. Not the interruption itself, which
is normal and expected, but the fact that an interruption at an arbitrary
instant left a state that looked finished.

> **The core observation**
>
> The interruption landed inside a shared file. Every stream in flight needed
> to edit that same file, and none of them could complete without it.
> Parallelism bought nothing there and cost correctness.

## 2 · Failure modes

Five distinct failures were observed. They are given identifiers because the
pattern and the metrics both refer back to them.

**F1 · Torn write** — A logically atomic change spread across several files was
interrupted partway. The half that landed was syntactically valid and
internally consistent, so nothing complained. Only a cross-file invariant could
have detected it.

**F2 · Silent stream** — Two of three streams produced no durable output
whatsoever — no files, no notes, no partial commits. Their work existed only
inside an agent context that no longer exists. From the repository's side they
are indistinguishable from streams that were never launched.

**F3 · Blind concurrency** — A peer session was still running at takeover and
its subject was unknowable from outside. It later vanished. Any edit to the
shared registry during that window was a coin flip against a conflict, and
there was no mechanism to find out.

**F4 · Spine contention** — Both city streams necessarily edit the same three
files. Work that appears embarrassingly parallel converges on a narrow shared
structure that cannot absorb concurrent writers.

**F5 · Ephemeral findings** — The research stream's entire value was
information. Information that is not written to a file at the moment it is
learned does not survive the agent that learned it.

## 3 · Spine and leaf

Measuring the interrupted change is what makes the pattern obvious. Split the
Seattle stream's work by whether a file is exclusive to one stream or shared by
all of them:

| File | Role | Lines | Contended by |
|---|---|---|---|
| `src/spatial/cities/seattle.py` | Leaf | 401 | this stream only |
| `src/config.py` | Spine | 23 | every city stream |
| `src/spatial/city_registry.py` | Spine | 18 | every city stream |
| `src/spatial/cities/__init__.py` | Spine | 12 | every city stream |

The spine is 53 of 454 lines — 12% of the work — but 3 of 4 files, 75% of the
collision surface. The overwhelming majority of a city's implementation is a
self-contained module that no other stream will ever open. The part that every
stream fights over is three small, mechanical edits.

This asymmetry is the whole design. Because the spine is small, serializing it
costs almost nothing. Because the spine is universal, parallelizing it costs
correctness — and it is exactly where the interruption landed.

```text
PARALLEL · LEAF                      SERIAL · SPINE
  seattle.py        401 ln           INTERLOCK — one holder
  los_angeles.py    608 ln             city_registry.py   18   ┐
  research/*.md     durable            config.py          23   ├ invariant gate · must pass
                                       cities/__init__.py 12   ┘
Leaf work fans out without coordination. Spine work passes through a single
holder and cannot be released until the invariant suite is green.
```

## 4 · The pattern

Railway interlocking prevents two trains from occupying one track section. It
does not make the network serial; it makes exactly the contended sections
serial and lets everything else run free. The same split applies here.

Every repository adopting this declares a **spine manifest**: the explicit list
of files that more than one concurrent stream may need. Everything not on that
list is leaf. The manifest is checked in, and it is the orchestrator's
contract.

### 1 · Claim

Before any edit, a stream writes a claim: its identifier, its leaf files, and
the spine files it will eventually need. Claims are visible to every other
stream, which is what F3 lacked.

Two streams claiming the same leaf file is an orchestration bug — resolve it
before dispatch, not after. A stream that cannot name its leaf files up front
is not yet decomposed enough to run in parallel.

### 2 · Build — leaf only

The stream does the bulk of its work touching nothing outside its own claim.
For a city that is the 400–900 line module, its tests, and its research notes.
No spine file is opened in this phase, so no two streams can conflict and no
interruption can tear a shared structure.

Leaf work commits freely and often. An interrupted leaf commit is inert — it
breaks nothing, because nothing references it yet. Findings are written to a
file the moment they are learned, which is the answer to F5.

### 3 · Interlock — spine, one at a time

The stream takes the interlock, makes the small mechanical spine edits that
wire its leaf into the system, runs the invariant suite, and releases. This is
minutes of work, and only one stream holds it at a time.

The interlock is released only on green. A red suite means the holder either
finishes or reverts — it never parks a torn write, which is the answer to F1.
Holding the interlock across a long-running task is prohibited; fetch,
research, and design happen in phase 2. Spine edits are additive by
construction: one enum member, one registry entry, one import block. If a
stream's spine edit is large, the spine needs refactoring, not more
coordination.

> **Why this beats worktrees alone**
>
> Separate git worktrees remove the write conflict but not the semantic one:
> three branches can each add a valid registry entry and still merge into a
> registry that violates an invariant none of them owned. The interlock is
> about the invariant, not the file lock.

## 5 · The invariant gate

The interlock is only as good as the check that gates it. The check must be
able to fail on the exact partial states a stream can be interrupted in — which
the existing suite could not.

For this repository the missing invariant is four lines, and it fails precisely
on the torn write that was found at takeover:

```python
# every identifier a lookup can return must resolve to a registration
for alias, cid in ALIASES.items():
    assert cid in REGISTRY, f"alias {alias!r} resolves to unregistered {cid}"
```

The generalisable form is **referential closure**: for every structure that
maps a name to a key, assert that every key it can produce exists in the
structure that consumes it. A torn write almost always breaks closure — it
lands one side of a reference and not the other.

Three classes of invariant cover most spine damage:

- **Closure** — every produced key resolves. Catches the
  enum-without-registration, the alias-without-target, the import-without-export.
- **Completeness** — every registered entity has the fields its consumers index
  without a guard, or those consumers are changed to guard.
- **Containment** — declared hierarchies actually nest. Here: every submarket
  coordinate falls inside its own division's bounding box, and every division
  inside the metro box.

Each spine file must be covered by at least one invariant before it is eligible
for parallel work. A spine file with no invariant is a file where a torn write
is undetectable, and it should be treated as un-parallelisable until one
exists.

## 6 · Metrics

Six measures, chosen because each one maps to an observed failure mode and each
is computable from git, CI, or a counted dispatch log. Metrics that require
judgement are marked as *observed* rather than automated — an honest manual
number beats a fabricated automatic one.

| Metric | Definition | Source | Target | Mode |
|---|---|---|---|---|
| Torn-write exposure | Wall-clock minutes the mainline fails the invariant suite. The headline number. | CI run history | 0 | auto |
| Interlock gap | Spine share of files changed minus spine share of lines changed. A wide gap means a few small edits carry all the risk. | `git diff --name-only` ∩ manifest | report | auto |
| Stream yield | Streams that produced a committed, durable artifact ÷ streams dispatched. Directly measures F2. | Dispatch log vs git log | 1.00 | auto |
| Invariant coverage | Spine files with at least one invariant asserting on them ÷ spine files. | Manifest vs test map | 1.00 | semi |
| Resume cost | Tool calls a cold agent needs to reconstruct state and reach its first correct edit. Measures whether streams leave a trail. | Takeover transcript | ≤ 5 | observed |
| Integration rework | Lines the integrator rewrote ÷ lines the streams delivered. Rising rework means the leaf boundary is drawn in the wrong place. | git log per file | < 0.15 | semi |

**Computing the interlock gap** — the one metric worth automating first,
because it identifies which work is safe to parallelize before any is
dispatched. Implemented as `scripts/interlock_gap.py`; run
`python scripts/interlock_gap.py <base>` for any diff range.

A high file share with a low line share is the signature of work that should be
parallel with a serialized tail. A high share on both means the streams are not
actually independent and should be merged into one.

## 7 · This session, scored

The pattern is retrospective, so it is worth applying to the run that produced
it. These are the measured values from the interrupted three-stream session and
the takeover that followed.

| Metric | At takeover | After | Note |
|---|---|---|---|
| Torn-write exposure | breached | 0 | Mainline resolved an unregistered CityId. Duration unknown — no CI signal existed to date it. |
| Interlock gap | 0.75 / 0.12 | — | 75% of files, 12% of lines. The textbook case for serializing the tail. |
| Stream yield | 0.33 | 1.00 | One of three streams left anything on disk, and that one was incomplete. |
| Invariant coverage | 0 / 3 | 3 / 3 | No spine file had a closure assertion. Three now do. |
| Resume cost | ~12 | — | Calls to locate the break by reading git state and re-deriving intent. No stream log existed. |
| Integration rework | — | low | The leaf module was kept whole; all repair was spine-side. Boundary was drawn correctly by luck, not design. |

> **Incidental finding**
>
> The takeover also surfaced a latent defect the parallel streams had nothing
> to do with: any deed record lacking coordinates crashed a geospatial lookup
> and was silently dropped, for every city, in committed code. Streams
> optimised for throughput do not find these. An integration phase that
> actually reads the surrounding code does.

## 8 · Adoption

Four concrete additions, in dependency order. The first two are prerequisites
for dispatching anything in parallel again.

1. **Spine manifest** — a checked-in list at `docs/agents/spine-manifest.txt`,
   one path per line. For this repository it starts as the three contended
   files plus the four producers, which every city stream also amends. Agents
   read it during Claim; CI reads it to compute the interlock gap.
   *(Implemented.)*
2. **Invariant suite** — a test module that asserts closure, completeness, and
   containment across the spine, marked so it can be run alone as the interlock
   gate. It must be fast — a gate nobody runs is not a gate.
   *(Implemented as `tests/unit/test_interlock_gate.py`; run `pytest -m interlock`.)*
3. **Stream log** — each stream writes `.streams/<id>.md` from its first
   action: claim, intent, decisions taken, current step, next step. Updated at
   each step boundary, committed with the work. This is the artifact whose
   absence made the takeover cost twelve tool calls instead of one, and it is
   the cheapest item on this list. *(Implemented via `.streams/_TEMPLATE.md`.)*
4. **Dispatch log** — the orchestrator records what it launched and when, so
   stream yield is computable at all. Without it, a stream that produced
   nothing leaves no evidence it ever existed. *(Implemented as
   `.streams/dispatch-log.md`, seeded with the incident record.)*

**Sequencing note.** Invariant coverage should reach 1.00 before the next
parallel dispatch. The pattern's safety rests entirely on the gate, and this
repository's gate currently covers only the spine files touched during the
takeover. `TestSpineCoverage` in the gate enforces manifest-wide coverage.

## 9 · Limits and open questions

Stated plainly, because a design doc that only argues its own case is not
useful.

1. **One incident, one repository.** The 12%/75% split is measured, but it is a
   single data point from a codebase with an unusually clean leaf structure —
   each city genuinely is a separate module. A repository whose features cut
   across many files will show a much worse gap, and may not be parallelisable
   at all under this pattern.
2. **The spine grows.** Every city so far has needed new field-name fallbacks
   in the shared producers. Those edits are small individually and unbounded
   collectively. At two or three more cities the fallback chains should become
   a per-city mapping table declared beside the dataset spec — which converts
   recurring spine edits into leaf edits, and is the highest-value refactor
   this pattern implies.
3. **The interlock is advisory.** Nothing here enforces exclusion between
   independent agent sessions on one machine; it is a convention plus a gate,
   not a lock. Whether that is sufficient, or whether it needs a real lease
   file, is unresolved.
4. **Resume cost is hand-counted.** It is the metric most likely to be gamed or
   ignored, and the one with the clearest link to recovery pain. A better
   proxy would be welcome.
5. **Untested against a live collision.** The peer session in this incident
   vanished before contending for the spine. The pattern's behaviour under
   genuine simultaneous demand is reasoned, not observed.

---

*Evidence drawn from the interrupted Seattle / Los Angeles / city-research
session and the takeover that followed. Line counts and registry states
measured directly from the repository at time of writing.*
