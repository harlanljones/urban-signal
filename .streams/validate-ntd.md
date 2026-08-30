# Stream log — validate-ntd — 2026-08-30

Copy this file to `.streams/<stream-id>.md` as your FIRST action (phase 1,
Claim) and update it at every step boundary. Commit it with your work.
Its absence is what makes a takeover cost twelve tool calls instead of one.

## Claim

- **Stream id:** `validate-ntd`
- **Leaf files I will create/edit:** `docs/research/ntd-transit-gtfs-validation.md`
  (required) + optional leaf module `apps/api/src/spatial/ntd_transit.py` and
  unit test `apps/api/tests/unit/test_ntd_transit.py` if a rollup helper is
  proven feasible. This `.streams/validate-ntd.md` is a leaf log file.
- **Spine files I expect to need:** none. This is a signal-VALIDATION task
  (Linear US-172). No registry/enums/producers/submarkets edits are needed;
  the deliverable is a research/validation document and, only if warranted, a
  self-contained leaf module with its own unit test that imports no spine
  symbols.

## Intent

Validate the FTA National Transit Database (NTD) as a metro-level transit
demand/service-context signal for Urban Signal. Establish the source's product
structure (monthly ridership/safety, annual data, monthly-updated GTFS
weblinks), access path (Socrata mirror on data.transportation.gov), freshness,
agency→metro crosswalk feasibility, and whether GTFS route/stop geometry maps
onto the repo's H3 7–9 grid. Probe five registered metros live (WMATA/DC,
CTA/Chicago, MBTA/Boston, SF Muni/San Francisco, King County/Seattle), verify
feed availability + staleness + spatial coverage, and decide ADOPT / DEFER /
REJECT. No feed is registered; no spine file is touched.

## Decisions

- 2026-08-30 — Claimed stream. transit.dot.gov is Akamai-blocked (HTTP 403 to
  scripted clients incl. browser UA); the NTD data is instead reachable through
  the FTA's Socrata mirror `data.transportation.gov` (HTTP 200). Monthly
  ridership = `Complete Monthly Ridership (with Adjustments and Estimates)`
  (8bui-9xvu) through **2026-06-01** for all five probed metros; GTFS weblinks =
  `General Transit Feed Specification Weblinks` (2u7n-ub22), monthly refreshed.
- 2026-08-30 — Live probes: MBTA / King County / CTA / SF Muni GTFS weblinks
  are live anonymous zips (HTTP 200); WMATA's weblink is API-gated (HTTP 401
  without a WMATA API key) — the ticket's "stale/incomplete weblinks" risk is
  real for at least one major metro. GTFS stops map cleanly to H3 (MBTA 8,609
  of 9,642 stops inside the Boston metro bbox).
- 2026-08-30 — Conclusion: **DEFER** as a registered feed. NTD is a rich,
  fresh, standardized national transit source with a clean machine path and
  clean H3 mapping, but it is a **trailing aggregate/level** signal (agency+UZA
  rollup, ~1–2-month lag, annual service data), not a per-event stream; a feed
  registration would need a new `FeedType` + bulk-synthesis producer (Socrata
  is reachable but NTD rows are not the event/watermark shape the
  `PaginatingClient` contract assumes), which is a spine/interlock change out
  of scope for this leaf. A leaf module proving stop→H3 + ridership-delta
  rollup is included; wiring is not.

## Current step

Phase 3 WRITE complete: `docs/research/ntd-transit-gtfs-validation.md` written,
leaf module `apps/api/src/spatial/ntd_transit.py` + unit test
`apps/api/tests/unit/test_ntd_transit.py` added, **9/9 tests pass** with the repo
venv (`apps/api/.venv/bin/pytest tests/unit/test_ntd_transit.py -q`).

## Next step

Report verdict to the ticket. No spine file was touched; working tree left dirty;
nothing committed or pushed.
