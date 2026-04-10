# Provider Hierarchy Recommendations

## Overview

Kabbalah uses a hierarchical provider assignment strategy to optimize cost, latency, and capability across the orchestration tree.

## Hierarchy Levels and Recommended Providers

### Level 1: Intake Node (Intake_Clarifier)
**Purpose**: Parse and refine user requests into premium specifications
**Frequency**: Once per project
**Recommended Providers** (in fallback order):
1. **OpenAI (GPT-4)** - Best reasoning for spec refinement
2. **Anthropic (Claude)** - Excellent reasoning and context understanding
3. **Google Gemini** - Strong reasoning capability
4. **Groq** - Fast inference as backup

**Rationale**: Happens only once per project, so premium models are cost-effective. High reasoning capability ensures quality specifications.

---

### Level 2: Root Orchestrator (Root_Planner)
**Purpose**: Decompose specifications into domain branches
**Frequency**: Once per project
**Recommended Providers** (in fallback order):
1. **OpenAI (GPT-4)** - Complex decomposition logic
2. **Anthropic (Claude)** - Strong structural reasoning
3. **Google Gemini** - Good decomposition capability

**Rationale**: Complex decomposition requires strong reasoning. Happens once, so premium models are justified.

---

### Level 3: Domain Orchestrator (Domain_Coordinator)
**Purpose**: Coordinate execution within a domain
**Frequency**: Once per domain (typically 3-5 times per project)
**Recommended Providers** (in fallback order):
1. **Google Gemini** - Good balance of cost and capability
2. **OpenAI (GPT-3.5)** - Cost-effective with good reasoning
3. **DeepSeek** - Competitive pricing and capability
4. **Mistral** - Open-source alternative

**Rationale**: Mid-tier models balance cost and capability. Happens multiple times, so cost optimization matters.

---

### Level 4a: Leaf Node - Builder (Leaf_Builder)
**Purpose**: Generate code and artifacts
**Frequency**: Many times per project (per task)
**Recommended Providers** (in fallback order):
1. **OpenAI (GPT-3.5)** - Reliable code generation
2. **DeepSeek** - Good code generation at lower cost
3. **Mistral** - Strong code generation capability
4. **Ollama (local)** - Free local inference

**Rationale**: Code generation is the most frequent operation. Cost-effective models are essential. Local fallback available.

---

### Level 4b: Leaf Node - Verifier (Leaf_Verifier)
**Purpose**: Verify and validate generated artifacts
**Frequency**: Many times per project (per task)
**Recommended Providers** (in fallback order):
1. **Anthropic (Claude)** - Excellent for careful analysis
2. **Groq** - Fast inference for verification
3. **OpenAI (GPT-4)** - Premium verification when needed

**Rationale**: Verification requires careful analysis. Claude excels at this. Groq provides fast fallback.

---

### Level 4c: Leaf Node - Auditor (Leaf_Auditor)
**Purpose**: Audit and ensure compliance
**Frequency**: Many times per project (per task)
**Recommended Providers** (in fallback order):
1. **Anthropic (Claude)** - Best for compliance and security analysis
2. **OpenAI (GPT-4)** - Strong reasoning for auditing
3. **Groq** - Fast inference as backup

**Rationale**: Auditing requires high accuracy and careful reasoning. Premium models justified for compliance.

---

### Level 5: Synthesizer (Synthesizer_Consolidator)
**Purpose**: Consolidate results from all branches
**Frequency**: Once per project
**Recommended Providers** (in fallback order):
1. **OpenAI (GPT-4)** - Complex consolidation logic
2. **Anthropic (Claude)** - Strong reasoning for merging
3. **Google Gemini** - Good consolidation capability

**Rationale**: Final consolidation is critical. Premium models ensure quality. Happens once, so cost is minimal.

---

## Cost Optimization Strategy

### Total Cost Breakdown (Example Project)

Assuming a project with:
- 1 Intake operation
- 1 Root decomposition
- 3 Domain coordinators
- 15 Leaf operations (5 builders, 5 verifiers, 5 auditors)
- 1 Synthesizer

**Cost-Optimized Configuration**:
```
Intake:           1x GPT-4      = ~$0.30
Root:             1x GPT-4      = ~$0.30
Domain (3x):      3x Gemini     = ~$0.15
Leaf Builders:    5x GPT-3.5    = ~$0.50
Leaf Verifiers:   5x Claude     = ~$1.00
Leaf Auditors:    5x Claude     = ~$1.00
Synthesizer:      1x GPT-4      = ~$0.30
─────────────────────────────────
Total:                           ~$3.55
```

**Premium Configuration** (all GPT-4):
```
Total:                           ~$15.00
```

**Savings**: ~76% cost reduction with hierarchy-based optimization

---

## Configuration Modes

