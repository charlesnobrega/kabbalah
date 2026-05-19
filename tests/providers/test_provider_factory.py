"""
Tests for Provider Factory

Tests the ProviderFactory implementation with all configuration modes.
"""

import pytest

from src.kabbalah.providers import (
    ProviderFactory,
    ConfigurationMode,
    OpenAIProvider,
    GroqProvider,
    MistralProvider,
)


class TestProviderFactory:
    """Test Provider Factory"""
    
    def test_factory_initialization(self):
        """Test that factory initializes correctly"""
        factory = ProviderFactory()
        
        assert factory is not None
        assert factory.config_mode == ConfigurationMode.UNIFIED
        assert factory.default_provider == "openai"
        assert len(factory.instances) == 0
    
    def test_get_available_providers(self):
        """Test getting list of available providers"""
        factory = ProviderFactory()
        providers = factory.get_available_providers()
        
        assert isinstance(providers, list)
        assert len(providers) >= 6
        assert "openai" in providers
        assert "groq" in providers
        assert "mistral" in providers
        assert "together" in providers
        assert "deepseek" in providers
        assert "google_gemini" in providers
    
    def test_create_provider_openai(self):
        """Test creating OpenAI provider"""
        factory = ProviderFactory()
        api_key = "test-openai-key"
        
        provider = factory.create_provider("openai", api_key=api_key)
        
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == api_key
    
    def test_create_provider_groq(self):
        """Test creating Groq provider"""
        factory = ProviderFactory()
        api_key = "test-groq-key"
        
        provider = factory.create_provider("groq", api_key=api_key)
        
        assert isinstance(provider, GroqProvider)
        assert provider.api_key == api_key
    
    def test_create_provider_unknown(self):
        """Test creating unknown provider raises error"""
        factory = ProviderFactory()
        
        with pytest.raises(ValueError):
            factory.create_provider("unknown_provider")
    
    def test_provider_caching(self):
        """Test that providers are cached"""
        factory = ProviderFactory()
        api_key = "test-openai-key"
        
        provider1 = factory.create_provider("openai", api_key=api_key)
        provider2 = factory.create_provider("openai", api_key=api_key)
        
        # Should be the same instance
        assert provider1 is provider2
    
    def test_unified_mode(self):
        """Test unified configuration mode"""
        factory = ProviderFactory()
        
        factory.set_configuration_mode(
            ConfigurationMode.UNIFIED,
            {"provider": "groq"}
        )
        
        assert factory.config_mode == ConfigurationMode.UNIFIED
        assert factory.default_provider == "groq"
    
    def test_explicit_mode(self):
        """Test explicit configuration mode"""
        factory = ProviderFactory()
        
        config = {
            "default": "openai",
            "roles": {
                "orchestrator": "groq",
                "analyzer": "mistral",
            }
        }
        
        factory.set_configuration_mode(ConfigurationMode.EXPLICIT, config)
        
        assert factory.config_mode == ConfigurationMode.EXPLICIT
        assert factory.role_providers["orchestrator"] == "groq"
        assert factory.role_providers["analyzer"] == "mistral"
    
    def test_hierarchy_mode(self):
        """Test hierarchy configuration mode"""
        factory = ProviderFactory()
        
        config = {
            "default": "openai",
            "hierarchy": {
                "orchestrator": "groq",
                "analyzer": "mistral",
            }
        }
        
        factory.set_configuration_mode(ConfigurationMode.HIERARCHY, config)
        
        assert factory.config_mode == ConfigurationMode.HIERARCHY
        assert factory.role_providers["orchestrator"] == "groq"
    
    def test_hybrid_mode(self):
        """Test hybrid configuration mode"""
        factory = ProviderFactory()
        
        config = {
            "default": "openai",
            "roles": {
                "orchestrator": "groq",
            },
            "fallbacks": {
                "orchestrator": ["groq", "mistral", "openai"],
            }
        }
        
        factory.set_configuration_mode(ConfigurationMode.HYBRID, config)
        
        assert factory.config_mode == ConfigurationMode.HYBRID
        assert factory.role_providers["orchestrator"] == "groq"
        assert factory.fallback_chains["orchestrator"] == ["groq", "mistral", "openai"]
    
    def test_set_fallback_chain(self):
        """Test setting fallback chain"""
        factory = ProviderFactory()
        
        factory.set_fallback_chain("orchestrator", ["groq", "mistral", "openai"])
        
        assert factory.fallback_chains["orchestrator"] == ["groq", "mistral", "openai"]
    
    def test_set_fallback_chain_invalid_provider(self):
        """Test setting fallback chain with invalid provider"""
        factory = ProviderFactory()
        
        with pytest.raises(ValueError):
            factory.set_fallback_chain("orchestrator", ["groq", "invalid_provider"])
    
    def test_get_provider_for_role_unified(self, monkeypatch):
        """Test getting provider for role in unified mode"""
        factory = ProviderFactory()
        factory.set_configuration_mode(
            ConfigurationMode.UNIFIED,
            {"provider": "groq"}
        )

        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        
        provider = factory.get_provider_for_role("orchestrator")
        
        assert isinstance(provider, GroqProvider)
    
    def test_get_provider_for_role_explicit(self, monkeypatch):
        """Test getting provider for role in explicit mode"""
        factory = ProviderFactory()
        
        config = {
            "default": "openai",
            "roles": {
                "orchestrator": "groq",
            }
        }
        
        factory.set_configuration_mode(ConfigurationMode.EXPLICIT, config)
        
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        
        provider = factory.get_provider_for_role("orchestrator")
        
        assert isinstance(provider, GroqProvider)
    
    def test_get_fallback_chain(self, monkeypatch):
        """Test getting fallback chain"""
        factory = ProviderFactory()
        
        factory.set_fallback_chain("orchestrator", ["groq", "mistral"])

        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        monkeypatch.setenv("MISTRAL_API_KEY", "test-mistral-key")
        
        chain = factory.get_fallback_chain("orchestrator")
        
        assert len(chain) == 2
        assert isinstance(chain[0], GroqProvider)
        assert isinstance(chain[1], MistralProvider)
    
    def test_clear_cache(self):
        """Test clearing provider cache"""
        factory = ProviderFactory()
        api_key = "test-openai-key"
        
        factory.create_provider("openai", api_key=api_key)
        assert len(factory.instances) > 0
        
        factory.clear_cache()
        assert len(factory.instances) == 0


class TestConfigurationMode:
    """Test Configuration Mode enum"""
    
    def test_configuration_modes(self):
        """Test all configuration modes exist"""
        assert ConfigurationMode.UNIFIED.value == "unified"
        assert ConfigurationMode.EXPLICIT.value == "explicit"
        assert ConfigurationMode.HIERARCHY.value == "hierarchy"
        assert ConfigurationMode.HYBRID.value == "hybrid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
