# Context Pack

Role: alpha-stage multi-agent orchestration runtime for experimentation and recovery.

## Document hierarchy (read this first — binding for any AI/dev)

1. **Canonical execution plan**: `docs/roadmap/handoff-execution-plan.md` (waves
   4–10, reconciled against the code on 2026-07-04). On any divergence between
   documents, THIS file wins — but always re-validate its claims against the code.
2. **Cleanup spec**: `docs/roadmap/cleanup-execution-plan.md` — the detailed
   version of wave 4. Its Phase A (git-history secret scan) is mandatory before
   any GitHub push, regardless of wave order.
3. **Analysis input (NOT canonical)**: `MELHORIAS_E_APRIMORAMENTOS.md` — external
   strategic analysis. Valuable for positioning/market context, but contains
   stale technical claims; the reconciliation table in the handoff plan §0 lists
   which of its items are already done or outdated. Never execute from it directly.
4. **Completed history**: `docs/roadmap/hardening-next-waves.md` (waves 1–3, done).
5. **Legacy — ignore**: `workspace/docs/ARCHITECTURE.md` and everything under
   `workspace/` (untracked, outdated; scheduled for removal in cleanup Phase C).
6. **Future single architecture doc**: `docs/ARCHITECTURE.md` does not exist yet —
   it is the deliverable of cleanup Phase D.1. Do not create competing
   architecture documents elsewhere.

Wave order: cleanup (wave 4) and the LLM loop (wave 5) are independent and may be
executed in either order; waves 6+ follow the dependencies stated in the handoff plan.

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
