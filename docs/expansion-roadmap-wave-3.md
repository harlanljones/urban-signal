# Expansion Roadmap: Wave 3 metro areas

> **Status:** Draft for execution · **Created:** 2026-08-26 · **Baseline:** 49 registered metros
> **Prioritization lens (decided):** Easiest verified wins — metros already verified
> *live* in the 2026-08 surveys that were blocked only on address→coordinate
> geocoding, now solved by ADR 0004 (`apps/api/src/spatial/geocoder.py`, in
> production across Norfolk 311, Cincinnati deeds, Hartford, San José, San
> Antonio, Austin TABC, DC SLA, Boise, etc.). Plus a fresh re-probe of the
> "Unresolved" metros whose portals 404'd the ArcGIS Hub sweep.
>
> **Linear tracking:** parent **US-192** (project *Urban Signal*), with
> sub-issues US-193–US-206.

---

## 1 · Program targets and strict metrics

| Metric | Baseline (2026-08-26) | Wave-1 target | Program target (provisional) | Verified by |
|---|---|---|---|---|
| Registered metros | 49 | 51 (+Honolulu, +Orlando) | 49 + 2 easiest + *N* from re-probe | `len(CityId)` + interlock closure |
| Live feed jobs | ~current | +≈4 (2 metros × partial) | + re-probe findings | scheduler job table |
| Platform clients | socrata, arcgis, carto, ckan, csv | unchanged | unchanged | client contract tests |

**Loosened success criterion (new this wave):** because geocoding is solved,
a feed is registrable if it is *live* and either natively geocoded **or**
address-geocodable via `needs_geocode=True` (ADR 0004). This is the single
biggest lever and is why "easiest verified wins" is viable now.

### Per-city acceptance gates (Definition of Done — all must pass)

Carried unchanged from `expansion-roadmap.md` §1.2 (G1–G10). The only
wave-specific note: for address-geocoded feeds, **G5 floor = 95%** (not 99%)
and **G8 null-H3 share = geocode gap** is *expected and documented*, not a
defect (Cook County / Cincinnati-deeds precedent).

---

## 2 · Architecture deltas

No new spine mechanism is required for Wave 3:

- **Geocoder (ADR 0004)** — already built and in production. Reuse directly:
  set `needs_geocode=True` on address-only `DatasetSpec`s; confirm recovery
  via the staging probe.
- **Four platform clients** (socrata, arcgis, carto, ckan) + **CSV client**
  (San Diego) already cover every candidate found to date. A *fifth* client
  (CKAN/custom) is only needed if the Phase-0 re-probe surfaces a portal that
  is neither Socrata nor ArcGIS Hub nor CARTO — verify before assuming.
- **Register-a-city runbook** (`expansion-roadmap.md` §8.1) is unchanged:
  claim `.streams/city-<id>.md` → leaf `cities/<city>.py` → serial spine
  (enum, aliases, `REGISTRY`, config endpoints, `field_map`) → gates G1–G10 →
  integrator README/dashboard row.

The only thing Wave 3 *adds* is the **Phase-0 discovery pass** (§3) and the
two geocoder-unlocked registrations (§4).

---

## 3 · Phase 0 — fresh re-probe of unresolved metros

The 2026-08 ArcGIS Hub sweep 404'd many top-US metros (their portals are
CKAN/custom, not Hub). Re-probe **row-level** (newest-row-by-watermark, *not*
catalog `modified`) for the 4 feed families (permits / 311 / SLA / deeds).

**Method** (from `wave-2-city-candidates.md`, with the loosened criterion):
1. Resolve each portal's platform (Socrata discovery, ArcGIS Hub DCAT, CKAN
   `datastore_search`, or direct REST). Hub `modified` disagrees with row
   reality — ignore it.
2. For each family: newest-row read (watermark DESC), column list, geocoding
   fields, recent-window `count`.
3. Tier the result:
   - **Tier 1** — live + natively geocoded → register directly.
   - **Tier 2** — live + address-only → register via geocoder (now a win).
   - **Tier 3** — stale / no portal → reject or defer.

**Re-probe target list** (top-population gaps first; one Linear ticket each,
US-197–US-206):

| Region | Targets |
|---|---|
| Mountain West | Phoenix AZ, Salt Lake City UT, Albuquerque NM |
| Deep South / Gulf | Atlanta GA, Memphis TN |
| Florida | Miami/Fort Lauderdale FL, Jacksonville FL |
| Midwest | St. Louis MO, Oklahoma City OK |
| Northeast / New England | Providence RI |

(Full extended list including Omaha, Tucson, Fresno, Colorado Springs,
Birmingham, Des Moines, Little Rock, Rochester, Madison, Lexington, Anchorage,
Syracuse, Bridgeport, Richmond, Buffalo is carried in the Phase-0 ticket
US-195.)

