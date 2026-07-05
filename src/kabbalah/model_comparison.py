"""Model comparison service built on the canonical LLMGateway."""

from __future__ import annotations

from typing import Any, Optional

from .llm_gateway import LLMGateway, ProviderSelection


def compare_models(
    *,
    task: str,
    gateway: LLMGateway,
    providers: Optional[list[str]] = None,
    role: str = "Leaf_Builder",
    capability: str = "chat",
    max_tokens: int = 256,
    temperature: float = 0.2,
    timeout: float = 30.0,
    trace_id: str = "model-comparison",
) -> dict[str, Any]:
    """Compare multiple provider/model candidates on the same task.

    Provider selection and budget enforcement are delegated to ``LLMGateway``.
    Individual provider failures are returned as rows instead of being hidden
    behind synthetic/mock responses.
    """
    requested = list(dict.fromkeys(providers or []))
    selections = gateway.select_providers(
        role=role,
        capability=capability,
        trace_id=trace_id,
    )
    selected = _filter_selections(selections, requested)

    rows: list[dict[str, Any]] = []
    seen_requested: set[str] = set()
    for selection in selected:
        seen_requested.update({selection.profile.provider_name, selection.profile.name})
        rows.append(
            _execute_comparison(
                selection=selection,
                task=task,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
        )

    if requested:
        for provider in requested:
            if provider not in seen_requested:
                rows.append(
                    {
                        "provider": provider,
                        "profile": None,
                        "model": None,
                        "latency_ms": 0.0,
                        "tokens": 0,
                        "cost": 0.0,
                        "response": "",
                        "error": (
                            "Provider not available for this role/capability. "
                            "Run `kabbalah setup` or update the registry."
                        ),
                    }
                )

    return {
        "task": task,
        "role": role,
        "capability": capability,
        "comparisons": rows,
        "summary": {
            "provider_count": len(rows),
            "error_count": sum(1 for row in rows if row["error"]),
            "total_cost": sum(float(row["cost"]) for row in rows),
            "total_tokens": sum(int(row["tokens"]) for row in rows),
        },
    }


def _filter_selections(
    selections: list[ProviderSelection],
    requested: list[str],
) -> list[ProviderSelection]:
    if not requested:
        return selections
    requested_set = set(requested)
    return [
        selection
        for selection in selections
        if selection.profile.provider_name in requested_set or selection.profile.name in requested_set
    ]


def _execute_comparison(
    *,
    selection: ProviderSelection,
    task: str,
    max_tokens: int,
    temperature: float,
    timeout: float,
) -> dict[str, Any]:
    profile = selection.profile
    request = {
        "model": profile.model,
        "messages": [{"role": "user", "content": task}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        response = selection.provider.execute_request(request, timeout=timeout)
    except Exception as exc:
        return {
            "provider": profile.provider_name,
            "profile": profile.name,
            "model": profile.model,
            "latency_ms": 0.0,
            "tokens": 0,
            "cost": 0.0,
            "response": "",
            "error": str(exc),
        }

    return {
        "provider": profile.provider_name,
        "profile": profile.name,
        "model": response.model or profile.model,
        "latency_ms": response.latency_ms,
        "tokens": response.tokens_used,
        "cost": response.cost,
        "response": response.content,
        "error": response.error,
    }
