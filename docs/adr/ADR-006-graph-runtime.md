# ADR-006: Graph Runtime

## Context

The roadmap includes graph runtime evolution. Current source code implements a tree-oriented runtime, not a graph engine.

## Decision

Defer graph runtime implementation. Model it as a future phase that depends on stabilizing tree orchestration, policy enforcement, memory governance, and provider execution.

## Rationale

Graph execution adds scheduling, cycle detection, state recovery, and observability complexity. The current tree runtime still has prototype execution paths.

## Consequences

- No graph runtime claims should be made in README or status reports.
- Graph design can continue in roadmap documents.
- A graph runtime PR should include migration, compatibility, and rollback plans.

## Alternatives Considered

- Replace tree orchestration now: rejected as premature.
- Ignore graph runtime: rejected because it is a documented future need.
