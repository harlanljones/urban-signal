from datetime import UTC, date, datetime

from src.models.calibration import CityAlertState, calibration_report
from src.models.explainability import CatalystExplainer
from src.serving.alert_state import CityAlertBudget
from src.serving.alert_state import JsonAlertStateStore


def test_city_stays_disabled_during_60_day_warmup():
    report = calibration_report("boston", date(2026, 1, 1), date(2026, 2, 28), 1, 1, 2, 2)
    state = CityAlertState("boston")
    state.observe(date(2026, 1, 1))
    assert not state.apply_report(report)
    assert state.review_reason == "warmup_incomplete"


def test_unlock_requires_pinball_and_lims_gates():
    report = calibration_report("boston", date(2026, 1, 1), date(2026, 3, 1), 1.11, 1, .49, 1)
    assert not report.alert_enabled
    assert report.pinball_gate is False


def test_attribution_drift_requires_review():
    assert CatalystExplainer.attribution_drift({"permits": 1.26}, {"permits": 1}) == .26
    assert CatalystExplainer.requires_attribution_review({"permits": 1.26}, {"permits": 1})


def test_budget_is_per_city_and_resets_by_day():
    clock = [datetime(2026, 1, 1, tzinfo=UTC)]
    budget = CityAlertBudget(1, now=lambda: clock[0])
    assert budget.allow("a")
    assert not budget.allow("a")
    assert budget.allow("b")
    clock[0] = datetime(2026, 1, 2, tzinfo=UTC)
    assert budget.allow("a")


def test_city_alert_state_round_trips_through_durable_adapter(tmp_path):
    store = JsonAlertStateStore(tmp_path / "alert-state.json")
    state = CityAlertState("boston")
    state.observe(date(2026, 1, 1))
    state.persist(store)

    restored = CityAlertState.load("boston", store)
    assert restored.first_feature_date == date(2026, 1, 1)
    assert restored.enabled is False
