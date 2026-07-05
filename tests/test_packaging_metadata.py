from __future__ import annotations

import ast
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.9/3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


def _read_pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as file_obj:
        return tomllib.load(file_obj)


def _package_version() -> str:
    module = ast.parse((ROOT / "src" / "kabbalah" / "__init__.py").read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    assert isinstance(node.value, ast.Constant)
                    assert isinstance(node.value.value, str)
                    return node.value.value
    raise AssertionError("__version__ is not defined in kabbalah.__init__")


def test_pyproject_is_the_packaging_source_of_truth() -> None:
    metadata = _read_pyproject()

    assert metadata["project"]["name"] == "kabbalah"
    assert metadata["project"]["dynamic"] == ["version"]
    assert metadata["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "kabbalah.__version__"
    assert metadata["project"]["scripts"]["kabbalah"] == "kabbalah.cli:main"


def test_package_version_is_single_sourced() -> None:
    version = _package_version()
    setup_text = (ROOT / "setup.py").read_text(encoding="utf-8")
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert re.fullmatch(r"0\.\d+\.\d+", version)
    assert "version=" not in setup_text
    assert version not in pyproject_text


def test_optional_extras_are_formalized() -> None:
    extras = _read_pyproject()["project"]["optional-dependencies"]

    assert {"mcp", "memory", "observability"}.issubset(extras)
    assert any(dep.startswith("mcp") for dep in extras["mcp"])
    assert any(dep.startswith("cognee") for dep in extras["memory"])
    assert "opentelemetry-exporter-prometheus==0.64b0" in extras["observability"]


def test_google_provider_transitives_are_constrained_for_extras() -> None:
    dependencies = set(_read_pyproject()["project"]["dependencies"])

    assert "protobuf==3.20.3" in dependencies
    assert "google-api-core==1.34.1" in dependencies
    assert "googleapis-common-protos>=1.57,<2.0dev" in dependencies
    assert "grpcio-status==1.48.2" in dependencies


def test_memory_extra_allows_cognee_dependency_ranges() -> None:
    metadata = _read_pyproject()
    dependencies = set(metadata["project"]["dependencies"])
    memory_dependencies = set(metadata["project"]["optional-dependencies"]["memory"])

    assert "openai>=1.80.1,<3.0.0" in dependencies
    assert "requests>=2.31.0,<3.0.0" in dependencies
    assert "click>=8.1.7,<9.0.0" in dependencies
    assert "openai==2.30.0" in memory_dependencies
    assert "requests==2.34.2" in memory_dependencies
    assert "litellm==1.83.7" in memory_dependencies
    assert "click==8.1.8" in memory_dependencies


def test_changelog_records_wave_history() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "# Changelog" in changelog
    assert "0.8.0" in changelog
    assert "Onda 8" in changelog
