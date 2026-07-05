"""Tests for Kabbalah CLI commands."""

import json
import sys

from kabbalah import cli
from kabbalah.configuration_manager import ConfigurationManager
from kabbalah.onboarding import ProviderValidationResult


class FakeKeyring:
    def __init__(self):
        self.values = {}

    def get_password(self, service_name, username):
        return self.values.get((service_name, username))

    def set_password(self, service_name, username, value):
        self.values[(service_name, username)] = value

    def delete_password(self, service_name, username):
        self.values.pop((service_name, username), None)


class FakeValidator:
    def __init__(self):
        self.calls = []

    def validate(self, provider, api_key):
        self.calls.append((provider, api_key))
        return ProviderValidationResult(provider=provider, valid=True, message="ok")


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
    assert payload["result"]["hardware"]["active"] is False
    assert "sk-test-secret-7890" not in captured.out
    openai = next(
        provider
        for provider in payload["result"]["config"]["providers"]
        if provider["provider"] == "openai"
    )
    assert openai["last4"] == "7890"


def test_setup_command_validates_and_stores_key_without_printing_secret(monkeypatch, capsys, tmp_path):
    manager = ConfigurationManager(
        keyring_backend=FakeKeyring(),
        installation_config_path=tmp_path / "config.json",
    )
    validator = FakeValidator()
    monkeypatch.setattr(cli, "ConfigurationManager", lambda: manager)
    monkeypatch.setattr(cli, "ProviderKeyValidator", lambda: validator)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "sk-test-secret-1111")
    monkeypatch.setattr(sys, "argv", ["kabbalah", "setup", "--providers", "openai", "--json"])

    exit_code = cli.main()
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert validator.calls == [("openai", "sk-test-secret-1111")]
    assert manager.get_provider_key_status("openai")["last4"] == "1111"
    assert "sk-test-secret-1111" not in captured.out


def test_config_key_budget_and_routing_commands(monkeypatch, capsys, tmp_path):
    manager = ConfigurationManager(
        keyring_backend=FakeKeyring(),
        installation_config_path=tmp_path / "config.json",
    )
    validator = FakeValidator()
    monkeypatch.setattr(cli, "ConfigurationManager", lambda: manager)
    monkeypatch.setattr(cli, "ProviderKeyValidator", lambda: validator)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "gsk-test-secret-2222")

    monkeypatch.setattr(sys, "argv", ["kabbalah", "config", "add-key", "groq_compatible", "--json"])
    assert cli.main() == 0
    assert "gsk-test-secret-2222" not in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["kabbalah", "config", "test-key", "groq_compatible", "--json"])
    assert cli.main() == 0
    test_payload = json.loads(capsys.readouterr().out)
    assert test_payload["result"]["valid"] is True
    assert "gsk-test-secret-2222" not in json.dumps(test_payload)

    monkeypatch.setattr(
        sys,
        "argv",
        ["kabbalah", "config", "set-budget", "--mode", "block", "--run-usd", "1.25", "--daily-usd", "5", "--json"],
    )
    assert cli.main() == 0
    budget_payload = json.loads(capsys.readouterr().out)
    assert budget_payload["result"]["budget"]["mode"] == "block"
    assert budget_payload["result"]["budget"]["run_limit_usd"] == 1.25

    monkeypatch.setattr(sys, "argv", ["kabbalah", "config", "set-routing", "budget_first", "--json"])
    assert cli.main() == 0
    routing_payload = json.loads(capsys.readouterr().out)
    assert routing_payload["result"]["routing"]["policy"] == "budget_first"

    monkeypatch.setattr(sys, "argv", ["kabbalah", "config", "remove-key", "groq_compatible", "--json"])
    assert cli.main() == 0
    assert manager.get_provider_key_status("groq_compatible")["status"] == "absent"


def test_config_list_json_includes_hardware_status(monkeypatch, capsys, tmp_path):
    manager = ConfigurationManager(
        keyring_backend=FakeKeyring(),
        installation_config_path=tmp_path / "config.json",
    )
    monkeypatch.setenv("KABBALAH_BRIDGE_STATE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setattr(cli, "ConfigurationManager", lambda: manager)
    monkeypatch.setattr(sys, "argv", ["kabbalah", "config", "list", "--json"])

    assert cli.main() == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["result"]["hardware"] == {
        "active": False,
        "message": "No hardware profile recorded yet.",
    }
