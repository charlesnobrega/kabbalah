"""
Tests for Together Provider

Tests the TogetherProvider implementation with real API calls.
"""

import os
import pytest
from dotenv import load_dotenv

from src.kabbalah.providers import TogetherProvider, ProviderResponse


# Load environment variables
load_dotenv()


@pytest.fixture
def provider():
    """Create a Together provider instance"""
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        pytest.skip("TOGETHER_API_KEY not set")
    
    return TogetherProvider(api_key=api_key)


class TestTogetherProvider:
    """Test Together Provider"""
    
    def test_provider_initialization(self, provider):
        """Test that provider initializes correctly"""
        assert provider is not None
        assert provider.api_key is not None
        assert provider.call_count == 0
        assert provider.total_cost == 0.0
    
    def test_validate_request_valid(self, provider):
        """Test validation of valid request"""
        request = {
            "model": "meta-llama/Llama-2-70b-chat-hf",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
        }
        
        assert provider.validate_request(request) is True
    
    def test_validate_request_missing_messages(self, provider):
        """Test validation fails without messages"""
        request = {
            "model": "meta-llama/Llama-2-70b-chat-hf",
        }
        
        with pytest.raises(ValueError):
            provider.validate_request(request)
    
    def test_validate_request_empty_messages(self, provider):
        """Test validation fails with empty messages"""
        request = {
            "model": "meta-llama/Llama-2-70b-chat-hf",
            "messages": [],
        }
        
        with pytest.raises(ValueError):
            provider.validate_request(request)
    
    def test_validate_request_invalid_model(self, provider):
        """Test validation fails with invalid model"""
        request = {
            "model": "invalid-model",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        with pytest.raises(ValueError):
            provider.validate_request(request)
    
    def test_execute_request_simple(self, provider):
        """Test simple request execution"""
        request = {
            "model": "meta-llama/Llama-2-70b-chat-hf",
            "messages": [
                {"role": "user", "content": "Say hello in one word"}
            ],
            "max_tokens": 50,
        }
        
        response = provider.execute_request(request)
        
        assert isinstance(response, ProviderResponse)
        assert response.content is not None or response.error is not None
        assert response.model == "meta-llama/Llama-2-70b-chat-hf"
        assert response.latency_ms > 0
        assert response.cost >= 0
    
    def test_execute_request_with_system_message(self, provider):
        """Test request with system message"""
        request = {
            "model": "meta-llama/Llama-2-70b-chat-hf",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
        }
        
        response = provider.execute_request(request)
        
        assert response.content is not None or response.error is not None
        assert response.latency_ms > 0
    
    def test_execute_request_with_temperature(self, provider):
        """Test request with temperature parameter"""
        request = {
            "model": "meta-llama/Llama-2-70b-chat-hf",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
            "temperature": 0.5,
        }
        
        response = provider.execute_request(request)
        
        assert response.content is not None or response.error is not None
        assert response.latency_ms > 0
    
    def test_calculate_cost(self, provider):
        """Test cost calculation"""
        cost = provider.calculate_cost(1000, "meta-llama/Llama-2-70b-chat-hf")
        
        assert cost >= 0
        assert isinstance(cost, float)


class TestProviderResponse:
    """Test ProviderResponse dataclass"""
    
    def test_provider_response_creation(self):
        """Test creating a ProviderResponse"""
        response = ProviderResponse(
            content="Hello",
            model="meta-llama/Llama-2-70b-chat-hf",
            tokens_used=10,
            cost=0.001,
            latency_ms=100.0,
        )
        
        assert response.content == "Hello"
        assert response.model == "meta-llama/Llama-2-70b-chat-hf"
        assert response.tokens_used == 10
        assert response.cost == 0.001
        assert response.latency_ms == 100.0
        assert response.error is None
    
    def test_provider_response_with_error(self):
        """Test ProviderResponse with error"""
        response = ProviderResponse(
            content="",
            model="meta-llama/Llama-2-70b-chat-hf",
            tokens_used=0,
            cost=0.0,
            latency_ms=50.0,
            error="API Error",
        )
        
        assert response.error == "API Error"
        assert response.content == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
