from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _workflow() -> dict:
    with (ROOT / ".github" / "workflows" / "ci.yml").open(encoding="utf-8") as file_obj:
        return yaml.safe_load(file_obj)


def test_ci_workflow_runs_on_push_and_pull_request() -> None:
    workflow = _workflow()
    triggers = workflow.get("on", workflow.get(True))

    assert "push" in triggers
    assert "pull_request" in triggers


def test_ci_workflow_covers_supported_matrix() -> None:
    matrix = _workflow()["jobs"]["test"]["strategy"]["matrix"]

    assert set(matrix["os"]) == {"ubuntu-latest", "windows-latest"}
    assert set(matrix["python-version"]) == {"3.9", "3.11"}


def test_ci_workflow_runs_lint_tests_and_gitleaks() -> None:
    workflow = _workflow()
    test_steps = workflow["jobs"]["test"]["steps"]
    step_text = "\n".join(str(step) for step in test_steps)

    assert "ruff check" in step_text
    assert "pytest tests -q" in step_text
    assert "gitleaks/gitleaks-action" in str(workflow["jobs"]["gitleaks"])


def test_readme_uses_real_github_badges() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "actions/workflows/ci.yml/badge.svg" in readme
    assert "img.shields.io/github/v/tag/charlesnobrega/kabbalah" in readme
    assert "img.shields.io/github/license/charlesnobrega/kabbalah" in readme
