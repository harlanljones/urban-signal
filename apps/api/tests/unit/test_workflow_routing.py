"""Routing contracts for the batch snapshot and dashboard release workflows."""

from __future__ import annotations

import fnmatch
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
WORKFLOWS = ROOT / ".github" / "workflows"


class GitHubActionsLoader(yaml.SafeLoader):
    """Safe YAML loader that keeps GitHub's unquoted ``on`` key as a string."""


GitHubActionsLoader.yaml_implicit_resolvers = {
    key: [
        (tag, pattern)
        for tag, pattern in resolvers
        if tag != "tag:yaml.org,2002:bool"
    ]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
GitHubActionsLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    yaml.SafeLoader.yaml_implicit_resolvers["o"][0][1],
    list("tTfF"),
)


def load_workflow(filename: str) -> dict:
    return yaml.load((WORKFLOWS / filename).read_text(), Loader=GitHubActionsLoader)


def ref(branch: str) -> str:
    return f"refs/heads/{branch}"


def expression_matches(expression: str, *, event: str, git_ref: str) -> bool:
    """Evaluate the simple event/ref boolean expressions used by job gates."""
    value = expression.replace("${{", "").replace("}}", "").replace("always()", "True")
    value = value.replace("needs.validate.result == 'success'", "True")
    value = value.replace("needs.validate.result == 'skipped'", "False")
    value = value.replace("github.event_name", repr(event))
    value = value.replace("github.ref", repr(git_ref))
    value = value.replace("&&", " and ").replace("||", " or ")
    return bool(eval(value, {"__builtins__": {}}, {}))


def trigger_matches(workflow: dict, event: str, branch: str, changed_paths: list[str]) -> bool:
    if event not in workflow["on"]:
        return False
    trigger = workflow["on"][event]
    if isinstance(trigger, list):
        return True
    if not isinstance(trigger, dict):
        return True
    if trigger.get("branches") and branch not in trigger["branches"]:
        return False
    path_patterns = trigger.get("paths")
    return not path_patterns or any(
        fnmatch.fnmatch(path, pattern) for path in changed_paths for pattern in path_patterns
    )


def test_actions_yaml_loader_preserves_on_key_as_mapping():
    workflow = load_workflow("batch-push.yml")

    assert "on" in workflow
    assert isinstance(workflow["on"], dict)


def test_snapshot_kv_mutation_is_limited_to_main_schedule_or_manual_dispatch():
    workflow = load_workflow("batch-push.yml")
    snapshot_gate = workflow["jobs"]["snapshot-push"]["if"]

    cases = [
        ("pull_request", ref("feature"), False),
        ("push", ref("main"), False),
        ("schedule", ref("main"), True),
        ("workflow_dispatch", ref("main"), True),
        ("workflow_dispatch", ref("feature"), False),
    ]
    for event, git_ref, expected in cases:
        assert expression_matches(snapshot_gate, event=event, git_ref=git_ref) is expected

    assert workflow["name"] == "batch-push-deploy"
    assert "validate" in workflow["jobs"]
    assert workflow["on"]["schedule"][0]["cron"] == "0 6 * * *"
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert "deploy-dashboard" not in workflow["jobs"]


def test_batch_check_runs_on_pr_and_push_without_docs_only_noise():
    workflow = load_workflow("batch-push.yml")

    assert trigger_matches(workflow, "pull_request", "feature", ["apps/api/src/main.py"])
    assert trigger_matches(workflow, "push", "main", ["apps/api/src/main.py"])
    assert not trigger_matches(workflow, "push", "main", ["README.md"])
    assert not trigger_matches(workflow, "push", "main", ["docs/guide.md"])
    assert not trigger_matches(workflow, "pull_request", "feature", ["docs/guide.md"])


