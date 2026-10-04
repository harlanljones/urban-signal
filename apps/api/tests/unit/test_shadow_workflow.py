"""Shadow execution must never inherit production publication privileges."""

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[4] / ".github/workflows/shadow-ingestion.yml"


def test_shadow_workflow_has_no_automatic_trigger():
    assert WORKFLOW.exists(), "manual shadow workflow has not been implemented"
    data = yaml.safe_load(WORKFLOW.read_text())
    triggers = data.get("on", data.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    assert data["permissions"] == {"contents": "read"}
    assert data["concurrency"]["cancel-in-progress"] is False


def test_shadow_jobs_are_main_only_and_storage_secrets_are_scoped():
    assert WORKFLOW.exists(), "manual shadow workflow has not been implemented"
    data = yaml.safe_load(WORKFLOW.read_text())
    assert "env" not in data
    for job in data["jobs"].values():
        assert "github.ref == 'refs/heads/main'" in job["if"]
    text = WORKFLOW.read_text()
    assert "CLOUDFLARE_API_TOKEN" not in text
    assert "WEBHOOK" not in text
    assert "kv bulk put" not in text
    assert "INGESTION_R2_ACCESS_KEY_ID" in text
    assert "INGESTION_R2_SECRET_ACCESS_KEY" in text
    assert "assert_ready" in text
    assert "probe_ingestion_store.py" in text
    assert "--mode" in text
