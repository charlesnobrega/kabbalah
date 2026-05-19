"""
Configuration Manager

Manages system configuration from multiple sources with precedence.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import platform

logger = logging.getLogger(__name__)


class ConfigurationSource(Enum):
    """Configuration sources"""
    ENVIRONMENT = "environment"
    FILE = "file"
    CLI = "cli"
    DEFAULT = "default"


class ConfigurationError(Exception):
    """Raised when configuration fails"""
    pass


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
    
    def __init__(self):
        """Initialize configuration manager"""
        self.config = Configuration()
        self.sources: Dict[str, ConfigurationSource] = {}
        self._detect_environment()
    
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
            with open(filepath, 'r') as f:
                if filepath.endswith('.json'):
                    data = json.load(f)
                elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                    import yaml
                    data = yaml.safe_load(f)
                else:
                    raise ConfigurationError(f"Unsupported file format: {filepath}")
            
            self._apply_config_dict(data, ConfigurationSource.FILE)
            logger.debug(f"Configuration loaded from {filepath}")
        
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {filepath}: {str(e)}")
    
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
                        self.config.providers[provider_name] = ProviderConfig(
                            name=provider_name,
                            **provider_config
                        )
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
