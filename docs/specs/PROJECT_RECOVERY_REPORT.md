# Project Recovery Report

Date: 2026-05-31

## What Exists

- Python package under `src/kabbalah`.
- Tree orchestration skeleton: intake, root, domain, leaf, synthesis.
- Runtime hardening modules for FSM, contracts, roles/traces, transitions, and Day 2 operations.
- Memory subsystem with JSONL backend and Cognee placeholder.
- Provider abstraction with six real provider adapters and a gated fake provider.
- Tool execution engine for local commands, files, grep, web, and placeholder MCP.
- In-memory observability module.
- Broad test suite including unit, integration, and property-based tests.
- Large historical documentation set.

## What Works

- Isolated module tests cover many core data structures and validation paths.
- JSONL memory storage works as a local fallback.
- Provider factory can instantiate implemented adapters.
- Mock provider is blocked unless explicit test mode is enabled.
- Tool engine can execute basic operations under configured allow-lists.
- Trace/log/metric collection works in-process.

## What Is Incomplete

- Leaf execution does not perform real provider/tool work.
- Cognee semantic retrieval is not implemented.
- MCP tool execution is not implemented.
- Enforcement modules are not consistently integrated into orchestrator execution.
- Observability does not export to OpenTelemetry/Prometheus despite dependencies.
- README and historical docs overstate provider and runtime completeness.
- Skill registry, central policy engine, and graph runtime are not implemented.

## What Should Be Prioritized

1. Make documentation status truthful and canonical.
2. Wire policy checks into orchestration and tool execution.
3. Replace leaf execution placeholder with a real, policy-gated execution path.
4. Implement provider factory usage in orchestration.
5. Stabilize memory semantics and governance integration.
6. Add external telemetry export only after runtime behavior is real.

## Suggested Next 30 Days

- Consolidate documentation around current status.
- Open issues for each prototype/missing subsystem.
- Add tests that prove leaf execution cannot silently simulate success.
- Add provider factory integration design.
- Define policy engine interface over existing enforcement modules.

## Suggested Next 90 Days

- Implement policy-gated leaf execution.
- Add real provider execution with budget tracking.
- Implement Cognee store/query or downgrade semantic claims.
- Add command/domain allow-list profiles for tool execution.
- Introduce external telemetry exporter behind configuration.

## Suggested Next 6 Months

- Build the skill registry as disabled-by-default governance infrastructure.
- Add agent/provider reputation based on observed runtime outcomes.
- Implement advisory meta evaluator.
- Prototype graph runtime only after tree execution is stable and recoverable.
