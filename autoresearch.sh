#!/usr/bin/env bash
# Offline tile loading CPU benchmark. Run from any directory.
# Primary: median shipped client queue/parse/merge/LOD/source-submission time.
# A fixed, verified dense 157-metro snapshot is built outside the timed workload.
# Excludes live network, GPU rendering, animation and browser/Core Web Vitals.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/apps/api"
export PYTHONHASHSEED=42 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export POLARS_MAX_THREADS=1 ONNX_EXECUTION_PROVIDER=CPUExecutionProvider
export CUDA_VISIBLE_DEVICES=""
exec "$ROOT/apps/api/.venv/bin/python" "$ROOT/scripts/autoresearch_benchmark.py" --tile-loading
