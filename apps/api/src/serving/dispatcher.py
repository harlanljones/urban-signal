"""Asynchronous Webhook Alert Dispatcher for high-momentum catalyst parcels."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping

import httpx

from src.config import settings
from src.schemas.models import CatalystAlert
from src.serving.alert_state import AlertStateStore, CityAlertBudget, InMemoryAlertStateStore

logger = logging.getLogger(__name__)

# These markets were added by the expansion roadmap and must remain quiet until
# their 60-day calibration and model-review gates are persisted as enabled.
CALIBRATION_REQUIRED_CITY_IDS = frozenset({
    "new_orleans", "norfolk", "detroit", "austin", "philadelphia", "cincinnati",
    "baton_rouge", "washington_dc", "boston", "denver", "baltimore", "montgomery",
    # Wave 3 (expansion-roadmap-wave-3.md §7): ship alert_enabled=false (calibrating).
    "phoenix", "miami_dade", "st_louis", "memphis", "albuquerque",
    # Wave 1/2 geocoder-unlocked + Pierce lane (same §7 rule).
    "honolulu", "orlando", "pierce",
})


class WebhookDispatcher:
    """Dispatches real-time LIMS > 85.0 catalyst alerts to external endpoints (Slack/Discord/REST)."""

    def __init__(self, target_urls: list[str] | None = None, daily_alert_budget: int = 100,
                 alert_budget: CityAlertBudget | None = None,
                 state_store: AlertStateStore | None = None,
                 city_states: Mapping[str, object] | None = None):
        self.target_urls = target_urls if target_urls is not None else settings.webhook_alert_urls
        self.alert_budget = alert_budget or CityAlertBudget(daily_alert_budget)
        self.state_store = state_store or InMemoryAlertStateStore()
        self.city_states = dict(city_states or {})

    def _city_alert_enabled(self, city_id: str) -> bool:
        """Fail closed for roadmap cities until calibration explicitly unlocks them."""
        if city_id not in CALIBRATION_REQUIRED_CITY_IDS:
            return True
        from src.models.calibration import CityAlertState

        state = self.city_states.get(city_id) or CityAlertState.load(city_id, self.state_store)
        return state.enabled

    async def dispatch_alert(self, alert: CatalystAlert) -> list[int]:
        """Broadcast catalyst alert payload to all registered webhook URLs."""
        if not self.target_urls:
            logger.debug("No webhook URLs configured; skipping dispatch for alert %s", alert.alert_id)
            return []
        if not self._city_alert_enabled(alert.city_id):
            logger.info("City %s remains in calibration; skipping alert %s", alert.city_id, alert.alert_id)
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
