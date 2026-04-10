# Kabbalah Provider Configuration Guide

## Quick Start

### Option 1: Use the Same IA for Everything (Simplest)

```yaml
# config.yaml
providers:
  mode: unified
  provider: openai
  model: gpt-3.5-turbo
```

**What this means**:
- Every part of Kabbalah uses OpenAI GPT-3.5
- Intake Node? GPT-3.5
- Root Orchestrator? GPT-3.5
- Domain Coordinators? GPT-3.5
- Leaf Builders? GPT-3.5
- Leaf Verifiers? GPT-3.5
- Leaf Auditors? GPT-3.5
- Synthesizer? GPT-3.5

**Cost**: Lowest (all same model)
**Complexity**: Lowest
**Performance**: Adequate for most tasks

---

### Option 2: Define Each Role Explicitly (Most Control)

```yaml
# config.yaml
providers:
  mode: explicit
  
  roles:
    intake_clarifier:
      provider: openai
      model: gpt-3.5-turbo
      description: "Parse user requests"
    
    root_planner:
      provider: openai
      model: gpt-3.5-turbo
      description: "Decompose into domains"
    
    domain_coordinator:
      provider: openai
      model: gpt-3.5-turbo
      description: "Coordinate domain execution"
    
    leaf_builder:
      provider: openai
      model: gpt-3.5-turbo
      description: "Generate code"
    
    leaf_verifier:
      provider: anthropic
      model: claude-3-sonnet
      description: "Verify code (Claude is better)"
    
    leaf_auditor:
      provider: anthropic
      model: claude-3-sonnet
      description: "Audit code (Claude is better)"
    
    synthesizer_consolidator:
      provider: openai
      model: gpt-3.5-turbo
      description: "Consolidate results"
```

**What this means**:
- You know EXACTLY which IA is used for each part
- Intake Node → OpenAI GPT-3.5
- Root Orchestrator → OpenAI GPT-3.5
- Domain Coordinators → OpenAI GPT-3.5
- Leaf Builders → OpenAI GPT-3.5
- Leaf Verifiers → Claude (better at verification)
- Leaf Auditors → Claude (better at auditing)
- Synthesizer → OpenAI GPT-3.5

**Cost**: Medium (mix of models)
**Complexity**: Medium
**Performance**: Optimized for each role

---

### Option 3: Let System Recommend (Best Balance)

```yaml
# config.yaml
providers:
  mode: hierarchy
  # System automatically uses:
  # - Premium models (GPT-4, Claude) for Intake, Root, Synthesizer
  # - Mid-tier models (Gemini, GPT-3.5) for Domain
  # - Cost-effective models (DeepSeek, Mistral) for Leaf
```

**What this means**:
- System chooses the best provider for each role
- Intake Node → GPT-4 (best reasoning)
- Root Orchestrator → GPT-4 (complex decomposition)
- Domain Coordinators → Gemini (balanced cost/performance)
- Leaf Builders → GPT-3.5 (cost-effective)
- Leaf Verifiers → Claude (best at verification)
- Leaf Auditors → Claude (best at auditing)
- Synthesizer → GPT-4 (best reasoning)

**Cost**: Medium-High (optimized)
**Complexity**: Lowest
**Performance**: Best

---

### Option 4: Mix Default + Specific Roles (Flexible)

```yaml
# config.yaml
providers:
  mode: hybrid
  
  # Default: use GPT-3.5 for everything
  default:
    provider: openai
    model: gpt-3.5-turbo
  
  # Exceptions: use Claude for verification and auditing
  overrides:
    leaf_verifier:
      provider: anthropic
      model: claude-3-sonnet
      description: "Claude is better at verification"
    
    leaf_auditor:
      provider: anthropic
      model: claude-3-sonnet
      description: "Claude is better at auditing"
```

**What this means**:
- Most roles use OpenAI GPT-3.5 (default)
- But Leaf Verifiers and Leaf Auditors use Claude (better at those tasks)
- Everything else? GPT-3.5

**Cost**: Low-Medium
**Complexity**: Low
**Performance**: Good

---

## Understanding Each Role

### Intake_Clarifier
**What it does**: Reads your project request and creates a detailed specification
**Happens**: Once per project
**Recommendation**: Use a smart model (GPT-4, Claude)

### Root_Planner
**What it does**: Breaks down the specification into domains (backend, frontend, etc.)
**Happens**: Once per project
**Recommendation**: Use a smart model (GPT-4, Claude)

### Domain_Coordinator
**What it does**: Manages execution within each domain
**Happens**: 3-5 times per project
**Recommendation**: Use a balanced model (Gemini, GPT-3.5)

### Leaf_Builder
**What it does**: Generates code and artifacts
**Happens**: Many times per project
**Recommendation**: Use a cost-effective model (GPT-3.5, DeepSeek, Mistral)

### Leaf_Verifier
**What it does**: Checks if generated code is correct
**Happens**: Many times per project
**Recommendation**: Use a careful model (Claude, Groq)

### Leaf_Auditor
**What it does**: Ensures code meets compliance and security standards
**Happens**: Many times per project
**Recommendation**: Use a careful model (Claude, GPT-4)

### Synthesizer_Consolidator
**What it does**: Combines results from all domains into final delivery
**Happens**: Once per project
**Recommendation**: Use a smart model (GPT-4, Claude)

