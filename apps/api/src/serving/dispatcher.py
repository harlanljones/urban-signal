"""Asynchronous Webhook Alert Dispatcher for high-momentum catalyst parcels."""

import asyncio
import logging

import httpx

from src.config import settings
from src.schemas.models import CatalystAlert
from src.serving.alert_state import CityAlertBudget

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Dispatches real-time LIMS > 85.0 catalyst alerts to external endpoints (Slack/Discord/REST)."""

    def __init__(self, target_urls: list[str] | None = None, daily_alert_budget: int = 100,
                 alert_budget: CityAlertBudget | None = None):
        self.target_urls = target_urls if target_urls is not None else settings.webhook_alert_urls
        self.alert_budget = alert_budget or CityAlertBudget(daily_alert_budget)

    async def dispatch_alert(self, alert: CatalystAlert) -> list[int]:
        """Broadcast catalyst alert payload to all registered webhook URLs."""
        if not self.target_urls:
            logger.debug("No webhook URLs configured; skipping dispatch for alert %s", alert.alert_id)
            return []
        if not self.alert_budget.allow(alert.city_id):
            logger.warning("Alert budget exhausted for city %s; skipping %s", alert.city_id, alert.alert_id)
            return []

        payload = alert.model_dump(mode="json")
        status_codes = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [
                client.post(url, json=payload, headers={"Content-Type": "application/json"})
                for url in self.target_urls
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for url, resp in zip(self.target_urls, responses):
                if isinstance(resp, Exception):
                    logger.error("Failed to dispatch alert to %s: %s", url, resp)
                elif resp.status_code >= 400:
                    logger.warning("Webhook endpoint %s returned HTTP %d", url, resp.status_code)
                    status_codes.append(resp.status_code)
                else:
                    logger.info("Successfully dispatched catalyst alert %s to %s", alert.alert_id, url)
                    status_codes.append(resp.status_code)

        return status_codes
