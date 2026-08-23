# Stream log — new-orleans-austin — 2026-08-23

## Claim

- **Stream id:** `new-orleans-austin`
- **Leaf files I will create/edit:**
  - `.streams/new-orleans-austin.md` (this file)
  - `docs/research/new-orleans-austin-verification.md`
- **Spine files I expect to need:** none

## Intent

Deepen NOLA (`data.nola.gov`) and Austin (`data.austintexas.gov`) from
"candidate" to "implementation-ready": fresh live probes of every candidate feed,
resolve the NOLA permits staleness question, assess NORA Sold Properties honestly,
search Austin harder for licenses/deeds, map each feed onto the shared producers'
fallback chains to name the exact new fallbacks needed, surface-level checks of
nearby domains, and deliver an implementation plan + build order in
`docs/research/new-orleans-austin-verification.md`. Research-only: no source edits.

## Decisions

- 2026-08-23 (start) — Read prior survey, city_registry.py, all four producers'
  parse_socrata_row chains, socrata_client.py, config.py endpoint names,
  seattle.py structure names. Probe shape: `<resource>.json?$limit=1`,
  `$select=count(*)`, `/api/views/<id>.json` for rowsUpdatedAt/columns, newest-row
  `$order=<watermark> DESC`.
- **NOLA permits staleness RESOLVED:** old feed `nbcf-m6c2` is dead-stale (last
  permit 2024-12-05; zero 2025+ rows; rowsUpdatedAt frozen 2025-08-17), but it was
  SUPERSEDED, not abandoned: `rcm3-fn58` ("Permits") is live (rowsUpdatedAt
  2026-08-23), carries 346k rows covering 2012→2026-08-22 continuously, fully
  geocoded via `location_1` (zero nulls). Register rcm3-fn58 instead.
- **NORA verdict:** still updating (max sale_date 2026-07-22) but tiny: 5,618 rows
  over 46 years, only 872 since 2020, no price column at all. Register optionally
  under FeedType.DEEDS with a King County-style caveat comment; low priority.
- **Austin 311 "(verify)" resolved:** xwdj-i9he has explicit `sr_location_lat` /
  `sr_location_long`; null rate 0.59% (14,972 / 2.53M). Usable.
- **Austin catalog finding:** data.austintexas.gov has EXITED the Socrata discovery
  mesh (domain query returns only 3 internal "ODP Dashboard" analytics datasets;
  even q=permits → 0). Domain resources still serve fine. Licenses/deeds absence
  confirmed by 11 failed queries + structural explanation (Texas Open Data Portal
  migration).
- **Nearby-domain sweep:** TABC statewide alcohol licenses exist on data.texas.gov
  (`7hf9-qc9f` upd 2026-08-22, `kguh-7q9z` upd 2026-08-23) but carry NO geocodes —
  not registration-ready. Travis County Socrata is a FedRAMP shell ("Domain not
  found", homepage 301) — dead end. No Louisiana statewide Socrata resolves.
- Fallback count finalized: ~26 new `or row.get(...)` fallbacks across 6 feeds →
  the per-city field-mapping-table refactor trigger FIRES.

## Current step

Writing `docs/research/new-orleans-austin-verification.md`.

## Next step

Done pending orchestrator review: both leaf files complete.