---

## Fallback Chains

If your primary provider fails, the system automatically tries the next one.

### Example: Explicit Mode with Fallbacks

```yaml
providers:
  mode: explicit
  
  roles:
    leaf_builder:
      provider: openai
      model: gpt-3.5-turbo
      fallback:
        - deepseek:deepseek-chat
        - mistral:mistral-medium
        - ollama:neural-chat
      description: "Generate code"
```

**What happens if OpenAI fails**:
1. Try OpenAI GPT-3.5 → FAILS
2. Try DeepSeek → FAILS
3. Try Mistral → SUCCESS ✓

**Cost**: You only pay for successful calls

---

## Environment Variables

You can also configure via environment variables:

```bash
# Unified mode
export KABBALAH_PROVIDER_MODE=unified
export KABBALAH_PROVIDER=openai
export KABBALAH_MODEL=gpt-3.5-turbo

# Explicit mode
export KABBALAH_PROVIDER_MODE=explicit
export KABBALAH_INTAKE_PROVIDER=openai
export KABBALAH_INTAKE_MODEL=gpt-3.5-turbo
export KABBALAH_ROOT_PROVIDER=openai
export KABBALAH_ROOT_MODEL=gpt-3.5-turbo
export KABBALAH_DOMAIN_PROVIDER=google
export KABBALAH_DOMAIN_MODEL=gemini-pro
export KABBALAH_LEAF_BUILDER_PROVIDER=openai
export KABBALAH_LEAF_BUILDER_MODEL=gpt-3.5-turbo
export KABBALAH_LEAF_VERIFIER_PROVIDER=anthropic
export KABBALAH_LEAF_VERIFIER_MODEL=claude-3-sonnet
export KABBALAH_LEAF_AUDITOR_PROVIDER=anthropic
export KABBALAH_LEAF_AUDITOR_MODEL=claude-3-sonnet
export KABBALAH_SYNTHESIZER_PROVIDER=openai
export KABBALAH_SYNTHESIZER_MODEL=gpt-3.5-turbo
```

---

## Checking Your Configuration

After starting Kabbalah, you can check which providers are configured:

```bash
# Show current configuration
kabbalah config show

# Output:
# Provider Configuration (Mode: explicit)
# ─────────────────────────────────────────
# Intake_Clarifier:        openai (gpt-3.5-turbo)
# Root_Planner:            openai (gpt-3.5-turbo)
# Domain_Coordinator:      google (gemini-pro)
# Leaf_Builder:            openai (gpt-3.5-turbo)
# Leaf_Verifier:           anthropic (claude-3-sonnet)
# Leaf_Auditor:            anthropic (claude-3-sonnet)
# Synthesizer:             openai (gpt-3.5-turbo)
```

---

## Monitoring Provider Usage

During execution, you can see which providers are being used:

```bash
# Show provider usage in real-time
kabbalah monitor providers

# Output:
# [Intake_Clarifier] Using openai (gpt-3.5-turbo)
# [Root_Planner] Using openai (gpt-3.5-turbo)
# [Domain_Coordinator] Using google (gemini-pro)
# [Leaf_Builder] Using openai (gpt-3.5-turbo)
# [Leaf_Verifier] Using anthropic (claude-3-sonnet)
# [Leaf_Auditor] Using anthropic (claude-3-sonnet)
# [Synthesizer] Using openai (gpt-3.5-turbo)
```

---

## Cost Estimation

### Scenario 1: Unified Mode (All GPT-3.5)
```
1 Intake + 1 Root + 3 Domain + 5 Builder + 5 Verifier + 5 Auditor + 1 Synthesizer
= ~$0.50 total
```

### Scenario 2: Explicit Mode (Mixed)
```
Intake (GPT-3.5) + Root (GPT-3.5) + Domain (Gemini) + Builder (GPT-3.5) 
+ Verifier (Claude) + Auditor (Claude) + Synthesizer (GPT-3.5)
= ~$2.00 total
```

### Scenario 3: Hierarchy Mode (Optimized)
```
Intake (GPT-4) + Root (GPT-4) + Domain (Gemini) + Builder (GPT-3.5) 
+ Verifier (Claude) + Auditor (Claude) + Synthesizer (GPT-4)
= ~$3.50 total
```

---

## Troubleshooting

### "Provider not found"
**Problem**: Configuration references a provider that's not available
**Solution**: Check provider name spelling, ensure API key is set

### "All providers failed"
**Problem**: Primary provider and all fallbacks failed
**Solution**: Check API keys, network connectivity, provider status

### "Unexpected provider used"
**Problem**: System used a different provider than expected
**Solution**: Run `kabbalah config show` to verify configuration

---

## Best Practices

1. **Start Simple**: Use Unified mode first, then optimize
2. **Monitor Costs**: Track which providers are used and their costs
3. **Test Fallbacks**: Ensure fallback chains work before production
4. **Document Choices**: Add descriptions to explain why each provider is chosen
5. **Review Regularly**: Check if provider choices still make sense

---

## Document Version

- **Version**: 1.0
- **Date**: 2026-04-09
- **Status**: Ready for Use
- **Related**: docs/specs/PROVIDER_HIERARCHY.md
