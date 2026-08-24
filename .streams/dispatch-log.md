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

## 2026-08-23 — wave B field-mapping refactor (single stream holding the interlock)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| wave-b-field-maps | `src/producers/field_maps.py` (new), `tests/unit/test_field_maps.py` | city_registry.py + all four producers | ~15:10 PT | completed — gates green (`pytest -m interlock` 17/17, full suite 251/251) | Per-city `DatasetSpec.extra["field_map"]` mechanism in all four parsers; LA MyLA311 spellings migrated out of shared chains into the registry entry as proof; 311 `sr_number`⇒chicago sniff tightened (Austin no longer trips it) |

**Yield:** 1 of 1. Refactor stayed additive — chains remain defaults, maps
override per city — so NOLA/Austin implementation (wave C1) is geography
modules plus mapping-table entries with zero parser edits.

## 2026-08-23 — wave C1 city registrations (New Orleans / Norfolk)

Per `docs/expansion-roadmap.md` §3. Pre-dispatch: all six registering datasets
re-probed live (fresh rows confirmed); two scope corrections vs the sweep —
Norfolk permits `fahm-yuh4` DOES carry direct lat/lng (registers), Norfolk 311
`nbyu-xjez` location is an address STRING and licenses `dpi6-sct5` have no
geometry (both DEFERRED until an address-geocoding capability exists; roadmap
C1 target adjusts 8→6 feeds). Projected spine share ~10% (≤20% gate).

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-new-orleans | `src/spatial/cities/new_orleans.py`, `tests/unit/test_producers_new_orleans.py` | config.py, city_registry.py, cities/__init__.py | ~16:00 PT | completed — 9 divisions / 21 submarkets; 4 feeds registered via field maps; 311 watermark corrected to `date_created` (survey wrong) |
| city-norfolk | `src/spatial/cities/norfolk.py`, `tests/unit/test_producers_norfolk.py` | config.py, city_registry.py, cities/__init__.py | ~16:00 PT | completed — 5 divisions / 13 submarkets; PERMITS+DEEDS registered; 311/licenses deferred (no geometry) |

**Yield:** 2 of 2. Spine share ~10% as projected. Gates: interlock 17/17,
city suites 67/67, full suite **318/318**. One interlock-review correction:
Norfolk job_type map order flipped to `["work_type", "type"]` — bare "Building"
classified OT and buried the NB/A2 signal. Obsolete xfail-until-spine markers
stripped from both test files once the maps landed (now hard assertions).
README coverage table + selector copy updated by integrator (dashboard
`src/serving/dashboard.py` + workers static copy still pending for the two new
cities — same shared-file hold pattern as the 2026-08-23 dashboard dispatch).

## 2026-08-23 — wave C2 city registrations (Detroit / Austin)

Per `docs/expansion-roadmap.md` §3. Austin pair re-probed live pre-dispatch
(fresh rows confirmed); Detroit's four ArcGIS FeatureServers re-probe inside the
stream claims. Projected spine share ~10% (≤20% gate).

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-detroit | `src/spatial/cities/detroit.py`, `tests/unit/test_producers_detroit.py` | config.py, city_registry.py, cities/__init__.py | ~16:40 PT | completed — 6 divisions / 16 submarkets; 4 ArcGIS feeds (licenses IS geocoded — research verdict corrected); ObjectId camelCase extras; typo-year sales sentinel documented |
| city-austin | `src/spatial/cities/austin.py`, `tests/unit/test_producers_austin.py` | config.py, city_registry.py, cities/__init__.py | ~16:40 PT | completed — 6 divisions / 16 submarkets; PERMITS+311 partial registration w/ TABC/FedRAMP-shell comment |

**Yield:** 2 of 2. Spine share ~10% as projected. Gates: interlock 17/17,
city suites + field-maps 93/93, full suite **390/390**. Two interlock-phase
findings: (1) the completeness gate correctly rejected the first spine
application — Detroit's arcgis-platform specs exposed that only the deeds
producer exposed an arcgis client; permits/311/SLA producers gained
`_client_for` platform routing (mirroring deeds) and their run_streams now
route by spec.platform. (2) Wave-B gap: 311 status/incident_address chains
lacked first_mapped wiring — completed for Austin's sr_status_desc/sr_location.
README coverage table + selector copy updated by integrator. 

## 2026-08-23 — wave F foundations (spine hold + two client leaves) — Linear HAR-16/17/18

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| wave-f-foundations | `tests/unit/test_scheduler.py` additions | scheduler.py (D1 dict dispatch, D3 metadata resolution), city_registry.py (`resolve_endpoint`) | ~23:30 PT | completed — interlock 17/17, scheduler 16/16 | D1 readable-failure routing; D3 `endpoint_by_year`; D4 snapshot mode |
| carto-client | `src/producers/carto_client.py` + tests | none | ~23:35 PT | completed — 27 unit + live contract green | keyset paging, NULL+sentinel exclusion (rtt_summary NULL dates found live) |
| ckan-client | `src/producers/ckan_client.py` + tests | none | ~23:35 PT | completed — 15 unit + 2 live green | offset paging; range clauses must route to datastore_search_sql; year-rollover hook |

