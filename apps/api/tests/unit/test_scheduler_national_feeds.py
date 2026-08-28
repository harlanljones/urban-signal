"""Scheduler wiring tests for GBFS and national feed producers."""

from unittest.mock import MagicMock

from src.producers.scheduler import MunicipalIngestionScheduler


def _scheduler() -> MunicipalIngestionScheduler:
    scheduler = MunicipalIngestionScheduler(rate_limit_delay_seconds=0)
    for producer in scheduler.producers.values():
        producer.producer = MagicMock()
    for config in scheduler.configs.values():
        config.enabled = False
    return scheduler


def test_gbfs_city_job_dispatches_to_run_stream():
    scheduler = _scheduler()
    job_name = "gbfs"
    producer = scheduler.producers["gbfs"]
    scheduler.configs[job_name].enabled = True
    producer.run_stream = MagicMock(return_value=3)

    result = scheduler.poll_job(job_name, limit=25)

    producer.run_stream.assert_called_once_with(city_id="nyc", limit=25)
    assert result["status"] == "SUCCESS"
    assert result["records_published"] == 3


def test_nfip_is_a_scheduled_national_job():
    scheduler = _scheduler()
    producer = scheduler.producers["nfip_claims"]
    producer.run_stream = MagicMock(return_value=4)

    result = scheduler.poll_job("nfip_claims", limit=50)

    producer.run_stream.assert_called_once_with(since=None, limit=50)
    assert result["status"] == "SUCCESS"
    assert result["records_published"] == 4


def test_disaster_declarations_is_registered_and_dispatchable():
    scheduler = _scheduler()
    assert "disaster_declarations" in scheduler.configs
    producer = scheduler.producers["nfip_claims"]
    producer.run_declarations = MagicMock(return_value=3)
    scheduler.configs["disaster_declarations"].enabled = True

    result = scheduler.poll_job("disaster_declarations", limit=10)

    producer.run_declarations.assert_called_once_with(since=None, limit=10)
    assert result["status"] == "SUCCESS"
    assert result["records_published"] == 3


def test_poi_change_is_registered_and_dispatchable():
    scheduler = _scheduler()
    assert "poi_change" in scheduler.producers
    assert "poi_change" in scheduler.configs
    producer = scheduler.producers["poi_change"]
    producer.run_stream = MagicMock(return_value=2)
    scheduler.configs["poi_change"].enabled = True

    result = scheduler.poll_job("poi_change", limit=10)

    producer.run_stream.assert_called_once_with(limit=10)
    assert result["status"] == "SUCCESS"
    assert result["records_published"] == 2


def test_ev_job_is_registered_but_disabled_until_verified():
    scheduler = _scheduler()

    assert "ev_charging" in scheduler.producers
    assert "ev_charging" in scheduler.configs
    assert scheduler.configs["ev_charging"].enabled is False


def test_poll_all_runs_enabled_national_jobs():
    scheduler = _scheduler()
    scheduler.configs["nfip_claims"].enabled = True
    scheduler.producers["nfip_claims"].run_stream = MagicMock(return_value=1)

    result = scheduler.poll_all(batch_limit=10)

    assert result["nfip_claims"]["records_published"] == 1