def test_dashboard_release_routes_only_relevant_main_changes_and_manual_main():
    workflow = load_workflow("dashboard-deploy.yml")
    trigger_paths = workflow["on"]["push"]["paths"]

    assert trigger_matches(workflow, "push", "main", ["apps/dashboard/src/app.js"])
    assert trigger_matches(workflow, "push", "main", ["apps/api/src/serving/dashboard.py"])
    assert trigger_matches(workflow, "push", "main", ["apps/api/src/spatial/city_registry.py"])
    assert trigger_matches(workflow, "push", "main", ["scripts/export_dashboard.py"])
    assert trigger_matches(workflow, "push", "main", ["packages/shared/package.json"])
    assert trigger_matches(workflow, "push", "main", ["bun.lock"])
    assert trigger_matches(workflow, "push", "main", ["turbo.json"])
    assert trigger_matches(workflow, "push", "main", [".github/workflows/batch-push.yml"])
    assert trigger_matches(workflow, "push", "main", [".github/workflows/dashboard-deploy.yml"])
    assert not trigger_matches(workflow, "push", "feature", ["apps/dashboard/src/app.js"])
    assert not trigger_matches(workflow, "push", "main", ["README.md"])
    assert not trigger_matches(workflow, "push", "main", ["docs/guide.md"])
    assert trigger_matches(workflow, "workflow_dispatch", "main", [])
    assert trigger_matches(workflow, "workflow_dispatch", "feature", [])
    assert not expression_matches(
        workflow["jobs"]["validate"]["if"],
        event="workflow_dispatch",
        git_ref=ref("feature"),
    )
    assert "apps/api/src/spatial/**" in trigger_paths


def test_dashboard_release_validates_zoom_interlock_web_and_uses_no_snapshot_dependency():
    workflow = load_workflow("dashboard-deploy.yml")
    validation = workflow["jobs"]["validate"]
    validation_text = "\n".join(
        step.get("name", "") + "\n" + step.get("run", "")
        for step in validation["steps"]
    )

    assert "grid-zoom.test.js" in validation_text
    assert "-m interlock" in validation_text
    assert "bun run build && bun run typecheck && bun run lint" in validation_text
    assert workflow["jobs"]["deploy-dashboard"]["needs"] == "validate"
    assert workflow["jobs"]["deploy-dashboard"]["if"]
    assert workflow["concurrency"]["cancel-in-progress"] is False


def test_manual_refresh_uses_lightweight_python_checks_and_metrics_artifact():
    workflow = load_workflow("batch-push.yml")
    validation_steps = workflow["jobs"]["validate"]["steps"]
    validation_text = "\n".join(step.get("name", "") + "\n" + step.get("run", "") for step in validation_steps)

    assert "-m interlock" in validation_text
    code_only_steps = [
        step
        for step in validation_steps
        if step.get("name") in {"Install JavaScript dependencies", "Check web packages", "Check dashboard zoom regressions"}
        or step.get("uses", "").startswith("oven-sh/setup-bun@")
    ]
    assert len(code_only_steps) == 4
    assert all(step["if"] == "github.event_name == 'push' || github.event_name == 'pull_request'" for step in code_only_steps)
    metric_artifact = next(
        step
        for step in workflow["jobs"]["snapshot-push"]["steps"]
        if step.get("name") == "Preserve snapshot metrics"
    )
    assert "build/snapshot-metrics.json" in metric_artifact["with"]["path"]
    assert any(
        "--metrics-out build/snapshot-metrics.json" in step.get("run", "")
        for step in workflow["jobs"]["snapshot-push"]["steps"]
    )
    assert workflow["jobs"]["snapshot-push"]["if"]


def test_cloudflare_secrets_are_scoped_to_write_jobs():
    batch = load_workflow("batch-push.yml")
    dashboard = load_workflow("dashboard-deploy.yml")

    for workflow in (batch, dashboard):
        assert "env" not in workflow
        assert "CLOUDFLARE_API_TOKEN" not in str(workflow["jobs"]["validate"])
        assert "CLOUDFLARE_ACCOUNT_ID" not in str(workflow["jobs"]["validate"])
    for workflow in (batch, dashboard):
        for job_name, job in workflow["jobs"].items():
            env = job.get("env", {})
            if "CLOUDFLARE_API_TOKEN" in env:
                assert job_name in {"snapshot-push", "deploy-dashboard"}
                assert "CLOUDFLARE_ACCOUNT_ID" in env
