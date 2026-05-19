# Phase 4: Action Plan

**Date**: 2026-04-10
**Status**: Ready for Implementation
**Duration**: 4-8 weeks (depending on scope)

---

## Decision Matrix

Before starting, answer these questions:

### Q1: Which Providers?
```
[ ] Option A: All 13 providers (complete, 8 weeks)
[ ] Option B: Priority 1+2 (8 providers, 5 weeks) ← RECOMMENDED
[ ] Option C: Priority 1 only (3 providers, 2 weeks)
```

### Q2: Testing Strategy?
```
[ ] Option A: Mocks only (fast, free, no validation)
[ ] Option B: Mocks + Real (complete, costs money)
[ ] Option C: Mocks default, Real optional (recommended) ← RECOMMENDED
```

### Q3: API Keys Available?
```
[ ] OpenAI: YES / NO
[ ] Anthropic: YES / NO
[ ] Google: YES / NO
[ ] DeepSeek: YES / NO
[ ] Mistral: YES / NO
[ ] Replicate: YES / NO
[ ] Azure OpenAI: YES / NO
[ ] Others: YES / NO
```

### Q4: Timeline?
```
[ ] Fast: 2-3 weeks (Priority 1, mocks only)
[ ] Medium: 4-5 weeks (Priority 1+2, mocks + real) ← RECOMMENDED
[ ] Complete: 6-8 weeks (All providers, mocks + real)
```

---

## Recommended Plan (Option B + C + Medium)

**Scope**: 8 providers (Priority 1+2)
**Testing**: Mocks by default, Real optional
**Duration**: 4-5 weeks
**Cost**: $1-2 in API tests

---

## Week 1: Infrastructure + Priority 1 Setup

### Day 1-2: Infrastructure
- [ ] Create `src/kabbalah/providers/__init__.py`
- [ ] Create `src/kabbalah/providers/base.py` with BaseProvider class
- [ ] Create `src/kabbalah/providers/mock_provider.py` with MockProvider class
- [ ] Create `tests/providers/__init__.py`
- [ ] Create `tests/providers/conftest.py` with test fixtures

### Day 3-4: Hypothesis Setup
- [ ] Install hypothesis: `pip install hypothesis`
- [ ] Create `tests/providers/strategies.py` with Hypothesis strategies
- [ ] Create `tests/providers/test_base_provider.py`
- [ ] Create `tests/providers/test_mock_provider.py`

### Day 5: OpenAI Provider
- [ ] Create `src/kabbalah/providers/openai_provider.py`
- [ ] Implement execute_request() method
- [ ] Implement stream_request() method
- [ ] Implement validate_request() method
- [ ] Implement calculate_cost() method
- [ ] Create `tests/providers/test_openai_provider.py`
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests

### Day 6-7: Anthropic Provider
- [ ] Create `src/kabbalah/providers/anthropic_provider.py`
- [ ] Implement all required methods
- [ ] Create `tests/providers/test_anthropic_provider.py`
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests

---

## Week 2: Priority 1 Completion + Priority 2 Start

### Day 1-2: Ollama Provider
- [ ] Create `src/kabbalah/providers/ollama_provider.py`
- [ ] Implement all required methods
- [ ] Create `tests/providers/test_ollama_provider.py`
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests

### Day 3-4: Google Gemini Provider
- [ ] Create `src/kabbalah/providers/gemini_provider.py`
- [ ] Implement all required methods
- [ ] Create `tests/providers/test_gemini_provider.py`
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests

### Day 5-7: Groq + Together Providers
- [ ] Create `src/kabbalah/providers/groq_provider.py`
- [ ] Create `src/kabbalah/providers/together_provider.py`
- [ ] Implement all required methods for both
- [ ] Create test files for both
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests

---

## Week 3: Priority 2 Completion + Integration Tests

### Day 1-3: Remaining Priority 2 Providers
- [ ] Create `src/kabbalah/providers/deepseek_provider.py`
- [ ] Create `src/kabbalah/providers/mistral_provider.py`
- [ ] Implement all required methods
- [ ] Create test files
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests

