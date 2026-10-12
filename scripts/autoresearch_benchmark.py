"""Autoresearch harness: fixed 157-metro dense publication and client CPU workload.

No production code is patched except the snapshot metadata wall clock. Models
are genuinely initialized/trained/exported with fixed seeds in a temporary dir.
Three builds start with empty prediction caches; initialization and verification
are excluded from snapshot_ms. Client timing includes JSON parse and shipped
mergeTilePayload, but excludes GPU rendering and network transfer.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import random
import resource
import socket
import statistics
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 10, 11, tzinfo=UTC)
        return value.replace(tzinfo=None) if tz is None else value.astimezone(tz)


def deny_network(*args, **kwargs):
    raise RuntimeError("Autoresearch workload must not access the network")


def canonical(value):
    if isinstance(value, dict):
        return {
            key: canonical(item)
            for key, item in value.items()
            if key != "inference_latency_ms"
        }
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite prediction in published output")
    return value


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tile-loading", action="store_true", help="Measure the shipped client loader after one verified snapshot build")
    tile_loading = parser.parse_args().tile_loading
    socket.socket.connect = deny_network
    socket.create_connection = deny_network
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)

    from src.export import snapshot_builder
    from src.serving.engine import MultiHorizonInferenceEngine
    from src.spatial.city_registry import REGISTRY

    snapshot_builder.datetime = FixedDatetime
    expected = json.loads((ROOT / "scripts/autoresearch_coverage.json").read_text())
    cities = sorted(expected)
    if set(cities) != {city.value for city in REGISTRY}:
        raise ValueError("Registry differs from pinned workload; rebaseline explicitly")
    all_cells = set().union(*(set(cells) for cells in expected.values()))
    timings = []
    signatures = []
    with tempfile.TemporaryDirectory(prefix="urban-signal-autoresearch-") as temp:
        root = Path(temp)
        init_start = time.perf_counter()
        engine = MultiHorizonInferenceEngine(model_dir=str(root / "models"), cache_predictions=True)
        init_ms = (time.perf_counter() - init_start) * 1000
        for trial in range(1 if tile_loading else 3):
            engine.clear_prediction_caches()
            output = root / f"snapshot-{trial}"
            started = time.perf_counter()
            manifest = await snapshot_builder.build_snapshot(
                output, engine=engine, cities=cities, dense_metro=True,
                include_legacy_cells=False,
            )
            timings.append((time.perf_counter() - started) * 1000)
            if manifest["cities"] != cities or manifest["cells"] != len(all_cells):
                raise ValueError("Publication lost metro/cell coverage")
            digest = hashlib.sha256()
            for city in cities:
                grid = json.loads((output / "grid" / f"{city}.json").read_text())
                actual = [feature["properties"]["h3_index"] for feature in grid["features"]]
                if len(actual) != len(set(actual)) or set(actual) != set(expected[city]):
                    raise ValueError(f"Dense coverage changed for {city}")
                for feature in grid["features"]:
                    props = feature["properties"]
                    for metric in snapshot_builder.NORMALIZED_METRICS:
                        for scope in ("metro", "national"):
                            if not 0 <= props[f"{metric}_{scope}_pct"] <= 100:
                                raise ValueError(f"Invalid percentile for {city}")
            # Hash every logical prediction, tile and catalyst, without duplicate
            # release twins. Metadata byte counts and measured latency are noise.
            for family in ("grid", "gridtiles", "gridtiles_res7", "gridtiles_res8", "gridtiles_res9", "cells", "catalysts", "submarkets"):
                for path in sorted((output / family).glob("*.json")):
                    if path.name == "index_meta.json":
                        continue
                    digest.update(str(path.relative_to(output)).encode())
                    digest.update(json.dumps(canonical(json.loads(path.read_text())), sort_keys=True, separators=(",", ":")).encode())
            actual_cells = {path.stem for path in (output / "cells").glob("*.json") if path.stem != "index_meta"}
            if actual_cells != all_cells:
                raise ValueError("Per-cell shard coverage changed")
            for res in (7, 8, 9):
                if not manifest["tile_indexes"][str(res)]:
                    raise ValueError(f"Missing LOD resolution {res}")
            signatures.append(digest.hexdigest())
            if trial == 0:
                client = "scripts/autoresearch_client.ts"
                if tile_loading:
                    from h3 import cell_to_latlng
                    parents = {parent for index in manifest["tile_indexes"].values() for parent in index}
                    (output / "benchmark-parent-centers.json").write_text(
                        json.dumps({parent: cell_to_latlng(parent) for parent in sorted(parents)})
                    )
                    client = "scripts/autoresearch_tile_loader.ts"
                await asyncio.to_thread(subprocess.run, ["bun", str(ROOT / client), str(output)], cwd=ROOT, check=True)
                bulk_bytes = (output / "kv-bulk.json").stat().st_size
                manifest_bytes = (output / "manifest.json").stat().st_size
                tile_bytes = sum(path.stat().st_size for path in (output / "gridtiles").glob("*.json"))
            # Keep at most one completed snapshot on disk.
            import shutil
            shutil.rmtree(output)
    if len(set(signatures)) != 1:
        raise ValueError("Fixed workload produced different semantic outputs across trials")
    baseline_signature = (ROOT / "scripts/autoresearch_semantic.sha256").read_text().strip()
    if signatures[0] != baseline_signature:
        raise ValueError("Publication semantics differ from the pinned baseline")
    print(f"METRIC snapshot_ms={statistics.median(timings):.3f}")
    print(f"METRIC model_init_ms={init_ms:.3f}")
    print(f"METRIC peak_rss_mib={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.3f}")
    print(f"METRIC bulk_bytes={bulk_bytes}")
    print(f"METRIC manifest_bytes={manifest_bytes}")
    print(f"METRIC tile_bytes={tile_bytes}")
    print(f"METRIC metros={len(cities)}")
    print(f"METRIC cells={len(all_cells)}")
    print(f"ASI semantic_sha256={signatures[0]}")


if __name__ == "__main__":
    asyncio.run(main())
