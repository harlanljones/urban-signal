# =============================================================================
# Urban Signal — Spatial Intelligence & Commercial Catalyst Forecasting Engine
# Multi-stage Dockerfile — single image serves all Python service roles
# =============================================================================

# ── Stage 1: dependency resolver ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv for fast, reproducible installs
RUN pip install --no-cache-dir uv==0.4.29

# Copy dependency manifests only — cache this layer aggressively
COPY pyproject.toml uv.lock ./

# Install all dependencies (including optional cpu onnxruntime; omit gpu extra)
# We use --system so the venv lands in /usr/local and is re-used in the final stage
RUN uv pip install --system --no-cache -e . 2>/dev/null || \
    pip install --no-cache-dir -e .


# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# System-level geo / native dependencies required by psycopg2, shapely, h3
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgdal-dev \
        libpq-dev \
        libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pull installed packages from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Application source
COPY src/ ./src/

# ONNX model artifacts (bind-mounted in compose for easy hot-swap)
COPY models_storage/ ./models_storage/

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose FastAPI port (only used by the api service)
EXPOSE 8000

# Default entrypoint — overridden per-service in docker-compose.yml
CMD ["uvicorn", "src.serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