**Yield:** 3 of 3. Gates: full suite **440 passed / 3 skipped / exit 0**.
C3/C5 note recorded on tickets: producers gain `.carto`/`.ckan` attributes at
their city registrations, not before.

## 2026-08-23 — wave C3 city registrations (Philadelphia / Washington DC) — Linear HAR-19/20

Per roadmap §3. Pre-dispatch probes: Philly CARTO SQL API live (nulls-first
DESC reconfirmed on permits), DC DCRA FeatureServer/18 live (ISSUE_DATE,
OBJECTID). Projected spine share ~12% (≤20% gate): enum/aliases/registry/
config + `.carto` producer attributes (first carto wiring) + DC year-slice map.

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-philadelphia | `src/spatial/cities/philadelphia.py`, `tests/unit/test_producers_philadelphia.py` | config.py, city_registry.py, cities/__init__.py, 4 producers (.carto attr) | ~23:50 PT | completed — 8 divisions / 18 submarkets; 4 CARTO feeds; WKB geometry projected client-side via select extras; rtt NULL/sentinel date caveats documented |
| city-dc | `src/spatial/cities/washington_dc.py`, `tests/unit/test_producers_dc.py` | config.py, city_registry.py, cities/__init__.py | ~23:50 PT | completed — 8 divisions / 18 submarkets; 4 ArcGIS feeds incl. full endpoint_by_year maps (2022–2026); non-spatial SLA/DEEDS via null-coord tolerance |

**Yield:** 2 of 2. Gates: interlock **20/20** (incl. new TestDashboardWiring),
city suites 75/75, full suite **518 passed / 3 skipped / exit 0**. Spine-phase
findings: (1) producers' own `_client_for` still hardcoded arcgis/socrata —
converted to the same dict dispatch as the scheduler (Philly's wiring test
caught it); (2) `SLALicenseEvent` lat/lng made Optional + SLA parser tolerates
missing coordinates (deeds precedent) unlocking DC's non-spatial licenses;
(3) scheduler forwards order_by/id_col/select extras to clients; (4) gate
endpoint check now platform-scheme aware (carto://ckan://); (5) workers/ moved
to apps/product upstream of this wave — static-copy invariant repointed and
re-synced with all eleven cities. Dashboard map wired for both cities in the
same spine hold per the AGENTS.md city registration rule.

**Yield:** 5 of 5 leaf streams (all durable artifacts written). Commit
deviation amended: `git commit` is denied by local permission policy, so the
orchestrator could not serially commit stream artifacts as planned above —
all ten files are left uncommitted in the working tree for the user to commit.
No spine files were touched at any point.

## 2026-08-23 — city registration (Cincinnati) — Linear HAR-21

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-cincinnati | `src/spatial/cities/cincinnati.py`, `tests/unit/test_producers_cincinnati.py` | config.py, city_registry.py, cities/__init__.py, dashboard.py, README.md | ~00:xx PT | in progress | Cincinnati geometry, three-feed Socrata contract, and dashboard wiring |

## 2026-08-24 — city registration (Baton Rouge) — Linear HAR-22

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-baton-rouge | `src/spatial/cities/baton_rouge.py`, `tests/unit/test_producers_baton_rouge.py` | config.py, city_registry.py, cities/__init__.py, dashboard.py, snapshot_builder.py, README.md | ~00:xx PT | completed — 31 focused tests, interlock green, build/typecheck green | Baton Rouge geometry, three-feed Socrata contract, and snapshot-mode wiring |

## 2026-08-24 — city registration (Denver) — Linear HAR-24

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-denver | `src/spatial/cities/denver.py`, `tests/unit/test_producers_denver.py` | config.py, city_registry.py, cities/__init__.py, dashboard.py, snapshot_builder.py, README.md | ~00:xx PT | completed — 29 focused tests, interlock green, build/typecheck green | Denver geometry, two-feed ArcGIS contract, and exclusion wiring |

## 2026-08-24 — city registration verification (Baltimore) — Linear HAR-25

| Stream id | Existing implementation | Verification scope | Outcome |
|---|---|---|---|
| city-baltimore | `src/spatial/cities/baltimore.py`, `tests/unit/test_producers_baltimore.py` plus already-wired spine | Baltimore tests, export/interlock/dashboard checks | verification complete — 31 tests passed; implementation remains owned by another agent |

## 2026-08-24 — Python core migration — Linear HAR-41

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| migration-apps-api | `apps/api/**` plus Python execution surfaces | all relocated Python core paths; no concurrent stream authorized | ~02:00 PT | completed — GATES-HAR-41 6/6 green; Linear HAR-41 Done | package/test relocation and execution-surface updates |
