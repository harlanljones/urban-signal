from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.models import CatalystAlert
from src.serving.alert_state import InMemoryAlertStateStore
from src.serving.dispatcher import WebhookDispatcher


def _alert(city_id: str) -> CatalystAlert:
    return CatalystAlert(
        city_id=city_id,
        alert_id="alert-test",
        h3_index="892a1072893ffff",
        lims_score=90,
        predicted_delta_6m=0.1,
        predicted_delta_12m=0.2,
        macro_outperformance_prob_18m=0.9,
        centroid_lat=40.7,
        centroid_lng=-74,
    )


@pytest.mark.asyncio
async def test_new_city_alerts_fail_closed_until_calibration_unlock():
    store = InMemoryAlertStateStore()
    dispatcher = WebhookDispatcher(target_urls=["https://example.test/hook"], state_store=store)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        assert await dispatcher.dispatch_alert(_alert("boston")) == []
        post.assert_not_awaited()


@pytest.mark.asyncio
async def test_calibrated_new_city_alert_is_budget_limited():
    store = InMemoryAlertStateStore()
    store.save("boston", {"first_feature_date": "2026-01-01", "enabled": True})
    dispatcher = WebhookDispatcher(target_urls=["https://example.test/hook"], state_store=store)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = MagicMock(status_code=202)
        assert await dispatcher.dispatch_alert(_alert("boston")) == [202]
        post.assert_awaited_once()


@pytest.mark.asyncio
async def test_existing_city_remains_backward_compatible():
    dispatcher = WebhookDispatcher(target_urls=["https://example.test/hook"])
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = MagicMock(status_code=200)
        assert await dispatcher.dispatch_alert(_alert("nyc")) == [200]
