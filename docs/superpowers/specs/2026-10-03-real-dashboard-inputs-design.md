# M5 — Integrate real dashboard inputs

Date: 2026-10-03. Status: proposed. Dependencies: M4 passes; required feeds, feature semantics and model readiness verified for each promoted scope.

## Purpose and release boundaries

Expose trustworthy municipal data in the Cloudflare dashboard with truthful provenance and reversible publication. Start with source-backed permit metrics for NYC. Promotion of prediction/LIMS features is a separate gate within this milestone: it requires all features used by the model, authoritative cost data where needed, and a validated model bundle. Permit-only success cannot authorize complete predictive claims.

## Feature and model contract

Define a versioned feature manifest linking committed source manifests, city/feed coverage, source freshness, explicit UTC as-of, schema/parser/feature versions, missingness and completeness. Snapshot export consumes this manifest instead of regenerating promoted inputs from registry defaults. Unpromoted cities retain their current path with explicit baseline/synthetic provenance; never silently mix a real permit metric with invented companion inputs and label the prediction source-backed.

For prediction promotion establish additional permit/cost, 311, licensing and deeds sources according to the actual feature contract. Specify units, geography, temporal joins and cost deduplication. Validate training/validation data provenance, temporal leakage controls, out-of-time performance, uncertainty/calibration and metric thresholds before selecting a production model. Those thresholds require a separate evidence-backed model decision; synthetic boot-time weights cannot satisfy it.

A model bundle fixes feature order/default semantics, preprocessing, serialized weights, SHAP background/configuration, calibration, versions and hashes. Loading must fail clearly for a mismatched bundle/feature schema. Missing inputs are not silently zero-filled unless the validated contract explicitly permits it and product provenance remains accurate.

## Dashboard behavior

Show separate snapshot time, feature as-of and source freshness where users assess a metric. Distinguish source-backed, baseline/synthetic, stale and unavailable values. Unsupported metrics display an explanation rather than a misleading zero. Preserve HTTP/MCP response compatibility through additive fields or an explicit schema-version release. Existing overlay context retains its own provenance.

Build and validate a complete candidate snapshot before activation. Stage the compatible reader before new data/schema. Use a publication mechanism with demonstrated consistency and rollback; do not assume multi-key KV writes form an atomic transaction. If the current publisher cannot guarantee acceptable activation behavior for the new contract, implement and test a versioned candidate/pointer scheme as a separately planned prerequisite. Retain the prior data/model bundle for rollback.

## Acceptance

- NYC source-backed permit metrics match validated M4 features and have truthful provenance/missingness.
- Full predictions remain gated until required sources and model validation pass; release reports distinguish metric and prediction promotion.
- Coverage, ranking, SHAP, model/feature compatibility, HTTP/MCP contracts and byte-synced dashboard checks pass.
- Production-URL visual checks cover 2D/3D zoom, rapid reversals, city navigation and stale/unavailable display states.
- Interrupted publication cannot expose an unsupported mixed contract; reader-first deployment and prior-version rollback are rehearsed.
- Monitoring separates upstream staleness, acquisition failures and serving failures. A failing scope retains a known valid version without disguising its age.

Registry coverage remains 157 cities until a separately verified change; NYC readiness does not establish real ingestion for every registered city.