### Mode 1: Unified Provider (Same IA for Everything)

Use a mesma IA em todas as partes do sistema. Simples e econômico.

```yaml
providers:
  mode: unified
  provider: openai
  model: gpt-3.5-turbo
  # Usa GPT-3.5 em TUDO: Intake, Root, Domain, Leaf, Synthesizer
```

**Quando usar**: 
- Orçamento limitado
- Prototipagem rápida
- Testes iniciais

---

### Mode 2: Explicit Per-Role (Você define cada papel)

Define explicitamente qual IA para cada papel. Você sabe exatamente o que está usando.

```yaml
providers:
  mode: explicit
  
  roles:
    # INTAKE NODE
    intake_clarifier:
      provider: openai
      model: gpt-3.5-turbo
      description: "Parse user requests"
    
    # ROOT ORCHESTRATOR
    root_planner:
      provider: openai
      model: gpt-3.5-turbo
      description: "Decompose into domains"
    
    # DOMAIN ORCHESTRATOR
    domain_coordinator:
      provider: openai
      model: gpt-3.5-turbo
      description: "Coordinate domain execution"
    
    # LEAF NODES
    leaf_builder:
      provider: openai
      model: gpt-3.5-turbo
      description: "Generate code and artifacts"
    
    leaf_verifier:
      provider: openai
      model: gpt-3.5-turbo
      description: "Verify generated artifacts"
    
    leaf_auditor:
      provider: openai
      model: gpt-3.5-turbo
      description: "Audit and ensure compliance"
    
    # SYNTHESIZER
    synthesizer_consolidator:
      provider: openai
      model: gpt-3.5-turbo
      description: "Consolidate results"
```

**Quando usar**:
- Você quer controle total
- Diferentes IAs para diferentes tarefas
- Otimização de custo/performance

---

### Mode 3: Hierarchy-Based (Recomendações Automáticas)

Sistema usa as recomendações de hierarquia. Se uma IA não estiver disponível, tenta a próxima.

```yaml
providers:
  mode: hierarchy
  
  # Sistema usa automaticamente:
  # - Premium (GPT-4, Claude) para Intake, Root, Synthesizer
  # - Mid-tier (Gemini, GPT-3.5) para Domain
  # - Cost-effective (DeepSeek, Mistral) para Leaf
```

**Quando usar**:
- Você quer o melhor balance custo/performance
- Deixar o sistema decidir
- Máxima flexibilidade

---

### Mode 4: Hybrid (Mistura de Modos)

Combine modos: use a mesma IA para algumas partes, e IAs diferentes para outras.

```yaml
providers:
  mode: hybrid
  
  # Padrão: use GPT-3.5 em tudo
  default:
    provider: openai
    model: gpt-3.5-turbo
  
  # Exceções: use IAs diferentes para papéis específicos
  overrides:
    leaf_verifier:
      provider: anthropic
      model: claude-3-sonnet
      description: "Use Claude for verification (better at analysis)"
    
    leaf_auditor:
      provider: anthropic
      model: claude-3-sonnet
      description: "Use Claude for auditing (better at compliance)"
```

**Quando usar**:
- Você quer usar uma IA principal, mas IAs especializadas para tarefas críticas
- Balance entre simplicidade e otimização

---

## Configuration Example

### YAML Configuration - Explicit Mode

```yaml
providers:
  mode: explicit
  
  roles:
    intake_clarifier:
      provider: openai
      model: gpt-3.5-turbo
      fallback:
        - anthropic:claude-3-sonnet
        - google:gemini-pro
      description: "Parse user requests into specifications"
    
    root_planner:
      provider: openai
      model: gpt-3.5-turbo
      fallback:
        - anthropic:claude-3-sonnet
        - google:gemini-pro
      description: "Decompose specifications into domains"
    
    domain_coordinator:
      provider: openai
      model: gpt-3.5-turbo
      fallback:
        - google:gemini-pro
        - deepseek:deepseek-chat
      description: "Coordinate domain execution"
    
    leaf_builder:
      provider: openai
      model: gpt-3.5-turbo
      fallback:
        - deepseek:deepseek-chat
        - mistral:mistral-medium
      description: "Generate code and artifacts"
    
    leaf_verifier:
      provider: openai
      model: gpt-3.5-turbo
      fallback:
        - anthropic:claude-3-sonnet
        - groq:mixtral-8x7b
      description: "Verify generated artifacts"
    
    leaf_auditor:
      provider: openai
      model: gpt-3.5-turbo
      fallback:
        - anthropic:claude-3-sonnet
        - groq:mixtral-8x7b
      description: "Audit and ensure compliance"
    
    synthesizer_consolidator:
      provider: openai
      model: gpt-3.5-turbo
      fallback:
        - anthropic:claude-3-sonnet
        - google:gemini-pro
      description: "Consolidate results from all branches"
```

