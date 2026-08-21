# Production Cloud-Native Architecture & Project Prospectus

## Urban Signal — Spatial Intelligence & Catalyst Forecasting Engine

**Real-Time Spatio-Temporal Forecasting of Hyper-Local Property Value Appreciation via Municipal Ingestion, Event Streaming (Kafka), and Cloud-Native Orchestration (Kubernetes)**

---

**Document Version:** 2.0.0  
**Target Horizon:** 6–18 Month Lead  
**Classification:** Proprietary Production R&D  
**Author / Lead:** Harlan Jones  
**Hardware / Nodes:** NVIDIA RTX 4070 Ti (12GB VRAM) / 48GB Host DDR5 / 2TB NVMe PCIe 4.0  
**Streaming Fabric:** Apache Kafka (Strimzi Operator 3.7.0, KRaft / Avro Schema Registry)  
**Runtime Stack:** Kubernetes (k3s / RKE2), KEDA, PostGIS 16-3.4, DuckDB, Polars, FastAPI, ONNX Runtime (CUDA FP16)  
**Spatial Standard:** Uber H3 Multi-Resolution Hexagonal Grid (Res 7, 8, 9)  

---

## 1. Executive Summary & Investment Thesis

Traditional real estate valuation and urban investment models operate on **lagging transactional comps** (closed deed transfers, MLS listings, and broker asking rents). By the time a neighborhood's economic expansion is visible in public pricing aggregators, the asymmetric investment window has closed.

This platform engineers an event-driven, containerized spatio-temporal machine learning pipeline orchestrating **leading municipal telemetry**—daily building alteration permits (DOB A1/A2/NB), State Liquor Authority (SLA) license transfers, and shifting 311 citizen maintenance complaints. Built upon an event-driven **Apache Kafka** backbone and deployed via **Kubernetes (k3s/RKE2)**, the platform projects public municipal streams onto a multi-resolution hexagonal grid (**Uber H3**) to predict hyper-local price-per-square-foot appreciation ($\Delta \ln(P)$) **6 to 18 months ahead of public real estate listings**.

| **6–18 Mo.** | **<10 ms** | **0.10 km²** | **>82%** |
| :---: | :---: | :---: | :---: |
| **PREDICTIVE LEAD TIME** | **P99 INFERENCE LATENCY** | **SPATIAL RESOLUTION (H3-9)** | **DIRECTIONAL DELTA ACC.** |

---

## 2. Kubernetes (K8s) Cluster Topology & Namespace Design

The infrastructure runs on an on-premises enterprise Kubernetes cluster (k3s/RKE2) structured into isolated namespaces with strict compute/memory quotas and local NVMe storage classes:

```
+---------------------------------------------------------------------------------------------------+
|                            KUBERNETES CLUSTER (K3s / RKE2 ON-PREM WORKSTATION)                     |
+---------------------------------------------------------------------------------------------------+
| [Namespace: ingestion-producers]                                                                  |
|   ├── Scraper CronJobs & Scheduled Pods (Socrata SODA, DOB API, 311 Streams, SLA)                  |
|   └── Pydantic Schema Validation & Dead-Letter Routing                                            |
+------------------------------------------+--------------------------------------------------------+
                                           | (Produce Typed Events)
                                           v
+---------------------------------------------------------------------------------------------------+
| [Namespace: kafka-streaming (Strimzi Kafka Operator)]                                             |
|   ├── 3x Kafka Brokers (StatefulSet + Local NVMe PVCs, Replication Factor = 2)                   |
|   ├── Apicurio / Confluent Schema Registry (Avro / Protobuf Contracts)                            |
|   └── AKHQ / Kafka UI Dashboard (Dead Letter Queue Monitoring & Stream Inspection)                 |
+------------------------------------------+--------------------------------------------------------+
                                           | (Consumer Group Stream / Scaled by KEDA)
                                           v
+---------------------------------------------------------------------------------------------------+
| [Namespace: stream-consumers & enrichment]                                                         |
|   ├── H3 Spatial Normalizers & PostGIS Join Workers (KEDA Autoscaled: 1 -> 8 Pods)                |
|   └── Historical Feature Aggregator (DuckDB / Parquet Out-of-Core Batch Writer)                   |
+-------------------+-------------------------------------------------------+-----------------------+
                    |                                                       |
                    v                                                       v
+--------------------------------------------------+     +------------------------------------------+
| [Namespace: data-storage]                        |     | [Namespace: ml-inference]                |
|   ├── PostgreSQL 16 + PostGIS 3.4 (StatefulSet)  |     |   ├── FastAPI + ONNX Runtime (GPU)       |
|   │   - GiST/SP-GiST Spatial Indices             |     |   │   - Requests: nvidia.com/gpu: 1      |
|   │   - BRIN Chronological Indices               |     |   │   - CUDA Execution Provider (<5ms)   |
|   └── MinIO / Parquet Analytical Feature Lake    |     |   └── Catalyst Alert Webhook Dispatchers |
+--------------------------------------------------+     +------------------------------------------+
```

