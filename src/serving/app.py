"""FastAPI application initialization with CORS, security headers, Prometheus metrics, and lifecycle hooks for Urban Signal."""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware
from src.config import settings
from src.serving.dashboard import get_dashboard_html, get_favicon_svg
from src.serving.llm_docs import get_llms_full_txt, get_llms_txt, get_robots_txt
from src.serving.router import router as api_router

# Prometheus Metrics Definitions
PREDICTION_REQUESTS = Counter(
    "prediction_requests_total",
    "Total property forecast requests processed",
    ["status"],
)
CATALYST_ALERTS_EMITTED = Counter(
    "catalyst_alerts_emitted_total",
    "Total high momentum catalyst alerts emitted",
)
INFERENCE_LATENCY = Histogram(
    "inference_latency_seconds",
    "Model inference latency in seconds",
    buckets=[0.001, 0.003, 0.005, 0.010, 0.025, 0.050, 0.100, 0.250],
)

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Hardened security headers for all HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hooks: initialize model sessions and connection pools."""
    logger.info("Initializing Urban Signal Inference Service (%s)...", settings.app_env)
    yield
    logger.info("Shutting down Urban Signal Inference Service.")


def create_app() -> FastAPI:
    """FastAPI Application Factory for Urban Signal."""
    app = FastAPI(
        title="Urban Signal API",
        description="Urban Signal — Real-Time Geospatial Intelligence & Commercial Catalyst Forecasting Engine via High-Velocity Municipal Ingestion, H3 Indexing, Kafka Streaming, and ONNX GPU Inference",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handlers for hardened error responses
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "message": exc.detail,
                "service": settings.service_name,
                "timestamp": time.time(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "message": "Invalid request schema or parameters",
                "details": exc.errors(),
                "service": settings.service_name,
                "timestamp": time.time(),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled server error: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error occurred while processing request.",
                "service": settings.service_name,
                "timestamp": time.time(),
            },
        )

    # API Routers
    app.include_router(api_router, prefix="/api/v1")

    # Prometheus Metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.get("/", tags=["Dashboard", "Root"])
    async def root(request: Request):
        """Interactive Geospatial Dashboard for browsers; Service metadata JSON for API clients."""
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return HTMLResponse(content=get_dashboard_html())
        return {
            "title": "Urban Signal",
            "service": settings.service_name,
            "status": "operational",
            "version": "2.0.0",
            "docs_url": "/docs",
            "health_url": "/health",
            "ready_url": "/ready",
            "live_url": "/live",
            "metrics_url": "/metrics",
            "dashboard_url": "/dashboard",
            "openapi_url": "/openapi.json",
            "llms_txt_url": "/llms.txt",
            "llms_full_txt_url": "/llms-full.txt",
            "robots_txt_url": "/robots.txt",
            "api_v1_routes": {
                "predict_single": "POST /api/v1/predict",
                "predict_batch": "POST /api/v1/predict/batch",
                "active_catalysts": "GET /api/v1/catalysts",
                "hex_features": "GET /api/v1/hex/{h3_index}/features",
                "grid_geojson": "GET /api/v1/grid",
                "submarkets": "GET /api/v1/submarkets",
                "divisions": "GET /api/v1/spatial/divisions",
                "submarket_prediction": "GET /api/v1/predictions/submarket/{name}",
                "dashboard_metrics": "GET /api/v1/dashboard/metrics",
            },
        }

    @app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
    async def dashboard():
        """Interactive Geospatial Web Visualization Dashboard Endpoint."""
        return HTMLResponse(content=get_dashboard_html())

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        """Brand SVG favicon served at the browser-conventional path."""
        return Response(
            content=get_favicon_svg(),
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/llms.txt", include_in_schema=False)
    async def llms_txt():
        """LLM-friendly site index (llms.txt standard)."""
        return Response(
            content=get_llms_txt(),
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/llms-full.txt", include_in_schema=False)
    async def llms_full_txt():
        """Complete LLM-oriented API reference in plain markdown."""
        return Response(
            content=get_llms_full_txt(),
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/robots.txt", include_in_schema=False)
    async def robots_txt():
        """Permissive crawler policy welcoming AI agents."""
        return Response(
            content=get_robots_txt(),
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Kubernetes Liveness and Readiness Probe."""
        return {
            "status": "healthy",
            "service": settings.service_name,
            "version": "2.0.0",
            "environment": settings.app_env,
        }

    @app.get("/ready", tags=["Health"])
    async def readiness_probe():
        """Kubernetes Readiness Probe."""
        return {
            "ready": True,
            "service": settings.service_name,
            "version": "2.0.0",
            "status": "ready",
        }

    @app.get("/live", tags=["Health"])
    async def liveness_probe():
        """Kubernetes Liveness Probe."""
        return {
            "live": True,
            "service": settings.service_name,
            "status": "alive",
        }

    return app


app = create_app()
