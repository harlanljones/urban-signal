"""US-106: durable scheduler watermark state (save/load roundtrip, guards)."""

import json
from unittest.mock import MagicMock

import pytest

from src.config import settings
from src.producers.scheduler import MunicipalIngestionScheduler


@pytest.fixture(scope="module")
def scheduler() -> MunicipalIngestionScheduler:
    sched = MunicipalIngestionScheduler(dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0)
    for p in sched.producers.values():
        p.producer = MagicMock()
    return sched


def test_save_then_load_roundtrip(scheduler, tmp_path, monkeypatch):
    state = tmp_path / "wm.json"
    monkeypatch.setattr(scheduler, "state_file", str(state))

    job = next(iter(scheduler.metrics))
    scheduler.metrics[job].high_watermark = "2026-08-24T00:00:00"
    scheduler._save_state()

    payload = json.loads(state.read_text())
    assert payload[job]["high_watermark"] == "2026-08-24T00:00:00"

    # Simulate a restart: wipe in-memory watermarks, then restore.
    saved = {j: m.high_watermark for j, m in scheduler.metrics.items() if m.high_watermark}
    for m in scheduler.metrics.values():
        m.high_watermark = None
    scheduler.metrics[job].high_watermark = None
    scheduler._load_state()

    for j, wm in saved.items():
        assert scheduler.metrics[j].high_watermark == wm
    assert scheduler.metrics[job].high_watermark == "2026-08-24T00:00:00"


def test_load_does_not_lower_existing_watermarks(scheduler, tmp_path, monkeypatch):
    job = next(iter(scheduler.metrics))
    state = tmp_path / "wm.json"
    state.write_text(json.dumps({job: {"high_watermark": "2020-01-01T00:00:00"}}))
    monkeypatch.setattr(scheduler, "state_file", str(state))

    scheduler.metrics[job].high_watermark = "2026-08-24T00:00:00"
    scheduler._load_state()
    assert scheduler.metrics[job].high_watermark == "2026-08-24T00:00:00"


def test_load_ignores_unknown_jobs_and_garbage(scheduler, tmp_path, monkeypatch):
    state = tmp_path / "wm.json"
    state.write_text('{"not_a_real_job": {"high_watermark": "2026-01-01T00:00:00"}}')
    monkeypatch.setattr(scheduler, "state_file", str(state))
    scheduler._load_state()  # no crash, nothing restored

    state.write_text("{not json")
    monkeypatch.setattr(scheduler, "state_file", str(state))
    scheduler._load_state()  # warning, no crash


def test_save_is_noop_without_state_file(scheduler, tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler, "state_file", None)
    scheduler._save_state()  # no file created, no crash
    assert not (tmp_path / "wm.json").exists()


def test_setting_defaults_to_disabled():
    """The FIELD default is disabled; a local .env may still configure a path,
    so assert against a settings instance that ignores env files."""
    from src.config import Settings

    fresh = Settings(_env_file=None)
    assert fresh.scheduler_state_file == ""
