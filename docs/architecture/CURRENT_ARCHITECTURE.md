# Current Architecture

Kabbalah currently implements a tree-shaped orchestration skeleton with supporting modules for provider abstraction, memory, governance, observability, and tool execution.

```text
UserRequest
  -> IntakeNode
  -> RootOrchestrator
  -> DomainOrchestrator
  -> LeafNode
  -> Synthesizer
  -> DeliveryPackage
```

## Runtime Flow

1. `IntakeNode` validates the user request and creates a `Specification`.
2. `RootOrchestrator` decomposes the specification into `DomainBranch` objects.
3. `DomainOrchestrator` converts branch tasks into `LeafNode` objects.
4. Leaf execution currently returns empty successful artifacts and does not call a real provider/tool loop.
5. `Synthesizer` merges artifacts and performs consistency checks.

## Supporting Modules

- Runtime hardening: `fsm_enforcement.py`, `contract_enforcement.py`, `role_trace_validation.py`, `transition_validation.py`, `day2_operations.py`.
- Memory: `memory_subsystem.py`, `memory_governance.py`.
- Providers: `providers/base.py`, `providers/factory.py`, and provider adapters.
- Tools: `tools/execution_engine.py`.
- Observability: `observability/observability_module.py`, `trace_id_tracking.py`.

## Known Architecture Gap

The architecture is not yet a fully integrated runtime. Many modules are implemented and tested independently, but orchestration does not yet enforce every policy gate or execute real leaf work through providers and tools.
