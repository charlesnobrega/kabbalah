# Providers Implementation Guide

## Overview

This guide details how to implement each LLM provider for Kabbalah Phase 4.

---

## Provider Template

Every provider must implement this interface:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Iterator
from dataclasses import dataclass

@dataclass
class ProviderResponse:
    """Standard response format for all providers"""
    content: str
    model: str
    tokens_used: int
    cost: float
    latency_ms: float
    error: Optional[str] = None
    raw_response: Optional[Dict] = None

class BaseProvider(ABC):
    """Base class for all LLM providers"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.config = kwargs
        self.call_count = 0
        self.total_cost = 0.0
    
    @abstractmethod
    def execute_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> ProviderResponse:
        """Execute a single request"""
        pass
    
    @abstractmethod
    def stream_request(
        self,
        request: Dict,
        timeout: float = 30.0
    ) -> Iterator[ProviderResponse]:
        """Stream responses (if supported)"""
        pass
    
    @abstractmethod
    def validate_request(self, request: Dict) -> bool:
        """Validate request format"""
        pass
    
    @abstractmethod
    def calculate_cost(self, tokens_used: int, model: str) -> float:
        """Calculate cost for request"""
        pass
    
    def get_stats(self) -> Dict:
        """Get provider statistics"""
        return {
            "call_count": self.call_count,
            "total_cost": self.total_cost,
            "average_cost": self.total_cost / max(1, self.call_count)
        }
```

---

## Provider Implementations

### 1. OpenAI Provider

**Status**: NOT IMPLEMENTED
**Priority**: 1 (Core)
**Complexity**: Medium
**Cost**: $0.01-0.05 per test

**Models Supported**:
- gpt-4
- gpt-4-turbo
- gpt-3.5-turbo
- gpt-3.5-turbo-16k

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/openai_provider.py`
- [ ] Implement execute_request() using OpenAI SDK
- [ ] Implement stream_request() for streaming
- [ ] Implement cost calculation (tokens * rate)
- [ ] Implement error handling (rate limits, auth, etc)
- [ ] Implement retry logic with exponential backoff
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Key Features**:
- Token counting (use tiktoken)
- Streaming support
- Function calling support
- Vision support (gpt-4-vision)

**Setup**:
```bash
pip install openai tiktoken
export OPENAI_API_KEY=sk-...
```

**Test Example**:
```python
def test_openai_simple_completion():
    provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
    response = provider.execute_request({
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 10
    })
    assert response.content
    assert response.cost > 0
```

---

### 2. Anthropic Provider

**Status**: NOT IMPLEMENTED
**Priority**: 1 (Core)
**Complexity**: Medium
**Cost**: $0.01-0.03 per test

**Models Supported**:
- claude-3-opus
- claude-3-sonnet
- claude-3-haiku
- claude-2.1
- claude-2

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/anthropic_provider.py`
- [ ] Implement execute_request() using Anthropic SDK
- [ ] Implement stream_request() for streaming
- [ ] Implement cost calculation (tokens * rate)
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Key Features**:
- Token counting
- Streaming support
- System prompts
- Vision support (claude-3)

**Setup**:
```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

**Test Example**:
```python
def test_anthropic_simple_completion():
    provider = AnthropicProvider(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = provider.execute_request({
        "model": "claude-3-haiku-20240307",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 10
    })
    assert response.content
    assert response.cost > 0
```

---

### 3. Ollama Provider

**Status**: NOT IMPLEMENTED
**Priority**: 1 (Core)
**Complexity**: Low
**Cost**: Free (local)

**Models Supported**:
- Any model available in Ollama
- llama2, mistral, neural-chat, etc.

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/ollama_provider.py`
- [ ] Implement execute_request() using Ollama API
- [ ] Implement stream_request() for streaming
- [ ] Implement cost calculation (always 0)
- [ ] Implement error handling (connection, model not found)
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Key Features**:
- Local inference (no API key needed)
- Streaming support
- Model management
- GPU acceleration support

**Setup**:
```bash
# Install Ollama from https://ollama.ai
ollama pull llama2
ollama serve  # Runs on localhost:11434

# In tests
export OLLAMA_BASE_URL=http://localhost:11434
```

**Test Example**:
```python
def test_ollama_simple_completion():
    provider = OllamaProvider(base_url="http://localhost:11434")
    response = provider.execute_request({
        "model": "llama2",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 10
    })
    assert response.content
    assert response.cost == 0  # Local, free
```

---

### 4. Google Gemini Provider

**Status**: NOT IMPLEMENTED
**Priority**: 2 (Important)
**Complexity**: Medium
**Cost**: $0.001-0.01 per test

**Models Supported**:
- gemini-pro
- gemini-pro-vision
- gemini-1.5-pro
- gemini-1.5-flash

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/gemini_provider.py`
- [ ] Implement execute_request() using Google SDK
- [ ] Implement stream_request() for streaming
- [ ] Implement cost calculation
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
pip install google-generativeai
export GOOGLE_API_KEY=...
```

---

### 5. Groq Provider

**Status**: NOT IMPLEMENTED
**Priority**: 2 (Important)
**Complexity**: Low
**Cost**: Free (free tier available)

**Models Supported**:
- mixtral-8x7b-32768
- llama2-70b-4096
- gemma-7b-it

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/groq_provider.py`
- [ ] Implement execute_request() using Groq SDK
- [ ] Implement stream_request() for streaming
- [ ] Implement cost calculation (free tier)
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
pip install groq
export GROQ_API_KEY=gsk-...
```

---

### 6. Together Provider

**Status**: NOT IMPLEMENTED
**Priority**: 2 (Important)
**Complexity**: Low
**Cost**: Free (free tier available)

**Models Supported**:
- meta-llama/Llama-2-70b-chat-hf
- mistralai/Mistral-7B-Instruct-v0.1
- NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/together_provider.py`
- [ ] Implement execute_request() using Together SDK
- [ ] Implement stream_request() for streaming
- [ ] Implement cost calculation
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
pip install together
export TOGETHER_API_KEY=...
```

---

### 7. DeepSeek Provider

**Status**: NOT IMPLEMENTED
**Priority**: 3 (Extended)
**Complexity**: Low
**Cost**: $0.001-0.01 per test

**Models Supported**:
- deepseek-chat
- deepseek-coder

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/deepseek_provider.py`
- [ ] Implement execute_request()
- [ ] Implement stream_request()
- [ ] Implement cost calculation
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
export DEEPSEEK_API_KEY=...
```

---

### 8. Mistral Provider

**Status**: NOT IMPLEMENTED
**Priority**: 3 (Extended)
**Complexity**: Low
**Cost**: $0.001-0.01 per test

**Models Supported**:
- mistral-small
- mistral-medium
- mistral-large

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/mistral_provider.py`
- [ ] Implement execute_request()
- [ ] Implement stream_request()
- [ ] Implement cost calculation
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
pip install mistralai
export MISTRAL_API_KEY=...
```

---

### 9. Replicate Provider

**Status**: NOT IMPLEMENTED
**Priority**: 3 (Extended)
**Complexity**: Medium
**Cost**: $0.001-0.01 per test

**Models Supported**:
- meta/llama-2-70b-chat
- mistralai/mistral-7b-instruct-v0.1
- stability-ai/stable-diffusion-3

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/replicate_provider.py`
- [ ] Implement execute_request()
- [ ] Implement stream_request()
- [ ] Implement cost calculation
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
pip install replicate
export REPLICATE_API_TOKEN=...
```

---

### 10. HuggingFace Provider

**Status**: NOT IMPLEMENTED
**Priority**: 3 (Extended)
**Complexity**: Medium
**Cost**: Free (free tier available)

**Models Supported**:
- Any model on HuggingFace Hub
- gpt2, distilbert, etc.

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/huggingface_provider.py`
- [ ] Implement execute_request()
- [ ] Implement stream_request()
- [ ] Implement cost calculation
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
pip install huggingface-hub
export HUGGINGFACE_API_KEY=hf_...
```

---

### 11. Azure OpenAI Provider

**Status**: NOT IMPLEMENTED
**Priority**: 3 (Extended)
**Complexity**: Medium
**Cost**: $0.01-0.05 per test

**Models Supported**:
- gpt-4
- gpt-3.5-turbo
- (depends on Azure deployment)

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/azure_openai_provider.py`
- [ ] Implement execute_request()
- [ ] Implement stream_request()
- [ ] Implement cost calculation
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
pip install openai
export AZURE_OPENAI_KEY=...
export AZURE_OPENAI_ENDPOINT=...
export AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

---

### 12. LM Studio Provider

**Status**: NOT IMPLEMENTED
**Priority**: 3 (Extended)
**Complexity**: Low
**Cost**: Free (local)

**Models Supported**:
- Any model available in LM Studio
- Local inference

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/lm_studio_provider.py`
- [ ] Implement execute_request()
- [ ] Implement stream_request()
- [ ] Implement cost calculation (always 0)
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
# Install LM Studio from https://lmstudio.ai
# Start LM Studio and load a model
# API runs on localhost:1234

export LM_STUDIO_BASE_URL=http://localhost:1234
```

---

### 13. vLLM Provider

**Status**: NOT IMPLEMENTED
**Priority**: 3 (Extended)
**Complexity**: Low
**Cost**: Free (local)

**Models Supported**:
- Any model supported by vLLM
- Local inference with GPU acceleration

**Implementation Checklist**:
- [ ] Create `src/kabbalah/providers/vllm_provider.py`
- [ ] Implement execute_request()
- [ ] Implement stream_request()
- [ ] Implement cost calculation (always 0)
- [ ] Implement error handling
- [ ] Implement retry logic
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests
- [ ] Write integration tests (optional)

**Setup**:
```bash
pip install vllm
vllm serve meta-llama/Llama-2-7b-hf  # Runs on localhost:8000

export VLLM_BASE_URL=http://localhost:8000
```

---

## Implementation Order

### Week 1: Infrastructure + Priority 1
1. Create BaseProvider class
2. Create MockProvider class
3. Implement OpenAI provider
4. Implement Anthropic provider
5. Implement Ollama provider

### Week 2: Priority 2
6. Implement Google Gemini provider
7. Implement Groq provider
8. Implement Together provider

### Week 3: Priority 3 + Tests
9. Implement DeepSeek provider
10. Implement Mistral provider
11. Implement Replicate provider
12. Implement HuggingFace provider
13. Implement Azure OpenAI provider
14. Implement LM Studio provider
15. Implement vLLM provider

### Week 4: Testing + PBT
16. Write unit tests for all providers
17. Write PBT tests for all providers
18. Update Phase 1-3 tests to use PBT
19. Create integration test infrastructure
20. Documentation

---

## Testing Each Provider

### Unit Tests (Mock)
```python
def test_provider_simple_request():
    """Test: Simple request works"""
    provider = SomeProvider(mock=True)
    response = provider.execute_request({...})
    assert response.content
    assert response.cost >= 0

def test_provider_error_handling():
    """Test: Errors are handled"""
    provider = SomeProvider(mock=True)
    with pytest.raises(ValueError):
        provider.execute_request({"invalid": "request"})

def test_provider_cost_calculation():
    """Test: Cost is calculated correctly"""
    provider = SomeProvider(mock=True)
    response = provider.execute_request({...})
    assert response.cost == expected_cost
```

### Property-Based Tests
```python
@given(request=valid_requests)
def test_provider_handles_valid_requests(request):
    """Property: All valid requests should succeed"""
    provider = SomeProvider(mock=True)
    response = provider.execute_request(request)
    assert response is not None
    assert response.error is None

@given(request=edge_case_requests)
def test_provider_handles_edge_cases(request):
    """Property: Edge cases should raise specific errors"""
    provider = SomeProvider(mock=True)
    with pytest.raises((ValueError, KeyError)):
        provider.execute_request(request)
```

### Integration Tests (Real API)
```python
@pytest.mark.integration
def test_provider_real_api():
    """Test: Real API works"""
    provider = SomeProvider(api_key=os.getenv("API_KEY"))
    response = provider.execute_request({...})
    assert response.content
    assert response.cost > 0
```

---

## Success Criteria

- ✅ All 13 providers implemented
- ✅ Each provider has >80% unit test coverage
- ✅ Each provider has property-based tests
- ✅ Mock provider infrastructure complete
- ✅ Integration test infrastructure complete
- ✅ Phase 1-3 tests updated to use PBT
- ✅ Documentation complete
- ✅ Cost tracking working
- ✅ Error handling comprehensive
- ✅ Fallback chains working

