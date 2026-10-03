#!/usr/bin/env python3
"""Measure snapshot builds and compare their serialized semantic outputs."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import resource
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


def compare_snapshot_outputs(
    baseline: dict[str, Any], candidate: dict[str, Any], *, limit: int = 100
) -> dict[str, Any]:
    """Compare logical KV outputs, ignoring only known run-to-run noise."""
    differences: list[dict[str, Any]] = []

    # Validate transport metadata against each actual payload before excluding
    # derived byte lengths from cross-run equality. Latency appears in grids,
    # catalysts and cells; comparing those lengths would compare latency again.
    for side, output in (("baseline", baseline), ("candidate", candidate)):
        manifest = output.get("manifest", {})
        for key, metadata in manifest.get("keys", {}).items():
            if key not in output or "bytes" not in metadata:
                continue
            payload = output[key]
            if key == "manifest":
                payload = {**payload, "keys": {k: v for k, v in payload["keys"].items() if k != "manifest"}}
            actual = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            if metadata["bytes"] != actual:
                differences.append({"path": f"manifest/keys/{key}/bytes", "kind": "invalid_byte_count", "side": side, "recorded": metadata["bytes"], "actual": actual})

    def diff(path: tuple[str, ...], left: Any, right: Any) -> None:
        if len(differences) >= limit:
            return
        if path and path[-1] == "inference_latency_ms":
            return
        if path in {
            ("manifest", "generated_at"),
            ("cells/index_meta", "generated_at"),
            ("national/index", "generated_at"),
        }:
            return
        if len(path) == 4 and path[:2] == ("manifest", "keys"):
            key, field = path[2], path[3]
            if field == "bytes" and key in baseline and key in candidate:
                return
        if isinstance(left, dict) and isinstance(right, dict):
            left_keys, right_keys = set(left), set(right)
            if left_keys != right_keys:
                differences.append(
                    {"path": "/".join(path), "kind": "object_keys", "left": sorted(left_keys), "right": sorted(right_keys)}
                )
            for key in sorted(left_keys & right_keys, key=str):
                diff((*path, str(key)), left[key], right[key])
            return
        if isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                differences.append(
                    {"path": "/".join(path), "kind": "array_length", "left": len(left), "right": len(right)}
                )
            for index, (left_item, right_item) in enumerate(zip(left, right)):
                diff((*path, str(index)), left_item, right_item)
            return
        if type(left) is not type(right) or left != right:
            differences.append(
                {"path": "/".join(path), "kind": "value", "left": left, "right": right}
            )

    diff((), baseline, candidate)
    return {"equal": not differences, "differences": differences, "truncated": len(differences) >= limit}


def _load_kv_output(path: Path) -> dict[str, Any]:
    entries = json.loads((path / "kv-bulk.json").read_text(encoding="utf-8"))
    result: dict[str, Any] = {}
    for entry in entries:
        key = entry["key"]
        if key in result:
            raise ValueError(f"Duplicate KV key in {path}: {key}")
        result[key] = json.loads(entry["value"])
    return result


def _identity(context_dir: Path | None) -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    context_hashes: dict[str, str | None] = {"metadata": None, "table": None}
    context_files = {
        "metadata": "bay_area_context_meta.json",
        "table": "bay_area_context_res9.parquet",
    }
    if context_dir is not None:
        for kind, filename in context_files.items():
            source = context_dir / filename
            if source.is_file():
                context_hashes[kind] = hashlib.sha256(source.read_bytes()).hexdigest()
    return {
        "commit": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "working_tree_dirty": bool(git("status", "--porcelain")),
        "context_input_files": context_files if context_dir is not None else None,
        "context_input_sha256": context_hashes if context_dir is not None else None,
    }


def _rss_mib() -> float:
    # ru_maxrss is KiB on Linux and bytes on macOS.
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(value / 1024 if os.uname().sysname == "Linux" else value / (1024 * 1024))


async def _run_build(
    *,
    engine: Any,
    output: Path,
    cities: list[str],
    context_dir: Path | None,
    cache: bool,
    metrics: Any,
) -> dict[str, Any]:
    from src.export.snapshot_builder import build_snapshot

    engine.cache_predictions = cache
    engine.metrics = metrics
    started = time.perf_counter()
    try:
        await build_snapshot(
            output,
            engine=engine,
            cities=cities,
            context_dir=context_dir,
            metrics=metrics,
        )
    finally:
        engine.metrics = None
    return {
        "duration_seconds": time.perf_counter() - started,
        "process_lifetime_peak_rss_mib": _rss_mib(),
        "metrics": metrics.snapshot(),
        "output": _load_kv_output(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Benchmark JSON output path")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--context-dir", type=Path, default=None)
    parser.add_argument("--cache-mode", choices=("off", "on", "compare"), default="compare")
    parser.add_argument("--cities", nargs="*", default=None)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    from src.export.snapshot_metrics import SnapshotMetrics
    from src.serving.engine import MultiHorizonInferenceEngine
    from src.spatial.city_registry import CityId

    cities = args.cities or [city.value for city in CityId]
    initialization_started = time.perf_counter()
    engine = MultiHorizonInferenceEngine(cache_predictions=False)
    model_initialization_seconds = time.perf_counter() - initialization_started
    raw_runs: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    # Each enabled configuration has three independent cold builds and three
    # warm builds by default. Reuse weights across every trial.
    modes = [(False, "disabled")] if args.cache_mode != "on" else []
    if args.cache_mode != "off":
        modes.extend([(True, "cold"), (True, "warm")])
    identity = _identity(args.context_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="snapshot-benchmark-") as temp:
        root = Path(temp)
        baseline_dirs: dict[int, Path] = {}
        for cached, cache_state in modes:
            label = "on" if cached else "off"
            for run_index in range(args.runs):
                # Warm trials retain the last cold trial's populated cache.
                if hasattr(engine, "clear_prediction_caches") and cache_state != "warm":
                    engine.clear_prediction_caches()
                mode_dir = root / f"{label}-current"
                if mode_dir.exists():
                    shutil.rmtree(mode_dir)
                metrics = SnapshotMetrics(
                    context_dir=args.context_dir,
                    provenance={
                        "cache_mode": label,
                        "cache_state": cache_state,
                        "run_index": run_index,
                    },
                )
                result = asyncio.run(
                    _run_build(
                        engine=engine,
                        output=mode_dir,
                        cities=cities,
                        context_dir=args.context_dir,
                        cache=cached,
                        metrics=metrics,
                    )
                )
                output = result.pop("output")
                raw_runs.append({
                    "run_index": run_index,
                    "cache_mode": label,
                    "cache_state": cache_state,
                    **result,
                })
                if args.cache_mode == "compare" and not cached:
                    baseline_dir = root / f"baseline-{run_index}"
                    baseline_dir.mkdir()
                    shutil.copyfile(mode_dir / "kv-bulk.json", baseline_dir / "kv-bulk.json")
                    baseline_dirs[run_index] = baseline_dir
                elif args.cache_mode == "compare":
                    baseline = _load_kv_output(baseline_dirs[run_index])
                    comparisons.append(compare_snapshot_outputs(baseline, output))
                del output
                shutil.rmtree(mode_dir)

    durations: dict[str, list[float]] = {}
    rss: dict[str, list[float]] = {}
    for item in raw_runs:
        configuration = "off" if item["cache_mode"] == "off" else f"on_{item['cache_state']}"
        durations.setdefault(configuration, []).append(item["duration_seconds"])
        rss.setdefault(configuration, []).append(item["process_lifetime_peak_rss_mib"])
    semantic = {
        "equal": all(item["equal"] for item in comparisons),
        "runs": comparisons,
    } if comparisons else None
    payload = {
        "schema_version": 1,
        "input_identity": {**identity, "cities": cities, "context_dir": str(args.context_dir) if args.context_dir else None},
        "cache_mode": args.cache_mode,
        "runs_requested": args.runs,
        "shared_model_initialization_seconds": model_initialization_seconds,
        "raw_runs": [
            {key: value for key, value in item.items() if key != "output"}
            for item in raw_runs
        ],
        "medians": {
            mode: {
                "duration_seconds": statistics.median(durations[mode]),
                "process_lifetime_peak_rss_mib_observation": statistics.median(rss[mode]),
            }
            for mode in durations
        },
        "semantic_comparison": semantic,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "semantic_equal": semantic["equal"] if semantic else None}))
    if semantic is not None and not semantic["equal"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
