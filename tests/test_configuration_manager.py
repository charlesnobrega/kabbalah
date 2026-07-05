"""
Tests for Configuration Manager
"""

import json
import os
import tempfile

import pytest

from src.kabbalah.configuration_manager import (
    ConfigurationError,
    ConfigurationManager,
    ProviderConfig,
)


class TestConfigurationManager:
    """Test Configuration Manager"""

    def test_manager_initialization(self):
        """Test manager initialization"""
        manager = ConfigurationManager()
        assert manager is not None
        assert manager.config is not None

    def test_load_defaults(self):
        """Test loading default configuration"""
        manager = ConfigurationManager()
        manager.load_defaults()

        assert manager.config.mode == "DAY1"
        assert manager.config.environment == "development"
        assert manager.config.log_level == "INFO"
        assert manager.config.default_provider == "openai"

    def test_load_from_env(self):
        """Test loading from environment variables"""
        manager = ConfigurationManager()

        # Set environment variables
        os.environ["KABBALAH_MODE"] = "DAY2"
        os.environ["KABBALAH_ENV"] = "production"
        os.environ["KABBALAH_LOG_LEVEL"] = "DEBUG"

        try:
            manager.load_from_env()

            assert manager.config.mode == "DAY2"
            assert manager.config.environment == "production"
            assert manager.config.log_level == "DEBUG"
        finally:
            # Clean up
            del os.environ["KABBALAH_MODE"]
            del os.environ["KABBALAH_ENV"]
            del os.environ["KABBALAH_LOG_LEVEL"]

    def test_load_from_json_file(self):
        """Test loading from JSON file"""
        manager = ConfigurationManager()

        config_data = {
            "mode": "DAY2",
            "environment": "staging",
            "log_level": "WARNING",
            "default_provider": "groq",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            manager.load_from_file(temp_file)

            assert manager.config.mode == "DAY2"
            assert manager.config.environment == "staging"
            assert manager.config.log_level == "WARNING"
            assert manager.config.default_provider == "groq"
        finally:
            os.unlink(temp_file)

    def test_load_from_nonexistent_file(self):
        """Test loading from nonexistent file"""
        manager = ConfigurationManager()

        with pytest.raises(ConfigurationError):
            manager.load_from_file("/nonexistent/path/config.json")

    def test_set_config(self):
        """Test setting configuration values"""
        manager = ConfigurationManager()

        manager.set_config("mode", "BOOTSTRAP")
        assert manager.config.mode == "BOOTSTRAP"

        manager.set_config("log_level", "ERROR")
        assert manager.config.log_level == "ERROR"

    def test_set_invalid_config_key(self):
        """Test setting invalid configuration key"""
        manager = ConfigurationManager()

        with pytest.raises(ConfigurationError):
            manager.set_config("invalid_key", "value")

    def test_get_config(self):
        """Test getting configuration values"""
        manager = ConfigurationManager()
        manager.load_defaults()

        assert manager.get_config("mode") == "DAY1"
        assert manager.get_config("environment") == "development"

    def test_get_config_with_default(self):
        """Test getting configuration with default"""
        manager = ConfigurationManager()

        value = manager.get_config("nonexistent_key", "default_value")
        assert value == "default_value"

    def test_validate_valid_configuration(self):
        """Test validating valid configuration"""
        manager = ConfigurationManager()
        manager.load_defaults()

        assert manager.validate_configuration()

    def test_validate_invalid_mode(self):
        """Test validating invalid mode"""
        manager = ConfigurationManager()
        manager.config.mode = "INVALID"

        assert not manager.validate_configuration()

    def test_validate_invalid_environment(self):
        """Test validating invalid environment"""
        manager = ConfigurationManager()
        manager.load_defaults()
        manager.config.environment = "invalid"

        assert not manager.validate_configuration()

    def test_validate_invalid_log_level(self):
        """Test validating invalid log level"""
        manager = ConfigurationManager()
        manager.load_defaults()
        manager.config.log_level = "INVALID"

        assert not manager.validate_configuration()

    def test_validate_invalid_memory_backend(self):
        """Test validating invalid memory backend"""
        manager = ConfigurationManager()
        manager.load_defaults()
        manager.config.memory_backend = "invalid"

        assert not manager.validate_configuration()

    def test_validate_invalid_tool_timeout(self):
        """Test validating invalid tool timeout"""
        manager = ConfigurationManager()
        manager.load_defaults()
        manager.config.tool_timeout = -1

        assert not manager.validate_configuration()

    def test_to_dict(self):
        """Test converting configuration to dictionary"""
        manager = ConfigurationManager()
        manager.load_defaults()

        config_dict = manager.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["mode"] == "DAY1"
        assert config_dict["environment"] == "development"
        assert "providers" in config_dict

    def test_to_json(self):
        """Test converting configuration to JSON"""
        manager = ConfigurationManager()
        manager.load_defaults()

        json_str = manager.to_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["mode"] == "DAY1"

    def test_provider_configuration(self):
        """Test provider configuration"""
        manager = ConfigurationManager()

        provider = ProviderConfig(
            name="openai",
            api_key="test_key",
            model="gpt-4",
            timeout=60,
        )

        manager.config.providers["openai"] = provider

        assert manager.config.providers["openai"].name == "openai"
        assert manager.config.providers["openai"].api_key == "test_key"
        assert manager.config.providers["openai"].model == "gpt-4"

    def test_domain_provider_configuration(self):
        """Test domain-specific provider configuration"""
        manager = ConfigurationManager()

        manager.config.domain_providers["backend"] = "openai"
        manager.config.domain_providers["frontend"] = "groq"

        assert manager.config.domain_providers["backend"] == "openai"
        assert manager.config.domain_providers["frontend"] == "groq"

    def test_provider_fallback_chain(self):
        """Test provider fallback chain"""
        manager = ConfigurationManager()

        manager.config.provider_fallback_chain = ["openai", "groq", "mistral"]

        assert len(manager.config.provider_fallback_chain) == 3
        assert manager.config.provider_fallback_chain[0] == "openai"

    def test_load_from_file_with_providers(self):
        """Test loading configuration with providers"""
        manager = ConfigurationManager()

        config_data = {
            "mode": "DAY1",
            "environment": "development",
            "providers": {
                "openai": {
                    "api_key": "test_key",
                    "model": "gpt-4",
                    "timeout": 60,
                },
                "groq": {
                    "api_key": "groq_key",
                    "model": "mixtral",
                    "timeout": 30,
                },
            },
            "provider_fallback_chain": ["openai", "groq"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            manager.load_from_file(temp_file)

            assert "openai" in manager.config.providers
            assert "groq" in manager.config.providers
            assert manager.config.providers["openai"].model == "gpt-4"
            assert len(manager.config.provider_fallback_chain) == 2
        finally:
            os.unlink(temp_file)

    def test_environment_detection(self):
        """Test environment detection"""
        manager = ConfigurationManager()

        assert "platform" in manager.config.metadata
        assert manager.config.metadata["platform"] in ["windows", "macos", "linux"]

    def test_configuration_precedence(self):
        """Test configuration precedence"""
        manager = ConfigurationManager()

        # Load defaults
        manager.load_defaults()
        assert manager.config.mode == "DAY1"

        # Override with environment
        os.environ["KABBALAH_MODE"] = "DAY2"
        try:
            manager.load_from_env()
            assert manager.config.mode == "DAY2"
        finally:
            del os.environ["KABBALAH_MODE"]

    def test_provider_key_status_reports_presence_without_exposing_secret(self, monkeypatch):
        """Provider status must show only source and suffix, never full key."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-123456")
        manager = ConfigurationManager()

        status = manager.get_provider_key_status("openai")
        config_status = manager.get_config_status(provider_names=["openai"])
        serialized = json.dumps(config_status)

        assert status["provider"] == "openai"
        assert status["status"] == "present"
        assert status["source"] == "environment"
        assert status["last4"] == "3456"
        assert "sk-test-openai-123456" not in serialized

    def test_provider_key_status_uses_keyring_without_returning_value(self, monkeypatch):
        """Keyring-backed status should not expose stored secret material."""

        class FakeKeyring:
            def get_password(self, service_name, username):
                assert service_name == "kabbalah"
                assert username == "provider:groq_compatible"
                return "gsk-test-9999"

        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        manager = ConfigurationManager(keyring_backend=FakeKeyring())

        status = manager.get_provider_key_status("groq_compatible")

        assert status == {
            "provider": "groq_compatible",
            "status": "present",
            "source": "keyring",
            "last4": "9999",
            "env_names": ["GROQ_API_KEY", "KABBALAH_GROQ_COMPATIBLE_API_KEY"],
        }

    def test_set_provider_api_key_requires_secure_storage(self):
        """Tracked/local cleartext storage must not be offered for provider keys."""
        manager = ConfigurationManager(keyring_backend=None)

        with pytest.raises(ConfigurationError, match="keyring"):
            manager.set_provider_api_key("openai", "sk-test", storage="env")

    def test_installation_config_persists_budget_and_routing_without_secrets(self, tmp_path):
        """Non-secret installation settings may persist locally, secrets may not."""
        config_path = tmp_path / "install.json"
        manager = ConfigurationManager(keyring_backend=None, installation_config_path=config_path)

        manager.set_budget_limits(mode="block", run_limit_usd=1.5, daily_limit_usd=5.0)
        manager.set_routing_policy("budget_first")

        reloaded = ConfigurationManager(keyring_backend=None, installation_config_path=config_path)
        reloaded.load_installation_config()
        status = reloaded.get_config_status(provider_names=["openai"])
        serialized = json.dumps(status)
        persisted = json.loads(config_path.read_text(encoding="utf-8"))

        assert status["budget"]["mode"] == "block"
        assert status["budget"]["run_limit_usd"] == 1.5
        assert status["budget"]["daily_limit_usd"] == 5.0
        assert status["routing"]["policy"] == "budget_first"
        assert persisted == {
            "budget": {
                "daily_limit_usd": 5.0,
                "mode": "block",
                "run_limit_usd": 1.5,
            },
            "routing": {"policy": "budget_first"},
        }
        assert "sk-" not in serialized.lower()
        assert "secret-value" not in serialized.lower()

    def test_load_from_file_with_domain_providers(self):
        """Test loading configuration with domain providers"""
        manager = ConfigurationManager()

        config_data = {
            "mode": "DAY1",
            "domain_providers": {
                "backend": "openai",
                "frontend": "groq",
                "infrastructure": "mistral",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            manager.load_from_file(temp_file)

            assert manager.config.domain_providers["backend"] == "openai"
            assert manager.config.domain_providers["frontend"] == "groq"
            assert manager.config.domain_providers["infrastructure"] == "mistral"
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
