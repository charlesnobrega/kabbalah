# Provider Implementation Template

Use this template to implement new providers quickly and consistently.

## Step 1: Create Provider Class

**File**: `src/kabbalah/providers/{provider_name}_provider.py`

```python
"""
{Provider Name} Provider Implementation

Implements the BaseProvider interface for {Provider Name}'s models.
"""

import os
import time
from typing import Dict, Optional, Iterator
import {provider_library} as {provider_alias}

from .base import BaseProvider, ProviderResponse


class {ProviderName}Provider(BaseProvider):
    """
    {Provider Name} LLM Provider.
    
    Supports:
    - model-1 (recommended)
    - model-2
    - model-3
    """
    
    # Pricing per 1M tokens
    PRICING = {
        "model-1": {
            "input": 0.001,
            "output": 0.002,
        },
        "model-2": {
            "input": 0.002,
            "output": 0.004,
        },
    }
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize {Provider Name} provider."""
        super().__init__(api_key, **kwargs)
        
        if not self.api_key:
            self.api_key = os.getenv("{PROVIDER_API_KEY_ENV_VAR}")
        
        if not self.api_key:
            raise ValueError("{PROVIDER_API_KEY_ENV_VAR} not provided")
        
        # Configure the API
        {provider_alias}.configure(api_key=self.api_key)
    
    def execute_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> ProviderResponse:
        """Execute a request to {Provider Name}."""
        self.validate_request(request)
        
        model_name = request.get("model", "model-1")
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)
        
        start_time = time.time()
        
        try:
            # TODO: Implement provider-specific request logic
            response = {provider_alias}.generate(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract content
            content = response.get("content", "")
            
            # Calculate tokens and cost
            input_tokens = len(str(messages)) // 4
            output_tokens = len(content) // 4
            cost = self._calculate_cost(model_name, input_tokens, output_tokens)
            
            provider_response = ProviderResponse(
                content=content,
                model=model_name,
                tokens_used=input_tokens + output_tokens,
                cost=cost,
                latency_ms=latency_ms,
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
        """Stream responses from {Provider Name}."""
        self.validate_request(request)
        
        model_name = request.get("model", "model-1")
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 1024)
        temperature = request.get("temperature", 0.7)
        
        start_time = time.time()
        
        try:
            # TODO: Implement provider-specific streaming logic
            response = {provider_alias}.stream(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            accumulated_content = ""
            
            for chunk in response:
                chunk_text = chunk.get("content", "")
                
                if chunk_text:
                    accumulated_content += chunk_text
                    
                    latency_ms = (time.time() - start_time) * 1000
                    input_tokens = len(str(messages)) // 4
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
            input_tokens = len(str(messages)) // 4
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
        """Validate a request."""
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
        
        model = request.get("model", "model-1")
        if model not in self.PRICING:
            raise ValueError(f"Unknown model: {model}")
        
        return True
    
    def calculate_cost(self, tokens_used: int, model: str) -> float:
        """Calculate cost for a request."""
        return self._calculate_cost(model, tokens_used // 2, tokens_used // 2)
    
    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost based on input and output tokens."""
        if model not in self.PRICING:
            return 0.0
        
        pricing = self.PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
```

## Step 2: Create Test File

**File**: `tests/providers/test_{provider_name}_provider.py`

```python
"""
Tests for {Provider Name} Provider

Tests the {ProviderName}Provider implementation with real API calls.
"""

import os
import pytest
from dotenv import load_dotenv

from src.kabbalah.providers import {ProviderName}Provider, ProviderResponse


load_dotenv()


@pytest.fixture
def provider():
    """Create a {Provider Name} provider instance"""
    api_key = os.getenv("{PROVIDER_API_KEY_ENV_VAR}")
    if not api_key:
        pytest.skip("{PROVIDER_API_KEY_ENV_VAR} not set")
    
    return {ProviderName}Provider(api_key=api_key)


class Test{ProviderName}Provider:
    """Test {Provider Name} Provider"""
    
    def test_provider_initialization(self, provider):
        """Test that provider initializes correctly"""
        assert provider is not None
        assert provider.api_key is not None
        assert provider.call_count == 0
        assert provider.total_cost == 0.0
    
    def test_validate_request_valid(self, provider):
        """Test validation of valid request"""
        request = {
            "model": "model-1",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50,
        }
        
        assert provider.validate_request(request) is True
    
    def test_execute_request_simple(self, provider):
        """Test simple request execution"""
        request = {
            "model": "model-1",
            "messages": [
                {"role": "user", "content": "Say hello in one word"}
            ],
            "max_tokens": 50,
        }
        
        response = provider.execute_request(request)
        
        assert isinstance(response, ProviderResponse)
        assert response.content is not None or response.error is not None
        assert response.model == "model-1"
        assert response.latency_ms > 0
        assert response.cost >= 0
    
    def test_calculate_cost(self, provider):
        """Test cost calculation"""
        cost = provider.calculate_cost(1000, "model-1")
        
        assert cost >= 0
        assert isinstance(cost, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## Step 3: Update __init__.py

**File**: `src/kabbalah/providers/__init__.py`

```python
from .base import BaseProvider, ProviderResponse
from .google_gemini_provider import GoogleGeminiProvider
from .{provider_name}_provider import {ProviderName}Provider

__all__ = [
    'BaseProvider',
    'ProviderResponse',
    'GoogleGeminiProvider',
    '{ProviderName}Provider',
]
```

## Step 4: Add API Key to .env

```bash
{PROVIDER_API_KEY_ENV_VAR}=your_api_key_here
```

## Step 5: Run Tests

```bash
python -m pytest tests/providers/test_{provider_name}_provider.py -v
```

## Checklist

- [ ] Provider class created with all required methods
- [ ] Test file created with comprehensive tests
- [ ] __init__.py updated with new provider
- [ ] API key added to .env
- [ ] Tests passing (or rate limited, which is OK)
- [ ] Documentation updated
- [ ] Code reviewed for quality

## Common Issues

### Issue: API Key Not Found
**Solution**: Check .env file and environment variable name

### Issue: Rate Limiting (429 errors)
**Solution**: Wait between test runs or upgrade to paid tier

### Issue: Response Parsing Error
**Solution**: Check provider's response format and adjust parsing logic

### Issue: Token Estimation Wrong
**Solution**: Use provider's token counting if available, or adjust character ratio

## Provider-Specific Notes

### OpenAI
- Uses `openai` library
- Supports chat completions and completions
- Good token counting available

### Groq
- Uses `groq` library
- Very fast inference
- Good for testing performance

### Mistral
- Uses `mistralai` library
- European provider
- Good for diversity

### Together
- Uses `together` library
- Distributed inference
- Good for scalability

### DeepSeek
- Uses `deepseek` library
- Chinese provider
- Good for international testing

---

**Use this template to implement new providers consistently and quickly.**