**Deliverable:** a tiered table here + per-city probe contracts for any
Tier-1/2 finding, stamped ≤72 h before its implementation wave (§5.3 drift
rule). Consider `scripts/metro_discovery_probe.py` mirroring
`scripts/backfill_probe.py` / `scripts/feed_staleness_probe.py`.

### 3.1 · Phase-0 results (probed 2026-08-27; evidence in `docs/research/wave-3-probe-*.md`)

All ten re-probe tickets (US-197–US-206) are complete. Verdict board:

| Target | Tier findings (per family) | Outcome |
|---|---|---|
| Phoenix AZ | permits **T1** (ArcGIS points); STR→SLA **T1**; 311 T3 (Dynamics 365 portal); deeds T3 | **Registered `phoenix`** (permits, sla) — `.streams/city-phoenix.md` |
| Atlanta GA | all four **T3** (portal → empty Azure Gov web app; unofficial extracts stale) | none — re-probe only if the portal ever appears |
| Miami/Fort Lauderdale FL | Miami-Dade permits **T1**, SLA (local business tax) **T1**, deeds **T2** (last-sale snapshot); 311 T3; Fort Lauderdale city T3; Broward SLA T1-occupational only | **Registered `miami_dade`** (permits, sla, deeds) — `.streams/city-miami-dade.md` |
| St. Louis MO | 311 **T2** (CSV zip, Web-Mercator→WGS84), permits **T2** (CSV), excise licenses **T2** (CSV) | **Registered `st_louis`** (311, permits, sla) — `.streams/city-st-louis.md` |
| Memphis TN | permits **T1** (Hub/AGIS), 311 **T1**; monthly cadence (31d) | **Registered `memphis`** (311, permits) — `.streams/city-memphis.md` |
| Salt Lake City UT | all **T3** (stale / active-only snapshots) | none |
| Jacksonville FL | all **T3** (WAF-gated; PA file dumps only) | none |
| Oklahoma City OK | all **T3** (Incapsula wall; browser-session catalog resolved but feeds frozen) | none |
| Albuquerque NM | permits **T2** (daily CSV dump, address→geocode); 311 T3 (token-gated); SLA/business-reg frozen T3 | **Registered `albuquerque`** (permits) — `.streams/city-albuquerque.md` |
| Providence RI | all four **T3** | REJECT — do not park a stream |

**Net:** 49 → **57 registered metros** (this wave's re-probe batch added
phoenix, miami_dade, st_louis, memphis, albuquerque; the geocoder-unlocked
wave-1 pair added honolulu, orlando; the wave-2 Pierce lane added pierce).
Interlock gate 22/22 green; full suite 1574 passed / 3 skipped (2026-08-27,
post-registration stale-assertion refresh in milwaukee/tulsa/louisville/
boston/las_vegas/leaf-naming/taxonomy/street-cut/submarket tests).

Extended-list metros (Omaha, Tucson, Fresno, …) remain unprobed — a later
`probe-extended` pass can run the same row-level contract if wave-3's
five-city yield justifies it.

---

## 4 · Wave 1 — easiest verified wins

Both verified **live** in the 2026-08 surveys, blocked *only* on geocoding,
now solved. Re-probe ≤72 h before build to confirm still-live.

### 4.1 Honolulu, HI — `honolulu` (partial, like Austin/LA)

| Feed | Endpoint | Geocoding | Note |
|---|---|---|---|
| 311 | `data.honolulu.gov/resource/jdy7-ftwe` | none (9 cols) → geocode | live 2026-08-23 |
| PERMITS | `data.honolulu.gov/resource/4vab-c87q` | address-only `joblocation` → geocode | 60 cols, rich date model (`issuedate`/`createddate`/`coissued`/`finalcoissued`); verify not a closed archive (title covered through 2025-06-30) |

Register as a **partial** metro. Set `needs_geocode=True`. Verify G5 (≥95%
address-geocoded) and G8 (null-H3 share = geocode gap, documented).

### 4.2 Orlando, FL — `orlando` (partial, + STR signal)

| Feed | Endpoint | Geocoding | Note |
|---|---|---|---|
| SLA | `7388-4re5` Business Tax Receipts | address-only → geocode | live 2026-08-23 |
| SLA | `ssrj-rbua` STR Licenses | address-only → geocode | live 2026-08-23 — **new signal type**: investor-buyout pressure |

Register as a **partial** metro. The STR feed is a candidate new signal family
(see `metro-expansion-and-new-signals.md` §2); prototype behind an ablation
before promoting into LIMS.

### 4.3 Feed-expansion bonus (no new metro)

Cheap wins enabled by ADR 0004 on **already-registered** metros — add the
deferred address-only feeds (no new bbox, no model calibration):

