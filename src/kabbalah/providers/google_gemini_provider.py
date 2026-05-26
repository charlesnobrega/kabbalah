"""
Google Gemini Provider Implementation

Implements the BaseProvider interface for Google's Gemini models.
"""

import os
import time
from typing import Dict, Optional, Iterator
import google.generativeai as genai

from .base import BaseProvider, ProviderResponse
from ..secrets_vault import get_api_key


class GoogleGeminiProvider(BaseProvider):
    """
    Google Gemini LLM Provider.
    
    Supports:
    - gemini-2.5-flash (recommended for most tasks)
    - gemini-2.5-pro (more powerful)
    - gemini-2.0-flash
    - gemini-pro-latest
    """
    
    # Pricing per 1M tokens (as of 2026-04-10)
    PRICING = {
        "gemini-2.5-flash": {
            "input": 0.075,      # $0.075 per 1M input tokens
            "output": 0.30,      # $0.30 per 1M output tokens
        },
        "gemini-2.5-pro": {
            "input": 1.50,
            "output": 6.00,
        },
        "gemini-2.0-flash": {
            "input": 0.075,
            "output": 0.30,
        },
        "gemini-pro-latest": {
            "input": 0.075,
            "output": 0.30,
        },
    }
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Google Gemini provider.
        
        Args:
            api_key: Google API key (or use vault/secrets_vault.py)
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)
        
        # Get API key: parameter > vault > environment
        if not self.api_key:
            try:
                self.api_key = get_api_key('google')
            except (KeyError, FileNotFoundError):
                self.api_key = os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in vault or environment")
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
    
    def execute_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> ProviderResponse:
        """
        Execute a request to Google Gemini.
        
        Args:
            request: Request with model, messages, max_tokens, etc.
            timeout: Request timeout (not used by Gemini API)
        
        Returns:
            ProviderResponse with the result
        """
        # Validate request
        self.validate_request(request)
        
        model_name = request.get("model", "gemini-2.5-flash")
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)
        top_p = request.get("top_p", 0.95)
        
        start_time = time.time()
        
        try:
            # Create the model
            model = genai.GenerativeModel(model_name)
            
            # Convert messages to Gemini format
            # Gemini expects a single prompt, not a message list
            # For now, we'll concatenate messages
            prompt = self._format_messages(messages)
            
            # Generate content
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                ),
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract content safely
            # Check if response has valid parts before accessing text
            content = ""
            if response:
                # Try to extract text safely
                try:
                    content = response.text
                except (ValueError, AttributeError):
                    # If response.text fails, try to extract from parts
                    if hasattr(response, 'parts') and response.parts:
                        content = "".join(
                            part.text for part in response.parts 
                            if hasattr(part, 'text') and part.text
                        )
                    # If still no content, check candidates
                    elif hasattr(response, 'candidates') and response.candidates:
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        content += part.text
            
            # Calculate tokens and cost
            # Gemini doesn't provide token counts in the response
            # We'll estimate based on character count (rough approximation)
            input_tokens = len(prompt) // 4  # Rough estimate
            output_tokens = len(content) // 4  # Rough estimate
            
            cost = self._calculate_cost(model_name, input_tokens, output_tokens)
            
            # Record the call
            provider_response = ProviderResponse(
                content=content,
                model=model_name,
                tokens_used=input_tokens + output_tokens,
                cost=cost,
                latency_ms=latency_ms,
                raw_response={"text": content},
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
        Stream responses from Google Gemini.
        
        Args:
            request: Request dictionary
            timeout: Request timeout
        
        Yields:
            ProviderResponse objects as they arrive
        """
        # Validate request
        self.validate_request(request)
        
        model_name = request.get("model", "gemini-2.5-flash")
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)
        top_p = request.get("top_p", 0.95)
        
        start_time = time.time()
        
        try:
            # Create the model
            model = genai.GenerativeModel(model_name)
            
            # Convert messages to Gemini format
            prompt = self._format_messages(messages)
            
            # Stream content
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                ),
                stream=True,
            )
            
            accumulated_content = ""
            
            for chunk in response:
                # Safely extract text from chunk
                chunk_text = ""
                if chunk:
                    try:
                        chunk_text = chunk.text
                    except (ValueError, AttributeError):
                        # If chunk.text fails, try to extract from parts
                        if hasattr(chunk, 'parts') and chunk.parts:
                            chunk_text = "".join(
                                part.text for part in chunk.parts 
                                if hasattr(part, 'text') and part.text
                            )
                        # If still no content, check candidates
                        elif hasattr(chunk, 'candidates') and chunk.candidates:
                            for candidate in chunk.candidates:
                                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                    for part in candidate.content.parts:
                                        if hasattr(part, 'text') and part.text:
                                            chunk_text += part.text
                
                if chunk_text:
                    accumulated_content += chunk_text
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Estimate tokens
                    input_tokens = len(prompt) // 4
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
            input_tokens = len(prompt) // 4
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
        
        model = request.get("model", "gemini-2.5-flash")
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
    
    def _format_messages(self, messages: list) -> str:
        """
        Format messages for Gemini API.
        
        Gemini expects a single prompt, not a message list.
        We'll format the messages as a conversation.
        
        Args:
            messages: List of message dictionaries
        
        Returns:
            Formatted prompt string
        """
        formatted = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
            else:
                formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