### YAML Configuration - Unified Mode

```yaml
providers:
  mode: unified
  provider: openai
  model: gpt-3.5-turbo
  
  # Fallback chain if primary provider fails
  fallback:
    - anthropic:claude-3-sonnet
    - google:gemini-pro
    - deepseek:deepseek-chat
```

### YAML Configuration - Hybrid Mode

```yaml
providers:
  mode: hybrid
  
  # Default for all roles
  default:
    provider: openai
    model: gpt-3.5-turbo
    fallback:
      - anthropic:claude-3-sonnet
      - google:gemini-pro
  
  # Overrides for specific roles
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

### Environment Variables

```bash
# Intake Node
KABBALAH_INTAKE_PROVIDER=openai
KABBALAH_INTAKE_MODEL=gpt-4
KABBALAH_INTAKE_FALLBACK=anthropic,google,groq

# Root Orchestrator
KABBALAH_ROOT_PROVIDER=openai
KABBALAH_ROOT_MODEL=gpt-4
KABBALAH_ROOT_FALLBACK=anthropic,google

# Domain Orchestrator
KABBALAH_DOMAIN_PROVIDER=google
KABBALAH_DOMAIN_MODEL=gemini-pro
KABBALAH_DOMAIN_FALLBACK=openai,deepseek,mistral

# Leaf Builders
KABBALAH_LEAF_BUILDER_PROVIDER=openai
KABBALAH_LEAF_BUILDER_MODEL=gpt-3.5-turbo
KABBALAH_LEAF_BUILDER_FALLBACK=deepseek,mistral,ollama

# Leaf Verifiers
KABBALAH_LEAF_VERIFIER_PROVIDER=anthropic
KABBALAH_LEAF_VERIFIER_MODEL=claude-3-sonnet
KABBALAH_LEAF_VERIFIER_FALLBACK=groq,openai

# Leaf Auditors
KABBALAH_LEAF_AUDITOR_PROVIDER=anthropic
KABBALAH_LEAF_AUDITOR_MODEL=claude-3-opus
KABBALAH_LEAF_AUDITOR_FALLBACK=openai,groq

# Synthesizer
KABBALAH_SYNTHESIZER_PROVIDER=openai
KABBALAH_SYNTHESIZER_MODEL=gpt-4
KABBALAH_SYNTHESIZER_FALLBACK=anthropic,google
```

---

## Provider Characteristics

### Premium Models (Intake, Root, Synthesizer, Auditor)
- **OpenAI GPT-4**: Best reasoning, highest cost (~$0.03/1K tokens)
- **Anthropic Claude**: Excellent reasoning, good cost (~$0.015/1K tokens)
- **Google Gemini**: Strong reasoning, competitive cost (~$0.0005/1K tokens)

### Mid-Tier Models (Domain Coordinator)
- **Google Gemini**: Balanced cost/capability
- **OpenAI GPT-3.5**: Reliable, cost-effective (~$0.0005/1K tokens)
- **DeepSeek**: Competitive pricing, good capability
- **Mistral**: Open-source, good performance

### Cost-Effective Models (Leaf Builders)
- **OpenAI GPT-3.5**: Reliable code generation
- **DeepSeek**: Lower cost, good code generation
- **Mistral**: Open-source alternative
- **Ollama**: Free local inference

---

## Fallback Chain Behavior

When a provider fails:
1. Log the failure with trace_id
2. Move to next provider in fallback chain
3. Retry the operation with new provider
4. If all providers fail, escalate error with full context

**Example Fallback Sequence**:
```
Leaf_Builder attempts:
  1. OpenAI GPT-3.5 → TIMEOUT
  2. DeepSeek → RATE_LIMITED
  3. Mistral → SUCCESS ✓
  
Result: Operation succeeds with Mistral
Cost: Minimal (only successful call charged)
```

---

## Monitoring and Optimization

### Metrics to Track
- Provider success rate per hierarchy level
- Average latency per provider
- Cost per operation
- Fallback frequency

### Optimization Triggers
- If provider success rate < 95% → move to next in fallback chain
- If average latency > 30s → consider faster provider
- If cost > budget → use cheaper provider in fallback chain

---

## Migration Path

### Phase 1: Premium Configuration
Start with all premium models to ensure quality.

### Phase 2: Hierarchy-Based Optimization
Implement hierarchy recommendations to reduce cost.

### Phase 3: Dynamic Optimization
Monitor metrics and adjust providers based on performance.

### Phase 4: Custom Optimization
Fine-tune per-domain provider selection based on workload characteristics.

---

## Document Version

- **Version**: 1.0
- **Date**: 2026-04-09
- **Status**: Ready for Implementation
- **Related**: docs/specs/design.md, docs/specs/requirements.md
