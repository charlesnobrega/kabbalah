"""Tests for Kabbalah CLI commands."""

import json
import sys

from kabbalah import cli


def test_status_json_outputs_safe_config_and_budget(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-7890")
    monkeypatch.setenv("KABBALAH_BRIDGE_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setattr(sys, "argv", ["kabbalah", "status", "--json"])

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert "config" in payload["result"]
    assert "budget" in payload["result"]
    assert "sk-test-secret-7890" not in captured.out
    openai = next(
        provider
        for provider in payload["result"]["config"]["providers"]
        if provider["provider"] == "openai"
    )
    assert openai["last4"] == "7890"
