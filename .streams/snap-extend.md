# Stream log — snap-extend — 2026-08-27

## Claim

- **Stream id:** snap-extend
- **Leaf files I will create/edit:** none (single-file spine edit + tests)
- **Spine files I expect to need:** apps/api/src/spatial/city_registry.py,
  apps/api/tests/unit/test_producers_snap.py, apps/product facts artifacts
  (via `bun run facts:export`)

## Intent

Extend the USDA SNAP SLA registration (965b312: dallas, denver, columbus,
raleigh, boise, wichita) to ALL remaining registered metros lacking
`FeedType.SLA`, via the shared `snap_sla_spec(state)` helper. No .github/
workflows changes. No git commit.

## Decisions

- 2026-08-27 17:55Z — Live REGISTRY probe (`reg.datasets.get(FeedType.SLA)`)
  confirms SLA-less set = task list of 20 **plus `prince_georges` (MD)**.
  Headline instruction says "ALL remaining registered metros that lack a
  FeedType.SLA spec" and the list was flagged untrusted, so prince_georges is
  included (21 metros, 13 states). austin/baton_rouge/boston/... already carry
  their own (non-SNAP) SLA specs — untouched.
- 2026-08-27 17:58Z — Single live probe (one grouped `outStatistics` count by
  State on the FeatureServer) confirms `State` column values are two-letter
  codes (format `State = 'XX'` valid) and NO state returns 0 rows, so no
  metro is skipped. Counts: CA 30079, HI 861, IN 5385, MD 3752, NC 8941,
  NM 1628, NV 1984, OH 9477, OK 3746, PA 9642, TN 6384, TX 20715, WA 4852.
- 2026-08-27 17:58Z — san_jose IS its own CityId in REGISTRY (distinct from
  the SF metro registration/divisions) → gets its own CA slice. pierce is WA.
  Duplicated state filters across metros sharing a state (TX x4 new,
  NV x2, TN x2, OH x2, NC x2, CA x2) follow the documented starter pattern
  (dallas/fort_worth both TX) — kept consistent.
- 2026-08-27 18:40Z — Registry insertions done via AST-located block insert
  (21 entries, 4-line comment + `FeedType.SLA: snap_sla_spec("<ST>")`), byte
  shape identical to the 965b312 hunks. Post-edit REGISTRY probe: zero
  SLA-less metros; all 21 new specs verified for where/cadence/mode/geocode.
- 2026-08-27 18:55Z — Tests: added `SNAP_EXTENDED_METROS` (21 pairs) +
  `test_extended_set_registers_sla_specs` + `test_every_registered_metro_has_sla`
  (supersedes the stale `test_non_starter_sla_less_city_still_raises` houston
  pin); contract test now iterates all 27 specs. Refreshed 15 stale per-city
  assertions in 13 files (exact-set assertions gain FeedType.SLA; SLA dropped
  from absent-raise lists; "only" test names updated). Pre-existing non-SNAP
  SLA specs carry `where=None` — the every-metro test asserts presence only.
- 2026-08-27 19:05Z — Ruff: global all-rules config applies; gate measured as
  zero NEW findings (HEAD-vs-worktree per-file comparison, stdin-filename
  method): city_registry 60==60, config 13==13, every touched test file at
  parity. One transient regression (pittsburgh unused-import after raise-block
  removal) fixed to parity. Product facts re-exported (SITE_FACTS_OK, 57
  metros; sla entries populated in city JSONs); `bun run lint` green.

## Outcome

- Interlock: `pytest -m interlock` → 22 tests, 0 failures.
- Full suite: `pytest -q` → 1588 tests, 0 failures/errors, 3 skipped
  (1585 passed — baseline parity; +2 new tests, −1 stale raise pin, −1
  las_vegas parametrize case).
- Ruff: zero new findings vs HEAD on all touched files.
- Product: facts:export regenerated facts.json + cities/*.json; bun run lint
  green (SITE_CONTENT_OK / AGENT_SURFACE_OK / MULTI_PAGE_OK, 57 city routes).
- US-364 commented (state untouched, already completed); comment body file
  deleted.
- Changeset (no commit made):
  - apps/api/src/spatial/city_registry.py (21 SLA specs)
  - apps/api/tests/unit/test_producers_snap.py
  - apps/api/tests/unit/test_producers_{charlotte,chattanooga,cleveland,
    dayton,houston,indianapolis,las_vegas,pierce,pittsburgh,
    prince_georges,reno,tulsa}.py
  - apps/product/public/facts.json + apps/product/public/cities/*.json
  - .streams/snap-extend.md, .streams/dispatch-log.md (append)

## Current step

DONE — stream complete, no follow-ups. (Other stream's files
.github/workflows/batch-push.yml and docs/research/probe-*.md untouched.)

## Next step

None.
