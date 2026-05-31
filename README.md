# Kabbalah - Multi-Agent Orchestration System

[![Status](https://img.shields.io/badge/status-development-yellow)](https://github.com/charlesnobrega/kabbalah)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Kabbalah is an alpha-stage multi-agent orchestration project. The repository currently contains a tree-based orchestration skeleton, runtime hardening primitives, provider abstractions, memory modules, tool execution primitives, observability primitives, and a broad test suite.

Important status note: the codebase is not yet a production-ready autonomous runtime. Several core paths are intentionally classified as partial or prototype, including real leaf execution, Cognee semantic retrieval, MCP execution, centralized policy orchestration, skill registry, and graph runtime.

## 🎯 Core Vision

Build an IDE that orchestrates multiple specialized agents in parallel, enforces compliance at runtime, shares semantic memory across agents, and delivers consolidated results with full auditability.

## 🏗️ Architecture

```
User Request
    ↓
[Intake Node] - Parse & refine request
    ↓
[Root Orchestrator] - Decompose into domains
    ↓
[Domain Orchestrators] - Coordinate per-domain execution (parallel)
    ↓
[Leaf Nodes] - Execute concrete tasks in parallel
    ↓
[Synthesizer] - Consolidate results
    ↓
Delivery Package
```

## ✨ Key Features

### 1. Tree-Based Orchestration
- Hierarchical structure for natural domain decomposition
- Parallel execution with dependency management
- Clear responsibility boundaries

### 2. Runtime Hardening
- FSM enforcement (BOOTSTRAP, DAY1, DAY2 modes)
- Role-based access control
- Contract enforcement (pre/post-conditions)
- Complete audit logging

### 3. Semantic Memory Sharing
- Cognee integration for semantic memory (Linux/macOS)
- JSONL fallback for Windows
- Atomic operations for consistency
- Memory governance with access control

### 4. Multi-Provider LLM Abstraction
- Runtime provider factory currently supports:
  - OpenAI
  - Google Gemini
  - Groq
  - Mistral
  - Together
  - DeepSeek
- A gated `MockProvider` exists for tests only.
- 4 configuration modes:
  - **Unified**: Same provider for all roles
  - **Explicit**: Define provider for each role
  - **Hierarchy**: System recommends based on role
  - **Hybrid**: Default + role-specific overrides
- Automatic fallback chains

### 5. Observability
- Hierarchical trace_id tracking (run_id:branch_id:leaf_id)
- Structured logging with full context
- Metrics collection (latency, error rate, provider usage)
- In-memory trace/log/metric collection

External telemetry export is not yet implemented.

### 6. Tool Execution
- Bash command execution
- File operations (read/write/delete)
- Grep search
- MCP tool execution
- Web requests
- Sandboxed execution with resource limits

### 7. Day 2 Operations Compliance
- Production-safe mode enforcement
- Bootstrap operation blocking
- Immutable audit logging
- Compliance validation

## 📋 Requirements

- Python 3.9+
- pip or poetry for dependency management
- LLM provider API keys (OpenAI, Anthropic, etc.)
- Optional: Cognee for semantic memory (Linux/macOS)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/charlesnobrega/kabbalah.git
cd kabbalah
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 4. Configure Providers

Create a `.env` file:

```bash
# Unified Mode (same provider for all)
KABBALAH_PROVIDER_MODE=unified
KABBALAH_PROVIDER=openai
KABBALAH_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=your_key_here

# Or Explicit Mode (different providers per role)
KABBALAH_PROVIDER_MODE=explicit
KABBALAH_INTAKE_PROVIDER=openai
KABBALAH_INTAKE_MODEL=gpt-3.5-turbo
KABBALAH_LEAF_VERIFIER_PROVIDER=anthropic
KABBALAH_LEAF_VERIFIER_MODEL=claude-3-sonnet
ANTHROPIC_API_KEY=your_key_here
```

### 5. Run Tests

```bash
pytest tests/ -v --cov=src/kabbalah
```

### 6. Check Configuration

```bash
kabbalah config --show
```

## 📚 Documentation

- **[Repository Audit](docs/specs/REPOSITORY_AUDIT.md)** - Current implementation status and risks
- **[Current Architecture](docs/architecture/CURRENT_ARCHITECTURE.md)** - Source-of-truth architecture map
- **[Repository Structure](docs/architecture/REPOSITORY_STRUCTURE.md)** - Documentation and project layout
- **[Governance](docs/governance/GOVERNANCE.md)** - Execution, tool, approval, security, rollback, and audit policy
- **[Git Workflow](docs/development/GIT_WORKFLOW.md)** - Branch, PR, commit, release, and rollback rules
- **[Roadmap](docs/roadmap/ROADMAP.md)** - Forward-looking roadmap
- **[Project Recovery Report](docs/specs/PROJECT_RECOVERY_REPORT.md)** - Recovery priorities and time horizons
- **[Requirements](docs/specs/requirements.md)** - 16 detailed requirements with acceptance criteria
- **[Design](docs/specs/design.md)** - Architecture, components, and interfaces
- **[Tasks](docs/specs/tasks.md)** - 167 implementation tasks organized by phase
- **[Provider Hierarchy](docs/specs/PROVIDER_HIERARCHY.md)** - Provider recommendations by role
- **[Configuration Guide](docs/specs/CONFIGURATION_GUIDE.md)** - User-friendly setup guide
- **[Validation Report](docs/specs/VALIDATION_REPORT.md)** - Complete spec validation

## 🔧 Configuration Modes

### Unified Mode (Simplest)
Use the same provider for all roles:

```yaml
providers:
  mode: unified
  provider: openai
  model: gpt-3.5-turbo
```

### Explicit Mode (Most Control)
Define provider for each role:

```yaml
providers:
  mode: explicit
  roles:
    intake_clarifier:
      provider: openai
      model: gpt-3.5-turbo
    leaf_verifier:
      provider: anthropic
      model: claude-3-sonnet
    # ... more roles
```

### Hierarchy Mode (Best Balance)
Let system recommend providers:

```yaml
providers:
  mode: hierarchy
  # System automatically uses:
  # - Premium models for Intake, Root, Synthesizer
  # - Mid-tier for Domain Coordinator
  # - Cost-effective for Leaf Builders
```

### Hybrid Mode (Flexible)
Default provider with role-specific overrides:

```yaml
providers:
  mode: hybrid
  default:
    provider: openai
    model: gpt-3.5-turbo
  overrides:
    leaf_verifier:
      provider: anthropic
      model: claude-3-sonnet
```

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suite

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Property-based tests
pytest tests/property/ -v
```

### Generate Coverage Report

```bash
pytest tests/ --cov=src/kabbalah --cov-report=html
open htmlcov/index.html
```

## 📊 Project Structure

```
kabbalah/
├── src/kabbalah/
│   ├── __init__.py
│   ├── models.py                    # Data models
│   ├── intake_node.py               # Request parsing
│   ├── root_orchestrator.py         # Specification decomposition
│   ├── domain_orchestrator.py       # Domain coordination
│   ├── synthesizer.py               # Result consolidation
│   ├── fsm_enforcement.py           # FSM enforcement
│   ├── role_trace_validation.py     # Role validation
│   ├── contract_enforcement.py      # Contract validation
│   ├── memory_subsystem.py          # Semantic memory
│   ├── memory_governance.py         # Memory access control
│   ├── trace_id_tracking.py         # Hierarchical tracing
│   ├── transition_validation.py     # Mode transitions
│   ├── domain_orchestrator.py       # Domain orchestration
│   └── ...
├── tests/
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   ├── property/                    # Property-based tests
│   └── ...
├── docs/
│   ├── specs/
│   │   ├── requirements.md
│   │   ├── design.md
│   │   ├── tasks.md
│   │   ├── PROVIDER_HIERARCHY.md
│   │   ├── CONFIGURATION_GUIDE.md
│   │   └── VALIDATION_REPORT.md
│   └── ...
├── config/
│   ├── config.yaml                  # Default configuration
│   └── ...
├── requirements.txt
├── setup.py
├── README.md
└── .gitignore
```

## 🎯 Current Recovery Priorities

1. Keep documentation aligned with actual code.
2. Wire policy checks into orchestration and tool execution.
3. Replace placeholder leaf execution with real, policy-gated provider/tool execution.
4. Implement or explicitly downgrade semantic memory claims.
5. Add external telemetry only after runtime behavior is stable.

## 🔐 Security

- Role-based access control (RBAC)
- Input validation and sanitization
- Encryption at rest and in transit
- Immutable audit logging
- Sandboxed tool execution
- Contract enforcement

## 📈 Performance

- Specification decomposition: <30 seconds
- Parallel execution overhead: <10%
- Result synthesis: <60 seconds
- Trace propagation: <5ms per operation
- Support for 100+ parallel leaf nodes

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code follows PEP 8 style guide
- Tests are included for new features
- Documentation is updated
- Test coverage remains >80%

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Charles Nóbrega** - Initial work

## 🙏 Acknowledgments

- KIRO V5 for tree-based orchestration concepts
- OpenClaude for provider abstraction
- Cognee for semantic memory
- Property-based testing community

## 📞 Support

For support, email support@example.com or open an issue on GitHub.

## 🗺️ Roadmap

- [x] Specification and design
- [ ] Phase 1: Core orchestration
- [ ] Phase 2: Runtime hardening
- [ ] Phase 3: Memory subsystem
- [ ] Phase 4: Provider abstraction
- [ ] Phase 5: Tool execution
- [ ] Phase 6: Observability
- [ ] Phase 7: Parser/pretty printer
- [ ] Phase 8: Configuration
- [ ] Phase 9: Day 2 operations
- [ ] Phase 10: Integration testing
- [ ] Phase 11: Documentation
- [ ] v1.0 Release

---

**Status**: Alpha / recovery and professionalization
**Last Updated**: 2026-05-31
