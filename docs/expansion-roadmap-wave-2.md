# Expansion Roadmap Wave 2: coverage depth before coverage breadth

**Status:** Approved 2026-08-24 (geocoding-first sequencing confirmed) · **Horizon:** ~4 weeks
**Tracker:** Linear project *Urban Signal* — HJ-113…HJ-125 (see §4)
**Predecessor:** `docs/expansion-roadmap.md` (5 → 17 metros, closed 2026-08-23)
**Evidence base:** `docs/research/wave-2-city-candidates.md` — live-probed 2026-08-24
**Baseline (measured, not asserted):** 17 cities · 55 feeds · socrata 34 / arcgis 14 / carto 4 / ckan 3

---

## Contents

1. [The thesis, and why this plan is not "12 more cities"](#1--the-thesis)
2. [Program targets and strict metrics](#2--program-targets-and-strict-metrics)
3. [Architecture deltas](#3--architecture-deltas)
4. [Wave sequence](#4--wave-sequence)
5. [Per-city registration contracts](#5--per-city-registration-contracts)
6. [Orchestration mechanics](#6--orchestration-mechanics)
7. [Model and alerting gates](#7--model-and-alerting-gates)
8. [Risk register](#8--risk-register)
9. [Open research](#9--open-research)

---

## 1 · The thesis

The 5 → 17 program was bounded by **platform clients**. That constraint is gone:
socrata, arcgis, carto and ckan cover every candidate found in the 2026-08-24
survey, and **no new client is required by anything in this plan.**

The constraint that replaced it is **geocoding**. Eleven verified, currently-
publishing feeds are excluded from the product for one reason: they carry an
address string and no coordinate pair. Seven of those eleven are in cities we
have already registered, hand-authored geography for, and are already paying
scheduler and model cost to serve.

| Path | New feeds | New metros to author | New calibration burden |
|---|---|---|---|
| Register 4 new Tier-1 cities | +4 | 4 | 4 cities × 60-day warm-up |
| Ship geocoding | **+11** | **0** | 0 new cities; existing cities deepen |

Registering Columbus, Nashville, PG County and Kansas City adds four feeds and
four hand-authored `cities/<city>.py` modules. Shipping geocoding adds eleven
feeds and zero modules — and it converts Norfolk from a 2-feed stub into a
4-feed city, DC and Denver from partials into complete ones.

**Therefore: geocoding first (Wave G), cities second (Waves C7–C8).** This is a
deliberate inversion of the predecessor program's shape, and it is the single
decision in this plan most worth arguing with before work starts.

A second, smaller thesis: the survey found the previous survey wrong about
Kansas City ("effectively dead" → its 311 feed is live with 816k geocoded rows,
found under a name the earlier query missed). Wave R's staleness probe watches
feeds we *have*; nothing watches for feeds we wrongly *rejected*. §9 fixes that.

---

## 2 · Program targets and strict metrics

### 2.1 Terminal state (exit criteria)

| Metric | Baseline (2026-08-24) | Target | Verified by |
|---|---|---|---|
| Registered cities | 17 | **21** | `len(REGISTRY)` + interlock closure |
| Live feed jobs | 55 | **70** | scheduler job table |
| Feeds unlocked by geocoding | 0 | **≥ 9 of 11** | per-feed G5 probe post-Wave-G |
| Cities at full 4-feed coverage | 7 of 17 | **10 of 21** | registry audit test |
| New platform clients | — | **0** | client contract tests unchanged |
| Geocode hit rate (per feed) | n/a | **≥ 95%** rows resolved to a coordinate | Wave-G probe script |
| Geocode cost per 1M rows | n/a | **≤ $0** (self-hosted) or documented ceiling | ADR 0004 |
| Parser chain terms added | — | **≤ 3 total** (field maps carry the rest) | source diff audit at close-out |
| Spine share of delivered lines per city wave | ≤ 20% (achieved) | **≤ 20%** | `scripts/interlock_gap.py <base>` pre-dispatch |
| Torn-write incidents | 0 | **0** | `.streams/dispatch-log.md` |

### 2.2 Per-city acceptance gates

**Unchanged.** Gates G1–G10 from `docs/expansion-roadmap.md` §1.2 apply verbatim,
including the AGENTS.md city-registration rule (never register a city without
verifying it appears on the map; `TestDashboardWiring` enforces it).

Two gates are **tightened** for geocoded feeds:

| # | Gate | Wave-2 threshold |
|---|---|---|
| G5′ | Live parse rate, geocoded feeds | ≥ 95% of newest 500 rows produce events **and** ≥ 95% carry a resolved coordinate; drop rate ≤ published geocode gap + 2pp |
| G8′ | Null-H3 share | ≤ 5% for any feed registered *because of* Wave G. A geocoded feed that lands above 5% null-H3 is reverted, not documented — the whole point of Wave G is that these feeds become spatial |

### 2.3 New gate: cadence honesty (G11)

The predecessor program assumed daily-ish publishing. Two Tier-1 candidates do
not publish daily, and the 7-day staleness alarm would page forever.

| # | Gate | Threshold | Method |
|---|---|---|---|
| G11 | Declared cadence | Every feed declares `extra={"expected_cadence_days": N}`; the Wave-R staleness probe alarms at `2 × N`, not a global 7 days | `scripts/feed_staleness_probe.py` reads the declaration; unit test asserts every registered feed declares one |

Backfill requirement: G11 applies to all 55 existing feeds, defaulting to 7,
so the probe's behaviour is unchanged where the assumption already held.

---

## 3 · Architecture deltas

Four deltas. **None of them is a new platform client.** Decisions to be recorded
in **ADR 0004** (geocoding) and **ADR 0005** (text watermarks), following the
pattern of ADR 0002.

### D6 · Geocoding capability (the wave's whole point) — **HJ-113**

**Shape:** a leaf module `src/spatial/geocoder.py` plus one spine touch in the
H3 enrichment consumer, invoked only when a normalized event arrives with an
address and no coordinate.

Requirements, in priority order:

1. **Deterministic and replayable.** The same address must yield the same
   coordinate on a replay six months later, or backfill parity (G6) becomes
   unverifiable. This rules out any provider whose results drift silently.
2. **Self-hostable.** 11 feeds × historical backfill is millions of geocodes.
   Census TIGER/Line + a local Nominatim or `libpostal`-based matcher keeps
   marginal cost at zero and avoids a per-city rate-limit story.
3. **Cached in Postgres.** `address_hash → (lat, lon, confidence, source)`.
   The cache is the replay guarantee, not an optimization.
4. **Confidence-gated.** Below a confidence floor the event is emitted with a
   null H3 rather than a wrong one. A wrong coordinate is worse than a missing
   one: it corrupts a cell's momentum features rather than merely thinning them.

**Explicitly out of scope:** parcel-join geocoding (DC's `SSL` key, Denver's
`PARID`). Those need a per-city parcel layer and are their own delta if D6's
address path proves insufficient. Recorded here so the boundary is deliberate.

**Sequencing note:** D6 must land and prove ≥ 95% hit rate on **one** existing
feed (Norfolk 311 is the cheapest test — Socrata, already-registered city,
already-authored geography) before the other ten feeds are wired.

### D7 · Text-watermark normalization (spine, small) — **HJ-114**

PG County's `transfer_date` is a text column carrying the sentinel `ZZZZZZZZ`,
which sorts above every real date — a naive `ORDER BY … DESC` watermark returns
garbage forever. NYC's `issuance_date` has the same class of problem (mixed
formats), already logged as a Wave-R spike in the predecessor plan.

Fold both into one delta: a declared `extra={"watermark_type": "text",
"watermark_format": "...", "watermark_exclude": ["ZZZZZZZZ"]}` resolved by the
client into a typed comparison. This closes the predecessor program's
outstanding NYC spike as a side effect.

### D8 · Cadence declaration (registry, data-only) — **HJ-115**

`extra={"expected_cadence_days": N}` per G11. Data, not code — the scheduler
already polls on `interval_seconds`; only the *alarm* threshold changes.

### D9 · Snapshot-mode reuse for parcel tables (no new code expected)

PG County's Property table is a 353k-row parcel snapshot, structurally identical
to Baton Rouge's business registry: no reliable incremental watermark, ingest by
id-set diff. **Verify D4 covers it as-is.** If it does, this delta is zero code
and the entry exists only to force the check. If it does not, that is a finding
worth a spine hold, not a silent workaround.

---

## 4 · Wave sequence

Same protocol as the predecessor: ≤ 2 implementation streams per wave, leaves
parallel, spine serial, never park a torn write.

| Wave | Streams | Delivers | Prereqs | Exit criteria |
|---|---|---|---|---|
| **G1** | `geocoder-core` (leaf) — **HJ-113** | `src/spatial/geocoder.py`, Postgres cache schema, confidence gating, ADR 0004 | none | ≥ 95% hit rate on Norfolk 311's newest 500 rows; deterministic replay proven by geocoding the same 500 rows twice across a cache flush |
| **G2** | `geocode-norfolk` **HJ-121** ∥ `watermark-text` **HJ-114** | Norfolk 311 + SLA registered (2 → 4 feeds); text-watermark support; NYC spike closed | G1 | G5′/G8′ on both Norfolk feeds; NYC watermark regression test green |
| **G3** | `geocode-dc` **HJ-122** ∥ `geocode-denver` **HJ-123** | DC SLA + DEEDS, Denver SLA + DEEDS → both cities complete | G2 | G5′/G8′ ×4; **19 cities-equivalent coverage at 63 feeds** |
| **G4** | `geocode-montco` **HJ-124** | MC311 registered if zip-centroid confidence clears the floor — **expected to fail**, and failing is an acceptable outcome recorded as evidence | G2 | Either G5′/G8′ green, or a documented rejection with measured confidence distribution |
| **C7** | `city-columbus` **HJ-118** ∥ `city-nashville` **HJ-119** | Columbus (1 feed) + Nashville (1–2) → 19 cities, ~65 feeds | none (arcgis ready) | DoD G1–G11 ×2 |
| **C8** | `city-pg-county` **HJ-125** ∥ `city-kansas-city` **HJ-120** | PG County (1–2) + KC (1) → **21 cities, ~68–70 feeds** | G2 (PG needs D7), D9 verified | DoD ×2; PG cadence exception documented under G11 |
| **R2** | `rejection-recheck` **HJ-116** | Quarterly re-probe of every *rejected* candidate, not just registered feeds (§9) | none | script re-finds KC 311 from the 2026-08-23 rejection list as its acceptance test |
| **M2** | `model-refresh` after each wave pair | Walk-forward retrain with new-city H3-7 block holdouts; per-city calibration | prior wave closed | pinball p50 within ±10% pooled baseline |

**Sequencing rationale:** G1–G4 deliver +9 feeds against zero new geography.
C7–C8 are cheap because they are single-feed partials on an existing client.
If capacity runs short, **C7/C8 are the droppable half of this plan; Wave G is
not.**

---

## 5 · Per-city registration contracts

Re-probe every ID at wave claim time (≤ 72 h), per the predecessor's §5.2(1).

| City (job_suffix) | Feeds → datasets (watermark) | Platform | field_map budget | Quirks tests must pin |
|---|---|---|---|---|
| **Columbus** `columbus` | PERMITS `Building_Permits/FeatureServer/0` (`ISSUED_DT`) | arcgis ×1 | ~6 | All-uppercase Accela schema; `B1_ALT_ID` is the permit id — `OBJECTID` must **not** reach the job-id chain; `G3_VALUE_TTL = 0` is legitimate, not a parse failure; `maxRecordCount` 2000 |
| **Nashville** `nashville` | PERMITS `Building_Permits_Issued_2/FeatureServer/0` (`Date_Issued`) · *optional* SLA Residential STR Permits | arcgis ×1–2 | ~5 | Mixed-case `Lat`/`Lon` attrs (not `latitude`); two-date model (`Date_Entered` + `Date_Issued`); `maxRecordCount` 1000; **311 is stuck at the 2025 slice — do not register it** until a 2026 layer appears |
| **Prince George's Co.** `pgco` | 311 `2ywx-ipcd` (`date_request_opened`) · *conditional* DEEDS-class `qzrv-2tnv` (`transfer_date`, snapshot) | socrata ×1–2 | ~4 | **D7 prereq** for the property table: `transfer_date` is text with `ZZZZZZZZ` sentinel; **D9/snapshot prereq** — 353k-row parcel table, not a transaction stream; 311 publishes on a ~monthly cadence, needs G11 declaration (`expected_cadence_days: 30`) |
| **Kansas City** `kcmo` | 311 `d4px-6rwg` (`open_date_time`) | socrata ×1 | ~3 | **Register permits nowhere** — KC permit tables are annual archives, 2019–2023, genuinely dead; SLA `pnm4-68wg` rejected (no date column at all); re-probe cadence before commit, newest row was 7 d old at survey |

**Honest note on totals:** this plan claims 21 cities and ~70 feeds, but four of
the eight new-city feeds are conditional (Nashville SLA, PG deeds ×1, and the
G4 MC311 outcome). The **firm** floor is **21 cities, 66 feeds**. Do not publish
the 70 figure until it is measured from `REGISTRY`, per the predecessor
program's feed-count reconciliation discipline.

---

## 6 · Orchestration mechanics

Unchanged from ADR 0001 / `docs/agents/parallel-streams.md`: claim → build
(leaf) → interlock (spine, serial, one stream at a time). Claim files at
`.streams/<id>.md`, dispatches in `.streams/dispatch-log.md`,
`python scripts/interlock_gap.py <base>` before dispatch.

One addition specific to Wave G: **the geocoder is a shared dependency**, so
G2/G3/G4 streams all consume it. Treat `src/spatial/geocoder.py` as spine after
G1 closes — a leaf stream must not edit it mid-wave to fix its own city's hit
rate. A city-specific address quirk goes in that city's `field_map`, exactly as
schema quirks do today.

---

## 7 · Model and alerting gates

Predecessor §6 applies unchanged for the four new cities (ship with
`alert_enabled=false`, 60-day warm-up, ±10% pinball unlock, H3-7 block
holdouts).

**New consideration — geocoded feeds change existing cities' distributions.**
Norfolk, DC, Denver and Montgomery are already calibrated. Adding feeds to a
calibrated city shifts its feature distributions mid-flight.

| Gate | Rule |
|---|---|
| Re-warm on deepening | Any registered city that gains a feed re-enters warm-up: `alert_enabled=false` for 30 days (not 60 — geography and history are already proven), then the standard ±10% pinball check against its own prior baseline |
| Attribution sanity | TreeSHAP weight drift ≤ 25% relative after a city gains a feed, same threshold as the predecessor's cross-city rule |
| Geocode provenance in features | Events with geocoder-derived coordinates carry a `coord_source` flag; the first retrain must confirm the model is not learning the flag itself as a signal |

That last row is the sharpest model risk in this plan: geocoded events will be
systematically different (older feeds, different cities, address-only sources),
and a model can learn "this came from a geocoder" as a proxy for "this is
Norfolk". Blocking it requires the flag to exist and be tested, not assumed away.

---

## 8 · Risk register

| # | Risk | Likelihood | Impact | Mitigation | Trigger response |
|---|---|---|---|---|---|
| W1 | Geocoder hit rate falls below 95% on real municipal address strings (abbreviations, unit numbers, missing city) | **High** | High | G1 proves on Norfolk before the other 10 feeds wire; confidence gate emits null-H3 rather than a wrong cell | < 95% on two feeds ⇒ Wave G descopes to the feeds that clear, remaining feeds stay excluded and honestly documented |
| W2 | Geocoded coordinates are wrong but confident (silent corruption of momentum features) | Medium | **High** | Confidence floor; spot-audit 100 random geocodes per feed against the source address before G5′ passes | any audit failure ⇒ raise the floor, re-run, do not ship |
| W3 | Replay non-determinism breaks backfill parity (G6) | Medium | High | Postgres cache **is** the determinism guarantee; G1 acceptance includes a two-pass replay across a cache flush | non-deterministic ⇒ pin provider version or reject the provider |
| W4 | PG County text watermark (`ZZZZZZZZ`) poisons ingestion | **Certain if unmitigated** | Medium | D7 typed compare + explicit exclude list; this is a known-value sentinel, not a discovery risk | watermark regression ⇒ freeze poll, repair, replay |
| W5 | PG County 311's ~monthly cadence pages the staleness monitor forever | High | Low | G11 cadence declaration before registration | alarm noise ⇒ the cadence declaration was wrong; fix the declaration, not the threshold |
| W6 | A Tier-1 feed retires between survey and implementation | Medium | Medium | §6 re-probe rule (≤ 72 h); Wave-R monitor | swap to Tier-3 (Sacramento, Charlotte) after a row-level probe, or descope |
| W7 | Model learns geocoder provenance as signal | Medium | High | `coord_source` flag + first-retrain check (§7) | confirmed ⇒ drop the flag from features and re-examine feed-level confounding before unlocking alerts |
| W8 | Wave G's scope grows into parcel-join geocoding | Medium | Medium | D6 declares parcel-join **out of scope** explicitly | if DC/Denver need it, that is a new ADR and a new wave, not a Wave-G expansion |
| W9 | Four new single-feed cities dilute the product (a "city" that is one permits feed) | Medium | Medium | Dashboard must show per-city feed coverage honestly (PRODUCT.md principle 3: treat city differences as product truth) | if a 1-feed city reads as broken to users, hold C7/C8 and finish Wave G instead |

---

## 9 · Open research

Two gaps this plan does **not** close, stated so they are not mistaken for
findings.

### 9.1 Nine unresolved metros

Houston, Phoenix, San Antonio, San Jose, Atlanta, Indianapolis, Jacksonville,
Milwaukee and Las Vegas were **not resolved to a platform** in the 2026-08-24
survey — Hub hostname guesses 404'd, DNS failed, or TLS verification failed.
Several are top-10 US cities. Nothing in this plan should be read as evidence
about them.

This is the highest-value remaining research task and is **deliberately not
scheduled here**, because a platform-discovery pass is a research stream, not an
implementation wave. Recommend dispatching it as its own stream in parallel with
Wave G, output landing in `docs/research/` as usual.

### 9.2 Rejection rot (Wave R2)

The predecessor's Wave-R staleness probe watches feeds we registered. Nothing
watches feeds we **rejected** — and this survey found Kansas City's 311 alive
one day after a survey concluded the city was "effectively dead", because the
earlier query looked under the wrong name.

Wave R2 builds the mirror-image monitor: a quarterly re-probe of every rejected
candidate in `docs/research/`, with **re-finding KC 311 from the 2026-08-23
rejection list as its acceptance test.** Cheap script, and it makes every
research doc in the repo self-correcting rather than decaying.

---

## Scorecard

Updated per wave close-out in `.streams/dispatch-log.md`.

| Wave | Cities cum. | Feeds cum. | Yield | Spine share | Incidents |
|---|---|---|---|---|---|
| baseline (2026-08-24) | 17 | 54 | 12/12 registrations closed (HJ-16–26); MC311 excluded by construction (no coordinates) | — | Boston Licensing Board excluded live-probe finding: `gpsx`/`gpsy` are State Plane meters (EPSG:26986), not degrees — fails G5 by construction, CRS transform deferred to geocoding wave (HJ-113). Baltimore 311 (gap 25.07%) and Montgomery permits (gap 4.97%) pass G5 under published-gap+2pp tolerance |
| G1 | 17 | 54 | | | |
| G2 | 17 | 56 | | | |
| G3 | 17 | 60 | | | |
| G4 | 17 | 60–61 | | | |
| C7 | 19 | 62–63 | | | |
| C8 | 21 | 65–69 | | | |

---

## Appendix · Full expansion backlog in Linear

Everything expansion-related now tracked in the Linear project *Urban Signal*.
Wave-2 tickets are in §4; this appendix covers the rest, which sits outside this
plan's waves but shares its subject.

### Signal expansion — beyond the original four feed families

Evidence: `docs/research/metro-expansion-and-new-signals.md` §2–3.

| Ticket | Work | Note |
|---|---|---|
| **HJ-126** | Extend `FeedType` + raw topic taxonomy | Spine prereq; `FeedType` is closed at 4 members today |
| **HJ-127** | License move-in/move-out flow from existing SLA feeds | **Highest value, lowest cost in the survey** — no new endpoint, no new `FeedType`; converts SLA from a stock to a flow signal |
| **HJ-128** | Crime incidents (CHI/SF/SEA live, NYC monthly, LA blocked by NIBRS gap) | Real LIMS-input candidate, but correlates with 311 — ship behind an ablation |
| **HJ-129** | Street-cut permits (NYC/CHI) | Disruption context only; 2 of 5 metros, overlaps CapEx density |
| **HJ-130** | NYC executed evictions | Context/validation only — single-metro features create cross-city asymmetry. Needs the geocoder |
| **HJ-131** | STR registrations + transit ridership | May close as "not worth it"; that is a valid outcome |

### Geography

| Ticket | Work | Note |
|---|---|---|
| **HJ-138** | **Decision (ADR): multi-source metro vs separate registration** | Blocks Pierce. Three separate registrations now cover one metropolitan area (DC, MontCo, +PG proposed) while the product sells metros |
| **HJ-132** | Register Pierce County WA (permits) | The only "yes" in the entire adjacent-county survey; richer date model than any registered city |
| **HJ-133** | Register Minneapolis MN (permits + year-sliced 311) | Ready via existing ArcGIS client; never scheduled into the 5→17 program |
| **HJ-134** | Row-level probe: Sacramento, Charlotte, Portland, Tampa | Holds, not rejections. Also the contingency pool for plan risk W6 |

### Hardening and recurring maintenance

| Ticket | Work | Note |
|---|---|---|
| **HJ-135** | Annual New Year rollover drill | Risk R3 is rated *"Certain (if unmitigated)"* — DC, Boston, Baltimore, +Minneapolis |
| **HJ-136** | Standing calendar for rotating source IDs | Norfolk FY (July), Alameda (annual), King County parcel sales (quarterly). The weekly probe cannot catch these — the endpoint is *replaced*, not staled |
| **HJ-137** | Verify Kafka partitioning + 2× replay lag target | Both were 5→17 checklist lines with no recorded result; cheap to change before the feed count grows, disruptive after |

### Deliberately not ticketed

- **Wave-A feed repairs** — verified complete in the registry on 2026-08-24:
  SF permits `i98e-djp9`, SF deeds `wv5m-vpq2`, Chicago deeds `wvhk-k5uv`,
  LA 311 `2cy6-i7zn` all repaired and live.
- **Wave-R staleness probe** — `scripts/feed_staleness_probe.py` exists and is
  wired to `.github/workflows/feed-staleness.yml`.
- **Calibration/alert-unlock mechanism** — `src/models/calibration.py` and the
  per-city gate in `src/serving/dispatcher.py` are built.
- **The 56th/57th feed** — the predecessor program's reconciliation explicitly
  concludes that 55 is the safe total and no speculative feed should be
  registered to reach 57. Not a task.
- **Snohomish County** — parked by the survey, not rejected; folded into the
  recurring-checks ticket rather than carrying its own.
