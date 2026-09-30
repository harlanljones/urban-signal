# Dispatch log

## 2026-08-30 — city registration/feed supplementation (El Paso) — Linear US-221

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-el-paso | `src/spatial/cities/el_paso.py` + El Paso-specific tests | config.py, city_registry.py, cities/__init__.py, producer spine if required | 2026-08-30 | blocked at shared feed/schema hold; existing leaf contract verified | no implementation artifact; evidence in stream log |

The orchestrator appends one row per launched stream, then closes it out with
an outcome. Without this record a stream that produced nothing (failure mode
F2) leaves no evidence it ever existed, and stream yield is not computable.

Format: one table per dispatch date. Yield = streams with a committed,
durable artifact ÷ streams dispatched.

## 2026-08-30 — Milwaukee feed supplementation (US-220)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-milwaukee-us220 | Milwaukee CKAN city specs + field maps + tests | city registry/config/producer wiring, dashboard/export | current session | completed; targeted tests green; five viable candidates, two rejected by live probe | leaf specs/maps/tests |

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

## 2026-08-30 — Louisville feed supplementation — Linear US-219

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| US-219 | `apps/api/tests/unit/test_producers_louisville.py` | shared street-cut producer + field-map/registry wiring required; forbidden by leaf scope | current session | blocked — CRIME/PERMITS leaf contracts pass; STREET_CUT drops Louisville `PERMIT_NO` rows and emits hard-coded Chicago IDs | 2 passing leaf contract tests |

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

## 2026-08-27 — US-192 close-out (wave-3 finish)

Orchestrator single interlock hold for US-196 after G5 staging probes;
stale global-state tests refreshed; roadmap results tables written. Five
wave-3 city leaves (phoenix, miami_dade, st_louis, memphis, albuquerque)
were already on disk with spine complete; interlock verified 22/22 and the
suite repaired to 1574 passed / 3 skipped.

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| hold-us196 | street_cut producer hook + tests + stale-test refresh | config.py + city_registry.py (chicago/sacramento specs) | this session | completed — gates green | roadmap §4.3.1, geocode hook, companion entries |
| finish-us195 | docs/expansion-roadmap-wave-3.md | none | this session | completed | §3.1 Phase-0 results table |

Uncommitted at close-out: spine delta + tests + roadmap doc (user commits).

## 2026-08-27 — Post-wave-3 parallel round (orchestrator: 3 streams)

| Stream id | Leaf claim | Spine needed | Dispatched | Task |
|---|---|---|---|---|
| verify-dashboard | none (read-only live checks) | none | this entry | dashboard METRO_META + snapshot/manifest coverage for 5 new metros |
| model-refresh | none (training artifacts, gitignored) | none | this entry | retrain incl. new metros as H3-7 holdouts (roadmap §5/§7) |
| us364-snap | tests + probe evidence | config.py + city_registry.py (starter-set SLA specs) | this entry | US-364 SNAP retailers as SLALicenseEvent |

Only one stream edits code; no interlock contention. Commit policy: none of
the streams git-commit — changesets land uncommitted for the maintainer.

| 2026-08-27 — us364-snap outcome | leaf: apps/api/tests/unit/test_producers_snap.py (+5 refreshed per-city tests) | spine: apps/api/src/config.py, apps/api/src/spatial/city_registry.py | completed | US-364: SNAP registered as FeedType.SLA on 6-metro starter set (dallas/denver/columbus/raleigh/boise/wichita) via shared snap_sla_spec(state); snapshot mode, cadence 14d; facts re-exported. Gates: interlock 22 passed, suite 1585 passed/3 skipped, product lint green, ruff zero-new-findings. Yield: 11 new tests + 6 registrations + product facts. |

## 2026-08-28 — Parallel fleet round (9 streams)

| Stream id | Leaf claim | Spine needed | Task |
|---|---|---|---|
| ci-watch | none (read-only) | none | watch 965b312 runs; verify deploy-dashboard + byte-sync + deep links |
| snap-extend | tests | config.py + city_registry.py | extend SNAP SLA to remaining SLA-less metros |
| ci-workflow-patch | none | .github/workflows/batch-push.yml (uncommitted patch) | fix deploy-dashboard skip on non-push events |
| snap-zip-backfill-design | none (design comment) | none | design auth-date backfill from 2005–2025 zip; comment on US-364 |
| triage-ne | triage probe docs (docs/research/probe-*.md) | none | row-level probes US-313/315/316/317/349/351/352/353 |
| triage-midatl | same | none | US-314/318/319/320/343/344/348/354 |
| triage-south | same | none | US-339/340/341/345/346/357/358/359 |
| triage-west | same | none | US-321/323/325/326/328/329/330/331/332 |
| triage-stale-sweep | none (Linear comments only) | none | status comments on 13 already-answered tickets (registered/REJECT) |

Only snap-extend edits app code; ci-workflow-patch touches only the workflow
file. No commits by agents.
| snap-extend | apps/api/src/spatial/city_registry.py, apps/api/tests/unit/test_producers_*.py (14 files) | apps/product artifacts via facts:export | US-364 SNAP SLA extended to 21 SLA-less metros (incl. prince_georges); interlock 22 + full suite 1585p/3s + ruff parity + product lint green |

| Stream id | Outcome |
|---|---|
| ci-watch | PASS — validate+snapshot+deploy all green on 965b312; byte-sync OK (CF script only); 5 deep links live in served METRO_META; staleness green. Wave-3 fully on the map. |
| snap-extend | 21 specs added (incl. prince_georges) — REGISTRY has zero SLA-less metros. interlock 22, suite 1588/3, facts+lint green, ruff parity. Uncommitted. |
| ci-workflow-patch | Root cause: validate `if:` excludes dispatch/schedule → transitive needs-skip of deploy-dashboard. Patch applied (uncommitted) to batch-push.yml:116. Gap documented: validate never runs on cron/dispatch (nightly deploys unvalidated) — ticket filed. |
| snap-zip-backfill-design | Zip probed: 95MB/703k rows, Record ID join 93-96%, M/D/YYYY dates; ~294k events/one-shot. Design comment on US-364 (option a: one-shot script + field-map addition). |
| triage-ne | 3 ready-for-agent: Buffalo (SLA-1), Rochester (D-1), Syracuse (SLA-1). 5 stays with evidence. 8 probe docs. |
| triage-midatl | ready-for-agent: Lynchburg (P1/SLA1), Virginia Beach (P2/SLA2/D2), Huntsville (P2, watermark caveat). 5 stays. 8 probe docs. |
| triage-south | ready-for-agent: Greenville (P1), Omaha (311-1), Toledo (311-1). 5 stays. 8 probe docs. |
| triage-west | ready-for-agent: Henderson (P1/SLA2), Aurora CO (P1/SLA1), Anchorage (D1), Tucson (SLA2). 5 stays. 9 probe docs. |
| triage-stale-sweep | 13 status comments: 8 registered, 5 reject-evidence. Labels/states untouched. |

## 2026-08-28 — Wave 4 leaves (5 parallel, leaf-only; orchestrator holds spine)

Tickets claimed: US-326 aurora, US-325 henderson, US-354 virginia_beach, US-358 omaha, US-359 toledo.
Leaf contract: cities/<city>.py + field_maps + fixture tests (no CityId imports), probe re-stamp, no spine, no commit.

