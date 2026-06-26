# ADR-001: Tree Orchestration

## Context

The repository models work as an intake step, root decomposition, domain branches, leaf nodes, and synthesis. This shape appears in `intake_node.py`, `root_orchestrator.py`, `domain_orchestrator.py`, and `synthesizer.py`.

## Decision

Keep tree orchestration as the primary runtime model for now.

## Rationale

The source code and tests already revolve around run ids, branch ids, leaf ids, and domain decomposition. Keeping this model avoids an unnecessary architectural rewrite while the repository is still recovering governance and runtime integration.

## Consequences

- Future execution work should make leaf execution real instead of replacing the orchestration model.
- Branch dependency handling should remain domain-aware.
- Parallel execution can be added behind the existing branch/leaf abstractions.

## Alternatives Considered

- Flat task queue: simpler, but loses the trace structure already implemented.
- Graph runtime immediately: more flexible, but premature until the current tree runtime is complete.