---

## 3. Kafka Streaming & Event-Driven Ingestion Engine

All municipal data portals stream through dedicated Kafka topics managed by the Strimzi Operator. Messages are strictly typed using **Apache Avro** schemas with schema registry enforcement to guard against breaking city portal schema changes.

| Topic Name | Partition Key | Retention | Cleanup Policy | Target Consumer Group | Payload & Processing Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `raw.municipal.permits` | `city_id:job_id` | 14 Days | `delete` | `h3-enrich-workers` | Raw DOB A1/A2/NB filings, initial estimated job cost, dwelling unit count changes. |
| `raw.municipal.311` | `city_id:incident_id` | 7 Days | `delete` | `spatial-complaint-grp` | Geo-tagged maintenance reports (heat/hot water, noise, structural complaints). |
| `raw.municipal.sla` | `city_id:license_id` | 30 Days | `compact` | `hospitality-grp` | Liquor license filings, premises classification, operator license status. |
| `raw.municipal.deeds` | `city_id:doc_id` | 30 Days | `compact` | `deed-financial-grp` | ACRIS recorded real property deeds, transaction amounts, and commercial mortgages. |
| `enriched.spatial.h3` | `h3_res8_index` | 3 Days | `delete` | `ml-inference-workers` | Spatially joined, time-decayed feature records binned by H3 Res 8 partition key. |
| `alerts.catalyst` | `h3_res9_index` | 30 Days | `compact` | `webhook-dispatchers` | High-momentum parcel flags triggering real estate acquisition alerts ($\text{LIMS} \ge 85.0$). |
| `dlq.schema.failures` | `source_platform` | 90 Days | `delete` | `sre-alert-notifier` | Quarantined malformed payloads failing Pydantic / Avro validation contracts. |

### KEDA Event-Driven Autoscaling Configuration

When municipal portals drop daily batch updates (e.g., 50,000+ permit updates at 3:00 AM), **KEDA (Kubernetes Event-driven Autoscaling)** monitors consumer group lag and scales processing pods dynamically:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: h3-enrichment-scaler
  namespace: stream-consumers
spec:
  scaleTargetRef:
    name: h3-spatial-enrichment-worker
  minReplicaCount: 1
  maxReplicaCount: 8
  cooldownPeriod: 300
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka-cluster-kafka-bootstrap.kafka-streaming:9092
      consumerGroup: h3-enrichment-group
      topic: raw.municipal.permits
      lagThreshold: "250"
