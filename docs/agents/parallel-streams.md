# Running streams in parallel

Rules for orchestrating more than one agent against this repository at once.
The reasoning, evidence, and metrics behind them are in the Agent Interlock
design doc; this file is the normative short form that agents follow.

## Spine and leaf

`docs/agents/spine-manifest.txt` lists the **spine**: files more than one
concurrent stream may need to edit. Everything else is a **leaf**.

For a new city, the leaf is `src/spatial/cities/<city>.py` and its tests —
400 to 900 lines, roughly 88% of the work. The spine edits are small and
mechanical: an enum member, an alias block, a registry entry, endpoint fields,
and whatever field-name fallbacks the city's schema needs in the shared
producers.

## The three phases

**1. Claim.** Before editing anything, state your stream id, your leaf files,
and the spine files you expect to need. If you cannot name your leaf files up
front, the task is not decomposed enough to run in parallel — say so instead of
starting.

**2. Build — leaf only.** Do the bulk of the work without opening a single
spine file. Commit leaf work freely; an interrupted leaf commit is inert
because nothing references it yet. Write findings to a file the moment you
learn them, not at the end.

**3. Interlock — spine, one stream at a time.** Make the spine edits, run the
invariant checks, and finish. Rules while holding the interlock:

- **Never park a torn write.** If the invariants are red, either finish the
  change or revert it. Do not stop in between — a half-applied spine change
  imports cleanly and fails at runtime, which is the exact failure this
  pattern exists to prevent.
- **Do not hold across long work.** Network fetches, schema research, and
  design belong in phase 2.
- **Keep spine edits additive.** If your spine edit is large, the spine needs
  refactoring — raise that rather than working around it.

## The invariants

Before finishing any spine edit, these must hold. The first one catches the
canonical torn write, where a lookup gains an identifier the registry lacks:

```python
# Closure: every identifier a lookup can return must resolve.
for alias, cid in ALIASES.items():
    assert cid in REGISTRY

# Containment: declared hierarchies actually nest.
#   every submarket coordinate inside its division bbox,
#   every division bbox inside the metro bbox.
```

Run `pytest tests/unit/test_producers_seattle.py tests/unit/test_producers_la.py`
for the closure and containment checks, then the full suite before finishing.

**Completeness** is the third class: if you register an entity, either give it
every field its consumers index without a guard, or route those consumers
through a guarded accessor. `get_dataset()` in `src/spatial/city_registry.py`
is the accessor for feeds — use it rather than indexing `.datasets[...]`
directly, so a city that lacks a feed fails with a readable message.

## Partial registrations are allowed

Not every city publishes every feed. Los Angeles has no open 311 or recorded
-deeds endpoint, so it registers two feeds rather than four. Register only what
exists and let `get_dataset()` raise for the rest — never point a feed at a
stale or unofficial mirror to fill the shape.

## Leaving a trail

If you are interrupted, the next agent starts cold with nothing but the working
tree. Keep a running note of claim, decisions, current step, and next step, and
commit it with the work. The absence of one is what makes a takeover expensive.
