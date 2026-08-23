"""LLM/agent-facing documentation generators (llms.txt, llms-full.txt, robots.txt)."""

_SERVICE_NAME = "Urban Signal"
_VERSION = "2.0.0"
_BASE = "http://localhost:8000"


def get_llms_txt() -> str:
    """Concise llms.txt index pointing agents at key resources."""
    return f"""# {_SERVICE_NAME}

> Real-Time Spatial Intelligence & Commercial Catalyst Forecasting Engine.
> REST API for multi-horizon commercial real estate appreciation forecasts over H3 hexagonal grids,
> powered by Kafka municipal ingestion (permits, 311 complaints, SLA licenses, deeds) and ONNX inference.
> Cities supported: New York City (nyc), Chicago (chicago), San Francisco Bay Area (san_francisco).

Core concepts:
- LIMS Score: 0-100 momentum score for a location's commercial appreciation outlook.
- Multi-horizon deltas: expected value change at 6 months (p10/p50/p90 quantiles), 12-month spatial spillover, and 18-month macro outperformance probability.
- Catalyst: an H3 cell flagged high-momentum (default threshold LIMS >= 85).
- H3 resolution: 7 (coarse) to 9 (fine); all spatial queries accept latitude/longitude or an h3_index.

## Service

- [Interactive Dashboard]({_BASE}/dashboard): browser geospatial visualization (HTML).
- [OpenAPI Schema]({_BASE}/openapi.json): machine-readable full API contract.
- [Swagger UI]({_BASE}/docs): interactive API explorer.
- [Full LLM Documentation]({_BASE}/llms-full.txt): complete endpoint reference with parameters, payloads, and examples.
- [Health Check]({_BASE}/health): liveness/readiness status JSON.

## API v1 Endpoints (prefix: /api/v1)

- [Cities]({_BASE}/api/v1/cities): GET catalog of supported metropolitan regions.
- [Submarkets]({_BASE}/api/v1/submarkets?city_id=nyc): GET submarket metadata, filterable by borough/division.
- [Divisions]({_BASE}/api/v1/spatial/divisions?city_id=nyc): GET boroughs/divisions for a city.
- [Predict]({_BASE}/api/v1/predict): POST multi-horizon forecast for a coordinate or H3 cell.
- [Batch Predict]({_BASE}/api/v1/predict/batch): POST forecasts for many cells at once.
- [Catalysts]({_BASE}/api/v1/catalysts?city_id=nyc): GET current top high-momentum catalyst clusters.
- [Grid GeoJSON]({_BASE}/api/v1/grid?city_id=nyc): GET H3 hex grid as GeoJSON FeatureCollection.
- [Submarket Prediction]({_BASE}/api/v1/predictions/submarket/{{name}}): GET forecast for a named submarket.
- [Dashboard Metrics]({_BASE}/api/v1/dashboard/metrics?city_id=nyc): GET aggregated city statistics.
- [Hex Features]({_BASE}/api/v1/hex/{{h3_index}}/features): GET raw spatio-temporal features for one H3 cell.

## Optional

- [Prometheus Metrics]({_BASE}/metrics): operational telemetry (scrapers only).
"""


