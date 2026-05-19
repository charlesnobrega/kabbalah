# Provider Testing Strategy - Kabbalah Phase 4

## Overview

This document defines how to test the Provider Abstraction Layer with real LLM providers while maintaining fast, deterministic unit tests.

---

## Testing Pyramid

```
┌─────────────────────────────────────────┐
│   Integration Tests (Real Providers)    │  Slow, Expensive, Real
│   - Real API calls                      │  - Only run with flag
│   - Real responses                      │  - Requires API keys
│   - Real error scenarios                │  - ~5-10 min per provider
└─────────────────────────────────────────┘
                    ▲
                    │
┌─────────────────────────────────────────┐
│   Property-Based Tests (Mocks)          │  Fast, Deterministic
│   - Hypothesis strategies               │  - Run on every commit
│   - Mock providers                      │  - No API keys needed
│   - Edge case generation                │  - ~30 sec total
└─────────────────────────────────────────┘
                    ▲
                    │
┌─────────────────────────────────────────┐
│   Unit Tests (Mocks)                    │  Very Fast
│   - Individual components               │  - Run on every save
│   - Mock responses                      │  - No API keys needed
│   - Happy path + error cases            │  - ~5 sec total
└─────────────────────────────────────────┘
```

---

## Provider Categories

### Category A: Local Providers (No API Key Needed)
- **Ollama** - Local LLM server
- **LM Studio** - Local LLM GUI
- **vLLM** - Local inference server

**Testing**: Can test with real local instance or mock

### Category B: Free Tier Providers (Optional API Key)
- **Groq** - Free tier available
- **Together** - Free tier available
- **HuggingFace** - Free tier available

**Testing**: Can test with free tier or mock

### Category C: Paid Providers (API Key Required)
- **OpenAI** - GPT-4, GPT-3.5
- **Anthropic** - Claude
- **Google Gemini** - Gemini models
- **DeepSeek** - DeepSeek models
- **Mistral** - Mistral models
- **Replicate** - Various models
- **Azure OpenAI** - Enterprise OpenAI

**Testing**: Mock by default, real tests optional with API keys

---

## Test Environment Setup

### Environment Variables

```bash
# Mock mode (default)
KABBALAH_TEST_MODE=mock

# Real provider testing (requires API keys)
KABBALAH_TEST_MODE=real
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk-...
TOGETHER_API_KEY=...
HUGGINGFACE_API_KEY=hf_...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=...
MISTRAL_API_KEY=...
REPLICATE_API_TOKEN=...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_ENDPOINT=...

# Local providers
OLLAMA_BASE_URL=http://localhost:11434
LM_STUDIO_BASE_URL=http://localhost:1234
VLLM_BASE_URL=http://localhost:8000
```

### Test Execution Modes

```bash
# Run only unit tests (fast, no API keys)
pytest tests/ -m "not integration"

# Run unit + PBT tests (fast, no API keys)
pytest tests/ -m "not integration" --hypothesis-seed=0

# Run integration tests with real providers (slow, requires API keys)
KABBALAH_TEST_MODE=real pytest tests/ -m "integration"

# Run specific provider tests
KABBALAH_TEST_MODE=real pytest tests/integration/test_openai_provider.py
```

---

## Mock Provider Implementation

### MockProvider Base Class

```python
class MockProvider:
    """Base class for mock providers in tests"""
    
    def __init__(self, deterministic=True):
        self.deterministic = deterministic
        self.call_count = 0
        self.call_history = []
    
    def execute_request(self, request):
        """Return deterministic mock response"""
        self.call_count += 1
        self.call_history.append(request)
        
        # Deterministic response based on input
        if self.deterministic:
            return self._deterministic_response(request)
        else:
            return self._random_response(request)
    
    def _deterministic_response(self, request):
        """Generate same response for same input"""
        # Hash input to generate consistent response
        pass
    
    def _random_response(self, request):
        """Generate random response for fuzzing"""
        pass
```

### Mock Scenarios

```python
# Scenario 1: Happy path
mock_provider.set_response("success", {"result": "..."})

# Scenario 2: Rate limit
mock_provider.set_response("rate_limit", {"error": "429"})

# Scenario 3: Timeout
mock_provider.set_response("timeout", {"error": "timeout"})

# Scenario 4: Invalid response
mock_provider.set_response("invalid", {"malformed": "json"})

# Scenario 5: Partial failure
mock_provider.set_response("partial", {"partial": True})
```

---

## Property-Based Testing Strategy

### Hypothesis Strategies for Providers

```python
from hypothesis import strategies as st

# Strategy for valid requests
valid_requests = st.fixed_dictionaries({
    "model": st.sampled_from(["gpt-4", "claude-3", "gemini-pro"]),
    "messages": st.lists(
        st.fixed_dictionaries({
            "role": st.sampled_from(["user", "assistant"]),
            "content": st.text(min_size=1, max_size=1000)
        }),
        min_size=1,
        max_size=10
    ),
    "temperature": st.floats(min_value=0.0, max_value=2.0),
    "max_tokens": st.integers(min_value=1, max_value=4096)
})

# Strategy for edge cases
edge_case_requests = st.one_of(
    st.fixed_dictionaries({"model": st.just(""), "messages": st.just([])}),  # Empty
    st.fixed_dictionaries({"model": st.just("unknown"), "messages": st.just([])}),  # Unknown
    st.fixed_dictionaries({"temperature": st.just(-1.0)}),  # Invalid temp
)
```

### Properties to Test