### Day 4-5: Integration Test Infrastructure
- [ ] Create `tests/integration/conftest.py`
- [ ] Create environment detection logic
- [ ] Create API key management
- [ ] Create integration test runners
- [ ] Create test reporting

### Day 6-7: Integration Tests (Optional)
- [ ] Create `tests/integration/test_openai_integration.py`
- [ ] Create `tests/integration/test_anthropic_integration.py`
- [ ] Create `tests/integration/test_ollama_integration.py`
- [ ] Run integration tests with real APIs (if keys available)

---

## Week 4: PBT Update + Documentation

### Day 1-3: Update Phase 1-3 Tests to PBT
- [ ] Update Phase 1 tests to use Hypothesis
- [ ] Update Phase 2 tests to use Hypothesis
- [ ] Update Phase 3 tests to use Hypothesis
- [ ] Create PBT failure database
- [ ] Create PBT reporting

### Day 4-5: Documentation
- [ ] Write provider setup guide
- [ ] Write provider configuration guide
- [ ] Write testing guide
- [ ] Write troubleshooting guide
- [ ] Create examples for each provider

### Day 6-7: Final Validation
- [ ] Run all unit tests
- [ ] Run all PBT tests
- [ ] Run integration tests (if applicable)
- [ ] Verify >80% coverage
- [ ] Update tasks.md to mark Phase 4 complete

---

## Week 5: Optional - Priority 3 Providers

If you want to add more providers:

### Day 1-2: Replicate Provider
- [ ] Create `src/kabbalah/providers/replicate_provider.py`
- [ ] Implement all required methods
- [ ] Create tests
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests

### Day 3-4: HuggingFace Provider
- [ ] Create `src/kabbalah/providers/huggingface_provider.py`
- [ ] Implement all required methods
- [ ] Create tests
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests

### Day 5-7: Azure OpenAI + Local Providers
- [ ] Create `src/kabbalah/providers/azure_openai_provider.py`
- [ ] Create `src/kabbalah/providers/lm_studio_provider.py`
- [ ] Create `src/kabbalah/providers/vllm_provider.py`
- [ ] Implement all required methods
- [ ] Create tests
- [ ] Write unit tests (>80% coverage)
- [ ] Write PBT tests

---

## Daily Checklist

### For Each Provider Implementation

```
Provider: _______________

Day 1: Setup
- [ ] Create provider file: src/kabbalah/providers/{name}_provider.py
- [ ] Create test file: tests/providers/test_{name}_provider.py
- [ ] Implement BaseProvider inheritance
- [ ] Implement __init__() method
- [ ] Implement validate_request() method

Day 2: Core Implementation
- [ ] Implement execute_request() method
- [ ] Implement stream_request() method
- [ ] Implement calculate_cost() method
- [ ] Implement error handling
- [ ] Implement retry logic

Day 3: Testing
- [ ] Write unit tests (happy path)
- [ ] Write unit tests (error cases)
- [ ] Write unit tests (edge cases)
- [ ] Achieve >80% coverage
- [ ] Write PBT tests with Hypothesis

Day 4: Validation
- [ ] Run unit tests locally
- [ ] Run PBT tests locally
- [ ] Run integration tests (if applicable)
- [ ] Verify cost calculation
- [ ] Verify error handling
- [ ] Update documentation
```

---

## File Structure After Completion

