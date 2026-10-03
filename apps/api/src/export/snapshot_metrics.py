"""Thread-safe stage and artifact measurements for one snapshot build."""

from __future__ import annotations

import json
import subprocess
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SnapshotMetrics:
    """Collect versioned metrics without adding them to the published KV set."""

    def __init__(
        self,
        *,
        provenance: dict[str, Any] | None = None,
        context_dir: Path | None = None,
        model_mode: str = "synthetic-default",
    ) -> None:
        self._lock = threading.Lock()
        self._durations: dict[str, float] = {}
        self._counters: dict[str, int] = {}
        self._artifacts: dict[str, Any] = {}
        self._provenance = dict(provenance or {})
        self._provenance.setdefault("model_mode", model_mode)
        self._provenance.update(_revision_identity())
        self._provenance["context"] = _context_provenance(context_dir)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        """Accumulate elapsed wall time under ``name`` (concurrent-safe)."""
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - started
            with self._lock:
                self._durations[name] = self._durations.get(name, 0.0) + elapsed

    def increment(self, name: str, count: int = 1) -> None:
        """Add ``count`` to a thread-safe counter."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + count

    def set_artifact(self, name: str, value: Any) -> None:
        with self._lock:
            self._artifacts[name] = value

    def set_context_availability(self, available: bool, reason: str | None = None) -> None:
        with self._lock:
            context = dict(self._provenance.get("context", {}))
            context["available"] = available
            if reason is not None:
                context["reason"] = reason
            else:
                context.pop("reason", None)
            self._provenance["context"] = context

    def snapshot(self) -> dict[str, Any]:
        """Return a detached JSON-shaped snapshot of current measurements."""
        with self._lock:
            return {
                "schema_version": 1,
                "durations_seconds": deepcopy(self._durations),
                "counters": deepcopy(self._counters),
                "artifacts": deepcopy(self._artifacts),
                "provenance": deepcopy(self._provenance),
            }

    def write(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.snapshot(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _revision_identity() -> dict[str, Any]:
    values: dict[str, Any] = {"commit": None, "tree": None, "dirty_worktree": None}
    for label, args in (
        ("commit", ["git", "rev-parse", "HEAD"]),
        ("tree", ["git", "rev-parse", "HEAD^{tree}"]),
    ):
        try:
            values[label] = subprocess.check_output(args, stderr=subprocess.DEVNULL, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    try:
        values["dirty_worktree"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        pass
    return values


def _context_provenance(context_dir: Path | None) -> dict[str, Any]:
    if context_dir is None:
        return {"available": False, "reason": "not_requested"}
    root = Path(context_dir)
    meta_path = root / "bay_area_context_meta.json"
    table_path = root / "bay_area_context_res9.parquet"
    missing = [name for path, name in ((meta_path, "metadata_missing"), (table_path, "table_missing")) if not path.is_file()]
    if missing:
        return {"available": False, "reason": ",".join(missing), "path": str(root)}
    try:
        import json

        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"available": False, "reason": f"metadata_unreadable: {exc}", "path": str(root)}
    generated_at = metadata.get("generated_at")
    result: dict[str, Any] = {
        "available": True,
        "path": str(root),
        "generated_at": generated_at,
    }
    try:
        source_time = datetime.fromisoformat(str(generated_at))
        if source_time.tzinfo is None:
            source_time = source_time.replace(tzinfo=UTC)
        result["age_seconds"] = max(0.0, (datetime.now(UTC) - source_time.astimezone(UTC)).total_seconds())
    except (TypeError, ValueError):
        result["age_seconds"] = None
        result["age_reason"] = "generated_at_missing_or_invalid"
    return result
