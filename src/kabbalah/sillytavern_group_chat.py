"""SillyTavern group chat event rendering helpers."""

from __future__ import annotations

from typing import Any, Mapping


EVENT_PREFIXES = {
    "allow": "[KABBALAH:ALLOW]",
    "deny": "[KABBALAH:DENY]",
    "hitl": "[KABBALAH:HITL]",
    "budget": "[KABBALAH:BUDGET]",
    "config": "[KABBALAH:CONFIG]",
    "error": "[KABBALAH:ERROR]",
}

SECRET_MARKERS = ("secret", "token", "password", "api_key", "apikey", "credential", "senha", "chave")


def render_group_event(
    *,
    event_type: str,
    agent: str,
    summary: str,
    details: Mapping[str, Any] | None = None,
    ticket_id: str | None = None,
    next_step: str | None = None,
) -> dict[str, Any]:
    """Render a Kabbalah status event for a SillyTavern group chat."""
    normalized_type = event_type.lower().strip()
    if normalized_type not in EVENT_PREFIXES:
        normalized_type = "error"

    safe_details = _sanitize_details(details or {})
    prefix = EVENT_PREFIXES[normalized_type]
    parts = [f"{prefix} {agent}: {summary}"]
    if ticket_id:
        parts.append(f"Ticket: {ticket_id}")
    if next_step:
        parts.append(f"Next: {next_step}")
    if safe_details:
        details_text = "; ".join(f"{key}={value}" for key, value in sorted(safe_details.items()))
        parts.append(f"Details: {details_text}")

    return {
        "event_type": normalized_type,
        "agent": agent,
        "summary": summary,
        "details": safe_details,
        "ticket_id": ticket_id,
        "next_step": next_step,
        "display_text": " | ".join(parts),
    }


def _sanitize_details(details: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in details.items():
        key_text = str(key)
        if any(marker in key_text.lower() for marker in SECRET_MARKERS):
            safe[key_text] = "***REDACTED***"
        else:
            safe[key_text] = value
    return safe
