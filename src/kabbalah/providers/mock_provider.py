"""
Test-only fake provider implementation.

This provider is intentionally blocked unless test mode is explicitly enabled.
Runtime code must not simulate real provider responses.
"""

import os
import time
import random
from typing import Dict, Optional, Iterator, List
from enum import Enum

from .base import BaseProvider, ProviderResponse


class MockResponseType(Enum):
    """Types of mock responses"""
    
    SUCCESS = "success"
    """Successful response"""
    
    ERROR = "error"
    """Error response"""
    
    TIMEOUT = "timeout"
    """Timeout response"""
    
    RATE_LIMIT = "rate_limit"
    """Rate limit response"""


class MockProvider(BaseProvider):
    """
    Test-only fake LLM Provider.
    
    Provides deterministic fake responses only for tests. It is guarded by
    KABBALAH_ALLOW_TEST_FAKE_PROVIDER so runtime code cannot accidentally use
    simulated provider data.
    """
    
    # Mock pricing (same as real providers for testing)
    PRICING = {
        "mock-model-1": {
            "input": 0.01,
            "output": 0.01,
        },
        "mock-model-2": {
            "input": 0.02,
            "output": 0.02,
        },
        "mock-model-3": {
            "input": 0.005,
            "output": 0.005,
        },
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        response_type: MockResponseType = MockResponseType.SUCCESS,
        response_content: str = "Mock response",
        latency_ms: float = 100.0,
        error_message: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize test-only fake provider.
        
        Args:
            api_key: Mock API key (ignored)
            response_type: Type of response to return
            response_content: Content to return in successful responses
            latency_ms: Simulated latency in milliseconds
            error_message: Error message for error responses
            **kwargs: Additional options
        """
        if os.getenv("KABBALAH_ALLOW_TEST_FAKE_PROVIDER") != "1":
            raise RuntimeError(
                "MockProvider is a test-only fake provider. "
                "Set KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1 only inside tests."
            )

        super().__init__(api_key, **kwargs)
        
        self.response_type = response_type
        self.response_content = response_content
        self.latency_ms = latency_ms
        self.error_message = error_message or "Mock error"
        self.request_history: List[Dict] = []
    
    def execute_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> ProviderResponse:
        """
        Execute a mock request.
        
        Args:
            request: Request dictionary
            timeout: Request timeout
        
        Returns:
            ProviderResponse with mock data
        """
        # Validate request
        self.validate_request(request)
        
        model_name = request.get("model", "mock-model-1")
        messages = request.get("messages", [])
        
        # Record request
        self.request_history.append({
            "model": model_name,
            "messages": messages,
            "timestamp": time.time(),
        })
        
        # Simulate latency
        start_time = time.time()
        time.sleep(self.latency_ms / 1000.0)
        latency_ms = (time.time() - start_time) * 1000
        
        # Generate response based on type
        if self.response_type == MockResponseType.SUCCESS:
            content = self.response_content
            error = None
            tokens_used = len(content) // 4
        
        elif self.response_type == MockResponseType.ERROR:
            content = ""
            error = self.error_message
            tokens_used = 0
        
        elif self.response_type == MockResponseType.TIMEOUT:
            content = ""
            error = "Mock timeout error"
            tokens_used = 0
        
        elif self.response_type == MockResponseType.RATE_LIMIT:
            content = ""
            error = "Mock rate limit error"
            tokens_used = 0
        
        else:
            content = ""
            error = "Unknown response type"
            tokens_used = 0
        
        # Calculate cost
        input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        output_tokens = tokens_used
        cost = self._calculate_cost(model_name, input_tokens, output_tokens)
        
        # Create response
        response = ProviderResponse(
            content=content,
            model=model_name,
            tokens_used=input_tokens + output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            error=error,
        )
        
        # Record call
        if error is None:
            self._record_call(response)
        
        return response
    
    def stream_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> Iterator[ProviderResponse]:
        """
        Stream mock responses.
        
        Args:
            request: Request dictionary
            timeout: Request timeout
        
        Yields:
            ProviderResponse objects
        """
        # Validate request
        self.validate_request(request)
        
        model_name = request.get("model", "mock-model-1")
        messages = request.get("messages", [])
        
        # Record request
        self.request_history.append({
            "model": model_name,
            "messages": messages,
            "timestamp": time.time(),
            "streaming": True,
        })
        
        start_time = time.time()
        
        if self.response_type == MockResponseType.SUCCESS:
            # Stream content in chunks
            content = self.response_content
            chunk_size = max(1, len(content) // 5)
            accumulated = ""
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                accumulated += chunk
                
                # Simulate streaming latency
                time.sleep(self.latency_ms / 1000.0 / 5)
                
                latency_ms = (time.time() - start_time) * 1000
                input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
                output_tokens = len(accumulated) // 4
                cost = self._calculate_cost(model_name, input_tokens, output_tokens)
                
                yield ProviderResponse(
                    content=accumulated,
                    model=model_name,
                    tokens_used=input_tokens + output_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                )
            
            # Record final call
            latency_ms = (time.time() - start_time) * 1000
            input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
            output_tokens = len(accumulated) // 4
            cost = self._calculate_cost(model_name, input_tokens, output_tokens)
            
            final_response = ProviderResponse(
                content=accumulated,
                model=model_name,
                tokens_used=input_tokens + output_tokens,
                cost=cost,
                latency_ms=latency_ms,
            )
            
            self._record_call(final_response)
        
        else:
            # Error response
            time.sleep(self.latency_ms / 1000.0)
            latency_ms = (time.time() - start_time) * 1000
            
            yield ProviderResponse(
                content="",
                model=model_name,
                tokens_used=0,
                cost=0.0,
                latency_ms=latency_ms,
                error=self.error_message,
            )
    
    def validate_request(self, request: Dict) -> bool:
        """
        Validate a mock request.
        
        Args:
            request: Request to validate
        
        Returns:
            True if valid
        
        Raises:
            ValueError: If invalid
        """
        if not isinstance(request, dict):
            raise ValueError("Request must be a dictionary")
        
        if "messages" not in request:
            raise ValueError("Request must contain 'messages'")
        
        messages = request["messages"]
        if not isinstance(messages, list) or len(messages) == 0:
            raise ValueError("Messages must be a non-empty list")
        
        for msg in messages:
            if not isinstance(msg, dict):
                raise ValueError("Each message must be a dictionary")
            if "role" not in msg or "content" not in msg:
                raise ValueError("Each message must have 'role' and 'content'")
        
        model = request.get("model", "mock-model-1")
        if model not in self.PRICING:
            raise ValueError(f"Unknown model: {model}")
        
        return True
    
    def calculate_cost(self, tokens_used: int, model: str) -> float:
        """
        Calculate cost for a mock request.
        
        Args:
            tokens_used: Number of tokens used
            model: Model name
        
        Returns:
            Cost in USD
        """
        return self._calculate_cost(model, tokens_used // 2, tokens_used // 2)
    
    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost based on input and output tokens.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        
        Returns:
            Cost in USD
        """
        if model not in self.PRICING:
            return 0.0
        
        pricing = self.PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def get_request_history(self) -> List[Dict]:
        """
        Get history of all requests made to this provider.
        
        Returns:
            List of request dictionaries
        """
        return self.request_history.copy()
    
    def clear_history(self) -> None:
        """Clear request history"""
        self.request_history.clear()
    
    def set_response_type(self, response_type: MockResponseType) -> None:
        """
        Set the type of response to return.
        
        Args:
            response_type: Type of response
        """
        self.response_type = response_type
    
    def set_response_content(self, content: str) -> None:
        """
        Set the content to return in successful responses.
        
        Args:
            content: Response content
        """
        self.response_content = content
    
    def set_latency(self, latency_ms: float) -> None:
        """
        Set the simulated latency.
        
        Args:
            latency_ms: Latency in milliseconds
        """
        self.latency_ms = latency_ms
    
    def set_error_message(self, error_message: str) -> None:
        """
        Set the error message for error responses.
        
        Args:
            error_message: Error message
        """
        self.error_message = error_message
