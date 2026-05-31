# Memory Analysis

## Current Memory Architecture

The current memory system is implemented in `src/kabbalah/memory_subsystem.py` and governed by `src/kabbalah/memory_governance.py`.

## Cognee Usage

`CogneeBackend` attempts to import `cognee` and marks itself available if import succeeds. Current `store`, `query`, and `ensure_consistency` methods are placeholders. They do not perform real semantic indexing or retrieval.

Status: prototype.

## JSONL Fallback

`JSONLBackend` stores `Knowledge` records in `knowledge.jsonl`, protected by a reentrant lock. Query behavior is substring matching against content and category. Store behavior rewrites the full knowledge file.

Status: implemented baseline.

## Semantic Retrieval

True semantic retrieval is not implemented. Current retrieval is either empty Cognee placeholder behavior or lexical JSONL matching.

Status: missing.

## Memory Governance

`MemoryGovernanceModule` defines memory categories, operations, access policies, and audit logs. This is a useful primitive, but orchestration does not yet enforce it around all memory reads/writes.

Status: implemented but not fully integrated.

## Proposed Memory Types

### Working Memory

Short-lived per-run context used while a branch or leaf is executing.

- Scope: one run or trace.
- Storage: in-memory plus optional JSONL checkpoint.
- Retention: short.
- Governance: role-scoped.

### Episodic Memory

Historical execution episodes, including decisions, failures, fixes, and review outcomes.

- Scope: project and run history.
- Storage: append-only JSONL or durable database.
- Retention: medium/long.
- Governance: audit-first, redaction required.

### Long-Term Memory

Stable project knowledge such as architecture constraints, accepted policies, and recurring decisions.

- Scope: repository/project.
- Storage: durable indexed backend.
- Retention: long.
- Governance: owner-approved writes.

### Knowledge Memory

Searchable facts, snippets, patterns, and references used for retrieval.

- Scope: domain-specific and shared knowledge.
- Storage: semantic backend when available, JSONL baseline otherwise.
- Retention: governed by relevance and source.
- Governance: source attribution required.

## Recommendations

1. Keep JSONL as the baseline durable backend.
2. Implement Cognee store/query before advertising semantic retrieval.
3. Add memory governance checks inside `MemorySubsystem.store_knowledge()` and `query_knowledge()`.
4. Add explicit memory type to `Knowledge.metadata` or a future schema.
5. Add migration and retention policies before long-term memory is enabled by default.
