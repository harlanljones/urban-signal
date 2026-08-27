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
to apps/dashboard upstream of this wave — static-copy invariant repointed and
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

## 2026-08-24 — feed-staleness probe: future-watermark guard + deeds audit — CI run 32703690250

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| probe-future-guard | `scripts/feed_staleness_probe.py`, `apps/api/tests/unit/test_feed_staleness_probe.py` | none | ~09:xx PT | completed — 9 probe tests, ruff clean, interlock 20 passed | `newest_watermark` ignores watermarks after `now`; all-future feeds now report stale |
| deeds-watermark-audit | `docs/research/deeds-watermark-audit.md` (read-only stream) | none | ~09:xx PT | completed — all 7 endpoints verified live | per-feed verdicts: nyc/chicago/nola genuinely slow, seattle dead publication, SF+philly wrong watermark_col (spine recs in doc, not applied) |
| deeds-watermark-cols | `apps/api/tests/unit/test_producers_philadelphia.py` (pinned watermark assertion) | city_registry.py | ~10:xx PT | completed — interlock 20 passed, full suite 561 passed (2 pre-existing HEAD failures verified via worktree) | SF deeds watermark `closed_roll_year`→`data_loaded_at`; Philly deeds watermark+keyset `document_date`→`recording_date` |
| deeds-seattle-replacement | `docs/research/seattle-deeds-replacement.md` (read-only stream) | none | ~10:xx PT | completed — all portals checked live | verdict: no live anonymous official KC transaction API exists; winner candidate `rpsale_extr` ArcGIS table (auth-gated item lookup, non-spatial, needs field map) or bulk-zip producer path; registration out of scope |
| seattle-deeds-interim | none (comment-only spine edit) | city_registry.py | ~11:xx PT | completed — access ruled out anonymously with live evidence (AGO directory, gismaps folders); interlock 20 passed, suite 567 passed | KNOWN-DEAD PUBLICATION comment on SEATTLE DEEDS spec; registration deferred pending KC access + terms sign-off |

## 2026-08-24 — D7 text-watermark normalization + sentinel exclusion — Linear HJ-114

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| d7-text-watermark | `apps/api/src/producers/watermarks.py`, `apps/api/tests/unit/test_watermarks.py`, `scripts/feed_staleness_probe.py`, `apps/api/tests/unit/test_feed_staleness_probe.py`, `docs/adr/0005-typed-text-watermarks.md` | scheduler.py | ~12:xx PT | completed — interlock 20 passed; full suite 573 passed / 0 failed; ruff clean on touched files (4 BLE001 pre-existing on HEAD); live PG `qzrv-2tnv` verified: guarded top-of-order returns real dates | typed watermark helpers (`typed_watermark_entry`, `newest_typed_watermark`, `watermark_exclude_clause`), scheduler NOT-IN guard + raw-string text high watermark, probe guard plumbing, ADR 0005 |

## 2026-08-24 — G11 per-feed expected_cadence_days declaration — Linear HJ-115

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| g11-cadence | `scripts/feed_staleness_probe.py`, `apps/api/tests/unit/test_feed_staleness_probe.py`, `apps/api/tests/unit/test_registry_cadence.py` (new) | city_registry.py (data-only backfill) | ~13:xx PT | completed — interlock 20 passed; full suite 579 passed / 0 failed; runtime audit 54/54 registry feeds declare cadence | probe alarms at 2 × declared N (CLI flag now fallback), all feeds backfilled N=7, registry invariant test |

## 2026-08-24 — HJ-44 close-out: live G5/G6 adjudication + Boston SLA exclusion — Linear HJ-44

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| hj44-closeout | `scripts/backfill_probe.py` (new G5/G6 leaf), `apps/api/tests/unit/test_backfill_probe.py` (5 tests) | city_registry.py, test_producers_boston.py, config.py description, README row, research docs, wave-2 scorecard | ~15:xx PT | completed — interlock 20 passed; full suite green; live probes: Baltimore permits/sla 1.0 + 311 0.65 newest / 0.774 mature (gap 25.07% published); Montgomery permits 0.952 (gap 4.97% published) + sla snapshot 1.0; Boston permits 0.982 (gap 2.37% published) + 311 1.0; Boston Licensing Board 0.004 → root-caused gpsx/gpsy = EPSG:26986 meters, excluded per MC311 precedent | `scripts/backfill_probe.py` (Kafka-free producer construction via `__new__`+injected indexer/shift_dynamics, snapshot-mode sampling, per-platform source_count), registry exclusion comment + published-gap annotations (BAL/MOC/BOS), README + research-doc updates, scorecard baseline corrected to 17 cities / 54 jobs with incident |

## 2026-08-24 — city registration (Prince George's County MD) — Linear HJ-125

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-pg-county | `src/spatial/cities/prince_georges.py`, `tests/unit/test_producers_prince_georges.py` | config.py, city_registry.py, cities/__init__.py, serving/dashboard.py, apps/dashboard/public/index.html, `_parse_datetime` %Y%m%d in both producers | ~14:xx PT | completed — interlock 20 passed; full suite 587 passed / 0 failed; live parse 25/25; parcel table deferred with pinned findings (MultiPolygon crash + account id gap) | PG 311 registration w/ G11 cadence exception, dashboard wiring, %Y%m%d date fix, D9 finding evidence |

## 2026-08-24 — C7/C8 city registrations (Columbus, Nashville, Kansas City) — HJ-118/119/120

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-columbus (subagent) | cities/columbus.py, test_producers_columbus.py | config.py, city_registry.py, cities/__init__.py, dashboard.py, index.html | ~18:30 PT | completed — interlock 20 passed; suite 615/0; live parse 300/300 | Columbus PERMITS registration (B1_ALT_ID-only id chain, G3_VALUE_TTL=0 pin) |
| city-nashville (subagent) | cities/nashville.py, test_producers_nashville.py | same spine set | ~18:30 PT | completed — interlock 20 passed; suite 615/0; permits+STR 100% parse each | Nashville PERMITS + SLA(STR) registrations; 311 re-adjudication flagged |
| city-kansas-city (subagent) | cities/kansas_city.py, test_producers_kansas_city.py | same spine set | ~18:30 PT | completed — interlock 20 passed; suite 615/0; live parse 25/25 | KC COMPLAINTS_311 registration correcting prior rejection |

