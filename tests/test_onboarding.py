"""Tests for setup/onboarding workflow."""

from kabbalah.configuration_manager import ConfigurationManager
from kabbalah.onboarding import ProviderValidationResult, run_setup_wizard

PROVIDER_ENV_KEYS = [
    "OPENAI_API_KEY",
    "KABBALAH_OPENAI_API_KEY",
    "GROQ_API_KEY",
    "KABBALAH_GROQ_API_KEY",
    "KABBALAH_GROQ_COMPATIBLE_API_KEY",
]


class FakeKeyring:
    def __init__(self):
        self.values = {}

    def get_password(self, service_name, username):
        return self.values.get((service_name, username))

    def set_password(self, service_name, username, value):
        self.values[(service_name, username)] = value


class FakeValidator:
    def __init__(self, valid=True):
        self.valid = valid
        self.calls = []

    def validate(self, provider, api_key):
        self.calls.append((provider, api_key))
        return ProviderValidationResult(
            provider=provider,
            valid=self.valid,
            message="ok" if self.valid else "invalid test key",
        )


def clear_provider_env(monkeypatch):
    for key in PROVIDER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_setup_wizard_validates_and_stores_provider_key_without_printing_secret(monkeypatch):
    clear_provider_env(monkeypatch)
    keyring = FakeKeyring()
    manager = ConfigurationManager(keyring_backend=keyring)
    outputs = []
    validator = FakeValidator(valid=True)

    result = run_setup_wizard(
        config_manager=manager,
        validator=validator,
        provider_names=["openai", "groq_compatible"],
        input_func=lambda prompt: "openai",
        secret_input_func=lambda prompt: "sk-test-secret-4321",
        output_func=outputs.append,
    )

    assert result["ok"] is True
    assert validator.calls == [("openai", "sk-test-secret-4321")]
    assert manager.get_provider_key_status("openai")["last4"] == "4321"
    assert "sk-test-secret-4321" not in "\n".join(outputs)


def test_setup_wizard_rejects_invalid_key_without_storing_it(monkeypatch):
    clear_provider_env(monkeypatch)
    keyring = FakeKeyring()
    manager = ConfigurationManager(keyring_backend=keyring)
    validator = FakeValidator(valid=False)

    result = run_setup_wizard(
        config_manager=manager,
        validator=validator,
        provider_names=["openai"],
        input_func=lambda prompt: "openai",
        secret_input_func=lambda prompt: "bad-key",
        output_func=lambda message: None,
    )

    assert result["ok"] is False
    assert manager.get_provider_key_status("openai")["status"] == "absent"
