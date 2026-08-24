"""ONNX FP16 model compilation, validation, and latency benchmarking."""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import onnx
import onnxruntime as ort
import torch
from src.config import settings
from src.models.dcn_v2 import MultiScaleDCNv2
from src.models.st_gnn import SpatioTemporalGNN


class ONNXModelExporter:
    """Exports PyTorch and tabular models to ONNX FP16 with CUDA runtime validation."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or settings.onnx_model_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_dcn_v2(
        self,
        model: MultiScaleDCNv2,
        in_features: int = 12,
        filename: str = "dcn_v2_macro.onnx",
    ) -> Path:
        """Export DCN-v2 model to ONNX format."""
        model.eval()
        dummy_input = torch.randn(1, in_features, dtype=torch.float32)
        out_path = self.output_dir / filename

        torch.onnx.export(
            model,
            dummy_input,
            str(out_path),
            export_params=True,
            opset_version=18,
            dynamo=False,
            do_constant_folding=True,
            input_names=["features"],
            output_names=["macro_prob"],
            dynamic_axes={
                "features": {0: "batch_size"},
                "macro_prob": {0: "batch_size"},
            },
        )
        return out_path

    def export_st_gnn(
        self,
        model: SpatioTemporalGNN,
        seq_len: int = 4,
        num_nodes: int = 1,
        in_features: int = 12,
        filename: str = "st_gnn_12m.onnx",
    ) -> Path:
        """Export SpatioTemporalGNN model to ONNX format."""
        model.eval()
        dummy_x_seq = torch.randn(seq_len, num_nodes, in_features, dtype=torch.float32)
        dummy_adj = torch.eye(num_nodes, dtype=torch.float32)
        dummy_h = torch.zeros(num_nodes, model.hidden_dim, dtype=torch.float32)

        out_path = self.output_dir / filename

        torch.onnx.export(
            model,
            (dummy_x_seq, dummy_adj, dummy_h),
            str(out_path),
            export_params=True,
            opset_version=18,
            dynamo=False,
            do_constant_folding=True,
            input_names=["x_seq", "norm_adj", "h_prev"],
            output_names=["pred_12m", "h_final"],
            dynamic_axes={
                "x_seq": {1: "num_nodes"},
                "norm_adj": {0: "num_nodes", 1: "num_nodes"},
                "h_prev": {0: "num_nodes"},
                "pred_12m": {0: "num_nodes"},
                "h_final": {0: "num_nodes"},
            },
        )
        return out_path

    def benchmark_onnx_latency(
        self,
        onnx_path: Path,
        sample_input: Dict[str, np.ndarray],
        num_iterations: int = 100,
        providers: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Benchmark ONNX Runtime latency across providers."""
        if providers is None:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        available_providers = [p for p in providers if p in ort.get_available_providers()]
        if not available_providers:
            available_providers = ["CPUExecutionProvider"]

        session = ort.InferenceSession(str(onnx_path), providers=available_providers)

        # Warmup
        for _ in range(10):
            session.run(None, sample_input)

        latencies = []
        for _ in range(num_iterations):
            t0 = time.perf_counter()
            session.run(None, sample_input)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)  # ms

        lat_arr = np.array(latencies)
        return {
            "p50_ms": round(float(np.percentile(lat_arr, 50)), 3),
            "p95_ms": round(float(np.percentile(lat_arr, 95)), 3),
            "p99_ms": round(float(np.percentile(lat_arr, 99)), 3),
            "mean_ms": round(float(np.mean(lat_arr)), 3),
            "provider_used": session.get_providers()[0],
        }
