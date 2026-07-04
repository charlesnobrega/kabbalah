"""Tests for Bitwarden vault integration wrapper."""

import json

import pytest

from kabbalah.cofre import CACHE_TTL, CofreBitwarden, CofreError, CofreSecretNotFound, Segredo


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


def test_cofre_cache_enabled_reuses_secret_until_ttl(monkeypatch):
    payload = json.dumps({"fields": [{"name": "api_key", "value": "cached-secret"}]})
    runner = FakeRunner(payload)
    monkeypatch.setenv("BW_SESSION", "session-token")
    cofre = CofreBitwarden(runner=runner, use_cache=True)

    assert cofre.get_chave("service") == "cached-secret"
    assert cofre.get_chave("service") == "cached-secret"

    assert len(runner.calls) == 1
    assert CACHE_TTL == 300


def test_segredo_model_does_not_expose_value_in_repr():
    segredo = Segredo(item_name="service", field_name="api_key", value="real-secret")

    assert segredo.value == "real-secret"
    assert "real-secret" not in repr(segredo)


def test_bitwarden_cli_path_pins_the_binary(monkeypatch):
    payload = json.dumps({"fields": [{"name": "api_key", "value": "s"}]})
    runner = FakeRunner(payload)
    monkeypatch.setenv("BW_SESSION", "session-token")
    monkeypatch.setenv("BITWARDEN_CLI_PATH", "C:/pinned/bw.exe")
    cofre = CofreBitwarden(runner=runner)

    cofre.get_chave("service")

    assert runner.calls[0][0][0] == "C:/pinned/bw.exe"


def test_bw_binary_hash_mismatch_refuses_execution(monkeypatch, tmp_path):
    fake_bw = tmp_path / "bw.exe"
    fake_bw.write_bytes(b"not the real binary")
    monkeypatch.setenv("BW_SESSION", "session-token")
    monkeypatch.setenv("BITWARDEN_CLI_PATH", str(fake_bw))
    monkeypatch.setenv("KABBALAH_BW_SHA256", "0" * 64)
    cofre = CofreBitwarden(runner=FakeRunner("{}"))

    with pytest.raises(CofreError, match="hash mismatch"):
        cofre.get_chave("service")


def test_bw_binary_hash_match_allows_execution(monkeypatch, tmp_path):
    import hashlib

    fake_bw = tmp_path / "bw.exe"
    fake_bw.write_bytes(b"binary content")
    payload = json.dumps({"fields": [{"name": "api_key", "value": "s"}]})
    monkeypatch.setenv("BW_SESSION", "session-token")
    monkeypatch.setenv("BITWARDEN_CLI_PATH", str(fake_bw))
    monkeypatch.setenv("KABBALAH_BW_SHA256", hashlib.sha256(b"binary content").hexdigest())
    cofre = CofreBitwarden(runner=FakeRunner(payload))

    assert cofre.get_chave("service") == "s"


def test_clear_on_read_serves_cached_secret_once(monkeypatch):
    payload = json.dumps({"fields": [{"name": "api_key", "value": "critical"}]})
    runner = FakeRunner(payload)
    monkeypatch.setenv("BW_SESSION", "session-token")
    cofre = CofreBitwarden(runner=runner, use_cache=True, clear_on_read=True)

    assert cofre.get_chave("service") == "critical"
    assert cofre.get_chave("service") == "critical"
    assert cofre.get_chave("service") == "critical"

    assert len(runner.calls) == 2


def test_limpar_cache_drops_cached_values(monkeypatch):
    payload = json.dumps({"fields": [{"name": "api_key", "value": "v"}]})
    runner = FakeRunner(payload)
    monkeypatch.setenv("BW_SESSION", "session-token")
    cofre = CofreBitwarden(runner=runner, use_cache=True)

    cofre.get_chave("service")
    cofre.limpar_cache()
    cofre.get_chave("service")

    assert len(runner.calls) == 2
