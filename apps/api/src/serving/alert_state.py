"""Per-city alert state and budget storage used by the serving path.

The default adapter is in-memory for local workers.  Deployments that need
restart-safe calibration state can inject ``JsonAlertStateStore``; the same
protocol is intentionally small so Postgres/DuckDB can be added at the
application boundary without changing the state machine.
"""

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Protocol


class AlertStateStore(Protocol):
    def load(self, city_id: str) -> dict[str, Any] | None: ...
    def save(self, city_id: str, state: dict[str, Any]) -> None: ...


class InMemoryAlertStateStore:
    """Safe default for tests and single-process development workers."""

    def __init__(self):
        self._states: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def load(self, city_id: str) -> dict[str, Any] | None:
        with self._lock:
            state = self._states.get(city_id)
            return dict(state) if state is not None else None

    def save(self, city_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            self._states[city_id] = dict(state)


class JsonAlertStateStore:
    """Small durable adapter for deployments without an available database."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = Lock()

    def load(self, city_id: str) -> dict[str, Any] | None:
        with self._lock:
            if not self.path.exists():
                return None
            data = json.loads(self.path.read_text())
            state = data.get(city_id)
            return dict(state) if state is not None else None

    def save(self, city_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            data = {}
            if self.path.exists():
                data = json.loads(self.path.read_text())
            data[city_id] = state
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(data, sort_keys=True))
            tmp.replace(self.path)


class CityAlertBudget:
    def __init__(self, daily_limit: int = 100, now=None):
        if daily_limit < 1:
            raise ValueError("daily_limit must be positive")
        self.daily_limit = daily_limit
        self._counts = defaultdict(int)
        self._now = now or (lambda: datetime.now(UTC))
        self._lock = Lock()

    def allow(self, city_id: str) -> bool:
        day = self._now().date()
        key = (city_id, day)
        with self._lock:
            if self._counts[key] >= self.daily_limit:
                return False
            self._counts[key] += 1
            return True

    def remaining(self, city_id: str) -> int:
        with self._lock:
            return max(0, self.daily_limit - self._counts[(city_id, self._now().date())])
