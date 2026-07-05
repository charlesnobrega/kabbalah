"""Tests for SillyTavern group chat example artifacts."""

import json
from pathlib import Path


EXAMPLE_DIR = Path("docs/examples/sillytavern/kabbalah-group-chat")


def test_sillytavern_group_chat_examples_are_present_and_valid_json():
    cards = json.loads((EXAMPLE_DIR / "blank-cards.json").read_text(encoding="utf-8"))
    routing = json.loads((EXAMPLE_DIR / "group-chat-routing.json").read_text(encoding="utf-8"))

    card_names = {card["name"] for card in cards["cards"]}

    assert "Root Orchestrator" in card_names
    assert {"Backend Domain", "Security Domain", "QA Domain", "Docs Domain"}.issubset(card_names)
    assert "compare_models" in routing["mcp_tools"]
    assert "render_group_event" in routing["mcp_tools"]
    assert routing["reply_order"] == "manual_or_list_order"


def test_sillytavern_group_chat_readme_documents_mcp_only_setup():
    readme = (EXAMPLE_DIR / "README.md").read_text(encoding="utf-8")

    assert "MCP-only" in readme
    assert "Manual" in readme
    assert "render_group_event" in readme
    assert "[KABBALAH:HITL]" in readme