```
src/kabbalah/
├── providers/
│   ├── __init__.py
│   ├── base.py (BaseProvider)
│   ├── mock_provider.py (MockProvider)
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   ├── ollama_provider.py
│   ├── gemini_provider.py
│   ├── groq_provider.py
│   ├── together_provider.py
│   ├── deepseek_provider.py
│   ├── mistral_provider.py
│   ├── replicate_provider.py (optional)
│   ├── huggingface_provider.py (optional)
│   ├── azure_openai_provider.py (optional)
│   ├── lm_studio_provider.py (optional)
│   └── vllm_provider.py (optional)

tests/
├── providers/
│   ├── __init__.py
│   ├── conftest.py
│   ├── strategies.py
│   ├── test_base_provider.py
│   ├── test_mock_provider.py
│   ├── test_openai_provider.py
│   ├── test_anthropic_provider.py
│   ├── test_ollama_provider.py
│   ├── test_gemini_provider.py
│   ├── test_groq_provider.py
│   ├── test_together_provider.py
│   ├── test_deepseek_provider.py
│   ├── test_mistral_provider.py
│   ├── test_replicate_provider.py (optional)
│   ├── test_huggingface_provider.py (optional)
│   ├── test_azure_openai_provider.py (optional)
│   ├── test_lm_studio_provider.py (optional)
│   └── test_vllm_provider.py (optional)
├── integration/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_openai_integration.py
│   ├── test_anthropic_integration.py
│   ├── test_ollama_integration.py
│   └── ... (other integration tests)
```

---

## Success Criteria

- ✅ All selected providers implemented
- ✅ Each provider has >80% unit test coverage
- ✅ Each provider has property-based tests
- ✅ Mock provider infrastructure complete
- ✅ Integration test infrastructure complete
- ✅ Phase 1-3 tests updated to use PBT
- ✅ All tests passing
- ✅ Documentation complete
- ✅ Cost tracking working
- ✅ Error handling comprehensive

---

## Commands to Run

### Setup
```bash
# Install dependencies
pip install openai anthropic google-generativeai groq together huggingface-hub hypothesis pytest

# Set environment variables
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...
export GROQ_API_KEY=gsk-...
export TOGETHER_API_KEY=...
export HUGGINGFACE_API_KEY=hf_...

# For local providers
export OLLAMA_BASE_URL=http://localhost:11434
export LM_STUDIO_BASE_URL=http://localhost:1234
export VLLM_BASE_URL=http://localhost:8000
```

### Testing
```bash
# Run unit tests only (fast, no API keys)
pytest tests/providers/ -m "not integration" -v

# Run unit tests with PBT (fast, no API keys)
pytest tests/providers/ -m "not integration" -v --hypothesis-seed=0

# Run integration tests (slow, requires API keys)
KABBALAH_TEST_MODE=real pytest tests/integration/ -v

# Run specific provider tests
pytest tests/providers/test_openai_provider.py -v

# Run with coverage
pytest tests/providers/ --cov=src/kabbalah/providers --cov-report=html
```

### Validation
```bash
# Check coverage
pytest tests/providers/ --cov=src/kabbalah/providers --cov-report=term-missing

# Run all tests
pytest tests/ -v

# Run with specific seed for reproducibility
pytest tests/providers/ --hypothesis-seed=12345
```

---

## Risk Mitigation

### Risk 1: API Key Leaks
**Mitigation**: Use environment variables, never commit keys, use .env files

### Risk 2: High API Costs
**Mitigation**: Use mocks by default, real tests optional, use free tier providers

### Risk 3: Provider API Changes
**Mitigation**: Pin SDK versions, monitor provider changelogs, test regularly

### Risk 4: Test Flakiness
**Mitigation**: Use mocks for unit tests, use Hypothesis for edge cases, retry logic

### Risk 5: Incomplete Coverage
**Mitigation**: Aim for >80% coverage, use coverage reports, add missing tests

---

## Next Steps

1. **Answer the 4 decision questions above**
2. **Choose your scope (Option A, B, or C)**
3. **Gather API keys (if doing real tests)**
4. **Start Week 1 implementation**
5. **Follow the daily checklist**
6. **Run tests daily**
7. **Update tasks.md as you complete items**

---

## Questions?

If you have questions about:
- **Provider implementation**: See PROVIDERS_IMPLEMENTATION_GUIDE.md
- **Testing strategy**: See PROVIDER_TESTING_STRATEGY.md
- **Current status**: See PHASE4_STATUS.md
- **Reality check**: See PHASE4_REALITY_CHECK.md

