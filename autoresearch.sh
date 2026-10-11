#!/usr/bin/env bash
# Offline dense-metro publication benchmark. Run from any directory.
# Primary: median cold-cache snapshot build milliseconds (three real builds).
# Secondary: client JSON parse/merge CPU time, payload bytes, RSS and coverage.
# This does not measure live ingestion, network latency, MapLibre rendering or CWV.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/apps/api"
export PYTHONHASHSEED=42 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export POLARS_MAX_THREADS=1 ONNX_EXECUTION_PROVIDER=CPUExecutionProvider
export CUDA_VISIBLE_DEVICES=""
exec "$ROOT/apps/api/.venv/bin/python" "$ROOT/scripts/autoresearch_benchmark.py"
