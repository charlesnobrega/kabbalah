"""
Provider Factory

Factory for creating and managing LLM provider instances.
Supports multiple configuration modes and fallback chains.
"""

import os
from typing import Dict, List, Optional, Type
from enum import Enum

from .base import BaseProvider
from .openai_provider import OpenAIProvider
from .google_gemini_provider import GoogleGeminiProvider
from .groq_provider import GroqProvider
from .mistral_provider import MistralProvider
from .together_provider import TogetherProvider
from .deepseek_provider import DeepSeekProvider


class ConfigurationMode(Enum):
    """Provider configuration modes"""
    
    UNIFIED = "unified"
    """Same provider for all roles"""
    
    EXPLICIT = "explicit"
    """Define each role's provider explicitly"""
    
    HIERARCHY = "hierarchy"
    """Provider hierarchy by role"""
    
    HYBRID = "hybrid"
    """Mix of above modes"""


class ProviderFactory:
    """
    Factory for creating and managing LLM provider instances.
    
    Supports:
    - Multiple provider types
    - Configuration modes (unified, explicit, hierarchy, hybrid)
    - Fallback chains
    - Cost/latency optimization
    """
    
    # Available providers
    PROVIDERS: Dict[str, Type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "google_gemini": GoogleGeminiProvider,
        "groq": GroqProvider,
        "mistral": MistralProvider,
        "together": TogetherProvider,
        "deepseek": DeepSeekProvider,
    }
    
    def __init__(self):
        """Initialize the provider factory"""
        self.instances: Dict[str, BaseProvider] = {}
        self.config_mode = ConfigurationMode.UNIFIED
        self.default_provider = "openai"
        self.role_providers: Dict[str, str] = {}
        self.fallback_chains: Dict[str, List[str]] = {}
    
    def create_provider(
        self,
        provider_name: str,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseProvider:
        """
        Create a provider instance.
        
        Args:
            provider_name: Name of the provider (e.g., "openai", "groq")
            api_key: API key for the provider (or use env var)
            **kwargs: Additional configuration options
        
        Returns:
            Provider instance
        
        Raises:
            ValueError: If provider name is unknown
        """
        if provider_name not in self.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available: {list(self.PROVIDERS.keys())}"
            )
        
        # Check if instance already exists
        cache_key = f"{provider_name}:{api_key or 'default'}"
        if cache_key in self.instances:
            return self.instances[cache_key]
        
        # Create new instance
        provider_class = self.PROVIDERS[provider_name]
        
        # Get API key from parameter or environment
        if not api_key:
            env_var = f"{provider_name.upper()}_API_KEY"
            api_key = os.getenv(env_var)
        
        instance = provider_class(api_key=api_key, **kwargs)
        self.instances[cache_key] = instance
        
        return instance
    
    def set_configuration_mode(
        self,
        mode: ConfigurationMode,
        config: Optional[Dict] = None
    ) -> None:
        """
        Set the provider configuration mode.
        
        Args:
            mode: Configuration mode
            config: Configuration dictionary (depends on mode)
        
        Raises:
            ValueError: If configuration is invalid
        """
        self.config_mode = mode
        
        if config is None:
            config = {}
        
        if mode == ConfigurationMode.UNIFIED:
            # Unified mode: same provider for all roles
            self.default_provider = config.get("provider", "openai")
            self.role_providers = {}
        
        elif mode == ConfigurationMode.EXPLICIT:
            # Explicit mode: define each role's provider
            self.role_providers = config.get("roles", {})
            self.default_provider = config.get("default", "openai")
        
        elif mode == ConfigurationMode.HIERARCHY:
            # Hierarchy mode: provider hierarchy by role
            self.role_providers = config.get("hierarchy", {})
            self.default_provider = config.get("default", "openai")
        
        elif mode == ConfigurationMode.HYBRID:
            # Hybrid mode: mix of above
            self.role_providers = config.get("roles", {})
            self.default_provider = config.get("default", "openai")
            self.fallback_chains = config.get("fallbacks", {})
    
    def set_fallback_chain(
        self,
        role: str,
        providers: List[str]
    ) -> None:
        """
        Set fallback chain for a role.
        
        Args:
            role: Role name
            providers: List of provider names in fallback order
        
        Raises:
            ValueError: If any provider is unknown
        """
        for provider_name in providers:
            if provider_name not in self.PROVIDERS:
                raise ValueError(f"Unknown provider: {provider_name}")
        
        self.fallback_chains[role] = providers
    
    def get_provider_for_role(self, role: str) -> BaseProvider:
        """
        Get the provider for a specific role.
        
        Args:
            role: Role name
        
        Returns:
            Provider instance
        """
        # Check if role has explicit provider
        if role in self.role_providers:
            provider_name = self.role_providers[role]
            return self.create_provider(provider_name)
        
        # Use default provider
        return self.create_provider(self.default_provider)
    
    def get_fallback_chain(self, role: str) -> List[BaseProvider]:
        """
        Get fallback chain for a role.
        
        Args:
            role: Role name
        
        Returns:
            List of provider instances in fallback order
        """
        if role in self.fallback_chains:
            provider_names = self.fallback_chains[role]
            return [self.create_provider(name) for name in provider_names]
        
        # Default fallback chain
        return [self.get_provider_for_role(role)]
    
    def get_available_providers(self) -> List[str]:
        """
        Get list of available provider names.
        
        Returns:
            List of provider names
        """
        return list(self.PROVIDERS.keys())
    
    def get_provider_stats(self, provider_name: str) -> Dict:
        """
        Get statistics for a provider.
        
        Args:
            provider_name: Name of the provider
        
        Returns:
            Statistics dictionary
        
        Raises:
            ValueError: If provider not found
        """
        cache_key = f"{provider_name}:default"
        if cache_key not in self.instances:
            raise ValueError(f"Provider {provider_name} not instantiated")
        
        return self.instances[cache_key].get_stats()
    
    def clear_cache(self) -> None:
        """Clear all cached provider instances"""
        self.instances.clear()
