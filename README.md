# Urban Signal

> **Real-Time Spatial Intelligence & Commercial Catalyst Forecasting Engine via Multi-City Municipal Ingestion, Event Streaming (Apache Kafka), and Cloud-Native GPU Inference (Kubernetes).**

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Apache Kafka](https://img.shields.io/badge/Kafka-Strimzi%203.7-231F20.svg)](https://kafka.apache.org/)
[![Uber H3](https://img.shields.io/badge/Uber%20H3-Res%207%2F8%2F9-000000.svg)](https://h3geo.org/)
[![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-CUDA%20FP16-005CED.svg)](https://onnxruntime.ai/)
[![PostGIS](https://img.shields.io/badge/PostGIS-16--3.4-336791.svg)](https://postgis.net/)

## Dashboard

| San Francisco Bay Area | Parcel Inspector & SHAP Attribution |
| :---: | :---: |
| ![San Francisco Bay Area Dashboard](docs/screenshots/dashboard-san_francisco.png) | ![Parcel Inspector](docs/screenshots/dashboard-inspector.png) |

| New York City (5 Boroughs) | Chicago (6 Divisions) |
| :---: | :---: |
| ![NYC Dashboard](docs/screenshots/dashboard-nyc.png) | ![Chicago Dashboard](docs/screenshots/dashboard-chicago.png) |

---

## 1. System Overview & Architecture

Traditional real estate valuation models rely on lagging transactional comps (deeds, MLS closed transfers). **Urban Signal** ingests leading municipal telemetry—daily building permits (DOB A1/A2/NB / Demolitions), Liquor / Hospitality Licenses, 311 citizen maintenance & quality-of-life complaints, and property deeds / tax rolls across **New York City (5 Boroughs)**, **Chicago (6 Divisions)**, and the **San Francisco Bay Area (5 Divisions)**—streaming them through Apache Kafka onto an **Uber H3 multi-resolution hexagonal grid** (Res 7, 8, 9) to predict appreciation ($\\Delta \\ln(P)$) **6 to 18 months ahead of public market listings**.

```
+---------------------------------------------------------------------------------------------------+
|                        MUNICIPAL OPEN DATA INGESTION (Socrata SODA REST APIs)                     |
|         DOB Permits (A1/A2/NB) | 311 Complaints | SLA Liquor Licenses | ACRIS Property Deeds      |
+-------------------------------------------------+-------------------------------------------------+
                                                  | Ingest & Deduplicate
                                                  v
+---------------------------------------------------------------------------------------------------+
|                           KAFKA STREAMING & APICURIO SCHEMA REGISTRY                              |
|   raw.municipal.permits | raw.municipal.311 | raw.municipal.sla | raw.municipal.deeds | dlq.*     |
+-------------------------------------------------+-------------------------------------------------+
                                                  | Consume & Enrich (KEDA Autoscaled)
                                                  v
+---------------------------------------------------------------------------------------------------+
|                       STREAM CONSUMERS & SPATIO-TEMPORAL ENRICHMENT                               |
|   • H3 Spatial Normalization (Res 7 Macro, Res 8 Submarket, Res 9 Micro)                          |
|   • Time-Decayed CapEx Calculator (180-day half-life exponential decay)                           |
|   • 311 Complaint Shift Dynamics Ratio ((QoL + eps) / (Neglect + eps))                            |
|   • Leading Indicator Momentum Score (LIMS) [0..100]                                              |
|   • Enriched Stream Emitter (enriched.spatial.h3) & Alert Trigger (alerts.catalyst)               |
+------------------------+--------------------------------------------------+-----------------------+
                         |                                                  |
                         v                                                  v
+--------------------------------------------------+     +------------------------------------------+
| DATA & ANALYTICAL STORAGE                        |     | REAL-TIME INFERENCE & SERVING (FastAPI)  |
| • PostGIS 16 (GiST spatial & BRIN time indices)  |     | • Multi-Horizon ONNX Engine (<5ms CUDA)  |
| • DuckDB (Out-of-Core Aggregations)              |     | • 6m LightGBM Quantile Pinball (p10/50/90|
| • Polars (High-Performance DataFrames)           |     | • 12m ST-GNN (HexGCN + GRU Recurrence)   |
| • MinIO S3 (Parquet Features & Model Registry)   |     | • 18m DCN-v2 (Cross Network Ensemble)    |
+--------------------------------------------------+     | • TreeSHAP Catalyst Driver Attributions  |
                                                         | • Hardened MapLibre GL Dashboard         |
                                                         | • Webhook Alert Dispatcher & Prometheus  |
                                                         +------------------------------------------+
```

---

## 2. Mathematical Formulations

### Exponential Time-Decayed CapEx Density
$$\\text{CapEx Density}_{\\text{cell } h, t} = \\frac{1}{\\text{Area}(h)} \\sum_{i \\in \\mathcal{P}_{h, t}} \\text{Cost}_i \\cdot e^{-\\lambda (t - t_i)}, \\quad \\lambda = \\frac{\\ln(2)}{180\\text{ days}}$$
Where $\\mathcal{P}_{h, t}$ represents structural building alteration permits in cell $h$ over lookback window $t$, and $\\text{Area}(h)$ is the geodesic area in $\\text{km}^2$.

### 311 Shift Dynamics Ratio
Measures transition from structural landlord disinvestment complaints ($C_{\\text{neglect}}$: heat, water outages, pests) to commercial footfall / quality-of-life complaints ($C_{\\text{QoL}}$: noise, sidewalk sheds, dining):
$$\\Delta R_{311} = \\frac{C_{\\text{QoL}} + \\varepsilon}{C_{\\text{neglect}} + \\varepsilon}$$

### Leading Indicator Momentum Score (LIMS)
$$\\text{LIMS}_h = \\alpha \\cdot \\mathcal{Z}(\\text{CapEx}_h) + \\beta \\cdot \\mathcal{Z}(\\text{PermitVelocity}_h) + \\gamma \\cdot \\mathcal{Z}(\\Delta R_{311, h}) + \\delta \\cdot \\mathcal{Z}(\\text{Lic}_{\\text{SLA}, h})$$
- Default weights: $\\alpha=0.35, \\beta=0.25, \\gamma=0.20, \\delta=0.20$
- Normalized via logistic sigmoid projection to $[0.0, 100.0]$. Scores $\\ge 85.0$ emit real-time Catalyst Alerts to `alerts.catalyst`.

---

## 3. Multi-Horizon Machine Learning Architecture

| Horizon | Objective Function | Architecture Tier | Primary Output |
| :--- | :--- | :--- | :--- |
| **6-Month Micro** | Pinball Loss ($\\alpha = 0.1, 0.5, 0.9$) | `LightGBMQuantilePredictor` | Immediate parcel price/sqft inflection intervals |
| **12-Month Neighborhood** | Huber Loss / MSE | `SpatioTemporalGNN` (`HexGCNLayer` + `nn.GRUCell`) | Spatial spillover & corridor diffusion |
| **18-Month Macro** | Binary Cross-Entropy | `MultiScaleDCNv2` (`CrossNetworkV2` + Deep MLP) | Probability of $>15\\%$ structural outperformance |

### Spatial-Temporal Leakage Prevention Protocol
Standard random K-Fold CV creates severe spatial-temporal data leakage (training on building A while evaluating adjacent building B in the same month). Urban Signal enforces a **Rolling Walk-Forward Temporal Split** coupled with **H3-7 Spatial Cluster Block Holdouts** (entire H3-7 parent hexagons held out from training) to guarantee model generalization across unseen urban markets.

### Interpretability & Explainability
Parcel predictions incorporate **TreeSHAP** (`CatalystExplainer`) decompositions, mapping the relative percentage contributions of CapEx density, permit velocity, 311 shift ratio, and SLA license filings directly in the API response and geospatial dashboard.

---

## 4. Repository Structure

```
urban-signal/
├── deploy/
│   ├── docker/
│   │   └── docker-compose.dev.yml          # Local Kafka (KRaft), Schema Registry, PostGIS, MinIO, AKHQ
│   └── k8s/
│       ├── namespaces.yaml                 # 5 isolated cluster namespaces
│       ├── kafka/
│       │   ├── strimzi-cluster.yaml        # Strimzi 3-broker cluster & NVMe storage
│       │   └── kafka-topics.yaml           # KafkaTopic manifests with retention policies
│       ├── storage/
│       │   └── postgis-statefulset.yaml    # PostGIS 16 + GiST/BRIN indexing PVCs
│       ├── consumers/
│       │   └── keda-scaledobject.yaml      # KEDA autoscaling spatial consumer pods (1 -> 8)
│       └── inference/
│           └── inference-deployment.yaml   # FastAPI + ONNX Runtime (CUDA GPU)
├── models_storage/                         # Serialized ONNX model artifacts (DCN-v2, ST-GNN)
├── src/
│   ├── config.py                           # Central Pydantic Settings & environment config
│   ├── schemas/                            # Pydantic models & Avro binary schema contracts (.avsc)
│   ├── spatial/                            # Uber H3 indexing, graph Laplacians, GIS utilities
│   ├── features/                           # Time-decay, 311 shift dynamics, LIMS calculator, DuckDB
│   ├── producers/                          # Socrata scrapers (DOB, 311, SLA, Deeds) & Scheduler
│   ├── consumers/                          # Base Kafka consumer, H3 enrichment, aggregation, PostGIS
│   ├── storage/                            # PostGIS synchronization engine & table schemas
│   ├── models/                             # LightGBM, ST-GNN, DCN-v2, Walk-Forward CV, ONNX exporter
│   └── serving/                            # FastAPI app, inference engine, dashboard, webhooks
├── tests/
│   ├── conftest.py                         # Pytest fixtures & sample NYC geospatial payloads
│   ├── unit/                               # 10 unit test suites
│   └── e2e/                                # End-to-end integration test suite
├── pyproject.toml                          # Project packaging and dependency specifications
├── LICENSE                                 # Apache 2.0 Open Source License
└── urban_signal_prospectus_k8s_kafka.md    # Full technical design prospectus
```

---

## 5. Configuration & Environment Variables

All settings are managed via `src/config.py` using `pydantic-settings` and can be overridden via `.env` or container environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `development` | Environment mode (`development`, `staging`, `production`) |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `SERVICE_NAME` | `urban-signal-predictor` | Service identifier |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker endpoints (`kafka-cluster-kafka-bootstrap.kafka-streaming:9092` in K8s) |
| `KAFKA_SCHEMA_REGISTRY_URL` | `http://localhost:8081` | Schema Registry endpoint |
| `KAFKA_SECURITY_PROTOCOL` | `PLAINTEXT` | Security protocol (`PLAINTEXT`, `SASL_PLAINTEXT`, `SSL`) |
| `POSTGRES_HOST` / `PORT` / `DB` | `localhost` / `5432` / `urbansignal` | PostGIS database connection parameters |
| `POSTGRES_USER` / `PASSWORD` | `postgres` / `postgres` | PostGIS authentication credentials |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO S3 object storage endpoint |
| `MINIO_ACCESS_KEY` / `SECRET_KEY` | `minioadmin` / `minioadmin` | MinIO S3 credentials |
| `MINIO_BUCKET_FEATURES` | `urban-signal-features` | S3 bucket for feature partitions & model registry |
| `SOCRATA_APP_TOKEN` | `None` | Optional Socrata API token for elevated rate limits |
| `H3_RES_MACRO` / `NEIGHBORHOOD` / `MICRO` | `7` / `8` / `9` | Multi-resolution Uber H3 grid levels |
| `CAPEX_HALFLIFE_DAYS` | `180.0` | Half-life parameter ($\\lambda = \\ln(2)/180$) for CapEx time decay |
| `LIMS_THRESHOLD` | `85.0` | Minimum LIMS score triggering a Catalyst Alert |
| `ONNX_MODEL_DIR` | `./models_storage` | Local path to exported ONNX model files |
| `ONNX_EXECUTION_PROVIDER` | `CUDAExecutionProvider` | ONNX Provider (`CUDAExecutionProvider` or `CPUExecutionProvider`) |
| `WEBHOOK_ALERT_URLS` | `[]` | JSON array of URLs for real-time catalyst alert dispatching |

---

## 6. Quickstart & Local Development

### Prerequisites
- Python 3.11+ / 3.12 (`uv` or `pip`)
- Docker & Docker Compose
- NVIDIA GPU (Optional: CUDA Execution Provider accelerates inference to $<5\\text{ms}$)

### Setup & Installation
```bash
# 1. Clone repository & enter directory
git clone https://github.com/harlanljones/urban-signal.git
cd urban-signal

# 2. Create virtual environment and install dependencies
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

# 3. Launch local Kafka (KRaft), Schema Registry, PostGIS, MinIO & AKHQ
docker compose -f deploy/docker/docker-compose.dev.yml up -d
```

### Local UI Endpoints
- **AKHQ Kafka Visualizer:** [http://localhost:8080](http://localhost:8080)
- **Schema Registry:** [http://localhost:8081](http://localhost:8081)
- **MinIO S3 Console:** [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`)
- **FastAPI Interactive API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Geospatial Catalyst Dashboard:** [http://localhost:8000/dashboard](http://localhost:8000/dashboard)

---

### Running Ingestion Producers & Poller Scheduler

You can stream data using individual one-off producer runs or the continuous polling scheduler:

```bash
# Option A: Continuous Municipal Ingestion Scheduler (with deduplication & DLQ)
python -m src.producers.scheduler --jobs permits 311 sla deeds --interval 60 --limit 500

# Option B: Run individual one-off streams
python -m src.producers.dob_permits_producer --limit 2000
python -m src.producers.complaints_311_producer --limit 2000
python -m src.producers.sla_licenses_producer --limit 1000
python -m src.producers.deeds_acris_producer --limit 1000
```

---

### Running Stream Consumers & Background Workers

```bash
# 1. Spatial Enrichment Worker (H3 Res 7/8/9 join & DuckDB out-of-core sink)
python -m src.consumers.spatial_enrichment_worker

# 2. Feature Aggregator Worker (Publishes to enriched.spatial.h3 & alerts.catalyst)
python -m src.consumers.feature_aggregation_worker

# 3. PostGIS Spatial Sync Worker (Persists raw streams & features with GiST/BRIN indices)
python -m src.consumers.postgis_worker
```

---

### Model Retraining Pipeline

Execute the automated walk-forward cross-validation, ONNX export, and MinIO model artifact upload:

```bash
python -m src.models.retraining_job \
  --version v2.1 \
  --epochs-gnn 15 \
  --epochs-dcn 15 \
  --n-estimators-lgbm 100
```

---

### Launching the Real-Time Serving API & Dashboard

```bash
# Start FastAPI service with automatic hot-reloading
uvicorn src.serving.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 7. Cloud-Native Kubernetes (k3s / RKE2) Deployment

The platform is engineered for on-premises enterprise Kubernetes clusters using Strimzi and KEDA:

```bash
# 1. Provision isolated namespaces
kubectl apply -f deploy/k8s/namespaces.yaml

# 2. Deploy Strimzi Kafka cluster & topics
kubectl apply -f deploy/k8s/kafka/strimzi-cluster.yaml
kubectl wait --for=condition=Ready kafka/kafka-cluster -n kafka-streaming --timeout=300s
kubectl apply -f deploy/k8s/kafka/kafka-topics.yaml

# 3. Create database credentials & deploy PostGIS StatefulSet
kubectl create secret generic postgis-credentials \
  --from-literal=password=postgres \
  -n data-storage \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f deploy/k8s/storage/postgis-statefulset.yaml

# 4. Deploy KEDA autoscaling spatial consumer workers
kubectl apply -f deploy/k8s/consumers/keda-scaledobject.yaml

# 5. Deploy ONNX GPU inference service
kubectl apply -f deploy/k8s/inference/inference-deployment.yaml

# 6. Check cluster status
kubectl get pods -A -l "app in (urban-signal-inference-service, h3-enrichment-worker, postgis)"
```

---

## 8. API Reference

### Health & Probe Endpoints
- `GET /health` — General health check
- `GET /ready` — Kubernetes readiness probe
- `GET /live` — Kubernetes liveness probe

```json
{
  "status": "healthy",
  "service": "urban-signal-predictor",
  "version": "2.0.0",
  "environment": "development"
}
```

### Prometheus Metrics
`GET /metrics`
Exposes real-time Prometheus telemetry including `prediction_requests_total`, `catalyst_alerts_emitted_total`, and `inference_latency_seconds`.

### Interactive Geospatial Dashboard
`GET /dashboard` or `GET /` (with `Accept: text/html`)
Serves the hardened, high-performance **MapLibre GL** web visualizer featuring multi-city selection (San Francisco, NYC, Chicago), submarket filtering, H3 hexagon inspection, LIMS heatmaps, and SHAP attribution waterfall charts.

---

### Single Real-Time Prediction
`POST /api/v1/predict`
```json
{
  "latitude": 37.7749,
  "longitude": -122.4194,
  "resolution": 9,
  "include_shap": true
}
```
**Response ($p99 < 10\\text{ms}$):**
```json
{
  "h3_index": "8928308280fffff",
  "resolution": 9,
  "centroid_lat": 37.7749,
  "centroid_lng": -122.4194,
  "lims_score": 88.45,
  "delta_6m_p10": 0.0312,
  "delta_6m_p50": 0.0845,
  "delta_6m_p90": 0.1420,
  "delta_12m_spillover": 0.1650,
  "prob_18m_macro_outperformance": 0.8920,
  "is_catalyst": true,
  "shap_attributions": {
    "capex_density_decayed": 38.5,
    "permit_velocity": 24.2,
    "shift_ratio_311": 19.8,
    "sla_new_filings_90d": 17.5
  },
  "inference_latency_ms": 3.42
}
```

---

### Batch Multi-Cell Prediction
`POST /api/v1/predict/batch`
```json
[
  {"latitude": 37.7749, "longitude": -122.4194, "resolution": 9, "include_shap": true},
  {"latitude": 40.7233, "longitude": -74.0030, "resolution": 9, "include_shap": true}
]
```

---

### Submarket Catalog Discovery
`GET /api/v1/submarkets?city_id=san_francisco&borough=SAN_FRANCISCO_CORE`
Returns the catalog of commercial/residential submarkets across divisions with centroid coordinates, camera presets, and baseline momentum profiles.

---

### Active Catalyst Clusters
`GET /api/v1/catalysts?city_id=san_francisco&min_lims=85.0&resolution=9&limit=50`
Retrieves top high-momentum submarkets and parcels currently triggering catalyst alerts ($\\text{LIMS} \\ge 85.0$).

---

### GeoJSON Hex Grid Export
`GET /api/v1/grid?city_id=san_francisco&resolution=9&k_ring=1&include_shap=true`
Returns a GeoJSON `FeatureCollection` of H3 hexagonal polygons with embedded LIMS scores, multi-horizon price appreciation forecasts, and SHAP drivers.

---

### Hexagon Spatial Feature Inspection
`GET /api/v1/hex/{h3_index}/features?resolution=9`
Returns raw spatio-temporal feature attributes, centroid coordinates, and GeoJSON polygon boundary for an individual H3 cell.

---

## 9. Testing & Quality Assurance

Run the automated test suite with pytest:
```bash
pytest tests/ -v
```

The test suite includes **118 automated unit and end-to-end integration tests** covering:
- **Spatial Indexing & Submarket Registries**: Multi-city coverage across San Francisco Bay Area (5 Divisions), NYC (5 Boroughs), and Chicago (6 Divisions).
- **Stream Processing & Avro Serialization**: Schema enforcement and dead-letter queue routing.
- **Out-of-core Feature Engineering**: DuckDB spatio-temporal joins and exponential CapEx decay.
- **Model Inference & Validation**: LightGBM Quantile Pinball loss, ST-GNN ONNX, DCN-v2 ONNX, and TreeSHAP explainability.
- **Serving & Hardened UI**: Security middleware, health/readiness/liveness probes, coordinate validation, error banners, and client state resilience.

---

## 10. License

Urban Signal is licensed under the [Apache 2.0 License](LICENSE).