| Stream id | Leaf claim | Spine needed | Outcome | Yielded artifact |
|---|---|---|---|---|
| wave4-virginia_beach | cities/virginia_beach.py, field_maps_virginia_beach.py, test_producers_virginia_beach.py (52 tests) | city_registry.py, config.py, cities/__init__.py, dashboard+index.html+snapshot, test_city_leaf_naming.py count 57→62 | completed (US-354) — live re-probe 2026-08-28 confirmed all 3 watermarks (permits IssueDate 2026/08/21, 7d=247; SLA Begin_Date 07/31/2026, typed-2026=2,862 correcting probe's "YTD 77"; deeds Sales_Date 2026-08-10, 7d=0/60d=1,474 batch caveat holds); fixtures byte-verified; interlock 22/22; VB suite 52/52; full suite 1797p/3s/1f (only failure = shared leaf-naming count, spine-side) | virginia_beach.py + field_maps_virginia_beach.py + test_producers_virginia_beach.py + probe re-stamp in leaf docstrings |

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| wave4-henderson | `src/spatial/cities/henderson.py` + `src/producers/field_maps_henderson.py` + `tests/unit/test_producers_henderson.py` | CityId enum + aliases, CityRegistration (PERMITS+SLA DatasetSpecs), config, cities/__init__, dashboard METRO_META, leaf-naming count 57→62 | US-325 claimed | completed — 40 tests green, live re-probe re-verified fixtures verbatim, interlock 22/22 | 2-feed partial metro: PERMITS T1 (DSC_Permits FS, WGS84 GISX/GISY, 11.8% null→address supplement) + SLA T2 (Active Licenses CSV, address-only needs_geocode "Henderson, NV"); 8 submarkets / 6 divisions; uncommitted |
| wave4-omaha | `src/spatial/cities/omaha.py` + `src/producers/field_maps_omaha.py` + `tests/unit/test_producers_omaha.py` | CityId enum OMAHA + aliases, CityRegistration (COMPLAINTS_311 DatasetSpec — DateOnly watermark + NULL-sort gotcha), config, cities/__init__, dashboard METRO_META "Omaha, NE", leaf-naming count 57→62 | US-358 claimed | completed — 37 tests green, live re-probe (648,608 rows; OBJECTID 663169/663325 fixtures verbatim on newest watermark), interlock 22/22 | 1-feed partial metro: COMPLAINTS_311 T1 (Mayor's Hotline Cityworks, MapServer/0, DATETIMEINIT DateOnly watermark, native outSR=4326, PROBADDRESS geocode); 10 submarkets / 6 divisions; uncommitted |
| wave4-aurora | `src/spatial/cities/aurora.py` + `src/producers/field_maps_aurora.py` + `tests/unit/test_producers_aurora.py` | CityId enum AURORA + aliases, CityRegistration (PERMITS+SLA DatasetSpecs — EPSG:2232 state-plane keys, snapshot SLA, liquor/all-biz/marijuana companions), config (`arcgis_aurora_permits_url`/`arcgis_aurora_sla_url`), cities/__init__, dashboard METRO_META "Aurora, CO", leaf-naming count 57→62 | US-326 claimed | completed — 42 tests green, live re-probe re-verified all 4 fixtures verbatim by OBJECTID (L44 IssueDate 2026-08-26T18:30:01Z; L34 Issue_Date 2026-08-18; L77 Issue_Date 2026-08-22 — probe's 08-21 was +1d stale), state-plane transform reproduces geometry to ~1m (abs 2e-5), interlock 22/22, full suite 1797/3 with the single shared leaf-naming pin red | 2-feed Tier-1 metro: PERMITS T1 (MapServer/44 full history, IssueDate watermark, WKID 2232 → outSR=4326 geometry primary; PropX/PropY EPSG:2232 fallback declared; L156/L157 rolling views NOT registered) + SLA T1 (L77 non-home snapshot + L34 liquor companion, Issue_Date watermark, native X/Y EPSG:2232 fallback); 10 submarkets / 6 divisions (Downtown/Aurora Highlands/Fitzsimons/SE Aurora…); uncommitted |
| wave4-toledo | `src/spatial/cities/toledo.py` + `src/producers/field_maps_toledo.py` + `tests/unit/test_producers_toledo.py` | CityId enum TOLEDO + aliases, CityRegistration (COMPLAINTS_311 1-feed partial DatasetSpec — oid_field REQUEST_ID, watermark INIT_DATE), config, cities/__init__, dashboard METRO_META "Toledo, OH" + byte-sync index.html + snapshot, leaf-naming count 57→62 | US-359 claimed | completed — 25 tests green, live re-probe 2026-08-27 23:04 UTC re-anchored fixtures verbatim (796129/796127/796130; watermark 23:04:37+00:00, 7d=1,092, CY=43,260), interlock 22/22, full suite 1805/3 with the single shared leaf-naming pin red (count 57→62); env fix: installed pyproj (declared dep missing from venv) unblocking aurora/boston state-plane tests | 1-feed partial metro: COMPLAINTS_311 T1 (Engage Toledo Cityworks MapServer/0, INIT_DATE watermark, native outSR=4326 geometry primary; **X_COORD/Y_COORD mixed CRS — Web Mercator meters AND Ohio State Plane feet — never mapped**, LOCATION→"Toledo, OH" needs_geocode fallback; newest-row corrupted point (15.03,6.67) dropped by is_in_toledo_metro); 9 submarkets / 5 divisions; uncommitted |

## 2026-08-28 — national expansion (US-381 umbrella; single stream, no parallel dispatch)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| national-grid | `src/spatial/national_grid.py`, `src/spatial/assets/us_outline_census_20m.geojson`, `src/export/national_builder.py` + tests | none | US-382 claimed ~18:30 UTC | completed (uncommitted) | hierarchically-closed CONUS/US H3 pyramid (5,251/36,757/257,299 at res 4/5/6) + LODES signal builder, 20 unit tests, live DE 2023 proof run, interlock green |
| national-kv-sharding | `src/export/snapshot_builder.py` + snapshot tests, `dashboard/src/snapshot.ts`, `dashboard/tests/index.test.ts`, `dashboard/tests/snapshot.test.ts` | none | US-385 claimed ~20:45 UTC | completed (uncommitted) | per-cell KV shards `cells/{h3}` + `cells/index_meta` (thread-pooled inference, size-budget enforcement, `--skip-legacy-cells`), worker shard-first + legacy-fallback lookup. interlock green; full suite 1596 passed |
| national-publish | `src/export/snapshot_builder.py` + snapshot/gate tests, `dashboard/src/snapshot.ts`, `dashboard/src/index.ts`, `dashboard/tests/*` | none | US-383 claimed ~04:30 UTC | completed (uncommitted) | national chunks `national/{res}/{parent}` + `national/index` (compact-JSON rows, sparse publication, 5 MiB budget, sha256 integrity), manifest `national` block (+1.31% boot), `GET /api/v1/national[/res]` routes verified live under wrangler dev. interlock 24 passed; full suite 1740 passed; bun 75 passed |

## 2026-08-28 — Wave 4 SPINE HOLD (orchestrator, serial)

Applied in one hold: CityId enum (+aurora/henderson/virginia_beach/omaha/toledo), _HANDWRITTEN_ALIASES (+20), _HANDWRITTEN_REGISTRY entries (5 cities; omaha/toledo got snap_sla_spec NE/OH to keep zero-SLA-less invariant), config.py (+14 arcgis endpoint settings), cities/__init__.py exports, serving/dashboard.py METRO_META (+5), regenerated apps/dashboard/public/index.html, test_city_leaf_naming.py pin 57->62.
Reconciled 3 pre-spine leaf tests to post-registration behavior (toledo borough division resolution DOWNTOWN_RIVERFRONT; VB deeds geocode hook now fires). TODO before user push: full CI run.
Gates after hold: pytest -m interlock 22/22; full suite 1813 passed / 3 skipped / 0 failed; export_dashboard regenerates index.html (byte-sync test green); facts:export OK (62 metros).

## 2026-08-28 — Wave 5 leaves (7 parallel, leaf-only; orchestrator holds spine + US-387)

Tickets claimed: US-349 buffalo, US-351 rochester, US-352 syracuse, US-318 lynchburg, US-340 greenville, US-330 anchorage, US-328 tucson.
Leaf contract: cities/<city>.py + field_maps + fixture tests (city_id strings, no CityId); tests must NOT assert division/borough resolution or geocode-hook call counts (both change when the spine lands — orchestrator reconciles if needed). SLA gate closed by orchestrator (snap_sla_spec) for partials. US-344 Huntsville excluded (conditional mid-Sept re-probe).

### US-352 syracuse — DONE (leaf, 2026-08-27)

Cities/syracuse.py (1 feed: SLA Rental Registry, services6 FeatureServer/0; 6 divisions / 8 submarkets), field_maps_syracuse.py (SLA map, capitalized Latitude/Longitude, PII RR_contact_name/pc_owner dropped), tests/unit/test_producers_syracuse.py (28 tests, spine-stable). Gates: -k syracuse 30 passed; interlock 24/24 (gate grew from 22 via in-flight spine edits — 0 failures); full suite 1848 passed / 3 skipped / 1 failed = spine-owned leaf-count pin (== 62, syracuse makes 63). Spine delta handoff in .streams/wave5-syracuse.md.

### US-349 buffalo — DONE (leaf, 2026-08-27)

cities/buffalo.py (1 feed: SLA Restaurant Licenses, Socrata data.buffalony.gov 4pp3-qkuj; 6 divisions / 8 submarkets — Canalside, Larkinville, Allentown, Elmwood Village, Hertel Avenue, Black Rock, Broadway-Fillmore, University Heights), field_maps_buffalo.py (SLA map: licenseno/issdttm/descript/businessname; borough←neighborhood passthrough; gpsx/gpsy NEVER candidates — **mixed CRS live**: WGS84 on some rows, NY State Plane feet on others; native latitude/longitude authoritative 500/500), tests/unit/test_producers_buffalo.py (28 tests, spine-stable: no division/borough-resolution or geocode-call-count asserts). Gates: buffalo tests 28/28; -k buffalo green; interlock 24 passed / 0 failed; full suite 1876 passed / 3 skipped / 1 failed = spine-owned leaf-count pin (== 62, concurrent wave-5 leaves make 67). Live re-probe 2026-08-27 re-stamped watermark issdttm 2026-08-20 (7d=23, 2/1429 nulls; expdttm/licensedttm/statusdttm never watermarks; renewal licenseno repeats → uniqkey id_keys head); 3 fixtures byte-verbatim. NEW vs probe doc: `neighborhood` column exists. Config key deviation: Socrata platform → `socrata_buffalo_sla_endpoint` per repo convention (ticket said arcgis_buffalo_*). Spine delta handoff in .streams/wave5-buffalo.md.

### US-318 lynchburg — DONE (leaf, 2026-08-28)

cities/lynchburg.py (3 feeds on ONE MapServer: mapviewer.lynchburgva.gov OpenData/ODPDynamic — PERMITS /37 TRAKiT tabular StartDate date-typed cadence 1d; SLA /33 Business Licenses LicenseIssued cadence 365; DEEDS /34 Transfers SaleDate cadence 1d; 3 divisions / 7 submarkets — Downtown, Riverfront, Diamond Hill, Tinbridge Hill, Heritage, Boonsboro, Wyndhurst), field_maps_lynchburg.py (3 maps; deeds doc_type UNMAPPED — ConveyanceForm/SaleType space-padded fixed-width; SLA TradeName mostly "" → falls to Company), tests/unit/test_producers_lynchburg.py (59 tests, spine-stable: no division/borough-resolution or geocode-call-count asserts). Gates: -k lynchburg 61 passed; interlock 24 passed / 0 failed; full suite 2021 passed / 3 skipped / 1 failed = spine-owned leaf-count pin (== 62, concurrent wave-5 leaves make 63+). Live re-probe 2026-08-28 re-stamped watermarks: PERMITS StartDate 2026-08-26 (7d=36, Aug=134, total 49,757), SLA LicenseIssued 2026-08-21 (7d=1, total 2,182, typed-2026 102 — probe's "YTD 77" was a narrower cohort), DEEDS SaleDate 2026-08-26 (7d=38, total 195,460); 3+2+3 fixtures byte-verbatim. NEW vs probe doc: layer /34 publishes NO objectIdField — OID is ESRI_OID, orderByFields=OBJECTID 400s → deeds spec carries order_by="ESRI_OID" (only forwarded arcgis kwarg); plain ISO string watermark comparison verified working on host (no ANSI-literal entry needed); deeds parcel_join LRSN→/41 Parcel polygon centroid (probe Path A) wired into spec. Spine delta handoff in .streams/wave5-lynchburg.md.

### US-328 tucson — DONE (leaf, 2026-08-28)

cities/tucson.py (1 feed: SLA BUSLIC business licenses, ArcGIS PublicMaps/OpenData_EconomicDevelopment/MapServer/3; 5 divisions / 8 submarkets — Downtown, Armory Park, Barrio Viejo, Fourth Avenue, University of Arizona, Midtown, Catalina Foothills edge, Oro Valley edge [evidenced: 1,021 CITY='ORO VALLEY' rows]), field_maps_tucson.py (SLA map: ACC_NUM/ACC_NAME/LIC_TYPE+NAIC_DESC/LIC_STATUS/DT_START/FULLADDRESS/ZIP_CODE; latitude/longitude NEVER candidates — store SR WKID 2868 Arizona-East feet, coords come only from outSR=4326 geometry lift), tests/unit/test_producers_tucson.py (41 tests, spine-stable: no division/borough-resolution or geocode-call-count asserts). Gates: tucson 41/41; -k tucson green; interlock 24/24; full suite 2021 passed / 3 skipped / 1 failed = spine-owned leaf-count pin (== 62, tucson + concurrent wave-5 leaves make 68). Live re-probe 2026-08-28 re-stamped watermark DT_START: 93,483 rows probe-exact; newest non-future 2026-05-29 (OBJECTID 6); future-dated sentinels 2026-09-12/2026-09-03 (newest row OBJECTID 16 has null geometry) → sentinel handling = spec where "DT_START <= CURRENT_TIMESTAMP" (verified live), watermark_exclude stays empty (rolling sentinels un-pinnable + host is ANSI-date); expected_cadence_days=30 + alarm_exempt=True + reason (slow ~2 non-future rows/60d). NEW vs probe doc: gis.tucsonaz.gov REJECTS ISO date literals in where (400) and only accepts ANSI date 'YYYY-MM-DD' — spine MUST add the host to ANSI_DATE_LITERAL_HOSTS (watermarks.py); CHAR-padded source columns (ACC_NUM/LIC_STATUS/ZIP_CODE) pinned byte-verbatim; FULLADDRESS mapped as the address (probe's STREETNUM parts-join is not first_mapped-compatible). 4 fixtures byte-verbatim (OBJECTID 16/6/7/9). Spine delta handoff in .streams/wave5-tucson.md.

### US-351 rochester — DONE (leaf, 2026-08-28)

cities/rochester.py (1 feed: DEEDS/sales via Tax Parcels, maps.cityofrochester.gov Open_Data/Tax_Parcels_Open_Data/FeatureServer/0 — on-prem ArcGIS, NOT the services2 AGOL org; 6 divisions / 8 submarkets — Center City, Corn Hill, Park Avenue, Neighborhood of the Arts, Charlotte, Maplewood, 19th Ward, Upper Falls; every anchor point-in-parcel verified live, Pittsford 0 hits → excluded), field_maps_rochester.py (DEEDS map: doc_id PRINTKEY→PARCELID fallback [no deed-doc-number column, Columbus precedent], bbl PARCELID, doc_type DEED_TYPE, amount SALE_PRICE, recorded SALE_DATE, address SITEADDRESS, borough CITY, zip ZIP5; VALID/MultiSale/PARCEL_SOURCE/BOOK/PAGE declared non-candidates; NO owner columns on layer → parties None, no PII), tests/unit/test_producers_rochester.py (36 tests, spine-stable: no division/borough-resolution or geocode-call-count asserts). Gates: rochester 36/36; -k rochester 37 green (incl. canonical-constants); interlock 24/24; full suite 1984 tests / 1 failed / 0 errors / 3 skipped = ONLY the spine-owned leaf-count pin (== 62, wave-5 leaves make 70) — with sibling test_producers_tucson.py EXCLUDED from collection (TypeError in their _flatten_feature fixture signature; their stream owns it; disclosed). Live re-probe 2026-08-28 re-stamped watermark SALE_DATE: total 64,746 (probe-exact), 2026 YTD 2,279, Jul 141 / Jun 350 / May 485, Aug 0 — monthly-roll lag holds; newest sale 07/22/2026 = probe headline row (547 Avis St, $110,000, W, BOOK 13214/PAGE 320) re-captured byte-verbatim as OBJECTID 5294 + $1 quitclaim OBJECTID 61058 (396 Brooks Ave, Q) as noise fixture, rings verbatim at outSR=4326, centroids live-computed. Native parcel polygons → needs_geocode=False, non_spatial=False, NO parcel_join (geometry primary); text MM/DD/YYYY lexical-sort trap (typed %m/%d/%Y mandatory); quitclaims KEPT at ingest (no per-city where; VALID empty on 64,632/64,746 → market-sale filtering analysis-side); expected_cadence_days=30 (monthly roll; stalled if Sept shows 0). Spine delta handoff in .streams/wave5-rochester.md.

### US-330 anchorage — DONE (leaf, 2026-08-28)

cities/anchorage.py (1 feed: DEEDS via assessor PropertyInformation_Hosted/FeatureServer/0 on services2.arcgis.com/Ce3DhLRthdwbHlfF — last-deed-per-parcel snapshot; 5 divisions / 8 submarkets — Downtown Anchorage, South Addition, Midtown, Rogers Park, Russian Jack, Sand Lake, Turnagain, Eagle River & Chugiak [evidenced: GIS_Site_City Eagle River 9,653 / Chugiak 3,274; Girdwood 1,613 too thin]), field_maps_anchorage.py (DEEDS map: doc_id Parcel_ID→GIS_ParcelNum11→OBJECTID, bbl Parcel_ID, recorded Deed_Date, borough GIS_Site_City→Tax_District, party2_grantee Owner_Name [snapshot grain: current owner = last deed's GRANTEE — deliberately NOT durham owner→grantor], address_street Parcel_Address [composed column; 5-part GIS_Site_Street_* not first_mapped-compatible], zipcode GIS_Site_Zipcode; document_amount + doc_type UNMAPPED — no price/deed-type column, assessed values must not masquerade [NOLA precedent]; party1_grantor/latitude/longitude never candidates), tests/unit/test_producers_anchorage.py (40 tests, spine-stable: no division/borough-resolution or geocode-call-count asserts). Gates: anchorage 40/40; -k anchorage green; interlock 24/24; full suite 2150 tests / 1 failed / 0 errors / 3 skipped = ONLY the spine-owned leaf-count pin (== 62, wave-5 leaves make 69). Live re-probe 2026-08-28 re-stamped watermark Deed_Date: newest NON-future 2026-08-25 (probe-exact; noon-UTC epoch-ms stamps — compare ISO strings, never local-midnight AKST/AKDT); 5 future sentinels max 2035-03-03 → spec where "Deed_Date <= CURRENT_TIMESTAMP" (verified live) + scheduler US-111 as second line; watermark_exclude stays empty (arcgis path ignores it); PUBDATE max 2026-08-26T23:23:21Z — daily BATCH republish continues → expected_cadence_days=3 (Fri→Mon is a normal 3-day watermark gap; alarm only when the daily batch stalls past weekend+Monday), no alarm_exempt; host ACCEPTS ISO date literals (NOT an ANSI_DATE_LITERAL_HOSTS candidate); maxRecordCount 2000; 2 fixtures byte-verbatim (OBJECTID 211515894 2101 W 47TH AVE → WEST_ANCH, OBJECTID 211522925 6620 CIMARRON CIR → EAST_ANCHORAGE; rings verbatim at outSR=4326, centroids live-computed). Spine delta handoff in .streams/wave5-anchorage.md.

### US-340 greenville — DONE (leaf, 2026-08-28)

cities/greenville.py (1 feed: PERMITS BuildingPermits_PriorTwoYears, citygis.greenvillesc.gov ArcGIS Server 10.81 MapServer/0 — MapServer not FeatureServer; 6 divisions / 8 submarkets — Downtown, West End, Village of West Greenville, North Main, Augusta Road, Overbrook, Verdae, Paris Mountain Edge), field_maps_greenville.py (PERMITS map: job_id PERMIT_NUM+OBJECTID, NewIssueDate watermark, APPLICDATE filing [numeric YYYYMMDD double, stays None], BP_STATUS+Status status, PERMIT_TYPE job_type, PERMIT_VALUATION cost, STREETADDRESS address; latitude/longitude NEVER candidates — X_COORD/Y_COORD are State Plane feet; no borough/zip/bbl candidates → source_neighborhood None passthrough; owner+contractor PII blocks dropped), tests/unit/test_producers_greenville.py (36 tests, spine-stable: no division/borough-resolution or geocode-call-count asserts; 3 fixtures byte-verbatim OBJECTID 490/595/636, run through the REAL ArcGISClient._flatten_feature lift then parse_socrata_row city_id="greenville"). RESUME of prior attempt (leaf modules in 89d4307, no tests): verified both modules sound vs live layer; fixed job_id OID fallback (Henderson precedent) + docstring re-stamp. Gates: greenville 36/36; -k greenville green; interlock 24/24; full suite 2150 / 1 failed / 0 errors / 3 skipped = ONLY the spine-owned leaf-count pin (== 62, wave-5 leaves make 6x); transient anchorage failure mid-session was sibling in-flight work (passes standalone). Live re-probe 2026-08-28 re-stamped watermark NewIssueDate 1787803200000 = 2026-08-27T04:00:00+00:00 (unchanged, 4 co-newest), windows 3d=29 / 7d=38 / 60d=280 / total 3,886. NEW vs probe doc: NewIssueDate NOT where-queryable (400) AND time= param silently ignored → window counts client-side only; 0 blank STREETADDRESS; all 3,886 rows carry geometry (outSR=4326). Spine delta handoff in .streams/wave5-greenville.md.

## 2026-08-28 — Wave 5 SPINE HOLD (orchestrator, serial) — close-out

Applied in one hold: CityId enum (+buffalo/rochester/syracuse/lynchburg/greenville/anchorage/tucson), _HANDWRITTEN_ALIASES (+43), _HANDWRITTEN_REGISTRY entries (7 cities; rochester/greenville/anchorage got snap_sla_spec NY/SC/AK to keep the zero-SLA-less invariant), config.py (+10 endpoint settings), producers/watermarks.py (gis.tucsonaz.gov added to ANSI_DATE_LITERAL_HOSTS per the tucson leaf's live 400-on-ISO-literal finding), cities/__init__.py exports, serving/dashboard.py METRO_META (+7), regenerated apps/dashboard/public/index.html, test_city_leaf_naming.py pin 62->69. REGISTRY = 69 cities.
Spine-delta specs taken from each leaf's FEED_SPECS (tucson/anchorage future-date sentinels via spec `where`, NOT watermark_exclude; lynchburg deeds order_by ESRI_OID; greenville rolling 2-year window, NewIssueDate not where-queryable).
Zero leaf-test reconciliation needed this wave — all 7 leaf suites were written spine-stable (no division-resolution or geocode-call-count asserts), unlike wave 4's 3 reconciliations.
Gates after hold: full suite 2211 collected / 0 failed / 3 skipped (live probes only), exit 0 — the leaf-count pin that read "1 failed" in every leaf-stream row is now green at 69; pytest -m interlock 24/24 (gate grew 22->24 via 89d4307's national-publish tests, not a regression); export_dashboard regenerates index.html byte-synced; facts:export OK (69 metros) + product lint OK (69 city routes, 79 total routes, sitemap/agent-surface green); ruff on the 5 touched spine files introduces zero new findings vs HEAD (pre-existing UP0xx/I001/F401 only; the 2 UP017 hits are unchanged lines that merely shifted 4984/5009 -> 5371/5396).
US-387 (validate-on-cron) NOT applied here: already landed on main independently via PR #4 (`cursor/us-387-validate-on-schedule-dispatch-c7d1`, merged 2026-08-28T05:11Z) — validate.if now includes schedule + workflow_dispatch. Re-applying would have duplicated the change.
Note for the merge: origin/main is 4 commits ahead of this branch (58248e5 PR#4 US-387, 6798594, ac0f1f3 PR#3 US-207, 9d10f14 US-209 Boston DEEDS/CKAN) — US-209 touches config.py + city_registry.py, so expect a merge to reconcile there and the registry count to move past 69.
US-344 Huntsville stays EXCLUDED (conditional on the mid-Sept watermark re-probe per its probe doc).

## 2026-08-28 — US-372 spine hold (us372-spine) — claimed + closed

Spine holder for the us372-state-licenses leaf delta, scoped by Harlan to THREE registrations:
CO liquor `ier5-5ms2`→Denver, TX TABC `7hf9-qc9f`→Houston/Dallas/Austin/SA, OR CCB `g77e-6bhs`→Portland.
Outcome: gate 24/24 green; config + registry edited; scheduler NO-OP; Portland SLA SWAP OLCC→CCB per
Harlan's answer (ADR 0007 one-endpoint-per-feedtype). Stream: .streams/us372-spine.md.
Pre-existing failure left untouched: test_city_leaf_naming (101 vs 97 — southeast-wave debt).
Follow-ups (done, not spine): Maricopa CSV probe doc, FRED_API_KEY env wiring, Tier 2 ETL plan.

## 2026-08-28 — Wave 6 Southeast (orchestrator) — RESEARCH COMPLETE, spine NOT applied

RESOLVED/DONE: US-334 orlando (already registered wave-3 via US-194; verified REGISTRY+ALIASES+METRO_META+index.html+snapshot/tiles; `pytest -m interlock` 24/24 on main @ 4acb689).
NEW REGISTRATIONS FOUND (spine payload in .streams/southeast-wave.md; spine hold NOT applied — see BLOCKER): US-298 savannah (PERMITS), US-300 bowling_green (PERMITS), US-303 tallahassee (PERMITS+311+DEEDS), US-301 spartanburg (PERMITS+SLA). ANSI_DATE_LITERAL_HOSTS must add pub.sagis.org / webgis.bgky.org / intervector.leoncountyfl.gov / maps.spartanburgcounty.org.
RESOLUTION-ONLY (already registered, gate-enforced): US-337 miami_dade (city_registry.py:4903), US-335 memphis (city_registry.py:4969).
NOT-VIABLE (research complete; re-probe triggers recorded): US-299 myrtle_beach, US-302 athens_clarke, US-341 columbia_sc, US-343 knoxville, US-345 mobile, US-339 birmingham, US-306 biloxi, US-305 gulfport, US-304 pensacola.
KEEP-DEFERRED (vendor SPA no bulk REST / county-shaped data): US-336 atlanta, US-338 jacksonville, US-342 fort_lauderdale.
EXCLUDED (standing): US-344 huntsville (conditional mid-Sept re-probe). IN REVIEW (untouched): US-293 gainesville.

BLOCKER (external, 2026-08-28): branch switched main -> `chore/restore-metros-and-columbus` mid-session; batch-1/2 southeast leaf .py files (savannah/bowling_green/tallahassee/spartanburg + field_maps + tests) LOST (not on disk, not in the only stash) — must be regenerated; AND a concurrent west-coast wave (anaheim/chandler/inland_empire/long_beach) is mid-spine-hold on the SAME spine files (city_registry.py, config.py, dashboard.py, index.html, test_city_leaf_naming.py) on that branch. Spine hold deferred until west hold lands on a stable branch + southeast leaf modules rebuilt. Full trail in .streams/southeast-wave.md.

## 2026-08-28 — US-240 Las Cruces, NM (leaf, west-las_cruces) — COMPLETE

TWO-FEED PARTIAL registration verified live from the city's official ArcGIS Server
(`maps.las-cruces.org/gis/rest/services/Information_Services/MapServer`, org
ejcbAsQEUUGWEyzb, native WKID 4326 point geometry — no State Plane issue):
- PERMITS: BuildingPermits/1, 82,433 rows, Issued_Date watermark (2016-10-03 →
  2026-08-21T06:00Z), 0 future-dated, 0 null-geometry.
- SLA: Business_Registrations/2, 26,508 rows, LastUpdateDate watermark
  (2018-12-09 → 2026-08-21T06:00Z).
311 = Tyler Portico (no open API), deeds = county parcel data only — both Tier 3,
stayed unregistered. Leaf files: cities/las_cruces.py, producers/field_maps_las_cruces.py,
tests/unit/test_producers_las_cruces.py (42 tests). Gates: 42 passed, -k las_cruces
44 passed, interlock 24/24, ruff clean. Spine delta documented in
.streams/west-las_cruces.md. No git commit.

### Wave 7 (West region) close-out — 30 of 30 tickets (2026-08-28)

**20 REGISTER** (leaf files built, verified, spine delta staged; 0 REJECT with evidence), **5 REJECT** (no verifiable feed — GP slee, Coeur d'Alene, Ogden, Cheyenne, Santa Clarita), **5 partial** (1-2 feeds only):

| Ticket | Slug | Feeds | Tests | Verdict |
|---|---|---|---|---|
| US-222 | inland_empire | PERMITS + CRIME | 47 | REGISTER |
| US-223 | oakland | 311 + CRIME | 35 | REGISTER |
| US-224 | long_beach | SLA + CRIME | 49 | REGISTER |
| US-225 | eugene | 311 + SLA + DEEDS | 45 | REGISTER |
| US-226 | salem_or | PERMITS + SLA | 47 | REGISTER |
| US-227 | scottsdale | PERMITS + SLA | 52 | REGISTER |
| US-228 | chandler | PERMITS | 32 | REGISTER |
| US-229 | tempe | 3 feeds | 59 | REGISTER |
| US-230 | stockton | (verified) | 33 | REGISTER |
| US-231 | modesto | SLA-only | 34 | REGISTER |
| US-232 | oxnard_ventura | SLA+311+CRIME | 37 | REGISTER |
| US-233 | vancouver_wa | PERMITS | 46 | REGISTER |
| US-234 | billings | PERMITS + 311 | 40 | REGISTER |
| US-235 | missoula | PERMITS | 32 | REGISTER |
| US-236 | bozeman | PERMITS + CRIME | 41 | REGISTER |
| US-237 | bend | PERMITS+SLA+311+CRIME | 59 | REGISTER |
| US-238 | medford | PERMITS+SLA+311 | 39 | REGISTER |
| US-239 | yakima | PERMITS | 34 | REGISTER |
| US-240 | las_cruces | PERMITS + SLA | 42 | REGISTER |
| US-241 | santa_fe | 311 | 33 | REGISTER |
| US-242 | greeley | — | — | REJECT (no feed) |
| US-243 | nampa | ROW-permits | 30 | REGISTER |
| US-244 | coeur_dalene | — | — | REJECT (stale, county offline) |
| US-245 | boulder | PERMITS + SLA | 43 | REGISTER |
| US-246 | ogden | — | — | REJECT (EnerGov only) |
| US-247 | santa_rosa | CRIME | 32 | REGISTER |
| US-248 | cheyenne | — | — | REJECT (stale 2014-2024) |
| US-249 | anaheim | PERMITS + SLA | 42 | REGISTER |
| US-250 | glendale_az | 311 + SLA | 40 | REGISTER |
| US-251 | santa_clarita | — | — | REJECT (Accela token-protected) |

**Phase 3 (serial spine hold) PENDING** — blocked by concurrent `southeast-wave` and wave-6 hold queue. Once the interlock is free: 1 hold = CityId enum + aliases + REGISTRY (25 cities) + config endpoints + cities/__init__ exports + dashboard METRO_META + regenerated index.html + leaf-count pin + snap_sla_spec for SLA-feed cities + ANSI_DATE_LITERAL_HOSTS additions (medford, chandler, inland_empire, stockton reported). 5 REJECTs get wontfix/closing comments.

### 2026-08-28 (later) — Wave 6 Southeast SPINE HOLD APPLIED (orchestrator, serial)

Leaf modules regenerated (savannah/bowling_green/tallahassee/spartanburg + field_maps + tests) after the mid-session branch switch dropped the batch-1/2 writes. Spine applied in one hold: CityId enum (+SAVANNAH/BOWLING_GREEN/TALLAHASSEE/SPARTANBURG), _HANDWRITTEN_ALIASES (+27), config.py (+8 endpoint settings), cities/__init__ imports + __all__ (+4), REGISTRY entries (savannah PERMITS+companion, bowling_green PERMITS, tallahassee PERMITS+311+DEEDS, spartanburg PERMITS+SLA), watermarks.py ANSI_DATE_LITERAL_HOSTS (+pub.sagis.org/webgis.bgky.org/intervector.leoncountyfl.gov/maps.spartanburgcounty.org), serving/dashboard.py METRO_META (+4), regenerated apps/dashboard/public/index.html via scripts/export_dashboard.py.
State after hold: `pytest -m interlock` 24 passed / 0 failed (all four cities wired on the map + snapshot + res-5 tiles + closure/containment/completeness + endpoints-in-settings + platform clients). Leaf suites + canonical-naming 303 passed; test_watermarks 7 passed; config Settings model loads with the new endpoint defaults. One leaf test reconciled (test_producers_bowling_green.py::test_not_registered_city_no_borough_resolution -> test_registered_city_resolves_borough) per the wave's "orchestrator reconciles when the spine lands" rule.
RESOLVED on Linear (comment + Done): US-298 savannah, US-300 bowling_green, US-303 tallahassee, US-301 spartanburg (registered); US-337 miami_dade, US-335 memphis (already registered); US-299 myrtle_beach, US-302 athens_clarke, US-341 columbia_sc, US-343 knoxville, US-345 mobile, US-339 birmingham, US-306 biloxi, US-305 gulfport, US-304 pensacola (NOT-VIABLE); US-336 atlanta, US-338 jacksonville, US-342 fort_lauderdale (KEEP-DEFERRED). US-334 orlando previously Done. Remaining open by standing: US-344 huntsville (excluded/conditional re-probe), US-293 gainesville (In Review).
COMMITS DEFERRED: git commit/push are permission-denied in this session — all wave-6 leaf, spine, index.html, and registry changes are UNCOMMITTED on the working tree. Human must commit before merge. NOTE the tree also carries untracked west-coast leaf files (anaheim/chandler/inland_empire/long_beach + .streams/west-*.md) and uncommitted US-372 CO liquor-license edits (config.py + city_registry.py diff) from sibling waves.

### 2026-08-30 — Tulsa feed supplementation — Linear US-217

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| US-217 | Tulsa city/producer/test leaf files | none; stop if required | 2026-08-30 | blocked — no feasible leaf-only source; required integration crosses shared spine | baseline Tulsa contract tests pass; no implementation changes |

### 2026-08-30 — next-ticket frontier (validation docs + dashboard bug fix) — US-172/173/389/390/391

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| validate-ntd (US-172) | `docs/research/ntd-transit-gtfs-validation.md` + leaf `src/spatial/ntd_transit.py` + test | none | 2026-08-30 | completed — DEFER; doc + 9-test leaf module, Socrata mirror + 4/5 GTFS feeds live | validation doc + leaf module + tests |
| assess-noaa (US-173) | `docs/research/noaa-climate-validation.md` + leaf `src/spatial/noaa_climate.py` + test | none | 2026-08-30 | completed — ADOPT data path/DEFER integration; GHCND daily CSVs no-token live, ~1–3-day lag | validation doc + leaf module + tests |
| validate-nfhl (US-389) | `docs/research/fema-nfhl-validation.md` + leaf `src/spatial/nfhl_rollup.py` + test | none | 2026-08-30 | completed — DEFER; polygon→H3 rollup proven (10 tests), live NFHL polygon queries | validation doc + leaf module + tests |
| validate-airnow-aqs (US-390) | `docs/research/airnow-aqs-validation.md` + leaf `src/spatial/airnow_signal.py` + test | none | 2026-08-30 | completed — ADOPT signal/DEFER registration; AQS test-key live, AirNow file product credential-free | validation doc + leaf module + tests |
| fix-deckgl-overlay (US-391) | `apps/api/src/serving/dashboard.py` (leaf; not in spine manifest) + byte-synced `apps/dashboard/public/index.html` via `scripts/export_dashboard.py` | none | 2026-08-30 | completed — dropped deck.gl, national LOD as MapLibre geojson layers; 32 serving tests + interlock green, byte-sync exact | dashboard fix + synced index.html |

All five streams completed with durable artifacts (yield 5/5). `serving/dashboard.py` is
not in `docs/agents/spine-manifest.txt`, so no interlock hold was needed; `pytest -m
interlock` remained green (24 passed) after all changes. Changes left uncommitted on the
working tree. Tickets resolved on Linear with evidence comments + completed state:
US-172, US-173, US-389, US-390, US-391.

All five streams are pure leaf (research docs under `docs/research/`, plus one
dashboard leaf for US-391). `serving/dashboard.py` is not in
`docs/agents/spine-manifest.txt`, so no interlock hold is required. Interlock
gate verified green (`pytest -m interlock`, 24 passed) before dispatch.

### 2026-08-30 — next-ticket frontier wave (US-397/398/399/400/401/402/403/404/406) — feed registration + leaf clients

Dispatched 6 parallel leaf subagents (TX TREC/TDLR; FL cadastral + Asheville; NOAA weather; environmental stress; transit; CVC index). All leaf work landed and passed (220 new tests). Serial spine hold applied for the feed registrations: config.py endpoint settings + city_registry.py DatasetSpec registration (TX TREC broker SLA on 9 feedless TX metros, FL cadastral PERMITS on Ocala+Orlando, Asheville DEEDS) + series_registry NTD series + SeriesClient SODA profile. Interlock gate green (24 passed) after every hold. US-405 skipped (blocked by US-374/378/379, all In Progress).

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us397-tx-trec-tdlr | TX TREC/TDLR specs + field maps + tests | config.py + city_registry.py (TREC broker SLA, 9 metros) | 2026-08-30 | completed — 18 tests, SLA registered, interlock green | specs/field-maps/tests + registry wiring |
| us398-fl-cadastral | FL cadastral spec + field map + tests | config.py + city_registry.py (PERMITS Ocala/Orlando) | 2026-08-30 | completed — 17 tests, registered, interlock green | spec/field-map/tests + registry wiring |
| us399-asheville-deeds | Buncombe roll spec + field map + tests | config.py + city_registry.py (DEEDS Asheville) | 2026-08-30 | completed — 53 tests, registered, interlock green | spec/field-map/tests + registry wiring |
| us400-noaa-weather | GHCN-D + NWS clients + tests | none (feature covariates) | 2026-08-30 | completed — 30 tests | clients + tests |
| us401-environmental-stress | AirNow/USDM/StormEvents/NWIS/tide clients + tests | none (feature covariates) | 2026-08-30 | completed — 29 tests | clients + tests |
| us402-ntd-ridership | NTD SeriesSpec + tests | series_registry.py + series_client.py (leaf) | 2026-08-30 | completed — 14 tests, 4 series registered | spec + registry + SODA branch |
| us403-gtfs-static | GtfsStaticClient + tests | none | 2026-08-30 | completed — 17 tests | client + tests |
| us404-mta-marta | MTA GTFS-RT client + MARTA spec + tests | none (MARTA needs Atlanta metro — deferred) | 2026-08-30 | completed — 14 tests | clients + tests |
| us406-cvc-index | CVC composite index + tests | none (feature store) | 2026-08-30 | completed — 28 tests | feature module + tests |

Yield 9/9. All tickets resolved on Linear with evidence comments + completed state. Changes left uncommitted on the working tree.

## 2026-08-30 — Mid-Atlantic / Northeast onboarding (orchestrator) — Linear US-419

Register Worcester MA (PERMITS + SLA) and wire CT statewide SLA/DEEDS for
New Haven + Bridgeport (supplement Hartford DEEDS). Probe basis:
`docs/research/northeast-new-england-expansion-probe-2026-08-30.md`.
Pre-dispatch re-probe (orchestrator, 2026-08-30): CT SLA `ngch-56tr` and CT
DEEDS `5mzw-sjtu` live; Worcester Building_Permits + Food_Establishment_Licenses
FeatureServers live (both Table type, address-only, text M/D/YYYY dates).

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-worcester | `src/spatial/cities/worcester.py` + `field_maps_worcester.py` + `test_producers_worcester.py` | config.py, city_registry.py, cities/__init__.py | 2026-08-30 | completed — 36 tests green, interlock 25/25, ruff clean; 2-feed partial (PERMITS+SLA, both non-spatial Tables, text M/D/YYYY watermark, needs_geocode) | leaf module + field maps + tests + stream log |
| city-new-haven | `src/spatial/cities/new_haven.py` + `field_maps_new_haven.py` + `test_producers_new_haven.py` | config.py, city_registry.py, cities/__init__.py | 2026-08-30 | completed — 31 tests green, interlock 25/25, ruff clean; SLA+DEEDS via CT statewide Socrata (ngch-56tr / 5mzw-sjtu), serialnumber+listyear composite id, needs_geocode | leaf module + field maps + tests + stream log |
| city-bridgeport | `src/spatial/cities/bridgeport.py` + `field_maps_bridgeport.py` + `test_producers_bridgeport.py` | config.py, city_registry.py, cities/__init__.py | 2026-08-30 | completed — 30 tests green, interlock 25/25, ruff clean; SLA+DEEDS via CT statewide Socrata, serialnumber+listyear composite id, needs_geocode | leaf module + field maps + tests + stream log |

### 2026-08-30 — Mid-Atlantic / Northeast onboarding — SPINE HOLD (orchestrator, serial)

Applied in one hold after all three leaves landed: config.py (+4 endpoint settings:
`arcgis_worcester_permits_url`/`arcgis_worcester_sla_url`/`socrata_ct_sla_endpoint`/
`socrata_ct_deeds_endpoint`); CityId enum (+WORCESTER/NEW_HAVEN/BRIDGEPORT);
_HANDWRITTEN_ALIASES (+10); _HANDWRITTEN_REGISTRY entries (worcester=PERMITS+SLA,
new_haven=SLA+DEEDS, bridgeport=SLA+DEEDS); Hartford DEEDS supplement (5mzw-sjtu,
`where="town = 'Hartford'"`) + Hartford SLA field_map/id_keys corrected to the real
ngch-56tr columns (prior map referenced nonexistent columns); shared
deeds_acris_producer loc fallback +`geo_coordinates` so native Points are read
before address geocoding. METRO_META/index.html regenerated via export_dashboard.py
(US-427 auto-generates from REGISTRY); product facts re-exported (132 metros).
Gates: `pytest -m interlock` 25/25; full pre-flight green
(scripts/verify_cicd_preflight.py); product lint green.
Yield 3/3 leaf streams. Changes left uncommitted (local git policy); sibling
streams (peoria/laredo/hpms) were concurrently on the same spine — the hold was
applied additively on top of their edits (US-429 auto-gather for cities/__init__).


### 2026-08-30 — South Central onboarding — city-shreveport (US-267) — REJECT

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-shreveport | none (REJECT) | none | 2026-08-30 | no leaf — all four families Tier 3; City AGOL reference-only, Caddo PW org reference-only, 311 = login-gated QScend, parcels = paid DataScout SaaS, case-index layers carry no date | `docs/research/probe-shreveport.md` + stream log |

Verdict: **Tier 3, no register.** City of Shreveport AGOL
(`cEsSI6IR59h5UGE4`, 1107 items) and Caddo Parish Public Works
(`ekpaOXhC7fFWoTJ9`, 16 items) are reference-only. PERMITS = case-index
layers (no DATE column); 311 = Port City 311 on QScend (login-gated);
SLA = Oct-2022 liquor snapshot; DEEDS = DataScout paywalled. Re-probe
trigger: city permit/311 export or anonymous parish parcel/Sales stream.

### 2026-08-30 — South Central REJECT closes (US-346/347)

Two South Central metro REJECT tickets closed (no leaf, no spine edits, no
code/registry/dashboard changes; local git policy — left uncommitted).

| Ticket | Verdict | Probe doc (stamp) | Final state | Why |
|---|---|---|---|---|
| US-346 (Little Rock, AR) | NO REGISTER — all four families Tier 3 | `docs/research/probe-little_rock.md` (2026-08-28) | Done + wontfix | No Socrata (`data.littlerock.gov` is a WordPress redirect); PERMITS = wrong-grain address points (`BPADDLR`/`BPADD`); 311 = Motorola CWI UI-only; DEEDS = PAgis no sales / Pulaski Hub private. SLA : city STR registry `Short_Term_Rentals_(Public_View)/FeatureServer/2` (169 pts, native geocode) is the lone live surface but watermarked **2026-06-08**, **0 approvals in 60d**. Re-probe trigger: ≥1 approval in 60d → Tier-1 SLA companion (Orlando STR precedent). |
| US-347 (Oklahoma City, OK) | REJECTED — all four families Tier 3 | `docs/research/wave-3-probe-oklahoma-city.md` (2026-08-27) | Done + wontfix | Portal resolved (ArcGIS Hub `open-okc.hub.arcgis.com`, 81 items / 58 datasets) but no permit/311/SLA/deeds on it. PERMITS = Accela ACA UI-only (near-miss Work Zones = rolling occupancy, wrong grain); 311 = CitySourced UI-only (vendor OneView v2 authenticated); SLA = Hotel Motel Tax snapshot, no date field; DEEDS = Land Documents city clerk index, **no sale price/grantee**, newest `IndexType='D'` **2026-06-02**, **0 rows in 30d**. Re-probe triggers: Accela extracts or CitySourced 311 on the Hub, or a county sales FeatureServer (migration in flight through Aug 2026). |

Closing comments added to both tickets via `linear issue comment add` (watermark
evidence + probe-doc path + re-probe trigger), then `--state Done --add-label
wontfix`. No leaves built, no re-probe performed (evidence already on disk).

## 2026-08-31 — US-408 map LOD research wave (parallel, leaf-only) — Linear US-416/417/418

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us416-maplibre-perf | docs/research/us-416-maplibre-perf.md | none (research) | 2026-08-31 | done | docs/research/us-416-maplibre-perf.md |
| us417-mvt-pmtiles-cloudflare | docs/research/us-417-mvt-pmtiles-cloudflare.md | none (research) | 2026-08-31 | done | docs/research/us-417-mvt-pmtiles-cloudflare.md |
| us418-lims-lodes-blend-honesty | docs/research/us-418-lims-lodes-blend-honesty.md | none (research) | 2026-08-31 | done | docs/research/us-418-lims-lodes-blend-honesty.md |
||||||| parent of 47d3760 (chore(streams): record frontier-sweep round 1 dispatch (US-439..443))

### 2026-09-13 — Frontier Sweep Round 1: Bay Area data layers (orchestrator, Copilot subagents)

Dispatched 5 parallel Copilot worktree sessions (model: claude-sonnet-5, effort: high), one per ticket, no commits — human reviews each worktree's PR_DESCRIPTION.md. Tickets claimed (self-assigned, In Progress) by orchestrator per single-dispatcher policy; workers read Linear only.

| Ticket | Stream | Scope | Expected leaf | Expected spine |
|---|---|---|---|---|
| US-439 | us439-lodes | LEHD LODES WAC/RAC → H3 res-9 | new producer/leaf module + tests | city_registry.py (dataset entries), scheduler |
| US-440 | us440-market | Redfin + Zillow ZIP→H3 area-weighted | new producer/leaf module + tests | city_registry.py, scheduler |
| US-441 | us441-permits | Multi-jurisdiction permits → H3 | new producer/leaf module + tests | city_registry.py, scheduler, dob_permits_producer.py |
| US-442 | us442-transit | 511 GTFS stop→H3 k-ring scoring | new producer/leaf module + tests | city_registry.py, scheduler |
| US-443 | us443-overture | Overture buildings/POI → H3 dasymetric mask | new producer/leaf module + tests | city_registry.py, scheduler |

All five are data-layer streams (no city registration), so TestDashboardWiring/TestSnapshotWiring gates are not implicated; workers still run `pytest -m interlock` from apps/api before finishing any spine edit. Spine conflicts across the 5 worktrees are expected on city_registry.py/scheduler.py — human resolves at merge (orchestrator re-serializes if asked).

### 2026-09-13 (closeout) — Frontier Sweep Round 1 outcomes

All 5 streams completed leaf-only (US-441 declared one spine edit: dob_permits_producer.py taxonomy wiring). Orchestrator merged origin/main into each branch, re-verified targeted tests + `pytest -m interlock` (green), squash-merged sequentially: #54 US-439, #55 US-442, #56 US-443, #57 US-440, #58 US-441. Dispatch record: #53. All five tickets moved to In Review with summary comments. PR_DESCRIPTION.md files left uncommitted in each worktree; their content landed as PR bodies. Deviations: Herdr unavailable → Copilot worktree sessions (claude-sonnet-5/high) per human instruction; codebase-memory index check skipped (tool unavailable). US-441 partial: county permit sources probed dead — SF/San Jose only; human decision needed on county endpoints. US-444 remains blocked until US-438..443 reach Done. Next unblocked US candidate after closeout: none (US-407 lacks ready-for-agent and self-describes feed-blocked).

### 2026-09-14 — West region triage closeout (US-321..333, tracker-only)

The nine West-region onboarding tickets sat in Backlog labeled `needs-triage`
with triage verdicts already commented on 2026-08-27 but never applied. This
pass applied them. No code, registry, dashboard, manifest, or spine file was
touched; `pytest -m interlock` ran green (35 passed) to confirm the
already-registered members remain map-wired.

| Ticket | Metro | Verdict | Evidence | Final state |
|---|---|---|---|---|
| US-321 | Mesa, AZ | wontfix — T3 all four families | `docs/research/probe-mesa.md` | Done + wontfix |
| US-322 | Salt Lake City, UT | wontfix — T3 all four families | `docs/research/wave-3-probe-salt-lake-city.md` | Done + wontfix |
| US-323 | Colorado Springs, CO | wontfix — T3 all four families | `docs/research/probe-colorado_springs.md` | Done + wontfix |
| US-329 | Fresno, CA | wontfix — T3 all four families | `docs/research/probe-fresno.md` | Done + wontfix |
| US-331 | Bakersfield, CA | wontfix — T3 all four families | `docs/research/probe-bakersfield.md` | Done + wontfix |
| US-332 | Provo, UT | wontfix — T3 all four families | `docs/research/probe-provo.md` | Done + wontfix |
| US-324 | Albuquerque, NM | already registered (feeds: permits, sla) | `cities/albuquerque.py`, chip at `index.html:1560` | Done |
| US-327 | Phoenix, AZ | already registered (feeds: deeds, permits, sla) | `cities/phoenix.py`, chip at `index.html:1665` | Done |
| US-333 | Honolulu, HI | already registered (feeds: 311, sla) | `cities/honolulu.py`, chip at `index.html:1615` | Done |

Closeout comments cite the probe doc, the re-probe trigger (for rejects), and
the live registration evidence (for the registered three); feed sets recorded
on 2026-08-27 were stale — `sla` has landed for Albuquerque/Honolulu and
`deeds` for Phoenix since. `needs-triage` kept per repo convention (57 of 103
completed onboarding tickets carry it). Backlog: 30 → 21. Re-probe triggers
are prose on the probe docs; `scripts/rejection_recheck.py`'s REJECTIONS
manifest remains wave-2 scoped (South Central rejects US-346/347 are also not
in it), so wave-3 rejections are not machine-watched — a deliberate gap, not a
regression.


### 2026-09-23 — Bay Area layers onto the map (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| bay-area-map-wiring | `.streams/bay-area-map-wiring.md` | none | 2026-09-23 | done | `src/export/bay_area_context.py`, snapshot `--context-dir`, dashboard "Bay Area layers" picker, `bay-area-context.yml` |

### 2026-09-25 — US-377 SLA restoration (single stream, with a diagnosis subagent)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| us-377-restore-sla | `.streams/us-377-restore-sla.md` | `city_registry.py`, `sla_licenses_producer.py`, `scheduler.py` | 2026-09-25 | done | `FeedType.CHILDCARE` + `INGESTION_MODES`, `childcare_producer.py`, nine restored `datasets.sla` blocks, `GATES-US-386` G3 closed |
| failing-test-diagnosis (subagent) | `tests/unit/**` read-mostly, 2 edits | none | 2026-09-25 | done | mapped 11 failures to node IDs from the interrupted run's progress log; fixed 2, reported 9 as src-side |

The originating task was GATES-US-386 G3 ("full suite passes"), which had been
stuck as `pending` with the note that the run "produced four dots and then made
no progress". It was a live network call, not a slow machine: the
`mock_scheduler` fixture stubbed five batch clients by name and the `nfip`
stream job escaped to the OpenFEMA API. Fixing that unmasked 9 further failures
that the stall had been hiding, all from US-377 having *replaced* rather than
accompanied nine cities' `datasets.sla` blocks.

Two things worth keeping from this round:

- The interlock gate rejected the first design (one `sla` producer serving both
  feeds). `producer_key == feed.value` and one-topic-per-feed are house rules;
  the fix was a dedicated `ChildcareLicensingProducer`, not a weaker gate.
- `addopts` now carries `-m 'not live'`, so a command-line `-m interlock` must
  still override it. Verified: 35 passed, 4954 deselected. A `-m` collision in
  `addopts` is a way to make a gate pass vacuously, and was worth the check.


### 2026-09-29 — Des Moines, IA onboarding (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| city-des-moines | `.streams/city-des-moines.md` | `config.py`, `city_registry.py` (follow-up: `config.py` only) | 2026-09-29 | done (registered, `sla` in PR #66; follow-up registered `violations`, stacked on PR #67) | `cities/des_moines.py`, `cities/data/des_moines.yaml`, `test_producers_des_moines.py` (39 tests, 60 after the follow-up), `docs/research/probe-des_moines.md`, `maps.dsm.city` in `ANSI_DATE_LITERAL_HOSTS`, regenerated dashboard/facts/`cities/des_moines.json`, README/PRODUCT 156 -> 157; follow-up: `datasets.violations` (Code Case, layer 0) and `arcgis_des_moines_code_cases_url` |

Des Moines was named in the wave-3 extended list but never probed. The probe found
one feed that qualifies and registered it: the City's Rental License layer
(`maps.dsm.city` ArcGIS Server 10.91, native points on all 15,475 rows, `IssuedDate`
newest 2026-09-25, 742 distinct licences issued since 2026-07-01) as `sla`, Tier 1,
cadence 7. It is the first Iowa metro and the only feed on it. `pytest -m interlock`
35 passed; the new leaf tests 39 passed; `verify_cicd_preflight.py` green on all six
gates; G5 500/500 parsed with 100% point and 100% address on the newest 500 rows.

What did not qualify, and why (row-level evidence and re-probe triggers are in the
probe doc): permits are live (351 in 7 days, newest 2026-09-28) but Tyler EnerGov has
no platform client; 311 (CitySourced / Tyler Portico) has no public row API; Polk
County deeds are live (newest 2026-09-24) but the `Parcel` table has no geometry and
`parcel_join` takes one key name for both sides while the county's point layer names
it differently; the PSDP crime layer is 29 days old with unproven cadence; the Code
Case layer is live but see the defect below.

Things worth keeping:

- **Pre-existing platform defect, not Des Moines.** `poll_job` calls
  `parse_socrata_row` for every job, but `ViolationsProducer` and `InspectionsProducer`
  (`enforcement_signals_producer.py`) only define `parse_row`, and `ViolationEvent`
  has `status_date`, which is not among the watermark attributes the scheduler reads.
  A mock `poll_job` run on `violations_boston` produced 0 events and one DLQ route.
  Only that one mock was run; any registered `violations` / `inspections` feed should be
  checked. Code Case was therefore left unregistered rather than registered into the
  DLQ. Fix is a spine change (both producers plus the watermark attrs).
- **`maps.dsm.city` rejects ISO string dates in `where`** (400) and accepts ANSI
  `date 'YYYY-MM-DD'`, so it joined `ANSI_DATE_LITERAL_HOSTS` in
  `producers/watermarks.py` (a shared module outside the spine manifest).
- **The unmapped `license_type` default is "On-Premises Liquor"**, and the layer has no
  licence-category column, so `license_type` reads `ContactType` and the feed filters
  to `Property Owner`. Contact names, addresses and e-mails are never mapped and the
  test fixtures redact them, but the ArcGIS client requests `outFields=*`, so those
  columns would ride along in a DLQ payload for any row that failed to parse (0 of the
  newest 500 did).
- **Only `sla` is a measured seed** on the 14 submarkets (742 licences, nearest
  anchor; 0 for the four suburban ones). `base_lims`, `capex`, `permit_vel` and
  `shift_ratio` are one neutral value on every submarket because no permits, 311 or
  scored feed is registered. The site-facts export already excludes those seeds.
- The two Huntsville edits present when the stream began were committed as `7ccc900`
  while the stream ran; neither file was touched here, and no other city's
  registration changed. `docs/signal-roadmap.md` and
  `docs/expansion-roadmap-wave-3.md` were not edited.

**Follow-up, same day and same stream: Code Case registered as `violations`.** The
`poll_job` / `parse_socrata_row` fix (PR #67) removed the only blocker recorded
above, so the layer left unregistered in the first pass is now the second Des Moines
feed. Re-probe 2026-09-29 (26 requests, default curl User-Agent, no WAF response):
33,061 rows, 33,061 distinct `CaseNumber`, every row a native point inside the metro
bbox, `DateOpened` newest **2026-09-25** with 0 future-dated rows, 7d **190** / 30d
**795** / 60d 1,843, longest gap between opened days over the trailing year **5 days**
(Thanksgiving and Christmas weeks). `DateOpened > date '...'` with `orderByFields=
DateOpened DESC,OBJECTID DESC` works on `maps.dsm.city`; the ISO string returns error
400. Registered `arcgis`, watermark `DateOpened`, ids `CaseNumber` then `OBJECTID`,
interval 1800, `expected_cadence_days: 7` (alarm at 14 days; the reload is not proven
daily, same as `sla`), field map `violation_id`, `code`, `status`, `status_date`,
`address` only. `Description` is deliberately not mapped (free text, 14,568 distinct
values, staff initials and names); `Remark` and the editor columns are never
mapped. Spine touched: `config.py` (one settings field) only. Gates: `pytest -m
interlock` 35 passed, the leaf tests 60 passed, `test_scheduler.py` 25 passed,
`test_producers_enforcement_signals.py` 11 passed, `verify_cicd_preflight.py` green on
all six gates, `ruff check` clean. G5 on the newest 500 rows: 500/500 parsed, points
500/500.

Worth keeping from the follow-up:

- **`scripts/backfill_probe.py` cannot probe a `violations` job as shipped**: its
  `PRODUCERS` table has no `violations` entry (`producer_for` raises `ValueError`), so
  Austin, Boston and now Des Moines report an error row for that feed. G5 was measured
  by running the script's own `probe_feed` with the producer injected and curl-captured
  rows as the transport. The script was not edited (outside the claimed files); adding
  `violations` and `inspections` to `PRODUCERS` is the follow-up.
- **The ArcGIS client cannot narrow `outFields`**, so the Code Case free-text and
  editor columns travel in a raw row and would land in a DLQ payload if a row failed to
  parse (0 of the newest 500 do). Same platform-wide note as the rental contacts.
- **Opened-case stream.** `status_date` and the watermark are both `DateOpened`, so a
  case is published once and later status changes are not re-emitted; `Address` is
  served with a trailing space that the shared parser keeps.

### 2026-09-30 — Four-family depth pass (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| depth-four-family | `.streams/depth-four-family.md` | `config.py`, `city_registry.py`, `scheduler.py` | 2026-09-29 | done (2 of 13 metros moved to four families) | `docs/research/four-family-depth-2026-09-30.md`, Columbus `datasets.'311'` + `arcgis_columbus_311_url`, Tallahassee `datasets.sla` (SNAP), `DatasetSpec.batch_limit`, `maps2.columbus.gov` in `ANSI_DATE_LITERAL_HOSTS`, regenerated facts |

Thirteen of the 32 metros one family short were probed live by three read-only
research workers. Columbus gains `311` from a City layer the open-data Hub does not
list (`maps2.columbus.gov` ServiceRequests MapServer/1); Tallahassee gains `sla` from
the statewide SNAP fallback after local sources came up empty and the state alcohol
extract geocoded 88%. The other eleven stay, each with a re-check trigger in the
research doc. Four-family metros go from 16 to 18.

Worth keeping:

- **Daily-extract feeds can outrun the poll cap.** Columbus loads its 311 layer once a
  day; the filtered extract passed 1,000 rows on 22 of 64 weekdays in 90 days, and a
  newest-first poll capped at 1,000 never reaches the oldest rows. `DatasetSpec` now
  takes an opt-in `batch_limit` (the scheduler's per-poll cap); Columbus 311 sets 5,000.
- **SNAP licences are a statewide sample (pre-existing, 54 metros).** Each SNAP job
  filters by state only and snapshots at most 1,000 rows ordered by `ObjectId`, so it
  sees the same 1,000 retailers every poll: 19 of Tallahassee's 242. Fix is a bbox in
  each SNAP `where` plus `batch_limit` where needed; not done here.
- **Geocoder drops context.** `FL` is a unit token in `normalize_address` (drops the
  state and the ZIP after it) and a `#` unit cuts everything after it, including the
  appended `geocode_context`. Affects address-only feeds; needs a `NORM_VERSION` bump.

### 2026-09-30 — SNAP licences scoped to each metro (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| snap-metro-scope | `.streams/snap-metro-scope.md` | `city_registry.py` | 2026-09-30 | done (54 metros) | `docs/research/snap-metro-scope-2026-09-30.md`, `snap_sla_where`, bbox `where` in 54 SNAP blocks, `batch_limit` on 18 |

Each SNAP `sla` spec now reads its state inside its metro bbox instead of the whole
state, and the 18 metros whose bbox holds 667 or more retailers declare a higher
cap (up to 7,000 for Houston). Across the 54 metros that takes the retailers each
metro actually receives from 5,694 of 34,686 to all of them, and ends the 47,656
out-of-metro rows a round of polls used to publish under metro city ids.

Worth keeping:

- **A snapshot is only as complete as its cap.** Snapshot feeds re-read the table
  each poll and cap it at `batch_limit` (1,000 by default) in OID or file order, so
  a table larger than the cap is truncated to the same first rows forever. This
  applies to every snapshot feed, not only SNAP; the other 38 are the next check.

### 2026-09-30 — Snapshot feeds reach their rows (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| snapshot-reach | `.streams/snapshot-reach.md` | `scheduler.py` | 2026-09-30 | done (31 of 38 feeds; 7 listed gaps) | `docs/research/snapshot-reach-2026-09-30.md`, `test_snapshot_reach.py`, per-job snapshot seen-sets, backfills keep `where` |

The 38 non-SNAP snapshot feeds were measured live. 33 held more rows than their
1,000-row cap and read in table order, so each poll saw the same slice. 15 now
read their whole table (caps up to 16,000 for Inland Empire), 16 read newest
first by the date they already track (12 of them new or resized), and 7 stay
listed gaps with their reasons.

Worth keeping:

- **Pick a shape for every snapshot feed.** A snapshot table either fits its cap
  with half again to spare or is read newest first with a window of 1.5 times
  its last 90 days of rows. `test_snapshot_reach.py` fails a new snapshot feed
  until it declares one, with a measured count.
- **Check the sort on the live server.** Raleigh sorts nulls first under
  `DESC`, and Cleveland's unbounded sort outlasts the client timeout; both
  needed a filter that the paging check found.

### 2026-09-30 — Feeds that fail or publish nothing (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| feed-repairs | `.streams/feed-repairs.md` | `config.py`, `scheduler.py`, `dob_permits_producer.py` | 2026-09-30 | done (27 feeds publishing again, Lexington and Seattle `sla` moved to SNAP, Madison `permits` retracted; the rest listed) | `docs/research/feed-health-2026-09-30.md`, `ct_liquor_specs.py`, `test_arcgis_client.py`, `test_ct_liquor_permits.py` |

One poll of every registered job found 36 that failed outright, 8 that fetched
nothing and 16 that fetched rows but published none. Every repair was re-polled
live through `poll_job` before it landed. The mid-Atlantic `deeds` wave (14
cities, none with a live source) is the next stacked change.

Worth keeping:

- **A registered endpoint is not a checked endpoint.** The interlock gate checks
  a spec's shape. Five ArcGIS feeds sat at a service root, three CKAN feeds
  named a package instead of a resource, and 14 deeds URLs never answered, all
  green on the gate. `test_arcgis_client.py` now covers the service-root case;
  a live one-row check before registration would cover the rest.
- **Zero rows and SUCCESS is not healthy.** Eight feeds polled SUCCESS with
  nothing fetched. The ArcGIS client now raises on a page with no
  `features`, but an empty source (Tulsa `311`) still looks the same as a wrong
  one to the scheduler.
- **Read the credential table before filtering it.** State licence tables hold
  every credential a state issues, most of them held by individuals; a city
  filter alone publishes people's names as premises (`ct_liquor_specs.py`).

### 2026-09-30 — Mid-Atlantic deeds repaired or retracted (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| midatlantic-deeds | `.streams/midatlantic-deeds.md` | `config.py`, `deeds_acris_producer.py` | 2026-09-30 | done (5 deeds feeds publishing, 7 retracted with SNAP `sla` instead, Roanoke and Richmond left failing) | `test_midatlantic_deeds.py`, ArcGIS `select` as `outFields`, the leaf `compose_deed_date` hook |

The 14 mid-Atlantic `deeds` feeds registered on 2026-09-06 had never pointed at a
live source. Frederick, Providence, Burlington, Allentown and Charleston WV now
read published last-sale or transfer layers, each polled live through `poll_job`
at its production cap (992 to 1,496 rows published per poll). Albany, Dover,
Harrisburg, Huntington, Manchester, Portland ME and Wilmington DE publish no sale
dates or prices anywhere public; their `deeds` feeds are retracted and each polls
the SNAP retailer slice for its metro box (59 to 144 stores).

Worth keeping:

- **Look past the city's own portal.** Three of the five replacements are not
  city data: Maryland's statewide assessment table, Vermont's property-transfer
  returns, and a county assessor's ArcGIS server that the earlier probe missed.
  The earlier probes checked the city's portal or the county's parcel layer and
  stopped there.
- **Keep party columns on the server.** Parcel and transfer layers carry owner,
  seller and buyer names next to the sale. ArcGIS specs now name their columns in
  `select`, which the client sends as `outFields`, so those names never reach a
  row, an event or the DLQ.

### 2026-09-30 — Incremental filters repaired (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| scheduler-semantics | `.streams/scheduler-semantics.md` | `scheduler.py`, `city_registry.py`, `config.py` | 2026-09-30 | done (32 feeds whose later polls failed now poll; zone-aware exact literals; date boundaries kept; composite sale ids; Lynchburg and Roanoke deeds publish through the parcel join) | `test_scheduler_boundaries.py`, `layer_time_zone`, `DatasetSpec.composite_id` |

Every incremental ArcGIS feed was polled twice through `poll_job` on
2026-09-30. On 32 feeds the second poll failed, because their hosts reject ISO
date strings; 25 feeds declare a local zone that the stored UTC watermark was
read in; date-only watermarks skipped the rest of their day; and sale feeds
keyed by parcel alone dropped a parcel's next sale. 77 of the 78 feeds polled
now succeed on both polls; Sioux Falls `permits` fails every query at the
source.

Worth keeping:

- **Poll twice.** A single poll from no watermark never sends the incremental
  filter, so a census of first polls cannot see the failures that start on the
  second.
- **Check a new id key against the layer's field list.** Chattanooga's and
  Raleigh's composite keys first named a `PIN` column neither layer has, which
  collapsed every sale on a date into one id; the second poll caught it.
- **Read the layer's `dateFieldsTimeReference`.** A declared zone applies to
  every literal, ISO or ANSI, not only to the dates the layer returns.

### 2026-09-30 — Richmond deeds from the assessor's workbook (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| richmond-deeds | `.streams/richmond-deeds.md` | `scheduler.py`, `city_registry.py`, `config.py`, `deeds_acris_producer.py` | 2026-09-30 | done (6,650 sales from the last 365 days published live, 6,647 at a parcel centroid; the next poll got a 304) | `xlsx_reader.py`, `DatasetSpec.link_pattern`, `parcel_join.row_key` |

Richmond's assessor publishes its transfers only as a monthly 72 MB Excel
workbook under a new name each release. The Excel client now streams `.xlsx`,
finds the current file from the page that links it, and skips an unchanged
file with a conditional GET.

Worth keeping:

- **Measure the URL, not the value count.** Richmond's ArcGIS Online host
  answered 404 to a 2,155-character query; a count limit alone does not bound a
  text-keyed `IN` list.
- **Keep names in the client.** A workbook has no `outFields`; the Excel
  client applies `select` before it hands any row on, so buyer and seller
  columns never reach the scheduler, an event or the DLQ.

### 2026-09-30 — SNAP stores for the last 25 SLA-less metros (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| snap-wave | `.streams/snap-wave.md` | none | 2026-09-30 | done (25 metros poll their SNAP slice; each live poll published its full count, 5,046 stores in all, none dead-lettered) | `sla` blocks in 25 corpus files |

Every registered metro now has an `sla` family. The blocks are the shared
`snap_sla_spec` output, checked by `TestSnapMetroScope`.

Worth keeping:

- **Count before you cap.** A metro whose stores reach two thirds of the
  default 1,000 needs a declared cap; none of these did.
- **Check same-state overlaps.** Chandler's and Tempe's boxes share 113 stores,
  which publish under both.


### 2026-09-30 — Backfills read each feed the way its poll does (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| backfill-args | `.streams/backfill-args.md` | none | 2026-09-30 | done (49 changed backfills checked live against the old loader; three polls repaired: St. Louis, Laredo and San Antonio `permits`) | `scripts/backfill_loader.py`, CKAN and CSV client fixes |

A backfill hands its client the poll's arguments, places parcel-joined sales,
starts a text window in the column's format and filters client-side where the
server cannot order the text.

Worth keeping:

- **Compare the two paths, not the specs.** A test polls and backfills every
  job with a mocked client and diffs the arguments; that caught the zipped
  CSVs, the workbook and the `select`s at once.
- **Check a declared format against today's rows.** St. Louis's export
  changed its date format after registration, and the CSV client then parsed
  no row; the first poll still worked, so only a second poll showed it.
- **Look for the column.** Cincinnati's watermark column never existed in its
  file; a snapshot poll does not notice, a windowed backfill reads nothing.

### 2026-09-30 — Text-dated polls read the rows since their watermark (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| text-windows | `.streams/text-windows.md` | none | 2026-09-30 | done (six feeds polled twice live from a set watermark; every row read inside the window) | `text_date_window` in `producers/watermarks.py`, ArcGIS POST for long queries, Reno `deeds` incremental |

A filter on a text date that does not sort (`MM/DD/YYYY`, Honolulu's long
dates) names the days since the watermark, with whole months and years as
`LIKE` patterns, instead of comparing text. Backfills use the same window.

Worth keeping:

- **Measure padding before writing a pattern.** Reno writes `09/05/2026` and
  Worcester `9/5/2026` under the same declared format; the window writes both.
- **ArcGIS Online caps a GET near 2,000 characters.** A longer query is a 404
  that looks like a missing layer; send it as a POST.
- **A batch-refreshed layer holds its watermark for weeks.** Rochester's and
  Virginia Beach's newest rows were six and four weeks old, so their windows
  grow until the next batch lands.

### 2026-09-30 — Richmond crime from Chesterfield County offenses (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| richmond-crime | `.streams/richmond-crime.md` | `config.py` | 2026-09-30 | done (1,249 offenses polled live and published on a 100 m grid; the second poll published none) | `CRIME_POINT_DECIMALS` leaf hook in the crime producer; simple assault read in either order |

Richmond `crime` reads Chesterfield County's police offenses inside the metro
box, re-reading the last 120 days each poll, with each point rounded to three
decimal places before it is indexed.

Worth keeping:

- **Check a masked address against its point.** The county masks addresses to
  the hundred block but not the coordinates; comparing distinct points per
  block showed it.
- **Look at the lateness before picking a watermark.** An occurrence date that
  arrives up to 118 days late needs a window, not a watermark.
- **Run a label fix across every feed.** The simple-assault fix for Richmond
  also moved Boston's and Chicago's simple assaults, which the rule had missed.

### 2026-09-30 — Party names out of deeds events (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| party-names | `.streams/party-names.md` | `deeds_acris_producer.py` | 2026-09-30 | done (Reno and DC `deeds` polled live: no owner column read, no event with a grantor or grantee) | `test_deeds_party_names.py` guard; `select` for Reno and DC `deeds` |

The deeds producer reads no grantor or grantee, and no spec maps one; 16 specs,
five leaf maps and Asheville's spec module dropped their entries.

Worth keeping:

- **Look past the field map.** The producer's fallback chain read party names
  from any row that carried a matching column, mapped or not.
- **Check a join layer's key shape.** DC's Parcel Lots layer keys `PAR`
  parcels, not the square-and-lot SSLs its sales carry; the join matched 12
  of 4,996.

### 2026-09-30 — Las Vegas deeds on their parcels (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| lv-deeds | `.streams/lv-deeds.md` | none | 2026-09-30 | done (5,000 sales polled live, all placed on their parcels inside the metro box; no geocoder call; the second poll published none) | parcel join to `CLV_PARCELS_POLY`; a `select` without the owner block |

Las Vegas `deeds` takes each sale's point from its parcel's polygon instead
of geocoding the owner's mailing address.

Worth keeping:

- **Read a table's address columns before geocoding them.** `ADDRESS1` to
  `ADDRESS5` follow `OWNER`; comparing their ZIP with the parcel's showed a
  third of them elsewhere.
- **Look for a polygon layer with the same row count.** The city publishes
  its parcel polygons beside the table, one for each of its 302,279 rows.

### 2026-09-30 — DC deeds on their lots (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| dc-deeds | `.streams/dc-deeds.md` | `scheduler.py`, `deeds_acris_producer.py` (pass `via` to the join) | 2026-09-30 | done (5,000 sales polled live: 4,374 of 4,996 placed, up from 12; the second poll published none) | Owner Polygons join; `via` hop through `CONDORELATE` |

DC `deeds` joins the Owner Polygons layer, and a condominium unit takes its
building's lot through `CONDORELATE`.

Worth keeping:

- **Sample the join key's shape on both sides.** Sales carry square-and-lot
  SSLs; the old layer keyed `PAR` parcels, the owner polygons key both.
- **Units live in a relate table.** Condominium units have no polygon of
  their own; DC's `CONDORELATE` names each unit's lot.

### 2026-09-30 — Licences at their premises (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| sla-premises | `.streams/sla-premises.md` | none | 2026-09-30 | done (Lynchburg: 2,037 of 2,210 licences placed on their parcels, no geocoder query; Tampa: same 3,062 published, 12 columns read instead of 94) | Lynchburg `parcel_join`; `select` for both; Tampa without the owner's mailing fallback |

Lynchburg licences take their parcel's centroid instead of a geocoded
mailing address, and Tampa's never publish or fetch the owner's details.

Worth keeping:

- **An address block named `Mail*` is not the premises.** Check the city and
  state columns before geocoding one.
- **A fallback in an address chain can reach a person.** Tampa's second
  `address_street` candidate was the owner's mailing address.

### 2026-09-30 — Addresses keep their place (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| geocode-context | `.streams/geocode-context.md` | none | 2026-09-30 | done (2,326 of 16,918 live geocoder queries from 55 feeds had lost their state under v2; none under v3; Census matched 28 of 30 sampled licence queries as v3 sends them, 8 as v2 sent them) | normalization `v3`; `compose_geocode_query` |

Geocoder queries keep the city and state after a unit, a floor or a street
word that spells a state code.

Worth keeping:

- **Two letters are not a state.** `CT`, `NE`, `WY`, `LA`, `DE` and `MT` are
  street words far more often than states inside an address line; read a
  state only at the line's end.
- **A normalizer change needs the version bump.** The cache freezes misses,
  so a query that lost its state stays unplaced until its hash changes.

### 2026-09-30 — Deeds from parcel records (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| deeds-wave | `.streams/deeds-wave.md` | `config.py` (three deeds endpoints, Hartford's parcel layer) | 2026-09-30 | done (22 metros probed by two read-only research workers; 3 registered: Nashville 4,373, Hartford 353 and Denver 2,445 sales polled live, all placed in their metro box, the second polls published none) | `docs/research/deeds-probe-2026-09-30.md`; `deeds` specs for Nashville, Hartford and Denver; regenerated facts |

Nashville, Hartford and Denver read each parcel's last sale and move to all
four signal families (18 to 21). Tempe, Bend, Medford and Tacoma have
sources that need client work first.

Worth keeping:

- **Look at the parcel layer, not only the catalog.** Nashville's and
  Denver's parcel layers carry each parcel's last sale; a title search of
  the Hub found no sales dataset.
- **A numeric key loses its zeros.** Denver's sales table stores the parcel
  id as a number, and the parcel layer keys a 13-digit string. Sample the
  key's shape on both sides before planning a join.
- **Check a recommended state set's cadence.** Connecticut's OPM sales set is
  published once a year and ended on 2025-09-30.

### 2026-09-30 — Maricopa deeds (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| maricopa-deeds | `.streams/maricopa-deeds.md` | `config.py` (the Assessor parcel layer) | 2026-09-30 | done (5 cities registered from one layer: Phoenix 9,224, Scottsdale 2,507, Chandler 1,573, Glendale 1,263 and Tempe 783 deeds polled live, none dead-lettered, the second polls published none) | `deeds` specs for Tempe, Chandler, Scottsdale and Glendale, Phoenix's moved; notes in `docs/research/deeds-probe-2026-09-30.md`; regenerated facts |

Tempe moves to all four signal families (21 to 22); Chandler, Scottsdale and
Glendale move from two to three; Phoenix's deeds, which dead-lettered every
row, now publish.

Worth keeping:

- **One county layer can serve several metros.** The Assessor's parcel layer
  names each parcel's city, so one spec shape registers every Maricopa city.
- **Let the server compute the window.** `CURRENT_DATE - INTERVAL '90' DAY`
  works on hosts that reject ISO date literals, and a snapshot filter built
  on it never goes stale.
- **Bound the window above.** Parcel layers carry future-dated sentinels
  (2044 to 2099 here); `<= CURRENT_TIMESTAMP` keeps them out.

### 2026-09-30 — Bend deeds (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| bend-deeds | `.streams/bend-deeds.md` | `city_registry.py` + `scheduler.py` (`metro_clip`), `config.py` (the sales table, the taxlot layer) | 2026-09-30 | done (1,048 county sales read on Bend's township-ranges, 1,019 placed inside the metro box and published, 29 skipped, none dead-lettered, the second poll published none) | `deeds` spec for Bend; `metro_clip` in poll_job and backfills; notes in `docs/research/deeds-probe-2026-09-30.md`; regenerated facts |

Bend moves to all four signal families (22 to 23).

Worth keeping:

- **A postal city is not the city.** Deschutes County's account table says
  "BEND" for rural addresses well outside the city; check a city column
  against the map before filtering on it.
- **A parcel id can carry its place.** Oregon taxlot ids start with the
  township and range, so a prefix filter narrows a county table to the ground
  under a metro box before any join.

### 2026-09-30 — Medford deeds (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| medford-deeds | `.streams/medford-deeds.md` | `config.py` (the sales layer) | 2026-09-30 | done (304 sales in the city read and published, none dead-lettered, the second poll published none) | `deeds` spec for Medford; `src/producers/tolerant_http.py` for hosts whose header lines break HTTP/1.1 syntax; notes in `docs/research/deeds-probe-2026-09-30.md`; regenerated facts |

Medford moves to all four signal families (23 to 24).

Worth keeping:

- **A host httpx cannot read is not a dead host.** When h11 raises "illegal
  header line", look at the raw headers with curl before ruling the source
  out; the fix is a listed host in `tolerant_http`, not a new client.
- **Look for the city in the city column's values.** Jackson County's
  `SiteCity` says `MEDFORD` inside the city and `MEDFORD/COUNTY` outside it,
  unlike Deschutes County's postal `City`.

### 2026-09-30 — Tacoma deeds (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| tacoma-deeds | `.streams/tacoma-deeds.md` | `city_registry.py` (`DatasetSpec.columns`), `scheduler.py` (forwards it; the parcel join's `where`), `config.py` (the sales file and the parcel layer) | 2026-09-30 | done (2,432 county sales read, 452 in the city published, none dead-lettered, the second poll published none) | `deeds` spec for Tacoma; header-less files in `CSVClient`; a filter on the parcel join; notes in `docs/research/deeds-probe-2026-09-30.md`; regenerated facts |

Tacoma moves to all four signal families (24 to 25).

Worth keeping:

- **A parcel layer can know the city when the sales do not.** A tax code
  area belongs to one city or none, so a join filtered to the city's codes
  keeps a county-wide sales file to the city without a boundary polygon.
- **Measure a big file's parse before registering it.** `io.StringIO` holds
  four bytes a character, so an 89 MB file cost more than half a gigabyte
  to read.

### 2026-09-30 — Scottsdale 311 (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| scottsdale-311 | `.streams/scottsdale-311.md` | `config.py` (the request table) | 2026-09-30 | done (3,000 closed requests read, 2,838 published, 162 without a point skipped, none dead-lettered, the second poll published none) | `311` spec for Scottsdale; notes in `docs/research/four-family-depth-2026-09-30.md`; regenerated facts |

Scottsdale moves to all four signal families (25 to 26).

Worth keeping:

- **A table that lists closed requests follows the close date.** When a
  source publishes a row only once it closes, a watermark on the filing date
  skips every slow request.
- **A blocked probe is not a blocked feed.** The host that stopped a burst of
  probe queries answered slow, plain requests an hour later; wait, then ask
  only for what the spec will send.

### 2026-09-30 — Pierce County deeds (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| pierce-deeds | `.streams/pierce-deeds.md` | `config.py` (descriptions only: the sales file and the parcel layer serve both feeds) | 2026-09-30 | done (2,432 county sales read, 2,317 published, 115 the parcel layer could not place skipped, none dead-lettered, the second poll published none) | `deeds` spec for Pierce County; notes in `docs/research/deeds-probe-2026-09-30.md`; regenerated facts |

Pierce County moves from two signal families to three (three-family tier 28
to 29).

Worth keeping:

- **A county metro can reuse a city's county-wide source.** When the source
  already covers the county, the county's feed is the city's without the
  filter that kept it to the city.

### 2026-09-30 — Charlotte permits (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| charlotte-permits | `.streams/charlotte-permits.md` | `config.py` (the county's permits layer) | 2026-09-30 | done (1,000 permit rows read, 997 permits published, 3 further parcels of published permits skipped, none dead-lettered, the second poll published none) | `permits` spec for Charlotte; the county host in `ANSI_DATE_LITERAL_HOSTS`; notes in `docs/research/two-family-depth-2026-09-30.md`; regenerated facts |

Charlotte moves from two signal families to three (three-family tier 29 to
30).

Worth keeping:

- **Look at the county's server when the city's has nothing.** Charlotte's
  permits were recorded as absent after the City's server was read and a
  guessed county path returned 404; the county's server, listed from its
  root, republishes them nightly.
- **Check where a server sorts nulls.** A newest-first order put the 4,006
  unissued permits ahead of every issued one, which a first poll would have
  read alone.

### 2026-09-30 — Charlotte deeds (single stream, Claude project thread)

| Stream id | Leaf claim | Spine needed | Dispatched | Outcome | Yielded artifact |
|---|---|---|---|---|---|
| charlotte-deeds | `.streams/charlotte-deeds.md` | `config.py` (the county's sales layer) | 2026-09-30 | done (8,925 sale rows read, 8,765 transfers published, 160 repeats of a transfer on a parcel's other property rows skipped, none dead-lettered, the second poll published none) | `deeds` spec for Charlotte; notes in `docs/research/two-family-depth-2026-09-30.md`; regenerated facts |

Charlotte moves from three signal families to all four (four-family tier 26
to 27).

Worth keeping:

- **When a county server answers one family, list its other services.** The
  server that republishes Mecklenburg County's permits also keeps the
  county's sales ledger, one row per transfer and parcel.
