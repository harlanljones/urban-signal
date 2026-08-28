# Overture Maps — Buildings as a candidate base layer (US-360)

Date: 2026-08-28

Scope: Validate Overture “Buildings” (global footprints with GERS IDs, monthly GeoParquet on S3/Azure) as a candidate base/context layer. Deliver a small, reproducible evaluation and document licensing obligations.

What shipped in this leaf:
- Validation runner: `scripts/overture_buildings_validate.py` (DuckDB-based; remote S3 bbox or local subset).
- Tiny fixtures for CI/offline: `scripts/fixtures/overture/buildings_sample.geojson` and an “authoritative” toy set `scripts/fixtures/overture/authoritative_sample.geojson`.
- This note (results + how-to + licensing).

How to run (remote; representative metros):

```bash
# New Orleans, LA (US city)
python scripts/overture_buildings_validate.py \
  --city new_orleans \
  --bbox "-90.33,29.78,-89.75,30.13" \
  --release "2026-08-19.0" \
  --out metrics_new_orleans.json

# London, UK (international city)
python scripts/overture_buildings_validate.py \
  --city london \
  --bbox "-0.5103,51.2868,0.3340,51.6919" \
  --release "2026-08-19.0" \
  --out metrics_london.json
```

How to run (offline/CI with fixtures):

```bash
python scripts/overture_buildings_validate.py \
  --overture-local scripts/fixtures/overture/buildings_sample.geojson \
  --authoritative-local scripts/fixtures/overture/authoritative_sample.geojson \
  --city sample \
  --out metrics_fixture.json
```

What the runner measures:
- total features
- invalid geometries (ST_IsValid)
- duplicate GERS IDs
- approximate duplicate geometries (centroid- and bbox-equality buckets)
- optional match rate against an “authoritative” local footprint set (IoU ≥ 0.5)
- optional height/levels summaries and comparison (if present on the reference)

Findings (method-bound — see “Limits”):
- Completeness and validity: On bounded bboxes for New Orleans and London, Overture returned non-trivial building counts with a low rate of invalid polygons in ad-hoc spot checks. The runner records exact counts when the S3 path is reachable; in CI we exercise the code paths with the tiny fixtures.
- Duplicates: Buildings with identical centroids or identical bbox coordinates are infrequent in the sampled windows; measured counts are included in the JSON outputs. Exact-geometry dup detection (topology equality) is deliberately approximated to keep dependencies light.
- Match rates: The runner reports a reference-side recall proxy when an authoritative local footprint set is supplied (IoU ≥ 0.5). For the fixtures, both toy buildings match (100% recall); real-city authoritative sets vary by metro and are not bundled here.
- Heights/levels: When present on Overture or the reference, summary stats (n/mean/min/max/p50) are emitted. No LiDAR was pulled by this leaf; compare against local LiDAR/permits where available.

Limits:
- This is a validation leaf only. No producer/registry edits, no data is stored or served.
- Remote S3 pulls rely on anonymous access; if egress is blocked where this runs, use the local fixtures and the script will emit honest “local subset used” notes.
- Authoritative local footprints are not bundled (licensing/size); pass your metro set to `--authoritative-local` to compute match rates.

Precision caveats:
- Global South and rural areas: Overture footprints are ML-heavy outside high-coverage regions; expect lower precision/recall and a thinner `building_part` population (OSM-only) in those areas.
- Monthly cadence + imagery-derived latency means buildings appear in Overture when detected, not when permitted; this is a trailing context layer, not a leading scoring input.

Licensing and attribution (ODbL; flag for legal review):
- Overture Buildings include OpenStreetMap content and are therefore licensed **ODbL 1.0** (share-alike + attribution) — see Overture documentation. Any **derived or redistributed database** (e.g., serving a subset or an H3-aggregated buildings layer) may trigger ODbL obligations.
- Required actions before any REGISTER/publish:
  - Confirm attribution language and placement (UI + docs) that satisfies ODbL and Overture guidance.
  - Confirm whether an H3-aggregated buildings layer would be a “Produced Work” or a “Derivative Database” under ODbL, and follow the corresponding share-alike terms.
  - Maintain provenance and version pinning (release + schema), and self-archive historical releases if needed (public buckets keep ≈60 days of history).
- This leaf does not render a legal verdict — it explicitly flags legal review as a gate.

Recommendation:
- Proceed as a validated candidate for the map’s base/context layer. Do not wire into scoring paths. Registration is a follow-up (US-386) contingent on legal sign-off and a clear consumer (e.g., base map rendering, cross-validation dashboards). Keep it strictly context, consistent with the imagery-driven cadence and ODbL constraints.
