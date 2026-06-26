# Context Pack

Role: alpha-stage multi-agent orchestration runtime for experimentation and recovery.

Runtime: Python package under `src/kabbalah`; tests under `tests`; packaging via `setup.py` and `requirements.txt`.

Do not use: real secrets in repo files, ungated mock provider behavior, root-level runtime modules, or old phase reports as source-of-truth.

Critical commands:

- `python -m pytest tests -q`
- `python -m pip install -r requirements.txt`
- `python -m pip install -r requirements-dev.txt`
- `python -m pip install -r requirements-memory.txt`
- `python -m pip install -r requirements-observability.txt`
- `python -m pip install -e .`

Known gotchas:

- The active Windows Python may point to a tool-managed interpreter without `pip`; use a project virtual environment.
- `LocalLLMProvider` exists for Ollama-style local calls but is not registered in the main provider factory.
- Cognee is optional and installed via `requirements-memory.txt`, not the base requirements file.
- Test/quality dependencies are in `requirements-dev.txt`; telemetry exporters are in `requirements-observability.txt`.
- Root/domain orchestration is sequential in code even where older docs/config mention parallel execution.
- Leaf execution still returns placeholder success artifacts and does not perform real provider/tool execution.
- Live provider tests require explicit gating; see `docs/specs/NO_MOCK_RUNTIME_POLICY.md`.

Recent decisions:

- Keep active code in `src/kabbalah`.
- Move historical root reports to `docs/archive/reports`.
- Move legacy code snapshots to `archive/legacy`.

Validation baseline:

- On 2026-06-25, the original base dependency set was not installable because optional Cognee conflicted with pinned core dependencies. Cognee was moved to `requirements-memory.txt`.