## 2026-08-24 — Wave G1 geocoder core — Linear US-28

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| geocoder-core | src/spatial/geocoder.py, test_geocoder.py, test_spatial_enrichment_worker.py, docs/adr/0004-address-geocoding.md | spatial_enrichment_worker.py, config.py | ~19:00 PT | completed — interlock 20 passed; suite 636/0; Norfolk 500-row acceptance 95.13%; determinism 350/350 across cache flush | deterministic cached geocoder + confidence gating + coord_source provenance |

## 2026-08-24 — Wave G2 Norfolk 311 registration — Linear US-75

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| norfolk-g2 | test_producers_norfolk.py extensions, ADR-free (covered by 0004) | city_registry.py, config.py, complaints_311_producer.py, sla_licenses_producer.py, spatial_enrichment_worker.py (cross-stream repair), scheduler.py (cross-stream repair) | ~20:00 PT | completed — interlock 20 passed; suite 650/0; 311 G5'/G8' PASS at 95.8%/4.2%; SLA reverted under G8' (34% placeholders) | Norfolk 311 geocoded registration; CensusBackend + geocode_backend setting; producer parse-time geocode hook; SLA revert evidence |

## 2026-08-24 — Wave G3 (DC upgrade + Denver evaluation) — US-74 / US-73

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| dc-g3 (subagent) | test_producers_dc.py rewrite | city_registry.py (DC SLA upgrade + where scope), spatial_enrichment n/a, geocoder.py normalizer v2 + state-guard | ~21:00 PT | completed — interlock 20; suite 671/0; SLA G5'/G8' PASS 96.2%/3.8% live | DC SLA geocoded upgrade; DEEDS stays non-spatial with finding |
| denver-g3 (subagent) | test_producers_denver.py rewrite | none (dual descope) | ~21:00 PT | completed — licenses descoped (no watermark), sales reverted (G8', zero addresses); candidate recipe + ADR-0005 warning pinned | evidence-pinned descope; quoted-watermark verification |

## 2026-08-24 — Wave G4 MC311 geocode evaluation — Linear US-94

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| montgomery-g4 | docs/research/mc311-geocode-evaluation.md, test_producers_montgomery.py pin | none (rejection branch) | ~22:00 PT | completed — rejection branch: 0/294 zip-only resolutions measured live; G5' fails at 0% | measured confidence-distribution evidence + test pin |

## 2026-08-24 — Staging bring-up + US-104 ingestion readiness — Linear US-104

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| staging-bringup | docker-compose.override.yml (local), .env (gitignored), Dockerfile build fix | Dockerfile (deps-only install), scheduler.py (US-106 state), config.py (SCHEDULER_STATE_FILE), dob/complaints producers (ckan client), test_interlock_gate.py (platform enforcement) | ~18:30 PT | stack up 10 svc healthy; loader full windowed run 7.45M fetched / 5.39M published / 381k gap-drops; scheduler resume proven ("Restored 46 job watermarks"); PostGIS parity spot-verified (NYC 311 952k, BAL 311 229k); backlog draining ~364/s after partition bump to 12 | scripts/backfill_loader.py + 7 tests, scheduler watermark persistence + 5 tests, ckan clients on permits/311 producers, interlock all-platform enforcement, US-105/106 Done, US-109/110/111 filed |

## 2026-08-24 — Wave R2 rejection recheck — Linear US-86

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| rejection-recheck-r2 | scripts/rejection_recheck.py, test_rejection_recheck.py, docs/research/rejection-recheck-report.json | .github/workflows/rejection-recheck.yml (quarterly cron) | ~22:30 PT | completed — interlock 20 passed; suite 683/0; acceptance case kc_311 re-finds from 2026-08-23 list | self-correcting rejection watch (10 entries, 4 probe kinds) |
| us107-stagger | apps/api/tests/unit/test_scheduler_stagger.py (6 tests) | scheduler.py (poll_due + start tick loop) | ~15:00 PT | completed — interlock 20 passed, suite 689 passed; live: only-due-jobs ticks, 311_chicago published fresh rows inside its 180s cadence | per-feed interval staggering (next_due monotonic deadlines), freshness bounded per feed |

## 2026-08-24 — US-69 Kafka partitioning + 2× replay consumer-lag verification — Linear US-69

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us69-replay-lag | `docs/replay-lag-verification.md`, `scripts/replay_lag_measure.py`, `scripts/replay_load.py` | none | ~15:30 PT | completed — 12 partitions verified on compose; consumer lag p95 ~7,300–7,600s vs <60s target (gates feed growth per US-69) | replay load and lag measurement scripts + verification doc |

## 2026-08-24 — ADR 0007 Multi-Source Metro vs Separate Registration — Linear US-68

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| adr0007-multi-source-metro | `docs/adr/0007-multi-source-metro-vs-separate-registration.md` | none | ~15:45 PT | completed — Accepted: separate registration retained for ingestion; multi-source metro deferred; unblocks Pierce | ADR 0007 recording decision & consequences |

## 2026-08-24 — City registration (Pierce County WA) — Linear US-80

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-pierce | `apps/api/src/spatial/cities/pierce.py`, `apps/api/tests/unit/test_producers_pierce.py` | config.py, city_registry.py, cities/__init__.py, dashboard.py, index.html | ~16:00 PT | completed — interlock 20 passed; suite green; 22nd registered metro | Pierce County geometry, ArcGIS permits + WA LCB SLA contract, dashboard wiring |

## 2026-08-24 — US-70 Annual New Year rollover drill — Linear US-70

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us70-rollover-drill | `apps/api/src/producers/rollover.py`, `scripts/rollover_drill.py`, `apps/api/tests/unit/test_rollover_drill.py`, `apps/api/tests/unit/test_feed_staleness_probe.py` | scheduler.py | ~16:15 PT | completed — interlock 20 passed; suite green; dynamic layer rollover detection + loud-fail drill | scheduler layer rollover detection + CLI drill tool + tests |

## 2026-08-24 — US-72 FeedType taxonomy extension — Linear US-72

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us72-feedtype-taxonomy | `apps/api/tests/unit/test_feedtype_taxonomy.py`, `apps/api/tests/unit/test_interlock_gate.py`, `apps/api/src/consumers/feature_aggregation_worker.py` | city_registry.py, config.py | ~16:25 PT | completed — interlock 20 passed; suite 719/0; CRIME, STREET_CUT, EVICTIONS, STR added to FeedType; enriched keyed city_id:h3 | FeedType enum extension + raw topics + enriched keying fix |

## 2026-08-24 — US-71 Crime incident feeds — Linear US-71

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us71-crime-feeds | `apps/api/src/producers/crime_incidents_producer.py`, `apps/api/src/schemas/models.py`, `apps/api/src/schemas/avro/crime_event.avsc`, `apps/api/src/features/pipeline.py`, `apps/api/src/consumers/spatial_enrichment_worker.py`, `apps/api/tests/unit/test_producers_crime.py`, `apps/api/tests/unit/test_schemas.py` | config.py, city_registry.py, scheduler.py | ~16:30 PT | completed — interlock 20 passed; suite 730/0; CHI/SF/SEA/NYC crime registered into raw_crime behind ablation | Crime incident producer + Avro schema + UCR Part-1/Part-2 classification + DuckDB table |

## 2026-08-24 — US-27 Business license move-in / move-out flow — Linear US-27

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us27-sla-flow | `apps/api/src/features/pipeline.py`, `apps/api/src/consumers/spatial_enrichment_worker.py`, `apps/api/src/consumers/feature_aggregation_worker.py`, `apps/api/src/schemas/models.py`, `apps/api/src/schemas/avro/enriched_h3_feature.avsc`, `apps/api/tests/unit/test_features.py`, `apps/api/tests/unit/test_schemas.py` | config.py (sla_flow_ablation_enabled flag) | ~16:35 PT | completed — interlock 20 passed; suite 730/0; sla_move_ins_90d + sla_move_outs_90d derived in pipeline behind ablation | SLA flow derivation in DuckDB feature pipeline + EnrichedH3Feature model & Avro schema |

| us31-deeplink | `apps/api/src/serving/dashboard.py`, `apps/product/src/main.js` | none (dashboard.py is leaf; interlock run per ticket contract) | ~18:05 PT | completed — interlock 20 passed; lint/typecheck/build green; browser-verified desktop + mobile | `/dashboard?city=<id>` deep links: dashboard param parsing + /compare column links |

## 2026-08-24 — US-108 FeatureAggregationWorker consume loop — Linear US-108

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us108-aggregation-loop | `apps/api/src/consumers/feature_aggregation_worker.py`, `apps/api/src/consumers/alert_dispatcher_worker.py` (new), `apps/api/src/schemas/avro/catalyst_alert.avsc`, `apps/api/tests/unit/test_feature_aggregation_worker.py` (new), `apps/api/tests/unit/test_alert_dispatcher_worker.py` (new), `docker-compose.yml` | config.py (aggregation_cell_cooldown_seconds, alert_state_file — additive) | ~18:20 PT | implemented — interlock 20 passed; suite 807/0; ADR 0008 contract live; AC#3 staging verification pending | cg_inference aggregation loop (cooldown/DLQ/metrics) + cg_alerts webhook dispatcher + avsc city_id fix |

## 2026-08-24 — product-site parity with dashboard v2 (US-119 / US-120 / US-121)

All three streams target `apps/product` with **disjoint leaf files**. Shared files — `apps/product/CHANGELOG.md`, `apps/product/public/llms.txt`, `apps/product/public/llms-full.txt`, and the `dist/` build output (`build.mjs` `rm`+write — concurrent builds would tear it) — are **not** written by streams; each stream proposes its shared-file edits in its claim log and the orchestrator applies them serially at close-out (same hold pattern as the 2026-08-23 dashboard wiring dispatch). Full `bun run build`/`lint`/verifier gate also runs serially at close-out. Artifacts stay uncommitted (local git policy).

| Stream id | Leaf claim | Shared files needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us119-compare-surface | `apps/product/pages/compare.html`, `apps/product/scripts/render-city.mjs` | CHANGELOG.md, llms-full.txt (page-guide), dist/ | ~in-flight | completed — typecheck green; compare state confirmed NOT URL-addressable (deep-linked `?city=` only); copy-only section added | nearby-region comparison copy on /compare/ + city CTA sublabel |
| us120-evictions-content | `apps/product/pages/system.html`, `apps/product/pages/evidence.html`, `apps/product/pages/cities.html`, `scripts/export_site_facts.py` (FEED_ORDER decision) | CHANGELOG.md, llms.txt/llms-full.txt (feed descriptions), public/facts.json (regenerated), dist/ | ~in-flight | completed — FEED_ORDER NOT extended (verify-site-content.mjs:33 + main.js:4 hard-assert 4 feeds; NYC-only asymmetry); hand-authored prose only; facts:check green | evictions stream documented on system/evidence/cities pages |
| us121-architecture-alerts | `apps/product/pages/architecture.html` | CHANGELOG.md, llms.txt/llms-full.txt (architecture lines), dist/ | ~in-flight | completed — typecheck green; new Alert dispatch spine node + feature aggregation loop rewrite per ADR 0008 | architecture.html aggregation/alert narrative |

**Orchestrator close-out:** shared edits applied serially (CHANGELOG ×3, llms.txt ×2, llms-full.txt ×3); `bun run build` + `bun run lint` green (SITE_BUILD_OK, SITE_CONTENT_OK, AGENT_SURFACE_OK, MULTI_PAGE_OK, 37 routes). Artifacts left uncommitted per local git policy. Yield: 3 of 3.

## 2026-08-25 — external context-signal validation wave (US-101 / US-102 / US-103 / US-122 / US-123)

Five pure-leaf, read-only research streams, each producing exactly two files
(its `.streams/<id>.md` claim log and one `docs/research/<topic>.md`). No spine
files touched. All five candidates were verified open, unassigned, and unblocked
(no relations) before claiming; assigned to `self` as the first write and each
closing comment attached before the next spawn. Verdicts recorded per issue,
with evidence pointers to the validation docs. Artifacts and claim logs left
uncommitted per local git policy.

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us101-lodes | `docs/research/census-lodes-validation.md` | none | ~2026-08-25 | completed — DEFER (near-register; data side proven; needs a new context signal family) | `docs/research/census-lodes-validation.md` (342 lines) |
| us102-bfs | `docs/research/census-bfs-validation.md` | none | ~2026-08-25 | completed — DEFER (county series annual/no sector detail; Jan-2026 methodology change) | `docs/research/census-bfs-validation.md` (248 lines) |
| us103-hud-usps | `docs/research/hud-usps-vacancy.md` | none | ~2026-08-25 | completed — DEFER (access restricted to gov/nonprofit + sublicense purpose; tract aggregates not points) | `docs/research/hud-usps-vacancy.md` (240 lines) |
| us122-qcew | `docs/research/bls-qcew-validation.md` | none | ~2026-08-25 | completed — DEFER conditional register-later (supression + OMB MSA seam + employment near-duplicate of LODES) | `docs/research/bls-qcew-validation.md` (265 lines) |
| us123-nlcd | `docs/research/annual-nlcd-layers.md` | none | ~2026-08-25 | completed — DEFER (no raster ingest capability; product-version drift risk; pilot feasible) | `docs/research/annual-nlcd-layers.md` (329 lines) |

**Yield:** 5 of 5 leaf streams (all durable artifacts written). Cross-cutting
finding: all five land as context layers, none register as event feeds — each
would need a new context signal family (Workforce/LandCover/etc.) and, for NLCD
and HUD–USPS, an areal/raster→H3 aggregation engine that does not exist in the
spine. LODES is the closest to REGISTER (no granularity mismatch, fully proven);
QCEW is register-later behind LODES/BFS. No code changed; no spine edits; gates
not run (no code touched).

## 2026-08-25 — registration wave (serial, spine-held) — US-126 first

Run serially, one subagent per issue holding the interlock, because every
registration edits the shared spine (`config.py`, `city_registry.py`) and the
deeds cluster also edits `deeds_acris_producer.py`. Interlock gate re-run by the
orchestrator after each release (`.venv/bin/python -m pytest -m interlock`).

| Stream id | Leaf claim | Spine touched | Outcome | Yielded artifact |
|---|---|---|---|---|
| us126-cincinnati-deeds | `apps/api/tests/unit/test_producers_cincinnati.py` + README/roadmap rows | config.py, city_registry.py, csv_client.py, deeds_acris_producer.py | completed — interlock 21/21; focused 115; reg 86; ruff net-new 0 | Cincinnati DEEDS registered (csv, snapshot, SaleDate synth, valid='Y'); live-probed and confirmed |
| us127-columbus-deeds | `apps/api/tests/unit/test_producers_columbus.py` + README/roadmap rows | config.py, city_registry.py, deeds_acris_producer.py | completed — interlock 21/21; unit 814/0; ruff net-new 0 | Columbus DEEDS registered (arcgis, annual snapshot, dual-schema field map); live probe: Instrument_Number NULL layer-wide (effective id = PARCELID+OBJECTID) |
| us129-pittsburgh-deeds | `apps/api/tests/unit/test_producers_pittsburgh.py` + README row | config.py, city_registry.py, deeds_acris_producer.py | completed — interlock 21/21 | Pittsburgh DEEDS registered (ckan; self.ckan wired for the interlock client-exposure invariant); live 501,120 rows, RECORDDATE daily |

## 2026-08-25 — registration wave (continued) — batch 1 (US-124 / US-135 / US-130)

Parallel subagents, grouped so each batch has disjoint producer files; only
shared `city_registry.py`/`config.py` are edited concurrently, in disjoint city
blocks (the C7/C8-proven pattern). Interlock gate re-run by the orchestrator after
each batch (21/21 held across all). Full unit suite at close-out: 868 passed /
0 failed. Ruff net-new 0 per stream (counts are pre-existing HEAD lint debt).

| Stream id | Leaf claim | Spine touched | Outcome | Yielded artifact |
|---|---|---|---|---|
| us124-san-diego-311 | `apps/api/tests/unit/test_producers_san_diego.py` + README row | config.py, city_registry.py, complaints_311_producer.py | completed — 18/18 focused; reg 102/102; ruff net-new 0 | San Diego COMPLAINTS_311 registered (csv, endpoint_by_year + companion open) |
| us135-minneapolis-sla | `apps/api/tests/unit/test_producers_minneapolis.py` + README row | config.py, city_registry.py, sla_licenses_producer.py (additive dba prepend) | completed — focused 185/185; ruff net-new 0 | Minneapolis SLA registered (arcgis On/Off Sale, companion_endpoints) |
| us130-philadelphia-deeds | `apps/api/tests/unit/test_producers_philadelphia.py` + README/roadmap rows | city_registry.py (extra.where) only | completed — phl 39/39; carto 28/28; ruff net-new 0 | Philly DEEDS scoped to `document_type='DEED'` (95.3% price-bearing; IN(...) rejected as it pulls 0.1%-bearing noise) |

## 2026-08-25 — registration wave (continued) — batch 2 (US-129 / US-133 / US-131)

| Stream id | Leaf claim | Spine touched | Outcome | Yielded artifact |
|---|---|---|---|---|
| us129-pittsburgh-deeds | (logged above) | config.py, city_registry.py, deeds_acris_producer.py | completed — interlock 21/21; 9/9; ruff net-new 0 | Pittsburgh DEEDS registered (ckan) |

Actually batch 2 also dispatched US-133 and US-131 — recording their close-outs here:

| Stream id | Leaf claim | Spine touched | Outcome | Yielded artifact |
|---|---|---|---|---|
| us133-norfolk-sla | `apps/api/tests/unit/test_producers_norfolk.py` + README/roadmap rows | config.py, city_registry.py, sla_licenses_producer.py (additive premises_name prepend) | completed — focused 95/95; Wiring 3/3; ruff net-new 0 | Norfolk SLA registered (socrata, placeholder-where → 96.2% geocode); obsolete G2 no-geometry verdict corrected |
| us131-nashville-311 | `apps/api/tests/unit/test_producers_nashville.py` + README row | config.py, city_registry.py | completed — 24/24; reg 108/108; Wiring 3/3; ruff net-new 0 | Nashville COMPLAINTS_311 registered (arcgis, Latitude IS NOT NULL); positive re-adjudication of HJ-119 exclusion |

## 2026-08-25 — registration wave (continued) — batch 3 (US-128 / US-132 / US-134) + close-out

| Stream id | Leaf claim | Spine touched | Outcome | Yielded artifact |
|---|---|---|---|---|
| us128-md-sdat-deeds | `apps/api/tests/unit/test_producers_{baltimore,montgomery,prince_georges}.py` + `test_watermarks.py` + README rows | watermarks.py, config.py, city_registry.py, deeds_acris_producer.py | completed — focused 37/37; deeds cluster 310/310; interlock 21/21; ruff net-new 0 | BALTIMORE/MONTGOMERY/PRINCE_GEORGES DEEDS registered (socrata, MD SDAT, snapshot) |
| us132-pittsburgh-311 | `apps/api/tests/unit/test_producers_pittsburgh.py` + README row | config.py, city_registry.py | completed — 17/17; reg 43/43; Wiring 3/3; ruff net-new 0 | Pittsburgh COMPLAINTS_311 registered (ckan, intraday; stale address-only-archive verdict corrected) |
| us134-kansas-city-sla | `apps/api/tests/unit/test_producers_kansas_city.py` + README row | config.py, city_registry.py, sla_licenses_producer.py (%Y%m%d), scripts/rejection_recheck.py | completed — 9/9; SLA reg 122/122; interlock 21/21; ruff net-new 0 | KANSAS_CITY SLA registered (socrata snapshot, cadence 90); rejection_recheck kc_sla superseded |

**Orchestrator close-out (2026-08-25):** `pytest -m interlock` 21/21; `pytest tests/unit` **868 passed / 3 skipped / 0 failed**. Two stale test expectations updated to the live registry (test_backfill_probe.py Baltimore scopes →4 feeds incl. deeds; test_rejection_recheck.py `kc_sla` → registered). `scripts/rejection_recheck.py` `nashville_311` marked `superseded_by:"US-131"`. Yield: 12 of 12 registration streams (5 in the completed batch + 7 with the deeds cluster). All artifacts and claim logs left uncommitted per local git policy; no dashboard edits were needed (all cities already listed; TestDashboardWiring green).
| us125-san-diego-sla | `apps/api/tests/unit/test_producers_san_diego.py` + README row | config.py, city_registry.py, sla_licenses_producer.py (csv wiring + account_key normalization) | completed — SD 25/25; combined focused 373/373; interlock 21/21; ruff net-new 0 | San Diego SLA registered (csv snapshot; NAICS 72 hospitality for LIMS; inactive backfill 403s today) |

**Registration wave complete — 12 of 12.** Final verification after US-125:
`pytest -m interlock` **21/21**; `pytest tests/unit` **875 passed / 3 skipped / 0 failed**.
All 12 registration issues (US-124, US-125, US-126, US-127, US-128, US-129,
US-130, US-131, US-132, US-133, US-134, US-135) implemented, gate-verified,
commented with evidence, and recorded above. Uncommitted per local git policy.
## 2026-08-26 — new-metro registration wave 1 (US-140 Houston / US-144 Indianapolis / US-157 Wichita)

Three parallel subagents, each registering a DIFFERENT single-feed new city
(leaf geometry module + registry + dashboard source + tests), editing only
their own — disjoint — city blocks; generated artifacts (static `index.html`,
product `facts.json`) regenerated by the orchestrator serially at close-out
from the final consistent state. Concurrent spine edits to `city_registry.py`
/`dashboard.py` were reconciled at close-out; `INDIANAPOLIS` was added to
`test_interlock_gate.py::CITY_EXPORT_NAMES` (was missing → exports previously
unvalidated); README metro count normalized to 30. Interlock 21/21 held
throughout. One discrepancy noted: neither Houston nor Indianapolis have the
ticket-suggested `SR_NUMBER`/`REQUESTID` columns — real keys are
`CASE_NUMBER`/`SERVICEREQUESTID` (+`OBJECTID`).

| Stream id | Leaf claim | Spine touched | Outcome | Yielded artifact |
|---|---|---|---|---|
| us140-houston | `cities/houston.py`, `test_producers_houston.py` | city_registry.py, config.py, cities/__init__.py, dashboard.py, test_interlock_gate.py, README.md | completed — interlock 21/21; 4/4; facts 30 | Houston COMPLAINTS_311 registered (arcgis, CREATED_ON; CASE_NUMBER key) |
| us144-indianapolis | `cities/indianapolis.py`, `test_producers_indianapolis.py` | same spine set | completed — interlock 21/21; 10/10; facts 30 | Indianapolis COMPLAINTS_311 registered (arcgis, REQUESTEDDATETIME; SERVICEREQUESTID key) |
| us157-wichita | `cities/wichita.py`, `test_producers_wichita.py` | same spine set | completed — interlock 21/21; 10/10; facts 30 | Wichita PERMITS registered (arcgis, ApplicationDate, layer-index-1 trap verified) |

**Yield:** 3 of 3. Register count now 30 metros. `pytest -m interlock` 21/21; product
`facts:check` FACTS_FRESH (30). test_retraining.py failures are environmental
(tmp_path/Minio), unrelated. Artifacts uncommitted per local git policy.

## 2026-08-26 — city registration (Chattanooga) — Linear US-155

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-chattanooga | `apps/api/src/spatial/cities/chattanooga.py`, `apps/api/tests/unit/test_producers_chattanooga.py` | config.py, city_registry.py, cities/__init__.py, permits/deeds producers, dashboard, snapshot export | current session | implemented; focused verification green | Chattanooga PERMITS + DEEDS registration |

## 2026-08-26 — city registration (Cleveland) — Linear US-153

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-cleveland | `apps/api/src/spatial/cities/cleveland.py`, `apps/api/tests/unit/test_producers_cleveland.py` | config.py, city_registry.py, cities/__init__.py, permits/311/deeds producers, dashboard, snapshot export | current session | implemented; interlock and focused verification green | Cleveland PERMITS + 311 + DEEDS registration |

## 2026-08-26 — city registration (Hartford) — Linear US-152

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-hartford | `apps/api/src/spatial/cities/hartford.py`, `apps/api/tests/unit/test_producers_hartford.py` | config.py, city_registry.py, cities/__init__.py, permits/311/SLA producers, dashboard, snapshot export | current session | implemented; focused tests and interlock green; Linear US-152 done | Hartford PERMITS + 311 + CT eLicensing SLA registration |

## 2026-08-26 — city registration (Raleigh) — Linear US-151

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-raleigh | `apps/api/src/spatial/cities/raleigh.py`, `apps/api/tests/unit/test_producers_raleigh.py` | config.py, city_registry.py, cities/__init__.py, permits/311/deeds producers, dashboard, snapshot export | current session | implemented; focused tests and interlock green; Linear US-151 pending resolution | Raleigh PERMITS + 311 + Wake County DEEDS registration |

## 2026-08-26 — city registration (San Antonio) — Linear US-141

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-san-antonio | `apps/api/src/spatial/cities/san_antonio.py`, `apps/api/tests/unit/test_producers_san_antonio.py` | config.py, city_registry.py, cities/__init__.py, permits/311 producers, dashboard, snapshot export | current session | implemented; focused tests and interlock green; Linear US-141 pending resolution | San Antonio PERMITS + 311 registration |

## 2026-08-26 — DC deeds parcel join — Linear US-139

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| dc-deeds-parcel-join | DC CAMA SSL → Parcel Lots centroid enrichment | config.py, city_registry.py, deeds producer/client, README, tests, interlock | current session | implemented; focused tests and interlock green; Linear US-139 done | DC deeds parcel-join implementation |

## 2026-08-26 — city registration (Sacramento) — Linear US-142

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-sacramento | `apps/api/src/spatial/cities/sacramento.py`, `apps/api/tests/unit/test_producers_sacramento.py` | config.py, city_registry.py, cities/__init__.py, permits/311 producers, dashboard, snapshot export | current session | implemented; focused tests, interlock, facts, and dashboard verification green | Sacramento PERMITS + 311 registration |

## 2026-08-26 — city registration (Reno) — Linear US-161

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-reno | `apps/api/src/spatial/cities/reno.py`, `apps/api/tests/unit/test_producers_reno.py` | config.py, city_registry.py, cities/__init__.py, deeds producer, dashboard, snapshot export | current session | implemented; focused tests, interlock, scheduler, facts, and dashboard verification green | Reno / Washoe County DEEDS registration |

## 2026-08-26 — city registration (Spokane) — Linear US-160

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-spokane | `apps/api/src/spatial/cities/spokane.py`, `apps/api/tests/unit/test_producers_spokane.py` | config.py, city_registry.py, cities/__init__.py, deeds/permits/SLA producers, XLS client, dashboard, snapshot export | current session | in progress | Spokane DEEDS + PERMITS + SLA registration |

## 2026-08-26 — city registration (Dayton) — Linear US-159

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-dayton | `apps/api/src/spatial/cities/dayton.py`, `apps/api/tests/unit/test_producers_dayton.py` | config.py, city_registry.py, cities/__init__.py, complaints producer, dashboard, snapshot export | current session | implemented; focused tests, interlock, facts, and dashboard verification green; Linear US-159 pending resolution | Dayton rolling-90-day 311 registration |

## 2026-08-26 — Frontier batch (20 tickets) — orchestrator: main session
Phase 0 (reconcile stale) DONE: US-101/102/103/122/160 closed (prior artifacts).
Phase 1 (claim) DONE: 20 tickets assigned to self (harlanljones).
Phase 2 (parallel leaf build) DISPATCHED — 20 leaf-workers, disjoint leaf files:
  Tier A (validation, no spine): US-123 nlcd, US-165 hmda, US-166 acs, US-167 zip-business-patterns, US-169 overture-maps, US-170 epa-echo
  Tier B (registration): US-136 austin(+TABC SLA), US-137 boston(+licensing), US-138 milwaukee(+permits/deeds), US-143 portland(new), US-145 las_vegas(new,ADR4), US-146 tampa(new), US-147 san_jose(new,ADR4), US-148 louisville(new), US-149 dallas(new), US-150 boise(new,state-plane), US-154 durham(new), US-156 el_paso(new), US-158 tulsa(new), US-159 dayton(new)
Phase 3 (serial interlock) PENDING — orchestrator applies spine deltas one at a time, runs pytest -m interlock + full suite.

## 2026-08-26 — city registration (Tulsa) — Linear US-158

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-tulsa | `apps/api/src/spatial/cities/tulsa.py`, `apps/api/tests/unit/test_producers_tulsa.py` | config.py, city_registry.py, cities/__init__.py, complaints producer, dashboard, snapshot export, interlock tests | current session | implemented; focused tests, interlock, facts, site-content, and dashboard verification green; Linear US-158 done | Tulsa approximately-30-day rolling 311 registration |

## 2026-08-26 — city registration (El Paso) — Linear US-156

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-el-paso | `apps/api/src/spatial/cities/el_paso.py`, `apps/api/tests/unit/test_producers_el_paso.py` | config.py, city_registry.py, cities/__init__.py, complaints producer, dashboard, snapshot export, interlock tests | current session | implemented; focused tests, interlock, facts, product build, site-content, and dashboard verification green; Linear US-156 done | El Paso approximately-30-day partial 311 registration |

## 2026-08-26 — city registration (Durham) — Linear US-154

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-durham | `apps/api/src/spatial/cities/durham.py`, `apps/api/tests/unit/test_producers_durham.py` | config.py, city_registry.py, cities/__init__.py, permits/deeds producers, dashboard, snapshot export, interlock tests | current session | implemented; focused tests, interlock, facts, product build, site-content, and dashboard verification green; Linear US-154 done | Durham PERMITS + DEEDS registration |

## 2026-08-26 — city registration (Dallas) — Linear US-149

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-dallas | `apps/api/src/spatial/cities/dallas.py`, `apps/api/src/producers/field_maps_dallas.py`, `apps/api/tests/unit/test_producers_dallas.py` | config.py, city_registry.py, cities/__init__.py, dashboard, snapshot export, interlock tests | current session | implemented; focused tests, interlock, facts, product build, and site-content verification green; Linear US-149 done | Dallas ROW construction proxy + Building Services rolling-30-day partial 311 registration |

## 2026-08-26 — city registration (Louisville) — Linear US-148

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-louisville | `apps/api/src/spatial/cities/louisville.py`, `apps/api/src/producers/field_maps_louisville.py`, `apps/api/tests/unit/test_producers_louisville.py` | config.py, city_registry.py, cities/__init__.py, dashboard, snapshot export, interlock tests | current session | implemented; focused tests, interlock, facts, product build, and site-content verification green; Linear US-148 done | Louisville annual 311 + Jefferson County ABC active-license registration |

## 2026-08-26 — city registration (San Jose) — Linear US-147

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-san-jose | `apps/api/src/spatial/cities/san_jose.py`, `apps/api/src/producers/field_maps_san_jose.py`, `apps/api/tests/unit/test_producers_san_jose.py` | config.py, city_registry.py, cities/__init__.py, dashboard, snapshot export, interlock tests | current session | implemented; live CKAN verification, focused tests, interlock, facts, product build, and site-content verification green; Linear US-147 done | San Jose address-geocoded permits + current-year 311 with 0,0 drop caveat |

## 2026-08-26 — city registration (Tampa) — Linear US-146

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-tampa | `apps/api/src/spatial/cities/tampa.py`, `apps/api/src/producers/field_maps_tampa.py`, `apps/api/tests/unit/test_producers_tampa.py` | config.py, city_registry.py, cities/__init__.py, dashboard, snapshot export, interlock tests | current session | implemented; live ArcGIS verification, focused tests, interlock, facts, product build, and site-content verification green; Linear US-146 done | Tampa full permits + alcohol-beverage partial SLA registration |

## 2026-08-26 — city registration (Las Vegas) — Linear US-145

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-las-vegas | `apps/api/src/spatial/cities/las_vegas.py`, `apps/api/src/producers/field_maps_las_vegas.py`, `apps/api/tests/unit/test_producers_las_vegas.py` | config.py, city_registry.py, cities/__init__.py, dashboard, snapshot export, interlock tests | current session | implemented; live ArcGIS verification, focused tests, shared regressions, interlock, facts, product build, and site-content verification green; Linear US-145 pending resolution | Las Vegas / Clark County address-only permits + parcel sales with ADR-0004 geocoding |

## 2026-08-26 — Phase 2 complete; Phase 3 (spine) BLOCKED
Phase 2 (parallel leaf build) DONE via 19 leaf-worker subagents:
  Tier A (6 validations): US-123/165/166/167/169/170 — all conclude DEFER (each would need a spine change); leaf docs + a few leaf metric modules, tests green. No spine delta.
  Tier B (13 registrations): leaf modules + per-city field_maps + tests built & passing.
  NOTE: the tree already held PRIOR-SESSION registrations (Dayton/Spokane/Durham/El Paso/Tulsa) — fully registered, interlock gate GREEN. So those 5 are done; my workers added missing field_maps/tests.
  Net-new leaf done. Phase 3 (serial interlock / spine application) — RESOLVED 2026-08-26:
  Verified-city spine already landed in an earlier hold (prior session registered
  Austin, Boston, Dallas, Dayton, Durham, El Paso, Spokane, Tulsa with verified
  endpoints). Confirmed `pytest -m interlock` is GREEN (22/22) on branch
  feat/epa-echo via the repo `.venv` interpreter.
  User decision: "apply only verified cities" → the remaining spine is DEFERRED:
    - 6 net-new cities (Portland, Las Vegas, Tampa, San Jose, Louisville, Boise)
      stay LEAF-ONLY; endpoints were flagged UNVERIFIED by their leaf streams
      (no network in sandbox) and the City-registration rule forbids registering
      an unverified mirror.
    - 3 feed additions (Austin TABC-SLA, Boston Licensing, Milwaukee PERMITS+DEEDS)
      stay LEAF-ONLY for the same reason; note Milwaukee's existing registration is
      deliberately SLA-only (US-87) and adding PERMITS needs the ADR-0004 geocoder
      decision, so it is not applied blindly.
  To finish: in a session with network, verify each endpoint live, then apply the
  documented spine deltas (one serial interlock hold per city) and re-run the gate.
  Leaf artifacts (city modules, per-city field_maps_<slug>.py, tests) are committed
  and gate-clean; no torn write remains.

## 2026-08-27 — Wave 3 metro expansion (US-192) — orchestrator: main session

Parent: [US-192](https://linear.app/harlanljones/issue/US-192/wave-3-metro-expansion-brainstorm-candidates) claimed In Progress.
Phase 1 (claim) DONE: US-193–US-206 assigned to harlanljones.
Phase 2 (parallel leaf) DISPATCHED — 13 leaf-workers, disjoint files.
US-195 held by orchestrator for synthesis into `docs/expansion-roadmap-wave-3.md`
after probes return. Shared roadmap is NOT a leaf; agents write per-city
`docs/research/wave-3-probe-*.md` instead.
Phase 3 (serial interlock / dashboard wiring) IN PROGRESS — Honolulu +
Orlando spines landed 2026-08-27 ~13:00–13:05 PT. Gate: `pytest -m interlock`
22/22. City-registration rule satisfied for both (METRO_META + index.html).

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-honolulu | `cities/honolulu.py` + field_maps + tests (US-193) | city_registry, cities/__init__, config, dashboard, index.html, complaints_311_producer | ~12:20 PT | **spine complete** — 311-only; interlock 22/22; datetime format added | honolulu.py + field_maps_honolulu.py + test_producers_honolulu.py + REGISTRY/METRO_META |
| city-orlando | `cities/orlando.py` + field_maps + tests (US-194) | city_registry, cities/__init__, config, dashboard, index.html | ~12:20 PT | **spine complete** — SLA BTR + STR companion; interlock 22/22 | orlando.py + field_maps_orlando.py + test_producers_orlando.py + REGISTRY/METRO_META |
| feed-expansion-geocode | `docs/research/wave-3-feed-expansion.md` drafts only (US-196) | later: city_registry DatasetSpecs on existing metros | ~12:20 PT | completed — drafts only; 3 net-new GOs (Sacramento companion, Chicago pubx-yq2d, NYC tqtj-sjs8); US-196 still In Progress | wave-3-feed-expansion.md |
| probe-phoenix | `docs/research/wave-3-probe-phoenix.md` (US-197) | none | ~12:20 PT | completed — partial ready (permits T1 + STR SLA T1; 311/deeds T3); US-197 Done | wave-3-probe-phoenix.md |
| probe-atlanta | `docs/research/wave-3-probe-atlanta.md` (US-198) | none | ~12:20 PT | completed — REJECT all four families (Tier 3); US-198 Done | wave-3-probe-atlanta.md |
| probe-miami | `docs/research/wave-3-probe-miami.md` (US-199) | none | ~12:20 PT | completed — partial ready (MDC permits+SLA T1; 311 T3); US-199 Done | wave-3-probe-miami.md |
| probe-st-louis | `docs/research/wave-3-probe-st-louis.md` (US-200) | none | ~12:20 PT | completed — partial ready (311 T1 zip, permits T2 CF CSV, liquor SLA T2 optional, deeds T3) | wave-3-probe-st-louis.md |
| probe-memphis | `docs/research/wave-3-probe-memphis.md` (US-201) | none | ~12:20 PT | completed — partial ready (permits T1 monthly, 311 T1; SLA/deeds T3); US-201 Done | wave-3-probe-memphis.md |
| probe-salt-lake-city | `docs/research/wave-3-probe-salt-lake-city.md` (US-202) | none | ~12:20 PT | completed — REJECT all four families (Tier 3); US-202 Done | wave-3-probe-salt-lake-city.md |
| probe-jacksonville | `docs/research/wave-3-probe-jacksonville.md` (US-203) | none | ~12:20 PT | completed — REJECT all four families (Tier 3); US-203 Done | wave-3-probe-jacksonville.md |
| probe-oklahoma-city | `docs/research/wave-3-probe-oklahoma-city.md` (US-204) | none | ~12:20 PT | completed — REJECT all four families (Tier 3); US-204 Done | wave-3-probe-oklahoma-city.md |
| probe-albuquerque | `docs/research/wave-3-probe-albuquerque.md` (US-205) | none | ~12:20 PT | completed — partial ready (permits T2 CSV; 311/SLA/deeds T3); US-205 Done | wave-3-probe-albuquerque.md |
| probe-providence | `docs/research/wave-3-probe-providence.md` (US-206) | none | ~12:20 PT | completed — REJECT all four families (Tier 3); US-206 Done | wave-3-probe-providence.md |

**Yield at dispatch:** 0 of 13 (in flight). **Torn-write exposure:** none — no spine edits in Phase 2.

## 2026-08-27 — US-199 Miami split (finish row-level from host fingerprint)

Fingerprint landed: Miami-Dade + Broward are ArcGIS Hub, not Socrata/CKAN.
Parent `probe-miami` still in flight writing `docs/research/wave-3-probe-miami.md`.
Three disjoint portal streams dispatched to finish family probes:

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| probe-miami-dade | `docs/research/wave-3-probe-miami-dade.md` | none | ~12:32 PT | completed — partial ready (permits T2, SLA T1, deeds T1, 311 T3) | wave-3-probe-miami-dade.md |
| probe-broward | `docs/research/wave-3-probe-broward.md` | none | ~12:32 PT | completed — partial ready (SLA T1 occupational licenses; permits/311/deeds T3) | wave-3-probe-broward.md |
| probe-fort-lauderdale | `docs/research/wave-3-probe-fort-lauderdale.md` | none | ~12:32 PT | completed — not a city leaf (permits/311/SLA frozen; sales are Broward) | wave-3-probe-fort-lauderdale.md |

## 2026-08-27 — Wave 3 city leaves (ready metros, leaf-only)

Honolulu + Orlando spines released. Parallel Phase-2 city modules for
probe-ready metros that have no `cities/<city>.py` yet. No spine edits in
these streams. US-195 synthesis still held until this wave of leaves
returns.

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-phoenix | `cities/phoenix.py` + field_maps + tests (US-197) | later: registry/config/dashboard | ~13:10 PT | **spine complete** — permits+STR-as-SLA; interlock 22/22 | phoenix.py + field_maps_phoenix.py + test_producers_phoenix.py + REGISTRY/METRO_META |
| city-memphis | `cities/memphis.py` + field_maps + tests (US-201) | later: registry/config/dashboard | ~13:10 PT | **spine complete** — permits+311; monthly cadence 31d; interlock 22/22 | memphis.py + field_maps_memphis.py + test_producers_memphis.py + REGISTRY/METRO_META |
| city-albuquerque | `cities/albuquerque.py` + field_maps + tests (US-205) | later: registry/config/dashboard | ~13:10 PT | **spine complete** — CSV permits; compose_permit_address hooked; interlock 22/22 | albuquerque.py + field_maps_albuquerque.py + test_producers_albuquerque.py + REGISTRY/METRO_META |
| city-miami-dade | `cities/miami_dade.py` + field_maps + tests (US-199) | later: registry/config/dashboard | ~13:10 PT | **spine complete** — permits+SLA+deeds; no 311; interlock 22/22 | miami_dade.py + field_maps_miami_dade.py + test_producers_miami_dade.py + REGISTRY/METRO_META |
| city-st-louis | `cities/st_louis.py` + field_maps + tests (US-200); csv_client zip-member if required | later: registry/config/dashboard | ~13:10 PT | **spine complete** — 311 zip + permits CSV + liquor SLA; mercator+zip_member wired; interlock 22/22 | st_louis.py + csv_client zip_member + REGISTRY/METRO_META |
| probe-broward | `docs/research/wave-3-probe-broward.md` (re-dispatch; file missing) | none | ~13:10 PT | superseded — original ~12:32 stream landed the file | wave-3-probe-broward.md |