- Sacramento PERMITS `BldgPermitIssued_CurrentYear` (address-only, `Status_Date` 2026-07-30)
- Norfolk 311 `nbyu-xjez` + SLA `dpi6-sct5` (deferred at registration)
- Washington DC SLA basic business licenses + DEEDS CAMA sales (non-spatial → geocode)
- Denver SLA active licenses + DEEDS sales/transfers (PARID/address keys)
- Chicago street-cut `pubx-yq2d` / `hr8i-6s6s` (partial coords)
- NYC street-cut `tqtj-sjs8` (address-only, deferred)

### 4.3.1 · US-196 outcome (applied 2026-08-27, serial hold; contract: `docs/research/wave-3-feed-expansion.md`)

| Feed | Staging G5 (newest 500, Census oneline, floor 0.9) | Action |
|---|---|---|
| Norfolk 311 + SLA, DC SLA + DEEDS | re-probed live, still fresh | already registered — no-op |
| Denver SLA / DEEDS | no address, no coords | **NO-GO** (US-73 descope stands) |
| Chicago `jdis-5sry` (primary) | 99.97% native coords | + `needs_geocode` hook + `field_map` (recovers the rare miss) |
| Chicago `pubx-yq2d` | 93.4% overall / 98.5% of address-bearing | **companion** (`cdot_permits_master`, unpolled until companion polling lands) |
| Chicago `hr8i-6s6s` | subset of pubx | NO-GO as second primary |
| Sacramento city permits | **90.4%** (< 95% floor; monthly batch, newest `Status_Date` 2026-07-30) | **inert companion** on county PERMITS; recheck ≥95% + batch stall after 2026-09-15 |
| NYC `tqtj-sjs8` | **78.0%** overall (house rows 60.1%, intersections 89.2%) | **unregistered** — both the full spec and the house-filtered fallback fail G5; `_nyc_row` shape retained |

Leaf change in the hold: `street_cut_permits_producer` gained the
`geocode_row_if_declared` fallback (ADR 0004) for coordinate-less rows on
specs that declare `needs_geocode`. Gates: interlock 22/22, full suite green.

---

## 5 · Wave sequence

| Wave | Streams | Delivers | Prereqs | Exit criteria |
|---|---|---|---|---|
| **P0** | `discovery` (leaf script) | tiered table of re-probe targets | none | Tier-1/2 findings + probe contracts |
| **W1** | `city-honolulu` ∥ `city-orlando` | +2 metros (partial) | geocoder (done) | DoD G1–G10 ×2; interlock green |
| **W2+** | per re-probe findings | top live+geocoded / live+address-only metros | P0 | DoD per city; dashboard wiring |

Contingency swaps: if a W1 feed dies between probe and build, fall back to the
next-ranked Tier-1/2 re-probe finding.

---

## 6 · Orchestration mechanics (unchanged)

1. Re-probe every dataset ID for the wave's cities (≤72 h stale allowed).
2. `python scripts/interlock_gap.py <base>` — require projected spine-share
   ≤20% for city waves.
3. Dispatch leaves; record claims in `.streams/`.
4. On each leaf completion: orchestrator applies the serial spine delta →
   `pytest -m interlock` → full suite → integrator doc/dashboard updates →
   commit if policy allows.
5. Close-out: yield row, scorecard update, model-refresh trigger.

---

## 7 · Model and alerting gates (unchanged)

New metros ship `alert_enabled=false` ("calibrating"); flip to `true` after
≥60 d of features with walk-forward pinball p50 within ±10% of pooled
baseline **and** LIMS decile spread ≥0.5× pooled spread. Every retrain
includes new cities as H3-7 spatial-block holdouts.

---

## 8 · Risk register

| # | Risk | Mitigation |
|---|---|---|
| R1 | Feed retires/pauses between probe and build (LA/KC precedent) | §3 re-probe ≤72 h before wave; Wave-R weekly monitor |
| R2 | Geocode recovery < G5 floor for a new city's address density | capture geocode-success sample in probe, not just "address present" |
| R3 | Portal platform unknown (CKAN/custom) | Phase-0 resolves platform before committing a wave; add client only if needed |
| R4 | Concurrent-spine torn write | serial holds, ≤2 streams, interlock per edit |

---

## 9 · Runbooks

### 9.1 Register-a-city (per stream, condensed)
1. Claim `.streams/city-<id>.md`; re-probe IDs; capture ≥1 fixture row/feed.
2. Leaf: `cities/<city>.py` (METRO_BBOX, DIVISION_BBOXES, DIVISIONS,
   SUBMARKETS). Set `needs_geocode=True` on address-only feeds.
3. Serial spine: enum, aliases, REGISTRY entry, config endpoints, `field_map`.
4. Gates G1–G10; integrator README/dashboard row + byte-synced `index.html`.

### 9.2 Weekly staleness probe (reuse existing)
`scripts/feed_staleness_probe.py` already emits per-feed age; extend to new
feeds at registration.