def get_llms_full_txt() -> str:
    """Complete endpoint reference with parameters, payload schemas, and examples."""
    return f"""# {_SERVICE_NAME} — Full API Reference

> Version {_VERSION}. Base URL shown in examples: `{_BASE}`.
> All responses are JSON unless noted. Errors return `{{"error": true, "status_code", "detail", "message", "service", "timestamp"}}`.
> Content negotiation: `GET /` returns the HTML dashboard when `Accept: text/html`, otherwise service metadata JSON.

## Authentication

None. The service is unauthenticated by design for internal deployment.

## Health & Operations

### GET /health
Liveness + readiness combined.
Response: `{{"status": "healthy", "service", "version", "environment"}}`

### GET /ready
Readiness probe. Response: `{{"ready": true, ...}}`

### GET /live
Liveness probe. Response: `{{"live": true, ...}}`

### GET /metrics
Prometheus exposition format (text). Counters: `prediction_requests_total`, `catalyst_alerts_emitted_total`. Histogram: `inference_latency_seconds`.

---

## API v1 (all paths below are prefixed with /api/v1)

### GET /cities
Catalog of supported metropolitan regions.
Example: `curl {_BASE}/api/v1/cities`
Response: `{{"count": <int>, "cities": [{{"city_id", "name", "divisions": [...]}}, ...]}}`

### GET /submarkets
Submarket metadata (name, borough/division, centroid lat/lng, base_lims, capex, permit_velocity, shift_ratio_311, sla_new_filings_90d, description).
Query params:
- `city_id` (string, optional; one of `nyc`, `chicago`, `san_francisco`/`sf`; default `nyc`)
- `borough` (string, optional; division/borough name filter)
Example: `curl "{_BASE}/api/v1/submarkets?city_id=san_francisco&borough=EAST_BAY"`
Response: `{{"city_id", "count", "borough", "submarkets": {{"<Name>": {{...meta}}}}, ...}}`

### GET /spatial/divisions
Boroughs/divisions for a city.
Query params: `city_id` (as above).
Response: `{{"city_id", "count", "divisions": [{{key, label, ...}}], }}`

### POST /predict
Multi-horizon appreciation forecast for one location.
Request body (application/json):
- `h3_index` (string, optional) OR `latitude` + `longitude` (numbers, optional) — one form required
- `resolution` (int, 7-9, default 9) — H3 resolution used to map coordinates to a cell
- `include_shap` (bool, default true) — attach SHAP feature attributions
Example:
```
curl -X POST {_BASE}/api/v1/predict \\
  -H 'Content-Type: application/json' \\
  -d '{{"latitude": 40.7580, "longitude": -73.9855, "resolution": 9, "include_shap": true}}'
```
Response fields:
- `h3_index`, `resolution`, `centroid_lat`, `centroid_lng`
- `lims_score` (0-100 momentum)
- `delta_6m_p10` / `delta_6m_p50` / `delta_6m_p90` (6-month value-change quantiles)
- `delta_12m_spillover` (12-month spatial spillover effect)
- `prob_18m_macro_outperformance` (probability, 0-1)
- `is_catalyst` (bool), `shap_attributions` (dict feature->weight, nullable), `inference_latency_ms`

Errors: 400 if neither h3_index nor lat/lng provided, or coordinates out of bounds.

### POST /predict/batch
Same as /predict but takes a JSON array of PredictionRequest objects. Invalid entries are skipped (no error).
Example:
```
curl -X POST {_BASE}/api/v1/predict/batch \\
  -H 'Content-Type: application/json' \\
  -d '[{{"h3_index": "892a100d5dfffff"}}, {{"latitude": 37.7749, "longitude": -122.4194}}]'
```
Response: JSON array of prediction objects (same schema as /predict).

### GET /catalysts
Top high-momentum catalyst clusters for a city.
Query params:
- `city_id` (optional, default nyc)
- `min_lims` (float 0-100, default 85)
- `resolution` (int 7-9, default 9)
- `borough` (optional filter)
- `limit` (int 1-500, default 50)
Example: `curl "{_BASE}/api/v1/catalysts?city_id=nyc&min_lims=88&limit=10"`
Response: `{{"city_id", "count", "threshold", "borough", "catalysts": [<prediction> + "submarket", "borough", "city_id"]}}`

### GET /grid
GeoJSON FeatureCollection of H3 hex polygons with prediction properties, covering city submarkets.
Query params:
- `city_id` (optional, default nyc)
- `resolution` (7-9, default 9), `k_ring` (0-3, default 1) — cells generated around each submarket center
- `borough`, `submarket` (optional filters; 404 if named submarket unknown)
- `include_shap` (bool, default false)
Response: standard GeoJSON `FeatureCollection`; each Feature has Polygon geometry (H3 cell boundary) and properties merged from features + prediction (`submarket`, `borough`, `city_id`, `lims_score`, deltas, etc.).

### GET /predictions/submarket/{{name}}
Forecast + metadata for a named submarket (e.g. `SoHo`, `Hudson Yards`, `Mission District`). Name lookup is case-insensitive across cities when `city_id` omitted.
Query params: `city_id` (optional), `include_shap` (default true), `resolution` (7-9, default 9).
Errors: 404 if unknown submarket.

### GET /dashboard/metrics
Aggregated stats for a city: submarket count, division count, average LIMS, total capex, top submarket, top-5 momentum list.
Query param: `city_id` (default nyc).

### GET /hex/{{h3_index}}/features
Raw spatio-temporal features for one H3 cell (capex_density_decayed, permit_velocity, shift_ratio_311, sla_new_filings_90d, lims_score, ...) plus centroid and boundary polygon.
Path param: valid H3 index. Query param: `resolution` (7-9, default 9).

---

## Machine-Readable Contract

FastAPI auto-generates the canonical OpenAPI 3.1 schema at `{_BASE}/openapi.json`.
Prefer it for typed client generation; this file is a human/LLM-oriented summary.

## Conventions

- All city-scoped endpoints accept `city_id`; invalid values return HTTP 400 listing supported cities.
- LIMS values supplied or returned in [0, 1] are normalized to a [0, 100] scale.
- Timestamps are UTC ISO-8601.
"""


def get_robots_txt() -> str:
    """Permissive robots policy welcoming AI agents, excluding ops-only endpoints."""
    return f"""# {_SERVICE_NAME} v{_VERSION} — robots.txt
# Agents and LLM crawlers are welcome. Start with /llms.txt for an overview
# or /llms-full.txt for the complete API reference.

User-agent: *
Allow: /
Disallow: /metrics

# Explicitly welcomed AI/LLM crawlers
User-agent: GPTBot
Allow: /
Disallow: /metrics

User-agent: OAI-SearchBot
Allow: /
Disallow: /metrics

User-agent: ChatGPT-User
Allow: /
Disallow: /metrics

User-agent: ClaudeBot
Allow: /
Disallow: /metrics

User-agent: Claude-Web
Allow: /
Disallow: /metrics

User-agent: anthropic-ai
Allow: /
Disallow: /metrics

User-agent: Google-Extended
Allow: /
Disallow: /metrics

User-agent: Applebot-Extended
Allow: /
Disallow: /metrics

User-agent: PerplexityBot
Allow: /
Disallow: /metrics

User-agent: cohere-ai
Allow: /
Disallow: /metrics

Sitemap: none
"""
