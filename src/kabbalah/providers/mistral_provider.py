"""
Mistral Provider Implementation

Implements the BaseProvider interface for Mistral's models.
"""

import os
import time
from typing import Dict, Optional, Iterator
from mistralai.client import Mistral

from .base import BaseProvider, ProviderResponse
from ..secrets_vault import get_api_key


class MistralProvider(BaseProvider):
    """
    Mistral LLM Provider.
    
    Supports:
    - mistral-large (recommended for most tasks)
    - mistral-medium
    - mistral-small
    """
    
    # Pricing per 1M tokens (as of 2026-04-10)
    PRICING = {
        "mistral-large": {
            "input": 0.27,      # $0.27 per 1M input tokens
            "output": 0.81,     # $0.81 per 1M output tokens
        },
        "mistral-medium": {
            "input": 0.27,
            "output": 0.81,
        },
        "mistral-small": {
            "input": 0.14,
            "output": 0.42,
        },
    }
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Mistral provider.
        
        Args:
            api_key: Mistral API key (or use vault/secrets_vault.py)
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)
        
        # Get API key: parameter > vault > environment
        if not self.api_key:
            try:
                self.api_key = get_api_key('mistral')
            except (KeyError, FileNotFoundError):
                self.api_key = os.getenv("MISTRAL_API_KEY")
        
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY not found in vault or environment")
        
        # Initialize Mistral client
        self.client = Mistral(api_key=self.api_key)
    
    def execute_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> ProviderResponse:
        """
        Execute a request to Mistral.
        
        Args:
            request: Request with model, messages, max_tokens, etc.
            timeout: Request timeout
        
        Returns:
            ProviderResponse with the result
        """
        # Validate request
        self.validate_request(request)
        
        model_name = request.get("model", "mistral-large")
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)
        top_p = request.get("top_p", 0.95)
        
        start_time = time.time()
        
        try:
            # Create the request (messages are already in dict format)
            response = self.client.chat.complete(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract content
            content = response.choices[0].message.content if response.choices else ""
            
            # Get token counts from response
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            
            cost = self._calculate_cost(model_name, input_tokens, output_tokens)
            
            # Record the call
            provider_response = ProviderResponse(
                content=content,
                model=model_name,
                tokens_used=input_tokens + output_tokens,
                cost=cost,
                latency_ms=latency_ms,
                raw_response={"usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens}},
            )
            
            self._record_call(provider_response)
            
            return provider_response
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            return ProviderResponse(
                content="",
                model=model_name,
                tokens_used=0,
                cost=0.0,
                latency_ms=latency_ms,
                error=str(e),
            )
    
    def stream_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> Iterator[ProviderResponse]:
        """
        Stream responses from Mistral.
        
        Args:
            request: Request dictionary
            timeout: Request timeout
        
        Yields:
            ProviderResponse objects as they arrive
        """
        # Validate request
        self.validate_request(request)
        
        model_name = request.get("model", "mistral-large")
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)
        top_p = request.get("top_p", 0.95)
        
        start_time = time.time()
        
        try:
            # Create the streaming request (messages are already in dict format)
            response = self.client.chat.stream(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            
            accumulated_content = ""
            input_tokens = 0
            
            for chunk in response:
                # Extract content from chunk
                if chunk.choices and chunk.choices[0].delta.content:
                    chunk_text = chunk.choices[0].delta.content
                    accumulated_content += chunk_text
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Estimate tokens
                    output_tokens = len(accumulated_content) // 4
                    cost = self._calculate_cost(model_name, input_tokens, output_tokens)
                    
                    yield ProviderResponse(
                        content=accumulated_content,
                        model=model_name,
                        tokens_used=input_tokens + output_tokens,
                        cost=cost,
                        latency_ms=latency_ms,
                    )
            
            # Record final call
            latency_ms = (time.time() - start_time) * 1000
            output_tokens = len(accumulated_content) // 4
            cost = self._calculate_cost(model_name, input_tokens, output_tokens)
            
            final_response = ProviderResponse(
                content=accumulated_content,
                model=model_name,
                tokens_used=input_tokens + output_tokens,
                cost=cost,
                latency_ms=latency_ms,
            )
            
            self._record_call(final_response)
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            yield ProviderResponse(
                content="",
                model=model_name,
                tokens_used=0,
                cost=0.0,
                latency_ms=latency_ms,
                error=str(e),
            )
    
    def validate_request(self, request: Dict) -> bool:
        """
        Validate a request.
        
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
        
        model = request.get("model", "mistral-large")
        if model not in self.PRICING:
            raise ValueError(f"Unknown model: {model}")
        
        return True
    
    def calculate_cost(self, tokens_used: int, model: str) -> float:
        """
        Calculate cost for a request.
        
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
