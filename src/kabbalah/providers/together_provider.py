"""
Together Provider Implementation

Implements the BaseProvider interface for Together's models.
"""

import os
import time
from typing import Dict, Optional, Iterator
from together import Client

from .base import BaseProvider, ProviderResponse


class TogetherProvider(BaseProvider):
    """
    Together LLM Provider.
    
    Supports:
    - meta-llama/Llama-2-70b-chat-hf (recommended)
    - meta-llama/Llama-2-13b-chat-hf
    - mistralai/Mistral-7B-Instruct-v0.1
    - NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO
    """
    
    # Pricing per 1M tokens (as of 2026-04-10)
    PRICING = {
        "meta-llama/Llama-2-70b-chat-hf": {
            "input": 0.90,      # $0.90 per 1M input tokens
            "output": 0.90,     # $0.90 per 1M output tokens
        },
        "meta-llama/Llama-2-13b-chat-hf": {
            "input": 0.225,
            "output": 0.225,
        },
        "mistralai/Mistral-7B-Instruct-v0.1": {
            "input": 0.15,
            "output": 0.15,
        },
        "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO": {
            "input": 0.90,
            "output": 0.90,
        },
    }
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Together provider.
        
        Args:
            api_key: Together API key (or use TOGETHER_API_KEY env var)
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)
        
        # Get API key from parameter or environment
        if not self.api_key:
            self.api_key = os.getenv("TOGETHER_API_KEY")
        
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY not provided and not in environment")
        
        # Initialize Together client
        self.client = Client(api_key=self.api_key)
    
    def execute_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> ProviderResponse:
        """
        Execute a request to Together.
        
        Args:
            request: Request with model, messages, max_tokens, etc.
            timeout: Request timeout
        
        Returns:
            ProviderResponse with the result
        """
        # Validate request
        self.validate_request(request)
        
        model_name = request.get("model", "meta-llama/Llama-2-70b-chat-hf")
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)
        top_p = request.get("top_p", 0.95)
        
        start_time = time.time()
        
        try:
            # Create the request using OpenAI-compatible API
            response = self.client.chat.completions.create(
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
                raw_response=response,
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
        Stream responses from Together.
        
        Args:
            request: Request dictionary
            timeout: Request timeout
        
        Yields:
            ProviderResponse objects as they arrive
        """
        # Validate request
        self.validate_request(request)
        
        model_name = request.get("model", "meta-llama/Llama-2-70b-chat-hf")
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)
        top_p = request.get("top_p", 0.95)
        
        start_time = time.time()
        
        try:
            # Create the streaming request
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True,
            )
            
            accumulated_content = ""
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    chunk_text = chunk.choices[0].delta.content
                    accumulated_content += chunk_text
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Estimate tokens
                    input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
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
            input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
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
        
        model = request.get("model", "meta-llama/Llama-2-70b-chat-hf")
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