```python
@given(request=valid_requests)
def test_provider_request_validation(request):
    """Property: Valid requests should not raise validation errors"""
    provider = MockProvider()
    response = provider.execute_request(request)
    assert response is not None
    assert "error" not in response

@given(request=edge_case_requests)
def test_provider_error_handling(request):
    """Property: Invalid requests should raise specific errors"""
    provider = MockProvider()
    with pytest.raises((ValueError, KeyError)):
        provider.execute_request(request)

@given(
    request1=valid_requests,
    request2=valid_requests
)
def test_provider_determinism(request1, request2):
    """Property: Same request should produce same response"""
    provider = MockProvider(deterministic=True)
    response1 = provider.execute_request(request1)
    response2 = provider.execute_request(request1)  # Same request
    assert response1 == response2

@given(requests=st.lists(valid_requests, min_size=1, max_size=10))
def test_provider_fallback_chain(requests):
    """Property: Fallback chain should try all providers"""
    providers = [MockProvider() for _ in range(3)]
    chain = ProviderFallbackChain(providers)
    
    for request in requests:
        response = chain.execute_request(request)
        assert response is not None
```

---

## Real Provider Integration Tests

### Test Structure

```python
@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("KABBALAH_TEST_MODE") != "real",
    reason="Requires real API keys"
)
class TestOpenAIProvider:
    
    @pytest.fixture
    def provider(self):
        return OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
    
    def test_simple_completion(self, provider):
        """Test: Simple completion works"""
        response = provider.execute_request({
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 10
        })
        assert response["choices"][0]["message"]["content"]
    
    def test_streaming(self, provider):
        """Test: Streaming works"""
        responses = list(provider.stream_request({
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Count to 3"}],
            "stream": True
        }))
        assert len(responses) > 0
    
    def test_error_handling(self, provider):
        """Test: Invalid requests raise errors"""
        with pytest.raises(ValueError):
            provider.execute_request({
                "model": "invalid-model",
                "messages": []
            })
    
    def test_timeout(self, provider):
        """Test: Timeout is respected"""
        with pytest.raises(TimeoutError):
            provider.execute_request(
                {...},
                timeout=0.001  # Very short timeout
            )
    
    def test_cost_tracking(self, provider):
        """Test: Cost is tracked correctly"""
        response = provider.execute_request({...})
        assert response["cost"] > 0
        assert response["tokens_used"] > 0
```

---

## Provider Implementation Checklist

For each provider, implement:

### 1. Core Implementation
- [ ] Provider class inheriting from `BaseProvider`
- [ ] `execute_request()` method
- [ ] `stream_request()` method (if supported)
- [ ] Error handling and retries
- [ ] Cost tracking
- [ ] Timeout handling

### 2. Configuration
- [ ] API key loading from environment
- [ ] Model selection
- [ ] Parameter validation
- [ ] Fallback configuration

### 3. Testing
- [ ] Unit tests with mocks (>80% coverage)
- [ ] Property-based tests with Hypothesis
- [ ] Integration tests with real API (optional)
- [ ] Error scenario tests
- [ ] Performance benchmarks

### 4. Documentation
- [ ] Setup instructions
- [ ] Configuration guide
- [ ] Error codes and handling
- [ ] Cost estimation
- [ ] Rate limits

---

## Providers to Implement (Priority Order)

### Priority 1: Core Providers (Must Have)
1. **OpenAI** - Most popular, well-documented
2. **Anthropic** - Claude, good alternative
3. **Ollama** - Local, no API key needed

### Priority 2: Important Providers (Should Have)
4. **Google Gemini** - Growing adoption
5. **Groq** - Fast inference, free tier
6. **Together** - Cost-effective, free tier

### Priority 3: Extended Providers (Nice to Have)
7. **DeepSeek** - Emerging, cost-effective
8. **Mistral** - European alternative
9. **Replicate** - Model marketplace
10. **Azure OpenAI** - Enterprise
11. **HuggingFace** - Open models
12. **LM Studio** - Local GUI
13. **vLLM** - Local inference

---

## Cost Estimation

### Testing Costs (Approximate)

| Provider | Cost per Test | Tests per Phase | Total Cost |
|----------|--------------|-----------------|-----------|
| OpenAI | $0.01-0.05 | 20 | $0.20-1.00 |
| Anthropic | $0.01-0.03 | 20 | $0.20-0.60 |
| Google Gemini | $0.001-0.01 | 20 | $0.02-0.20 |
| Groq | Free | 20 | $0.00 |
| Together | Free | 20 | $0.00 |
| Local (Ollama) | Free | 20 | $0.00 |

**Total estimated cost for Phase 4 integration tests: $0.50-3.00**

---

## Execution Plan

### Week 1: Infrastructure
- [ ] Set up mock provider base class
- [ ] Set up Hypothesis strategies
- [ ] Set up test environment detection
- [ ] Create test fixtures

### Week 2: Priority 1 Providers
- [ ] Implement OpenAI provider
- [ ] Implement Anthropic provider
- [ ] Implement Ollama provider
- [ ] Write tests for each

### Week 3: Priority 2 Providers
- [ ] Implement Google Gemini provider
- [ ] Implement Groq provider
- [ ] Implement Together provider
- [ ] Write tests for each

### Week 4: Priority 3 Providers + PBT
- [ ] Implement remaining providers
- [ ] Update all Phase 1-3 tests to use PBT
- [ ] Create PBT failure database
- [ ] Documentation

---

## Success Criteria

- ✅ All providers have unit tests with >80% coverage
- ✅ All providers have property-based tests
- ✅ All providers have integration tests (optional, with flag)
- ✅ All Phase 1-3 tests updated to use real PBT
- ✅ Mock provider infrastructure complete
- ✅ Test environment detection working
- ✅ Cost tracking implemented
- ✅ Documentation complete