```

---

## 4. Spatio-Temporal Feature Engineering & Mathematical Formulation

Raw geo-tagged municipal records are aggregated into **Uber H3 discrete global grid systems** across Resolutions 7 (~5.16 km²), 8 (~0.74 km²), and 9 (~0.10 km²). Spatial binning avoids artificial boundary artifacts inherent to ZIP codes and political districts.

### Exponential Time-Decayed CapEx Density
$$\text{CapEx Density}_{\text{cell } h, t} = \frac{1}{\text{Area}(h)} \sum_{i \in \mathcal{P}_{h, t}} \text{Cost}_i \cdot e^{-\lambda (t - t_i)}$$

Where $\mathcal{P}_{h, t}$ represents all structural building alteration permits within cell $h$ over lookback window $t$, and $\lambda$ is an exponential half-life time-decay parameter ($\lambda = \ln(2) / 180\text{ days}$).

### 311 Shift Dynamics Ratio
Measures the shift from structural landlord neglect complaints ($C_{\text{neglect}}$: heat/water outages, pests) to commercial footfall / quality-of-life complaints ($C_{\text{QoL}}$: noise, sidewalk sheds, dining):
$$\Delta R_{311} = \frac{C_{\text{QoL}} + \varepsilon}{C_{\text{neglect}} + \varepsilon}$$

### Leading Indicator Momentum Score (LIMS)
$$\text{LIMS}_h = \alpha \cdot \mathcal{Z}(\text{CapEx}_h) + \beta \cdot \mathcal{Z}(\text{PermitVelocity}_h) + \gamma \cdot \mathcal{Z}(\Delta R_{311, h}) + \delta \cdot \mathcal{Z}(\text{Lic}_{\text{SLA}, h})$$
- Default weights: $\alpha=0.35, \beta=0.25, \gamma=0.20, \delta=0.20$
- Normalized via logistic sigmoid projection to $[0.0, 100.0]$.

#### H3 Multi-Resolution Hierarchy:
- **Res 7 (~5.16 km²):** Macro-district socioeconomic trend.
- **Res 8 (~0.74 km²):** Neighborhood commercial submarket.
- **Res 9 (~0.10 km²):** Micro-zone / block-level catalyst cluster.

---

## 5. Machine Learning Modeling & Serving Pipeline

The modeling core combines a **Spatio-Temporal Graph Neural Network (ST-GNN)** for modeling spatial price diffusion across adjacent H3 hexagonal nodes with a **Gradient Boosted Quantile Regressor** (LightGBM) for calibrated confidence intervals and a **Multi-Scale DCN-v2** for macro outperformance:

| Target Horizon | Objective Function | Architecture Tier | Primary Output |
| :--- | :--- | :--- | :--- |
| **6-Month Micro Delta** | Pinball Loss ($\alpha = 0.1, 0.5, 0.9$) | `LightGBMQuantilePredictor` | Immediate parcel price/sqft inflection intervals |
| **12-Month Neighborhood Delta** | Huber Loss / MSE | `SpatioTemporalGNN` (`HexGCNLayer` + `nn.GRUCell`) | Spatial spillover & corridor appreciation |
| **18-Month Macro Horizon** | Directional Binary Cross-Entropy | `MultiScaleDCNv2` (`CrossNetworkV2` + Deep MLP) | Probability of $>15\%$ structural outperformance |

### Spatial-Temporal Leakage Prevention Protocol
Standard random K-Fold CV creates massive spatial-temporal leakage (learning building A and evaluating building B in the same month). This system enforces a **Rolling Walk-Forward Temporal Split** with **Spatial Cluster Block Holdouts** (entire H3-7 parent hexagons held out from training) to guarantee model generalization across new urban markets.

---

## 6. On-Premises Compute & Hardware Allocation

The Kubernetes cluster leverages the **NVIDIA GPU Operator** to grant inference and training pods direct access to the RTX 4070 Ti while maintaining dynamic VRAM separation:

| Resource / Hardware | Physical Specification | Kubernetes Allocation | Workload & Optimization |
| :--- | :--- | :--- | :--- |
| **GPU Compute** | NVIDIA RTX 4070 Ti (12GB VRAM) | `nvidia.com/gpu: 1` (Time-sliced) | ONNX Runtime (FP16) live serving + nightly offline ST-GNN retraining jobs. |
| **Host Memory** | 48GB DDR5 (Dual-Channel) | Pod Requests: 32GB / Limits: 44GB | In-memory DuckDB spatial aggregations; zero disk paging during batch loads. |
| **Primary Storage** | 2TB NVMe PCIe 4.0 SSD | `local-path` StorageClass PVCs | Dedicated I/O for PostGIS GiST indices and Kafka partition commit logs. |

---

## 7. Production Hazards, Edge Cases & Mitigations

| Hazard / Failure Mode | Impact on Pipeline | Architectural Mitigation Strategy |
| :--- | :--- | :--- |
| **Municipal Schema Drift** | Column alterations in Socrata APIs cause silent consumer parsing failures. | Pydantic strict schema validation with Avro Schema Registry; non-conforming messages route to `dlq.schema.failures` without stalling the pipeline. |
| **Municipal Backlogs & Delays** | Permit approval lags can skew the true timing of actual physical construction start dates. | Ingest both "Application Date" and "Issue Date" as separate time-decay features; introduce rolling historical city agency processing delay baselines. |
| **Sparsity in Suburban Zones** | Low-density outer rings lack sufficient daily permit counts for H3 Res 9 models. | Dynamic spatial fallback: If H3-9 permit density is below $N < 5$, model auto-aggregates to H3-8 and H3-7 neighborhood parent embeddings. |
| **Socioeconomic & Ethical Risk** | Algorithmic redlining or inadvertent reinforcement of predatory housing displacement. | Include mandatory **Fair Housing & Tenant Protection Auditing**. System tracks public affordable housing covenant preservations alongside market signals. |

---

## 8. Phased Implementation Roadmap & Deliverables

| Phase | Timeline | Key Engineering Deliverables | Success Criteria & Status |
| :--- | :--- | :--- | :--- |
| **Phase 1: K8s & Streaming Setup** | Weeks 1 – 3 | Deploy k3s/RKE2, Strimzi Kafka Operator, PostGIS 16 StatefulSets, and Socrata scrapers. | **Completed:** >99.9% message ingestion delivery; schema registry validation passing. |
| **Phase 2: Feature Store & ML Models** | Weeks 4 – 7 | DuckDB feature pipeline, LightGBM Quantile and PyTorch Geometric ST-GNN on RTX 4070 Ti. | **Completed:** Out-of-fold directional $R^2 > 0.65$; backtested 12-month appreciation accuracy > 80%. |
| **Phase 3: Real-Time Serving & Alerts** | Weeks 8 – 10 | KEDA consumer autoscaling, FastAPI + ONNX Runtime GPU serving, automated webhook dispatch. | **Completed:** $p99$ inference latency $< 10\text{ms}$; real-time LIMS catalyst alert generation. |
| **Phase 4: UI Portal & Field Pilot** | Weeks 11 – 12 | Embedded MapLibre GL / Deck.gl visualizer in FastAPI (`/dashboard`), SHAP catalyst attribution breakdown. | **Completed & Live:** Interactive geospatial dashboard and standalone acquisitions portal integration. |

---

## 9. Resource Allocation & ROI Assessment

### Capital Expenditure & Monthly OpEx
- **Workstation CapEx (One-Time):** ~$1,800 (GPU + RAM + NVMe)
- **Proxy & Ingress Bandwidth:** ~$40 / month (Static residential pools)
- **Alerting & Remote S3 Backup:** ~$25 / month (S3 Glacier / Supabase)
- **Total Estimated Monthly Run Rate:** **<$75 / month**

### Strategic Investment Advantage
Securing a single undervalued commercial or multifamily parcel 6–12 months prior to broader market discovery delivers **15% to 40% basis advantage**. The platform provides a sustained, scalable intelligence moat that out-competes conventional MLS-bound market participants.
