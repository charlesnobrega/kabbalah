# Kabbalah Architecture

Kabbalah is an alpha-stage zero-trust orchestration runtime for AI agents. Its
current value is the security kernel around tool and agent execution: every
externally visible action must pass through intent scoring, authorization,
contract checks, optional human approval, and audit-friendly persistence.

This is the single architecture overview for the repository. Execution status and
future waves live in `docs/roadmap/handoff-execution-plan.md`; dated decisions
live in `docs/adr/`.

## Runtime flow

```text
UserRequest / MCP client / CLI
  -> Security kernel
     -> Qlipot risk scoring
     -> FirewallMCP authorization
     -> agent contracts
     -> HITL when required
  -> IntakeNode
  -> RootOrchestrator
  -> DomainOrchestrator
  -> LeafNode
  -> LLMGateway / CapabilityRegistry
  -> ProviderFactory
  -> BudgetManager / BudgetLedger when injected
  -> Synthesizer
  -> DeliveryPackage
```

The historical tree-shaped flow is implemented and tested. Leaf execution now
performs real provider work when `DomainOrchestrator` is constructed with an
`LLMGateway`; without an injected gateway it returns explicit
`status="skipped"` rather than fake success. Root-level orchestration still
constructs `DomainOrchestrator` without a gateway by default.

## Layers

```text
                    +--------------------------------------+
Input               | SillyTavern / CLI / MCP clients      |
                    +------------------+-------------------+
                                       |
                                       v
                    +--------------------------------------+
Security kernel     | kabbalah_mcp_bridge.py (stdio MCP)   |
                    | 1. Qlipot risk scoring               |
                    | 2. FirewallMCP authorization         |
                    | 3. Contract verification             |
                    | 4. HITL approval when required       |
                    +------------------+-------------------+
                                       |
                                       v
                    +--------------------------------------+
Orchestration       | Intake -> Root -> Domain -> Leaf      |
                    | Synthesizer -> DeliveryPackage        |
                    +------------------+-------------------+
                                       |
                                       v
                    +--------------------------------------+
LLM layer           | LLMGateway -> CapabilityRegistry      |
                    | ProviderFactory -> provider adapters  |
                    | BudgetManager gates provider return   |
                    | Mock only gated; HardwareProfiler fit |
                    +------------------+-------------------+
                                       |
                                       v
                    +--------------------------------------+
Persistence/audit   | SQLite state DB and append-only logs  |
                    +--------------------------------------+
```

## Components and responsibilities

| Component | Responsibility |
|---|---|
| `kabbalah_mcp_bridge.py` | stdio MCP bridge for SillyTavern and other MCP clients. It exposes tools and enforces the security pipeline before execution. |
| `src/kabbalah/qlipot.py` | Intent/risk scoring, including temporal context and hardening against common encoding and unicode evasions. |
| `src/kabbalah/firewall_mcp.py` | MCP action authorization, RBAC integration, and HITL decision signaling. |
| `src/kabbalah/contratos.py` and `src/kabbalah/contrato_store.py` | Agent contract verification, persisted counters, and append-only violation/event logging. |
| `src/kabbalah/hitl.py` | Human-in-the-loop request model and approval states. Pending approval is not treated as approval. |
| `src/kabbalah/cofre.py` | Bitwarden-backed secret access with cache and operational safeguards. |
| `src/kabbalah/tools/execution_engine.py` | Tool execution boundary for filesystem, command, and network-style actions. |
| `src/kabbalah/intake_node.py` | User request validation and conversion to a canonical specification. |
| `src/kabbalah/root_orchestrator.py` | Decomposes specifications into domain branches. |
| `src/kabbalah/domain_orchestrator.py` | Converts domain branch work into leaf nodes. With an injected `LLMGateway`, leaf execution tries ordered provider candidates, returns an `llm_response` artifact, and can record ledger usage. |
| `src/kabbalah/llm_gateway.py` | Canonical provider selector by role, capability, and budget hint. It delegates provider construction to `ProviderFactory`, checks `BudgetManager` when configured, and returns ordered candidates for fallback-capable callers. |
| `src/kabbalah/providers/` | Provider abstraction and adapters for native and OpenAI-compatible external/local LLM providers. Runtime mock use is gated. |
| `src/kabbalah/budget_manager.py` | Append-only `BudgetLedger` plus `BudgetManager` for run/day/provider limits in `warn` or `block` mode. |
| `src/kabbalah/hardware_profile.py` | Local hardware fingerprinting, GPU/CPU/RAM detection, static model fit classification, and measured-token tier classification for local profiles. |
| `src/kabbalah/memory_subsystem.py` and `src/kabbalah/memory_governance.py` | Memory storage, fallback behavior, and memory access governance. |
| `src/kabbalah/observability/` and `src/kabbalah/trace_id_tracking.py` | Logs, trace IDs, and operational observability. |

## Canonical decisions

1. `LLMGateway` is the top-level selector; `ProviderFactory` constructs providers.
   Runtime consumers should not select providers directly through the factory.
2. The security kernel is fail-closed. Verification exceptions, missing
   authorization, or missing approval deny execution.
3. Human approval is explicit. A pending HITL ticket is not approval.
4. Audit data is append-only. New stores should follow the `contrato_eventos`
   pattern.
5. Runtime code belongs under `src/kabbalah/`. Root-level Python is limited to
   explicit entrypoints such as the MCP bridge.
6. Mock providers are for tests only and must remain gated by explicit test
   configuration.
7. Secrets are never stored in source files. Runtime credentials come from the
   configured vault or environment and must not be logged.

## Persistence

The MCP bridge uses a single SQLite state database selected by
`KABBALAH_BRIDGE_STATE_DB` and defaulting to `.kabbalah_bridge_state.sqlite3`.
Current tables include HITL tickets, contract state/events, `budget_ledger`,
and `hardware_profiles`. Future stores should reuse the same database unless
the architecture document and ADRs justify a different boundary.

SQLite stores should use short-lived connections, a busy timeout, and explicit
append-only event tables for audit trails.

## Repository layout

```text
kabbalah/
├── .github/                 # CI and GitHub templates
├── archive/                 # legacy source snapshots kept for lineage
├── config/                  # example configuration
├── docs/
│   ├── ARCHITECTURE.md      # this document
│   ├── adr/                 # dated architecture decision records
│   ├── analysis/            # non-canonical analysis inputs
│   ├── archive/             # archived specs, reports, and tool artifacts
│   ├── audit/               # forensic/security audit records
│   ├── development/         # local workflow and Git guidance
│   ├── governance/          # security and execution policy
│   ├── ops/                 # operational context packs
│   ├── roadmap/             # executable plans and future waves
│   ├── security/            # security migration and incident notes
│   └── specs/               # living specs and setup guides
├── scripts/                 # operational scripts
├── src/kabbalah/            # canonical Python package
├── tests/                   # canonical test suite
├── kabbalah_mcp_bridge.py   # stdio MCP bridge entrypoint
└── setup.py                 # packaging and CLI entrypoint
```

Root-level Markdown should stay minimal: `README.md`, `CONTRIBUTING.md`, and
`LICENSE`. Historical phase reports belong under `docs/archive/`.

## References

- Execution plan: `docs/roadmap/handoff-execution-plan.md`
- Cleanup plan: `docs/roadmap/cleanup-execution-plan.md`
- Completed hardening waves: `docs/roadmap/hardening-next-waves.md`
- ADR index: `docs/adr/`
- No-mock runtime policy: `docs/specs/NO_MOCK_RUNTIME_POLICY.md`
