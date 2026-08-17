# Kabbalah Research

Kabbalah is designed to benefit from advances in AI research without allowing the architecture to become a permanent collection of unrelated frameworks and papers.

This document describes the public research direction, not the private implementation roadmap.

## Research philosophy

A new technique is valuable to Kabbalah when it can do at least one of the following:

- improve an existing capability;
- replace a weaker mechanism;
- simplify the architecture;
- reduce resource cost;
- improve robustness;
- improve learning quality;
- reduce dependence on a specific model or provider;
- increase autonomy without weakening user control.

Interesting research is not automatically architecture.

External projects should primarily be treated as sources of mechanisms, evidence, and design lessons. Kabbalah should absorb what works without becoming structurally dependent on the identity of every project it studies.

## Active research areas

### Agentic reasoning and adaptive cognition

How an autonomous runtime can select or combine reasoning strategies according to task difficulty, uncertainty, available resources, and risk.

### Context and memory

Long-term memory, recurrent state, memory consolidation, forgetting, provenance, contradiction, retrieval, and methods for avoiding unbounded context growth.

### Self-learning

Learning from runtime experience without assuming that model-weight updates are required. This includes memory revision, strategy improvement, skill acquisition, correction, and evidence-based belief updates.

### Controlled evolution

Self-improvement mechanisms that can propose and evaluate changes while remaining below stable authority boundaries and promotion criteria.

### Human-agent collaboration

Human guidance as a source of intent, correction, preference, and direction rather than as a substitute for technical containment.

### Robustness and hardness

Methods for measuring how difficult it is to cause an autonomous system to violate its mandate, contaminate its learning, expand authority, misuse resources, or lose containment while preserving useful capability.

### Secure autonomous execution

Controlled tool use, least privilege, sandboxing, capability boundaries, provenance, and defenses against malicious or contaminated inputs.

### Federated intelligence

Ways for independent installations to share useful evidence, knowledge, strategies, or validated results without surrendering local control or exposing unnecessary private data.

### Efficient inference and resource governance

Model routing, cascades, local/remote hybrids, adaptive compute, context efficiency, hardware-aware scheduling, and methods for maximizing useful intelligence per unit of resource.

### Evaluation and verification

Continuous evaluation, verifiers, adaptive benchmarks, adversarial testing, regression detection, and methods for distinguishing real capability from optimistic implementation claims.

### Parametric learning

SFT, adapters, preference optimization, reinforcement learning, distillation, and distributed training remain research directions for a future training capability. They are not required for Kabbalah to learn at runtime.

## Adoption rule

Research should move toward implementation only when there is a concrete reason to believe it improves Kabbalah as a system.

A preferred adoption sequence is:

1. identify the capability or problem affected;
2. compare the research result with the current mechanism;
3. prototype or simulate the change where practical;
4. measure capability, cost, and robustness;
5. adopt, adapt, reject, or keep the idea as research;
6. avoid retaining obsolete parallel mechanisms without a reason.

## Research classifications

Kabbalah uses four simple outcomes when evaluating external work:

- **Adopt** — use the mechanism substantially as-is because it clearly improves the system.
- **Adapt** — absorb the useful idea while keeping Kabbalah's own architecture and authority model.
- **Research** — preserve the idea for later because prerequisites, evidence, or timing are not sufficient.
- **Reject** — the technique does not improve the project enough to justify its complexity or tradeoffs.

## Public vs. private research

The public project documents themes, principles, and selected conclusions.

Detailed threat models, internal architecture, implementation experiments, adversarial methods, tuning information, unpublished benchmarks, and development roadmaps are maintained privately.
