"""
Base Provider Interface

Defines the abstract interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Iterator
import time


@dataclass
class ProviderResponse:
    """Standard response format for all providers"""
    
    content: str
    """The generated content/response"""
    
    model: str
    """The model used for generation"""
    
    tokens_used: int
    """Number of tokens used in the request"""
    
    cost: float
    """Cost of the request in USD"""
    
    latency_ms: float
    """Latency of the request in milliseconds"""
    
    error: Optional[str] = None
    """Error message if request failed"""
    
    raw_response: Optional[Dict] = None
    """Raw response from the provider (for debugging)"""


class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    All providers must implement this interface to be compatible with Kabbalah.
    """
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize the provider.
        
        Args:
            api_key: API key for the provider
            **kwargs: Additional configuration options
        """
        self.api_key = api_key
        self.config = kwargs
        self.call_count = 0
        self.total_cost = 0.0
        self.total_tokens = 0
    
    @abstractmethod
    def execute_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> ProviderResponse:
        """
        Execute a single request to the provider.
        
        Args:
            request: Request dictionary with:
                - model: Model name
                - messages: List of messages
                - max_tokens: Maximum tokens to generate
                - temperature: Temperature for generation
                - top_p: Top-p sampling parameter
            timeout: Request timeout in seconds
        
        Returns:
            ProviderResponse with the result
        
        Raises:
            ValueError: If request is invalid
            TimeoutError: If request times out
            Exception: If provider returns an error
        """
        pass
    
    @abstractmethod
    def stream_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> Iterator[ProviderResponse]:
        """
        Stream responses from the provider (if supported).
        
        Args:
            request: Request dictionary
            timeout: Request timeout in seconds
        
        Yields:
            ProviderResponse objects as they arrive
        
        Raises:
            NotImplementedError: If provider doesn't support streaming
        """
        pass
    
    @abstractmethod
    def validate_request(self, request: Dict) -> bool:
        """
        Validate that a request has the correct format.
        
        Args:
            request: Request dictionary to validate
        
        Returns:
            True if valid, False otherwise
        
        Raises:
            ValueError: If request is invalid with details
        """
        pass
    
    @abstractmethod
    def calculate_cost(self, tokens_used: int, model: str) -> float:
        """
        Calculate the cost of a request.
        
        Args:
            tokens_used: Number of tokens used
            model: Model name
        
        Returns:
            Cost in USD
        """
        pass
    
    def get_stats(self) -> Dict:
        """
        Get provider statistics.
        
        Returns:
            Dictionary with:
                - call_count: Number of calls made
                - total_cost: Total cost in USD
                - average_cost: Average cost per call
                - total_tokens: Total tokens used
        """
        return {
            "call_count": self.call_count,
            "total_cost": self.total_cost,
            "average_cost": self.total_cost / max(1, self.call_count),
            "total_tokens": self.total_tokens,
        }
    
    def _record_call(self, response: ProviderResponse) -> None:
        """
        Record a call for statistics.
        
        Args:
            response: The response from the call
        """
        self.call_count += 1
        self.total_cost += response.cost
        self.total_tokens += response.tokens_used
