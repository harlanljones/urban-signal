"""US-107: staggered per-feed interval polling."""

import time
from unittest.mock import MagicMock

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler


@pytest.fixture(scope="module")
def scheduler() -> MunicipalIngestionScheduler:
    sched = MunicipalIngestionScheduler(dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0)
    for p in sched.producers.values():
        p.producer = MagicMock()
    return sched


def _limit_to_three(scheduler):
    names = sorted(scheduler.configs)[:3]
    for name, cfg in scheduler.configs.items():
        cfg.enabled = name in names
        cfg.next_due = 0.0  # module fixture: reset rescheduling from prior tests
    return names


def test_all_jobs_due_on_first_tick(scheduler, monkeypatch):
    names = _limit_to_three(scheduler)
    ran = []
    monkeypatch.setattr(scheduler, "poll_job", lambda job_name, limit=None: ran.append(job_name) or {})
    scheduler.poll_due()
    assert ran == names  # sorted order, all due at boot (next_due defaults 0.0)


def test_only_due_jobs_run(scheduler, monkeypatch):
    names = _limit_to_three(scheduler)
    scheduler.configs[names[1]].next_due = time.monotonic() + 999.0
    ran = []
    monkeypatch.setattr(scheduler, "poll_job", lambda job_name, limit=None: ran.append(job_name) or {})
    scheduler.poll_due()
    assert names[1] not in ran
    assert set(ran) == {names[0], names[2]}


def test_run_job_reschedules_at_its_own_interval(scheduler, monkeypatch):
    names = _limit_to_three(scheduler)
    monkeypatch.setattr(scheduler, "poll_job", lambda job_name, limit=None: {})
    before = time.monotonic()
    scheduler.poll_due()
    for name in names:
        interval = scheduler.configs[name].interval_seconds
        expected = before + interval
        assert scheduler.configs[name].next_due == pytest.approx(expected, abs=5.0), name


def test_registry_declares_per_feed_intervals(scheduler):
    assert scheduler.configs["311_baltimore"].interval_seconds == 180.0
    assert scheduler.configs["sla_montgomery"].interval_seconds == 900.0
    assert scheduler.configs["permits"].interval_seconds == 300.0
    intervals = {cfg.interval_seconds for cfg in scheduler.configs.values()}
    assert len(intervals) > 1  # genuinely per-feed, not one global value


def test_start_ticks_run_due_jobs_then_stop(scheduler, monkeypatch):
    _limit_to_three(scheduler)
    ticks = []
    monkeypatch.setattr(scheduler, "poll_due", lambda batch_limit=None: ticks.append(1))
    scheduler.start(interval_seconds=1.0, max_cycles=1)
    assert ticks == [1]


def test_disabled_jobs_never_run(scheduler, monkeypatch):
    names = _limit_to_three(scheduler)
    scheduler.configs[names[0]].enabled = False
    ran = []
    monkeypatch.setattr(scheduler, "poll_job", lambda job_name, limit=None: ran.append(job_name) or {})
    scheduler.poll_due()
    assert names[0] not in ran
