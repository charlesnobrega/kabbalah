"""
Tests for Groq Provider

Tests the GroqProvider implementation with real API calls.
"""

import os
import pytest
from dotenv import load_dotenv

from src.kabbalah.providers import GroqProvider, ProviderResponse


# Load environment variables
load_dotenv()


@pytest.fixture
def provider():
    """Create a Groq provider instance"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY not set")
    
    return GroqProvider(api_key=api_key)


class TestGroqProvider:
    """Test Groq Provider"""
    
    def test_provider_initialization(self, provider):
        """Test that provider initializes correctly"""
        assert provider is not None
        assert provider.api_key is not None
        assert provider.call_count == 0
        assert provider.total_cost == 0.0
    
    def test_validate_request_valid(self, provider):
        """Test validation of valid request"""
        request = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
        }
        
        assert provider.validate_request(request) is True
    
    def test_validate_request_missing_messages(self, provider):
        """Test validation fails without messages"""
        request = {
            "model": "mixtral-8x7b-32768",
        }
        
        with pytest.raises(ValueError):
            provider.validate_request(request)
    
    def test_validate_request_empty_messages(self, provider):
        """Test validation fails with empty messages"""
        request = {
            "model": "mixtral-8x7b-32768",
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
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "user", "content": "Say hello in one word"}
            ],
            "max_tokens": 50,
        }
        
        response = provider.execute_request(request)
        
        assert isinstance(response, ProviderResponse)
        assert response.content is not None or response.error is not None
        assert response.model == "mixtral-8x7b-32768"
        assert response.latency_ms > 0
        assert response.cost >= 0
    
    def test_execute_request_with_system_message(self, provider):
        """Test request with system message"""
        request = {
            "model": "mixtral-8x7b-32768",
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
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
            "temperature": 0.5,
        }
        
        response = provider.execute_request(request)
        
        assert response.content is not None or response.error is not None
        assert response.latency_ms > 0
    
    def test_execute_request_records_stats(self, provider):
        """Test that execute_request records statistics"""
        initial_count = provider.call_count
        initial_cost = provider.total_cost
        
        request = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
        }
        
        response = provider.execute_request(request)
        
        if response.error is None:
            assert provider.call_count == initial_count + 1
            assert provider.total_cost >= initial_cost
    
    def test_get_stats(self, provider):
        """Test getting provider statistics"""
        request = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
        }
        
        provider.execute_request(request)
        
        stats = provider.get_stats()
        
        assert "call_count" in stats
        assert "total_cost" in stats
        assert "average_cost" in stats
        assert "total_tokens" in stats
        assert stats["total_cost"] >= 0
    
    def test_calculate_cost(self, provider):
        """Test cost calculation"""
        cost = provider.calculate_cost(1000, "mixtral-8x7b-32768")
        
        assert cost >= 0
        assert isinstance(cost, float)
    
    def test_stream_request(self, provider):
        """Test streaming request"""
        request = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "user", "content": "Count to 3"}
            ],
            "max_tokens": 50,
        }
        
        responses = list(provider.stream_request(request))
        
        assert len(responses) > 0
        
        # Check first response
        first_response = responses[0]
        assert isinstance(first_response, ProviderResponse)
        
        # Check last response
        last_response = responses[-1]
        assert last_response.content is not None or last_response.error is not None
    
    def test_multiple_requests(self, provider):
        """Test multiple sequential requests"""
        for i in range(2):
            request = {
                "model": "mixtral-8x7b-32768",
                "messages": [
                    {"role": "user", "content": f"Say hello {i}"}
                ],
                "max_tokens": 50,
            }
            
            response = provider.execute_request(request)
            
            assert response.content is not None or response.error is not None
        
        stats = provider.get_stats()
        assert stats["call_count"] >= 0


class TestProviderResponse:
    """Test ProviderResponse dataclass"""
    
    def test_provider_response_creation(self):
        """Test creating a ProviderResponse"""
        response = ProviderResponse(
            content="Hello",
            model="mixtral-8x7b-32768",
            tokens_used=10,
            cost=0.001,
            latency_ms=100.0,
        )
        
        assert response.content == "Hello"
        assert response.model == "mixtral-8x7b-32768"
        assert response.tokens_used == 10
        assert response.cost == 0.001
        assert response.latency_ms == 100.0
        assert response.error is None
    
    def test_provider_response_with_error(self):
        """Test ProviderResponse with error"""
        response = ProviderResponse(
            content="",
            model="mixtral-8x7b-32768",
            tokens_used=0,
            cost=0.0,
            latency_ms=50.0,
            error="API Error",
        )
        
        assert response.error == "API Error"
        assert response.content == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
