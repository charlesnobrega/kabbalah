"""
Tests for Provider Configuration Manager

Tests the ProviderConfigurationManager implementation.
"""

import pytest
import os
import json
import tempfile

from src.kabbalah.providers import (
    ProviderConfigurationManager,
    ConfigurationMode,
)


class TestProviderConfigurationManager:
    """Test Provider Configuration Manager"""
    
    def test_initialization(self):
        """Test that configuration manager initializes correctly"""
        manager = ProviderConfigurationManager()
        
        assert manager is not None
        assert manager.config is not None
        assert manager.config["mode"] == "unified"
        assert manager.config["default_provider"] == "openai"
    
    def test_load_defaults(self):
        """Test loading default configuration"""
        manager = ProviderConfigurationManager()
        manager.load_defaults()
        
        assert manager.config["mode"] == "unified"
        assert manager.config["default_provider"] == "openai"
        assert manager.config["cost_optimization"] is True
        assert manager.config["latency_optimization"] is False
    
    def test_load_from_env(self, monkeypatch):
        """Test loading configuration from environment variables"""
        monkeypatch.setenv("KABBALAH_PROVIDER_MODE", "explicit")
        monkeypatch.setenv("KABBALAH_DEFAULT_PROVIDER", "groq")
        monkeypatch.setenv("KABBALAH_ORCHESTRATOR_PROVIDER", "mistral")
        
        manager = ProviderConfigurationManager()
        manager.load_from_env()
        
        assert manager.config["mode"] == "explicit"
        assert manager.config["default_provider"] == "groq"
        assert manager.config["roles"]["orchestrator"] == "mistral"
    
    def test_load_from_json_file(self):
        """Test loading configuration from JSON file"""
        config_data = {
            "mode": "explicit",
            "default_provider": "groq",
            "roles": {
                "orchestrator": "mistral",
                "analyzer": "openai",
            }
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            manager = ProviderConfigurationManager()
            manager.load_from_file(temp_path)
            
            assert manager.config["mode"] == "explicit"
            assert manager.config["default_provider"] == "groq"
            assert manager.config["roles"]["orchestrator"] == "mistral"
        finally:
            os.unlink(temp_path)
    
    def test_load_from_yaml_file(self):
        """Test loading configuration from YAML file"""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")
        
        config_data = {
            "mode": "explicit",
            "default_provider": "groq",
            "roles": {
                "orchestrator": "mistral",
            }
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            manager = ProviderConfigurationManager()
            manager.load_from_file(temp_path)
            
            assert manager.config["mode"] == "explicit"
            assert manager.config["default_provider"] == "groq"
        finally:
            os.unlink(temp_path)
    
    def test_load_from_nonexistent_file(self):
        """Test loading from nonexistent file raises error"""
        manager = ProviderConfigurationManager()
        
        with pytest.raises(FileNotFoundError):
            manager.load_from_file("/nonexistent/path/config.json")
    
    def test_load_from_unsupported_format(self):
        """Test loading from unsupported file format raises error"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("some content")
            temp_path = f.name
        
        try:
            manager = ProviderConfigurationManager()
            
            with pytest.raises(ValueError):
                manager.load_from_file(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_set_config(self):
        """Test setting configuration at runtime"""
        manager = ProviderConfigurationManager()
        
        new_config = {
            "mode": "explicit",
            "default_provider": "mistral",
        }
        
        manager.set_config(new_config)
        
        assert manager.config["mode"] == "explicit"
        assert manager.config["default_provider"] == "mistral"
    
    def test_apply_configuration(self):
        """Test applying configuration to factory"""
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "explicit",
            "default_provider": "groq",
            "roles": {
                "orchestrator": "mistral",
            }
        })
        
        manager.apply_configuration()
        
        assert manager.factory.config_mode == ConfigurationMode.EXPLICIT
        assert manager.factory.default_provider == "groq"
        assert manager.factory.role_providers["orchestrator"] == "mistral"
    
    def test_validate_configuration_valid(self):
        """Test validating valid configuration"""
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "explicit",
            "default_provider": "openai",
            "roles": {
                "orchestrator": "groq",
            }
        })
        
        assert manager.validate_configuration() is True
    
    def test_validate_configuration_invalid_mode(self):
        """Test validating configuration with invalid mode"""
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "invalid_mode",
        })
        
        with pytest.raises(ValueError):
            manager.validate_configuration()
    
    def test_validate_configuration_invalid_provider(self):
        """Test validating configuration with invalid provider"""
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "unified",
            "default_provider": "invalid_provider",
        })
        
        with pytest.raises(ValueError):
            manager.validate_configuration()
    
    def test_validate_configuration_invalid_role_provider(self):
        """Test validating configuration with invalid role provider"""
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "explicit",
            "default_provider": "openai",
            "roles": {
                "orchestrator": "invalid_provider",
            }
        })
        
        with pytest.raises(ValueError):
            manager.validate_configuration()
    
    def test_validate_configuration_invalid_fallback(self):
        """Test validating configuration with invalid fallback"""
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "hybrid",
            "default_provider": "openai",
            "fallbacks": {
                "orchestrator": ["groq", "invalid_provider"],
            }
        })
        
        with pytest.raises(ValueError):
            manager.validate_configuration()
    
    def test_get_config(self):
        """Test getting configuration"""
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "explicit",
            "default_provider": "groq",
        })
        
        config = manager.get_config()
        
        assert config["mode"] == "explicit"
        assert config["default_provider"] == "groq"
    
    def test_to_dict(self):
        """Test exporting configuration as dictionary"""
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "explicit",
            "default_provider": "groq",
        })
        
        config_dict = manager.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["mode"] == "explicit"
    
    def test_to_json(self):
        """Test exporting configuration as JSON"""
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "explicit",
            "default_provider": "groq",
        })
        
        json_str = manager.to_json()
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["mode"] == "explicit"
    
    def test_to_yaml(self):
        """Test exporting configuration as YAML"""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")
        
        manager = ProviderConfigurationManager()
        
        manager.set_config({
            "mode": "explicit",
            "default_provider": "groq",
        })
        
        yaml_str = manager.to_yaml()
        
        assert isinstance(yaml_str, str)
        parsed = yaml.safe_load(yaml_str)
        assert parsed["mode"] == "explicit"
    
    def test_configuration_precedence(self, monkeypatch):
        """Test configuration precedence (runtime > file > env > defaults)"""
        manager = ProviderConfigurationManager()
        
        # Start with defaults
        assert manager.config["default_provider"] == "openai"
        
        # Load from env
        monkeypatch.setenv("KABBALAH_DEFAULT_PROVIDER", "groq")
        manager.load_from_env()
        assert manager.config["default_provider"] == "groq"
        
        # Set runtime config (overrides env)
        manager.set_config({"default_provider": "mistral"})
        assert manager.config["default_provider"] == "mistral"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
