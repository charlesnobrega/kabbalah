# ADR-005: Policy Engine

## Context

The repository contains separate enforcement modules for FSM state, role permissions, memory governance, contracts, and Day 2 operations. There is no single central policy engine.

## Decision

Treat current enforcement modules as policy primitives and design a central policy engine as a future integration layer.

## Rationale

The primitives are tested and useful. The missing work is consistent orchestration integration and centralized decision logging, not replacement.

## Consequences

- New runtime actions should call policy primitives before execution.
- A future policy engine should compose existing modules.
- Documentation must not claim a central policy engine exists today.

## Alternatives Considered

- Keep policies permanently scattered: rejected because it increases bypass risk.
- Rewrite all enforcement now: rejected because it would be high-risk and unnecessary.
