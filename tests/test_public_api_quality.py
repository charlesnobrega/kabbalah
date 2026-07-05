"""Public API quality checks for Onda 8.6."""

from __future__ import annotations

import ast
from pathlib import Path

PUBLIC_API_FILES = [
    Path("src/kabbalah/llm_gateway.py"),
    Path("src/kabbalah/hardware_profile.py"),
    Path("src/kabbalah/cofre.py"),
    Path("src/kabbalah/contratos.py"),
    Path("src/kabbalah/contrato_store.py"),
    Path("src/kabbalah/firewall_mcp.py"),
]


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _function_annotations(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    missing: list[str] = []
    args = [*function.args.args, *function.args.kwonlyargs]
    if function.args.vararg is not None:
        args.append(function.args.vararg)
    if function.args.kwarg is not None:
        args.append(function.args.kwarg)
    for arg in args:
        if arg.arg not in {"self", "cls"} and arg.annotation is None:
            missing.append(f"{function.name}.{arg.arg}")
    if function.returns is None:
        missing.append(f"{function.name}.return")
    return missing


def test_public_api_has_docstrings() -> None:
    """Ensure public classes and functions document their contract."""

    missing: list[str] = []
    for path in PUBLIC_API_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(node.name):
                if ast.get_docstring(node) is None:
                    missing.append(f"{path}:{node.name}")
            if isinstance(node, ast.ClassDef) and _is_public(node.name):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(child.name):
                        if ast.get_docstring(child) is None:
                            missing.append(f"{path}:{node.name}.{child.name}")

    assert missing == []


def test_public_api_has_type_hints() -> None:
    """Ensure public functions and methods expose typed call contracts."""

    missing: list[str] = []
    for path in PUBLIC_API_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(node.name):
                missing.extend(f"{path}:{item}" for item in _function_annotations(node))
            if isinstance(node, ast.ClassDef) and _is_public(node.name):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(child.name):
                        missing.extend(f"{path}:{node.name}.{item}" for item in _function_annotations(child))

    assert missing == []
