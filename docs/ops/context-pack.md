# Context Pack

Role: alpha-stage multi-agent orchestration runtime for experimentation and recovery.

> Workspace-level rules (all AIs, all projects): `E:\projetos\AGENTS.md` — this
> project folder (`E:\projetos\kabbalah`) is the working root; never treat
> `E:\projetos` as the project.

## Document hierarchy (read this first — binding for any AI/dev)

1. **Canonical execution plan**: `docs/roadmap/handoff-execution-plan.md` (waves
   4–10, reconciled against the code on 2026-07-04). On any divergence between
   documents, THIS file wins — but always re-validate its claims against the code.
2. **Cleanup spec**: `docs/roadmap/cleanup-execution-plan.md` — the detailed
   version of wave 4. Its Phase A (git-history secret scan) is mandatory before
   any GitHub push, regardless of wave order.
3. **Analysis input (NOT canonical)**: `docs/analysis/MELHORIAS_E_APRIMORAMENTOS.md` — external
   strategic analysis. Valuable for positioning/market context, but contains
   stale technical claims; the reconciliation table in the handoff plan §0 lists
   which of its items are already done or outdated. Never execute from it directly.
4. **Completed history**: `docs/roadmap/hardening-next-waves.md` (waves 1–3, done).
5. **Legacy — ignore**: `workspace/docs/ARCHITECTURE.md` and everything under
   `workspace/` (untracked, outdated; scheduled for removal in cleanup Phase C).
6. **Single architecture doc**: `docs/ARCHITECTURE.md` — created by cleanup
   Phase D.1 and now maintained as the concise architecture overview. Do not
   create competing architecture documents elsewhere.

Wave order: cleanup (wave 4) and the LLM loop (wave 5) are independent and may be
executed in either order; waves 6+ follow the dependencies stated in the handoff plan.

Runtime: Python package under `src/kabbalah`; tests under `tests`; packaging via `pyproject.toml` with `setup.py` kept as a compatibility shim.

Do not use: real secrets in repo files, ungated mock provider behavior, root-level runtime modules, or old phase reports as source-of-truth.

Critical commands:

- `.venv\Scripts\python.exe -m pytest tests -q`
- `python -m pip install -r requirements.txt`
- `python -m pip install -r requirements-dev.txt`
- `python -m pip install -e ".[memory]"`
- `python -m pip install -e ".[observability]"`
- `python -m pip install -e .`

Known gotchas:

- The active Windows Python may point to a tool-managed interpreter without `pip`; use the project `.venv`.
- `LocalLLMProvider` exists as legacy code; the main provider factory now routes local Ollama-style calls through `ollama_local` and `OpenAICompatibleProvider`.
- Cognee is optional and installed via `pip install -e ".[memory]"`; `requirements-memory.txt` is kept as a mirror.
- Test/quality dependencies are in the `dev` extra and `requirements-dev.txt`; telemetry exporters are in the `observability` extra and `requirements-observability.txt`.
- Root/domain orchestration is sequential in code even where older docs/config mention parallel execution.
- Leaf execution performs real provider calls only when `DomainOrchestrator` is constructed with an `LLMGateway`; without an injected gateway it returns explicit `status="skipped"`, not fake success.
- Live provider tests require explicit gating; see `docs/specs/NO_MOCK_RUNTIME_POLICY.md`.

Recent decisions:

- Keep active code in `src/kabbalah`.
- Move historical root reports to `docs/archive/reports`.
- Move legacy code snapshots to `archive/legacy`.
- Onda 5 uses `LLMGateway` as the provider selector, `ProviderFactory` only as
  constructor, `BudgetLedger` as append-only call ledger, and `HardwareProfiler`
  as the canonical local hardware fingerprint/fit source.
- Onda 7 adds `BudgetManager` enforcement (`warn` default, `block` opt-in),
  gateway budget checks, ordered provider fallback, `get_budget_stats`, and
  profile-priced ledger costs when provider responses report `cost=0.0`.
- Onda 8 started with provider default refresh (`gpt-4o`, `gemini-2.5-pro`,
  `mistral-large`, `gpt-oss-120b`, `Meta-Llama-3.3-70B-Instruct`), safe
  config status (`get_config_status`), `compare_models`, SillyTavern group
  event rendering (`render_group_event`), and `kabbalah status --json`.
  Remaining visible-product work: full `kabbalah setup/config` wizard, rich
  status panel, packaging/CI, and README-vitrine.
- Onda 9 added Kabbalah-Bench and optional tree search behind
  `KABBALAH_SEARCH_MODE=tree`; default orchestration remains linear.
- Onda 11 added offline signed SyncHub bundles: Ed25519 identity, trust list,
  modes `off|receber|receber+contribuir`, replay/tamper/version gates, and
  benchmark before/after evidence for federated corrections.

Validation baseline:

- On 2026-06-25, the original base dependency set was not installable because optional Cognee conflicted with pinned core dependencies. Cognee was moved to `requirements-memory.txt`.
