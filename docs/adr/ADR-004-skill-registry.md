# ADR-004: Skill Registry

## Context

The project discusses specialized skills and cybersecurity skill compatibility, but no runtime skill registry exists in source code.

## Decision

Do not integrate external skills directly into execution. Define a future registry as a governed metadata layer before any runtime skill invocation.

## Rationale

External skills can expand tool access and security risk. A registry needs policy metadata, approval state, sandbox constraints, and audit hooks before execution.

## Consequences

- Skill registry is documentation/design only today.
- Any future implementation must be policy-first.
- Cybersecurity skills require additional restrictions before use.

## Alternatives Considered

- Directly import external skill repositories: rejected due to supply-chain and execution risk.
- Ignore skills entirely: rejected because the roadmap explicitly includes them.
