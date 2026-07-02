# Kabbalah

[![Status](https://img.shields.io/badge/status-alpha-yellow)](https://github.com/charlesnobrega/kabbalah)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Kabbalah is an alpha-stage Python project for multi-agent orchestration. The repository contains a tree-based orchestration skeleton, provider abstractions, runtime hardening primitives, memory modules, tool execution primitives, observability primitives, and tests.

This repository is not yet a production autonomous runtime. Current gaps include real leaf execution, centralized policy orchestration, MCP execution, Cognee-backed semantic retrieval, skill registry wiring, graph runtime wiring, and true parallel execution in the main orchestration path.

## Current runtime reality

- Main package: `src/kabbalah`.
- Packaging: `setup.py`, `requirements.txt`.
- Runtime provider factory currently supports OpenAI, Google Gemini, Groq, Mistral, Together, and DeepSeek.
- `MockProvider` is test-only and must stay gated by `KABBALAH_ALLOW_TEST_FAKE_PROVIDER=1`.
- `LocalLLMProvider` exists for Ollama-style local calls, but it is not wired into the main provider factory yet.
- Root/domain orchestration is sequential in the current implementation, despite config/docs describing intended parallelism.
- Leaf execution currently returns placeholder success artifacts; it does not yet run a real provider/tool loop.
- SillyTavern MCP bridge exists at `kabbalah_mcp_bridge.py` and exposes guarded tools through qlipot, FirewallMCP, HITL tickets, Bitwarden cache, agent contracts, retry limits, and SyncHub stats.
- Agent contracts and SyncHub are implemented as local in-memory primitives. Network propagation is phase-1/local only; P2P/central federation is not production-wired yet.

## Repository layout

```text
kabbalah/
├── src/kabbalah/              # Runtime package
├── tests/                     # Unit, integration, provider, property tests
├── config/                    # Example configuration
├── docs/
│   ├── architecture/          # Current architecture and structure docs
│   ├── specs/                 # Requirements, design, policies, roadmap specs
│   ├── adr/                   # Architecture decision records
│   ├── audit/                 # Audit evidence and findings
│   ├── development/           # Contributor workflow
│   ├── governance/            # Operating rules
│   ├── ops/                   # Short operational context for future agents
│   └── archive/reports/       # Historical phase/session reports
├── archive/legacy/            # Legacy code snapshots kept out of import paths
├── scripts/                   # Utility scripts
├── requirements.txt
├── setup.py
├── pytest.ini
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
python -m pip install -r requirements-memory.txt
```

External telemetry exporters are also optional:

```bash
python -m pip install -r requirements-observability.txt
```

Optional MCP bridge dependencies are isolated because the official MCP SDK may
require newer transitive dependency versions than the legacy provider stack:

```bash
python -m pip install -r requirements-mcp.txt
```

## SillyTavern MCP bridge

The example config for SillyTavern is available in:

- `sillytavern_config.json`
- `sillytavern_mcp_config.json`

Current bridge tools include:

- `read_file`, `write_file`, `execute_command`, `network_request`
- `read_env_var`, `call_tool`, `database_query`
- `check_hitl_status`
- `propose_contract`, `sign_contract`, `reject_contract`, `complete_task`
- `get_network_stats`

All bridge logging is configured for `stderr`; `stdout` remains reserved for
MCP/JSON-RPC stdio traffic.

## Configuration

Use `.env.example` as a template only. Do not commit real credentials.

Supported provider names in the current factory:

- `openai`
- `google_gemini`
- `groq`
- `mistral`
- `together`
- `deepseek`

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

If collection fails with missing dependencies, install the project dependencies in an isolated virtual environment first:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Live provider tests must not run implicitly. Use the policy in `docs/specs/NO_MOCK_RUNTIME_POLICY.md` before enabling any live external call.

## Important docs

- [Current Architecture](docs/architecture/CURRENT_ARCHITECTURE.md)
- [Repository Structure](docs/architecture/REPOSITORY_STRUCTURE.md)
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
