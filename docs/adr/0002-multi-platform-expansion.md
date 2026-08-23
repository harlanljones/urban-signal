# ADR 0002: Multi-Platform Expansion Abstractions

**Status:** Proposed
**Date:** 2026-08-23
**Scope:** urban-signal
**Supersedes:** —
**Companion:** `docs/expansion-roadmap.md` (program plan, waves, metrics)

## Context

The 2026-08-23 coverage surveys verified 12 candidate metros across four data
platforms. Five cities are implementable with the existing Socrata/ArcGIS
clients, but Philadelphia publishes only through CARTO's SQL API, Boston only
through CKAN, Washington DC slices permit/311 layers **per calendar year**,
and Baton Rouge's business registry is a snapshot with **no watermark column**.
Philadelphia's date fields additionally carry sentinel values (years 3200 and
9798) that would poison watermark queries.

Scaling to 17 cities by growing shared `or row.get(...)` fallback chains was
already rejected — the per-city field-mapping table shipped first (Wave B,
`src/producers/field_maps.py`) after its trigger fired at four cities needing
non-trivial spellings.

## Decision

Four bounded abstractions, each landing behind the existing interlock gate:

1. **Client routing becomes a dict dispatch.**
   `_client_for(meta)` (scheduler.py) currently special-cases `arcgis` over a
   default `socrata`. It becomes `{platform: client_attr}` with a readable
   error for unregistered platforms, so CARTO/CKAN clients plug in without
   further scheduler edits.

2. **Two new paginating clients as leaf modules.**
   `CartoClient` (est. 120–180 LOC; SQL keyset paging on
   `(updated_at, cartodb_id)`, sentinel-date exclusion in watermark queries)
   and `CKANClient` (est. 150–200 LOC; `datastore_search` offset paging,
   explicit rejection of non-datastore file resources, year-resource hook).
   Both are new files — leaf work; unit tests run against recorded payloads
   plus max-records-bounded live contract tests.

3. **Year-slice endpoints declared as data, resolved at poll time.**
   DC/Boston-style per-year layers enter via
   `DatasetSpec.extra["endpoint_by_year"]`; the scheduler resolves the current
   year's layer when a job starts and re-baselines its watermark metric on
   rollover. A frozen-clock staging drill runs every December 15 (runbook:
   expansion-roadmap §8.2). Rejected alternative: per-year manual config edits
   — guaranteed New Year outage.

4. **Snapshot ingestion mode for watermark-less registries.**
   `extra={"ingestion_mode": "snapshot"}` switches the producer from
   watermark-incremental to full-pull diff against stored ids. Gated on a 3-day
   ≤0.1% row-parity soak before the city's wave closes.

Field-specific column spellings continue entering exclusively as
`DatasetSpec.extra["field_map"]` data (ADR-0001-adjacent Wave B mechanism);
parser chains may grow at most ~6 terms program-wide.

## Consequences

- The four raw Kafka topics, H3 enrichment, storage, and serving stack are
  untouched; all deltas sit between the poller and the parsers.
- Every platform quirk surfaces as registry data or client-contract test, not
  parser branches: uppercase coordinates (`LATITUDE`), DateOnly strings,
  numeric yyyymmdd dates, sentinel dates, missing watermarks.
- Cost of admission for a new platform is one leaf client + one routing-dict
  entry, priced before any city commits to it (roadmap Wave F precedes C3–C6).
- Risk accepted: year-slice feeds need an annual operational drill; snapshot
  feeds trade incremental efficiency for full-pull id diffs.
