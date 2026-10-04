# NYC permit source validation

Observed and recorded 2026-10-03 UTC from the existing bounded source audit and publisher dataset metadata for `nyc / permits`, Socrata dataset `ipu4-2q9a`. Endpoint: <https://data.cityofnewyork.us/resource/ipu4-2q9a.json>. Contract version: `1.0.0`; machine-readable status is in [nyc-permit-source-contract.json](nyc-permit-source-contract.json).

## Evidence inspected

- Dataset metadata identifies “DOB Permit Issuance,” attributes the feed to NYC Department of Buildings, and describes one row per permit/work type. Publisher description says the dataset is updated daily and existing records change as approval status changes. It also states newer permits are issued through DOB NOW, so this dataset has an explicit coverage limitation.
- A bounded explicit projection succeeded with `$select=:id,:updated_at,permit_si_no,job__,issuance_date,dobrundate`. Three rows had distinct `:id` and `permit_si_no` values, issuance dates in June 2020, and the same general May 2026 system-update period. This shows event time and update time differ; it does not prove global uniqueness or update semantics.
- A bounded count returned 3,990,806 rows. This is a sizing observation, not a validated row total or complete snapshot guarantee.
- A scoped query for `job__=340733647` returned permits `3765466` and `3763757` with matching job/document/sequence/type values. Therefore `job__` is ambiguous as a permit identity. The serial `permit_si_no` remains only a candidate identity pending a complete null/uniqueness check.
- An unrestricted `:id,:updated_at,*` query returned HTTP 400. Keep the adapter projection explicit and restricted to the contract's listed fields. Current metadata names the coordinate columns `gis_latitude` and `gis_longitude`; they are included in the contract, though this audit did not fetch their values.
- A full distinct-ID aggregate and an ordered update-time query timed out. No full 3.99-million-row download was attempted. Estimated source-query cost is unavailable.

The fixture under `apps/api/tests/fixtures/ingestion/nyc-permits.json` keeps the sample projection and duplicate-job observation in separate sections because they came from separate bounded queries; it does not fabricate a combined source row. It excludes names, phone numbers, street addresses, and unrelated personal columns. GIS columns are part of the current safe projection based on dataset metadata, but were not present in the bounded samples.

## Acquisition strategy in code

`SocrataPermitSource` sends an explicit `$select`, orders by `:updated_at,:id`, and uses a lexicographic keyset cursor so rows sharing a timestamp can continue by row ID. A declared inclusive update-time upper bound is applied to each page. It follows a full page with another request; only a short or empty page establishes exhaustion of the requested query scope. Request retries are bounded (429, 5xx and network timeouts). Missing identity/update/row IDs, repeated business identities, and out-of-order page boundaries fail the acquisition.

A bounded query reaching exhaustion is not marked as a full reconciliation. The contract remains not ready: `SourceContract.assert_ready()` rejects every required guarantee whose status is not `verified`. Thus live collection must remain disabled until evidence establishes the publisher behavior represented in the contract.

## Unresolved M1 gates

- Check `permit_si_no` nullability and uniqueness across a complete validated extraction or authoritative publisher guarantee; determine whether it survives release replacement.
- Verify `:id` persistence, `:updated_at` precision/filtering and which corrections/status/geometry changes advance it.
- Exercise adjacent publisher pages at equal timestamps and prove ordering/cursor behavior; the ordered request currently timed out.
- Establish snapshot consistency under concurrent source changes, a complete reconciliation method, deletion and replacement visibility, and a tested tombstone policy.
- Confirm page/request ceilings, application-token needs, quota and rate-limit behavior; measure bounded bootstrap/reconciliation time, bytes, retries and cost.
- Assess DOB NOW coverage separately. This BIS-issued-permits feed cannot provide estimated cost and is insufficient for the broader dashboard capex/LIMS features.

Until these items are resolved by reproducible evidence, source readiness is intentionally false. No live completeness, deletion, quota, or cost guarantee is asserted here.
