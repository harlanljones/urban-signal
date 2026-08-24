# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Urban Signal serves two primary audiences:

- prospective users, partners, and investors evaluating whether the system offers credible, useful spatial intelligence;
- technical evaluators and contributors who need to understand how municipal records become spatial features, forecasts, and dashboard experiences.

## Product Purpose

Urban Signal turns leading municipal telemetry—permits, 311 complaints, licenses, deeds, and related public records—into multi-city spatial intelligence. It normalizes city-specific feeds, assigns events to a multi-resolution Uber H3 grid, computes interpretable momentum features, and supports forecasts of commercial and property-market change ahead of conventional lagging indicators.

The marketing and learning experience should let both audiences understand the product deeply, inspect how it works, and reach the live dashboard quickly.

## Positioning

Unlike a conventional property dashboard built mainly from completed transactions, Urban Signal uses the operational exhaust of cities as leading evidence: heterogeneous public records are normalized into a shared spatial and temporal system, then processed into explainable signals and multiple forecast horizons.

## Operating Context

Visitors evaluate the project through a public product site, a live geospatial dashboard, city-specific source documentation, repository code, architecture explanations, and API behavior. The learning path must support both a fast credibility scan and deeper technical exploration without splitting those audiences into separate experiences.

## Capabilities and Constraints

- Seventeen metros are currently registered: New York City, Chicago, San Francisco Bay Area, Seattle, Los Angeles, New Orleans, Norfolk, Detroit, Austin, Cincinnati, Boston, Baltimore, Montgomery County, Baton Rouge, Denver, Philadelphia, and Washington DC. The city registry remains authoritative; the marketing build verifies its machine-readable city projection against that registry.
- Feed coverage varies by city. Missing or incomplete municipal sources must be described honestly; the site must never imply uniform four-feed coverage.
- Processing spans source-specific Socrata, ArcGIS, Carto, and CKAN ingestion; schema normalization; Kafka event streams; H3 spatial enrichment; time-decayed feature aggregation; PostGIS and object storage; multi-horizon model training and ONNX inference; snapshots; and edge delivery.
- The city registry and dashboard wiring are authoritative for which cities appear in the product.
- The marketing site will be a standalone web app inside the existing Turborepo, separate from `apps/product`.
- Product and model claims must remain traceable to repository evidence. Do not invent customers, performance results, testimonials, or commercial availability.
- Machine readers can discover a concise guide at `apps/dashboard/public/llms.txt`, expanded context at `apps/dashboard/public/llms-full.txt`, and structured product facts at `apps/dashboard/public/facts.json`.

## Brand Commitments

- Product name: Urban Signal.
- Voice: technically exact, candid about source limitations, confident without overstating evidence, and generous with explanation.
- The overall product-site theme is thorough explanation made engaging through interactive UI and purposeful motion.

## Evidence on Hand

- `README.md` contains the product overview, registered-city matrix, architecture, mathematical formulations, model horizons, and dashboard screenshots.
- `src/spatial/city_registry.py` and `src/spatial/cities/` contain the city-level source and geography contracts.
- `src/producers/`, `src/consumers/`, `src/features/`, `src/models/`, `src/storage/`, `src/serving/`, and `src/export/` contain the processing implementation.
- `docs/screenshots/` contains real dashboard captures.
- `docs/research/` records source discovery and known gaps.
- No customer testimonials, adoption metrics, or independently validated forecast-performance claims are currently on hand; future work must not fabricate them.

## Product Principles

1. Show the evidence trail: every important claim should lead to a source, transformation, formula, code path, or live behavior.
2. Reward both depths: make the system legible in minutes and genuinely explorable for visitors who stay.
3. Treat city differences as product truth: explain uneven public-data ecosystems instead of smoothing them into a false uniformity.
4. Make complexity navigable: use progressive disclosure and interaction to clarify the pipeline without trivializing it.
5. Prefer working proof: connect explanations to the live dashboard and repository wherever possible.

## Accessibility & Inclusion

The standalone site must support keyboard navigation, visible focus, semantic structure, reduced-motion preferences, readable contrast, and responsive layouts across mobile and desktop.
