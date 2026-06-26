"""Tests for Bitwarden vault integration wrapper."""

import json

import pytest

from kabbalah.cofre import CofreBitwarden, CofreError, CofreSecretNotFound


class FakeRunner:
    def __init__(self, payload, returncode=0, stderr=""):
        self.payload = payload
        self.returncode = returncode
        self.stderr = stderr
        self.calls = []

    def __call__(self, args, *, timeout, env):
        self.calls.append((args, timeout, env))

        class Result:
            pass

        result = Result()
        result.returncode = self.returncode
        result.stdout = self.payload
        result.stderr = self.stderr
        return result


def test_cofre_get_chave_reads_named_field_from_bitwarden_item(monkeypatch):
    payload = json.dumps(
        {
            "fields": [
                {"name": "OPENAI_API_KEY", "value": "test-secret"},
            ]
        }
    )
    runner = FakeRunner(payload)
    monkeypatch.setenv("BW_SESSION", "session-token")
    cofre = CofreBitwarden(runner=runner)

    value = cofre.get_chave("kabbalah-openai", field_name="OPENAI_API_KEY")

    assert value == "test-secret"
    assert runner.calls[0][0][:3] == ["bw", "get", "item"]
    assert runner.calls[0][2]["BW_SESSION"] == "session-token"


def test_cofre_missing_session_raises_error(monkeypatch):
    monkeypatch.delenv("BW_SESSION", raising=False)
    cofre = CofreBitwarden(runner=FakeRunner("{}"))

    with pytest.raises(CofreError, match="BW_SESSION"):
        cofre.get_chave("kabbalah-openai")


def test_cofre_missing_secret_field_raises_not_found(monkeypatch):
    monkeypatch.setenv("BW_SESSION", "session-token")
    cofre = CofreBitwarden(runner=FakeRunner(json.dumps({"fields": []})))

    with pytest.raises(CofreSecretNotFound):
        cofre.get_chave("kabbalah-openai", field_name="OPENAI_API_KEY")


def test_cofre_testar_conexao_returns_false_on_cli_failure(monkeypatch):
    monkeypatch.setenv("BW_SESSION", "session-token")
    cofre = CofreBitwarden(runner=FakeRunner("", returncode=1, stderr="not logged in"))

    assert cofre.testar_conexao() is False
