# Dispatch log

The orchestrator appends one row per launched stream, then closes it out with
an outcome. Without this record a stream that produced nothing (failure mode
F2) leaves no evidence it ever existed, and stream yield is not computable.

Format: one table per dispatch date. Yield = streams with a committed,
durable artifact ÷ streams dispatched.

## 2026-08-23 — city expansion (Seattle / Los Angeles / research)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-seattle | `src/spatial/cities/seattle.py` + tests | config.py, city_registry.py, cities/__init__.py | ~09:00 PT | interrupted mid-spine — torn write: enum + aliases landed, REGISTRY entry did not | partial (completed by takeover) |
| city-los-angeles | `src/spatial/cities/los_angeles.py` + tests | config.py, city_registry.py, cities/__init__.py, producers | ~09:00 PT | silent stream — no durable output at takeover; recovered later in mainline work | recovered |
| research-cities | `docs/research/city-expansion-candidates.md` | none | ~09:00 PT | silent stream — findings existed only in agent context | none at takeover |

**Yield at takeover:** 0.33 (1 of 3). **Torn-write exposure:** breached until
takeover repair; duration unknown — no CI signal existed to date it.
Full post-mortem: `docs/adr/0001-agent-interlock.md` sections 1 and 7.

## 2026-08-23 — dashboard city wiring (Seattle / Los Angeles)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| dashboard-seattle | `.streams/dashboard-seattle.md` (spec only) | none — target `src/serving/dashboard.py` held by integrator | ~12:20 PT | completed | spec (applied same day) |
| dashboard-los-angeles | `.streams/dashboard-los_angeles.md` (spec only) | none — same shared-file hold | ~12:20 PT | completed | spec (applied same day) |
| interlock (orchestrator) | apply both specs serially + verify + sync `workers/public/index.html` | n/a | ~12:30 PT | completed | dashboard edit, worker static copy |

**Yield:** 2 of 2 leaf streams. Shared file edited once, serially, after both
specs landed — no concurrent write to `dashboard.py`.

## 2026-08-23 — data-coverage research (expand-feeds / expand-geo-signals / new-orleans-austin / socrata-sweep / platform-hunt)

Research-only dispatch following `docs/research/city-expansion-candidates.md`
recommendation to widen coverage. All five streams are pure leaf: each creates
exactly two files (its `.streams/<id>.md` claim log and one
`docs/research/<topic>.md`). No spine files touched. Deviation from the usual
commit-with-your-work rule: to avoid `.git/index.lock` contention between five
concurrent streams, the **orchestrator commits each stream's artifacts serially
at close-out** instead of the streams committing mid-flight.

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| expand-feeds | `docs/research/current-city-feed-gaps.md` | none | ~13:45 PT | completed | survey: 3 broken registrations (SF deeds ID serves eviction notices; SF permits dead; Chicago deeds deleted), KC sales stale since 2025-11-28, LA 311 relaunched as MyLA311 `2cy6-i7zn` |
| expand-geo-signals | `docs/research/metro-expansion-and-new-signals.md` | none | ~13:45 PT | completed | survey: Pierce County permits = only geographic yes; license-transition + crime signals verified across metros |
| new-orleans-austin | `docs/research/new-orleans-austin-verification.md` | none | ~13:45 PT | completed | survey: NOLA implementation-ready (permits superseded by `rcm3-fn58`); Austin partial city; field-mapping refactor trigger fires (26 fallbacks / 4 cities) |
| socrata-sweep | `docs/research/socrata-sweep.md` | none | ~13:45 PT | completed | ranked sweep: Norfolk VA 4/4 with real sales feed; Cincinnati, Baton Rouge next |
| platform-hunt | `docs/research/non-socrata-platforms.md` | none | ~13:45 PT | completed | Detroit 4/4 on existing ArcGIS client (0 platform code); Philly needs ~150-line CartoClient; CKAN not worth alone; SD dumps rejected |

## 2026-08-23 — wave A feed repairs (single stream holding the interlock)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| wave-a-feed-repairs | `tests/unit/test_producers_la.py`, `.env.example`, stale-test fix in `tests/unit/test_export_snapshot.py` | config.py, city_registry.py, complaints_311_producer.py, deeds_acris_producer.py | ~14:20 PT | completed — gates green (`pytest -m interlock` 17/17, full suite 230/230) | 3 broken registrations repointed (SF deeds/permits, Chicago deeds), LA MyLA311 `2cy6-i7zn` registered as third feed, producer fallbacks + null-island guard |

**Yield:** 1 of 1. Spine edits applied additively in one serial hold; no torn
write window (interlock gate run immediately after edits, before any commit
point). Uncommitted per local git policy — user commits.

**Yield:** 5 of 5 leaf streams (all durable artifacts written). Commit
deviation amended: `git commit` is denied by local permission policy, so the
orchestrator could not serially commit stream artifacts as planned above —
all ten files are left uncommitted in the working tree for the user to commit.
No spine files were touched at any point.
