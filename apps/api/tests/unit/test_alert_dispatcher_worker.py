"""Offline tests for the AlertDispatcherWorker (ADR 0008 §6, US-108 AC#3)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import settings
from src.consumers.alert_dispatcher_worker import AlertDispatcherWorker
from src.schemas.models import CatalystAlert


def _alert_record(**overrides) -> dict:
    record = {
        "alert_id": "alert-abc12345",
        "city_id": "nyc",
        "h3_index": "892a100d59fffff",
        "h3_resolution": 9,
        "lims_score": 91.5,
        "predicted_delta_6m": 0.183,
        "predicted_delta_12m": 0.32,
        "macro_outperformance_prob_18m": 0.96,
        "centroid_lat": 40.7233,
        "centroid_lng": -74.003,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    record.update(overrides)
    return record


@pytest.fixture
def fake_dispatcher():
    dispatcher = MagicMock()
    dispatcher.dispatch_alert = AsyncMock(return_value=[200])
    return dispatcher


@pytest.fixture
def worker(fake_dispatcher):
    with (
        patch("src.consumers.alert_dispatcher_worker.BaseKafkaConsumer"),
        patch("src.consumers.alert_dispatcher_worker.BaseKafkaProducer"),
    ):
        return AlertDispatcherWorker(dispatcher=fake_dispatcher)


class TestAlertDispatcherWorker:
    def test_constructs_model_and_dispatches(self, worker, fake_dispatcher):
        worker.process_record(_alert_record(), settings.topic_catalyst_alerts, "k1")

        fake_dispatcher.dispatch_alert.assert_called_once()
        alert = fake_dispatcher.dispatch_alert.call_args.args[0]
        assert isinstance(alert, CatalystAlert)
        assert alert.city_id == "nyc"
        assert alert.alert_id == "alert-abc12345"

    def test_dispatch_failure_routes_to_dlq_and_loop_continues(self, worker, fake_dispatcher):
        fake_dispatcher.dispatch_alert.side_effect = RuntimeError("webhook down")
        worker.process_record(_alert_record(), settings.topic_catalyst_alerts, "k1")

        worker.dlq_producer.route_to_dlq.assert_called_once()
        kwargs = worker.dlq_producer.route_to_dlq.call_args.kwargs
        assert kwargs["failed_topic"] == settings.topic_catalyst_alerts
        assert kwargs["key"] == "k1"

        # A later good message still dispatches — the loop never dies.
        worker.process_record(_alert_record(), settings.topic_catalyst_alerts, "k2")
        assert fake_dispatcher.dispatch_alert.call_count == 2

    def test_calibration_or_budget_skip_is_not_a_failure(self, worker, fake_dispatcher):
        # WebhookDispatcher returns [] on calibration/budget skips.
        fake_dispatcher.dispatch_alert.return_value = []
        worker.process_record(_alert_record(), settings.topic_catalyst_alerts, "k1")
        worker.dlq_producer.route_to_dlq.assert_not_called()

    def test_malformed_payload_routes_to_dlq(self, worker, fake_dispatcher):
        worker.process_record({"lims_score": "not-a-number"}, settings.topic_catalyst_alerts, "bad")
        worker.dlq_producer.route_to_dlq.assert_called_once()
        fake_dispatcher.dispatch_alert.assert_not_called()

    def test_unknown_future_fields_are_dropped_not_fatal(self, worker, fake_dispatcher):
        worker.process_record(
            _alert_record(new_field_from_schema_evolution="x"),
            settings.topic_catalyst_alerts,
            "k1",
        )
        worker.dlq_producer.route_to_dlq.assert_not_called()
        alert = fake_dispatcher.dispatch_alert.call_args.args[0]
        assert alert.city_id == "nyc"

    def test_json_state_store_wired_when_configured(self, tmp_path):
        from src.serving.alert_state import JsonAlertStateStore

        with (
            patch("src.consumers.alert_dispatcher_worker.BaseKafkaConsumer"),
            patch("src.consumers.alert_dispatcher_worker.BaseKafkaProducer"),
        ):
            store = JsonAlertStateStore(tmp_path / "alert_state.json")
            w = AlertDispatcherWorker(state_store=store)
        assert w.dispatcher.state_store is store

    def test_default_state_store_in_memory_without_config(self):
        # No dispatcher injected and no ALERT_STATE_FILE configured:
        # restart-resets in-memory calibration.
        from src.serving.alert_state import InMemoryAlertStateStore

        with (
            patch("src.consumers.alert_dispatcher_worker.BaseKafkaConsumer"),
            patch("src.consumers.alert_dispatcher_worker.BaseKafkaProducer"),
        ):
            w = AlertDispatcherWorker()
        assert isinstance(w.dispatcher.state_store, InMemoryAlertStateStore)
