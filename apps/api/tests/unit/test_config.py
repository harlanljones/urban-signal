from src.config import Settings


def test_empty_webhook_environment_value_is_treated_as_no_destinations():
    settings = Settings(_env_file=None, webhook_alert_urls="")

    assert settings.webhook_alert_urls == []
