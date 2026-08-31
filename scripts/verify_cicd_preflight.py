"""CI/CD pre-flight gate — run before ending any task that changes repo files.

Every change in this repo breaks CI/CD consistently unless all gates pass
first.  The ``batch-push-deploy`` workflow runs the same checks on every
push/PR to ``main``; a failure blocks deployment.  Run this script at the
end of a task, not as a fixup afterward:

    python3 scripts/verify_cicd_preflight.py

Exit code 0 = all gates green.  First failure stops the run.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
API = REPO / "apps" / "api"
PRODUCT = REPO / "apps" / "product"
DASHBOARD_PY = API / "src" / "serving" / "dashboard.py"
DASHBOARD_HTML = REPO / "apps" / "dashboard" / "public" / "index.html"
FACTS_JSON = PRODUCT / "public" / "facts.json"
VENV_PYTHON = API / ".venv" / "bin" / "python"


def _run(cmd: list[str], cwd: str | None = None, label: str | None = None) -> None:
    tag = label or cmd[0]
    print(f"\n--- {tag} ", end="", flush=True)
    result = subprocess.run(cmd, cwd=cwd or str(REPO), capture_output=True, text=True)
    if result.returncode != 0:
        print("FAILED", flush=True)
        print(result.stdout)
        print(result.stderr)
        sys.exit(result.returncode)
    print("OK", flush=True)


def _api_python(cmd: list[str]) -> list[str]:
    """Run a Python command through the API virtualenv with PYTHONPATH set."""
    env = {**dict(PYTHONPATH=str(API))}
    return [str(VENV_PYTHON), *cmd]


def _metro_meta_ids(text: str) -> set[str]:
    """Extract the registered-city ids from a dashboard ``METRO_META`` block."""
    match = re.search(r"const METRO_META = \{(.*?)\n\s*\};", text, re.S)
    if not match:
        return set()
    return set(re.findall(r"^\s+(\w+): \{ name:", match.group(1), re.M))


def _check_cross_reference() -> None:
    """Dashboard <-> product-site cross-reference.

    A city change must land on BOTH surfaces consistently: the live dashboard
    (``serving/dashboard.py`` METRO_META + its byte-synced static copy) and the
    product site (``facts.json`` + ``cities/*.json``).  This gate fails when one
    surface was updated but the other was not.
    """
    from src.spatial.city_registry import REGISTRY
    from src.serving.dashboard import get_dashboard_html

    registry = {k.value for k in REGISTRY}
    # METRO_META is generated from REGISTRY (US-427) and no longer exists as a
    # literal in the source — read the dashboard side through its interface.
    dashboard_src = _metro_meta_ids(get_dashboard_html())
    dashboard_static = _metro_meta_ids(DASHBOARD_HTML.read_text())
    facts = {m["id"] for m in json.loads(FACTS_JSON.read_text())["metros"]}

    problems: list[str] = []
    if dashboard_src != registry:
        problems.append(
            "rendered dashboard METRO_META differs from REGISTRY "
            f"(missing={sorted(registry - dashboard_src)}, "
            f"extra={sorted(dashboard_src - registry)})"
        )
    if dashboard_static != dashboard_src:
        problems.append(
            "byte-synced apps/dashboard/public/index.html METRO_META differs from "
            "rendered get_dashboard_html() (missing="
            f"{sorted(dashboard_src - dashboard_static)}, "
            f"extra={sorted(dashboard_static - dashboard_src)})"
        )
    if facts != registry:
        problems.append(
            "product facts.json metros differ from REGISTRY "
            f"(missing={sorted(registry - facts)}, "
            f"extra={sorted(facts - registry)})"
        )
    if problems:
        print("FAILED", flush=True)
        print("\n".join(f"  - {p}" for p in problems))
        sys.exit(1)
    print("OK", flush=True)


def main() -> None:
    # ------------------------------------------------------------------ #
    # 1. API interlock gate                                               #
    # ------------------------------------------------------------------ #
    _run(
        _api_python(["-m", "pytest", "-q", "-m", "interlock", str(API / "tests" / "unit" / "test_interlock_gate.py")]),
        label="interlock gate",
    )

    # ------------------------------------------------------------------ #
    # 2. Dashboard ↔ product-site cross-reference                         #
    # ------------------------------------------------------------------ #
    print("\n--- dashboard ↔ product cross-ref ", end="", flush=True)
    _check_cross_reference()

    # ------------------------------------------------------------------ #
    # 3. Product facts drift                                              #
    # ------------------------------------------------------------------ #
    _run(
        ["bun", "run", "facts:check"],
        cwd=str(PRODUCT),
        label="product facts:check",
    )

    # ------------------------------------------------------------------ #
    # 4. Product site lint (build + verify-agent-surface + verify-multi-page) #
    # ------------------------------------------------------------------ #
    _run(
        ["bun", "run", "lint"],
        cwd=str(PRODUCT),
        label="product lint",
    )

    # ------------------------------------------------------------------ #
    # 5. Dashboard export (generate index.html from serving/dashboard.py, #
    #    then confirm byte-sync)                                           #
    # ------------------------------------------------------------------ #
    _run(
        _api_python([str(REPO / "scripts" / "export_dashboard.py")]),
        label="dashboard export",
    )

    # ------------------------------------------------------------------ #
    # 6. Ruff on CI-checked files + newly added Python                    #
    # ------------------------------------------------------------------ #
    # CI's batch-push-deploy ruff-checks a fixed file list; align with it
    # and additionally cover newly added (untracked/staged) Python files so a
    # new module with lint errors is caught before push.  Pre-existing
    # violations in long-lived files are out of scope for this gate.
    ci_ruff_files = [
        "scripts/feed_staleness_probe.py",
        "apps/api/src/producers/watermarks.py",
        "apps/api/tests/unit/test_feed_staleness_probe.py",
    ]
    added = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, cwd=str(REPO),
    ).stdout.splitlines()
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=A"],
        capture_output=True, text=True, cwd=str(REPO),
    ).stdout.splitlines()
    new_py = [
        f for f in added + staged
        if f.endswith(".py") and ("apps/api/src/" in f or "apps/api/tests/" in f)
    ]
    ruff_targets = ci_ruff_files + sorted(set(new_py))
    _run(["ruff", "check", *ruff_targets], label="ruff check")

    print("\n✓ CI/CD pre-flight green — all gates pass", flush=True)


if __name__ == "__main__":
    main()