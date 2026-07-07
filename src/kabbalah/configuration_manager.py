"""
Configuration Manager

Manages system configuration from multiple sources with precedence.
"""

import json
import logging
import os
import platform
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SECRET_KEY_MARKERS = ("api_key", "apikey", "private_key", "password", "secret", "token", "credential", "senha")


class ConfigurationSource(Enum):
    """Configuration sources"""

    ENVIRONMENT = "environment"
    FILE = "file"
    CLI = "cli"
    DEFAULT = "default"


class ConfigurationError(Exception):
    """Raised when configuration fails"""

    pass


def _reject_secret_like_payload(value: Any, *, path: str = "config") -> None:
    """Prevent accidental persistence of secret-looking installation settings."""
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if any(marker in key_text for marker in _SECRET_KEY_MARKERS):
                raise ConfigurationError(f"Refusing to persist secret-like key at {path}.{key}")
            _reject_secret_like_payload(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_secret_like_payload(item, path=f"{path}[{index}]")


@dataclass
class ProviderConfig:
    """Provider configuration"""

    name: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    endpoint: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    cost_per_1k_tokens: float = 0.0


@dataclass
class Configuration:
    """System configuration"""

    mode: str = "DAY1"
    environment: str = "development"
    log_level: str = "INFO"

    # Provider configuration
    default_provider: str = "openai"
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    provider_fallback_chain: List[str] = field(default_factory=list)

    # Per-domain provider configuration
    domain_providers: Dict[str, str] = field(default_factory=dict)

    # Memory configuration
    memory_backend: str = "cognee"
    memory_max_size: int = 1000000

    # Tool execution configuration
    tool_timeout: int = 300
    tool_max_retries: int = 3

    # Observability configuration
    observability_enabled: bool = True
    trace_sampling_rate: float = 1.0

    # Resource limits
    max_concurrent_tasks: int = 10
    max_memory_mb: int = 4096

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigurationManager:
    """
    Manages system configuration from multiple sources.

    Features:
    - Load from environment variables
    - Load from JSON/YAML files
    - Load from CLI arguments
    - Configuration precedence
    - Per-domain provider configuration
    - Validation and defaults
    """

    # Default configuration
    DEFAULTS = {
        "mode": "DAY1",
        "environment": "development",
        "log_level": "INFO",
        "default_provider": "openai",
        "memory_backend": "cognee",
        "tool_timeout": 300,
        "tool_max_retries": 3,
        "observability_enabled": True,
        "trace_sampling_rate": 1.0,
        "max_concurrent_tasks": 10,
        "max_memory_mb": 4096,
    }

    PROVIDER_KEY_ENVS = {
        "openai": ["OPENAI_API_KEY", "KABBALAH_OPENAI_API_KEY"],
        "google_gemini": [
            "GOOGLE_GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "KABBALAH_GOOGLE_GEMINI_API_KEY",
        ],
        "groq": ["GROQ_API_KEY", "KABBALAH_GROQ_API_KEY"],
        "groq_compatible": ["GROQ_API_KEY", "KABBALAH_GROQ_COMPATIBLE_API_KEY"],
        "mistral": ["MISTRAL_API_KEY", "KABBALAH_MISTRAL_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY", "KABBALAH_DEEPSEEK_API_KEY"],
        "together": ["TOGETHER_API_KEY", "KABBALAH_TOGETHER_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY", "KABBALAH_OPENROUTER_API_KEY"],
        "cerebras": ["CEREBRAS_API_KEY", "KABBALAH_CEREBRAS_API_KEY"],
        "sambanova": ["SAMBANOVA_API_KEY", "KABBALAH_SAMBANOVA_API_KEY"],
    }

    _AUTO_KEYRING = object()

    def __init__(
        self,
        *,
        keyring_backend: Any = _AUTO_KEYRING,
        installation_config_path: Optional[str | Path] = None,
    ):
        """Initialize configuration manager"""
        self.config = Configuration()
        self.sources: Dict[str, ConfigurationSource] = {}
        self._keyring = self._load_keyring() if keyring_backend is self._AUTO_KEYRING else keyring_backend
        self.installation_config_path = Path(
            installation_config_path
            or os.environ.get("KABBALAH_INSTALL_CONFIG_PATH", str(Path.home() / ".kabbalah" / "config.json"))
        )
        self.installation_settings: Dict[str, Any] = {
            "budget": {},
            "network": {"mode": "off", "trust_list": []},
            "routing": {"policy": "balanced"},
        }
        self._detect_environment()

    @staticmethod
    def _load_keyring() -> Any:
        """Return the optional keyring backend when installed."""
        try:
            import keyring  # type: ignore[import-not-found]
        except Exception:
            return None
        return keyring

    def _detect_environment(self) -> None:
        """Detect runtime environment"""
        system = platform.system()
        if system == "Windows":
            self.config.metadata["platform"] = "windows"
        elif system == "Darwin":
            self.config.metadata["platform"] = "macos"
        else:
            self.config.metadata["platform"] = "linux"

    def load_defaults(self) -> None:
        """Load default configuration"""
        for key, value in self.DEFAULTS.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.sources[key] = ConfigurationSource.DEFAULT

        logger.debug("Default configuration loaded")

    def load_from_env(self) -> None:
        """Load configuration from environment variables"""
        # Mode
        if "KABBALAH_MODE" in os.environ:
            self.config.mode = os.environ["KABBALAH_MODE"]
            self.sources["mode"] = ConfigurationSource.ENVIRONMENT

        # Environment
        if "KABBALAH_ENV" in os.environ:
            self.config.environment = os.environ["KABBALAH_ENV"]
            self.sources["environment"] = ConfigurationSource.ENVIRONMENT

        # Log level
        if "KABBALAH_LOG_LEVEL" in os.environ:
            self.config.log_level = os.environ["KABBALAH_LOG_LEVEL"]
            self.sources["log_level"] = ConfigurationSource.ENVIRONMENT

        # Default provider
        if "KABBALAH_DEFAULT_PROVIDER" in os.environ:
            self.config.default_provider = os.environ["KABBALAH_DEFAULT_PROVIDER"]
            self.sources["default_provider"] = ConfigurationSource.ENVIRONMENT

        # Memory backend
        if "KABBALAH_MEMORY_BACKEND" in os.environ:
            self.config.memory_backend = os.environ["KABBALAH_MEMORY_BACKEND"]
            self.sources["memory_backend"] = ConfigurationSource.ENVIRONMENT

        # Tool timeout
        if "KABBALAH_TOOL_TIMEOUT" in os.environ:
            try:
                self.config.tool_timeout = int(os.environ["KABBALAH_TOOL_TIMEOUT"])
                self.sources["tool_timeout"] = ConfigurationSource.ENVIRONMENT
            except ValueError:
                logger.warning("Invalid KABBALAH_TOOL_TIMEOUT value")

        # Provider API keys
        for provider in ["openai", "anthropic", "google", "groq", "mistral", "deepseek", "together"]:
            env_key = f"KABBALAH_{provider.upper()}_API_KEY"
            if env_key in os.environ:
                if provider not in self.config.providers:
                    self.config.providers[provider] = ProviderConfig(name=provider)
                self.config.providers[provider].api_key = os.environ[env_key]

        logger.debug("Environment configuration loaded")

    def load_from_file(self, filepath: str) -> None:
        """
        Load configuration from JSON/YAML file.

        Args:
            filepath: Path to configuration file
        """
        if not os.path.exists(filepath):
            raise ConfigurationError(f"Configuration file not found: {filepath}")

        try:
            with open(filepath, "r") as f:
                if filepath.endswith(".json"):
                    data = json.load(f)
                elif filepath.endswith(".yaml") or filepath.endswith(".yml"):
                    import yaml

                    data = yaml.safe_load(f)
                else:
                    raise ConfigurationError(f"Unsupported file format: {filepath}")

            self._apply_config_dict(data, ConfigurationSource.FILE)
            logger.debug(f"Configuration loaded from {filepath}")

        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {filepath}: {str(e)}") from e

    def load_installation_config(self) -> None:
        """Load non-secret installation settings from the user config file."""
        if not self.installation_config_path.exists():
            return
        try:
            with open(self.installation_config_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            raise ConfigurationError(f"Failed to load installation config: {exc}") from exc
        self.installation_settings["budget"] = dict(data.get("budget", {}))
        self.installation_settings["network"] = dict(data.get("network", {"mode": "off", "trust_list": []}))
        self.installation_settings["routing"] = dict(data.get("routing", {"policy": "balanced"}))

    def save_installation_config(self) -> None:
        """Persist non-secret installation settings to the user config file."""
        _reject_secret_like_payload(self.installation_settings)
        self.installation_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.installation_config_path, "w", encoding="utf-8") as handle:
            json.dump(self.installation_settings, handle, ensure_ascii=False, indent=2, sort_keys=True)

    def _apply_config_dict(self, data: Dict[str, Any], source: ConfigurationSource) -> None:
        """
        Apply configuration from dictionary.

        Args:
            data: Configuration dictionary
            source: Configuration source
        """
        for key, value in data.items():
            if key == "providers" and isinstance(value, dict):
                for provider_name, provider_config in value.items():
                    if isinstance(provider_config, dict):
                        self.config.providers[provider_name] = ProviderConfig(name=provider_name, **provider_config)
            elif key == "domain_providers" and isinstance(value, dict):
                self.config.domain_providers.update(value)
            elif key == "provider_fallback_chain" and isinstance(value, list):
                self.config.provider_fallback_chain = value
            elif hasattr(self.config, key):
                setattr(self.config, key, value)
                self.sources[key] = source

    def set_config(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self.sources[key] = ConfigurationSource.CLI
        else:
            raise ConfigurationError(f"Unknown configuration key: {key}")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value
        """
        if hasattr(self.config, key):
            return getattr(self.config, key)
        return default

    def get_provider_key_status(self, provider: str) -> Dict[str, Any]:
        """
        Return provider credential status without exposing the credential value.

        The lookup order is environment, OS keyring, then in-memory/file
        configuration for backward compatibility. Only the last four characters
        are exposed for human confirmation.
        """
        env_names = self._provider_env_names(provider)
        for env_name in env_names:
            value = os.environ.get(env_name)
            if value:
                return self._provider_status(
                    provider=provider,
                    status="present",
                    source="environment",
                    last4=self._last4(value),
                    env_names=env_names,
                )

        keyring_value = self._get_keyring_provider_api_key(provider)
        if keyring_value:
            return self._provider_status(
                provider=provider,
                status="present",
                source="keyring",
                last4=self._last4(keyring_value),
                env_names=env_names,
            )

        configured = self.config.providers.get(provider)
        if configured and configured.api_key:
            return self._provider_status(
                provider=provider,
                status="present",
                source="configuration",
                last4=self._last4(configured.api_key),
                env_names=env_names,
            )

        return self._provider_status(
            provider=provider,
            status="absent",
            source="none",
            last4=None,
            env_names=env_names,
        )

    def get_config_status(self, *, provider_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Return safe installation/configuration status for humans and MCP."""
        names = provider_names or sorted(set(self.PROVIDER_KEY_ENVS) | set(self.config.providers))
        budget_settings = self.installation_settings.get("budget", {})
        network_settings = self.installation_settings.get("network", {"mode": "off", "trust_list": []})
        routing_settings = self.installation_settings.get("routing", {"policy": "balanced"})
        return {
            "mode": self.config.mode,
            "environment": self.config.environment,
            "default_provider": self.config.default_provider,
            "providers": [self.get_provider_key_status(provider) for provider in names],
            "storage": {
                "keyring_available": self._keyring is not None,
                "keyring_service": "kabbalah",
                "bitwarden_supported": True,
                "tracked_cleartext_supported": False,
            },
            "budget": {
                "mode": budget_settings.get("mode", os.environ.get("KABBALAH_BUDGET_MODE", "warn")),
                "run_limit_usd": budget_settings.get("run_limit_usd", os.environ.get("KABBALAH_BUDGET_RUN_USD")),
                "daily_limit_usd": budget_settings.get("daily_limit_usd", os.environ.get("KABBALAH_BUDGET_DAILY_USD")),
                "provider_limits_usd": budget_settings.get("provider_limits_usd", {}),
            },
            "routing": {
                "policy": routing_settings.get("policy", "balanced"),
            },
            "network": {
                "mode": network_settings.get("mode", "off"),
                "public_key": network_settings.get("public_key"),
                "publisher_id": network_settings.get("publisher_id"),
                "trusted_publishers": len(network_settings.get("trust_list", [])),
            },
        }

    def set_provider_api_key(self, provider: str, api_key: str, *, storage: str = "keyring") -> None:
        """Store a provider API key in the configured secure backend."""
        if not provider:
            raise ConfigurationError("Provider name is required")
        if not api_key:
            raise ConfigurationError("API key is required")
        if storage != "keyring":
            raise ConfigurationError(
                "Provider API keys must be stored in keyring or Bitwarden; "
                "tracked files, stdout, logs, and local cleartext env files are not allowed."
            )
        if self._keyring is None:
            raise ConfigurationError(
                "keyring backend is not available. Install keyring or use Bitwarden via CofreBitwarden."
            )
        self._keyring.set_password("kabbalah", self._keyring_provider_username(provider), api_key)

    def remove_provider_api_key(self, provider: str, *, storage: str = "keyring") -> None:
        """Remove a provider API key from the configured secure backend."""
        if storage != "keyring":
            raise ConfigurationError("Only keyring removal is supported by ConfigurationManager")
        if self._keyring is None:
            raise ConfigurationError("keyring backend is not available")
        try:
            self._keyring.delete_password("kabbalah", self._keyring_provider_username(provider))
        except Exception as exc:
            raise ConfigurationError(f"Failed to remove provider key from keyring: {exc}") from exc

    def get_provider_api_key(self, provider: str) -> Optional[str]:
        """Return a provider key for internal validation without printing it."""
        for env_name in self._provider_env_names(provider):
            value = os.environ.get(env_name)
            if value:
                return value
        return self._get_keyring_provider_api_key(provider)

    def ensure_federation_identity(self) -> Dict[str, str]:
        """Generate or return this installation's Ed25519 federation identity."""

        if self._keyring is None:
            raise ConfigurationError("keyring backend is required for federation private keys")
        network = dict(self.installation_settings.get("network", {"mode": "off", "trust_list": []}))
        private_key = self._keyring.get_password("kabbalah", "federation:private_key")
        public_key = network.get("public_key")
        from .sync_hub import gerar_par_chaves_federacao, publisher_id

        if not public_key or not private_key:
            public_key, private_key = gerar_par_chaves_federacao()
            self._keyring.set_password("kabbalah", "federation:private_key", private_key)
            network["public_key"] = public_key
            network.setdefault("mode", "off")
            network.setdefault("trust_list", [])
        network["publisher_id"] = publisher_id(str(public_key))
        self.installation_settings["network"] = network
        self.save_installation_config()
        return {"public_key": str(public_key), "publisher_id": str(network.get("publisher_id"))}

    def get_federation_private_key(self) -> Optional[str]:
        """Return the private federation key for internal signing only."""

        if self._keyring is None:
            return None
        return self._keyring.get_password("kabbalah", "federation:private_key")

    def set_network_mode(self, mode: str) -> None:
        """Persist the federated-network mode for this installation."""

        if mode not in {"off", "receber", "receber+contribuir"}:
            raise ConfigurationError("Network mode must be off, receber, or receber+contribuir")
        network = dict(self.installation_settings.get("network", {"trust_list": []}))
        network["mode"] = mode
        network.setdefault("trust_list", [])
        self.installation_settings["network"] = network
        self.save_installation_config()

    def add_trusted_publisher(self, public_key: str) -> None:
        """Trust one federated publisher public key."""

        network = dict(self.installation_settings.get("network", {"mode": "off", "trust_list": []}))
        trust_list = list(network.get("trust_list", []))
        if public_key not in trust_list:
            trust_list.append(public_key)
        network["trust_list"] = sorted(trust_list)
        self.installation_settings["network"] = network
        self.save_installation_config()

    def remove_trusted_publisher(self, public_key: str) -> None:
        """Remove one federated publisher public key from the trust list."""

        network = dict(self.installation_settings.get("network", {"mode": "off", "trust_list": []}))
        network["trust_list"] = [item for item in network.get("trust_list", []) if item != public_key]
        self.installation_settings["network"] = network
        self.save_installation_config()

    def set_budget_limits(
        self,
        *,
        mode: Optional[str] = None,
        run_limit_usd: Optional[float] = None,
        daily_limit_usd: Optional[float] = None,
        provider_limits_usd: Optional[Dict[str, float]] = None,
    ) -> None:
        """Persist non-secret budget limits for this installation."""
        budget = dict(self.installation_settings.get("budget", {}))
        if mode is not None:
            if mode not in {"warn", "block"}:
                raise ConfigurationError("Budget mode must be 'warn' or 'block'")
            budget["mode"] = mode
        if run_limit_usd is not None:
            budget["run_limit_usd"] = float(run_limit_usd)
        if daily_limit_usd is not None:
            budget["daily_limit_usd"] = float(daily_limit_usd)
        if provider_limits_usd is not None:
            budget["provider_limits_usd"] = {provider: float(limit) for provider, limit in provider_limits_usd.items()}
        self.installation_settings["budget"] = budget
        self.save_installation_config()

    def set_routing_policy(self, policy: str) -> None:
        """Persist the routing policy for this installation."""
        if policy not in {"balanced", "budget_first", "quality_first", "local_first"}:
            raise ConfigurationError("Routing policy must be balanced, budget_first, quality_first, or local_first")
        self.installation_settings["routing"] = {"policy": policy}
        self.save_installation_config()

    def validate_configuration(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if valid, False otherwise
        """
        # Validate mode
        valid_modes = ["BOOTSTRAP", "DAY1", "DAY2"]
        if self.config.mode not in valid_modes:
            logger.error(f"Invalid mode: {self.config.mode}")
            return False

        # Validate environment
        valid_envs = ["development", "staging", "production"]
        if self.config.environment not in valid_envs:
            logger.error(f"Invalid environment: {self.config.environment}")
            return False

        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.config.log_level not in valid_levels:
            logger.error(f"Invalid log level: {self.config.log_level}")
            return False

        # Validate memory backend
        valid_backends = ["cognee", "jsonl"]
        if self.config.memory_backend not in valid_backends:
            logger.error(f"Invalid memory backend: {self.config.memory_backend}")
            return False

        # Validate timeouts
        if self.config.tool_timeout <= 0:
            logger.error("Tool timeout must be positive")
            return False

        # Validate resource limits
        if self.config.max_concurrent_tasks <= 0:
            logger.error("Max concurrent tasks must be positive")
            return False

        if self.config.max_memory_mb <= 0:
            logger.error("Max memory must be positive")
            return False

        logger.debug("Configuration validation passed")
        return True

    def _provider_env_names(self, provider: str) -> List[str]:
        return list(
            self.PROVIDER_KEY_ENVS.get(
                provider,
                [f"{provider.upper()}_API_KEY", f"KABBALAH_{provider.upper()}_API_KEY"],
            )
        )

    @staticmethod
    def _provider_status(
        *,
        provider: str,
        status: str,
        source: str,
        last4: Optional[str],
        env_names: List[str],
    ) -> Dict[str, Any]:
        return {
            "provider": provider,
            "status": status,
            "source": source,
            "last4": last4,
            "env_names": env_names,
        }

    @staticmethod
    def _last4(value: str) -> str:
        return value[-4:] if len(value) >= 4 else value

    @staticmethod
    def _keyring_provider_username(provider: str) -> str:
        return f"provider:{provider}"

    def _get_keyring_provider_api_key(self, provider: str) -> Optional[str]:
        if self._keyring is None:
            return None
        try:
            return self._keyring.get_password(
                "kabbalah",
                self._keyring_provider_username(provider),
            )
        except Exception:
            logger.debug("Failed to query keyring provider status", exc_info=True)
            return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        return {
            "mode": self.config.mode,
            "environment": self.config.environment,
            "log_level": self.config.log_level,
            "default_provider": self.config.default_provider,
            "providers": {
                name: {
                    "name": provider.name,
                    "model": provider.model,
                    "timeout": provider.timeout,
                    "max_retries": provider.max_retries,
                }
                for name, provider in self.config.providers.items()
            },
            "provider_fallback_chain": self.config.provider_fallback_chain,
            "domain_providers": self.config.domain_providers,
            "memory_backend": self.config.memory_backend,
            "memory_max_size": self.config.memory_max_size,
            "tool_timeout": self.config.tool_timeout,
            "tool_max_retries": self.config.tool_max_retries,
            "observability_enabled": self.config.observability_enabled,
            "trace_sampling_rate": self.config.trace_sampling_rate,
            "max_concurrent_tasks": self.config.max_concurrent_tasks,
            "max_memory_mb": self.config.max_memory_mb,
            "metadata": self.config.metadata,
        }

    def to_json(self) -> str:
        """
        Convert configuration to JSON.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=2, default=str)
