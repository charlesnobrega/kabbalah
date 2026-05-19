"""
Tests for Mock Provider

Tests the MockProvider implementation for testing without real API calls.
"""

import pytest
import time

from src.kabbalah.providers import ProviderResponse
from src.kabbalah.providers.mock_provider import MockProvider, MockResponseType


ALLOW_FAKE_PROVIDER_ENV = "KABBALAH_ALLOW_TEST_FAKE_PROVIDER"


@pytest.fixture(autouse=True)
def allow_test_fake_provider(request, monkeypatch):
    """Allow the explicit test fake for all tests except the runtime guard."""
    if request.node.name != "test_mock_provider_requires_explicit_test_mode":
        monkeypatch.setenv(ALLOW_FAKE_PROVIDER_ENV, "1")


def test_mock_provider_requires_explicit_test_mode(monkeypatch):
    """Runtime must not be able to instantiate fake providers accidentally."""
    monkeypatch.delenv(ALLOW_FAKE_PROVIDER_ENV, raising=False)

    with pytest.raises(RuntimeError, match="test-only fake provider"):
        MockProvider()


class TestMockProvider:
    """Test Mock Provider"""
    
    def test_provider_initialization(self):
        """Test that mock provider initializes correctly"""
        provider = MockProvider()
        
        assert provider is not None
        assert provider.api_key is None
        assert provider.response_type == MockResponseType.SUCCESS
        assert provider.response_content == "Mock response"
        assert provider.latency_ms == 100.0
        assert provider.call_count == 0
        assert provider.total_cost == 0.0
    
    def test_provider_initialization_with_options(self):
        """Test initializing mock provider with options"""
        provider = MockProvider(
            response_type=MockResponseType.ERROR,
            response_content="Custom response",
            latency_ms=50.0,
            error_message="Custom error"
        )
        
        assert provider.response_type == MockResponseType.ERROR
        assert provider.response_content == "Custom response"
        assert provider.latency_ms == 50.0
        assert provider.error_message == "Custom error"
    
    def test_validate_request_valid(self):
        """Test validation of valid request"""
        provider = MockProvider()
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
        }
        
        assert provider.validate_request(request) is True
    
    def test_validate_request_missing_messages(self):
        """Test validation fails without messages"""
        provider = MockProvider()
        
        request = {
            "model": "mock-model-1",
        }
        
        with pytest.raises(ValueError):
            provider.validate_request(request)
    
    def test_validate_request_empty_messages(self):
        """Test validation fails with empty messages"""
        provider = MockProvider()
        
        request = {
            "model": "mock-model-1",
            "messages": [],
        }
        
        with pytest.raises(ValueError):
            provider.validate_request(request)
    
    def test_validate_request_invalid_model(self):
        """Test validation fails with invalid model"""
        provider = MockProvider()
        
        request = {
            "model": "invalid-model",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        with pytest.raises(ValueError):
            provider.validate_request(request)
    
    def test_execute_request_success(self):
        """Test successful request execution"""
        provider = MockProvider(
            response_type=MockResponseType.SUCCESS,
            response_content="Hello, world!"
        )
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
        }
        
        response = provider.execute_request(request)
        
        assert isinstance(response, ProviderResponse)
        assert response.content == "Hello, world!"
        assert response.model == "mock-model-1"
        assert response.error is None
        assert response.latency_ms >= 100.0
        assert response.cost > 0
        assert provider.call_count == 1
    
    def test_execute_request_error(self):
        """Test error request execution"""
        provider = MockProvider(
            response_type=MockResponseType.ERROR,
            error_message="Mock error occurred"
        )
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        response = provider.execute_request(request)
        
        assert response.content == ""
        assert response.error == "Mock error occurred"
        assert response.tokens_used > 0  # Input tokens are still counted
        assert response.cost > 0  # Cost is still calculated
        assert provider.call_count == 0  # Error responses not recorded
    
    def test_execute_request_timeout(self):
        """Test timeout request execution"""
        provider = MockProvider(
            response_type=MockResponseType.TIMEOUT
        )
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        response = provider.execute_request(request)
        
        assert response.error == "Mock timeout error"
        assert response.content == ""
    
    def test_execute_request_rate_limit(self):
        """Test rate limit request execution"""
        provider = MockProvider(
            response_type=MockResponseType.RATE_LIMIT
        )
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        response = provider.execute_request(request)
        
        assert response.error == "Mock rate limit error"
        assert response.content == ""
    
    def test_stream_request_success(self):
        """Test successful streaming request"""
        provider = MockProvider(
            response_type=MockResponseType.SUCCESS,
            response_content="Hello, world!",
            latency_ms=50.0
        )
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        responses = list(provider.stream_request(request))
        
        assert len(responses) > 0
        
        # Check first response
        first_response = responses[0]
        assert isinstance(first_response, ProviderResponse)
        assert first_response.content != ""
        
        # Check last response
        last_response = responses[-1]
        assert last_response.content == "Hello, world!"
        assert last_response.error is None
        
        # Check that provider recorded the call
        assert provider.call_count == 1
    
    def test_stream_request_error(self):
        """Test streaming error request"""
        provider = MockProvider(
            response_type=MockResponseType.ERROR,
            error_message="Stream error"
        )
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        responses = list(provider.stream_request(request))
        
        assert len(responses) == 1
        assert responses[0].error == "Stream error"
    
    def test_calculate_cost(self):
        """Test cost calculation"""
        provider = MockProvider()
        
        cost = provider.calculate_cost(1000, "mock-model-1")
        
        assert cost >= 0
        assert isinstance(cost, float)
    
    def test_request_history(self):
        """Test request history tracking"""
        provider = MockProvider()
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        provider.execute_request(request)
        provider.execute_request(request)
        
        history = provider.get_request_history()
        
        assert len(history) == 2
        assert history[0]["model"] == "mock-model-1"
        assert history[1]["model"] == "mock-model-1"
    
    def test_clear_history(self):
        """Test clearing request history"""
        provider = MockProvider()
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        provider.execute_request(request)
        assert len(provider.get_request_history()) == 1
        
        provider.clear_history()
        assert len(provider.get_request_history()) == 0
    
    def test_set_response_type(self):
        """Test setting response type"""
        provider = MockProvider()
        
        assert provider.response_type == MockResponseType.SUCCESS
        
        provider.set_response_type(MockResponseType.ERROR)
        assert provider.response_type == MockResponseType.ERROR
    
    def test_set_response_content(self):
        """Test setting response content"""
        provider = MockProvider()
        
        assert provider.response_content == "Mock response"
        
        provider.set_response_content("New content")
        assert provider.response_content == "New content"
    
    def test_set_latency(self):
        """Test setting latency"""
        provider = MockProvider()
        
        assert provider.latency_ms == 100.0
        
        provider.set_latency(50.0)
        assert provider.latency_ms == 50.0
    
    def test_set_error_message(self):
        """Test setting error message"""
        provider = MockProvider()
        
        assert provider.error_message == "Mock error"
        
        provider.set_error_message("New error")
        assert provider.error_message == "New error"
    
    def test_latency_simulation(self):
        """Test that latency is simulated correctly"""
        provider = MockProvider(latency_ms=200.0)
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        start_time = time.time()
        response = provider.execute_request(request)
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Should be at least 200ms
        assert elapsed_ms >= 200.0
        assert response.latency_ms >= 200.0
    
    def test_multiple_models(self):
        """Test with multiple mock models"""
        provider = MockProvider()
        
        for model in ["mock-model-1", "mock-model-2", "mock-model-3"]:
            request = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Say hello"}
                ],
            }
            
            response = provider.execute_request(request)
            
            assert response.model == model
            assert response.cost > 0
    
    def test_statistics_tracking(self):
        """Test statistics tracking"""
        provider = MockProvider(
            response_type=MockResponseType.SUCCESS,
            response_content="Test response"
        )
        
        request = {
            "model": "mock-model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
        }
        
        # Make multiple requests
        for _ in range(3):
            provider.execute_request(request)
        
        stats = provider.get_stats()
        
        assert stats["call_count"] == 3
        assert stats["total_cost"] > 0
        assert stats["average_cost"] > 0
        assert stats["total_tokens"] > 0


class TestMockResponseType:
    """Test Mock Response Type enum"""
    
    def test_response_types(self):
        """Test all response types exist"""
        assert MockResponseType.SUCCESS.value == "success"
        assert MockResponseType.ERROR.value == "error"
        assert MockResponseType.TIMEOUT.value == "timeout"
        assert MockResponseType.RATE_LIMIT.value == "rate_limit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
