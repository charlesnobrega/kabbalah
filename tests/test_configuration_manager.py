"""
Tests for Configuration Manager
"""

import pytest
import os
import json
import tempfile
from src.kabbalah.configuration_manager import (
    ConfigurationManager,
    Configuration,
    ProviderConfig,
    ConfigurationError,
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
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
