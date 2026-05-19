"""
Provider Configuration Manager

Manages provider configuration from multiple sources:
- Environment variables
- Configuration files (YAML/JSON)
- CLI arguments
- Runtime configuration
"""

import os
import json
from typing import Dict, Optional, Any
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .factory import ConfigurationMode, ProviderFactory


class ProviderConfigurationManager:
    """
    Manages provider configuration from multiple sources.
    
    Configuration precedence (highest to lowest):
    1. Runtime configuration (set_config)
    2. CLI arguments
    3. Configuration files (YAML/JSON)
    4. Environment variables
    5. Defaults
    """
    
    def __init__(self):
        """Initialize the configuration manager"""
        self.factory = ProviderFactory()
        self.config: Dict[str, Any] = {}
        self.load_defaults()
    
    def load_defaults(self) -> None:
        """Load default configuration"""
        self.config = {
            "mode": "unified",
            "default_provider": "openai",
            "roles": {},
            "fallbacks": {},
            "cost_optimization": True,
            "latency_optimization": False,
        }
    
    def load_from_env(self) -> None:
        """Load configuration from environment variables"""
        # Mode
        mode = os.getenv("KABBALAH_PROVIDER_MODE", "unified")
        if mode in [m.value for m in ConfigurationMode]:
            self.config["mode"] = mode
        
        # Default provider
        default_provider = os.getenv("KABBALAH_DEFAULT_PROVIDER")
        if default_provider:
            self.config["default_provider"] = default_provider
        
        # Per-role providers
        for role in ["orchestrator", "analyzer", "executor", "validator", "synthesizer"]:
            env_var = f"KABBALAH_{role.upper()}_PROVIDER"
            provider = os.getenv(env_var)
            if provider:
                self.config["roles"][role] = provider
        
        # Cost optimization
        cost_opt = os.getenv("KABBALAH_COST_OPTIMIZATION", "true").lower()
        self.config["cost_optimization"] = cost_opt in ["true", "1", "yes"]
        
        # Latency optimization
        latency_opt = os.getenv("KABBALAH_LATENCY_OPTIMIZATION", "false").lower()
        self.config["latency_optimization"] = latency_opt in ["true", "1", "yes"]
    
    def load_from_file(self, config_path: str) -> None:
        """
        Load configuration from file (YAML or JSON).
        
        Args:
            config_path: Path to configuration file
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
        """
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        suffix = path.suffix.lower()
        
        if suffix == ".json":
            with open(path, "r") as f:
                file_config = json.load(f)
        elif suffix in [".yaml", ".yml"]:
            if not HAS_YAML:
                raise ValueError("PyYAML not installed. Install with: pip install pyyaml")
            with open(path, "r") as f:
                file_config = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        # Merge with existing config
        self.config.update(file_config)
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """
        Set configuration at runtime.
        
        Args:
            config: Configuration dictionary
        """
        self.config.update(config)
    
    def apply_configuration(self) -> None:
        """Apply the current configuration to the factory"""
        # Set configuration mode
        mode_str = self.config.get("mode", "unified")
        try:
            mode = ConfigurationMode(mode_str)
        except ValueError:
            raise ValueError(f"Unknown configuration mode: {mode_str}")
        
        # Prepare mode-specific config
        mode_config = {
            "default": self.config.get("default_provider", "openai"),
            "roles": self.config.get("roles", {}),
            "fallbacks": self.config.get("fallbacks", {}),
        }
        
        self.factory.set_configuration_mode(mode, mode_config)
        
        # Set fallback chains
        for role, providers in self.config.get("fallbacks", {}).items():
            if isinstance(providers, list):
                self.factory.set_fallback_chain(role, providers)
    
    def get_provider_for_role(self, role: str):
        """
        Get provider for a role.
        
        Args:
            role: Role name
        
        Returns:
            Provider instance
        """
        return self.factory.get_provider_for_role(role)
    
    def get_fallback_chain(self, role: str):
        """
        Get fallback chain for a role.
        
        Args:
            role: Role name
        
        Returns:
            List of provider instances
        """
        return self.factory.get_fallback_chain(role)
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()
    
    def validate_configuration(self) -> bool:
        """
        Validate the current configuration.
        
        Returns:
            True if valid
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate mode
        mode = self.config.get("mode", "unified")
        if mode not in [m.value for m in ConfigurationMode]:
            raise ValueError(f"Invalid mode: {mode}")
        
        # Validate default provider
        default_provider = self.config.get("default_provider", "openai")
        if default_provider not in self.factory.get_available_providers():
            raise ValueError(f"Unknown provider: {default_provider}")
        
        # Validate role providers
        for role, provider in self.config.get("roles", {}).items():
            if provider not in self.factory.get_available_providers():
                raise ValueError(f"Unknown provider for role {role}: {provider}")
        
        # Validate fallback chains
        for role, providers in self.config.get("fallbacks", {}).items():
            if not isinstance(providers, list):
                raise ValueError(f"Fallback chain for {role} must be a list")
            for provider in providers:
                if provider not in self.factory.get_available_providers():
                    raise ValueError(f"Unknown provider in fallback chain: {provider}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export configuration as dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()
    
    def to_json(self) -> str:
        """
        Export configuration as JSON.
        
        Returns:
            JSON string
        """
        return json.dumps(self.config, indent=2)
    
    def to_yaml(self) -> str:
        """
        Export configuration as YAML.
        
        Returns:
            YAML string
        
        Raises:
            ValueError: If PyYAML not installed
        """
        if not HAS_YAML:
            raise ValueError("PyYAML not installed. Install with: pip install pyyaml")
        return yaml.dump(self.config, default_flow_style=False)
