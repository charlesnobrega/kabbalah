# ADR-003: Memory Strategy

## Context

The codebase includes a semantic memory interface, a Cognee backend stub, a JSONL backend, and a memory governance module. JSONL works locally; Cognee semantic behavior is not implemented.

## Decision

Use JSONL as the reliable baseline memory backend and treat Cognee as an experimental semantic backend until its store/query paths are implemented and tested.

## Rationale

The JSONL backend has concrete file behavior and tests. Cognee availability detection exists, but semantic retrieval is not a working runtime capability.

## Consequences

- Memory docs must distinguish lexical JSONL search from semantic retrieval.
- Cognee work should be tracked as implementation, not documentation cleanup.
- Governance policies should apply uniformly to both backends.

## Alternatives Considered

- Make Cognee mandatory: rejected because current behavior falls back and Cognee methods are placeholders.
- Remove Cognee: rejected because it is a documented direction and can remain experimental.
