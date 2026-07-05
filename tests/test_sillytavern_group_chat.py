"""Tests for SillyTavern group chat event rendering."""

from kabbalah.sillytavern_group_chat import render_group_event


def test_render_group_event_formats_hitl_ticket_with_next_step():
    event = render_group_event(
        event_type="hitl",
        agent="Security",
        summary="Ação requer aprovação humana.",
        details={"acao": "execute_command", "risk": "high"},
        ticket_id="hitl_123",
        next_step="Use check_hitl_status.",
    )

    assert event["event_type"] == "hitl"
    assert event["display_text"].startswith("[KABBALAH:HITL] Security")
    assert "hitl_123" in event["display_text"]
    assert "Use check_hitl_status." in event["display_text"]


def test_render_group_event_redacts_secret_like_detail_values():
    event = render_group_event(
        event_type="config",
        agent="Config",
        summary="Provider key present.",
        details={"api_key": "sk-test-secret", "last4": "1234"},
    )

    assert event["details"]["api_key"] == "***REDACTED***"
    assert event["details"]["last4"] == "1234"
    assert "sk-test-secret" not in event["display_text"]


def test_render_group_event_rejects_unknown_event_type():
    event = render_group_event(
        event_type="unknown",
        agent="Coordinator",
        summary="Something happened.",
    )

    assert event["event_type"] == "error"
    assert event["display_text"].startswith("[KABBALAH:ERROR]")
