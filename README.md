# Kabbalah

[![Status](https://img.shields.io/badge/status-alpha-yellow)](https://github.com/charlesnobrega/kabbalah)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Kabbalah is an alpha-stage Python project for multi-agent orchestration. The repository contains a tree-based orchestration skeleton, provider abstractions, runtime hardening primitives, memory modules, tool execution primitives, observability primitives, and tests.

This repository is not yet a production autonomous runtime. Current gaps include root-level gateway wiring, configuration/onboarding UI, Cognee-backed semantic retrieval, skill registry wiring, graph runtime wiring, and true parallel execution in the main orchestration path.

## Current runtime reality

- Main package: `src/kabbalah`.
- Packaging: `pyproject.toml`, `setup.py` compatibility shim, `requirements*.txt` mirrors.
- Runtime provider factory currently supports native OpenAI, Google Gemini, Groq, Mistral, Together, and DeepSeek, plus OpenAI-compatible entries for Ollama local, OpenRouter, Groq-compatible, Cerebras, and SambaNova.
- `MockProvider` is test-only, is not exported from `kabbalah.providers`, and must stay gated by `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`.
- `LocalLLMProvider` exists as legacy code; the main local route is `ollama_local` through the generic OpenAI-compatible adapter.
- Root/domain orchestration is sequential in the current implementation, despite config/docs describing intended parallelism.
- Leaf execution runs a real provider loop only when `DomainOrchestrator` is constructed with an injected `LLMGateway`; without a gateway it returns explicit `status="skipped"`, not fake success.
- SillyTavern MCP bridge exists at `kabbalah_mcp_bridge.py` and exposes guarded tools through qlipot, FirewallMCP, HITL tickets, Bitwarden cache, agent contracts, retry limits, SyncHub stats, budget stats, safe config status, and model comparison.
- Agent contracts are persisted in SQLite by the bridge. SyncHub network propagation is phase-1/local only; P2P/central federation is not production-wired yet.

## Repository layout

```text
kabbalah/
├── src/kabbalah/              # Runtime package
├── tests/                     # Unit, integration, provider, property tests
├── config/                    # Example configuration
├── docs/
│   ├── ARCHITECTURE.md        # Single architecture overview
│   ├── adr/                   # Architecture decision records
│   ├── analysis/              # Non-canonical analysis inputs
│   ├── archive/               # Historical specs, reports, updates, tool artifacts
│   ├── audit/                 # Audit evidence and findings
│   ├── development/           # Contributor workflow
│   ├── governance/            # Operating rules
│   ├── ops/                   # Short operational context for future agents
│   ├── roadmap/               # Executable plans and future waves
│   ├── security/              # Security incident/migration notes
│   └── specs/                 # Living specs, policies, and setup guides
├── archive/legacy/            # Legacy code snapshots kept out of import paths
├── scripts/                   # Utility scripts
├── requirements*.txt          # Base, dev, MCP, memory, observability dependencies
├── kabbalah_mcp_bridge.py     # stdio MCP bridge entrypoint
├── pyproject.toml
├── setup.py
├── pytest.ini
├── ruff.toml
└── README.md
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

For Windows/PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

Development/test dependencies are separate:

```bash
python -m pip install -r requirements-dev.txt
```

Cognee-backed semantic memory is optional and intentionally kept out of the base install:

```bash
python -m pip install -e ".[memory]"
```

External telemetry exporters are also optional:

```bash
python -m pip install -e ".[observability]"
```

Optional MCP bridge dependencies are isolated because the official MCP SDK may
require newer transitive dependency versions than the legacy provider stack:

```bash
python -m pip install -e ".[mcp]"
```

## Setup and CLI status

Configure provider keys per installation with the interactive wizard:

```bash
kabbalah setup
```

The wizard lists supported providers, reads keys with hidden input, validates
each key with a minimal provider call, and stores valid keys in the OS keyring.
It does not write provider keys to tracked files, the state database, logs, or
stdout.

Useful config commands:

```bash
kabbalah config list --json
kabbalah config add-key openai --json
kabbalah config test-key openai --json
kabbalah config remove-key openai --json
kabbalah config set-budget --mode block --run-usd 1.25 --daily-usd 5 --json
kabbalah config set-routing budget_first --json
```

The runtime status panel is available as JSON:

```bash
kabbalah status --json
```

It returns safe provider key status (`present`/`absent`, source and `last4`) and
budget/hardware stats. It must not print full API keys or secrets.

Use `-v` or `-vv` for progressive logging. CLI exit codes are documented in
`docs/specs/cli-exit-codes.md`.

## SillyTavern MCP bridge

The example config for SillyTavern is available in:

- `sillytavern_config.json`
- `sillytavern_mcp_config.json`
- `docs/examples/sillytavern/kabbalah-group-chat/`

Current bridge tools include:

- `read_file`, `write_file`, `execute_command`, `network_request`
- `read_env_var`, `call_tool`, `database_query`
- `check_hitl_status`
- `propose_contract`, `sign_contract`, `reject_contract`, `complete_task`
- `get_network_stats`, `get_budget_stats`, `get_config_status`
- `compare_models`
- `render_group_event`

All bridge logging is configured for `stderr`; `stdout` remains reserved for
MCP/JSON-RPC stdio traffic.

`compare_models` sends the same task to selected gateway providers and returns
JSON rows with `provider`, `model`, `latency_ms`, `tokens`, `cost`, `response`,
and `error`. It uses the normal bridge authorization pipeline and the
`LLMGateway`, so budget policy and missing API keys surface as real provider
errors instead of mock output. Test-only comparisons use `MockProvider` only
when `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`.

`render_group_event` formats Kabbalah decisions for SillyTavern group chats
with stable prefixes such as `[KABBALAH:DENY]`, `[KABBALAH:HITL]`,
`[KABBALAH:BUDGET]`, and `[KABBALAH:CONFIG]`. Secret-like detail keys are
redacted before display text is returned.

Wave-1 hardening defaults:

- Contracts are required by default before non-bootstrap MCP tools run. Flow:
  `propose_contract` with `papeis=["coordinator"]` → `sign_contract` → target
  tool. Temporary escape hatch: `KABBALAH_BRIDGE_REQUIRE_CONTRACTS=0`.
- `execute_command` is disabled by default in the bridge. Enable only when
  operationally required with `KABBALAH_BRIDGE_ENABLE_SHELL=1`.
- File/database paths are restricted by `KABBALAH_BRIDGE_ALLOWED_DIRS`
  (defaults to this repository root).
- `read_env_var` only returns variables listed in
  `KABBALAH_BRIDGE_ENV_ALLOWLIST`.
- Private, loopback, link-local, reserved and unspecified network destinations
  are blocked unless `KABBALAH_BRIDGE_ALLOW_PRIVATE_NETWORKS=1`.

Wave-2 hardening (persistent contracts):

- Agent contracts are persisted in SQLite (`KABBALAH_BRIDGE_STATE_DB`, same
  file as HITL tickets). A signed contract survives a bridge restart.
- `max_calls` consumption is an atomic SQL update, safe under concurrency.
- Violations and contract-absence attempts are recorded in an append-only
  audit log (`contrato_eventos` table).
- Absence of a contract is audited as `ausencia_contrato` and is no longer
  conflated with a real violation of an active contract.

Wave-3 hardening (scoring and vault):

- Risk scoring normalizes unicode (NFKC, zero-width stripping, homoglyph
  folding), matches real destructive command patterns beyond keywords, and
  decodes plausible base64 payloads before evaluation.
- `qlipot.aplicar_correcao` is restricted to authorized origins, clamps the
  delta to ±0.30, and keeps an append-only correction audit trail stamped
  with `RISK_ASSESSOR_VERSION`.
- Vault: `BITWARDEN_CLI_PATH` pins the `bw` binary path, `KABBALAH_BW_SHA256`
  optionally pins its hash, and `clear_on_read=True` makes cached secrets
  single-use.

Wave-5 LLM loop:

- `LLMGateway` is the canonical provider selector by role, capability, and budget hint.
- `OpenAICompatibleProvider` covers Ollama local, OpenRouter, Groq-compatible, Cerebras, and SambaNova without provider-specific SDKs.
- `DomainOrchestrator` can execute leaf work through an injected gateway and returns `llm_response` artifacts on real provider success.
- `BudgetLedger` records provider/model tokens and cost in append-only SQLite when injected.
- `HardwareProfiler` fingerprints local CPU/GPU/RAM, stores hardware profiles in the bridge state DB, and classifies local model fit/tier without vendor-based assumptions.

Wave-7 budget manager:

- `BudgetManager` enforces configurable limits by run, day, and provider from `KABBALAH_BUDGET_*`.
- `KABBALAH_BUDGET_MODE=warn` is the default; `KABBALAH_BUDGET_MODE=block` raises `BudgetExceededError`.
- `LLMGateway` checks budget before returning providers and supports ordered fallback candidates.
- `get_budget_stats` is exposed as a read-only MCP bridge tool.
- Leaf ledger cost uses provider `usage` plus `ModelProfile` pricing when a provider reports `cost=0.0`.

## Configuration

Use `.env.example` as a template only. Do not commit real credentials.

Supported provider names in the current factory:

- `openai`
- `google_gemini`
- `groq`
- `mistral`
- `together`
- `deepseek`
- `ollama_local`
- `openrouter`
- `groq_compatible`
- `cerebras`
- `sambanova`

Example:

```bash
KABBALAH_PROVIDER_MODE=unified
KABBALAH_PROVIDER=openai
KABBALAH_MODEL=gpt-4
OPENAI_API_KEY=your_key_here
```

## Tests

```bash
python -m pytest tests -q
```

On Windows/PowerShell, prefer the project virtual environment explicitly:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

If collection fails with missing dependencies, install the project dependencies in an isolated virtual environment first:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Live provider tests must not run implicitly. Use the policy in `docs/specs/NO_MOCK_RUNTIME_POLICY.md` before enabling any live external call.

## Important docs

- [Architecture](docs/ARCHITECTURE.md)
- [Execution Handoff Plan](docs/roadmap/handoff-execution-plan.md)
- [Cleanup Execution Plan](docs/roadmap/cleanup-execution-plan.md)
- [Repository Audit](docs/specs/REPOSITORY_AUDIT.md)
- [No Mock Runtime Policy](docs/specs/NO_MOCK_RUNTIME_POLICY.md)
- [Governance](docs/governance/GOVERNANCE.md)
- [Git Workflow](docs/development/GIT_WORKFLOW.md)
- [Roadmap](docs/roadmap/ROADMAP.md)

## Development standards

- Keep code under `src/kabbalah`; do not add importable runtime modules at repository root.
- Keep historical reports under `docs/archive/reports`.
- Keep legacy snapshots under `archive/legacy` unless they are being actively migrated.
- Do not hardcode or print secrets.
- Prefer small changes with tests and documentation updates.
- Do not claim production readiness until runtime provider/tool execution is wired and verified.

## License

MIT. See [LICENSE](LICENSE).
